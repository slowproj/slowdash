// panel-misc.mjs //
// Author: Sanshiro Enomoto <sanshiro@uw.edu> //
// Created on 24 July 2022 //

export { HtmlPanel as Panel1, HrefPanel as Panel2 };

 
import { JG as $ } from './jagaimo/jagaimo.mjs';
import { JGIndicatorWidget } from './jagaimo/jagawidgets.mjs';
import { Panel, bindInput } from './panel.mjs';
import { Transformer } from './transformer.mjs';


class HtmlPanel extends Panel {
    static describe() {
        return { type: 'html', label: 'HTML Form' };
    }
    
    static buildConstructRows(table, on_done=config=>{}) {
        let tr1 = $('<tr>').html(`
            <td>HTML File</td><td><input list="sd-html-datalist"></td>
       `).appendTo(table);
        let tr2 = $('<tr>').html(`
            <td style="padding-top:1em"><button hidden style="font-size:x-large">Create</button></td><td></td>
        `).appendTo(table);
        let button = tr2.find('button');
        tr1.find('input').bind('input', e=>{
            let input = $(e.target);
            if (input.val().length > 0) {
                button.show();
            }
            else {
                button.hide();
            }
        });
        button.bind('click', e=>{
            let config = {
                type: 'html',
                location: 'project',  // 'config' or 'system' (or 'external'?)
                file: table.find('input').val(),
                title: '',
            };
            on_done(config);
        });
    }

    
    constructor(div, style={}) {
        super(div, style);

        this.titleDiv = $('<div>').appendTo(div);
        this.frameDiv = $('<div>').appendTo(div);
        this.contentDiv = $('<div>').appendTo(this.frameDiv);

        this.titleDiv.css({
            'font-family': 'sans-serif',
            'font-size': '20px',
            'font-weight': 'normal',
            'margin': '0 10px 0 0',
            'white-space': 'nowrap',
            'overflow': 'hidden',
        });
        this.frameDiv.css({
            width:'calc(100% - 12px)',
            height:'calc(100% - 20px - 2em)',
            'margin-top': '10px',
            'margin-left': '10px',
            overflow:'hidden',
        });
        this.contentDiv.css({
            position: 'relative',
            width:'100%',
            height:'100%',
            margin: 0,
            padding:0,
            overflow:'auto',
        });

        this.indicator = new JGIndicatorWidget($('<div>').appendTo(div));
        this.variables = [];
    }

    
    async configure(config, options={}, callbacks={}) {
        await super.configure(config, options, callbacks);
        this.titleDiv.text(this.config.title ?? '');
        this.variables = [];

        const base = ((this.config.location??'') == 'system' ? './' : './api/config/content/');
        this.url = base + 'html-' + config.file;
        this.url += '?content_type=html';
    
        await this._loadPage();
    }


    openSettings(div) {
        let inputsDiv = $('<div>').appendTo(div);
        inputsDiv.html(`
            <table style="margin-top:1em">
              <tr><th>HTML File</th><td><input list="sd-html-datalist"></td></tr>
              <tr><th>Title</th><td><input></td></tr>
              <tr><th>Scaling</th><td><input type="number" step="any" placeholder="auto-scale"></td></tr>
              <tr><th>On Update</th><td><label><input type="checkbox">reload HTML</label></td></tr>
            </table>
        `);

        let k = 0;
        bindInput(this.config, 'file', inputsDiv.find('input').at(k++).css('width', '20em'));
        bindInput(this.config, 'title', inputsDiv.find('input').at(k++).css('width', '20em'));
        bindInput(this.config, 'scaling', inputsDiv.find('input').at(k++).css('width', '10em'));
        bindInput(this.config, 'reload', inputsDiv.find('input').at(k++));
    }


