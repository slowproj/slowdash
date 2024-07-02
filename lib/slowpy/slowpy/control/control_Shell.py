
import subprocess, logging
from slowpy.control import ControlNode


class ShellNode(ControlNode):
    def __init__(self, command, decode=True, strip=True, **kwargs):
        self.command = command
        self.kwargs = { key:value for key,value in kwargs if key not in ['shell', 'stdout', 'capture_output'] }
        self.kwargs['shell'] = kwargs.get('shell', True)
        self.decode = decode
        self.strip = strip

        self.last_return_code = None

        
    def set(self, value):
        self.do_command(value, stdout=None)

        
    def get(self):
        return self.do_command(stdout=subprocess.PIPE)

    
    def do_command(self, *args, **kwargs):
        cmd = self.command + ''.join([ f' {arg}' for arg in args ])
        try:
            p = subprocess.run(cmd, **{**self.kwargs, **kwargs})
        except Exception as e:
            logging.error(f'ShellNode("{cmd}"): %s' % str(e))
            self.last_return_code = None
            return None
        self.last_return_code = p.returncode
        output = p.stdout

        if output is not None:
            if self.decode:
                output = output.decode()
            if self.strip:
                output = output.strip()

        return output


    @classmethod
    def _node_creator_method(cls):
        def shell(self, command, **kwargs):
            return ShellNode(command, **kwargs)

        return shell


    ## child nodes ##
    def arg(self, *args):
        return ShellArgNode(self, *args)

    
    
class ShellArgNode(ControlNode):
    def __init__(self, shell_node, *args):
        self.shell_node = shell_node
        self.args = args

        
    def set(self, value=None):
        if value is None:
            self.shell_node.do_command(*self.args)
        else:
            self.shell_node.do_command(*self.args, value)

        
    def get(self):
        return self.shell_node.do_command(*self.args)

    
    
def export():
    return [ ShellNode ]
