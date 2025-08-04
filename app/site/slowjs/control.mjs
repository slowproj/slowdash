// control.mjs //
// Author: Sanshiro Enomoto <sanshiro@uw.edu> //
// Created on 18 November 2021 //
// Refactored on 18 June 2022 //
// Refactored on 5 March 2025 //


import { JG as $, JGDateTime,  } from './jagaimo/jagaimo.mjs';


export class Controller {
    constructor(view) {  // "view" is an instance of "Layout" or "Panel"
        this.callbacks = {
            changeDisplayTimeRange: (displayRange) => {},
            forceUpdate: () => {},
            suspend: (duration) => {},
        };
        
        this.view = view;
        this.currentData = null;
        this.isUpdateRunning = false;

        this.socket = null;
        this._setupStreaming();
    }

    
    setCallbacks(callbacks) {
        $.extend(this.callbacks, callbacks);
    }

    
    async configure(config, options={}) {
        const default_options = {
            inactive: config?.control?.inactive ?? false,   // no control buttons at all
            immutable: config?.control?.immutable ?? false,   // no settings, no deleting
            standalone: false,  // no popout
        }
        if (config !== null) {
            this.options = $.extend({}, default_options, this.options ?? {}, options);
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

    
    async redraw() {
        await this.view.configure();
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
        if (this.isUpdateRunning) {
            return {code:200, text:'OK'};
        }
        this.isUpdateRunning = true;
        
        // If the range is not specified, use the same range as before, and reuse the loaded data.
        if (range !== null) {
            this.currentData = {
                __meta: {
                    range: range,
                    isPartial: false,
                    isCurrent: false,
                    currentDataTime: null,
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
            this.isUpdateRunning = false;
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
            opts.push('resample='+(length/600).toFixed(1));
            opts.push('reducer=last');
        }
        
        let url_list = [];
        if (length < 5*86500) {
            url_list.push('api/data/' + Object.keys(channels).join(',') + '?' + opts.join('&'));
        }
        else {
            for (let ch in channels) {
                url_list.push('api/data/' + ch + '?' + opts.join('&'));
            }
        }
                
        let status = { code:200, text:'OK' };
        for (let i = 0; i < url_list.length; i++) {
            let data = {};
            try {
                const response = await fetch(url_list[i]);
                if (! response.ok) {
                    status = { code: response.status, text: response.statusText };
                }
                else {
                    data = await response.json();
                }
            }
            catch (err) {
                status = { code: -1, text: 'SlowDash server not reachable' };
            }

            for (let ch in data) {
                this.currentData[ch] = data[ch];
            }
            this.currentData.__meta.isPartial = (i < url_list.length-1);

            this.view.draw(this.currentData);
        }

        // re-establishing web-socket after server-recovery
        if ((this.socket === null) && (status.code > 0)) {
            this._setupStreaming();
        }
        
        this.isUpdateRunning = false;
        
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
        if (this.socket !== null) {
            return;
        }

        let url = new URL(window.location.href);
        url.protocol = (url.protocol == 'https:' ? 'wss:' : 'ws:');
        url.search = '';
        url.hash = '';
        
        if (url.pathname.match(/\.[a-zA-Z0-9]+$/)) {  
            // last path element has an extension (file) -> remove the file name
            url.pathname = url.pathname.replace(/\/[^/]*$/, '/');
        }
        else {
            url.pathname += (url.pathname.endsWith('/') ? '' : '/');
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
            this.socket = null;
        };
        this.socket.onerror = (error) => {
            console.error("Web Socket Error: " + error);
        };
        this.socket.onmessage = (event) => {
            const now = $.time();
            const to = this.currentData?.__meta?.range?.to ?? null;
            if (to !== 0) {
                if ((to === null) || (to < 0)) {
                    return;
                }
                if (to < now-1) {
                    return;
                }
            }
            
            let data = JSON.parse(event.data);
            data['__meta'] = {
                isCurrent: true,
                isPartial: true,
                currentDataTime: now,
            }
            
            this.view.draw(data);
        }
    }
};



export class Scheduler {
    constructor(options={}) {
        this.initialize(options);
        
        this.lastUpdateTime = 0;
        this.currentUpdateTime = 0;
        this.pendingRequests = 0;
        this.suspendUntil = 0;
        this.resetAt = 0;
        
        this.isBeating = false;
    }

    
    initialize(options={}) {
        const defaults = {
            updateInterval: 0,   // >0: interval, ==0: once, <0: no auto updates
            resetDelay: 0,
            update: async () => {},
            setStatus: (statusText) => {},
            setProgress: (progress) => {},
            setBeatTime: (time) => {},
        };
        this.options = $.extend({}, defaults, options);

        this.updateInterval = this.options.updateInterval;
        this.resetDelay = this.options.resetDelay;
    }
    

    start() {
        this.lastUpdateTime = 0;
        this.pendingRequests = 0;
        this.suspendUntil = 0;
        
        if (! this.isBeating) {
            this.isBeating = true;
            this._beat();
        }
    }


    setUpdateInterval(interval) {
        this.updateInterval = interval;
    }

    
    suspend(duration) {
        this.suspendUntil = $.time() + duration;
    }


    scheduleReset() {
        if (this.resetDelay > 0) {
            this.resetAt = $.time() + this.resetDelay;
        }
    }


    async update() {
        const now = $.time();
        if (now - this.currentUpdateTime < 60) {
            this.pendingRequests++;
            return;
        }
        
        this.lastUpdateTime = now;
        this.currentUpdateTime = now;
        this.pendingRequests = 0;
        this.suspendUntil = 0;

        let status = await this.options.update();
        this.currentUpdateTime = 0;
        if (status === null) {
            let date = (new JGDateTime(this.lastUpdateTime)).asString('%a, %b %d %H:%M');
            status = 'Update: ' + date;
        }
        this.options.setStatus(status);
    }

    
    _beat() {
        const now = $.time();
        if ((this.resetAt > 0) && (now > this.resetAt)) {
            window.location.reload(false);
        }
        this.options.setBeatTime(now);

        let lapse = now - this.lastUpdateTime;
        let suspend = this.suspendUntil - now;
        let togo;
        if ((this.lastUpdateTime == 0) || (this.pendingRequests > 0)) {
            togo = 0;
        }
        else if (this.updateInterval <= 0) {
            togo = 1e10;
        }
        else {
            togo = this.updateInterval - lapse;
        }
        if (suspend > togo) {
            togo = suspend;
        }
        if (togo < 0) {
            togo = 0;
        }

        let text1, text2;
        if (this.lastUpdateTime == 0) {
            text1 = 'initial loading';
        }
        else {
            text1 = lengthString(lapse, false, parseInt) + ' ago';
        }
        if (this.currentUpdateTime > 0) {
            text2 = ', receiving data... ' + parseInt(now - this.currentUpdateTime) + ' s';
        }
        else if (suspend >= togo-1) {
            text2 = ', update suspended for next ' + parseInt(togo) + ' s';
        }
        else if (
            ((this.updateInterval >= 60) && (togo < 10)) ||
            ((this.updateInterval > 1800) && (togo < 60))
        ){
            text2 = ', update in ' + parseInt(togo) + ' s';
        }
        else {
            text2 = '';
        }
        this.options.setProgress('(' + text1 + text2 + ')');
        
        if (togo <= 0) {
            this.update();
        }
        setTimeout(()=>{this._beat();}, 1000);
    }
};



export function lengthString(lapse, shortForm=true, transform=x=>parseFloat(x.toFixed(1))) {
    let t = parseFloat(lapse);
    if (isNaN(t)) return lapse;
    let sign = (t < 0) ? '-' : '';
    t = Math.abs(t);
    if (t < 60) {
        return transform(t) + (shortForm ? ' s' : ' seconds');
    }
    else if (t < 120.1) {
        return transform(t/60) + (shortForm ? ' min' : ' minute');
    }
    else if (t < 3600.1) {
        return transform(t/60) + (shortForm ? ' min' : ' minutes');
    }
    else if (t < 7200.1) {
        return transform(t/3600) + (shortForm ? ' h' : ' hour');
    }
    else if (t < 86400.1) {
        return transform(t/3600) + (shortForm ? ' h' : ' hours');
    }
    else if (t < 2*86400.1) {
        return transform(t/86400) + (shortForm ? ' d' : ' day');
    }
    else {
        return transform(t/86400) + (shortForm ? ' d' : ' days');
    }
}
