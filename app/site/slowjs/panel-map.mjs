// panel-map.mjs //
// Author: Sanshiro Enomoto <sanshiro@uw.edu> //
// Created on 8 August 2022 //


import { JG as $ } from './jagaimo/jagaimo.mjs';
import { JGInvisibleWidget } from './jagaimo/jagawidgets.mjs';
import { JGPlotColorBarScale } from './jagaimo/jagaplot.mjs';
import { Panel, bindInput } from './panel.mjs';


export class MapPanel extends Panel {
    static describe() {
        return { type: 'map', label: 'Map View of Histogram or Graph' };
    }
    
    static buildConstructRows(table, on_done=config=>{}) {
        let tr1 = $('<tr>').html(`
            <td>Map Name</td><td><input list="sd-map-datalist"></td>
       `).appendTo(table);
        let tr2 = $('<tr>').html(`
            <td>Channel</td><td><input list="sd-histgraph-datalist"></td>
       `).appendTo(table);
        let tr3 = $('<tr>').html(`
            <td style="padding-top:1em"><button hidden style="font-size:x-large">Create</button></td><td></td>
        `).appendTo(table);

        let button = tr3.find('button');
        tr2.find('input').bind('input', e=>{
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
                type: 'map',
                map: table.find('input').at(0).val(),
                channel: table.find('input').at(1).val(),
                axes: {
                    ylog: false,
                    yfixed: false,
                    ymin: 0,
                    ymax: 1,
                    ytitle: '',
                    title: '',
                },
                colorCoding: 'Parula',
                emptyColor: '#ff0000',
            };
            on_done(config);
        });
    }

    
    constructor(div, style={}) {
        super(div, style);
        
        this.map = null;
        this.scale = null;
        this.loaded_map = null;
        this.currentDataTime = -1;
    }

    
    async configure(config, options={}, callbacks={}) {
        this.div.empty();
        await super.configure(config, options, callbacks);
        
        if (config.map && (config.map == this.loaded_map)) {
            this._build(config, callbacks);
            return;
        }
        
        this.loaded_map = config.map;
        const url = './api/config/ffile/map-' + config.map + '.json';
        const response = await fetch('./api/config/file/map-' + config.map + '.json');
        if (! response.ok) {
            this.div.html(`
                <h3>Map Loading Error</h3>
                <p>
                Name: ${config.map}<br>
                URL: ${url}<br>
                Error: ${response.status} ${response.statusText}
            `);
            return null;
        }
        let map = await response.json();
        if (map) {
            this.map = map;
            this._build(config, callbacks);
        }
    }

    
    _build(config, callbacks) {
        if (this.config.legend === undefined) {
            this.config.legend = { style: null };
        }
        if (! ['side', 'box', 'hidden', 'none'].includes(this.config.legend.style)) {
            this.config.legend.style = 'none';
        }
        
        const legendWidthFraction = 0.3;
        const divWidth = this.div.boundingClientWidth();
        const divHeight = this.div.boundingClientHeight();
        const legendDivWidth = divWidth * legendWidthFraction;
        const plotDivWidth = divWidth * (1 - ((config.legend?.style == 'side') ? legendWidthFraction : 0.0));
        let legendFontSize = window.getComputedStyle(this.div.get()).getPropertyValue('font-size');
        if (! (legendDivWidth / parseFloat(legendFontSize) > 16)) {
            legendFontSize = legendDivWidth / 16.0 + "px";
        }
        
        const panelStyle = {
            frameDiv: {
                'position': 'relative',
                'height': divHeight + 'px',
                'overflow': 'hidden',
            },
            plotDiv: {
                'width': plotDivWidth + 'px',
                'height': divHeight + 'px',
            },
            legendDiv: {
                'position': 'absolute',
                'left': (divWidth - legendDivWidth) + 'px',
                'top': '2em',
                'width': legendDivWidth + 'px',
                'padding': 0,
                'margin': 0,
                'font-family': window.getComputedStyle(this.div.get()).getPropertyValue('font-family'),
                'font-size': legendFontSize,
                'z-index': '+1',
            },
            dataReadingDiv: {
                'position': 'absolute',
                'top': `calc(${divHeight}px - 2em)`,
                'left': '1em',
                'z-index': '+1',
            },
        };
        
        this.frameDiv = $('<div>').css(panelStyle.frameDiv).appendTo(this.div);
        this.plotDiv = $('<div>').css(panelStyle.plotDiv).appendTo(this.frameDiv);
        this.legendDiv = $('<div>').css(panelStyle.legendDiv).appendTo(this.frameDiv);
        this.dataReadingDiv = $('<div>').css(panelStyle.dataReadingDiv).appendTo(this.frameDiv);
        if (this.config.legend.style == 'none') {
            this.legendDiv.css('display', 'none');
        }
        else if (this.config.legend.style !== 'side') {
            this.legendDiv.css({
                top: '2.8em',
                left: `calc(${divWidth-legendDivWidth}px - 3em)`,
                padding: '0.5em',
                background: this.style.pageBackgroundColor, 
                border: '1px solid gray',
                'border-radius': '7px',
            });
            if (this.config.legend.style == 'hidden') {
                new JGInvisibleWidget(this.legendDiv, { sensingObj: this.div, group: 'legend', opacity: 1 });
            }
        }

        let [svgWidth, svgHeight] = [ this.plotDiv.get().offsetWidth, this.plotDiv.get().offsetHeight ];
        if (! (svgWidth > 0) || ! (svgHeight > 0)) {
            // window being resized
            return;
        }
        
        this.svg = $('<svg>', 'svg').appendTo(this.plotDiv).attr({
            "xmlns": "http://www.w3.org/2000/svg",
            "xmlns:xlink": "http://www.w3.org/1999/xlink",
            "version": "1.1",
        });
        this.svg.css({
            position: 'absolute',
            top: '0px',
            left: '0px',
            width: svgWidth + 'px',
            height: svgHeight + 'px',
        });

        const referencePlotWidth = 640, referencePlotHeight = 480;
        let sizeRatio = Math.min(svgWidth / referencePlotWidth, svgHeight / referencePlotHeight);
        let plotScaling = 1;
        if (sizeRatio > 0.7) {
            plotScaling = 1;
        }
        else {
            plotScaling = sizeRatio /0.7;
        }
        const width = svgWidth / plotScaling;
        const height = svgHeight / plotScaling;
        this.svg.attr({"viewBox": `0 0  ${width} ${height}`});
        
        const titleHeight = 30;
        const scaleBarWidth = 10, scaleLabelWidth = 80, scaleVerticalMargin = 60;
        const scaleHeight = height - titleHeight - scaleVerticalMargin;
        
        const drawWidth = width - scaleBarWidth - scaleLabelWidth, drawHeight = height - titleHeight;
        let [x0, y0, x1, y1] = [0, 0, parseFloat(this.map.width ?? 1), parseFloat(this.map.height ?? 1)];
        if (! (x1 > x0)) x1 = x0+1;
        if (! (y1 > x0)) y1 = y0+1;
        let [dx, dy] = [0, 0];
        if ((y1-y0)/(x1-x0) > drawHeight/drawWidth) {
            dx = (y1-y0) * drawWidth/drawHeight - (x1-x0);
            x0 -= dx/2;
            x1 += dx/2;
        }
        else {
            dy = (x1-x0) * drawHeight/drawWidth - (y1-y0);
            y0 -= dy/2;
            y1 += dy/2;
        }
       
        this.drawingArea = $('<g>', 'svg').appendTo(this.svg).attr({
            'transform': `translate(0 ${titleHeight}) scale(${drawWidth/(x1-x0)} ${drawHeight/(y1-y0)}) translate(${-x0} ${-y0})`,
            'fill': 'gray',
            'stroke': 'none',
        });
        this.scaleArea = $('<g>', 'svg').appendTo(this.svg);
        
        let titleArea = $('<g>', 'svg').appendTo(this.svg).attr({
            'font-family': 'sans-serif',
            'font-size': '20px',
            'dominant-baseline': 'middle',
            'stroke': null,
            'fill': this.style.strokeColor,
        });
        $('<text>', 'svg').appendTo(titleArea).attr({
            x: 0, y: titleHeight/2,
            'text-anchor': 'begin',
        }).text(config.axes?.title ?? config.channel ?? '');
        
        for (let itemConf of this.map.items ?? []) {
            const shape = $.sanitize(itemConf.shape);
            if (itemConf.shape === shape) {
                let elem = $(`<${shape}>`, 'svg').attr(itemConf.attr).appendTo(this.drawingArea);
                elem.addClass('sd-map-element').data('sd-index', itemConf.index ?? null);
                elem.data('sd-org-stroke', elem.attr('stroke') ?? '');
                elem.data('sd-org-stroke-width', elem.attr('stroke-width') ?? '');
            }
        }

        this.scale = new JGPlotColorBarScale(0, 1, false, {
            x: drawWidth + scaleBarWidth, y: titleHeight + scaleVerticalMargin/2,
            length: scaleHeight,
            scaleBarWidth: scaleBarWidth,
            labelMargin: scaleLabelWidth,
            labelPosition: 'right',
            colorCoding: this.config.colorCoding ?? 'Parula',
            ticksOutwards: true,
            frameColor: this.style.plotLabelColor, // LabelColor on purpose
            labelColor: this.style.plotLabelColor,
            title: this.config.axes?.ytitle ?? this.config.channel,
        });

        
        //// Data Reading ////
        
        this.dataReadingDiv.data('cursorLabel', '');
        this.plotDiv.bind('mouseover', e=>{
            const elem = $(e.target).closest('.sd-map-element');
            if (elem.size() > 0) {
                const [x, y] = [elem.data('sd-index'), elem.data('sd-value')];
                elem.attr('stroke', this.style.plotFrameColor);
                elem.attr('stroke-width', '0.01');
                this.dataReadingDiv.text('(' + x + ', ' + y + ')');
            }
            else {
                this.dataReadingDiv.text('');
            }
        });
        this.plotDiv.bind('mouseout', e=>{
            const elem = $(e.target).closest('.sd-map-element');
            elem.attr('stroke', elem.data('sd-org-stroke'));
            elem.attr('stroke-width', elem.data('sd-org-stroke-width'));
        });
    }

    
    openSettings(div) {
        let inputsDiv = $('<div>').appendTo(div);
        inputsDiv.html(`
            <table style="margin-top:1em">
              <tr><th>Map Name</th><td><input list="sd-map-datalist"></td></tr>
              <tr><th>Channel</th><td><input list="sd-histgraph-datalist"></td></tr>
              <tr><th>Title</th><td><input placeholder="auto"></td></tr>
              <tr><td>---</td><td></td></tr>
              <tr><th>Axis Title</th><td><input placeholder="empty"></td></tr>
              <tr><th>Range</th><td><label><input type="radio" name="yrange">Fixed</label>: <input>-<input></td></tr>
              <tr><td></td><td><label><input type="radio" name="yrange">Auto</label></td></tr>
              <tr><td></td><td><label><input type="checkbox">log</label></td></tr>
              <tr><th>Legend Style</th><td><select>
                <option value="side">Side Panel</option>
                <option value="box">Corner Box</option>
                <option value="hidden">Hidden Corner Box</option>
                <option value="none">None</option>
              </select></td></tr>
              <tr><td>---</td><td></td></tr>
              <tr><th>Color Coding</th><td><select>
                  <option value="Parula">Parula</option>
                  <option value="Viridis">Viridis</option>
                  <option value="Magma">Magma</option>
                  <option value="Rainbow">Rainbow</option>
                  <option value="Gray">Gray</option>
                  <hr/>
                  <option value="UWGold">UWGold</option>
                  <option value="UW">UW</option>
                  <option value="MIT">MIT</option>
                  <option value="KIT">KIT</option>
              </select></td></tr>
              <tr><th>No-data Color</th><td><input type="color"></td></tr>
            </table>
        `);

        if (! this.config.axes) {
            this.config.axes = {
                ylog: false,
                yfixed: false,
                ymin: 0,
                ymax: 1,
                ytitle: '',
                title: '',
            }
        }

        let k = 0;
        bindInput(this.config, 'map', inputsDiv.find('input').at(k++).css('width', '20em'));
        bindInput(this.config, 'channel', inputsDiv.find('input').at(k++).css('width', '20em'));
        bindInput(this.config.axes, 'title', inputsDiv.find('input').at(k++).css('width', '20em'));
        bindInput(this.config.axes, 'ytitle', inputsDiv.find('input').at(k++).css('width', '20em'));
        bindInput(this.config.axes, 'yfixed', inputsDiv.find('input').at(k++), true);
        bindInput(this.config.axes, 'ymin', inputsDiv.find('input').at(k++).css('width', '5em'));
        bindInput(this.config.axes, 'ymax', inputsDiv.find('input').at(k++).css('width', '5em'));
        bindInput(this.config.axes, 'yfixed', inputsDiv.find('input').at(k++), false);
        bindInput(this.config.axes, 'ylog', inputsDiv.find('input').at(k++), true);
        bindInput(this.config.legend, 'style', inputsDiv.find('select').at(0));
        bindInput(this.config, 'colorCoding', inputsDiv.find('select').at(1).css('width', '12em'));
        bindInput(this.config, 'emptyColor', inputsDiv.find('input').at(k++).css('width', '5em'));
    }

    
    fillInputChannels(inputChannels) {
        if (this.config.channel) {
            inputChannels.push(this.config.channel);
        }
    }

    
    draw(dataPacket, displayTimeRange=null) {
        if ((dataPacket === null) || (dataPacket.__meta?.isPartial ?? false)) {
            return;
        }
        if (! this.config.channel) {
            return;
        }
        if (! this.drawingArea) {
            return; 
       }

        let data = dataPacket[this.config.channel]?.x;
        if (! data) {
            if (Panel._dataPacketIncludes(dataPacket, this.currentDataTime)) {
                return; // keep the drawing from the last "current"
            }
            data = { 'x': [], 'y': [] };
        }
        if (dataPacket.__meta?.isCurrent ?? false) {
            this.currentDataTime = dataPacket.__meta.currentDataTime;
        }
        
        if (Array.isArray(data)) {
            if (data.length > 0) {
                data = data[data.length-1];
            }
            else {
                data = { 'x': [], 'y': [] };
            }
        }
        if (typeof(data) == "string") {
            try {
                data = JSON.parse(data);
            }
            catch(error) {
                data = { 'x': [], 'y': [] };
            }
        }

        let values = {};
        let [ymin, ymax] = [null, null];
        if (data.y?.length > 0) {
            const y = data.y;
            const n = Math.min(data.y.length);
            const x = (data.x?.length == data.y.length) ? data.x : [... Array(n)].map((_, i)=>i);
            for (let k = 0; k < n; k++) {
                const [xk, yk] = [ x[k], y[k] ];
                if (! isNaN(xk) && ! isNaN(yk)) {
                    values[Math.round(xk)] = yk;
                    [ ymin, ymax ] = [ Math.min(ymin??yk, yk), Math.max(ymax??yk, yk) ];
                }
            }
        }
        else if (((data.counts ?? []).length > 0) && data.bins) {
            const histogram = data;
            const nbins = histogram.counts.length;
            const binwidth = (histogram.bins.max - histogram.bins.min) / nbins;
            for (let k = 0; k < nbins; k++) {
                const x = Math.floor(histogram.bins.min + (k+0.5)*binwidth);
                const y = histogram.counts[k];
                if (! isNaN(y)) {
                    values[x] = y;
                    ymax = Math.max(ymax??y, y);
                }
            }
            ymin = 0;
        }

        if (ymin !== null) {
            if (this.config.axes?.yfixed ?? false) {
                ymin = this.config.axes?.ymin ?? 0;
                ymax = this.config.axes?.ymax ?? (ymin + 1);
            }
            else if (! this.config.axes?.ylog ?? false) {
                if ((ymin > 0) && (ymin / ymax < 0.1)) {
                    ymin = 0;
                }
            }
            if (ymin >= ymax) {
                ymax = ymin + 1;
            }
        }

        //// Draw ////
        this.scaleArea.empty();
        this.scale.setRange(ymin, ymax, this.config.axes?.ylog ?? false);
        this.scale.draw(this.scaleArea);

        for (let elem of this.drawingArea.find('.sd-map-element').enumerate()) {
            const index = elem.data('sd-index');
            if ((index === null) || isNaN(parseInt(index))) {
                continue;
            }
            const y = values[index];
            if ((y === undefined) || (y === null)) {
                elem.attr('fill', this.config.emptyColor ?? '#ff0000');
                elem.data('sd-value', '--');
            }
            else {
                elem.attr('fill', this.scale.colorNameOf(y));
                elem.data('sd-value', y);
            }
        }
    }
};
