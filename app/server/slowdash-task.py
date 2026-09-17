# Created by Sanshiro Enomoto on 26 June 2026 #

import os, sys, time, re, json, argparse, asyncio, importlib.util, logging, traceback
from slowpy.mesh import Tasklet, RetainerAutocide, Mesh, MeshStdio


def load_task_module(path:str, *, name:str, argv:list[str]|None=None):
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        raise FileNotFoundError(path)

    module_name = name
    if module_name in sys.modules:
        module_name = f'_slowtask_{module_name}_{abs(hash(path))}'
    
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
        module._sd_tasklet = tasklet
        exec('from slowpy.control import ControlSystem', module.__dict__)
        exec('ControlSystem._mesh = _sd_tasklet._mesh', module.__dict__)
        
    return module, tasklet



async def main():
    parser = argparse.ArgumentParser(description = 'Run a Python script as a SlowTask')
    parser.add_argument('script', help='user task script to load')
    parser.add_argument('--name', action='store', dest='name', help='task name; defauts to the script filename')
    parser.add_argument('--mesh', action='store', dest='mesh', help='SlowMesh URL, e.g., slowmq://localhost:18881')
    parser.add_argument('--params', action='store', dest='params', default='{}', help='JSON string for task parameters')
    parser.add_argument(
        '--logging',
        action='store', dest='loglevel', default='default', choices=['default', 'debug', 'info', 'warning', 'error'],
        help='logging level'
    )
    args, script_args = parser.parse_known_args()

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
    mesh_url = args.mesh
    if script_args[:1] == ['--']:
        script_args = script_args[1:]

    params = {}
    try:
        params = json.loads(args.params)
    except Exception as e:
        print(f'bad JSON for params: {args.params}')
        sys.exit(-1)
    
    if not name:
        name = os.path.splitext(os.path.basename(path))[0]
        if name.startswith('slowtask-'):
            name = name[len('slowtask-'):]
        name = re.sub(r'[^a-zA-Z0-9]', '_', name)

    autocider = RetainerAutocide(name)
    autocider.start()

    # use a dedicated MeshStdio to capture error messages during script loading (including loader.exec_module())
    mesh, mesh_stdio = None, None
    try:
        mesh = Mesh(name=name, url=mesh_url)
        mesh_stdio = MeshStdio(mesh, name=name, topic_prefix='sd.task')
        await mesh.aio_start()
        await mesh_stdio.aio_start()
        await asyncio.sleep(0.1) # have stdio start

        async def notify_life_event(task_name:str, mesh_id:str, event_name:str):
            try:
                await mesh.aio_publish(f'sd.task.life_event.{task_name}.{mesh_id}', {
                    'mesh_id': mesh_id,
                    'name': task_name,
                    'timestamp': int(time.time()),
                    'event': event_name,
                })
            except Exception as e:
                logging.error(f'slowdask-task: unable to publish task life-event: {mesh_id}: {e}')
    
        try:
            module, tasklet = load_task_module(path=path, name=name, argv=script_args)
            await notify_life_event(name, mesh.mesh_id, 'script loaded')
        except Exception as e:
            await notify_life_event(name, mesh.mesh_id, 'script loading failed')
            tb = traceback.format_exc()
            if tb is not None and len(tb.strip()) > 0:
                logging.error(tb)
                print(tb)
            return
    finally:
        await asyncio.sleep(0.1) # have stdio flush
        try:
            await mesh_stdio.aio_stop()
        except Exception as e:
            print(e)
        try:
            await mesh.aio_close()
        except Exception as e:
            print(e)
            
    try:
        await tasklet.run_module(module=module, name=name, params=params, mesh_url=mesh_url)
    except Exception as e:
        logging.error(f'slowdash-task: error on loading: {e}')
            

            
    
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        print(e)
        sys.exit(-1)
