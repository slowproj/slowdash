// panel-singles.mjs //
// Author: Sanshiro Enomoto <sanshiro@uw.edu> //
// Created on 31 July 2025 //


import { JG as $, JGDateTime } from './jagaimo/jagaimo.mjs';
import { JGPlotAxisScale } from './jagaimo/jagaplot.mjs';
import { JGTabWidget } from './jagaimo/jagawidgets.mjs';
import { Panel, bindInput } from './panel.mjs';



class SingleDisplayItem {
    constructor(svgParent, panelConfig, style) {
        this.parent = svgParent;
        this.panelConfig = panelConfig;
        this.style = $.extend({}, style);
        
        this.elem = undefined;
        this.currentDataTime = -1;
    }

    
    configure(config) {
        this.config = config;
        
        if (! this.configure_this) {
            return;
        }
        this.elem = this.configure_this(config).appendTo(this.parent);

        this.currentDataTime = -1;
        this.update_this(null, null, '---', '---');
    }

    
    openItemSettings(div) {
    }

    
    update(dataPacket) {
        if (! dataPacket || ! this.config.channel) {
            return;
        }
        
        const ts = dataPacket[this.config.channel];
        if (! ts) {
            if (
                (dataPacket.__meta?.isPartial ?? false) ||
                (Panel._dataPacketIncludes(dataPacket, this.currentDataTime))
            ) {
                // keep the current data (no update); otherwise draw "---"
                return;
            }
        }
        else if (dataPacket.__meta?.isCurrent ?? false) {
            this.currentDataTime = dataPacket.__meta.currentDataTime;
        }
        
        let time=null, value=null;
        if ((ts?.t !== undefined) && (ts?.t !== null)) {
            if (Array.isArray(ts.t)) {
                let k = ts.t.length - 1;
                while ((k >= 0) && isNaN(ts.x[k])) {
                    k--;
                }
                if (k >= 0) {
                    time = ts.t[k] + (ts.start ?? 0);
                    value = ts.x[k];
                }
            }
            else {
                time = ts.t + (ts.start ?? 0);
                value = ts.x;
            }
        }
        
        let time_text, value_text;
        if (time === null) {
            time_text = '---';
        }
        else {
            const time_format = this.config.time_format || '%a,%H:%M';
            time_text = (new JGDateTime(time)).asString(time_format);
        }
        if (value === null) {
            value_text = '---';
        }
        else if (this.config.format) {
            value_text = $.sprintf(this.config.format, value);
        }
        else {
            value_text = value;
        }
        
        this.update_this(time, value, time_text, value_text);
    }
};



