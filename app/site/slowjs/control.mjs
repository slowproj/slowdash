// control.mjs //
// Author: Sanshiro Enomoto <sanshiro@uw.edu> //
// Created on 18 November 2021 //
// Refactored on 18 June 2022 //
// Refactored on 5 March 2025 //


import { JG as $ } from './jagaimo/jagaimo.mjs';


export class Controller {
    constructor(view) {  // "view" is an instance of "Layout" or "Panel"
        this.view = view;
        this.currentData = null;

        this._setupStreaming();
    }

    
    async configure(config=null, options={}, callbacks={}) {
        const default_options = {
            inactive: false,   // no control buttons at all
            immutable: false,   // no settings, no deleting
            standalone: false,  // no popup
        }
        const default_callbacks = {
            changeDisplayTimeRange: (displayRange) => {},
            forceUpdate: () => {},
            suspend: (duration) => {},
        };
        if (config !== null) {
            this.options = $.extend({}, default_options, this.options ?? {}, options);
            this.callbacks = $.extend({}, default_callbacks, this.callbacks ?? {}, callbacks);
        }
        
        const view_callbacks = {
            changeDisplayTimeRange: (displayRange) => {
                // displayRange can be null for a default range
                this.view.draw(this.currentData, displayRange);
                this.callbacks.changeDisplayTimeRange(displayRange);
            },
            reconfigure: async () => {
                await this.configure();
            },
            popout: (panel) => {
                this._popoutPanel(panel);
            },
            publish: (topic, message) => {
                this.publish(topic, message);
            },
            forceUpdate: this.callbacks.forceUpdate,
            suspend: this.callbacks.suspend,
        };
        await this.view.configure(config, this.options, view_callbacks);

        if (this.currentData !== null) {
            this.update();
        }
    }

    
    async setGrid(rows, columns) {
        let [nrows, ncols] = [parseFloat(rows), parseInt(columns)];
        if (!(nrows > 0) || ! (ncols > 0)) {
            return;
        }
        if (this.view.config.control?.grid) {
            this.view.config.control.grid.rows = nrows;
            this.view.config.control.grid.columns = ncols;
            await this.configure();
        }
    }

    
    async update(range=null) {
        // If the range is not specified, use the same range as before, and reuse the loaded data.
        if (range !== null) {
            this.currentData = {
                __meta: {
                    range: range,
                    isPartial: false,
                    isCurrent: false,
                }
            };
        }

        let channels = {}; {
            let inputChannels = [];
            this.view.fillInputChannels(inputChannels);
            for (let ch of inputChannels) {
                if (! (ch in this.currentData)) {
                    channels[ch] = 1;
                }
            }
        }
        
        if (Object.keys(channels).length <= 0) {
            this.view.draw(this.currentData);
            return {code:200, text:'OK'};
        }
        this.currentData.__meta.isPartial = true;
        
        let length;
        if (this.currentData.__meta.range.from <= 0) {
            length = -this.currentData.__meta.range.from;
        }
        else if (this.currentData.__meta.range.to <= 0) {
            const now = $.time();
            length = (now + this.currentData.__meta.range.to) - this.currentData.__meta.range.from;
        }
        else {
            length = this.currentData.__meta.range.to - this.currentData.__meta.range.from;
        }
        let opts = [ 'length='+length, 'to='+this.currentData.__meta.range.to ];
        if (length > 7200) {
            opts.push('resample='+(length/600).toFixed(1))
            opts.push('reducer=last');
        }
        
        let url_list = [];
        if (length < 5*86500) {
            url_list.push('api/data/' + Object.keys(channels).join(',') + '?' + opts.join('&'))
        }
        else {
            for (let ch in channels) {
                url_list.push('api/data/' + ch + '?' + opts.join('&'));
            }
        }
                
        let status = { code:200, text:'OK' };
        for (let i = 0; i < url_list.length; i++) {
            const response = await fetch(url_list[i]);
            if (! response.ok) {
                status = { code: response.status, text: response.statusText };
                continue;
            }
            const data = await response.json();

            for (let ch in data) {
                this.currentData[ch] = data[ch];
            }
            this.currentData.__meta.isPartial = (i < url_list.length-1);
            
            this.view.draw(this.currentData);
        }

        return status;
    }

    
    async publish(topic, doc) {
        if (topic !== 'currentdata') {
            return;
        }
        const message = (typeof doc === 'string') ? doc : JSON.stringify(doc);
        
        if (this.socket && (this.socket.readyState === WebSocket.OPEN)) {
            this.socket.send(message);
        }
        else {
            const url = './api/control/currentdata';
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json; charset=utf-8' },
                body: message,
            });
            this.callbacks.forceUpdate();
        }
    }

    
    _popoutPanel(panel) {
        let popout_config = JSON.parse(JSON.stringify(this.view.config));
        delete popout_config._project;
        delete popout_config.meta;
        popout_config.panels = [ JSON.parse(JSON.stringify(panel.config)) ];
        popout_config.control.grid = { 'rows': 1, 'columns': 1 };
        popout_config.control.reload = 0;
        
        const range = this.currentData?.__meta?.range;
        if (range) {
            popout_config.control.range = {
                "length": Math.round(range.to-range.from),
                "to": Math.round(range.to)
            };
        }
        else {
            popout_config.control.range.to = $.time();
        }

        let url = window.location.origin + window.location.pathname;
        url += '?configdata=' + btoa(JSON.stringify(popout_config));
        window.open(url);
    }

    
    _setupStreaming() {
        let url = new URL(window.location.href);
        url.protocol = 'ws:';
        url.search = '';
        url.hash = '';
        
        if (url.pathname.match(/\.[a-zA-Z0-9]+$/)) {  
            // last path element has an extension (file) -> remove the file name
            url.pathname = url.pathname.replace(/\/[^/]*$/, '/')
        }
        else {
            url.pathname += (url.pathname.endsWith('/') ? '' : '/')
        }
        url.pathname += 'ws/subscribe/currentdata';

        // if HTTPS is used and WebSocket is not WSS, an error occurs here
        try {
            this.socket = new WebSocket(url.toString());
        }
        catch(error) {
            this.socket = null;
            console.log("WebSocket setup error: " + error);
            console.log("Maybe web-socket entry (/ws) is not forwarded by reverse proxy?");
            console.log("Data streaming is disabled.");
            return;
        }
        
        this.socket.onopen = () => {
            console.log("Web Socket Connected");
        };
        this.socket.onclose = () => {
            console.log("Web Socket Closed");
        };
        this.socket.onerror = (error) => {
            console.error("Web Socket Error: " + error);
        };
        this.socket.onmessage = (event) => {
            const to = this.currentData?.__meta?.range?.to ?? null;
            if (to !== 0) {
                if ((to === null) || (to < 0)) {
                    return;
                }
                if (to < $.time()-1) {
                    return;
                }
            }
            
            let data = JSON.parse(event.data);
            data['__meta'] = {
                isCurrent: true,
                isPartial: true,
            }
            
            this.view.draw(data);
        }
    }
};

