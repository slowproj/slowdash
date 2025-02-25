// layout.mjs //
// Author: Sanshiro Enomoto <sanshiro@uw.edu> //
// Created on 18 November 2021 //
// Refactored on 18 June 2022 //


import { JG as $ } from './jagaimo/jagaimo.mjs';
import { JGInvisibleWidget, JGDialogWidget } from './jagaimo/jagawidgets.mjs';
import { PanelPluginLoader } from './panel-plugin-loader.mjs';


export class Layout {
    constructor(div, style={}) {
        this.layoutDiv = div;
        this.currentDataPacket = null;

        const dummyPlotDiv = $('<div>').addClass('sd-plot').appendTo(div);
        const contextColor = getComputedStyle(div.get()).color;
        const contextBackgroundColor = getComputedStyle(div.get()).backgroundColor;
        const plotColor = getComputedStyle(dummyPlotDiv.get()).color;
        const plotBackgroundColor = getComputedStyle(dummyPlotDiv.get()).backgroundColor;
        const pageBackgroundColor = getComputedStyle(div.closest('body').get()).backgroundColor;

        let plotMiddleColor = 'gray';
        const colorPattern = /rgb.*\( *([0-9\.]+), *([0-9\.]+), *([0-9\.]+)/;
        const c = plotColor.match(colorPattern);
        if (c) {
            plotMiddleColor = `rgba(${c[1]},${c[2]},${c[3]},0.4)`;
        }
        
        this.defaultStyle = {
            strokeColor: contextColor,
            pageBackgroundColor: pageBackgroundColor,
            plotBackgroundColor: plotBackgroundColor,
            plotMarginColor: contextBackgroundColor,
            plotFrameColor: plotColor,
            plotLabelColor: contextColor,
            plotGridColor: plotMiddleColor,
            plotFrameThickness: 2,
            plotTicksOutwards: true,
            plotGridEnabled: true,
            negatingImages: style.negate,
        };

        this.beatCallbacks = [];
        this.beat();

        this.setupStreamingData();
    }


    beat() {
        for (let f of this.beatCallbacks) {
            f();
        }
        setTimeout(()=>{this.beat();}, 1000);
    }
    

    async load_panels() {
        let loader = new PanelPluginLoader();
        this.PanelClassList = await loader.load();
    }
   
    
    configure(config=null, callbacks={}) {
        const default_callbacks = {
            changeDisplayTimeRange: range => {},
            forceUpdate: () => {},
            suspend: (duration) => {},
            popoutPanel: (index) => {},
        };
        if (config !== null) {
            this.config = config;
            this.callbacks = $.extend({}, default_callbacks, this.callbacks??{}, callbacks);
        }
        
        if (this.config.control === undefined) {
            this.config.control = {};
        }
        if ((this.config.control.grid?.columns??0) < 1) {
            this.config.control.grid = { columns: 1, rows: 1 };
        }
        if (this.config.panels === undefined) {
            this.config.panels = [];
        }
        else {
            // remove panels marked as "deleted"
            this.config.panels = this.config.panels.filter(p => !(p.deleted??false));
        }
        
        let layoutWidth = document.documentElement.clientWidth;
        let layoutHeight = document.documentElement.clientHeight - this.layoutDiv.pageY();

        const scrollBarWidth = 20; // this does not exist yet, so <html>.clientWidth does not include it
        const layoutInnerWidth = layoutWidth - scrollBarWidth;
        const layoutInnerHeight = layoutHeight /*- scrollBarWidth */ - 2; // 4 for panel border on hover
        
        const ncols = parseInt(this.config.control.grid.columns ?? 1);
        const nrows = parseInt(this.config.control.grid.rows ?? 1);
        const cellWidth = Math.floor(layoutInnerWidth / ncols);
        const cellHeight = Math.floor(layoutInnerHeight / nrows);

        let fontSize = '100%';
        let fontScaling = 100.0;
        if (ncols == 3) {
            fontScaling =80;
        }
        else if (ncols > 3) {
            fontScaling = 100.0 / (ncols-2);
        }
        
        this.layoutDiv.empty().css({
            'position': 'relative',
            'width': layoutWidth + 'px',
            'height': layoutHeight + 'px',
            'overflow': 'auto',
            'display': 'flex',
            'flex-wrap': 'wrap',
            'font-size': fontSize,
        });
        let style = $.extend({}, this.defaultStyle, this.config._project?.style?.panel ?? {});
        
        this.panels = [];
        this.beatCallbacks = [];
        for (let entry of this.config.panels) {
            let panelDiv = $('<div>').addClass('sd-panel').appendTo(this.layoutDiv);
            panelDiv.css({
                'width': (cellWidth-12)+'px',
                'height': (cellHeight-12)+'px',
                'position': 'relative',
                'margin': '5px',
                'padding': 0,
                'border-radius': '10px',
                'font-size': fontScaling + '%',
            });

            if (this.config.layout?.focus_highlight !== false) {
                panelDiv.bind('pointerenter', e=>{
                    let target = $(e.target);
                    target.css('border', '1px solid rgba(128,128,128,0.7)');
                    let duration = parseInt(this.config.layout?.focus_highlight ?? 10);
                    if (duration > 0) {
                        let timeoutId = target.attr('sd-timeoutId');
                        if (timeoutId) {
                            clearTimeout(timeoutId);
                        }
                        timeoutId = setTimeout(()=>{
                            target.css('border', '1px solid rgba(128,128,128,0)');
                        }, duration*1000);
                        target.attr('sd-timeoutId', timeoutId);
                    }
                });
                panelDiv.bind('mouseleave', e=>{
                    $(e.target).css('border', '1px solid rgba(128,128,128,0)');
                });
            }

            //... backwards compatibility
            if ((entry.type === undefined) || (entry.type == 'timeseries')) {
                entry.type = 'timeaxis';
            }

            let panel = null;
            for (let PanelClass of this.PanelClassList) {
                if (entry.type == PanelClass.describe().type) {
                    panel = new PanelClass(panelDiv, style);
                }
            }
            if (panel === null) {
                console.log('unable to find panel type: ' + entry.type);
            }
            if (panel !== null) {
                let callbacks = {
                    changeDisplayTimeRange: range => {
                        // range value can be null for a default range
                        for (let panel of this.panels) {
                            panel.draw(this.currentDataPacket, range);
                        }
                        this.callbacks.changeDisplayTimeRange(range);
                    },
                    reloadData: () => {
                        this.load(null);
                    },
                    updateData: () => {
                        this.callbacks.forceUpdate();
                    },
                    suspendUpdate: (duration) => {
                        this.callbacks.suspend(duration);
                    },
                    reconfigure: () => {
                        this.configure(null);
                        this.load(null);
                    },
                    popout: (p) => {
                        for (let i = 0; i < this.panels.length; i++) {
                            if (this.panels[i] === p) {
                                //this.fullscreenPanel(i);
                                this.callbacks.popoutPanel(i);
                            }
                        }
                    },
                    publish: (topic, message) => {
                        //console.log("publish", topic, JSON.stringify(message));
                        this.publish(topic, message);
                    },
                };
                panel.configure(entry, callbacks, this.config._project);
                this.panels.push(panel);
                if (panel.beatCallback) {
                    this.beatCallbacks.push(panel.beatCallback);
                }
            }
        }

        if (this.config.control.immutable || ((this.config.control.mode??'') == 'display')) {
            for (let panel of this.panels) {
                panel.ctrlDiv.remove();
                panel.ctrlDiv = undefined;
            }
        }
        else if ((this.config.control.mode??'') == 'protected') {
            for (let panel of this.panels) {
                panel.ctrlDiv.find('.sd-modifying').remove();
            }
        }
        else {
            const addDivStyle = {
                'width': (cellWidth-100)+'px',
                'height': (cellHeight-80)+'px',
                'border-width': 'thin',
                'border-style': 'solid',
                'border-radius': '10px',
                'padding': '20px',
                'margin-left': '40px',
                'margin-top': '20px',
            };
            const addButtonStyle = {
                'font-size': '120%',
            };
            let addDiv = $('<div>').addClass('sd-pad').css(addDivStyle).appendTo(this.layoutDiv);
            if (this.config.panels.length > 0) {
                new JGInvisibleWidget(addDiv);
            }

            let addDialogDiv = $('<div>').addClass('sd-pad').css({'display':'none'});
            // cannot be layoutDiv, as 'position:fiexed' does not work under an element with transform
            addDialogDiv.appendTo(this.layoutDiv.closest('body'));
            
            let addDialog = new JGDialogWidget(addDialogDiv, {
                title: 'Add a New Panel',
                closeOnGlobalClick: false,   // keep this false, otherwise not all inputs will be handled
                closeButton: true,
            });
            $('<button>').text('Add a New Panel').css(addButtonStyle).appendTo(addDiv).click(e=>{
                addDialog.open();
            });
            this.buildAddNew(addDialogDiv.find('.jaga-dialog-content'), addDialog);
        }
            
        if (this.currentDataPacket !== null) {
            for (let panel of this.panels) {
                panel.draw(this.currentDataPacket, this.currentDataPacket.range);
            }
        }
    }

    
    buildAddNew(div, dialog) {
        div.css({
            'font-size': '130%'
        });
        div.html(`
            <span style="font-size:140%">Create a New Panel</span>
            <table style="margin-top:1em;margin-left:1em">
              <tr><td>Type</td><td>
                <select style="font-size:130%">
                </select></td></tr>
            </table>
          </div>
        `);

        let select = div.find('select');
        let PanelClassTable = {};
        for (let PanelClass of this.PanelClassList) {
            const desc = PanelClass.describe();
            if (desc.label) {
                select.append($('<option>').attr('value', desc.type).attr('label', desc.label).text(desc.label));
                PanelClassTable[desc.type] = PanelClass;
            }
        }
        
        let table = div.find('table');
        let addPanel = config => {
            if (config) {
                this.config.panels.push(config);
                this.configure(this.config);
                this.load();
            }
        }

        function updateSelection() {
            table.find('tr:not(:first-child)').remove();
            let type = table.find('select').selected().attr('value');
            let PanelClass = PanelClassTable[type];
            if (PanelClass) {
                PanelClass.buildConstructRows(table, config => {
                    dialog.close();
                    addPanel(config);
                });
            }
        }
        updateSelection();
        div.find('select').bind('change', e=>{updateSelection();});
    }

    
    setGrid(rows, columns) {
        let [nrows, ncols] = [parseFloat(rows), parseInt(columns)];
        if (!(nrows > 0) || ! (ncols > 0)) {
            return;
        }
        this.config.control.grid.rows = nrows;
        this.config.control.grid.columns = ncols;
        this.configure(this.config);
        this.load();
    }

    
    fullscreenPanel(index) {
        let panelDiv = this.layoutDiv.find('.sd-panel').at(index);
        if (panelDiv.boundingClientHeight() > 0.7 * this.layoutDiv.boundingClientHeight()) {
            // pop-in: back to original grid
            this.configure(this.config);
            return;
        }
        
        const rows = this.config.control.grid.rows;
        const cols = this.config.control.grid.columns;
        this.config.control.grid.rows = 1;
        this.config.control.grid.columns = 1;
        this.configure(this.config);
        this.config.control.grid.rows = rows;
        this.config.control.grid.columns = cols;

        panelDiv = this.layoutDiv.find('.sd-panel').at(index);
        this.layoutDiv.get().scrollTop = panelDiv.get().offsetTop - 10;
    }

    
    load(range=null, on_complete=status=>{}) {
        // If the data range is not specified, use the same range before, and reuse the loaded data.
        // Even for the identical data range, panels must be updated because a new plot for the same channel might have been added.
        
        if ((range === null) && (this.currentDataPacket?.isTransitional ?? false)) {
            // update request (by initial configure() with promise etc) while loading
            //return;   // instead of uncommenting this, modify the code to make load() called after configure()
        }
        if (range !== null) {
            this.currentDataPacket = {
                isTransitional: true,
                range: range,
                data: {}
            };
        }

        let channels = {}; {
            let inputChannels = [];
            for (let panel of this.panels) {
                panel.fillInputChannels(inputChannels);
            }
            for (let ch of inputChannels) {
                if (! (ch in this.currentDataPacket.data)) {
                    channels[ch] = 1;
                }
            }
        }        
        
        if (Object.keys(channels).length <= 0) {
            this.currentDataPacket.isTransitional = false;
            on_complete({code:200, text:'OK'});
            for (let panel of this.panels) {
                panel.draw(this.currentDataPacket, this.currentDataPacket.range);
            }
            return;
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
                
        let n = url_list.length;
        let status = {code:200, text:'OK'};
        let processPartialPacket = packet => {
            n--;
            this.currentDataPacket.isTransitional = (n > 0);
            for (let ch in packet) {
                this.currentDataPacket.data[ch] = packet[ch];
            }
            for (let panel of this.panels) {
                panel.draw(this.currentDataPacket, this.currentDataPacket.range);
            }
            if (n == 0) {
                on_complete(status);
            }
        };
        for (let url of url_list) {
            fetch(url)
                .then(response => {
                    if (! response.ok) {
                        status = { code: response.status, text: response.statusText };
                        throw new Error(response.status);
                    }
                    return response.json();
                })
                .catch(e => {
                    if (status.code == 200) {
                        status = {code: -1, text: e.message};
                    }
                    return {};
                })
                .then(packet => {
                    processPartialPacket(packet);
                });
        }
    }

    
    setupStreamingData() {
        let url = new URL(window.location.href);
        url.protocol = 'ws:';
        url.search = ''
        url.hash = ''
        
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
            const record = JSON.parse(event.data);
            const now = $.time();
            const dataPacket = {
                isTransitional: true,
                range: { from: now - 60, to: now },
                data: record,
            };
            if (this.panels) {
                for (let panel of this.panels) {
                    panel.draw(dataPacket, dataPacket.range);
                }
            }
        };
    }

    async publish(topic, doc) {
        if (topic != 'currentdata') {
            return;
        }
        const message = (typeof doc == 'string') ? doc : JSON.stringify(doc);
        
        if (this.socket && (this.socket.readyState == WebSocket.OPEN)) {
            this.socket.send(message);
        }
        else {
            const url = './api/control/currentdata';
            fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json; charset=utf-8' },
                body: message,
            })
                .then(response => {
                    this.callbacks.forceUpdate();
                })
                .catch(e => {
                });
        }
    }
};

