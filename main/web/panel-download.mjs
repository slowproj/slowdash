// panel-misc.mjs //
// Author: Sanshiro Enomoto <sanshiro@uw.edu> //
// Created on 24 July 2022 //

import { JG as $, JGDateTime } from './jagaimo/jagaimo.mjs';
import { JGIndicatorWidget } from './jagaimo/jagawidgets.mjs';
import { Panel, bindInput } from './panel.mjs';


export class DownloadPanel extends Panel {
    static describe() {
        return { type: 'download', label: '' };
    }
    
    static buildConstructRows(table, on_done=config=>{}) {
        let tr = $('<tr>').html(`
            <td style="padding-top:1em"><button hidden style="font-size:x-large">Create</button></td><td></td>
        `).appendTo(table);

        let button = tr.find('button');
        button.bind('click', e=>{
            let config = {
                use_utc: false,
                channels: []
            };
            on_done(config);
        });
    }

    
    constructor(div, style) {
        super(div, style);

        this.channelList = null;

        this.frameDiv = $('<div>').appendTo(div);
        this.titleDiv = $('<div>').appendTo(this.frameDiv).text("Data Download / Export");
        this.contentDiv = $('<div>').appendTo(this.frameDiv);
        this.indicator = new JGIndicatorWidget($('<div>').appendTo(div));

        this.frameDiv.css({
            width:'calc(100% - 44px)',
            height:'calc(100% - 44px)',
            margin: '10px',
            'margin-bottom': 0,
            padding:'10px',
            'padding-bottom': 0,
            border: 'thin solid',
            'border-radius': '5px',
            overflow:'auto',
        });
        this.titleDiv.css({
            'font-family': 'sans-serif',
            'font-size': '20px',
            'font-weight': 'normal',
            'margin': '0',
            'margin-bottom': '10px',
        });
        this.contentDiv.css({
            position: 'relative',
            width:'calc(100% - 5px)',
            height:'calc(100% - 3em)',
            margin: 0,
            padding:0,
            overflow:'visible',
        });
    }

    
    configure(config, callbacks={}, project_config=null) {
        super.configure(config, callbacks);

        this.channelList = null;
        if (project_config?.project?.name) {
            this.cachePath = `slowdash-${project_config.project.name}-ChannelList`;
        }
        else {
            this.cachePath = null;
        }
        if (this.cachePath) {
            const cacheTime = localStorage.getItem(this.cachePath + '-cachetime');
            if (parseFloat(cacheTime ?? 0) > $.time() - 3600) {
                let cachedDoc = localStorage.getItem(this.cachePath + '-doc');
                if (cachedDoc) {
                    this.channelList = JSON.parse(cachedDoc);
                }
            }
        }
        if (this.channelList !== null) {
            this.buildDownloadPanel(this.contentDiv, config);
        }
        else {
            fetch('api/channels')
                .then(response => {
                    if (response.ok) return response.json();
                })
                .then(record => {
                    this.channelList = record;
                    localStorage.setItem(this.cachePath + '-cachetime', $.time());
                    localStorage.setItem(this.cachePath + '-doc', JSON.stringify(record));
                    this.buildDownloadPanel(this.contentDiv, config);
                });
        }
    }


