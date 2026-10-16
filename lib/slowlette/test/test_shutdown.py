"""Run with PYTHONPATH=lib/slowlette python -m unittest discover -s lib/slowlette/test -p test_shutdown.py."""
import asyncio
import os
import itertools
from pathlib import Path
import signal
import subprocess
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

import slowlette
from slowlette.server import dispatch_asgi


class LifespanTests(unittest.IsolatedAsyncioTestCase):
    async def test_shutdown_returns_and_runs_hooks_once(self):
        events = []
        async def dispatch(name):
            events.append(name)
        app = SimpleNamespace(slowlette=SimpleNamespace(dispatch_event=dispatch))
        messages = asyncio.Queue()
        messages.put_nowait({'type': 'lifespan.shutdown'})
        receive = AsyncMock(side_effect=messages.get)
        send = AsyncMock()
        await asyncio.wait_for(dispatch_asgi(app, {'type': 'lifespan'}, receive, send), 1)
        self.assertEqual(events, ['shutdown', 'post_shutdown'])
        receive.assert_awaited_once()
        send.assert_awaited_once_with({'type': 'lifespan.shutdown.complete'})

    async def test_cancelled_lifespan_does_not_emit_pre_shutdown(self):
        dispatch = AsyncMock()
        app = SimpleNamespace(slowlette=SimpleNamespace(dispatch_event=dispatch))
        await dispatch_asgi(app, {'type': 'lifespan'},
                            AsyncMock(side_effect=asyncio.CancelledError), AsyncMock())
        dispatch.assert_awaited_once_with('shutdown')

    async def test_pre_shutdown_stops_subapps_in_reverse_order(self):
        events = []
        class Component(slowlette.App):
            def __init__(self, name):
                super().__init__()
                self.name = name
            @slowlette.on_event('pre_shutdown')
            async def stop(self):
                events.append(self.name)
        app = slowlette.App()
        app.slowlette.include(Component('broker'))
        app.slowlette.include(Component('consumer'))
        await app.slowlette.dispatch_event('pre_shutdown')
        self.assertEqual(events, ['consumer', 'broker'])

    async def test_websocket_cancellation_propagates_even_if_close_fails(self):
        for close_error in (None, RuntimeError('connection already closed')):
            with self.subTest(close_error=close_error):
                app = SimpleNamespace(slowlette=SimpleNamespace(
                    websocket=AsyncMock(side_effect=asyncio.CancelledError)))
                send = AsyncMock(side_effect=close_error)
                with self.assertRaises(asyncio.CancelledError):
                    await dispatch_asgi(app, {'type': 'websocket', 'raw_path': b'/ws',
                                             'headers': []}, AsyncMock(), send)
                send.assert_awaited_once()


@unittest.skipUnless(os.name == 'posix', 'requires POSIX signals')
class SignalShutdownTests(unittest.TestCase):
    def test_live_websocket_is_closed_before_lifespan_shutdown(self):
        # The child uses real server signal handlers and a connected client.
        # A pre-bound socket keeps the test independent of fixed port allocation.
        code = r'''
import asyncio, os, signal, socket
import slowlette
import uvicorn
import websockets
from slowlette.server import serve_asgi_uvicorn, serve_asgi_hypercorn

sock = socket.socket()
sock.bind(('127.0.0.1', 0))
port = sock.getsockname()[1]
events = []
background = []
class App(slowlette.App):
    @slowlette.on_event('startup')
    async def startup(self):
        background.append(asyncio.create_task(client()))
    @slowlette.websocket('/ws')
    async def ws(self, websocket: slowlette.WebSocket):
        await websocket.accept()
        self.connection = websocket
        events.append('connected')
        try:
            while True:
                await websocket.receive()
        except slowlette.WebSocketConnectionClosed:
            events.append('disconnected')
    @slowlette.on_event('pre_shutdown')
    async def pre_shutdown(self):
        events.append('pre_shutdown')
        await self.connection.close(code=1001)
    @slowlette.on_event('shutdown')
    async def shutdown(self):
        events.append('shutdown')
        await asyncio.gather(*background)
    @slowlette.on_event('post_shutdown')
    async def post_shutdown(self):
        events.append('post_shutdown')
        assert events == ['connected', 'pre_shutdown', 'disconnected', 'shutdown', 'post_shutdown'], events
        print('HOOKS_OK', flush=True)

async def client():
    while True:
        try:
            ws = await websockets.connect(f'ws://127.0.0.1:{port}/ws')
            break
        except OSError:
            await asyncio.sleep(0.01)
    async with ws:
        await asyncio.sleep(0.2)  # also exercises the old signal override
        os.kill(os.getpid(), SIGNAL)
        await ws.wait_closed()

runner = serve_asgi_uvicorn if SERVER == 'uvicorn' else serve_asgi_hypercorn
previous_handlers = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
runner(App(), port, fd=sock.fileno(), ws='websockets-sansio')
assert all(signal.getsignal(sig) == handler for sig, handler in previous_handlers.items())
assert events == ['connected', 'pre_shutdown', 'disconnected', 'shutdown', 'post_shutdown'], events
print('SHUTDOWN_OK', flush=True)
'''
        for server, sig in itertools.product(('uvicorn', 'hypercorn'), (signal.SIGINT, signal.SIGTERM)):
            with self.subTest(server=server, signal=sig.name):
                env = dict(os.environ)
                package_root = str(Path(__file__).resolve().parents[1])
                env['PYTHONPATH'] = package_root + os.pathsep + env.get('PYTHONPATH', '')
                proc = subprocess.run([sys.executable, '-c', f'SIGNAL = {int(sig)}\nSERVER = {server!r}\n' + code],
                                      env=env, capture_output=True, text=True, timeout=15)
                output = proc.stdout + proc.stderr
                # Recent Uvicorn re-raises SIGTERM after cleanup.
                self.assertIn(proc.returncode, (0, -int(sig)), output)
                if server == 'uvicorn':
                    self.assertIn('Application shutdown complete', output)
                self.assertIn('HOOKS_OK', output)
                if proc.returncode == 0:
                    self.assertIn('SHUTDOWN_OK', output)
                for error in ('Task was destroyed', 'Traceback', 'Event loop is closed',
                              'Exception in ASGI application'):
                    self.assertNotIn(error, output)


if __name__ == '__main__':
    unittest.main()
