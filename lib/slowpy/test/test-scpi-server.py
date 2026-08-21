
from slowpy.control import RandomWalkDevice
device = RandomWalkDevice(n=2)



from slowpy.control import ScpiServer
server = ScpiServer()


@server.scpi('*IDN?')
def get_idn():
    return 'RandomWalk'


@server.scpi('V0')
def set_V0(value:float):
    device.write(0, value)


@server.scpi('V1')
def set_V1(value:float):
    device.write(1, value)


@server.scpi('MEASure:V0?')
def get_V0():
    return device.read(0)


@server.scpi('MEASure:V1?')
def get_V1():
    return device.read(1)


        
if __name__ == '__main__':
    from optparse import OptionParser
    optionparser = OptionParser()
    optionparser.add_option(
        '--port', action='store', dest='port', type='int', default=5025,
        help='port number'
    )
    (opts, args) = optionparser.parse_args()

    server.start(port=opts.port)
