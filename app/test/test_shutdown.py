"""Regression test: python -m unittest discover -s app/test -p test_shutdown.py."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import unittest


@unittest.skipUnless(os.name == 'posix', 'requires POSIX signals')
class SlowDashShutdownTests(unittest.TestCase):
    def test_shutdown_with_browser_stream_and_internal_mesh(self):
        code = r'''
import asyncio, logging, os, signal, socket, tempfile
from pathlib import Path
import slowlette
from slowdash import App
from sd_slowmq import SlowMQComponent
from sd_webmesh import WebMeshComponent

logging.basicConfig(level=logging.INFO)
sock = socket.socket()
sock.bind(('127.0.0.1', 0))
port = sock.getsockname()[1]
clients = []
original_cancel_all = asyncio.runners._cancel_all_tasks

def check_tasks(loop):
    original_cancel_all(loop)
    assert not asyncio.all_tasks(loop), asyncio.all_tasks(loop)
    print('NO_PENDING_TASKS', flush=True)
asyncio.runners._cancel_all_tasks = check_tasks

async def browser():
    reader, writer = await asyncio.open_connection('127.0.0.1', port)
    writer.write(b'GET /event/webmesh/attach HTTP/1.1\r\nHost: localhost\r\n'
                 b'Accept: text/event-stream\r\nConnection: close\r\n\r\n')
    await writer.drain()
    await reader.readuntil(b'event: register')
    # Make disconnected subscribers eligible to reconnect immediately.
    for component in app.slowlette.subapps:
        mesh = getattr(component, '_mesh', None) or getattr(component, 'mesh', None)
        if mesh is not None:
            mesh._pubsub.retry_wait = 0
    broker = next(c for c in app.slowlette.subapps if isinstance(c, SlowMQComponent))
    assert broker._clients, 'test requires live SlowMQ connections'
    print('BROWSER_AND_MESH_CONNECTED', flush=True)
    os.kill(os.getpid(), SIGNAL)
    await reader.read()
    writer.close()
    await writer.wait_closed()
    print('BROWSER_CLOSED', flush=True)

class Check(slowlette.App):
    @slowlette.on_event('post_startup')
    async def ready(self):
        clients.append(asyncio.create_task(browser()))
    @slowlette.on_event('post_shutdown')
    async def finished(self):
        await asyncio.gather(*clients)
        webmesh = next(c for c in app.slowlette.subapps if isinstance(c, WebMeshComponent))
        assert not webmesh._client_stop_table
        assert not webmesh._client_queue_table
        print('SHUTDOWN_COMPLETE', flush=True)

with tempfile.TemporaryDirectory() as project:
    Path(project, 'SlowdashProject.yaml').write_text(
        f'slowdash_project:\n  name: ShutdownTest\n  mesh:\n    url: slowmq://127.0.0.1:{port}\n')
    app = App(project_dir=project, port=port)
    app.slowlette.include(Check())
    app.run(port=port, fd=sock.fileno(), ws='websockets-sansio')
'''
        root = Path(__file__).resolve().parents[2]
        env = dict(os.environ)
        env['PYTHONPATH'] = os.pathsep.join(str(root / path) for path in (
            'lib/slowlette', 'lib/slowpy', 'app/server'))
        for sig in (signal.SIGINT, signal.SIGTERM):
            with self.subTest(signal=sig.name):
                proc = subprocess.run([sys.executable, '-c', f'SIGNAL = {int(sig)}\n' + code],
                                      env=env, capture_output=True, text=True, timeout=10)
                output = proc.stdout + proc.stderr
                self.assertIn(proc.returncode, (0, -int(sig)), output)
                for marker in ('BROWSER_AND_MESH_CONNECTED', 'BROWSER_CLOSED', 'SHUTDOWN_COMPLETE'):
                    self.assertIn(marker, output)
                if proc.returncode == 0:
                    self.assertIn('NO_PENDING_TASKS', output)
                for error in ('AsyncSlowMQ Error', 'Task was destroyed', 'Traceback',
                              'Event loop is closed', 'timeout graceful shutdown exceeded'):
                    self.assertNotIn(error, output)


if __name__ == '__main__':
    unittest.main()
