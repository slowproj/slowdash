"""Run with PYTHONPATH=lib/slowpy python -m unittest discover -s lib/slowpy/test -p test_mesh_logger_shutdown.py."""
import asyncio
import logging
import unittest
from unittest.mock import AsyncMock

from slowpy.mesh.logger import MeshLogHandler


class MeshLoggerShutdownTests(unittest.IsolatedAsyncioTestCase):
    async def test_stop_during_initial_delay_completes_queue_item(self):
        handler = MeshLogHandler()
        mesh = type('Mesh', (), {'aio_publish': AsyncMock()})()
        await handler.aio_start(mesh)
        handler._put_message({'logger': 'test', 'level_name': 'INFO'})
        await asyncio.sleep(0)
        await handler.aio_stop()
        await asyncio.wait_for(handler._queue.join(), 1)
        mesh.aio_publish.assert_not_awaited()
        self.assertIsNone(handler._worker_task)
        self.assertIsNone(handler._mesh)

    async def test_stop_while_publishing_and_restart(self):
        handler = MeshLogHandler()
        started = asyncio.Event()
        async def publish(*args):
            started.set()
            await asyncio.Future()
        mesh = type('Mesh', (), {'aio_publish': AsyncMock(side_effect=publish)})()
        await handler.aio_start(mesh)
        handler._is_first = False
        handler._put_message({'logger': 'test', 'level_name': 'INFO'})
        await asyncio.wait_for(started.wait(), 1)
        worker = handler._worker_task
        await handler.aio_stop()
        self.assertTrue(worker.cancelled())
        await asyncio.wait_for(handler._queue.join(), 1)
        mesh.aio_publish = AsyncMock()
        await handler.aio_start(mesh)
        handler._is_first = False
        handler._put_message({'logger': 'test', 'level_name': 'INFO'})
        await asyncio.wait_for(handler._queue.join(), 1)
        mesh.aio_publish.assert_awaited_once()
        await handler.aio_stop()
        await handler.aio_stop()

    async def test_cancellation_of_stop_caller_is_not_swallowed(self):
        handler = MeshLogHandler()
        publishing = asyncio.Event()
        cleaning_up = asyncio.Event()
        async def publish(*args):
            publishing.set()
            try:
                await asyncio.Future()
            finally:
                cleaning_up.set()
                await asyncio.Future()
        mesh = type('Mesh', (), {'aio_publish': AsyncMock(side_effect=publish)})()
        await handler.aio_start(mesh)
        handler._is_first = False
        handler._put_message({'logger': 'test', 'level_name': 'INFO'})
        await asyncio.wait_for(publishing.wait(), 1)
        stop = asyncio.create_task(handler.aio_stop())
        await asyncio.wait_for(cleaning_up.wait(), 1)
        stop.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await stop
        self.assertIsNone(handler._worker_task)
        self.assertIsNone(handler._mesh)
        await asyncio.wait_for(handler._queue.join(), 1)

    async def test_queued_emit_callback_does_not_enqueue_after_stop(self):
        handler = MeshLogHandler()
        await handler.aio_start(None)
        handler.emit(logging.LogRecord('test', logging.INFO, __file__, 1, 'test', (), None))
        await handler.aio_stop()
        await asyncio.sleep(0)
        self.assertTrue(handler._queue.empty())
        await asyncio.wait_for(handler._queue.join(), 1)


if __name__ == '__main__':
    unittest.main()
