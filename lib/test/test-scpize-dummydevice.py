#! /bin/env python3

from slowpy.control import ScpiServer, ScpiAdapter, RandomWalkDevice


class RandomWalkScpiDevice(ScpiAdapter):
    def __init__(self):
        super().__init__(idn='RandomWalk')
        self.device = RandomWalkDevice(n=2)


    def do_command(self, cmd_path, params):
        '''
        parameters:
          cmd_path: array of strings, SCPI command splitted by ':'
          params: array of strings, SCPI command parameters splited by ','
        return value: reply text (even if empty) or None if command is not recognized
        '''
        
        # Implemented Commands: "V0 Value" "V1 Value" "MEASure:V0?" "MEASure:V1?"
        # Common SCPI commands, such as "*IDN?", are implemented in the parent ScpiAdapter class
        if len(params) == 1 and cmd_path[0].startswith('V'):
            try:
                if cmd_path[0] == 'V0':
                    self.device.write(0, float(params[0]))
                elif cmd_path[0] == 'V1':
                    self.device.write(1, float(params[0]))
                else:
                    self.push_error(f'invalid command {cmd_path[0]}')
            except:
                self.push_error(f'bad parameter value: {params[0]}')
            return ''
            
        elif len(cmd_path) == 2 and cmd_path[0].startswith('MEAS'):
            if cmd_path[1] == 'V0?':
                return self.device.read(0)
            elif cmd_path[1] == 'V1?':
                return self.device.read(1)
            else:
                self.push_error(f'invalid command {cmd_path[0]}')
            return ''
            
        return None

    
        
if __name__ == '__main__':
    from optparse import OptionParser
    optionparser = OptionParser()
    optionparser.add_option(
        '--port', action='store', dest='port', type='int', default=17674,
        help='port number'
    )
    (opts, args) = optionparser.parse_args()

    device = RandomWalkScpiDevice()
    server = ScpiServer(device, port=opts.port)
    server.start()