class SquareItem extends SingleDisplayItem {
    constructor(svgParent, style) {
        super(svgParent, style);
    }

    
    openItemSettings(div) {
        if (! this.config.gauge) {
            this.config.gauge = { min: 0, max: 0 };
        }
        if (! this.config.ranges) {
            this.config.ranges = {
                normal: { min: 0, max: 0, color: '#06b6d4' },
                warn: { min: 0, max: 0, color: '#f59e0b' },
                error: { min: 0, max: 0, color: '#d81b60' },
            };
        }
        
        div.html(`
            <table>
              <tr><td>Channel</td><td><input list="sd-numeric-datalist"></td></tr>
              <tr><td>Label</td><td><input placeholder="auto"></td></tr>
              <tr><td>Value Format</td><td><input placeholder="%f"></td></tr>
              <tr><td>Time Format</td><td><input placeholder="%a,%H:%M"></td></tr>
              <tr><td>Gauge</td><td>min: <input type="number" step="any">, max: <input type="number" step="any"></td></tr>
              <tr><td>Ranges</td><td><input type="color"> min: <input type="number" step="any">, max: <input type="number" step="any"></td></tr>
              <tr><td></td><td><input type="color"> min: <input type="number" step="any">, max: <input type="number" step="any"></td></tr>
              <tr><td></td><td><input type="color"> min: <input type="number" step="any">, max: <input type="number" step="any"></td></tr>
              <tr><td></td><td style="font-size:70%">overwrapping ok, evaluated from top to bottom<br>(for positive one-sided, only max boundaries can be set)</td></tr>
            </table>
        `);

        let k = 0;
        bindInput(this.config, 'channel', div.find('input').at(k++).css('width', '20em'));
        bindInput(this.config, 'label', div.find('input').at(k++).css('width', '20em'));
        bindInput(this.config, 'format', div.find('input').at(k++).css('width', '10em'));
        bindInput(this.config, 'time_format', div.find('input').at(k++).css('width', '10em'));
        bindInput(this.config.gauge, 'min', div.find('input').at(k++).css('width', '5em'));
        bindInput(this.config.gauge, 'max', div.find('input').at(k++).css('width', '5em'));
        bindInput(this.config.ranges.normal, 'color', div.find('input').at(k++));
        bindInput(this.config.ranges.normal, 'min', div.find('input').at(k++).css('width', '5em'));
        bindInput(this.config.ranges.normal, 'max', div.find('input').at(k++).css('width', '5em'));
        bindInput(this.config.ranges.warn, 'color', div.find('input').at(k++));
        bindInput(this.config.ranges.warn, 'min', div.find('input').at(k++).css('width', '5em'));
        bindInput(this.config.ranges.warn, 'max', div.find('input').at(k++).css('width', '5em'));
        bindInput(this.config.ranges.error, 'color', div.find('input').at(k++));
        bindInput(this.config.ranges.error, 'min', div.find('input').at(k++).css('width', '5em'));
        bindInput(this.config.ranges.error, 'max', div.find('input').at(k++).css('width', '5em'));
    }

    
    get_defaults() {
        return {
            "format": null,
        };
    }

    
    configure_this() {
        let g = $('<g>', 'svg').attr({
            'text-anchor': 'begin',
            'dominant-baseline': 'hanging',
        });
        
        this.channel_label = $('<text>', 'svg').appendTo(g).text(this.config.label??this.config.channel).attr({
            "x": 10, "y": 10,
            'text-anchor': 'begin',
            "font-size": 10,
        });
        this.value_label = $('<text>', 'svg').appendTo(g).text('---').attr({
            "x": 10, "y": 35,
            "fill": this.panelConfig.color.base,
            "fill-opacity": this.panelConfig.color?.value_opacity ?? 1.0,
            "font-size": 15,
            "font-weight": 'bold',
            'text-anchor': 'begin',
        });
        this.time_label = $('<text>', 'svg').appendTo(g).text('---').attr({
            "x": 10, "y": 83,
            'text-anchor': 'begin',
            "font-size": 8,
        });

        this.gauge = null;
        this.gauge_length = 83;
        const gauge_min = parseFloat(this.config.gauge?.min);
        const gauge_max = parseFloat(this.config.gauge?.max);
        if (gauge_min < gauge_max) {
            const gauge_opacity = parseFloat(this.panelConfig.color?.gauge_opacity ?? 0.4);
            const tile_opacity = parseFloat(this.panelConfig.color?.tile_opacity ?? 0.1);
            const gauge_base_opacity = Math.max(0, Math.min(1, 0.8 * tile_opacity + 0.2 * gauge_opacity));
            $('<rect>', 'svg').appendTo(g).attr({
                "x": 12, "y": 55,
                "width": this.gauge_length,
                "height": 10,
                "fill": this.panelConfig.color.base,
                "fill-opacity": gauge_base_opacity,
            });
            this.gauge = $('<rect>', 'svg').appendTo(g).attr({
                "x": 12, "y": 55,
                "width": 0,
                "height": 10,
                "fill": this.panelConfig.color.base,
                "fill-opacity": gauge_opacity,
            });
            this.gauge_min = gauge_min;
            this.gauge_max = gauge_max;
            this.gauge_opacity = gauge_opacity;

            if (this.config.ranges) {
                for (let range of [ 'error', 'warn', 'normal' ]) {
                    const range_min = parseFloat(this.config.ranges[range].min ?? 0);
                    const range_max = parseFloat(this.config.ranges[range].max ?? range_min);
                    if ((range_min < range_max) && this.config.ranges[range].color) {
                        const x0 = (range_min - this.gauge_min) / (this.gauge_max - this.gauge_min);
                        const x1 = (range_max - this.gauge_min) / (this.gauge_max - this.gauge_min);
                        const r0 = Math.min(Math.max(x0, 0), 1);
                        const r1 = Math.min(Math.max(x1, 0), 1);
                        $('<rect>', 'svg').appendTo(g).attr({
                            "x": 12 + this.gauge_length*r0, "y": 64,
                            "width": this.gauge_length*(r1-r0),
                            "height": 1,
                            "fill": this.config.ranges[range].color,
                            "fill-opacity": 1,
                        });
                    }
                }
            }

            let scale_g = $('<g>', 'svg').appendTo(g).attr({
                'transform': `translate(12, 65) scale(0.25)`,
            });
            this.scale = new JGPlotAxisScale(this.gauge_min, this.gauge_max, false, {
                "x": 0, "y": 0, "length": this.gauge_length/0.25,
                "labelPosition": "bottom",
                "numberOfTicks": 1,
                "frameThickness": 0,
                "frameColor": this.panelConfig.color.base,
            });
            this.scale.draw(scale_g);
        }

        return g;
    }

    
    update_this(time, value, time_text, value_text) {
        this.value_label.text(value_text);
        this.time_label.text(time_text);
        if (value === null) {
            if (this.gauge) {
                this.gauge.attr({'fill-opacity': 0});
            }
            return;
        }
        
        let range_color = null;
        if (this.config.ranges) {
            for (let range of [ 'normal', 'warn', 'error' ]) {
                const range_min = parseFloat(this.config.ranges[range].min ?? 0);
                const range_max = parseFloat(this.config.ranges[range].max ?? range_min);
                if ((value >= range_min) && (value < range_max)) {
                    range_color = this.config.ranges[range].color ?? null;
                    break;
                }
            }
        }
        if (range_color === null) {
            range_color = this.panelConfig.color.base;
        }
        
        if (this.panelConfig.ranges?.apply_to_tile) {
            this.parent.find('.sd-scalarpanel-tile').attr({'fill': range_color});
        }
        if (this.panelConfig.ranges?.apply_to_value) {
            this.value_label.attr({'fill': range_color});
        }        
        if (this.gauge) {
            const x = (value - this.gauge_min) / (this.gauge_max - this.gauge_min);
            const r = Math.min(Math.max(x, 0), 1);
            this.gauge.attr('width', this.gauge_length*r);
            if (this.panelConfig.ranges?.apply_to_gauge) {
                this.gauge.attr({'fill': range_color});
            }
            this.gauge.attr({"fill-opacity": this.gauge_opacity});
        }
    }
};



