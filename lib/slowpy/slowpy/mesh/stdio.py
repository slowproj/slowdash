# Created by Sanshiro Enomoto on 13 August 2025 #

import sys, time, queue, asyncio, threading, builtins, logging
from slowpy.control import control_system as ctrl
from .mesh import Mesh



class _MeshStdout:
    """Instance of this class will replace sys.stdout or sys.stderr
    - print() is overriden in MeshStdioBridge separately, so that the content is not divided into multiple packets
    """
    
    def __init__(self, router, stream_name, original):
        self._router = router
        self._stream_name = stream_name
        self._original = original
        self.encoding = getattr(original, 'encoding', None)
        self.errors = getattr(original, 'errors', None)


    def write(self, text):
        if not isinstance(text, str):
            text = str(text)

        self._router.write(self._stream_name, text)
        
        return len(text)

    
    def flush(self):
        try:
            self._original.flush()
        except Exception:
            pass

        
    def isatty(self):
        try:
            return self._original.isatty()
        except Exception:
            return False

    
    def __getattr__(self, name):
        return getattr(self._original, name)



class _MeshStdioRouter:
    """Process-wide stdio router for all MeshStdio instances in the process.
    - ThreadID is used to distinguish multiple MeshStdios
    """

    def __init__(self):
        self._threading_bridges = {}

        self._orig_stdout = None
        self._orig_stderr = None
        self._orig_print = None
        self._orig_input = None

        self._stdin_thread = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        self._installed = False

        self._thread_warning_shown = False


    def install_once(self):
        with self._lock:
            if self._installed:
                return

            self._orig_stdout = sys.stdout
            self._orig_stderr = sys.stderr
            self._orig_print = builtins.print
            self._orig_input = builtins.input

            sys.stdout = _MeshStdout(self, 'stdout', self._orig_stdout)
            sys.stderr = _MeshStdout(self, 'stderr', self._orig_stderr)
            builtins.print = self.print
            builtins.input = self.input
        
            self._installed = True
            self._start_stdin_thread()


    def register_current_thread(self, bridge):
        self.install_once()
        with self._lock:
            self._threading_bridges[threading.get_ident()] = bridge


    def unregister_current_thread(self, bridge):
        with self._lock:
            thread_id = threading.get_ident()
            if self._threading_bridges.get(thread_id) is bridge:
                del self._threading_bridges[thread_id]


    def _current_bridge(self):
        with self._lock:
            return self._threading_bridges.get(threading.get_ident())


    def _registered_bridges(self):
        with self._lock:
            return set(self._threading_bridges.values())


    def write(self, stream, text):
        original = self._orig_stderr if stream == 'stderr' else self._orig_stdout
        if original is None:
            original = sys.__stderr__ if stream == 'stderr' else sys.__stdout__

        try:
            original.write(text)
        except Exception:
            pass

        bridge = self._current_bridge()
        if bridge is None:
            # if a user creates a new thread, the thread_id becomes unknown...
            if not self._thread_warning_shown:
                logging.warning(
                    'MeshStdio: stdout from unknown thread. ' +
                    'Call MeshStdio.attach_remote_stdio_to_current_thread() in a new thread, AND ' +
                    'call MeshStdio.detach_remote_stdio_from_current_thread() before terminating the thread'
                )
                self._thread_warning_shown = True
        else:
            bridge.put_output(stream, text)


    def print(self, *values, sep=' ', end='\n', file=None, flush=False):
        bridge = self._current_bridge()
        if bridge is None:
            return self._orig_print(*values, sep=sep, end=end, file=file, flush=flush)

        if file is None or file is sys.stdout:
            stream_name = 'stdout'
            original = self._orig_stdout
        elif file is sys.stderr:
            stream_name = 'stderr'
            original = self._orig_stderr
        else:
            return self._orig_print(*values, sep=sep, end=end, file=file, flush=flush)

        text = sep.join(str(value) for value in values) + end

        try:
            original.write(text)
            if flush:
                original.flush()
        except Exception:
            pass

        bridge.put_output(stream_name, text)


    def input(self, prompt=''):
        bridge = self._current_bridge()
        if bridge is None:
            return self._orig_input(prompt)

        return bridge.input(prompt)
        
        
    def _start_stdin_thread(self):
        stdin = sys.__stdin__
        if stdin is None or getattr(stdin, 'closed', False):
            return

        def read_stdin():
            while not ctrl.is_stop_requested() and not self._stop_event.is_set():
                try:
                    line = stdin.readline()
                except Exception:
                    break
                if line == '':
                    break

                bridges = self._registered_bridges()
                if len(bridges) == 1:
                    bridges.pop().put_input(line, source='local')
                else:
                    # Local input() to multiple MeshStdio bridges; input will not be delivered due to ambiguity.
                    # Inputs from PubSub are still delivered even with multiple MeshStdio bridges.
                    logging.warning('MeshStdio: local input() to multiple MeshStdio bridges: input is discarded')

        self._stdin_thread = threading.Thread(target=read_stdin, daemon=True)
        self._stdin_thread.start()

        
    
