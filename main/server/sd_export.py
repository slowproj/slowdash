#! /usr/bin/env python3
# Created by Sanshiro Enomoto on 27 December 2024 #

from sd_component import PluginComponent


class ExportComponent(PluginComponent):
    def __init__(self, app, project):
        super().__init__('export', app, project)
        

    def build(self, plugin_config):
        export_list = [ export.get('type', '').lower() for export in plugin_config ]
        if 'csv' not in export_list:
            plugin_config.append({'type': 'CSV'})
        if ('notebook' not in export_list) and ('jupyter' not in export_list):
            plugin_config.append({'type': 'Notebook'})

        return super().build(plugin_config)
