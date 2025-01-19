# Created by Sanshiro Enomoto on 18 January 2025 #

        
import sys, signal
from wsgiref.simple_server import make_server, WSGIRequestHandler


class RequestHandler(WSGIRequestHandler):
    def log_message(self, fmt, *args):
        pass


def signal_handler(signum, frame):
    raise KeyboardInterrupt

    
def run(app, port):
    sys.stderr.write('Listening at port %d\n' % port)

    try:
        signal.signal(signal.SIGTERM, signal_handler)
        with make_server('', port, app, handler_class=RequestHandler) as server:
            server.serve_forever()
    except KeyboardInterrupt:
        pass
    
    sys.stderr.write('Terminated\n')    
