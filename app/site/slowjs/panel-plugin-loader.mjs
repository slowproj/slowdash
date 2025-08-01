// panel-plugin-loader.mjs //
// Author: Sanshiro Enomoto <sanshiro@uw.edu> //
// Created on 4 November 2024 //


export { PanelPluginLoader };


import { Panel } from './panel.mjs';


class PanelPluginLoader {
    constructor() {
        this.panels = [];

        this.core_files = [
            './panel-plot.mjs',
            './panel-singles.mjs',
            './panel-canvas.mjs',
            './panel-map.mjs',
            './panel-table.mjs',
            './panel-html.mjs',
            './panel-catalog.mjs',
            './panel-download.mjs',
            './panel-misc.mjs',
        ];
        this.plugin_files = [
        ];
    }

    
    add_plugin(filepath) {
        this.plugin_files.push(filepath);
    }

    
    async load(filepath) {
        this.panels = [];

        let load_from_module = (module) => {
            for (const key in module) {
                let obj = module[key];
                if (typeof obj == 'function' && obj.prototype instanceof Panel) {
                    this.panels.push(obj);
                }
            }
        };
        
        // to keep the order in the pull-down menu, load the core modules one by one
        for (const filepath of this.core_files) {
            const module = await import(filepath);
            load_from_module(module);
        }
        
        const modules = await Promise.all(this.plugin_files.map(filepath => import(filepath)));
        modules.forEach((module, index) => { load_from_module(module); });
        
        return this.panels;
    }
};