    fillInputChannels(inputChannels) {
        for (let variable of this.variables) {
            if (variable.channel && variable.waiting) {
                inputChannels.push(variable.channel);
            }
        }
    }

    
    draw(data, displayTimeRange=null) {
        if (this.config.reload ?? false) {
            this._loadPage().then(()=>{
                this._updateContents(data, displayTimeRange);
            });
        }
        else {
            this._updateContents(data, displayTimeRange);
        }
    }

    
    _adjustScaling() {
        let scaling = parseFloat(this.config.scaling ?? 0);
        if (! (scaling > 0)) {
            const div = this.contentDiv.get();
            const scaling_w = div.offsetWidth / div.scrollWidth;
            const scaling_h = div.offsetHeight / div.scrollHeight;
            scaling = Math.min(scaling_w, scaling_h);
            if (scaling < 0.6) {
                scaling = 0.6;
            }
        }
        if ((scaling > 0) && (Math.abs(scaling-1) > 0.01)) {
            this.contentDiv.css({
                width: 100/scaling + '%',
                height: 100/scaling + '%',
                transform: 'scale(' + scaling + ')',
                'transform-origin': '0 0',
            });
        }
    }

    
    async _loadPage() {
        const response = await fetch(this.url);
        if (! response.ok) {
            this.contentDiv.html(`
                <h3>HTML File Loading Error</h3>
                Name: ${this.config.file}<br>
                <p>
                URL: ${this.url}<br>
                Error: ${response.status} ${response.statusText}
            `);
            return null;
        }
        const html = await response.text();
        if (html) {
            this._render(html);  // everything will be rendered; injections, XSS, ..., are accepted by users risk
            this._adjustScaling();
        }
    }


    _render(html) {
        //...TODO: remove event handlers
        this.contentDiv.html(html);  // CSS in <head> works here

        this.variables = [];
        for (let type of [ 'sd-value', 'sd-enabled' ]) {
            for (let element of this.contentDiv.find(`[${type}]`).enumerate()) {
                const metric = element.attr(`${type}`);
                const isInput = (['INPUT', 'SELECT'].includes(element.get().tagName));
                let isLive = element.attr('sd-live');  // if not live, values are updated only after SUBMIT
                if ((isLive === undefined) || (isLive === null)) {
                    isLive = ! isInput;   // <input> is not live by default
                }
                this.variables.push($.extend(
                    {
                        type: type,
                        metric: metric,
                        live: !! isLive,
                        waiting: true,
                    },
                    Transformer.decompose(metric)
                ));
                if (isLive) {
                    element.bind('change', e=> {
                        const record = {};
                        record[metric] = { 'x': element.val() };
                        this.callbacks.publish('currentdata', record);
                    });
                }
            }
        }
        
        this.contentDiv.find('input[type="submit" i]').bind('click', e=>{
            e.preventDefault();
            this._submit($(e.target).attr('name'), $(e.target).closest('form'));
        });
        
        this.contentDiv.find('form').bind('submit', e=>{
            e.preventDefault();
        });
    }

    
    async _submit(submit_name, form) {
        let doc = {};
        if (submit_name) {
            doc[submit_name] = true
        }
        for (let input of form.find('input,select').enumerate()) {
            if ((input.attr('type') ?? '').toUpperCase() != 'SUBMIT') {
                const name = input.attr('name');
                if (name) {
                    doc[name] = input.val();
                }
            }
        }

        for (let variable of this.variables) {
            variable.waiting = true;
        }
        
        const url = './api/control';
        this.indicator.open("Sending Command...", "&#x23f3;", event?.clientX ?? null, event?.clientY ?? null);
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json; charset=utf-8' },
                body: JSON.stringify(doc, null, 2)
            });
            if (! response.ok) {
                throw new Error(response.status + ' ' + response.statusText);
            }
            const reply = await response.text();
            if (reply.length == 0) {
                throw new Error('empty response');
            }
            const reply_doc = JSON.parse(reply);
            if ((reply_doc.status ?? '').toUpperCase() == 'ERROR') {
                throw new Error(reply_doc.message ?? '');
            }
            this.indicator.close("Command Processed", "&#x2705;", 1000);
            
            this.callbacks.forceUpdate();
        }
        catch (e) {
            this.indicator.close("Command Failed: " + e.message, "&#x274c;", 5000);
            console.error("Command Failed: " + e.message);
        }
    }
    
    
    _updateContents(dataPacket, displayTimeRange) {
        let values = {};
        for (let variable of this.variables) {
            if (! variable.waiting) {
                continue;
            }
            let data = null;
            if (variable.channel) {
                if (variable.channel in dataPacket) {
                    data = dataPacket[variable.channel];
                }
                else if (dataPacket.__meta?.isPartial || false) {
                    continue;
                }
            }
            if (! variable.live) {
                variable.waiting = false;
            }

            let value = data?.x ?? null;
            if (value) {
                if (variable.transform) {
                    value = variable.transform.apply(value);
                }
                values[variable.metric] = value;
            }
        }
        
        for (let type of [ 'sd-value', 'sd-enabled' ]) {
            for (let element of this.contentDiv.find(`[${type}]`).enumerate()) {
                const metric = element.attr(`${type}`);
                if (! (metric in values)) {
                    continue;
                }
                const value = values[metric];
                if (type == 'sd-value') {
                    if (['INPUT', 'SELECT'].includes(element.get().tagName)) {
                        element.val(value);
                    }
                    else {
                        element.text(value);
                    }
                }
                else if (type == 'sd-enabled') {
                    element.enabled(value);
                }
            }
        }
    }
}



