#! /usr/bin/env python3
        
from slowpy.control import ControlSystem, ScpiServer, ScpiAdapter

ControlSystem.import_control_module('DummyDevice')
device = ControlSystem().randomwalk_device()

adapter = ScpiAdapter(idn='RandomWalk')
adapter.bind_nodes([
    ('CONFIGure:WALK', device.walk().setpoint(limits=(0,None))),
    ('CONFIGure:DECAY', device.decay().setpoint(limits=(0,1))),
    ('V0', device.ch(0).setpoint()),
    ('V1', device.ch(1).setpoint()),
    ('MEASure:V0', device.ch(0).readonly()),
    ('MEASure:V1', device.ch(1).readonly()),
])


if __name__ == '__main__':
    from optparse import OptionParser
    optionparser = OptionParser()
    optionparser.add_option(
        '--port', action='store', dest='port', type='int', default=17674, help='port number'
    )
    optionparser.add_option(
        '--terminator', action='store', dest='line_terminator', type='string', default='CR',
        help='line terminator, CR or LF'
    )
    (opts, args) = optionparser.parse_args()

    server = ScpiServer(adapter, port=opts.port, line_terminator='\x0a' if opts.line_terminator=='LF' else '\x0d')
    server.start()
