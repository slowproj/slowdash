# Created by Sanshiro Enomoto on 25 February 2025 #

import sys, os, glob, logging

import slowlette
from sd_component import Component


class UserHtmlComponent(Component):
    def __init__(self, app, project):
        super().__init__(app, project)

        # userhtml files
        self.slowlette.include(slowlette.FileServer(
            filedir = os.path.join(self.app.project_dir, 'userhtml'),
            prefix = '/userhtml',
            exclude = ['/userhtml/api', '/userhtml/slowjs'],
        ))

        # make slowjs accessble at /userhtml/slowjs
        self.slowlette.include(slowlette.FileServer(
            filedir = os.path.join(project.sys_dir, 'app', 'site', 'slowjs'),
            prefix = '/userhtml/slowjs',
        ))
        
        
    # make api accessble at /userhtml/api
    @slowlette.get('/userhtml/api/{*}')
    async def api_redirect(self, path:list, opts:dict):
        url = '/'.join(path[1:])
        if len(opts):
            url += '?' + '&'.join([f'{k}={v}' for k,v in opts.items()])
        return await self.app.request(url)


    @slowlette.get('/api/config/contentlist')
    async def get_content_meta(self):
        filelist = []
        for filepath in glob.glob(os.path.join(self.app.project_dir, 'userhtml', '*.html')):
            filelist.append([filepath, int(os.path.getmtime(filepath))])
            filelist = sorted(filelist, key=lambda entry: entry[1], reverse=True)
                
        doc = []
        for filepath, mtime in filelist:
            basename = os.path.basename(filepath)
            rootname, ext = os.path.splitext(os.path.basename(filepath))

            doc.append({
                'type': 'userhtml',
                'name': rootname,
                'mtime': mtime,
                'config_file': basename,
            })

        return doc
