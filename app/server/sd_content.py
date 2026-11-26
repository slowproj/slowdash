# Created by Sanshiro Enomoto on 19 Mar 2022 #

import sys, os, time, glob, io, json, yaml, asyncio, threading, importlib, inspect, logging, traceback
import pathlib, stat, pwd, grp, enum

import slowlette
from sd_component import Component


class ContentByPython(threading.Thread):
    def __init__(self, app, filepath):
        super().__init__()
        self.app = app
        self.filepath = filepath
        self.name = os.path.splitext(os.path.basename(self.filepath))[0]

        self.meta = { 'content_error': 'not processed' }
        self.result = None

        
    async def load(self):
        # We need this to run async _setup() in a way not to block other async functions.
        # Note that user-defined _setup() might run for a long time without await-ing.
        loop = asyncio.get_running_loop()
        self.start()
        await loop.run_in_executor(None, self.join)
        
        return self.meta, self.result

    
    def run(self):
        eventloop = asyncio.new_event_loop()
        asyncio.set_event_loop(eventloop)
        eventloop.run_until_complete(self.go())
        eventloop.close()

        
    async def go(self):
        try:
            module = importlib.machinery.SourceFileLoader(self.name, self.filepath).load_module()
        except Exception as e:
            msg = f'unable to load content Python module: {self.filepath}: {e}'
            logging.error(msg)
            self.meta = { 'content_error': msg }
        
        def get_func(module, name):
            if (name in module.__dict__) and callable(module.__dict__[name]):
                return module.__dict__[name]
            else:
                return None

        func_setup = get_func(module, '_setup')
        if func_setup is None:
            msg = f'no entry point ({self.name}) in content Python module: {self.filepath}'
            logging.error(msg)
            self.meta = { 'content_error': msg }
        else:
            nargs = len(inspect.signature(func_setup).parameters)
            if nargs >= 2:
                args = [ self.app, self.params ]
            elif nargs >= 1:
                args = [ self.app ]
            else:
                args = []
                            
            try:
                if inspect.iscoroutinefunction(func_setup):
                    self.result = await func_setup(*args)
                else:
                    self.result = await asyncio.to_thread(func_setup, *args)
                self.meta = {}
            except Exception as e:
                msg = f'error in content Python module: {self.filepath}: {e}'
                logging.error(msg)
                tb = traceback.format_exc()
                if tb is not None and len(tb.strip()) > 0:
                    logging.info(tb)
                    print(tb)
                self.meta = { 'content_error': msg }
                self.result = None

                

