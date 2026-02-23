#! /usr/bin/python3


''' 
## To enable CGI from user-dir:
- Configure Apache:
  $ cd /etc/apache2/mods-enabled
  $ sudo ln -s ../mods-available/userdir.conf .
  $ sudo ln -s ../mods-available/userdir.load .
  $ sudo ln -s ../mods-available/cgi.load .

- Edit /etc/apache2/mods-enabled/userdir.conf
  AllowOverride: -> ExecCGI

- Edit /home/USER/public_html/.htaccess
  Options +ExecCGI
  AddType application/x-httpd-cgi .cgi
  AddHandler cgi-script .cgi

## To use the camera from CGI:
  $ sudo adduser www-data video
'''


import sys, time, io, traceback
import picamera2

def take_photo(opts):
    data = io.BytesIO()
    try:
        picam2 = picamera2.Picamera2()
        config = picam2.create_still_configuration()        
        picam2.configure(config)
        picam2.start(show_preview=False)
        time.sleep(1)
        picam2.capture_file(data, format='jpeg')        
    except Exception as e:
        sys.stdout.write('Content-Type: text/plain\n\n')
        sys.stdout.write('ERROR: %s\n\n' % str(e))
        sys.stdout.write(traceback.format_exc())
        sys.stdout.write('\n')
        return
    
    size = data.getbuffer().nbytes
    if size == 0:
        sys.stdout.write('Content-type: text/plain\n\n')
        sys.stdout.write('ERROR: empty frame\n')
        sys.stdout.flush()
        return
        
    sys.stdout.write('Content-type: image/jpeg\n')
    sys.stdout.write('Content-length: %d\n' % size)
    sys.stdout.write('\n')
    sys.stdout.flush()
    sys.stdout.buffer.write(data.getvalue())
    sys.stdout.buffer.flush()

    
    
take_photo({})
