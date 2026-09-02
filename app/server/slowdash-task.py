# Created by Sanshiro Enomoto on 26 June 2026 #

import os, sys, re, argparse, asyncio, logging, traceback
from slowpy.mesh import RetainerAutocide, Mesh, MeshStdio
from sd_task import load_task_module


async def main():
    parser = argparse.ArgumentParser(description = 'Run a Python script as a SlowTask')
    parser.add_argument('script', help='user task script to load')
    parser.add_argument('--name', action='store', dest='name', help='task name; defauts to the script filename')
    parser.add_argument('--mesh', action='store', dest='mesh', help='SlowMesh URL, e.g., slowmq://localhost:18881')
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

    if not name:
        name = os.path.splitext(os.path.basename(path))[0]
        if name.startswith('slowtask-'):
            name = name[len('slowtask-'):]
        name = re.sub(r'[^a-zA-Z0-9]', '_', name)

    autocider = RetainerAutocide(name)
    autocider.start()

    # Dedicated MeshStdio to capture error messages during script loading (including loader.exec_module())
    try:
        mesh = Mesh(name=name, url=mesh_url)
        mesh_stdio = MeshStdio(mesh, topic_prefix='sd.task')
        await mesh_stdio.aio_start()
        await mesh.aio_start()
    except Exception as e:
        logging.error(f'slowdash-task: error on setting up Mesh: {e}')
        return

    try:
        module, tasklet = load_task_module(path=path, name=name, argv=script_args)
        print(f'slowdash-task: {name} loaded')
    except Exception as e:
        module = None
        tb = traceback.format_exc()
        if tb is not None and len(tb.strip()) > 0:
            logging.error(tb)
            print(tb)
    finally:
        try:
            await mesh_stdio.aio_stop()
        except:
            pass
        try:
            await mesh.aio_close()
        except Exception:
            pass

    params = {}
    try:
        if module is not None:
            # this will start tasklet's own mesh and mesh stdio
            await tasklet.run_module(module=module, name=name, params=params, mesh_url=mesh_url)
    except Exception as e:
        logging.error(f'slowdash-task: error on loading: {e}')

    

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        sys.exit(-1)
