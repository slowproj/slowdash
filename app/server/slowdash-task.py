# Created by Sanshiro Enomoto on 26 June 2026 #

import os, re, argparse, logging
from slowpy.mesh import RetainerAutocide
from sd_task import load_task_module


def main(argv=None):
    parser = argparse.ArgumentParser(description = 'Run a Python script as a SlowTask')
    parser.add_argument('script', help='user task script to load')
    parser.add_argument('--name', help='task name; defauts to the script filename')
    parser.add_argument('--slowdash-url', help='SlowDash URL, e.g., http://localhost:18881')
    parser.add_argument(
        '--logging',
        action='store', dest='loglevel', default='default', choices=['default', 'debug', 'info', 'warning', 'error'],
        help='logging level'
    )
    parser.add_argument('script_args', nargs=argparse.REMAINDER, help='arguments passed to the user script')
    args = parser.parse_args(argv)

    loglevel_name = args.loglevel.upper()
    if loglevel_name == 'DEFAULT':
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

    path = args.script
    name = args.name
    script_args = args.script_args
    if script_args[:1] == ['--']:
        script_args = script_args[1:]

    if not name:
        name = os.path.splitext(os.path.basename(path))[0]
        if name.startswith('slowtask-'):
            name = name[len('slowtask-'):]
        name = re.sub(r'[^a-zA-Z0-9]', '_', name)

    autocider = RetainerAutocide(name)
    autocider.start()

    slowdash_url = args.slowdash_url
    if not slowdash_url:
        slowdash_url='http://localhost:18881'
    
    module, tasklet = load_task_module(path=path, name=name, argv=script_args)

    tasklet.run(slowdash_url=slowdash_url, name=name, module=module)

    

if __name__ == '__main__':
    main()
