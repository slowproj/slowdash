# Created by Sanshiro Enomoto on 19 Mar 2022 #

import sys, os, glob, io, yaml, asyncio, logging, traceback
import pathlib, stat, pwd, grp, enum

import slowapi
from sd_component import Component


class ConfigComponent(Component):
    def __init__(self, app, project):
        super().__init__(app, project)
        self.project_dir = self.project.project_dir
        

    @slowapi.get('/config')
    async def get_config(self):
        return await self._get_config(with_list=False)

        
    @slowapi.get('/config/list')
    async def get_list(self):
        return await self._get_config(with_list=True, with_content_meta=True)

        
    @slowapi.get('/config/filelist')
    async def get_filelist(self, sortby='mtime', reverse:bool=False):
        if self.project_dir is None:
            return []
        
        filelist = []
        for filepath in glob.glob(os.path.join(self.project_dir, 'config', '*.*')):
            filestat = os.lstat(filepath)
            mtime = int(os.path.getmtime(filepath))
            filelist.append({
                'name': os.path.basename(filepath),
                'size': os.path.getsize(filepath),
                'mode': stat.filemode(filestat.st_mode),
                'owner': pwd.getpwuid(filestat.st_uid)[0],
                'group': grp.getgrgid(filestat.st_gid)[0],
                'mtime': mtime
            })

        if len(filelist) > 0 and sortby in filelist[0].keys():
            filelist = sorted(filelist, key=lambda entry: entry[sortby], reverse=reverse)
            
        return filelist

        
    @slowapi.get('/config/json/{filename}')
    async def get_json(self, filename:str):
        meta, content = await self._load_json(filename)
        try:
            # this requires W_OK, might fail from CGI etc.
            pathlib.Path(filepath).touch()
        except:
            pass
            
        if content is None:
            return slowapi.Response(400)
        
        return content


    @slowapi.get('/config/meta/{filename}')
    async def get_meta(self, filename:str):
        meta, content = await self._load_json(filename)
        if meta is None:
            return slowapi.Response(400)
        return meta

    
    @slowapi.get('/config/file/{filename}')
    async def get_file(self, filename:str):
        filepath, ext = self._get_filepath_ext(filename, os.R_OK)
        if filepath is None:
            logging.warning(f'GET config/file: {filename}: access denied')
            return slowapi.Response(404)

        if not self.project.is_secure:
            if ext not in [ '.json', '.yaml', '.html', '.csv', '.svn', '.png', '.jpg', '.jpeg' ]:
                return slowapi.Response(403)  # Forbidden
                
        return slowapi.FileResponse(filepath)

        
    @slowapi.post('/config/file/{filename}')
    async def post_file(self, filename: str, body:bytes, overwrite:str='no'):
        filepath, ext = self._get_filepath_ext(filename)
        if filepath is None:
            logging.warning(f'POST config/file: {filename}: access denied')
            return Reply(400)
        if not self.project.is_secure:
            if ext not in [ '.json', '.yaml', '.html', '.csv', '.svn', '.png', '.jpg', '.jpeg' ]:
                return slowapi.Response(403)  # Forbidden

        config_dir = os.path.join(self.project_dir, 'config')
        if not os.path.isdir(config_dir):
            try:
                os.makedirs(config_dir)
            except:
                logging.error('unable to create directory: ' + config_dir)
                return slowapi.Response(500)       # Internal Server Error
            
        mode = self.project.config.get('system', {}).get('file_mode', 0o644) + 0o100
        if mode & 0o070 != 0:
            mode = mode + 0o010
        if mode & 0o007 != 0:
            mode = mode + 0o001
        try:
            os.chmod(config_dir, mode)
        except Exception as e:
            logging.warning('unable to change file mode (%03o): %s: %s' % (mode, config_dir, str(e)))
            
        gid = self.project.config.get('system', {}).get('file_gid', -1)
        try:
            os.chown(config_dir, -1, gid)
        except Exception as e:
            logging.warning('unable to change file gid (%d): %s: %s' % (gid, config_dir, str(e)))

        if os.path.exists(filepath):
            if not os.access(filepath, os.W_OK):
                return slowapi.Response(403)   # Forbidden
            if overwrite != 'yes':
                return slowapi.Response(202)   # Accepted: no action made, try with overwrite flag
            
        try:
            with open(filepath, "wb") as f:
                f.write(body)
        except Exception as e:
            logging.error(f'unable to write file: {filepath}: %s' % str(e))
            return slowapi.Response(500)    # Internal Server Error

        try:
            mode = self.project.config.get('system', {}).get('file_mode', 0o644)
            os.chmod(filepath, mode)
        except Exception as e:                
            logging.warning('unable to change file mode (%03o): %s: %s' % (mode, filepath, str(e)))
        try:
            gid = self.project.config.get('system', {}).get('file_gid', -1)
            os.chown(filepath, -1, gid)
        except Exception as e:
            logging.warning('unable to change file gid (%d): %s: %s' % (gid, config_dir, str(e)))

        return slowapi.Response(201) # Created


    @slowapi.delete('/config/file/{filename}')
    async def delete_file(self, filename: str):
        filepath, ext = self._get_filepath_ext(filename, os.W_OK)
        if filepath is None:
            logging.warning(f'DETETE config/file: {filename}: access denied')
            return slowapi.Response(404)  # Not Found
        if not self.project.is_secure:
            if ext not in [ '.json', '.yaml', '.html', '.csv', '.svn', '.png', '.jpg', '.jpeg' ]:
                return slowapi.Response(403)  # Forbidden
        
        try:
            os.remove(filepath)
            logging.info(f'config file deleted: {filename}')
        except Exception as e:
            logging.error(f'file deletion error: {filename}: {e}')
            return slowapi.Response(500)   # Internal Server Error
        
        return slowapi.Response(200)


    async def _get_config(self, with_list=True, with_content_meta=True):
        self.project.update()
        if self.project.config is None:
            doc = {
                'slowdash': {
                    'version': self.project.version
                },
                'project': {}
            }
        else:
            doc = {
                'slowdash': {
                    'version': self.project.version
                },
                'project': {
                    'name': self.project.config.get('name', 'Untitled Project'),
                    'title': self.project.config.get('title', ''),
                    'is_secure': self.project.is_secure,
                },
                'style': self.project.config.get('style', None),
            }

        if (not with_list) or (self.project_dir is None):
            return doc
        
        filelist = []
        for filepath in glob.glob(os.path.join(self.project_dir, 'config', '*-*.*')):
            filelist.append([filepath, int(os.path.getmtime(filepath))])
            filelist = sorted(filelist, key=lambda entry: entry[1], reverse=True)
                
        contents = {}
        for filepath, mtime in filelist:
            filename = os.path.basename(filepath)
            rootname, ext = os.path.splitext(os.path.basename(filepath))
            kind, name = rootname.split('-', 1)
            config_key = '%s_config' % kind
            if ext not in [ '.json', '.yaml', '.html', '.py' ]:
                continue
            if config_key not in contents:
                contents[config_key] = []

            meta_info = {}
            if with_content_meta:
                meta_info = await self.get_meta(filename)

            contents[config_key].append({
                'name': name,
                'mtime': mtime,
                'title': meta_info.get('title', ''),
                'description': meta_info.get('description', ''),
                'config_file': filename,
                'config_error': meta_info.get('config_error', ''),
                'config_error_line': meta_info.get('config_error_line', '')
            })
        doc['contents'] = contents

        return doc

                
    async def _load_json(self, filename:str):
        filepath, ext = self._get_filepath_ext(filename, os.R_OK)
        if filepath is None:
            logging.warning(f'GET config: {filename}: access denied')
            return None, None

        meta, content = {}, None
        if ext not in [ '.json', '.yaml', '.py' ]:
            meta['config_error'] = 'bad file type'
            return meta, content
        if os.path.getsize(filepath) <= 0:
            meta['config_error'] = 'empty file'
            return meta, content

        doc = None
        if ext == '.py':
            try:
                process = await asyncio.create_subprocess_shell(
                    f'python3 {filepath}',
                    stdout = asyncio.subprocess.PIPE,
                    stderr = asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                returncode = process.returncode
                doc = stdout.decode().strip()
                msg = stderr.decode().strip()
                logging.info(f'{filename}: {msg}')
            except Exception as e:
                returncode = -1
            if returncode != 0:
                err_msg = msg.split('\n')[-1]
                logging.warn(f'JSON-generator Python error: {filepath}: {err_msg}')
                meta['config_error'] = f'Python Error: {err_msg}'
                return meta, None
        else:
            try:
                with open(filepath) as f:
                    doc = f.read()
            except Exception as e:
                logging.warn(f'unable to read config file: {filepath}: {e}')
                meta['config_error'] = f'unagle to read file: {e}'
                return meta, None

        try:
            content = yaml.safe_load(doc)
        except yaml.YAMLError as e:
            if hasattr(e, 'problem_mark'):
                line = e.problem_mark.line+1
                meta['config_error_line'] = line
                meta['config_error'] = 'Line %d: %s' % (line, e.problem)
            else:
                meta['config_error'] = str(e)
        
        if type(content) != dict:
            meta['config_error'] = 'not a dict'
        else:
            meta = content.get('meta', {})

        return meta, content

            
    def _get_filepath_ext(self, filename, access_flag=None):
        if self.project_dir is None:
            return None, None
        
        name, ext = os.path.splitext(filename)

        # sanity check
        if len(name) == 0 or not name.replace('_', '0').replace('-', '0').isalnum():
            return None, None

        filepath = os.path.join(self.project_dir, 'config', filename)
        if access_flag is not None:
            if not os.path.isfile(filepath) or not os.access(filepath, access_flag):
                return None, None

        return filepath, ext.lower()