    openSettings(div) {
        let inputsDiv = $('<div>').appendTo(div);
        inputsDiv.html(`
            <table style="margin-top:1em">
              <tr><th>Default Timezone</th><td><label><input type="checkbox">Use UTC</label></td></tr>
            </table>
        `);

        let k = 0;
        bindInput(this.config, 'use_utc', inputsDiv.find('input').at(k++), false);
    }

    
    buildDownloadPanel(div, config) {
        const defaults = {
            use_utc: false,
            to: $.time(),
            length: 3600,
            resampling: '',
            resampling_unit: 's',
            resampling_reducer: 'mean',
            show_details: false,
        }
        let thisconfig = $.extend({}, defaults, config);
        if (! thisconfig.to || isNaN(parseInt(thisconfig.to))) {
            thisconfig.to = $.time();
        }
        else {
            thisconfig.to = parseInt(thisconfig.to);
        }
        if (! thisconfig.from || isNaN(parseInt(thisconfig.from))) {
            if (! thisconfig.length || isNaN(parseInt(thisconfig.length))) {
                thisconfig.length = 3600;
            }
            thisconfig.from = thisconfig.to - parseInt(thisconfig.length);
        }
        
        div.html(`
          <div style="display:flex;height:100%;width:calc(100% - 10px);">
            <div style="flex-grow:1;height:100%"></div>
            <div style="display:flex;flex-direction:column;height:100%;margin-left:5em;">
              <div></div>
              <div style="display:flex;margin-top:auto;">
                <div class="jaga-dialog-button-pane" style="margin-left:auto;"></div>
              </div>
            </div>
            <div style="display:flex;flex-direction:column;height:100%;margin-left:5em;">
              <div></div>
              <div style="display:flex;margin-top:auto;">
                <div class="jaga-dialog-button-pane" style="margin-left:auto;"></div>
              </div>
            </div>
            <div style="height:100%;width:100%"></div>
          </div>
        `);
        let channelDiv = div.find('div').at(1);
        let rangeDiv = div.find('div').at(3);
        let buttonDiv = div.find('div').at(5);
        let scriptDiv = div.find('div').at(7);
        let button2Div = div.find('div').at(9);
        channelDiv.html(`
          <span style="white-space:nowrap">Name: <input style="width:20em"></span><p>
          Channels: <br><span stle="white-space:nowrap"><input list="sd-all-datalist" style="width:auto"><button>Add</button> <button>Clear</button></span><br>
          <span style="font-size:small;margin-top:5px;white-space:nowrap">(can use wildcards; example: <span style="background:gainsboro">adc_ch*</span> )</span>
          <div style="flex-grow:1;width:100%;overflow:auto;border:thin dotted;border-radius:5px">
            <span style="font-size:large;color:gray">No Channels Selected</span>
            <table></table>
          </div>
        `);
        rangeDiv.html(`
          <table style="white-space:nowrap">
            <tr><td>From</td><td><input type="datetime-local"> (browser time)</td></tr>
            <tr><td>To</td><td><input type="datetime-local"> (browser time)</td></tr>
            <tr>
              <td>Resampling</td>
              <td>
                <input type="number" step="any" placeholder="auto" style="width:6em">
                <select>
                  <option value="s">sec</option>
                  <option value="m">min</option>
                  <option value="h">hours</option>
                  <option value="d">days</option>
                </select>, 
                <select>
                  <option value="last">last</option>
                  <option value="mean">mean</option>
                  <option value="median">median</option>
                  <option value="min">min</option>
                  <option value="max">max</option>
                  <option value="sum">sum</option>
                  <option value="std">std</option>
                  <option value="count">count</option>
                </select>
              </td>
            </tr>
            <tr><td>Data Timezone</td><td><label><input type="checkbox">UTC (otherwise server time)</label></td></tr>
          </table>
          <p>
          <div style="font-size:small;margin-left:1em">
            <details>
            <summary>Auto Resampling Behavior</summary>
            <ul style="margin-top:0">
              <li>If only one channel is selected, no resampling is applied for the "auto" setting.
            </ul>
            <b>CSV Table Format</b>
            <ul style="margin-top:0">
              <li>For the time points, the median data interval among the selected channels is used, where
              <br>for each channel, the median interval among data points of the channel is used.
              <li>Resampling is done within the DB queries whenever possible, but auto-resampling disables this.
              A non-auto resampling value might significantly improve the speed (especially for TSDBs).
            </ul>
            <b>JSON Format</b>
            <ul style="margin-top:0">
              <li>No resampling is applied for the "auto" setting.
            </ul>
            </details>
          <div>
        `);
        buttonDiv.html(`
          <button disabled>Download CSV</button>
          <button disabled>Download JSON</button>
          <a style="display:none"></a>
        `);
        scriptDiv.html(`
          <span style="font-size:120%">Plotting Script Generation (Experimental)</span>
          <ul>
            <li> To run the script, the SlowPy library must be installed.
                 See <a href="./docs/index.html#Installation" target="_blank">documentation</a> for installation procedures,
                 or use the <tt style="white-space:nowrap">slowpy-notebook</tt> container.<p>
            <li> This feature is experimental. The generated scripts might not be compatible with future releases of SlowDash.<p>
            <li> Time-axis plots (time-series) and XY plots (histograms, graphs, etc) cannot be mixed.<p>
            <li> <b>Jupyter is Disabled</b>: to enable the direct Jupyter link, the URL and token of a Jupyter process must be set in the SlowDash project configuration.
          </ul>
        `);
        button2Div.html(`
          <button disabled>Download Python</button>
          <button disabled>Download Notebook</button>
          <button disabled>Open Jupyter</button>
          <a style="display:none"></a>
        `);
        div.find('input').attr('autocomplete', 'off');

        if (config.show_details) {
            rangeDiv.find('details').get().open = true;
        }
        if (config.has_jupyter) {
            scriptDiv.find('li').last().css('display', 'none');
        }
        
        
        //// Channel List ////
        
        channelDiv.css('position', 'relative');
        let nameInput = channelDiv.find('input').at(0);
        let channelInput = channelDiv.find('input').at(1);
        let channelTable = channelDiv.find('table').at(0);
        let channelTableDiv = channelTable.closest('div');
        let channelTableMessage = channelTableDiv.find('span');
        let channelTableTop = channelTableDiv.get().offsetTop;
        let containerHeight = channelDiv.boundingClientHeight();
        channelTableDiv.css('height', containerHeight - channelTableTop + "px");
        nameInput.val('SlowDash-' + (new JGDateTime()).asString('%y%m%d-%H%M%S'));
        
        let [tsChannelList, allChannelList] = [[], []];
        for (let entry of (this.channelList ?? [])) {
            allChannelList.push(entry.name);
            if ((entry.type ?? 'timeseries') == 'timeseries') {
                tsChannelList.push(entry.name);
            }    
        }

        let checkState = () => {
            let has_ts = false, has_obj = false;
            for (let input of channelTable.find('input').enumerate()) {
                if (input.checked()) {
                    if (input.data('sd-data-type') == 'timeseries') {
                        has_ts = true;
                    }
                    else {
                        has_obj = true;
                    }
                }
            }

            if (has_ts === has_obj) {
                buttonDiv.find('button').at(0).enabled(false);
                buttonDiv.find('button').at(1).enabled(has_ts);
                button2Div.find('button').enabled(false);
            }
            else if (has_ts) {
                buttonDiv.find('button').enabled(true);
                button2Div.data('datatype', 'timeseries').find('button').enabled(true);
            }
            else {
                buttonDiv.find('button').at(0).enabled(false);
                buttonDiv.find('button').at(1).enabled(true);
                button2Div.data('datatype', 'obj').find('button').enabled(true);
            }
        };
        
        let addChannel = channel => {
            if (! channel) return;
            if (channel.indexOf('*') >= 0) {
                let pattern = new RegExp(channel.split('.').join('\\.').split('*').join('.*'));
                for (let ch of allChannelList) {
                    if (pattern.test(ch)) {
                        addChannel(ch);
                    }
                }
                return;
            }

            let already_exists = false;
            for (let ch of channelTable.find('input').enumerate()) {
                if (channel == ch.data('sd-channel')) {
                    ch.checked(true);
                    already_exists = true;
                    break;
                }
            }
            if (! already_exists) {
                let datatype = 'timeseries';
                if (! tsChannelList.includes(channel)) {
                    datatype = 'unknown';
                    for (let entry of (this.channelList ?? [])) {
                        if (entry.name == channel) {
                            datatype = entry.type ?? 'timeseries';
                        }
                    }
                }
                
                let tr = $('<tr>').appendTo(channelTable);
                let label = $('<label>').appendTo($('<td>').appendTo(tr));
                let input = $('<input>').attr('type', 'checkbox').checked(true);
                input.data('sd-channel', channel).data('sd-data-type', datatype).bind('change', e=> {
                    checkState();
                });
                label.append(input).append($('<span>').text(channel));
                if (datatype != 'timeseries') {
                    tr.append($('<td>').css({'font-size': '80%', 'padding-left': '3em'}).text(`(${datatype})`));
                }
                else {
                    tr.append($('<td>'));
                }
                channelTableMessage.css('display', 'none');
            }

            checkState();
        };
        
        for (let ch of thisconfig.channels ?? []) {
            addChannel(ch);
        }
        channelInput.bind('change', e=>{
            addChannel(channelInput.val());
            channelInput.val('');
        });
        channelDiv.find('button').at(0).bind('click', e=>{
            addChannel(channelInput.val());
        });
        channelDiv.find('button').at(1).bind('click', e=>{
            channelTable.empty();
            channelTableMessage.css('display', 'inline');
            buttonDiv.find('button').enabled(false);
            button2Div.find('button').enabled(false);
        });
        
        
        //// Time Range ////
        
        let k = 0;
        bindInput(thisconfig, 'from', rangeDiv.find('input').at(k++));
        bindInput(thisconfig, 'to', rangeDiv.find('input').at(k++));
        bindInput(thisconfig, 'resampling', rangeDiv.find('input').at(k++));
        bindInput(thisconfig, 'resampling_unit', rangeDiv.find('select').at(0));
        bindInput(thisconfig, 'resampling_reducer', rangeDiv.find('select').at(1));
        bindInput(thisconfig, 'use_utc', rangeDiv.find('input').at(k++));


        //// Download Button ////
        
        let download_url = (opts={}) => {
            let channels = [];
            for (let ch of channelTable.find('input').enumerate()) {
                if (ch.checked()) {
                    channels.push(ch.data('sd-channel'));
                }
            }

            let to = Number(thisconfig.to);
            let length = to - Number(thisconfig.from);

            if (channels.length == 0) {
                alert("Select channels");
                return;
            }
            if (! (to > 0) || ! (length > 0)) {
                alert("Invalid time range");
                return;
            }
            
            let timezone = (thisconfig.use_utc ? 'UTC' : 'local');
            
            let resample = Number(thisconfig.resampling);
            if (resample > 0) {
                if (thisconfig.resampling_unit == 'm') {
                    resample *= 60;
                }
                else if (thisconfig.resampling_unit == 'h') {
                    resample *= 3600;
                }
                else if (thisconfig.resampling_unit == 'd') {
                    resample *= 86400;
                }
            }
            else {
                resample = 0;
            }
            
            let query_opts = [ 'length='+length, 'to='+to, 'timezone='+timezone ];
            if (resample > 0) {
                query_opts.push('resample=' + resample);
                query_opts.push('reducer=' + thisconfig.resampling_reducer);
            }
            for (let key in opts) {
                query_opts.push(key + '=' + encodeURIComponent(opts[key]));
            }

            return channels.join(',') + '?' + query_opts.join('&');
        };

        buttonDiv.find('button').at(0).bind('click', e=>{
            const filename = channelDiv.find('input').at(0).val() + ".csv";
            const url = 'api/dataframe/' + download_url();
            buttonDiv.find('a').attr('download', filename).attr('href', url).click();
        });
        buttonDiv.find('button').at(1).bind('click', e=>{
            const filename = channelDiv.find('input').at(0).val() + ".json";
            const url = 'api/data/' + download_url();
            buttonDiv.find('a').attr('download', filename).attr('href', url).click();
        });
        button2Div.find('button').at(0).bind('click', e=>{
            const filename = channelDiv.find('input').at(0).val() + ".py";
            const opts = { datatype: button2Div.data('datatype'), slowdash_url: window.location.origin };
            const url = 'api/extension/jupyter/python/' + download_url(opts);
            buttonDiv.find('a').attr('download', filename).attr('href', url).click();
        });
        button2Div.find('button').at(1).bind('click', e=>{
            const filename = channelDiv.find('input').at(0).val() + ".ipynb";
            const opts = { datatype: button2Div.data('datatype'), slowdash_url: window.location.origin };
            const url = 'api/extension/jupyter/notebook/' + download_url(opts);
            buttonDiv.find('a').attr('download', filename).attr('href', url).click();
        });
        button2Div.find('button').at(2).bind('click', async e=>{
            const filename = channelDiv.find('input').at(0).val() + ".ipynb";
            const opts = { datatype: button2Div.data('datatype'), slowdash_url: window.location.origin };
            const url = 'api/extension/jupyter/jupyter/' + download_url(opts);
            const headers = { 'Content-Type': 'application/json; charset=utf-8' };
            const doc = { 'filename': filename };
            this.indicator.open("Launching Jupyter...", "&#x23f3;", event?.clientX ?? null, event?.clientY ?? null);
            let response = await fetch(url, { method: 'POST', headers: headers, body: JSON.stringify(doc, null, 2) });
            if ((response.status != 200) && (response.status != 201)) {
                this.indicator.close("Error on launching Jupyter: " + response.status + " " + response.statusText, "&#x274c;", 5000);
            }
            else {
                const reply = await response.json();
                if ((reply.status??'') != 'ok') {
                    this.indicator.close("Error on launching Jupyter: " + (reply.message ?? ''), "&#x274c;", 5000);
                }
                else {
                    this.indicator.close("Success", "&#x2705;", 1000);
                    if (reply.notebook_url.substr(0, 4) == 'http') {
                        window.location.href = reply.notebook_url;
                    }
                }
            }
        });
            
        
        
        //// Panel Scaling ////
        
        const scaleH = this.contentDiv.get().offsetWidth / this.contentDiv.get().scrollWidth;
        const scaleV = this.contentDiv.get().offsetHeight / this.contentDiv.get().scrollHeight;
        const scale = Math.min(scaleH, scaleV);
        if (scale < 1) {
            const thisscale = (scale > 0.6 ? scale : 0.6);
            this.contentDiv.css({
                width:'calc(' + 100/thisscale + '%)',
                height:'calc(' + 100/thisscale + '% - 4em)',
                transform: 'scale(' + thisscale + ')',
                'transform-origin': '0 0',
            });
            if (scale > 0.6) {
                this.frameDiv.css({
                    overflow: 'visible'
                });
            }
        }
    }
}