const ItemClassCollection = {
    square: SquareItem,
};



export class SinglesPanel extends Panel {
    static describe() {
        return { type: 'singles', label: 'Single Values (Scalars)' };
    }
    
    static buildConstructRows(table, on_done=config=>{}) {
        let tr1 = $('<tr>').html(`
            <td>Style</td><td>
            <select style="font-size:130%">
              <option hidden>Select...</option>
              <option value="square">Square</options>
            </select></td>
       `).appendTo(table);

        function updateSelection2() {
            while (table.find('tr').size() > 2) {
                table.find('tr').at(2).remove();
            }
            let item_type = tr1.find('select').selected().attr('value');
            let tr2 = $('<tr>').html(`
                <td>Channel</td><td><input list="sd-numeric-datalist"></td>
            `).appendTo(table);
            let tr3 = $('<tr>').html(`
                <td style="padding-top:1em"><button hidden style="font-size:130%">Create</button></td><td></td>
            `).appendTo(table);
            
            let button = tr3.find('button');
            table.find('input').bind('input', e=>{
                let filled = true;
                for (let input_k of table.find('input').enumerate()) {
                    if (! (input_k.val().length > 0)) {
                        filled = false;
                        break;
                    }
                }
                if (filled) {
                    button.show();
                }
                else {
                    button.hide();
                }
            });
            button.bind('click', e=>{
                let config = {
                    type: 'singles',
                    item_type: item_type,
                    items: [{
                        channel: tr2.find('input').val(),
                    }],
                };
                on_done(config);
            });
        }
        tr1.find('select').bind('change', e=>{ updateSelection2(); });
    }

    
    constructor(div, style={}) {
        super(div, style);

        this.titleDiv = $('<div>').appendTo(div);
        this.contentDiv = $('<div>').appendTo(div);
        
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
            width:'calc(100% - 22px)',
            height:'calc(100% - 20px - 2em)',
            margin: 0,
            padding:0,
            overflow:'hidden',
        });

        this.svg = $('<svg>', 'svg').appendTo(this.contentDiv).attr({
            "xmlns": "http://www.w3.org/2000/svg",
            "xmlns:xlink": "http://www.w3.org/1999/xlink",
            "version": "1.1",
        });

        this.items = [];
        this.inputChannels = [];
        this.grid = { rows: 1, columns: 1 };
    }

    
    async configure(config, options={}, callbacks={}) {
        await super.configure(config, options, callbacks);
        this.titleDiv.text(this.config.title);

        if (this.config.items === undefined) {
            this.config.items = [];
        }
        if (this.config.item_type === undefined) {
            this.config.item_type = 'square';
        }
        if (! this.config.color?.base) {
            this.config.color = { base: this.style.strokeColor };
        }

        let rows = this.config.grid?.rows ?? 0;
        let cols = this.config.grid?.columns ?? 0;
        if (! (rows > 0) || ! (cols > 0)) {
            const n = Math.max(this.config.items.length, 1);
            if (cols > 0) {
                rows = Math.floor((n-1)/cols)+1;
            }
            else if (rows > 0) {
                cols = Math.floor((n-1)/rows)+1;
            }
            else {
                if (n <= 1) { [rows, cols] = [1, 1]; }
                else if (n <= 3) { [rows, cols] = [1, n]; }
                else if (n <= 8) { [rows, cols] = [2, Math.ceil(n/2)]; }
                else if (n <= 15) { [rows, cols] = [3, Math.ceil(n/3)]; }
                else if (n <= 20) { [rows, cols] = [4, Math.ceil(n/4)]; }
                else {
                    rows = Math.floor(Math.sqrt(n));
                    cols = Math.ceil(n/rows);
                }
            }
        }
        this.grid = { rows: rows, columns: cols };
                
        this._build();
    }

    
    _build() {
        this.svg.empty();

        const margin_top = this.config.margin?.top ?? 0;
        const margin_bottom = this.config.margin?.bottom ?? 0;
        const margin_left = this.config.margin?.left ?? 0;
        const margin_right = this.config.margin?.right ?? 0;
        
        const w = this.contentDiv.get().offsetWidth - margin_left - margin_right;
        const h = this.contentDiv.get().offsetHeight - margin_top - margin_bottom;

        let rx=1, ry=1;
        const wk = w / this.grid.columns, hk = h / this.grid.rows;
        if (wk > hk) {
            rx = wk / hk;
        }
        else {
            ry = hk / wk;
        }
        this.svg.css({'position': 'relative', 'top': margin_top+'px', 'left': margin_left+'px'});
        this.svg.attr({'width': w,  'height': h});
        this.svg.attr({"viewBox": `0 0 ${rx*100*this.grid.columns} ${ry*100*this.grid.rows}`});

        let ItemClass = ItemClassCollection[this.config.item_type || 'square'];
        if (! ItemClass) {
            console.log('ERROR: unknown Single Value Item: ' + this.config.item_type);
            console.log(this.config);
            return;
        }
        
        this.items = [];
        this.inputChannels = [];
        for (const itemConfig of this.config.items ?? []) {
            const dx = rx * 100 * Math.trunc(this.items.length % this.grid.columns);
            const dy = ry * 100 * Math.trunc(this.items.length / this.grid.columns);
            let g = $('<g>', 'svg').appendTo(this.svg).attr({
                'transform': `translate(${dx}, ${dy})`,
                'width': rx * 100,
                'height': ry * 100,
                "fill": this.style.strokeColor,
            });
            $('<rect>', 'svg').appendTo(g).addClass('sd-scalarpanel-tile').attr({
                "x": 5, "y": 5, 'width': rx*100-5, 'height': ry*100-5,
                "stroke": 'none',
                "font-family": 'sans-serif',
                "fill": this.config.color?.base ?? this.config.strokeColor,
                "fill-opacity": this.config.color?.tile_opacity ?? 0.1,
            });

            let item = new ItemClass(g, this.config, this.style);
            this.items.push(item);
            this.inputChannels.push(itemConfig.channel);
            item.configure(itemConfig);
        }
    }

    
    openSettings(div) {
        if (! this.config.grid) {
            this.config.grid = { rows: 0, columns: 0 };
        }
        if (! this.config.margin) {
            this.config.margin = { top: 0, right: 0, bottom: 0, left: 0 };
        }
        if (! this.config.color?.value_opacity) {
            this.config.color = {
                base: this.config.color?.base ?? this.style.strokeColor,
                value_opacity: 1.0,
                gauge_opacity: 0.4,
                tile_opacity: 0.1,
            };
        }
        if (! this.config.ranges) {
            this.config.ranges = {
                apply_to_value: false, apply_to_gauge: true, apply_to_tile: false,
            };
        }
        
        div.css('display', 'flex');
        const boxStyle = {
            'border': 'thin solid',
            'border-radius': '5px',
            'margin': '5px',
            'padding': '5px',
        };
        
        let panelDiv = $('<div>').appendTo(div).css(boxStyle);
        panelDiv.html(`
            <span style="font-size:130%;font-weight:bold">Tiles</span>
            <hr style="margin-bottom:2ex">
            <table>
              <tr><td>Title</td><td><input placeholder="empty"></td></tr>
              <tr><td>Margin</td><td>T:<input>, R:<input>, B:<input>, L:<input></td></tr>
              <tr><td>Grid</td><td>rows: <input type="number" step="1">, columns: <input type="number" step="1"></td></tr>
              <tr><td valign="top">Color</td><td><table style="margin:0;padding:0">
                <tr><td>Base</td><td><input type="color"></td></tr>
                <tr><td>Value</td><td>
                  opacity: <input type="number" step="any">, <label><input type="checkbox">range colors</label>
                </td></tr><tr><td>Gauge</td><td>
                  opacity: <input type="number" step="any">, <label><input type="checkbox" checked>range colors</label>
                </td></tr><tr><td>Tile</td><td>
                  opacity: <input type="number" step="any">, <label><input type="checkbox">range colors</label>
                </td></tr>
              </table></td></tr>
            </table>
        `);
        let k = 0;
        bindInput(this.config, 'title', panelDiv.find('input').at(k++).css('width', '20em'));
        bindInput(this.config.margin, 'top', panelDiv.find('input').at(k++).css('width', '3em'));
        bindInput(this.config.margin, 'right', panelDiv.find('input').at(k++).css('width', '3em'));
        bindInput(this.config.margin, 'bottom', panelDiv.find('input').at(k++).css('width', '3em'));
        bindInput(this.config.margin, 'left', panelDiv.find('input').at(k++).css('width', '3em'));
        bindInput(this.config.grid, 'rows', panelDiv.find('input').at(k++).css('width', '5em'));
        bindInput(this.config.grid, 'columns', panelDiv.find('input').at(k++).css('width', '5em'));
        bindInput(this.config.color, 'base', panelDiv.find('input').at(k++).css('width', '5em'));
        bindInput(this.config.color, 'value_opacity', panelDiv.find('input').at(k++).css('width', '5em'));
        bindInput(this.config.ranges, 'apply_to_value', panelDiv.find('input').at(k++));
        bindInput(this.config.color, 'gauge_opacity', panelDiv.find('input').at(k++).css('width', '5em'));
        bindInput(this.config.ranges, 'apply_to_gauge', panelDiv.find('input').at(k++));
        bindInput(this.config.color, 'tile_opacity', panelDiv.find('input').at(k++).css('width', '5em'));
        bindInput(this.config.ranges, 'apply_to_tile', panelDiv.find('input').at(k++));
        
        let itemsDiv = $('<div>').appendTo(div).css(boxStyle);
        itemsDiv.html(`
            <span style="font-size:130%;font-weight:bold">Items</span>
            <hr style="margin-bottom:2ex">
        `);
        let tabsDiv = $('<div>').appendTo(itemsDiv);
        for (let item of this.items) {
            const label = item.config.channel;
            const pageDiv = $('<div>').addClass('jaga-tabPage').attr('label', label).appendTo(tabsDiv);
            item.openItemSettings(pageDiv);
        }
        let tabs = new JGTabWidget(tabsDiv);
        tabs.openPage(-1);

        let addDiv = $('<div>').appendTo(div).css(boxStyle);
        addDiv.html(`
            <span style="font-size:130%;font-weight:bold">Add New</span>
            <hr style="margin-bottom:2ex">
            <table style="margin-top:1em">
              <tr><td>Type</td><td>Single Values</td></tr>
            </table>
        `);
        SinglesPanel.buildConstructRows(addDiv.find('table'), async config=>{
            this.config.items.push(config.items[0]);
            await this.configure(this.config, this.options, this.callbacks);
            this.openSettings(div.empty());
        });
    }

    
    fillInputChannels(inputChannels) {
        for (let channel of this.inputChannels) {
            inputChannels.push(channel);
        }
    }

    
    draw(data, displayTimeRange=null) {
        for (let item of this.items) {
            item.update(data);
        }
    }
};
