// control.mjs //
// Author: Sanshiro Enomoto <sanshiro@uw.edu> //
// Created on 18 November 2021 //
// Refactored on 18 June 2022 //
// Refactored on 5 March 2025 //


import { JG as $ } from './jagaimo/jagaimo.mjs';


export class Platform {
    
    static getUrlOptions() {
        let options = {};
        const search = window.location.search.split('?')[1];
        if (search) {
            for(let kv of search.split('&')) {
                let [key, value] = kv.split('=');
                options[key] = decodeURIComponent(value);
            }
        }

        return options;
    }


    static async initialize(defaults={}, options={}, args={}) {
        // defaults: used when not specified elsewhere
        // args: overwrite values specified elsewhere
        // options: URL parameters
        
        setTimeout(
            () => { Platform.setupDataList() },
            3000
        );
        return await Platform.fetchConfig(defaults, options, args);
    }
    
    
    static async fetchConfig(defaults, options, args) {
        let params = {
            config_file: options.config,
            config_data: options.configdata,
            defaults: defaults,
            page_config: {},
            args: args,
        };

        params = await Platform._load_project_config(params);
        params = await Platform._load_page_config(params);
        params = await Platform._load_theme(params);

        return $.extend(true, {}, params.defaults, params.page_config, params.args);
    }

    
    static async _load_project_config(params) {
        const defaults = {
            project: { name: null, title: "New Project" },
            style: { theme: 'light' }
        };
        const response = await fetch('./api/config');
        if (! response.ok) {
            console.error("ERROR: fetching proect config: " + response.status + " " + response.statusText);
            return params;
        }
        const config = await response.json();
        if (config) {
            params.args._project = $.extend(true, {}, defaults, config);
            params.defaults.meta = { name: null, title: params.args._project.title };
        }
        return params;
    }
    

    static async _load_page_config(params) {
        if (params.config_data) {
            try {
                params.page_config = JSON.parse(atob(params.config_data));
            }
            catch (error) {
                $('<div>').appendTo($('body')).html(`
                    <h3>Configuration Loading Error</h3>
                        Error: ${error.message}
                `);
                return;
            }
        }
        
        else if (params.config_file) {
            let config = null;
            const response = await fetch('./api/config/content/' + params.config_file);
            if (response.ok) {
                config = await response.json();
            }
            if (config) {
                params.page_config = config;
            }
            else {
                params.page_config = {
                    control: {
                        grid: { 'rows': 1, 'columns': 1 },
                        reload: 0,
                        inactive: true,
                    },
                    "panels": [{
                        type: "config_editor",
                        title: "Configuration File Error",
                        file: params.config_file,
                    }]
                };
            }
        }
        
        return params;
    }

    
    static async _load_theme(params) {
        const style = $.extend({}, params.args._project?.style??{}, params.page_config.style??{}, params.args.style??{});
        const theme = style.theme ?? 'light';
        let theme_css = $('#sd-theme-css');
        try {
            await new Promise((resolve, reject) => {
                theme_css.bind('load', () => resolve({}));
                theme_css.bind('error', (e) => reject(e));
                theme_css.attr('href', 'slowjs/slowdash-' + theme + '.css');
            });
        }
        catch(e) {
            $('<div>').appendTo($('body')).html(`
                <h3>Theme-CSS Loading Error</h3>
                Name: slowdash-${theme}.css<br>
                Error: ${e.message}
            `);
        }
        
        return params;
    }


    static async setupDataList() {
        let numeric_datalist = $('<datalist>').attr('id', 'sd-numeric-datalist').appendTo(document.body);
        let table_datalist = $('<datalist>').attr('id', 'sd-table-datalist').appendTo(document.body);
        let tree_datalist = $('<datalist>').attr('id', 'sd-tree-datalist').appendTo(document.body);
        let blob_datalist = $('<datalist>').attr('id', 'sd-blob-datalist').appendTo(document.body);
        let hist_datalist = $('<datalist>').attr('id', 'sd-histogram-datalist').appendTo(document.body);
        let hist2d_datalist = $('<datalist>').attr('id', 'sd-histogram2d-datalist').appendTo(document.body);
        let graph_datalist = $('<datalist>').attr('id', 'sd-graph-datalist').appendTo(document.body);
        let histgraph_datalist = $('<datalist>').attr('id', 'sd-histgraph-datalist').appendTo(document.body);
        let all_datalist = $('<datalist>').attr('id', 'sd-all-datalist').appendTo(document.body);
        
        const response = await fetch('api/channels?fields=name');
        const record = await response.json();
        if (! record || Object.keys(record).length == 0) {
            return;
        }
        for (let entry of record) {
            if (! entry.name) {
                continue;
            }
            all_datalist.append($('<option>').attr('value', entry.name).text(entry.name));
            if (((entry.type??'') == '') || (entry.type == 'numeric')) {
                if (! (entry.current??false)) {
                    numeric_datalist.append($('<option>').attr('value', entry.name).text(entry.name));
                }
            }
            else if (entry.type == 'table') {
                table_datalist.append($('<option>').attr('value', entry.name).text(entry.name));
            }
            else if (entry.type == 'tree') {
                tree_datalist.append($('<option>').attr('value', entry.name).text(entry.name));
            }
            else if (entry.type == 'blob') {
                blob_datalist.append($('<option>').attr('value', entry.name).text(entry.name));
            }
            else if (entry.type == 'histogram') {
                hist_datalist.append($('<option>').attr('value', entry.name).text(entry.name));
                histgraph_datalist.append($('<option>').attr('value', entry.name).text(entry.name));
            }
            else if (entry.type == 'histogram2d') {
                hist2d_datalist.append($('<option>').attr('value', entry.name).text(entry.name));
            }
            else if (entry.type == 'graph') {
                graph_datalist.append($('<option>').attr('value', entry.name).text(entry.name));
                histgraph_datalist.append($('<option>').attr('value', entry.name).text(entry.name));
            }
        }
        
        const response2 = await fetch('./api/config/contentlist');
        const contentlist = await response2.json();
        if (contentlist) {
            let dashboard_dl = $('<datalist>').attr('id', 'sd-dashboard-datalist').appendTo(document.body);
            let map_dl = $('<datalist>').attr('id', 'sd-map-datalist').appendTo(document.body);
            let html_dl = $('<datalist>').attr('id', 'sd-html-datalist').appendTo(document.body);
            for (let entry of contentlist) {
                if (entry.type == 'slowdash') {
                    dashboard_dl.append($('<option>').attr('value', entry.name).text(entry.name));
                }
                else if (entry.type == 'map') {
                    map_dl.append($('<option>').attr('value', entry.name).text(entry.name));
                }
                else if (entry.type == 'html') {
                    html_dl.append($('<option>').attr('value', entry.name).text(entry.name));
                }
            }
        }
    }
}
