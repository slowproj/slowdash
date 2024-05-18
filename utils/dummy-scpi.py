#! /usr/bin/env python3
        
import slowpy


if __name__ == '__main__':
    from optparse import OptionParser
    optionparser = OptionParser()
    optionparser.add_option(
        '--port', action='store', dest='port', type='int', default=17674,
        help='port number'
    )
    optionparser.add_option(
        '--terminator', action='store', dest='line_terminator', type='string', default='CR',
        help='line terminator, CR or LF'
    )
    (options, args) = optionparser.parse_args()
    
    device = slowpy.DummyScpiDevice(line_terminator='\x0a' if options.line_terminator=='LF' else '\x0d')
    server = slowpy.SerialDeviceEthernetServer(device, port=options.port)
    server.start()
