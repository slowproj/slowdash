#! /usr/bin/env python3
# Created by Sanshiro Enomoto on 27 December 2024 #

from component import PluginComponent


class ExportComponent(PluginComponent):
    def __init__(self, app, project):
        super().__init__('export', app, project)
        

    def build(self, plugin_config):
        export_list = [ export.get('type', None) for export in plugin_config ]
        if 'CSV' not in export_list:
            plugin_config.append({'type': 'CSV'})
        if ('Notebook' not in export_list) and ('Jupyter' not in export_list):
            plugin_config.append({'type': 'Notebook'})

        return super().build(plugin_config)
