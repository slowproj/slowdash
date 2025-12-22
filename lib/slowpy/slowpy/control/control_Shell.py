# Created by Sanshiro Enomoto on 29 June 2024 #


import subprocess
import slowpy.control as spc


class ShellNode(spc.ControlNode):
    def __init__(self, command, decode=True, strip=True, **kwargs):
        self.command = command
        self.kwargs = { key:value for key,value in kwargs if key not in ['shell', 'stdout', 'capture_output'] }
        self.kwargs['shell'] = kwargs.get('shell', True)
        self.decode = decode
        self.strip = strip

        
    def set(self, value):
        self.do_command(value, stdout=None)

        
    def get(self):
        return self.do_command(stdout=subprocess.PIPE)

    
    def do_command(self, *args, **kwargs):
        cmd = self.command + ''.join([ f' {arg}' for arg in args ])
        try:
            p = subprocess.run(cmd, **{**self.kwargs, **kwargs})
        except Exception as e:
            raise spc.ControlException(f'ShellNode("{cmd}"): %s' % str(e))

        output = p.stdout
        if output is None:
            return ''
        
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
    def value(self):  # for set_point() and ramping() grand-child nodes
        return ShellValueNode(self)

    
    def arg(self, *args):
        return ShellArgNode(self, *args)

    
    
class ShellArgNode(spc.ControlNode):
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

    
    ## child nodes ##
    def value(self):  # for set_point() and ramping() grand-child nodes
        return ShellValueNode(self)

    
    
class ShellValueNode(spc.ControlVariableNode):
    def __init__(self, parent_node):
        self.parent_node = parent_node
        
    
    def set(self, value):
        return self.parent_node.set(value)
            
    
    def get(self):
        return self.parent_node.get()
