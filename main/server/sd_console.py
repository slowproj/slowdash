# Created by Sanshiro Enomoto on 31 December 2024 #


import sys, io, logging

import slowapi
from sd_component import Component


class ConsoleComponent(Component):
    def __init__(self, app, project):
        super().__init__(app, project)
        
        self.console_stdin = None
        self.console_stdout = None
        self.console_outputs = []
        self.max_lines = 10000
        
        if not app.is_command and not app.is_cgi:
            self.console_stdin = io.StringIO()
            self.console_stdout = io.StringIO()
            sys.stdin = self.console_stdin
            sys.stdout = self.console_stdout
            

    def __del__(self):
        if self.console_stdin is not None:
            sys.stdin = sys.__stdin__
            sys.stdout = sys.__stdout__
            self.console_stdin.close()
            self.console_stdout.close()

            
    def public_config(self):
        return { 'console': {
            'enabled': self.console_stdin is not None,
            'max_lines': self.max_lines,
        }}

    
    @slowapi.get('/console')
    def read(self, nlines:int=20):
        if self.console_stdout is None:
            return '[no console output]'

        self.console_outputs += [ line for line in self.console_stdout.getvalue().split('\n') if len(line)>0 ]
        self.console_stdout.seek(0)
        self.console_stdout.truncate(0)
        self.console_stdout.seek(0)
        
        if len(self.console_outputs) > self.max_lines:
            self.console_outputs = self.console_outputs[-max_lines:]
                
        return '\n'.join(self.console_outputs[-nlines:])


    @slowapi.post('/console')
    def write(self, body:bytes):
        cmd = body.decode()
        logging.info(f'Console Input: {cmd}')
        
        pos = self.console_stdin.tell()
        self.console_stdin.seek(0, io.SEEK_END)
        self.console_stdin.write('%s\n' % cmd)
        self.console_stdin.seek(pos)
        
        return slowapi.Response(201)