export class SlowpyPanel extends Panel {
    static describe() {
        return { type: 'slowpy', label: '' };
    }
    
    static buildConstructRows(table, on_done=config=>{}) {
        let tr = $('<tr>').html(`
            <td style="padding-top:1em"><button hidden style="font-size:x-large">Create</button></td><td></td>
        `).appendTo(table);

        let button = tr.find('button');
        button.bind('click', e=>{
            let config = {
                use_utc: false,
                channels: []
            };
            on_done(config);
        });
    }

    
    constructor(div, style) {
        super(div, style);
        
        this.frameDiv = $('<div>').appendTo(div);
        this.titleDiv = $('<div>').appendTo(this.frameDiv).text("SlowPy Plotting Script (EXPERIMENTAL: this script might not be compatible with future releases of SlowDash)");
        this.contentDiv = $('<div>').appendTo(this.frameDiv);

        this.contentDiv.html(`
          <div style="display:flex;height:calc(100% - 10px);width:calc(100% - 10px)">
              <div style="flex-grow:1;height:100%;min-width:70%">
                  <textarea spellcheck="false" autocomplete="off"></textarea>
                  <div style="font-size:80%;margin-top:0.5em">
                      <b>Note</b> The SlowPy library must be installed to run this script. See <a href="./docs/index.html#Installation" target="_blank">documentation</a> for installation procedures.
                  </div>
              </div>
              <div style="display:flex;flex-direction:column;height:100%;width:100%;margin-left:3ex">
                  <div style="display:flex;width:100%;margin-top:auto">
                      <div class="jaga-dialog-button-pane" style="margin-left:auto">
                          <button>Copy</button>
                          <button>Save</button>
                          <a style="display:none"></a>
                      </div>
                  </div>
              </div>
          </div>
        `);
        
        this.textarea = this.contentDiv.find('textarea');
        this.buttonDiv = this.contentDiv.find('.jaga-dialog-button-pane');
        let copyBtn = this.buttonDiv.find('button').at(0);
        let saveBtn = this.buttonDiv.find('button').at(1);

        this.frameDiv.css({
            width:'calc(100% - 44px)',
            height:'calc(100% - 44px)',
            margin: '10px 10px 10px 10px',
            padding:'10px',
            border: 'thin solid',
            'border-radius': '5px',
            overflow:'hidden',
        });
        this.titleDiv.css({
            'font-family': 'sans-serif',
            'font-size': '20px',
            'font-weight': 'normal',
            'margin': '0',
            'margin-bottom': '10px',
        });
        this.contentDiv.css({
            position: 'relative',
            width:'calc(100% - 5px)',
            height:'calc(100% - 2em)',
            margin: 0,
            padding:0,
            overflow:'auto',
        });
        this.textarea.css({
            width: 'calc(100% - 2em)',
            height: 'calc(100% - 4em)',
            margin: '0',
            padding: '0.5em',
            wrap: 'off',
            'white-space': 'pre',
            'font-family': 'monospace',
            'font-size': '120%',
            color: 'purple',
            border: 'thin dotted',
            'border-radius': '5px',
            'overflow': 'auto',
            'resize': 'none',
        });

        copyBtn.bind('click', e=>{
            if (true) {
                // document.execCommand() is depreciated
                let selection = window.getSelection();
                selection.removeAllRanges();
                let range = document.createRange();
                range.selectNode(this.textarea.get());
                selection.addRange(range);
                document.execCommand("copy");
                selection.removeAllRanges();
            }
            else {
                // this works only with HTTPS
                navigator.clipboard.writeText(this.textarea.val());
            }
        });
        saveBtn.bind('click', e=>{
            let a = this.buttonDiv.find('a');
            a.attr('download', `slowpy-plot-${new JGDateTime().asString('%y%m%d-%H%M%S')}.py`);
            a.attr('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(this.textarea.val()));
            a.click();
        });
    }

    
    configure(config, callbacks={}) {
        super.configure(config, callbacks);

        const defaults = {
            channels: [],
            format: 'csv',
            use_utc: false,
            to: $.time(),
            length: 3600,
            resampling: '',
            resampling_unit: 's',
            resampling_reducer: 'mean',
        }
        let thisconfig = $.extend({}, defaults, config);
        if (! thisconfig.to || isNaN(parseInt(thisconfig.to))) {
            thisconfig.to = $.time();
        }
        else {
            thisconfig.to = parseInt(thisconfig.to);
        }
        if (! thisconfig.from || isNaN(parseInt(thisconfig.from))) {
            if (! thisconfig.length || isNaN(parseInt(thisconfig.length))) {
                thisconfig.length = 3600;
            }
            thisconfig.from = thisconfig.to - parseInt(thisconfig.length);
        }
        thisconfig.length = thisconfig.to - thisconfig.from;

        let channels = '';
        for (let i = 0; i < thisconfig.channels.length; i++) {
            channels += ((i == 0) ? '[' : ',');
            channels += "'" + thisconfig.channels[i] + "'";
        }
        channels += ']';

        if (thisconfig.length <= 7200) {
            thisconfig.from = `${-thisconfig.length}`;
        }
        else {
            thisconfig.from = `'${(new JGDateTime(thisconfig.to)).asString('%Y-%m-%dT%H:%M:%S%:z')}'`;
        }
        thisconfig.to = `'${(new JGDateTime(thisconfig.to)).asString('%Y-%m-%dT%H:%M:%S%:z')}'`;
        const space_after_from = ' '.repeat(thisconfig.to.length - thisconfig.from.length);
        
        let script = '';
        if (config.format == 'csv') {
            script = (
               `|from slowpy import SlowFetch
                |from matplotlib import pyplot as plt
                |
                |sf = SlowFetch('${window.location.origin}')
                |#sf.set_user(USER, PASS)                  # set the password if the SlowDash page is protected
                |
                |df = sf.dataframe(                        ### this returns a Pandas DataFrame
                |    channels = ${channels},           
                |    start = ${thisconfig.from},${space_after_from}  # Date-time string, UNIX time, or negative integer for seconds to "stop"
                |    stop = ${thisconfig.to},   # Date-time string, UNIX time, or non-positive integer for seconds to "now"
                |    resample = 0,                         # resampling time-backets intervals, zero for auto
                |    reducer = 'mean',                     # 'last' (None), 'mean', 'median'
                |    filler = None)                        # 'fillna' (None), 'last', 'linear'
                |
                |df.plot(x='DateTime', y=${channels})
                |
                |plt.show()                                # this line is not necessary in IPython (Jupyter etc.)`
            ).replace(/ *\|/g, '');
        }
        else {
            script = (
              ` |from slowpy import SlowFetch
                |from slowpy import slowplot as plt
                |
                |sf = SlowFetch('${window.location.origin}')
                |#sf.set_user(USER, PASS)                  # set the password if the SlowDash page is protected
                |
                |packet = sf.lastobj(                      ### this returns a dict of SlowPy data objects
                |    channels=${channels},           
                |    start = ${thisconfig.from},${space_after_from}  # Date-time string, UNIX time, or negative integer for seconds to "stop"
                |    stop = ${thisconfig.to},   # Date-time string, UNIX time, or non-positive integer for seconds to "now"
                |)
                |
                |for ch in ${channels}:
                |    plt.plot(packet[ch])                  # note that "plt" is slowpy.slowplot, not matplotlib.pyplot
                |
                |plt.show()                                # this line is not necessary in IPytho (Jupyter etc.)`
            ).replace(/ *\|/g, '');
        }
            
        this.textarea.val(script);
    }


    openSettings(div) {
        let inputsDiv = $('<div>').appendTo(div);
        inputsDiv.html(`
            <table style="margin-top:1em">
              <tr><th>Default Timezone</th><td><label><input type="checkbox">Use UTC</label></td></tr>
            </table>
        `);

        let k = 0;
        bindInput(this.config, 'use_utc', inputsDiv.find('input').at(k++), false);
    }
}
