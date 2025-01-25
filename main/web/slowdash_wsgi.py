# Created by Sanshiro Enomoto on 12 Dec 2024 #

import sys, os, atexit, logging
logging.basicConfig(level=logging.INFO)

from slowdash_cgi_config import sys_dir, project_dir
sys.path.insert(0, os.path.join(sys_dir, 'main', 'server'))


# The CGI mode disables launching task processes (user module and slow-task).
# CGI/WSGI might create multiple SlowDash processes, but staring the tasks multiple times might cause a problem.
# If WSGI is configured to start only one SlowDash process, the CGI mode can be disabled (e.g., enable SlowDash tasks).
is_cgi = True


# The "is_cgi" variable might be modified after this module is loaded (by CGI that imports this module etc.),
# so we cannot create a "application" object here. Instead, we create a "application" function and initialze App in it.
from slowdash import App
from slowdash.slowapi import WSGI
app = None
wsgi_app = None

def application(environ, start_response):
    global app, project_dir, is_cgi
    if app is None:
        app = App(project_dir=project_dir, is_cgi=is_cgi)
        wsgi_app = WSGI(app)
        logging.info('created a SlowDash instance')

    return wsgi_app(environ, start_response)


def terminate():
    global app
    if app is not None:
        app.terminate()
        
atexit.register(terminate)