class HrefPanel extends Panel {
    static describe() {
        return { type: 'href', label: 'User/External Web Page' };
    }
    
    static buildConstructRows(table, on_done=config=>{}) {
        let tr1 = $('<tr>').html(`
            <td>URL</td><td><input style="width:30em"></td>
        `).appendTo(table);
        $('<tr>').html(`
            <td></td><td>For User-HTML, prepend "./userhtml/" before the HTML file name.</td>
        `).appendTo(table);
        $('<tr>').html(`
            <td></td><td>For external page, start with "https://".</td>
        `).appendTo(table);
        let tr2 = $('<tr>').html(`
            <td style="padding-top:1em"><button hidden style="font-size:x-large">Create</button></td><td></td>
        `).appendTo(table);

        let button = tr2.find('button');
        tr1.find('input').bind('input', e=>{
            let input = $(e.target);
            if (input.val().length > 0) {
                button.show();
            }
            else {
                button.hide();
            }
        });
        button.bind('click', e=>{
            let config = {
                type: 'href',
                title: '',
                url: table.find('input').val(),
                reload: true,
                query_range: false,
                scaling: null,
                offset_top: 0,
                offset_left: 0,
            };
            on_done(config);
        });
    }

    
    constructor(div, style={}) {
        super(div, style);
        this.titleDiv = $('<div>').appendTo(div);
        this.contentDiv = $('<div>').appendTo(div);        
        this.iframe = $('<iframe>').appendTo(this.contentDiv);

        this.titleDiv.css({
            'font-family': 'sans-serif',
            'font-size': '20px',
            'font-weight': 'normal',
            'margin': '0',
            'margin-bottom': '10px',
            'white-space': 'nowrap',
            'overflow': 'hidden',
        });
        this.contentDiv.css({
            position: 'relative',
            width:'calc(100% - 12px)',
            height:'calc(100% - 20px - 2em)',
            'margin-top': '10px',
            'margin-left': '10px',
            padding:0,
            overflow:'hidden',
        });
        this.iframe.css({
            position: 'relative',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            border: 'none',
            overflow:'auto',
        });
    }

    
    async configure(config, options={}, callbacks={}) {
        await super.configure(config, options, callbacks);
        this.titleDiv.text(this.config.title ?? '');
        
        this.iframe.bind('load', e=>{
            let scaling = parseFloat(this.config.scaling);
            if (! (scaling > 0)) {
                try {
                    // this does not work for external sites
                    const contentBody = this.iframe.get().contentWindow.document.body;
                    const scaling_w = this.contentDiv.get().offsetWidth / contentBody.scrollWidth;
                    const scaling_h = this.contentDiv.get().offsetHeight / contentBody.scrollHeight;
                    scaling = Math.min(scaling_w, scaling_h);
                }
                catch (error) {
                    const scaling_w = this.contentDiv.get().offsetWidth / document.documentElement.clientWidth;
                    const scaling_h = this.contentDiv.get().offsetHeight / document.documentElement.clientHeight;
                    scaling = Math.min(scaling_w, scaling_h);
                }
            }
            if ((scaling > 0) && (Math.abs(scaling-1) > 0.01)) {
                this.iframe.css({
                    width: 100/scaling + '%',
                    height: 100/scaling + '%',
                    transform: 'scale(' + scaling + ')',
                    'transform-origin': '0 0',
                });
            }

            // this does not work for external sites
            const top = parseFloat(this.config.offset_top ?? 0);
            const left = parseFloat(this.config.offset_left ?? 0);
            if ((top > 0) || (left > 0)) {
                try {
                    this.iframe.get().contentWindow.scrollTo(top, left);
                }
                catch (error) {
                    console.log(error);
                }
            }
        });
    }

    
    addControlButtons(div) {
        super.addControlButtons(div);
        let openBtn = $('<button>').html('&#x1f517;').prependTo(div);
        openBtn.attr('title', 'Open').bind('click', e=>{
            window.open(this.iframe.attr('src'));
        });
    }
        
        
    openSettings(div) {
        let inputsDiv = $('<div>').appendTo(div);
        inputsDiv.html(`
            <table style="margin-top:1em">
              <tr><th>Title</th><td><input></td></tr>
              <tr><th>URL</th><td><input></td></tr>
              <tr><th>Reload</th><td><label><input type="checkbox">Reload the page on data update</label></td></tr>
              <tr><th></th><td><label><input type="checkbox">Append time range parameters to URL</label></td></tr>
              <tr><th>Scaling</th><td><input placeholder="auto-scale"></td></tr>
              <tr><th>Offset</th><td>Top: <input> px, Left: <input> px</td></tr>
            </table>
            <p>
            <div font="small">
               <ul>
                 <li>For User-HTML page, prepend "./api/userhtml/" before the file name.
                 <li>For external page, start with "https://".
                 <li>Auto-scale and Offset do not work for external pages.
               </ul>
            </div>
        `);

        let k = 0;
        bindInput(this.config, 'title', inputsDiv.find('input').at(k++).css('width', '30em'));
        bindInput(this.config, 'url', inputsDiv.find('input').at(k++).css('width', '30em'));
        bindInput(this.config, 'reload', inputsDiv.find('input').at(k++));
        bindInput(this.config, 'query_range', inputsDiv.find('input').at(k++));
        bindInput(this.config, 'scaling', inputsDiv.find('input').at(k++).css('width', '10em'));
        bindInput(this.config, 'offset_top', inputsDiv.find('input').at(k++).css('width', '7em'));
        bindInput(this.config, 'offset_left', inputsDiv.find('input').at(k++).css('width', '7em'));
    }

    
    draw(data, displayTimeRange=null) {
        if ((this.config.reload === false) && this.iframe.attr('src')) {
            return;
        }
        if (data && (data?.__meta?.isPartial ?? false)) {
            return;
        }

        let this_url = this.config.url;
        if (this.config.query_range === true) {
            const range = this._findDataTimeRange(data, displayTimeRange);
            if (this_url.indexOf('?') > 0) {
                this_url += '&';
            }
            else {
                this_url += '?';
            }
            this_url += `sd-from=${range.from}&sd-to=${range.to}`;
        }
        this.iframe.attr('src', this_url); // this will cause reloading
    }
}
