#! /bin/env python3

from slowpy.control import ControlSystem, ScpiServer, ScpiAdapter

ControlSystem.import_control_module('DummyDevice')
device = ControlSystem().randomwalk_device()

adapter = ScpiAdapter(idn='RandomWalk')
adapter.bind_nodes([
    ('CONFIG:WALK', device.decay()),
    ('CONFIG:DECAY', device.decay()),
    ('V0', device.ch(0).setpoint()),
    ('V1', device.ch(1).setpoint()),
    ('MEAS:V0', device.ch(0)),
    ('MEAS:V1', device.ch(1)),
])



if __name__ == '__main__':
    from optparse import OptionParser
    optionparser = OptionParser()
    optionparser.add_option(
        '--port', action='store', dest='port', type='int', default=17674,
        help='port number'
    )
    (opts, args) = optionparser.parse_args()
    
    server = ScpiServer(adapter, port=opts.port)
    server.start()
