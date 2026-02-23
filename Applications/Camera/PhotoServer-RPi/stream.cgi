#! /bin/env python3

import sys, io, threading, functools, logging
import picamera2

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = threading.Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

            
with picamera2.Picamera2() as picam2:
    config = picam2.create_video_configuration(main={
        "size": (640,480)
    })
    picam2.configure(config)

    encoder = picamera2.encoders.MJPEGEncoder()  # use hardware MJPEG encoder
    output = StreamingOutput()
    picam2.start_recording(encoder, picamera2.outputs.FileOutput(output))
    
    sys.stdout.write('Age: 0\n')
    sys.stdout.write('Cache-Control: no-cache, private\n')
    sys.stdout.write('Pragma: no-cache\n')
    sys.stdout.write('Content-Type: multipart/x-mixed-replace; boundary=FRAME\n\n')
    sys.stdout.flush()
    try:
        with output.condition:
            while True:
                output.condition.wait()
                frame = output.frame
                sys.stdout.buffer.write(b'--FRAME\r\n')
                sys.stdout.buffer.write(b'Content-Type: image/jpeg\n')
                sys.stdout.buffer.write(b'Content-Length: %d\n\n' % len(frame))
                sys.stdout.buffer.write(frame)
                sys.stdout.buffer.write(b'\r\n')
                sys.stdout.flush()
    except Exception as e:
        logging.error(str(e))
    finally:
        picam2.stop_recording()
