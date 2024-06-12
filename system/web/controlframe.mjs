// controlframe.mjs //
// Author: Sanshiro Enomoto <sanshiro@uw.edu> //
// Created on 3 May 2022 //

import { JG as $, JGDateTime,  } from './jagaimo/jagaimo.mjs';
import { JGPullDownWidget, JGDialogWidget } from './jagaimo/jagawidgets.mjs';


export function boot(defaults, optparse_func, start_func) {
    let options = {};
    let search = window.location.search.split('?')[1];
    if (search) {
        for(let kv of search.split('&')) {
            let [key, value] = kv.split('=');
            options[key] = decodeURIComponent(value);
        }
    }
    
    let params = {
        config_file: options.config,
        config_data: options.configdata,
        defaults: defaults,
        page_config: {},
        args: optparse_func(options),
        start_func: start_func
    };
    
    function initiate(params) {
        load_project_config(params);
    }
    
    function load_project_config(params) {
        let project_config = {
            project: { name: null, title: "New Project" },
            style: { theme: 'light' }
        };
        fetch('./api/config')
            .then(response => {
                if (! response.ok) {
                    throw new Error(response.status + " " + response.statusText);
                }
                return response.json();
            })
            .catch(e => {
                $('<div>').appendTo($('body')).html(`
                    <h3>Project-Configuration Loading Error</h3>
                    Error: ${e.message}
                `);
                return null;
            })
            .then(config => {
                if (config) {
                    params.args._project = $.extend(true, {}, project_config, config);
                    params.defaults.meta = { name: null, title: params.args._project.title };
                    load_page_config(params);
                }
            });
    }
    
    function load_page_config(params) {
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
            load_theme(params);
        }
        else if (params.config_file) {
            fetch('./api/config/jsonfile/' + params.config_file)
                .then(response => {
                    if (! response.ok) {
                        throw new Error(response.status + " " + response.statusText);
                    }
                    return response.json();
                })
                .catch(e => {
                    params.page_config = {
                        control: {
                            grid: { 'rows': 1, 'columns': 1 },
                            reload: 0,
                            immutable: true,
                        },
                        "panels": [{
                            type: "config_editor",
                            title: "Configuration File Error",
                            file: params.config_file,
                        }]
                    };
                    load_theme(params);
                })
                .then(config => {
                    if (config) {
                        params.page_config = config;
                        load_theme(params);
                    }
                });
        }
        else {
            load_theme(params);
        }
    }

    
    function load_theme(params) {
        const style = $.extend({}, params.args._project?.style??{}, params.page_config.style??{}, params.args.style??{});
        const theme = style.theme ?? 'light';
        let theme_css = $('#sd-theme-css');
        new Promise((resolve, reject) => {
            theme_css.bind('load', () => resolve({}));
            theme_css.bind('error', (e) => reject(e));
            theme_css.attr('href', 'slowdash-' + theme + '.css');
        })
            .catch(e => {
                $('<div>').appendTo($('body')).html(`
                    <h3>Theme-CSS Loading Error</h3>
                    Name: slowdash-${theme}.css<br>
                    Error: ${e.message}
                `);
            })
            .then((x) => {
                start(params);
            });
    }


    function start(params) {
        let config = $.extend(true, {}, params.defaults, params.page_config, params.args);
        setTimeout(()=>{setupDataList();}, 3000);
        params.start_func(config);
    }

    initiate(params);
}


