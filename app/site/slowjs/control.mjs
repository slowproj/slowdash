// control.mjs //
// Author: Sanshiro Enomoto <sanshiro@uw.edu> //
// Created on 18 November 2021 //
// Refactored on 18 June 2022 //
// Refactored on 5 March 2025 //


import { JG as $ } from './jagaimo/jagaimo.mjs';
import { JGInvisibleWidget, JGDialogWidget } from './jagaimo/jagawidgets.mjs';



export class Controller {
    constructor(view) {  // "view" is an instance of "Layout" or "Panel"
        this.view = view;
        this.currentDataPacket = null;

        this._setupStreaming();
    }

    
    async configure(config=null, callbacks={}) {
        const default_callbacks = {
            changeDisplayTimeRange: (range) => {
                // range value can be null for a default range
                this.view.drawRange(this.currentDataPacket, range);
                this.callbacks.changeDisplayTimeRange(range);
            },
            reconfigure: async () => {
                await this.configure();
                this.update();  // channnels might have been added by the reconfigure
            },
            forceUpdate: () => {},
            suspend: (duration) => {},
            popoutPanel: (index) => {},
            publish: (topic, message) => { this.publish(topic, message); },
        };
        
        if (config !== null) {
            this.callbacks = $.extend({}, default_callbacks, this.callbacks ?? {}, callbacks);
        }
        await this.view.configure(config, this.callbacks);
        
        if (this.currentDataPacket !== null) {
            this.view.drawRange(this.currentDataPacket, this.currentDataPacket.range);
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
            this.currentDataPacket = {
                isTransitional: true,
                isCurrent: false,
                range: range,
                data: {}
            };
        }

        let channels = {}; {
            let inputChannels = [];
            this.view.fillInputChannels(inputChannels);
            for (let ch of inputChannels) {
                if (! (ch in this.currentDataPacket.data)) {
                    channels[ch] = 1;
                }
            }
        }        
        
        if (Object.keys(channels).length <= 0) {
            this._processData({}, false);
            return {code:200, text:'OK'};
        }
        
        let length = this.currentDataPacket.range.to - this.currentDataPacket.range.from;
        let opts = [ 'length='+length, 'to='+this.currentDataPacket.range.to ];
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

            const isTransitional = (i < url_list.length-1);
            this._processData(data, isTransitional);
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
        url.pathname += 'subscribe/currentdata';

        this.socket = new WebSocket(url.toString());
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
            this._processCurrentData(JSON.parse(event.data));
        }
    }

    
    _processData(data, isTransitional) {
        this.currentDataPacket.isTransitional = isTransitional;
        for (let ch in data) {
            this.currentDataPacket.data[ch] = data[ch];
        }
        this.view.drawRange(this.currentDataPacket, this.currentDataPacket.range);
    }

    
    _processCurrentData(data) {
        const to = this.currentDataPacket?.range?.to ?? null;
        if ((to === null) || (to < 0)) {
            return;
        }
        const now = $.time();
        if ((to > 0) && (to < now - 10)) {  //... BUG: "10 sec" window is temporary
            return;
        }
        
        const dataPacket = {
            isTransitional: true,
            isCurrent: true,
            range: { from: now - 60, to: now },
            data: data,
        };
        this.view.drawRange(dataPacket, dataPacket.range);
    }
};

