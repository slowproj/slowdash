# Created by Sanshiro Enomoto on 31 December 2024 #


import sys, io, asyncio, logging

import slowapi
from sd_component import Component



class AwaitableStringIO(io.StringIO):
    def __init__(self, async_event_loop):
        super().__init__()
        self.async_event_loop = async_event_loop
        self._condition = asyncio.Condition()

        
    async def wait_for_write(self):
        async with self._condition:
            await self._condition.wait()

            
    def write(self, s):
        # this might be called in a different thread from the async event loop
        result = super().write(s)
        asyncio.run_coroutine_threadsafe(self._schedule_notification(), self.async_event_loop)
        return result

            
    async def _schedule_notification(self):
        asyncio.create_task(self._notify_write())

            
    async def _notify_write(self):
        async with self._condition:
            self._condition.notify_all()



class ConsoleComponent(Component):
    def __init__(self, app, project):
        super().__init__(app, project)
        
        self.enabled = not app.is_command and not app.is_cgi
        self.revision = 1
        
        self.console_stdin = None
        self.console_stdout = None
        self.console_awaitable_stdout = None
        self.console_outputs = []
        self.max_lines = 10000

        if self.enabled:
            self.console_stdin = io.StringIO()
            sys.stdin = self.console_stdin
            self.console_stdout = io.StringIO()
            sys.stdout = self.console_stdout

        
    def build(self):
        # call build() after the event loop is started
        if not self.enabled:
            return

        self.console_awaitable_stdout = AwaitableStringIO(asyncio.get_event_loop())
        sys.stdout = self.console_awaitable_stdout
        
        if self.console_stdout is not None:
            output = self.console_stdout.getvalue()
            self.console_outputs += [ line for line in output.split('\n') if len(line)>0 ]
            self.console_stdout.close()

        self.console_stdout = self.console_awaitable_stdout
        

    def terminate(self):
        if self.console_stdin is not None:
            sys.stdin = sys.__stdin__
            self.console_stdin.close()
        if self.console_stdout is not None:
            sys.stdout = sys.__stdout__
            self.console_stdout.close()

            
    def public_config(self):
        return { 'console': {
            'enabled': self.console_stdin is not None,
            'max_lines': self.max_lines,
        }}

    
    @slowapi.get('/console')
    async def read(self, request:slowapi.Request, nlines:int=20, since:int=0):
        if not self.enabled:
            return {
                'revision': 0,
                'text': '[console not enabled]'
            }

        if request.is_async:
            if  self.console_awaitable_stdout is None:
                # AwaitableStringIO cannot be used with WSGI, as there is no contineous event loop
                self.build()

            if (self.revision <= since) and (self.console_stdout.tell() == 0):
                await self.console_stdout.wait_for_write()
                await asyncio.sleep(0.2)
            
        if self.console_stdout.tell() > 0:
            output = self.console_stdout.getvalue()
            self.console_stdout.seek(0)
            self.console_stdout.truncate(0)
            self.console_stdout.seek(0)
            
            self.console_outputs += [ line for line in output.split('\n') if len(line)>0 ]
            if len(self.console_outputs) > self.max_lines:
                self.console_outputs = self.console_outputs[-max_lines:]
            self.revision += 1

        if len(self.console_outputs) == 0:
            return {
                'revision': self.revision,
                'text': '[no console output]'
            }
        
        return {
            'revision': self.revision,
            'text': '\n'.join(self.console_outputs[-nlines:])
        }


    @slowapi.post('/console')
    def write(self, body:bytes):
        cmd = body.decode()
        logging.info(f'Console Input: {cmd}')
        
        pos = self.console_stdin.tell()
        self.console_stdin.seek(0, io.SEEK_END)
        self.console_stdin.write('%s\n' % cmd)
        self.console_stdin.seek(pos)
        
        return slowapi.Response(201)
