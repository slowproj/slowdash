#! /usr/bin/env python3
# Created by Sanshiro Enomoto on 3 Sep 2021 #


import sys, os, logging
from argparse import ArgumentParser

from sd_app import App
from sd_webui import WebUI


if __name__ == '__main__':
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
        action='store', dest='loglevel', default='info', choices=['debug', 'info', 'warning', 'error'],
        help='logging level'
    )
    parser.add_argument(
        '-i', '--indent',
        action='store', dest='indent', type=int, default=-1,
        help='JSON output indenting (default: no indent)'
    )
    args = parser.parse_args()

    if args.COMMAND is None and args.port <= 0:
        parser.print_help()
        sys.exit(-1)

    loglevel = getattr(logging, args.loglevel.upper(), None)
    if type(loglevel) != int:
        loglevel = logging.INFO
    logging.basicConfig(
        level=loglevel,
        format='%(asctime)s %(levelname)s: %(message)s', 
        datefmt='%y-%m-%d %H:%M:%S'
    )
    logging.basicConfig(level=loglevel)
        
    app = App(
        project_dir = args.project_dir,
        project_file = args.project_file,
        is_cgi = False,
        is_command = (args.port<=0)
    )
    if app.project.config is None:
        sys.exit(-1)

    webui = WebUI(app)
    if args.port <= 0:
        if args.indent >= 0:
            webui.json_kwargs['indent'] = args.indent
        result = webui.process_get_request(args.COMMAND)
        result.write_to(sys.stdout.buffer)
        sys.stdout.write('\n')
        
    else:
        import sd_server
        sd_server.start(
            webui,
            port = args.port, 
            web_path = os.path.join(os.path.dirname(os.path.abspath(os.path.join(__file__, os.pardir))), 'web'),
            index_file = 'slowhome.html' if webui.app.project is not None else 'welcome.html',
        )
        
    app.terminate()
