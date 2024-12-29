#! /usr/bin/env python3
# Created by Sanshiro Enomoto on 27 December 2024 #

import component


class ExportComponent(component.PluginComponent):
    def __init__(self, app, project):
        super().__init__('export', app, project)
        

    def build(self):
        export_list = [ export.get('type', None) for export in self.plugin_config ]
        if 'CSV' not in export_list:
            self.plugin_config.append({'type': 'CSV'})
        if ('Notebook' not in export_list) and ('Jupyter' not in export_list):
            self.plugin_config.append({'type': 'Notebook'})

        return super().build()