function setupDataList() {
    let ts_datalist = $('<datalist>').attr('id', 'sd-timeseries-datalist').appendTo(document.body);
    let table_datalist = $('<datalist>').attr('id', 'sd-table-datalist').appendTo(document.body);
    let tree_datalist = $('<datalist>').attr('id', 'sd-tree-datalist').appendTo(document.body);
    let blob_datalist = $('<datalist>').attr('id', 'sd-blob-datalist').appendTo(document.body);
    let hist_datalist = $('<datalist>').attr('id', 'sd-histogram-datalist').appendTo(document.body);
    let hist2d_datalist = $('<datalist>').attr('id', 'sd-histogram2d-datalist').appendTo(document.body);
    let graph_datalist = $('<datalist>').attr('id', 'sd-graph-datalist').appendTo(document.body);
    let histgraph_datalist = $('<datalist>').attr('id', 'sd-histgraph-datalist').appendTo(document.body);
    let all_datalist = $('<datalist>').attr('id', 'sd-all-datalist').appendTo(document.body);
    
    fetch('api/channels?fields=name')
        .then(response => {
            if (response.ok) return response.json();
        })
        .then(record => {
            if (! record || Object.keys(record).length == 0) {
                return;
            }
            for (let entry of record) {
                if (! entry.name) {
                    continue;
                }
                all_datalist.append($('<option>').attr('value', entry.name).text(entry.name));
                if (((entry.type??'') == '') || (entry.type == 'timeseries')) {
                    ts_datalist.append($('<option>').attr('value', entry.name).text(entry.name));
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
        });

    fetch('./api/config/list')
        .then(response => {
            if (response.ok) return response.json();
        })
        .then(config => {
            let dashboard_dl = $('<datalist>').attr('id', 'sd-dashboard-datalist').appendTo(document.body);
            for (let entry of config.contents?.slowdash_config ?? []) {
                dashboard_dl.append($('<option>').attr('value', entry.name).text(entry.name));
            }
            let map_dl = $('<datalist>').attr('id', 'sd-map-datalist').appendTo(document.body);
            for (let entry of config.contents?.map_config ?? []) {
                map_dl.append($('<option>').attr('value', entry.name).text(entry.name));
            }
            let html_dl = $('<datalist>').attr('id', 'sd-html-datalist').appendTo(document.body);
            for (let entry of config.contents?.html_config ?? []) {
                html_dl.append($('<option>').attr('value', entry.name).text(entry.name));
            }
        });    
}


export function upload(dialog, filename, content, options={}) {
    const defaults = {
        contentType: 'text/plain',
        overwritable: false,
        quietOnSuccess: false,
        on_success: () => {},
        on_cancel: () => {},
        on_error: (e) => {},
    };
    let opts = $.extend({}, defaults, options);
    
    let url = './api/' + filename;
    if (opts.overwritable) {
        url += '?overwrite=yes';
    }

    let headers = {};
    if (opts.contentType) {
        headers['Content-Type'] = opts.contentType;
    }
    
    fetch(url, {
        method: 'POST',
        headers: headers,
        body: content,
    })
        .then(response => {
            if (response.status == 202) {
                dialog.html(`
                    <h3>File already exists. Overwrite?</h3>
                    <h4>${filename}</h4>
                    <div class="jaga-dialog-button-pane"><button>Yes</button><button>No</button></div>
                `);
                dialog.find('button').at(0).click(e=>{
                    dialog.get().close();
                    opts.overwritable = true;
                    upload(dialog, filename, content, opts);
                });
                dialog.find('button').at(1).click(e=>{
                    dialog.get().close();
                    opts.on_cancel();
                });
                dialog.get().showModal();
                return;
            }
            if (! response.ok) {
                throw new Error(response.status + " " + response.statusText);
            }
            if (! options.quietOnSuccess) {
                dialog.html(`
                    <h3>File uploaded</h3>
                    <h4>${filename}</h4>
                    <div class="jaga-dialog-button-pane"><button>Ok</button></div>
                `);
                dialog.find('button').at(0).click(e=>{
                    dialog.get().close();
                    opts.on_success();
                });
                dialog.get().showModal();
            }
            else {
                opts.on_success();
            }
        })
        .catch(e => {
            dialog.html(`
                <h3>File uploading Failed</h3>
                <h4>${filename}</h4>
                ${e.message}
                <div class="jaga-dialog-button-pane"><button>Close</button></div>
            `);
            dialog.find('button').at(0).click(e=>{
                dialog.get().close();
                opts.on_error(e);
            });
            dialog.get().showModal();
        });
}



function lengthString(lapse, shortForm=true, transform=x=>parseFloat(x.toFixed(1))) {
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


export class Frame {
    constructor(obj, options={}) {
        const defaults = {
            title: "SlowDash",
            initialStatus: "loading...",
            initialBeat: "",
            style: {
                theme: 'light',
                title: {
                    background: undefined,
                    color: undefined,
                },
                logo: {
                    file: undefined,
                    background: undefined,
                    position: 'left',
                    link: undefined,
                },
            },
            reloadInterval: 0,
            reloadIntervalSelection: [ 0, -1, 2, 5, 10, 30, 60, 5*60, 15*60, 30*60, 60*60 ],
            reloadIntervalChange: function(interval) {},
            reload: function(on_complete) {},
            resetDelay: 0
        };
        this.obj = obj;
        this.options = $.extend(true, {}, defaults, options);

        const style = {
            headerDiv: {
                "display": "flex",
                "margin": "0",
                "padding": "0",
                "border": "none",
            },
            leftDiv: { "margin": "5px" },
            rightDiv: { "margin": "5px 10px 5px auto" },
            leftLogoDiv: { 'width': '0%', 'overflow': 'hidden', 'margin': '0 5px 0 0', 'padding': 0 },
            rightLogoDiv: { 'width': '0%', 'overflow': 'hidden', 'margin': '0 0 0 5px', 'padding': 0 },
            
            titleDiv: { "font-size": "1.4vw" },
            clockDiv: { "font-size": "1vw" },
            controlDiv: { "margin-top": "5px" },
            selectSpan: {},
            select: { "font-size": "1vw", "margin-right": "5px", "padding": "3px", "border-radius": "7px" },
            statusSpan: { "font-size": "1vw", 'margin-right': "0.5vw" },
            beatSpan: { "font-size": "0.7vw", "margin-right": "0.5vw" },
            buttonDiv: { "margin-top": "5px", "display": "flex" },
            button: { "font-size": "1.2vw", "margin-left": "5px" }
        };
        
        let headerDiv = this.obj.addClass('sd-header').css(style.headerDiv);
        let leftLogoDiv = $('<div>').css(style.leftLogoDiv).appendTo(headerDiv);
        let leftDiv = $('<div>').css(style.leftDiv).appendTo(headerDiv);
        let rightDiv = $('<div>').css(style.rightDiv).appendTo(headerDiv);
        let rightLogoDiv = $('<div>').css(style.rightLogoDiv).appendTo(headerDiv);
        
        let titleDiv = $('<div>').css(style.titleDiv).appendTo(leftDiv);
        let controlDiv = $('<div>').css(style.controlDiv).appendTo(leftDiv);
        this.selectSpan = $('<span>').css(style.selectSpan).appendTo(controlDiv);
        this.statusSpan = $('<span>').css(style.statusSpan).appendTo(controlDiv);
        this.beatSpan = $('<span>').css(style.beatSpan).appendTo(controlDiv);
        this.clockDiv = $('<div>').css(style.clockDiv).appendTo(rightDiv);
        this.buttonDiv = $('<div>').css(style.buttonDiv).appendTo(rightDiv);
        this.style = style;

        const titleBackground = this.options.style.title?.background ?? this.options.style.title_color;
        const titleColor = this.options.style.title?.color ?? this.options.style.title_text_color;
        if (titleBackground) {
            headerDiv.css('background', titleBackground);
        }
        if (titleColor) {
            headerDiv.css('color', titleColor);
        }
        // otherwise from theme
        
        titleDiv.text(this.options.title);
        this.statusSpan.text(this.options.initialStatus);
        this.beatSpan.text(this.options.initialBeat);
        this.clockDiv.text((new JGDateTime()).asString('%a, %b %d %H:%M %Z'));
        
        this.reloadInterval = this.options.reloadInterval;
        if (this.options.reloadIntervalSelection?.length ?? 0 > 0) {
            let heading = '&#x1f680; ';
            let pulldownItems = [];
            for (let interval of this.options.reloadIntervalSelection) {
                let value = parseInt(interval);
                let label = 'Every ' + lengthString(interval, false);
                if (value < 0) {
                    label = 'Auto Reload Off';
                }
                else if (value == 0) {
                    label = 'Reload Now';
                }
                pulldownItems.push({ value: value, label: label });
            }
            function setReloadLabel(obj, length) {
                if (length > 0) {
                    obj.setLabel(heading + ' Every ' + lengthString(length));
                }
                else {
                    obj.setLabel(heading + ' Auto Reload Off');
                }
            }
            let reloadSel = $('<select>').css(style.select).prependTo(this.selectSpan);
            this.reloadPulldown = new JGPullDownWidget(reloadSel, {
                heading: heading,
                items: pulldownItems,
                initial: 0,
                select: (event, value, obj) => {
                    let length = parseFloat(value);
                    if (length == 0) {
                        this.update();
                        setReloadLabel(this.reloadPulldown, this.reloadInterval);
                    }
                    else if (length < 0) {
                        this.reloadInterval = 0;
                        this.reloadPulldown.setLabel(heading + 'Auto Reload Off');
                        this.options.reloadIntervalChange(this.reloadInterval);
                    }
                    else {
                        this.reloadInterval = length;
                        this.options.reloadIntervalChange(this.reloadInterval);
                    }
                    this.suspendUntil = 0;
                    this.scheduleReset();
                }
            });
            setReloadLabel(this.reloadPulldown, this.reloadInterval);
        }

        if (this.options.style.logo?.file) {
            const file = './api/config/file/' + this.options.style.logo.file;
            const img = $('<img>').attr('src', file).css({'width': '100%', 'border': 'none'});
            const size = getComputedStyle(headerDiv.get()).height;
            let div = (this.options.style.logo?.position ?? 'left') == 'right' ? rightLogoDiv : leftLogoDiv;
            div.css({'width': size, 'height': size}).append(img);
            if (this.options.style.logo?.background) {
                div.css('background', this.options.style.logo?.background);
            }
            if (this.options.style.logo?.link) {
                div.css('cursor', 'pointer').bind('click', e=>{
                    window.open(this.options.style.logo?.link);
                });
            }
        }
    }
    
    prependSelect(select) {
        select.css(this.style.select).prependTo(this.selectSpan);
    }
    
    appendSelect(select) {
        select.css(this.style.select).appendTo(this.selectSpan);
    }
    
    appendButton(button) {
        button.css(this.style.button).appendTo(this.buttonDiv);
    }

    start() {
        this.lastUpdateTime = 0;
        this.currentUpdateTime = 0;
        this.pendingRequests = 0;
        this.suspendUntil = 0;
        this.resetAt = 0;
        this._beat();
    }
    
    suspend(len) {
        this.suspendUntil = $.time() + len;
    }
    
    scheduleReset() {
        if (this.options.resetDelay > 0) {
            this.resetAt = $.time() + this.options.resetDelay;
        }
    }
    
    update() {            
        let now = $.time();
        if (now - this.currentUpdateTime < 60) {
            this.pendingRequests++;
            return;
        }
        this.lastUpdateTime = now;
        this.currentUpdateTime = now;
        this.pendingRequests = 0;
        this.suspendUntil = 0;
        
        this.options.reload(status => {
            this.currentUpdateTime = 0;
            if (status == null) {
                let date = (new JGDateTime(this.lastUpdateTime)).asString('%a, %b %d %H:%M');
                status = 'Update: ' + date;
            }
            this.statusSpan.text(status);
        });
    }

    setStatus(text) {
        this.statusSpan.html(text);
    }
    
    _beat() {
        const now = $.time();
        if ((this.resetAt > 0) && (now > this.resetAt)) {
            window.location.reload(false);
        }
        
        this.clockDiv.text((new JGDateTime(now)).asString('%a, %b %d %H:%M %Z'));

        let lapse = now - this.lastUpdateTime;
        let suspend = this.suspendUntil - now;
        let togo = (this.reloadInterval > 0 ? this.reloadInterval - lapse : 1e10);
        if ((this.lastUpdateTime == 0) || (this.pendingRequests > 0)) {
            togo = 0;
        }
        if (suspend > togo) {
            togo = suspend;
        }

        let text;
        if (this.lastUpdateTime == 0) {
            text = 'initial loading';
        }
        else {
            text = lengthString(lapse, false, parseInt) + ' ago';
        }
        if (this.currentUpdateTime > 0) {
            text += ', receiving data... ' + parseInt(now - this.currentUpdateTime) + ' s';
        }
        else {
            if (suspend >= togo-1) {
                text += ', update suspended for next ' + parseInt(togo) + ' s';
            }
            else if (
                ((this.reloadInterval > 60) && (togo < 10)) ||
                    ((this.reloadInterval > 1800) && (togo < 60))
            ){
                text += ', reload in ' + parseInt(togo) + ' s';
            }
        }
        this.beatSpan.text('(' + text + ')');
        
        if (togo <= 0) {
            this.update();
        }
        setTimeout(()=>{this._beat();}, 1000);
    }
};



class TimeDialog {
    constructor(obj, options={}) {
        const defaults = {
            title: 'Data Time',
            apply: (time) => {},
            cancel: () => {},
        };
        this.obj = obj;
        this.options = $.extend(true, {}, defaults, options);

        this.dialog = new JGDialogWidget(this.obj, {
            title: this.options.title,
            buttons: {
                'Apply': e=> {
                    let time = this.apply();
                    this.options.apply(time);
                },
                'Cancel': e=> {
                    this.options.cancel();
                },
            }
        });
    }

    open(time) {
        let div = this.obj.find('.jaga-dialog-content');
        div.html(`
            <div class="jaga-dialog-content" style="margin:1em">
              <input type="datetime-local">
            </div>
        `);
        let date = new JGDateTime(time > 0 ? time : $.time()).asString('%Y-%m-%dT%H:%M');
        div.find('input').at(0).val(date);

        this.dialog.open();
    }

    apply() {
        let div = this.obj.find('.jaga-dialog-content');
        let time = parseFloat(new JGDateTime(new Date(div.find('input').at(0).val())).asInt());
        return time;
    }
};


class TimeRangeDialog {
    constructor(obj, options={}) {
        const defaults = {
            title: 'Data Time Range',
            apply: (length, to) => {},
            close: () => {},
        };
        this.obj = obj;
        this.options = $.extend(true, {}, defaults, options);

        this.dialog = new JGDialogWidget(this.obj, {
            title: this.options.title,
            close: this.options.close,
            buttons: {
                'Apply': e=> {
                    let range = this.apply();
                    this.options.apply(range);
                },
                'Cancel': e=> {
                    this.options.close();
                },
            }
        });
    }

    open(length, to=null) {
        let div = this.obj.find('.jaga-dialog-content');
        div.html(`
            <div class="jaga-dialog-content" style="margin:1em">
            <table>
              <tr><th align="left">From</th><th align="left">To</th></tr>
              <tr><td>
                <label><input type="radio" name="fromtype"> <input type="number" step="any" style="width:5em">
                <select>
                  <option value="s">sec</option>
                  <option value="m">min</option>
                  <option value="h">hours</option>
                  <option value="d">days</option>
                </select> before</label>
              </td><td>
                <label><input type="radio" name="totype"> current time</label>
              </td></tr>
              <tr><td>
                <label><input type="radio" name="fromtype"> <input type="datetime-local"></label>
              </td><td>
                <label><input type="radio" name="totype"> <input type="datetime-local"></label>
              </td></tr>
            </table>
            </div>
        `);
        let now = $.time();
        let to_date = new JGDateTime(to ?? now).asString('%Y-%m-%dT%H:%M');
        let from_date = new JGDateTime((to ?? now)-length).asString('%Y-%m-%dT%H:%M');

        let unit = 's';
        if (length >= 2*86400) { length /= 86400.0; unit = 'd'; }
        else if (length >= 2*3600) { length /= 3600.0; unit = 'h'; }
        else if (length >= 60) { length /= 60.0; unit = 'm'; }
        
        div.find('input').at(0).checked(to === null);
        div.find('input').at(1).val(length).bind('focus', e=>{
            div.find('input').at(0).checked(true);
            div.find('input').at(1).get().select();
        });
        div.find('select').at(0).val(unit);
        div.find('input').at(2).checked(to === null);
        div.find('input').at(3).checked(to !== null);
        div.find('input').at(4).val(from_date).bind('focus', e=>{div.find('input').at(3).checked(true);});
        div.find('input').at(5).checked(to !== null);
        div.find('input').at(6).val(to_date).bind('focus', e=>{div.find('input').at(5).checked(true);});
        
        this.dialog.open();
    }

    apply() {
        let div = this.obj.find('.jaga-dialog-content');
        let isByLength = div.find('input').at(0).checked();
        let isToCurrent = div.find('input').at(2).checked();
        let to = isToCurrent ? null : parseFloat(new JGDateTime(new Date(div.find('input').at(6).val())).asInt());
        if (! (to > 0)) {
            to = null;
        }
        if (isByLength) {
            let length = parseFloat(div.find('input').at(1).val());
            let unit = div.find('select').at(0).val();
            if (! (length > 0)) { length = 3600; unit = 's'; }
            if (unit == 'm') length *= 60;
            else if (unit == 'h') length *= 3600;
            else if (unit == 'd') length *= 86400;
            return { length: length, to: to };
        }
        else {
            let from = parseFloat(new JGDateTime(new Date(div.find('input').at(4).val())).asInt());
            let length = (to||$.time()) - from;
            if (! (length > 0)) length = 3600;
            return { length: length, to: to };
        }
    }
};


class GridDialog {
    constructor(obj, options={}) {
        const defaults = {
            title: 'Grid Layout',
            apply: (grid) => {},
            cancel: () => {},
        };
        this.obj = obj;
        this.options = $.extend(true, {}, defaults, options);

        this.dialog = new JGDialogWidget(this.obj, {
            title: this.options.title,
            buttons: {
                'Apply': e=> { this.options.apply(this.apply()); },
                'Cancel': e=> { this.options.cancel(); },
            }
        });
    }

    open(initialValue) {
        let div = this.obj.find('.jaga-dialog-content');
        div.html(`
            <div class="jaga-dialog-content" style="margin:1em">
              Rows: <input type="number" min="1" max="8" step="1" style="width:10ex"> x
              Columns: <input type="number" min="1" max="8" step="1" style="width:10ex">
            </div>
        `);
        let [rows, cols] = initialValue.split('x');
        div.find('input').at(0).val(rows);
        div.find('input').at(1).val(cols);
        
        this.dialog.open();
    }

    apply() {
        let div = this.obj.find('.jaga-dialog-content');
        return parseFloat(div.find('input').at(0).val()) + "x" + parseInt(div.find('input').at(1).val());
    }
};


export class TimePullDown {
    constructor(obj, options={}) {
        const defaults = {
            items: [
                0, 3*3600, 8*3600, 86400, 7*86400, 30*86400, 90*86400, -1
            ],
            heading: '&#x1f558; ',
            initial: 0,
            select: (time) => {},
        };
        this.obj = obj;
        this.options = $.extend(true, {}, defaults, options);
        this.lastValue = 0;

        this.dialogDiv = $('<div>').css({color:'black'}).appendTo(obj.closest('div'));
        this.dialog = new TimeDialog(this.dialogDiv, {
            title: 'Data Time',
            apply: time => {
                let date = (new JGDateTime(time)).asString('%Y-%m-%d, %H:%M:%S');
                this.pulldown.setLabel(this.options.heading + date);
                this.options.select(time);
                this.lastValue = time;
            },
            cancel: () => {
                if (this.lastValue == 0) {
                    this.pulldown.setLabel(this.options.heading + 'Current');
                }
                else {
                    let date = (new JGDateTime(this.lastValue)).asString('%Y-%m-%d, %H:%M:%S');
                    this.pulldown.setLabel(this.options.heading + date);
                }
            }
        });
        
        let items = [];
        for (let value of this.options.items) {
            if (value > 0) {
                items.push({value: value, label: lengthString(value, false) + ' ago'});
            }
            else if (value === 0) {
                items.push({value: 0, label: 'Current'});
            }
            else if (value < 0) {
                items.push({value: -1, label: 'Other...'});
            }
        }

        this.pulldown = new JGPullDownWidget(this.obj, {
            heading: this.options.heading,
            items: items,
            initial: 0,
            select: (event, value, obj) => {
                let past = parseFloat(value);
                if (past > 0) {
                    let time = $.time() - past;
                    let date = (new JGDateTime(time)).asString('%Y-%m-%d, %H:%M:%S');
                    this.pulldown.setLabel(this.options.heading + date);
                    this.options.select(time);
                    this.lastValue = time;
                }
                else if (past === 0) {
                    this.options.select(0);
                    this.lastValue = 0;
                }
                else if (past < 0) {
                    this.dialog.open(this.lastValue);
                }
            }
        });
    }
    
    set(time) {
        if (time > 0) {
            let date = (new JGDateTime(time)).asString('%Y-%m-%d, %H:%M:%S');
            this.pulldown.setLabel(this.options.heading + date);
        }
        this.lastValue = time;
    }        
};


export class TimeRangePullDown {
    constructor(obj, options={}) {
        const defaults = {
            items: [
                300, 900, 1800, 3600, 10800, 21600, 43200, 86400,
                259200, 604800, 2592000, 7776000,
                0
            ],
            custom_items: [],
            heading: '&#x1f558; ',
            initial: 3600,
            select: (from, to) => {},
            select_custom_item: (key) => {},
        };
        this.obj = obj;
        this.options = $.extend(true, {}, defaults, options);

        this.range = { length: parseFloat(this.options.initial), to: null };
        
        this.dialogDiv = $('<div>').css({color:'black'}).appendTo(obj.closest('div'));
        this.dialog = new TimeRangeDialog(this.dialogDiv, {
            title: 'Data Time Range',
            apply: range => {
                console.log("APPLY");
                this.range = range;
                this.options.select(this.range.length, this.range.to);
            },
            close: () => {
                this.pulldown.setLabel(this._getRangeLabel());
            }
        });
        
        let items = [];
        for (let value of this.options.custom_items) {
            items.push({value: value, label: value});
        }
        for (let value of this.options.items) {
            if (typeof value != 'number') {
                items.push({value: value, label: value});
            }
            else if (value > 0) {
                items.push({value: value, label: 'Last ' + lengthString(value, false)});
            }
            else if (value == 0) {
                items.push({value: 0, label: 'Other...'});
            }
        }
        this.pulldown = new JGPullDownWidget(this.obj, {
            heading: this.options.heading,
            items: items,
            initial: 0,
            select: (event, value, obj) => {
                let length = parseFloat(value);
                if (length > 0) {
                    this.range.length = length;
                    this.range.to = null;
                    this.options.select(this.range.length, null);
                }
                else if (length === 0) {
                    this.dialog.open(this.range.length, this.range.to);
                }
                else {
                    this.options.select_custom_item(value);
                }
            }
        });
        this.pulldown.setLabel(this._getRangeLabel());
    }

    set(length, to=null) {
        this.range.length = length;
        this.range.to = to;
        this.pulldown.setLabel(this._getRangeLabel());
    }
        
    _getRangeLabel() {
        if (! (this.range.length > 0)) {
            return this.options.heading + 'Undefined';
        }
        if (this.range.to === null) {
            return this.options.heading + 'Last ' + lengthString(this.range.length, false);
        }
        let dateFormat = (this.range.length < 90*86400) ? '%b%d,%H:%M' : '%b%d,%Y';
        return (
            this.options.heading +
            (new JGDateTime(this.range.to - this.range.length).asString(dateFormat)) +
            ' - ' +
            (new JGDateTime(this.range.to).asString(dateFormat))
        );
    }
};


export class GridPullDown {
    constructor(obj, options={}) {
        const defaults = {
            heading: '&#x1f4c8; ',
            items: [ '1x1', '2x2', '3x3', '2x1', '3x1', '4x1', 'Other...' ],
            initial: 0,
            select: (grid) => {},
        };
        this.obj = obj;
        this.options = $.extend(true, {}, defaults, options);
        this.lastValue = '1x1';

        this.dialogDiv = $('<div>').css({color:'black'}).appendTo(obj.closest('div'));
        this.dialog = new GridDialog(this.dialogDiv, {
            title: 'Grid Layout',
            apply: grid => {
                this.pulldown.setLabel(this.options.heading + grid);
                this.options.select(grid);
                this.lastValue = grid;
            },
            cancel: () => {
                this.pulldown.setLabel(this.options.heading + this.lastValue);
            }
        });
        
        this.pulldown = new JGPullDownWidget(this.obj, {
            heading: this.options.heading,
            items: this.options.items,
            initial: this.options.initial,
            select: (event, value, obj) => {
                if (value == 'Other...') {
                    this.dialog.open(this.lastValue);
                }
                else {
                    this.options.select(value);
                    this.lastValue = value;
                }
            }
        });
    }
    
    set(grid) {
        this.pulldown.setLabel(this.options.heading + grid);
        this.lastValue = grid;
    }        
};



export class SaveConfigDialog {
    constructor(obj, options={}) {
        const defaults = {
            title: 'Save Configuration',
            saveConfig: (name, doc) => {}
        };
        this.obj = obj;
        this.options = $.extend(true, {}, defaults, options);

        this.dialog = new JGDialogWidget(this.obj, {
            title: this.options.title,
            y: 50,
        });
    }

    open(config) {
        let div = this.obj.find('.jaga-dialog-content');
        div.html(`
            <table style="margin-top:1em;margin-left:1em">
              <tr><td>Name</td><td><input pattern="^[a-zA-Z][a-zA-Z0-9_\\-]*$" required="true" placeholder="use only alphabets or digits, do not use space" style="width:30em"></td></tr>
              <tr><td>Title</td><td><input placeholder="optional" style="width:30em"></td></tr>
              <tr><td>Description</td><td><textarea rows="3" cols="60" placeholder="optional"></textarea></td></tr>
              <tr><td>---</td><td></td></tr>
              <tr><td>Control Mode</td><td>
                <label><input type="radio" name="mode" value="normal" checked>Normal</label>
              </td></tr>
              <tr><td></td><td>
                <label><input type="radio" name="mode" value="protedted">Protected
                <span font-size="60%">(layout cannot be modified)</span></label>
              </td></tr>
              <tr><td></td><td>
                <label><input type="radio" name="mode" value="display">Display
                <span font-size="60%">(no interaction, simple header)</span></label>
              </td></tr>
            </table>
            <div style="display:flex;justify-content:flex-end;padding-right:10px;margin:1em" class="jaga-dialog-button-pane">
                <button>Save &amp; Reload</button><button>Cancel</button>
            </div>
            <hr>
            <details>
              <summary>See the content</summary>
              <textarea rows="30" style="width:calc(100% - 10px)" autocomplete="off" spellcheck="false" wrap="off">
            </details>
        `);

        let orgName = '';
        let validNamePattern = new RegExp('^[a-zA-Z0-9][a-zA-Z0-9_\\-]*$');
        if (config.meta?.name?.length>0 && validNamePattern.test(config.meta?.name)) {
            orgName = config.meta.name;
        }
        else {
            orgName = '';
        }
        let prevName = orgName;

        let record = JSON.parse(JSON.stringify(config));
        for (let key in record) {
            if ((key.length > 0) && ((key[0] == '_') || (key == 'meta'))) {
                delete record[key];
            }
        }
        
        div.find('input').at(0).val(prevName);
        div.find('input').at(1).val(config.meta?.title ?? '');
        div.find('textarea').at(0).val(config.meta?.description ?? '');
        div.find('textarea').at(1).val($.JSON_stringify(record, {expandAll:false}));
        if (div.find('input').at(0).val().length == 0) {
            div.find('button').at(0).enabled(false);
        }
            
        // name input
        div.find('input').at(0).bind('input', e=>{
            let name = $(e.target).val();
            if (validNamePattern.test(name) || name == '') {
                prevName = name;
            }
            else {
                $(e.target).val(prevName);
            }
            div.find('button').at(0).enabled(e.target.validity.valid);
        });
        
        // buttons
        div.find('button').bind('click', e=>{
            const cmd = $(e.target).closest('button').text();
            if (cmd == "Cancel") {
                this.dialog.close();
                return;
            }
            
            if (config.meta === undefined) {
                config.meta = {};
            }
            config.meta.name = div.find('input').at(0).val();
            config.meta.title = div.find('input').at(1).val();
            config.meta.description = div.find('textarea').at(0).val();
            
            let updated_config = JSON.parse(div.find('textarea').at(1).val());
            if (updated_config.meta === undefined) {
                updated_config.meta = {};
            }
            updated_config.meta.name = div.find('input').at(0).val();
            updated_config.meta.title = div.find('input').at(1).val();
            updated_config.meta.description = div.find('textarea').at(0).get().value;
            if (div.find('input').at(3).checked()) {
                updated_config.control.mode = 'protected';
            }
            else if (div.find('input').at(4).checked()) {
                updated_config.control.mode = 'display';
            }
            else {
                updated_config.control.mode = 'normal';
            }
            
            this.options.saveConfig(updated_config.meta.name, updated_config);
            
            this.dialog.close();
        });

        this.dialog.open();
    }
};

