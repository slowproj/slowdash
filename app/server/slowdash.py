#! /usr/bin/env python3
# Created by Sanshiro Enomoto on 3 Sep 2021 #
# Restructured to use SlowAPI by Sanshiro Enomoto on 12 January 2025 #


import sys, os, asyncio, logging
import slowapi

from sd_component import Component
from sd_project import Project
from sd_config import ConfigComponent
from sd_console import ConsoleComponent
from sd_datasource import DataSourceComponent
from sd_export import ExportComponent
from sd_usermodule import UserModuleComponent
from sd_taskmodule import TaskModuleComponent
from sd_misc_api import MiscApiComponent



class App(slowapi.App):
    def __init__(self, project_dir=None, project_file=None, is_cgi=False, is_command=False):
        super().__init__()

        self.is_cgi = is_cgi
        self.is_command = is_command
        
        if project_dir is not None:
            project_dir = os.path.abspath(os.path.join(os.getcwd(), project_dir))
        self.project = Project(project_dir, project_file)
        self.project_dir = self.project.project_dir

        # Execution Environment
        if self.project.config is None:
            return
        
        if self.project.project_dir is not None:
            try:
                os.chdir(self.project.project_dir)
            except Exception as e:
                logging.error('unable to move to project dir "%s": %s' % (self.project.project_dir, str(e)))            
                self.project.project_dir = None
        if self.project.sys_dir is not None:
            sys.path.insert(1, os.path.join(self.project.sys_dir, 'app', 'plugin'))
        if self.project.project_dir is not None:
            sys.path.insert(1, self.project.project_dir)
            sys.path.insert(1, os.path.join(self.project.project_dir, 'config'))
            
        # API Components: see slowapi.App for the mechanism
        self.slowapi.include(ConsoleComponent(self, self.project))   # this must be the first
        self.slowapi.include(ConfigComponent(self, self.project))
        self.slowapi.include(DataSourceComponent(self, self.project))
        self.slowapi.include(ExportComponent(self, self.project))
        self.slowapi.include(UserModuleComponent(self, self.project))
        self.slowapi.include(TaskModuleComponent(self, self.project))
        self.slowapi.include(MiscApiComponent(self, self.project))

        
    def terminate(self):
        """graceful terminate
          - used by components that have a thread (usermodule/taskmodule), to send a stop request etc.
        """
        for component in reversed([ app for app in self.slowapi ]):
            if isinstance(component, Component):
                component.terminate()
        logging.info('SlowDash has been terminated gracefully')



if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser(usage = '\n'
        + '  Web-Server Mode:      %(prog)s [Options] --port=PORT\n'
        + '  Command-line Mode:    %(prog)s [Options] COMMAND'
    )
    parser.add_argument(
        'COMMAND', nargs='?',
        help='API query string. Ex) "config", "channels", "data/CHANNELS?length=LENGTH"'
    )
    parser.add_argument(
        '-p', '--port',
        action='store', dest='port', type=int, default=0,
        help='port number for web connection; command-line mode without this option'
    )
    parser.add_argument(
        '--project-dir',
        action='store', dest='project_dir', default=None,
        help='project directory (default: current dir if not specified by SLOWDASH_PROJECT environmental variable)'
    )
    parser.add_argument(
        '--project-file',
        action='store', dest='project_file', default=None,
        help='project file (default: SlowdashProject.yaml file at the project directory)'
    )
    parser.add_argument(
        '--logging',
        action='store', dest='loglevel', default='default', choices=['default', 'debug', 'info', 'warning', 'error'],
        help='logging level'
    )
    parser.add_argument(
        '--wsgi',
        action='store_true', dest='wsgi', default=False, 
        help='use WSGI (otherwise ASGI)'
    )
    parser.add_argument(
        '-i', '--indent',
        action='store', dest='indent', type=int, default=None,
        help='JSON output indenting (default: no indent)'
    )
    args = parser.parse_args()

    if args.COMMAND is None and args.port <= 0:
        parser.print_help()
        sys.exit(-1)

    loglevel_name = args.loglevel.upper()
    if loglevel_name == 'DEFAULT':
        if args.port <= 0:
            loglevel = logging.WARNING
        else:
            loglevel = logging.INFO
    else:
        loglevel = getattr(logging, loglevel_name, None)
    if type(loglevel) != int:
        loglevel = logging.WARNING
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(
        level=loglevel,
        format='%(asctime)s %(levelname)s: %(filename)s %(funcName)s():   %(message)s', 
        datefmt='%y-%m-%d %H:%M:%S'
    )
    
    app = App(
        project_dir = args.project_dir,
        project_file = args.project_file,
        is_cgi = False,
        is_command = (args.port<=0),
    )
    if app.project.config is None:
        sys.exit(-1)

    if args.port <= 0:
        # command-line mode
        async def main():
            json_opts = { 'indent': args.indent }
            response = await app.slowapi(args.COMMAND)
            sys.stdout.write(response.get_content(json_opts).decode())
            sys.stdout.write('\n')
        asyncio.run(main())
        
    else:
        # web-server mode: append Authentication and FileServer
        if app.project.auth_list is not None:
            app.slowapi.add_middleware(slowapi.BasicAuthentication(auth_list=app.project.auth_list))
        app.slowapi.add_middleware(slowapi.FileServer(
            filedir = os.path.join(app.project.sys_dir, 'app', 'site'),
            index_file = 'slowhome.html' if app.project is not None else 'welcome.html',
            exclude='/api',
            drop_exclude_prefix=True
        ))

        if args.wsgi:
            slowapi.WSGI(app, slowapi.serve_wsgi_ref).run(port=args.port, host='0.0.0.0', log_level=logging.WARNING)
        else:
            app.run(port=args.port, host='0.0.0.0', log_level=logging.WARNING)
        
    app.terminate()
