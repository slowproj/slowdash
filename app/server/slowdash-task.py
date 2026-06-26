# Created by Sanshiro Enomoto on 26 June 2026 #

import sys, os, re, importlib.util
from slowpy.mesh.tasklet import Tasklet


def load_task_module(path:str, *, name:str|None=None, argv:list[str]|None=None):
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        raise FileNotFoundError(path)

    if not name:
        name = os.path.splitext(os.path.basename(path))[0]
        if name.startswith('slowtask-'):
            name = name[len('slowatsk-'):]
        name = re.sub(r'[^a-zA-Z0-9]', '_', name)

    module_name = name
    if module_name in sys.modules:
        module_name = f'_slowtask_{module_mame}_{abs(hash(path))}'
    
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f'unable to load task script: {path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    script_dir = os.path.dirname(path)
    old_argv = sys.argv
    old_path = list(sys.path)
    sys.argv = [path] + list(argv or [])
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    finally:
        sys.argv = old_argv
        sys.path[:] = old_path

    for value in module.__dict__.values():
        if isinstance(value, Tasklet):
            tasklet = value
            break
    else:
        tasklet = Tasklet(use_oldstyle_callbacks=True)
        module.Tasklet = Tasklet
        module.tasklet = tasklet
        
    return tasklet, name, module



def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description = 'Run a Python script as a SlowTask')
    parser.add_argument('script', help='user task script to load')
    parser.add_argument('--name', help='task name; defauts to the script filename')
    parser.add_argument('--slowdash-url', help='SlowDash URL, e.g., http://localhost:18881')
    parser.add_argument('script_args', nargs=argparse.REMAINDER, help='arguments passed to the user script')
    args = parser.parse_args(argv)

    slowdash_url = args.slowdash_url
    if not slowdash_url:
        slowdash_url='http://localhost:18881'
    
    script_args = args.script_args
    if script_args[:1] == ['--']:
        script_args = script_args[1:]

    tasklet, name, module = load_task_module(args.script, name=args.name, argv=script_args)

    tasklet.run(slowdash_url=slowdash_url, name=name, module=module)

    

if __name__ == '__main__':
    main()
