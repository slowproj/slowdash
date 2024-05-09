#! /bin/env python3

import io, threading, functools, logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

PAGE="""\
<html>
<head>
<title>Raspberry Pi - MJPEG streaming</title>
</head>
<body>
<h1>Raspberry Pi - MJPEG Streaming</h1>
<img src="stream.mjpg" width="640" height="480">
</body>
</html>
"""


class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = threading.Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

    
class StreamingHandler(BaseHTTPRequestHandler):
    def __init__(self, streaming_output, *args, **kwargs):
        self.streaming_output = streaming_output
        BaseHTTPRequestHandler.__init__(self, *args, **kwargs)
        
    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                with self.streaming_output.condition:
                    while True:
                        self.streaming_output.condition.wait()
                        frame = self.streaming_output.frame
                        self.wfile.write(b'--FRAME\r\n')
                        self.send_header('Content-Type', 'image/jpeg')
                        self.send_header('Content-Length', len(frame))
                        self.end_headers()
                        self.wfile.write(frame)
                        self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning('Removed streaming client %s: %s', self.client_address, str(e))
                    
        else:
            self.send_error(404)
            self.end_headers()


            
class StreamingServer(ThreadingMixIn, HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


    
import picamera2

with picamera2.Picamera2() as picam2:
    config = picam2.create_video_configuration(main={
        "size": (640,480)
    })
    picam2.configure(config)

    #encoder = picamera2.encoders.JpegEncoder()
    encoder = picamera2.encoders.MJPEGEncoder()  # use hardware MJPEG encoder
    output = StreamingOutput()
    
    picam2.start_recording(encoder, picamera2.outputs.FileOutput(output))
    try:
        address = ('', 8000)
        server = StreamingServer(address, functools.partial(StreamingHandler, output))
        server.serve_forever()
    finally:
        picam2.stop_recording()
