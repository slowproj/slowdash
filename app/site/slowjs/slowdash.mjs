// slowdash.mjs //
// Author: Sanshiro Enomoto <sanshiro@uw.edu> //
// Created on 29 March 2025 //


import { JG as $, JGDateTime } from './jagaimo/jagaimo.mjs';
import { JGDialogWidget } from './jagaimo/jagawidgets.mjs';
import { Layout } from './layout.mjs';
import { Controller, Scheduler } from './control.mjs';
import { Platform, SaveConfigDialog } from './platform.mjs';


export class SlowDash {
    
    constructor(div, config=null, options=null) {
        this.callbacks = {
            setStatus: (statusText) => {},
            setProgress: (progressText) => {},
            setBeatTime: (time) => {},
        };
        this.init_config = config;
        this.init_options = options;
        
        this.config = null;
        
        this.layout = new Layout(div);
        this.controller = new Controller(this.layout);
        this.scheduler = new Scheduler();

        this.currentDisplayTimeRange = null;
        this.resetDelay = 0;
    }
    

    setCallbacks(callbacks) {
        $.extend(this.callbacks, callbacks);
    }

    
    async configure(config, options={}) {
        // config can be one of:
        // - URL query string, e.g., window.location.search.split('?')[1]
        // - config file name
        // - config object (dict)
        
        if (typeof config == 'string') {
            this.config = await this._buildConfig(config, options);
        }
        else if ($.isDict(config)) {
            const defaults = { control: { range: { length: 3600, to: 0 }}};
            this.config = await Platform.initialize(defaults, options, config);
        }

        if (! this.config) {
            return null;
        }
        
        if (this.config.panels) {
            ;
        }
        else if (this.config.items) {
            // config is for Canvas -> wrap it with a Panel.
            this.config = {
                _project: this.config._project,
                meta: this.config.meta,
                control: this.config.control,
                panels: [{
                    type: 'canvas',
                    view_box: this.config.view_box || this.config.viewBox,
                    defaults: this.config.defaults ?? {},
                    items: this.config.items,
                    forms: this.config.forms,
                }]
            };
            this.config.control.inactive = true;
        }
        else {
            this.config.panels = [];
        }
        
        if ((this.config.control.grid?.columns??0) < 1) {
            this.config.control.grid = { columns: 1, rows: 1 };
            const n = this.config.panels.length;
            const cols = n<=12 ? [1, 1, 1, 2, 2, /*n=5*/ 3, 3, /*n=7*/3, 3, 3, 4, 4, /*n=12*/ 4][n] : 4;
            const rows = n<=12 ? [1, 1, 2, 2, 2, /*n=5*/ 2, 2, /*n=7*/3, 3, 3, 3, 3, /*n=12*/ 3][n] : 4;
            this.config.control.grid = { columns: cols, rows: rows };
        }
        
        if ((this.config.control.mode??'') == 'protected') {
            this.resetDelay = 300;
        }
        else if ((this.config.control.mode??'') == 'display') {
            this.resetDelay = 10;
        }
        else {
            this.resetDelay = 0;
        }
            
        this.currentDisplayTimeRange = {
            "from": this.config.control.range.to - this.config.control.range.length,
            "to": this.config.control.range.to,
        };
        
        this.scheduler.initialize({
            updateInterval: this.config.control.reload,
            resetDelay: this.resetDelay,
            update: async () => {
                return await this._update();
            },
            setStatus: (statusText) => {
                this.callbacks.setStatus(statusText);
            },
            setProgress: (progressText) => {
                this.callbacks.setProgress(progressText);
            },
            setBeatTime: (time) => {
                this.callbacks.setBeatTime(time);
            },
        });

        this.controller.setCallbacks({
            changeDisplayTimeRange: range => {
                this.currentDisplayTimeRange = range;
                this.scheduler.scheduleReset();
            },
            forceUpdate: () => {
                this.scheduler.update();
            },
            suspend: (duration=300) => {
                this.scheduler.suspend(duration);
            },
        });
            
        return this.config;
    }


    setRange(length, to) {
        this.config.control.range.length = Math.round(length);
        this.config.control.range.to = (to === null) ? 0 : Math.round(to);
        
        this.currentDisplayTimeRange = {
            "from": this.config.control.range.to - this.config.control.range.length,
            "to": this.config.control.range.to,
        };
        
        this.scheduler.update();
    }

    
    getCurrentDisplayTimeRange() {
        return this.currentDisplayTimeRange;
    }

    
    setUpdateInterval(interval) {  // interval: 0: once, -1: stop auto-reloading, >0: periodically
        if (interval !== 0) {
            this.config.control.reload = interval;
            this.scheduler.setUpdateInterval(interval);
        }
        else {
            this.scheduler.update();
        }
        
        return this.config.control.reload;
    }

    
    setGrid(rows, cols) {
        this.controller.setGrid(rows, cols);
    }

    
    async start() {
        if (this.config === null) {
            await this.configure(this.init_config, this.init_options);
        }
        await this.controller.configure(this.config, {});
        
        this.scheduler.start();
    }