class _MeshStdioBridge:
    def __init__(self, mesh:Mesh, *, max_input_queue:int=1000, max_output_queue:int=1000):
        self._mesh = mesh
        self._max_input_queue = max_input_queue
        self._max_output_queue = max_output_queue
        
        self._separate_stderr = False

        self._input_queue = queue.Queue(maxsize=max_input_queue)
        self._output_queue = queue.Queue(maxsize=max_output_queue)
        self._stop_event = threading.Event()
        self._publisher_task = None


    @property
    def stdin_topics(self):
        topics = []
        
        mesh_id = self._mesh.mesh_id
        if mesh_id:
            topics.append(f'sd.task.stdin.{mesh_id}')
            
        return topics


    @property
    def stdout_topics(self):
        mesh_id = self._mesh.mesh_id
        if mesh_id:
            return [ f'sd.task.stdout.{mesh_id}' ]
        else:
            return []


    @property
    def stderr_topics(self):
        if not self._separate_stderr:
            return self.stdout_topics
        
        mesh_id = self._mesh.mesh_id
        if mesh_id:
            return [ f'sd.task.stderr.{mesh_id}' ]
        else:
            return []

        
    def close(self):
        self._stop_event.set()
        

    async def aio_start(self):
        for topic in self.stdin_topics:
            await self._mesh.aio_subscribe(topic, self._handle_stdin_message)
        self._publisher_task = asyncio.create_task(self._publish_output())


    async def aio_stop(self):
        if self._publisher_task is not None:
            self._publisher_task.cancel()
            try:
                await self._publisher_task
            except Exception:
                pass
            except:
                pass

            self._publisher_task = None


    def put_output(self, stream, text):
        if len(text) == 0:
            return

        record = {
            'mesh_id': self._mesh.mesh_id,
            'timestamp': time.time(),
            'stream': stream,
            'kind': 'text',
            'text': text,
        }
        try:
            self._output_queue.put_nowait(record)
        except queue.Full:
            logging.warning(f'MeshStdio stdout/stderr queue full; dropping output')


    def input(self, prompt=''):
        if prompt:
            sys.stdout.write(str(prompt))
            sys.stdout.flush()
            
        while not ctrl.is_stop_requested() and not self._stop_event.is_set():
            try:
                item = self._input_queue.get(timeout=0.1)
                return item.get('line', '')
            except queue.Empty:
                pass

        logging.debug(f'MeshStdio: input cancelled')
        return None

    
    def put_input(self, line, *, source, headers=None):
        if isinstance(line, bytes):
            line = line.decode(errors='replace')
        elif not isinstance(line, str):
            line = str(line)
        line = line.removesuffix('\n').removesuffix('\r')

        item = {
            'source': source,
            'line': line,
            'timestamp': time.time(),
            'headers': headers
        }

        try:
            self._input_queue.put_nowait(item)
        except queue.Full:
            logging.warning('MeshStdio stdin queue is fill; dropping input')


    def _handle_stdin_message(self, headers, data):
        line = data
        if isinstance(data, dict):
            line = data.get('line', data.get('text', ''))
            
        self.put_input(line, source='mesh', headers=headers)


    async def _publish_output(self):
        while not ctrl.is_stop_requested() and not self._stop_event.is_set():
            try:
                record = self._output_queue.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.05)
                continue
            
            topics = self.stderr_topics if record.get('stream') == 'stderr' else self.stdout_topics
            headers = {
                'mesh_id': self._mesh.mesh_id,
                'stream': record.get('stream')
            }
            
            for topic in topics:
                try:
                    await self._mesh.aio_publish(topic, record, headers=headers)
                except Exception as e:
                    logging.warning(f'MeshStdio: publish failed: {e}')


                    
class MeshStdio:
    _stdio_router = _MeshStdioRouter()

    def __init__(self, mesh:Mesh):
        self._mesh = mesh
        self._stdio_bridge = None

        
    @property
    def spec(self):
        return {
            'stdin': self._stdio_bridge.stdin_topics if self._stdio_bridge is not None else [],
            'stdout': self._stdio_bridge.stdout_topics if self._stdio_bridge is not None else [],
            'stderr': self._stdio_bridge.stderr_topics if self._stdio_bridge is not None else []
        }

    
    async def aio_start(self):
        self._stdio_bridge = _MeshStdioBridge(self._mesh)
        self.attach_current_thread()
        await self._stdio_bridge.aio_start()

            
    async def aio_stop(self):
        try:
            self.detach_current_thread()
            self._stdio_bridge.close()
            await self._stdio_bridge.aio_stop()
        except Exception:
            pass
        
            
    def attach_current_thread(self):
        MeshStdio._stdio_router.register_current_thread(self._stdio_bridge)
    
    
    def detach_current_thread(self):
        MeshStdio._stdio_router.unregister_current_thread(self._stdio_bridge)
