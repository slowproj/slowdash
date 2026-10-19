# Created by Sanshiro Enomoto on 25 February 2025 #

import sys, os, glob, logging
from urllib.parse import urlencode

import slowlette
from sd_component import Component


class UserHtmlComponent(Component):
    def __init__(self, app, project):
        super().__init__(app, project)

        if self.app.project_dir is None:
            return

        # userhtml files
        self.slowlette.include(slowlette.FileServer(
            filedir = os.path.join(self.app.project_dir, 'userhtml'),
            prefix = '/userhtml',
            exclude = ['/api', '/slowjs'],
        ))

        # make slowjs accessble at /userhtml/slowjs
        self.slowlette.include(slowlette.FileServer(
            filedir = os.path.join(project.sys_dir, 'app', 'site', 'slowjs'),
            prefix = '/userhtml/slowjs',
        ))
        
        
    # make api accessble at /userhtml/api
    @slowlette.get('/userhtml/api/{*}')
    async def api_redirect(self, path:list, opts:dict):
        #url = '/'.join(path[1:])
        #if len(opts):
        #    url += '?' + urlencode(opts)
        #return await self.app.request(url)

        url = '/'.join(['..'] + path[1:])
        if len(opts):
            url += '?' + urlencode(opts)
        response = slowlette.Response(302, headers={
            'Location': url,
            'Content-Length': '0',
        })

        return response


    @slowlette.eventstream('/userhtml/event/{*}')
    async def event_redirect(self, path:list, opts:dict, eventstream:slowlette.EventStream):
        url = '/'.join(['..'] + path[1:])
        if len(opts):
            url += '?' + urlencode(opts)
        response = slowlette.Response(302, headers={
            'Location': url,
            'Content-Length': '0',
        })

        return response

    
    @slowlette.get('/api/config/contentlist')
    async def get_content_meta(self):
        if self.app.project_dir is None:
            return

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
