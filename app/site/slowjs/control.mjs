// control.mjs //
// Created by Sanshiro Enomoto on 18 November 2021
// Refactored by Sanshiro Enomoto on 18 June 2022
// Refactored by Sanshiro Enomoto on 5 March 2025


import { JG as $, JGDateTime,  } from './jagaimo/jagaimo.mjs';


export class DataRequest {
    #defaultOptions;
    #defaultRequests;
    #customRequests;
    #streamingChannels;
    
    constructor(length, to, defaultOptions={}) {
        const defaults = {
            length: length,
            to: to,
            resample: -1,
            reducer: 'last',
            filler: 'fillna',
            envelope: 0,
            priorData: 0,
            resamplingBuckets: 600,
            resamplingThreshold: 7200,
        };
        this.#defaultOptions = $.extend({}, defaults, defaultOptions);
        
        this.#defaultRequests = {};
        this.#customRequests = {};
        
        this.#streamingChannels = new Set();
    }

    
    append(channel, customOptions={}, fromQuery=true, fromStreaming=true) {
        if (fromStreaming) {
            this.#streamingChannels.add(channel);
        }
        if (! fromQuery) {
            return;
        }
        
        let { resamplingThreshold, resamplingBuckets, ...requestOpts } = this.#defaultOptions;

        for (const name in this.#defaultOptions) {
            if (name in customOptions) {
                const customValue = customOptions[name];
                if (name === 'resamplingThreshold') {
                    resamplingThreshold = customValue;
                }
                else if (name === 'resamplingBuckets') {
                    if (customValue > 1) {
                        resamplingBuckets = customValue;
                    }
                }
                else {
                    requestOpts[name] = customValue;
                }
            }
        }
        if (resamplingThreshold < 0 || requestOpts.length <= resamplingThreshold) {
            requestOpts.resample = -1;
        }
        else {
            requestOpts.resample = (requestOpts.length / resamplingBuckets).toFixed(1);
        }
        
        let requestParams = Object.entries(requestOpts).map(([key, value]) => {
            return key + '=' + encodeURIComponent(value);
        }).join('&');
            
        let requestId = channel;
        if (Object.keys(customOptions).length > 0) {
            const op = Object.entries(customOptions).map(([k,v])=>`${k}=${v}`).join(',');
            requestId += '{' + op + '}';
            this.#customRequests[requestId] = [ channel, requestParams ];
        }
        else {
            this.#defaultRequests[requestId] = [ channel, requestParams ];
        }
        
        return requestId;
    }