    redraw() {
        this.controller.redraw();
    }

    
    scheduleReset() {
        this.scheduler.scheduleReset();
    }

    
    async _buildConfig(config, options) {
        let optionsDict = {};
        if (typeof options == 'string') {
            for(let kv of options.split('&')) {
                let [key, value] = kv.split('=');
                optionsDict[key] = decodeURIComponent(value);
            }
        }
        else if ($.isDict(options)) {
            $.extend(true, optionsDict, options);
        }
        
        if (typeof config == 'string') {
            if (/^[a-zA-Z0-9._-]+$/.test(config)) {
                optionsDict['config'] = config;
            }
            else {
                for(let kv of config.split('&')) {
                    let [key, value] = kv.split('=');
                    optionsDict[key] = decodeURIComponent(value);
                }
            }
        }
        
        const [ defaults, args ] = this._buildSettings(optionsDict);

        return await Platform.initialize(defaults, optionsDict, args);
    }

    
    // takes options (from URL QUERY_STRING), returns [ defaults, args ]
    // urlOptions: key-value pairs in the URL query string
    // defaults: used when not specified elsewhere
    // args: overwrite values specified elsewhere
    _buildSettings(options) {
        const defaults = {
            control: {
                range: {length: 900, to: 0},
                reload: 300,
                mode: 'normal',
            },
            style: {},
        };
        const args = {
            control: {
                range: {},
                grid: {},
            },
        };
        
        if (options.mode) {
            args.control.mode = options.mode;
        }
        if (options.theme) {
            args.style = { theme: options.theme };
        }
        if (options.time) {
            let to = (new JGDateTime(options.time)).asInt();
            if (to > 0) {
                args.control.range.to = to;
            }
        }
        if (options.to) {
            let to = (new JGDateTime(options.to)).asInt();
            if (to > 0) {
                args.control.range.to = to;
            }
        }
        if (options.length && parseFloat(options.length) > 10) {
            args.control.range.length = parseFloat(options.length);
        }
        if (options.reload) {
            if (parseFloat(options.reload) >= 1) {
                args.control.reload = Math.max(1, parseFloat(options.reload));
            }
            else {
                args.control.reload = parseFloat(0);
            }
        }
        if (options.grid) {
            let [rows, cols] = options.grid.split('x');
            args.control.grid = { rows: rows, columns: cols };
        }
        if (options.channel) {
            args.panels = [];
            for (const item of options.channel.split(';')) {
                const [channels, type] = item.split('/');
                if ((type ?? 'timeseries') == 'timeseries') {
                    let panel = { type: 'timeseries', plots: [] };
                    for (const ch of channels.split(',')) {
                        panel.plots.push({ type: 'timeseries', channel: ch });
                    }
                    args.panels.push(panel);
                }
                else if (['histogram', 'ts-histogram', 'histogram2d', 'graph'].includes(type)) {
                    let panel = { type: 'plot', axes: {}, plots: [] };
                    if (type == 'histogram2d') {
                        panel['axes']['colorscale'] = 'Parula';
                    }
                    for (const ch of channels.split(',')) {
                        panel.plots.push({ type: type, channel: ch });
                    }
                    args.panels.push(panel);
                }
                else if (['singles'].includes(type)) {
                    let panel = { type: 'singles', items: [] };
                    for (const ch of channels.split(',')) {
                        panel.items.push({ channel: ch });
                    }
                    args.panels.push(panel);
                }
                else if (['table', 'tree', 'blob'].includes(type)) {
                    for (const ch of channels.split(',')) {
                        args.panels.push({ type: type, channel: ch });
                    }
                }
            }
        }

        return [ defaults, args ];
    }


    // this is called by Scheduler, this calls controller.update()
    async _update() {
        let length = this.config.control?.range?.length ?? 0;
        if (! (length > 0)) {
            length = 3600;
        }
        let to = this.config.control?.range?.to ?? 0;
        if (! (to > 0)) {
            to = 0;
        }
        let from = to - length;
        
        const status = await this.controller.update({from:from, to:to});
        
        if (status.code == 200) {
            return null;
        }
        else {
            let message = 'Error on ';
            message += (new JGDateTime()).asString('%a, %b %d %H:%M');
            message += " [ ";
            if (status.code >= 0) {
                message += "Status" + status.code + ", ";
            }
            message += status.text + " ]";
            return message;
        }
    }
}
