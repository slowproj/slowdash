# Created by Sanshiro Enomoto on 31 December 2024 #


import sys, io, logging
from sd_component import Component


class ConsoleComponent(Component):
    def __init__(self, app, project):
        super().__init__(app, project)
        
        self.console_stdin = None
        self.console_stdout = None
        self.console_outputs = []
        
        self.original_stdin = sys.stdin
        self.original_stdout = sys.stdout
        if not app.is_command and not app.is_cgi:
            self.console_stdin = io.StringIO()
            self.console_stdout = io.StringIO()
            sys.stdin = self.console_stdin
            sys.stdout = self.console_stdout
            

    def __del__(self):
        if self.console_stdin is not None:
            sys.stdin = self.original_stdin
            sys.stdout = self.original_stdout
            self.console_stdin.close()
            self.console_stdout.close()


    def process_get(self, path, opts, output):
        if len(path) > 0 and path[0] == 'console':
            if self.console_stdout is not None:
                self.console_outputs += [ line for line in self.console_stdout.getvalue().split('\n') if len(line)>0 ]
                self.console_stdout.seek(0)
                self.console_stdout.truncate(0)
                self.console_stdout.seek(0)
                if len(self.console_outputs) > 10000:
                    self.console_outputs = self.console_outputs[-10000:]
                output.write('\n'.join(self.console_outputs[-20:]).encode())
            else:
                output.write('[no console output]'.encode())
            output.flush()
            return 'text/plain'
                
        return None


    def process_post(self, path, opts, doc, output):
        if len(path) > 0 and path[0] == 'console':
            cmd = doc.decode()
            if cmd is None:
                return 400  # Bad Request
            logging.info(f'Console Input: {cmd}')

            pos = self.console_stdin.tell()
            self.console_stdin.seek(0, io.SEEK_END)
            self.console_stdin.write('%s\n' % cmd)
            self.console_stdin.seek(pos)
            return True
        
        return None