class ContentComponent(Component):
    def __init__(self, app, project):
        super().__init__(app, project)
        
        self.contents_dir = self.project.contents_dir


    @slowlette.get('/api/content/itemlist')
    async def get_contentlist(self):
        filelist = []
        if self.contents_dir is not None:
            for filepath in glob.glob(os.path.join(self.contents_dir, '*-*.*')):
                filelist.append([filepath, int(os.path.getmtime(filepath))])
                filelist = sorted(filelist, key=lambda entry: entry[1], reverse=True)
                
        doc = []
        for filepath, mtime in filelist:
            basename = os.path.basename(filepath)
            rootname, ext = os.path.splitext(os.path.basename(filepath))
            kind, name = rootname.split('-', 1)
            if ext not in [ '.json', '.yaml', '.html', '.py' ]:
                continue

            if kind in [ 'slowdash', 'slowplot', 'slowcruise' ]:
                meta_info, content = await self._load_content(basename, 'json')
            else:
                meta_info, content = {}, {}

            doc.append({
                'type': kind,
                'name': name,
                'mtime': mtime,
                'title': meta_info.get('title', ((content and content.get('title', name)) or '')),
                'description': meta_info.get('description', ''),
                'content_file': basename,
                'content_error': meta_info.get('content_error', ''),
                'content_error_line': meta_info.get('content_error_line', '')
            })

        return doc

        
    @slowlette.get('/api/content/item/{filename}')
    async def get_content(self, filename:str, content_type:str='json'):
        meta, content = await self._load_content(filename, content_type)
        if meta is None:
            return None   # not in my list -> use Slowlette aggregation
        if content is None:
            return slowlette.Response(400)
        
        filepath, ext = self._get_filepath_ext(filename, os.R_OK)
        if filepath is not None:
            try:
                pathlib.Path(filepath).touch()
            except Exception:
                # this requires W_OK, might fail from CGI etc. Errors here is not serious
                pass
            
        return content


    @slowlette.get('/api/content/filelist')
    async def get_filelist(self, sortby='mtime', reverse:bool=False):
        if self.contents_dir is None:
            return []
        
        filelist = []
        for filepath in glob.glob(os.path.join(self.contents_dir, '*.*')):
            filestat = os.lstat(filepath)
            mtime = int(os.path.getmtime(filepath))
            try:
                owner = pwd.getpwuid(filestat.st_uid)[0]
            except Exception:
                owner = filestat.st_uid
            try:
                group = grp.getgrgid(filestat.st_gid)[0]
            except Exception:
                group = filestat.st_gid
            filelist.append({
                'name': os.path.basename(filepath),
                'size': os.path.getsize(filepath),
                'mode': stat.filemode(filestat.st_mode),
                'owner': owner,
                'group': group,
                'mtime': mtime
            })

        if len(filelist) > 0 and sortby in filelist[0].keys():
            filelist = sorted(filelist, key=lambda entry: entry[sortby], reverse=reverse)
            
        return filelist

        
    @slowlette.get('/api/content/file/{filename}')
    async def get_file(self, filename:str):
        filepath, ext = self._get_filepath_ext(filename, os.R_OK)
        if filepath is None:
            return None
        if filepath is False:
            logging.warning(f'GET content/file: {filename}: access denied')
            return slowlette.Response(404)

        if not self.project.is_secure:
            if ext not in [ '.json', '.yaml', '.html', '.csv', '.svg', '.png', '.jpg', '.jpeg' ]:
                return slowlette.Response(403)  # Forbidden
                
        return slowlette.FileResponse(filepath)

        
    @slowlette.post('/api/content/file/{filename}')
    async def post_file(self, filename: str, body:bytes, overwrite:str='no'):
        if self.contents_dir is None:
            return slowlette.Response(403)   # Forbidden
        
        filepath, ext = self._get_filepath_ext(filename)
        if filepath is False or filepath is None:
            logging.warning(f'POST content/file: {filename}: access denied')
            return slowlette.Response(400)
        
        if not self.project.is_secure:
            if ext not in [ '.json', '.yaml', '.html', '.csv', '.svg', '.png', '.jpg', '.jpeg' ]:
                return slowlette.Response(403)  # Forbidden

        if not os.path.isdir(self.contents_dir):
            try:
                os.makedirs(self.contents_dir)
            except Exception as e:
                logging.error(f'unable to create directory: {self.contents_dir}: {e}')
                return slowlette.Response(500)       # Internal Server Error
            
        mode = self.project.config.get('system', {}).get('file_mode', 0o644) + 0o100
        if mode & 0o070 != 0:
            mode = mode + 0o010
        if mode & 0o007 != 0:
            mode = mode + 0o001
        try:
            os.chmod(self.contents_dir, mode)
        except Exception as e:
            logging.warning('unable to change file mode (%03o): %s: %s' % (mode, self.contents_dir, str(e)))
            
        gid = self.project.config.get('system', {}).get('file_gid', -1)
        try:
            os.chown(self.contents_dir, -1, gid)
        except Exception as e:
            logging.warning('unable to change file gid (%d): %s: %s' % (gid, self.contents_dir, str(e)))

        if os.path.exists(filepath):
            if not os.access(filepath, os.W_OK):
                return slowlette.Response(403)   # Forbidden
            if overwrite != 'yes':
                return slowlette.Response(202)   # Accepted: no action made, try with overwrite flag
            
        try:
            with open(filepath, "wb") as f:
                f.write(body)
        except Exception as e:
            logging.error(f'unable to write file: {filepath}: %s' % str(e))
            return slowlette.Response(500)    # Internal Server Error

        try:
            mode = self.project.config.get('system', {}).get('file_mode', 0o644)
            os.chmod(filepath, mode)
        except Exception as e:                
            logging.warning('unable to change file mode (%03o): %s: %s' % (mode, filepath, str(e)))
        try:
            gid = self.project.config.get('system', {}).get('file_gid', -1)
            os.chown(filepath, -1, gid)
        except Exception as e:
            logging.warning('unable to change file gid (%d): %s: %s' % (gid, filepath, str(e)))

        return slowlette.Response(201) # Created


    @slowlette.delete('/api/content/file/{filename}')
    async def delete_file(self, filename: str):
        filepath, ext = self._get_filepath_ext(filename, os.W_OK)
        if filepath is None:
            return None
        if filepath is False:
            logging.warning(f'DELETE content/file: {filename}: access denied')
            return slowlette.Response(404)  # Not Found
        if not self.project.is_secure:
            if ext not in [ '.json', '.yaml', '.html', '.csv', '.svg', '.png', '.jpg', '.jpeg' ]:
                return slowlette.Response(403)  # Forbidden
        
        try:
            os.remove(filepath)
            logging.info(f'content file deleted: {filename}')
        except Exception as e:
            logging.error(f'file deletion error: {filename}: {e}')
            return slowlette.Response(500)   # Internal Server Error
        
        return slowlette.Response(200)

                
    async def _load_content(self, filename:str, content_type):
        filepath, ext = self._get_filepath_ext(filename, os.R_OK)
        if filepath is None:
            if content_type == 'html' and filename.startswith('html-'):
                filepath, ext = self._get_filepath_ext(filename+'.py', os.R_OK)
                if filepath is None:
                    filepath, ext = self._get_filepath_ext(filename+'.html', os.R_OK)
            
        if filepath is None:
            return None, None  # no such file (at the accessible locations)
        if filepath is False:
            return { 'content_error': 'permission denied' }, None
        if os.path.getsize(filepath) <= 0:
            return { 'content_error': 'empty file' }, None

        doc = None
        if ext == '.py':
            return await ContentByPython(self.app, filepath).load()
        
        elif content_type != 'json':
            if not self.project.is_secure:
                if ext not in [ '.json', '.yaml', '.html', '.csv', '.svg', '.png', '.jpg', '.jpeg' ]:
                    return { 'content_error': 'bad file type' }, None
                
            content = None
            try:
                with open(filepath, 'rb') as f:
                    content = f.read()
            except Exception as e:
                msg = f'unable to read content file: {filepath}: {e}'
                logging.error(msg)
                return { 'content_error': msg }, None
            return {}, content
        
        else:
            if ext not in [ '.json', '.yaml' ]:
                return { 'content_error': 'bad file type' }, None
            try:
                with open(filepath) as f:
                    doc = f.read()
            except Exception as e:
                msg = f'unable to read content file: {filepath}: {e}'
                logging.error(msg)
                return { 'content_error': msg }, None

            meta, content = {}, None
            if ext == '.json':
                # YAML 1.1 cannot parse 1e-3 as a number, making it a string value.
                # This is solved in YAML 1.2, but PyYAML still implements YAML 1.1.
                # Hence we cannot use PyYAML to parse a JSON document.
                try:
                    content = json.loads(doc)
                except json.JSONDecodeError as e:
                    meta['content_error_line'] = e.lineno
                    meta['content_error'] = 'Line %d: %s' % (e.lineno, e.msg)
            elif ext == '.yaml':
                try:
                    content = yaml.safe_load(doc)
                except yaml.YAMLError as e:
                    if hasattr(e, 'problem_mark'):
                        line = e.problem_mark.line+1
                        meta['content_error_line'] = line
                        meta['content_error'] = 'Line %d: %s' % (line, e.problem)
                    else:
                        meta['content_error'] = str(e)
            if type(content) != dict:
                meta['content_error'] = meta.get('content_error', 'not a dict')
            else:
                meta = content.get('meta', {})

            return meta, content

            
    def _get_filepath_ext(self, filename, access_flag=None):
        '''
        returns (None, None) if the file does not exist
        returns (False, False) if permission is denied
        returns (filepath, ext.lower()) otherwise
        '''
        
        if self.contents_dir is None:
            logging.info(f'ContentFile: no contents dir')
            return None, None
        
        name, ext = os.path.splitext(filename)

        # sanity check
        if (
            len(name) == 0 or name.startswith('.') or
            not name.replace('_', '0').replace('-', '0').replace('.', '0').isalnum()
        ):
            logging.warning(f'ContentFile: sanity check failed: {filename}')
            return False, False

        filepath = os.path.join(self.contents_dir, filename)
        if not os.path.exists(filepath):
            if access_flag in (os.R_OK, os.X_OK):
                return None, None
            else:
                # TODO: for os.W_OK, check the parent directory
                pass
        elif not os.path.isfile(filepath):
            logging.warning(f'ContentFile: not a file: {filepath}')
            return False, False
        
        if (access_flag is not None) and (not os.access(filepath, access_flag)):
            logging.info(f'ContentFile: permission denied by access flag: {filepath}')
            return False, False

        return filepath, ext.lower()
