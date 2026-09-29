# Created by Sanshiro Enomoto on 29 September 2026 #

        
import logging, asyncio, contextvars, sys



class MeshLogHandler(logging.Handler):
    def __init__(self, max_queue_size=1000):
        super().__init__()

        self._mesh = None
        self._worker_task = None
        self._event_loop = None
        
        self._queue = asyncio.Queue(maxsize=max_queue_size)
        self._mesh_ready = asyncio.Event()

        self._logging_suspended = contextvars.ContextVar(f'mesh_logging_suspended_{id(self)}', default=False)

        
    def emit(self, record):
        message = self._make_message(record)

        if self._event_loop is None:
            #sys.stderr.write(f'### LOG BEFOER LOOP: {message}\n')
            return
        
        if self._logging_suspended.get():
            #sys.stderr.write(f'### ERROR DURING LOGGER PUBLISH: {message}\n')
            return
        
        self._event_loop.call_soon_threadsafe(self._put_message, message)

        
    def _put_message(self, message):
        try:
            self._queue.put_nowait(message)
        except asyncio.QueueFull:
            sys.stderr.write(f'### ERROR: LOGGING QUEUE FULL\n')

        
    def _make_message(self, record):
        return {
            "timestamp": record.created,
            "level": record.levelno,
            "level_name": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process": record.process,
            "thread": record.thread,
        }

        
    async def aio_start(self, mesh):
        self._event_loop = asyncio.get_running_loop()
        self._mesh = mesh
        self._mesh_ready.set()
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._handle_log())


    async def aio_stop(self):
        self._mesh_ready.clear()
        self._mesh = None

        
    async def _handle_log(self):
        while True:
            message = await self._queue.get()
            await self._mesh_ready.wait()

            token = self._logging_suspended.set(True)
            try:
                await self._mesh.aio_publish('log', message)
            except Exception as e:
                sys.stderr.write(f'### ERROR: LOG PUBLISH: {e}\n')
                self._mesh_ready.clear()
            finally:
                self._logging_suspended.reset(token)
                self._queue.task_done()