    channelList() {
        let list = [];

        for (const [id, [ch, opts]] of Object.entries(this.#defaultRequests)) {
            list.push(ch);
        }
        for (const [id, [ch, opts]] of Object.entries(this.#customRequests)) {
            list.push(ch);
        }

        return list;
    }

    
    streamingChannelList() {
        return Array.from(this.#streamingChannels);
    }

    
    queryList(existingData, thresholdToCombimeRequests=5*86500) {
        let list = [];

        if (this.#defaultOptions.length < thresholdToCombimeRequests) {
            let channels = [], opts;
            for (const [id, [ch, params]] of Object.entries(this.#defaultRequests)) {
                if (! Object.hasOwn(existingData, id)) {
                    channels.push(ch);
                    opts = params;
                }
            }
            if (channels.length > 0) {
                list.push([null, `${channels.join(',')}?${opts}`]);
            }
        }
        else{
            for (const [id, [ch, opts]] of Object.entries(this.#defaultRequests)) {
                if (! Object.hasOwn(existingData, id)) {
                    list.push([null, `${ch}?${opts}`]);
                }
            }
        }

        // custom requests are always individual
        for (const [id, [ch, opts]] of Object.entries(this.#customRequests)) {
            if (! Object.hasOwn(existingData, id)) {
                list.push([id, `${ch}?${opts}`]);
            }
        }

        return list;
    }
};



class DataReceiver {
    #loggedErrors;
    
    constructor() {
        this.#loggedErrors = new Set();
    }

    
    parseDataJson(textdata) {
        if (textdata.length <= 2) {
            return {};
        }
        
        let data = {};
        try {
            data = JSON.parse(textdata.replace(/(:|{|\[|,)\s*NaN/g, '$1"NaN"'), (k,v) => {
                return (v === 'NaN') ? NaN : v;
            });
        }
        catch (err) {
            if (! this.#loggedErrors.has('data')) {
                this.#loggedErrors.add('data');
                console.error('invalid data packet: ', err);
                console.log(textdata);
            }
        }

        return data;
    }
};



export class QueryReceiver extends DataReceiver {    
    constructor() {
        super();
    }

    
    async receive(queryList, onReceiveData) {
        let status = { code:200, text:'OK' };
        for (let i = 0; i < queryList.length; i++) {
            const [id, query] = queryList[i];
                                          
            let textdata = '';
            try {
                const response = await fetch('api/data/' + query);
                if (! response.ok) {
                    status = { code: response.status, text: response.statusText };
                }
                else {
                    textdata = await response.text();
                }
            }
            catch (err) {
                status = { code: -1, text: 'SlowDash server not reachable' };
            }

            const data = this.parseDataJson(textdata);
            const isPartial = (i < queryList.length-1);
            onReceiveData(id, data, isPartial);
        }

        return status;
    }
};



export class StreamingReceiver extends DataReceiver {
    #onReceiveData;
    #url;
    #sse;
    #clientId;
    #subscriptionList;
    
    constructor(onReceiveData) {
        super();
        
        this.#onReceiveData = onReceiveData;

        this.#url = null;
        this.#sse = null;
        this.#clientId = null;
        this.#subscriptionList = new Set();

        this.#setup();
    }


    async subscribe(channels) {
        if (this.#clientId == null) {
            console.error("SSE subscription: no client_id received");
            return;
        }
        const url = this.#url.toString() + 'api/webmesh/subscribe/data?client_id=' + this.#clientId;
        
        for (const channel of channels) {
            if (this.#subscriptionList.has(channel)) {
                continue;
            }
            
            const Message = {
                'channel': channel,
            };

            try {
                const response = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json; charset=utf-8' },
                    body: JSON.stringify(Message),
                });
                if (! response.ok) {
                    console.error("SSE subscription failed: " + response.statusText);
                }
                else {
                    this.#subscriptionList.add(channel);
                    console.log("SSE subscription: " + channel);
                }
            }
            catch (err) {
                console.error("SSE subscription failed: server not reachable");
            }
        }
    }

    
    async unsubscribe() {
        if (this.#clientId == null) {
            return;
        }
        if (this.#subscriptionList.size == 0) {
            return;
        }
        this.#subscriptionList.clear();
        
        const url = this.#url.toString() + 'api/webmesh/unsubscribe?client_id=' + this.#clientId;
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json; charset=utf-8' },
                body: '',
            });
            if (! response.ok) {
                console.error("SSE unsubscription failed: " + response.statusText);
            }
            else {
                console.log("SSE unsubscription completed");
            }
        }
        catch (err) {
            console.error("SSE unsubscription failed: server not reachable");
        }
    }

    
    #setup() {
        if (this.#sse != null) {
            return;
        }
        
        this.#url = new URL(window.location.href);
        this.#url.search = '';
        this.#url.hash = '';
        if (this.#url.pathname.match(/\.[a-zA-Z0-9]+$/)) {  
            // the last path element has an extension (file) -> remove the file name
            this.#url.pathname = this.#url.pathname.replace(/\/[^/]*$/, '/');
        }
        else {
            this.#url.pathname += (this.#url.pathname.endsWith('/') ? '' : '/');
        }

        try {
            this.#sse = new EventSource(this.#url.toString() + 'event/webmesh/attach');
        }
        catch(error) {
            this.#sse.close();
            this.#sse = null;
            console.error("SSE setup error: " + error);
            console.log("Data streaming is disabled.");
            return;
        }
        
        this.#sse.onopen = () => {
            ;
        };
        this.#sse.onclose = () => {
            console.log("SSE Closed");
            this.#sse = null;
        };
        this.#sse.addEventListener("register", (event) => {
            try {
                this.#clientId = JSON.parse(event.data).client_id;
            }
            catch (err){
                console.error("SSE Error: bad register event: " + err);
                return;
            }
            console.log('SSE Connected: client_id=' + this.#clientId);
        });
        
        this.#sse.addEventListener("data", (event) => {
            this.#onReceiveData(this.parseDataJson(event.data));
        });

        this.#sse.onerror = () => {
            this.#sse.close();
            this.#sse = null;
            console.error("SSE Error: Data streaming is closed.");
        };
    }
};



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
        
        this.queryReceiver = new QueryReceiver();
        this.streamingReceiver = new StreamingReceiver((data) => {
            console.log('SSE data received', data);
        });
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
                if (this.currentData !== null) {
                    this.view.draw(this.currentData, displayRange);
                }
                this.callbacks.changeDisplayTimeRange(displayRange);
            },
            reconfigure: async () => {
                await this.configure();
            },
            popout: (panel) => {
                this.#popoutPanel(panel);
            },
            emit: (topic, message) => {
                this.emit(topic, message);
            },
            forceUpdate: this.callbacks.forceUpdate,
            suspend: this.callbacks.suspend,
        };
        await this.view.configure(config, this.options, view_callbacks);

        this.streamingReceiver.unsubscribe();
        let dataRequest = new DataRequest(10, 0);
        this.view.fillDataRequest(dataRequest);
        this.streamingReceiver.subscribe(dataRequest.streamingChannelList());
        
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

        let length, to = this.currentData.__meta.range.to;
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
        
        let dataRequest = new DataRequest(length, to);
        this.view.fillDataRequest(dataRequest);
        
        const queryList = dataRequest.queryList(this.currentData);
        if (queryList.length <= 0) {
            this.view.draw(this.currentData);
            this.isUpdateRunning = false;
            return {code:200, text:'OK'};
        }
        this.currentData.__meta.isPartial = true;

        const status = this.queryReceiver.receive(queryList, (id, data, isPartial) => {
            for (const ch in data) {
                this.currentData[id ?? ch] = data[ch];
            }
            this.currentData.__meta.isPartial = isPartial;
            if (! isPartial) {
                this.view.draw(this.currentData);
            }
        });
        this.isUpdateRunning = false;
        
        return status;
    }

    
    async emit(topic, doc) {
        const url = './api/emit/' + topic;
        const message = (typeof doc === 'string') ? doc : JSON.stringify(doc);
        
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json; charset=utf-8' },
            body: message,
        });
        this.callbacks.forceUpdate();
    }

    
    #popoutPanel(panel) {
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
        if ((this.lastUpdateTime === 0) || (this.pendingRequests > 0)) {
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
        if (this.lastUpdateTime === 0) {
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
