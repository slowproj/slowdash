// panel-plot.mjs //
// Author: Sanshiro Enomoto <sanshiro@uw.edu> //
// Created on 18 November 2021 //
// Refactored on 18 June 2022 //


export { TimeAxisPlotPanel, PlotPanel };
 
import { JG as $, JGDateTime } from './jagaimo/jagaimo.mjs';
import { JGTabWidget, JGInvisibleWidget } from './jagaimo/jagawidgets.mjs';
import { JGPlotWidget, JGPlotAxisScale } from './jagaimo/jagaplot.mjs';
import { Panel, bindInput, getPaletteColor } from './panel.mjs';


class Plot {
    configure(config, axes, legend, panel) {
        this.config = config;
        this.axes = axes;
        this.legend = legend;
        this.panel = panel;

        if (this.config.label === undefined) {
            this.config.label = '';
        }
        if (this.config.format === undefined) {
            this.config.format = '%.5g';
        }
        if (this.config.color === undefined) {
            this.config.color = getPaletteColor(0);
        }
        if (this.config.opacity === undefined) {
            this.config.opacity = 1;
        }

        this.label = $('<span>').appendTo(this.legend).text(this.getLabel()).css({
            'color': config.color,
            'font-weight':'bold',
        });
        this.stat = $('<div>').appendTo(this.legend).css({
            'display': 'inline-block',
            'margin-left': '1em',
        });
    }

    setStyle(style) {
        if (style?.title && ! this.panel.config.axes?.title) {
            this.axes.setTitle(style.title);
        }
        if (style?.xtitle && ! this.panel.config.axes?.xtitle) {
            this.axes.setXTitle(style.xtitle);
        }
        if (style?.ytitle && ! this.panel.config.axes?.ytitle) {
            this.axes.setYTitle(style.ytitle);
        }
        if (style?.ztitle && ! this.panel.config.axes?.ztitle) {
            this.axes.setZTitle(style.ztitle);
        }
    }
    
    setStat(stat) {
        if ($.isDict(stat)) {
            this.stat.empty().css('display', '');
            let table = $('<table>').appendTo(this.stat);
            for (const key in stat) {
                let tr = $('<tr>').appendTo(table);
                $('<td>').appendTo(tr).text(key);
                $('<td>').appendTo(tr).text(stat[key])/*.css('text-align', 'right')*/;
            }
        }
        else {
            this.stat.css('display', 'inline-block');
            this.stat.text(String(stat));
        }
    }
    
    openSettings(div) {
        div.html(`
            <table>
              <tr><td>Channel</td><td><input list="sd-numeric-datalist"></td></tr>
              <tr><td>Label</td><td><input placeholder="auto"></td></tr>
              <tr><td>Format</td><td><input placeholder="%f"></td></tr>
              
            </table>
        `);
        let table = div.find('table');

        let k = 0;
        if (this.config.channelX && this.config.channelY) {
            table.find('tr:first-child').remove();
            table.prepend($('<tr>').html(`<td>Channel Y</td><td><input list="sd-numeric-datalist"></td>`));
            table.prepend($('<tr>').html(`<td>Channel X</td><td><input list="sd-numeric-datalist"></td>`));
            bindInput(this.config, 'channelX', div.find('input').at(k++).css('width', '20em'));
            bindInput(this.config, 'channelY', div.find('input').at(k++).css('width', '20em'));
        }
        else {
            bindInput(this.config, 'channel', div.find('input').at(k++).css('width', '20em'));
        }
        bindInput(this.config, 'label', div.find('input').at(k++).css('width', '20em'));
        bindInput(this.config, 'format', div.find('input').at(k++).css('width', '5em'));
        if (this.config.color) {
            table.append($('<tr>').html(`
              <tr><td>Color</td><td><input type="color">, Opacity: <input type="number" step="0.05" min="0" max="1" placeholder="1"></td></tr>
            `));
            bindInput(this.config, 'color', div.find('input').at(k++).css('width', '5em'));
            bindInput(this.config, 'opacity', div.find('input').at(k++).css('width', '5em'));
        }
    }
    
    fillInputChannels(inputChannels) {
        for (const field of ['channel', 'channelX', 'channelY']) {
            if (this.config[field] !== undefined) {
                inputChannels.push(this.config[field]);
            }
        }
    }
    
    draw(dataPacket) {}

    getLabel() {
        if ((this.config.label ?? '') !== '') {
            return this.config.label;
        }
        if ((this.config.channel ?? '') !== '') {
            return this.config.channel;
        }
        if (
            ((this.config.channelX ?? '') !== '') &&
            ((this.config.channelY ?? '') !== '')
        ){
            return this.config.channelX + ',' + this.config.channelY;
        }
        return 'untitled';
    }

    getXRange() { return [0, 1]; }
    getYRange() { return [0, 1]; }
    getZRange() { return [0, 1]; }
};


class HistogramPlot extends Plot {
    configure(config, axes, legend, panel) {
        if (! config.opacity) {
            config.opacity = 0.2;
        }
        super.configure(config, axes, legend, panel);

        this.histogram = {
            bins: { min: 0, max: 1 }, 
            counts: [],
            style: { 
                lineWidth: 1, lineColor: config.color,
                fillColor: config.color, fillOpacity: config.opacity,
            },
        };
        this.axes.addHistogram(this.histogram);
    }

    setStyle(style) {
        super.setStyle(style);        
        if (style?.color) {
            let color = parseInt(style.color);
            color = isNaN(color) ? style.color : getPaletteColor(color);
            this.histogram.style.lineColor = color;
            this.histogram.style.fillColor = color;
            this.label.css('color', color);
        }
        if (style?.opacity) {
            this.histogram.style.fillOpacity = style.opacity;
        }
    }

    draw(dataPacket) {
        let data = dataPacket.data[this.config.channel]?.x;
        if (! data) {
            if (! dataPacket.isTransitional) {
                this.histogram.counts = [];
            }
            return;
        }
        if (Array.isArray(data)) {
            if (data.length < 1) {
                return;
            }
            data = data[data.length-1];
        }
        if (typeof(data) == "string") {
            try {
                data = JSON.parse(data);
            }
            catch(error) {
                return;
            }
        }
        if (data._attr) {
            this.setStyle(data._attr);
        }
        if (data._stat) {
            this.setStat(data._stat);
        }
        if (! data.bins) {
            return;
        }
        const histogram = data;
        
        if (histogram.bins.min === undefined || histogram.bins.max == undefined || ! histogram.counts) {
            this.histogram.counts = Array(this.histogram.counts.length).fill(0);
            return;
        }

        this.histogram.bins.min = histogram.bins.min;
        this.histogram.bins.max = histogram.bins.max;
        this.histogram.counts = histogram.counts;
    }

    getXRange() {
        return [ this.histogram.bins.min, this.histogram.bins.max ];
    }
    getYRange() {
        return [ 0, this.histogram.counts.reduce((a,b)=>Math.max(a,b), 1) ];
    }
};



class TimeseriesHistogramPlot extends HistogramPlot {
    configure(config, axes, legend, panel) {
        super.configure(config, axes, legend, panel);
    }
    
    openSettings(div) {
        super.openSettings(div);
        let table = div.find('table');
        let tr = $('<tr>').appendTo(table);
        $('<td>').text('Bins').appendTo(tr);
        let td = $('<td>').appendTo(tr);
        $('<span>').text('n: ').appendTo(td);
        let nInput = $('<input>').attr({type:"number",placeholder:'auto'}).appendTo(td);
        $('<span>').text(', min: ').appendTo(td);
        let binminInput = $('<input>').attr({type:"number",placeholder:'auto'}).appendTo(td);
        $('<span>').text(', max: ').appendTo(td);
        let binmaxInput = $('<input>').attr({type:"number",placeholder:'auto'}).appendTo(td);

        if (! this.config.bins) {
            this.config.bins = {n: null, min: null, max: null};
        }
        bindInput(this.config.bins, 'n', nInput.css('width', '5em'));
        bindInput(this.config.bins, 'min', binminInput.css('width', '5em'));
        bindInput(this.config.bins, 'max', binmaxInput.css('width', '5em'));
    }
    
    draw(dataPacket) {
        let ts = dataPacket.data[this.config.channel];
        if (! ts) {
            if (! dataPacket.isTransitional) {
                this.setStat('---');
                this.histogram.counts = [];
            }
            return;
        }
        if ((ts?.x === undefined) || (Array.isArray(ts.x) && (ts.x.length <= 0))) {
            this.setStat('---');
            return;
        }
        if (! (Array.isArray(ts.x))) {
            ts.x = [ ts.x ];
        }
        
        let nbins = parseInt(this.config.bins?.n ?? null);
        let min = parseFloat(this.config.bins?.min ?? null);
        let max = parseFloat(this.config.bins?.max ?? null);
        if (isNaN(parseInt(nbins))) {
            nbins = null;
        }
        if (isNaN(parseFloat(min))) {
            min = ts.x.reduce((a,b)=>Math.min(a,b), ts.x[0]);
        }
        if (isNaN(parseFloat(max))) {
            max = ts.x.reduce((a,b)=>Math.max(a,b), ts.x[0]);
        }
        if (min >= max) {
            max = min + 1;
        }
        if ((nbins === null) || isNaN(parseFloat(nbins)) || ! (nbins > 0)) {
            if (ts.x.length < 10) {
                nbins = 10;
            }
            else if (ts.x.length < 100) {
                nbins = 20;
            }
            else if (ts.x.length < 500) {
                nbins = 50;
            }
            else {
                nbins = 100;
            }
        }
        let binOf = x => {
            if (x < min || x >= max) return null;
            return Math.floor(nbins * (x - min) / (max - min));
        };

        this.histogram.bins.min = min;
        this.histogram.bins.max = max;
        this.histogram.counts = Array(nbins);
        this.histogram.counts.fill(0);

        let lastValue = null;
        for (let xk of ts.x) {
            if (xk === null) {
                continue;
            }
            lastValue = xk;
            const bin = binOf(xk);
            if (bin !== null) {
                this.histogram.counts[bin] += 1;
            }
        }
        this.setStat($.sprintf(this.config.format || '%f', lastValue));
    }
};


class Histogram2dPlot extends Plot {
    configure(config, axes, legend, panel) {
        super.configure(config, axes, legend, panel);
        this.config.color = undefined;
        this.config.opacity = undefined;
        
        this.histogram2d = {
            xbins: { min: 0, max: 1 },
            ybins: { min: 0, max: 1 }, 
            counts: [],
            style: {},
        };
        this.axes.addHistogram2d(this.histogram2d);
    }

    openSettings(div) {
        super.openSettings(div);
    }
    
    setStyle(style) {
        super.setStyle(style);
    }

    draw(dataPacket) {
        let data = dataPacket.data[this.config.channel]?.x;
        if (! data) {
            if (! dataPacket.isTransitional) {
                this.histogram2d.counts = [];
            }
            return;
        }
        if (Array.isArray(data)) {
            if (data.length < 1) {
                return;
            }
            data = data[data.length-1];
        }
        if (typeof(data) == "string") {
            try {
                data = JSON.parse(data);
            }
            catch(error) {
                return;
            }
        }
        if (data._attr) {
            this.setStyle(data._attr);
        }
        if (data._stat) {
            this.setStat(data._stat);
        }
        if (! data.xbins || ! data.ybins) {
            return;
        }
        const histogram = data;
        
        if (
            (histogram.xbins.min === undefined || histogram.xbins.max == undefined) || 
            (histogram.ybins.min === undefined || histogram.ybins.max == undefined) || 
            ! histogram.counts
        ){
            return;
        }

        this.histogram2d.xbins.min = histogram.xbins.min;
        this.histogram2d.xbins.max = histogram.xbins.max;
        this.histogram2d.ybins.min = histogram.ybins.min;
        this.histogram2d.ybins.max = histogram.ybins.max;
        this.histogram2d.counts = histogram.counts;
    }

    getXRange() {
        return [ this.histogram2d.xbins.min, this.histogram2d.xbins.max ];
    }
    getYRange() {
        return [ this.histogram2d.ybins.min, this.histogram2d.ybins.max ];
    }
    getZRange() {
        let max = 1;
        for (const yslice of this.histogram2d.counts) {
            for (const x of yslice) {
                if (x > max) max = x;
            }
        }
        return [ 0, max ];
    }
};



class GraphPlot extends Plot {
    configure(config, axes, legend, panel) {
        super.configure(config, axes, legend, panel);
        this.graph = {
            x: [],
            y: [],
            style: {}
        };

        this.valueRange = {xmin: 0, xmax: 1, ymin: 0, ymax: 1};
    }

    setStyle(style) {
        super.setStyle(style);
    }

    openSettings(div) {
        super.openSettings(div);
    }
    
    draw(dataPacket) {
        let data = dataPacket.data[this.config.channel]?.x;
        if (! data) {
            if (! dataPacket.isTransitional) {
                this.graph.y = [];
            }
            return;
        }
        if (Array.isArray(data)) {
            if (data.length < 1) {
                this.graph.y = [];
                return;
            }
            data = data[data.length-1];
        }
        if (typeof(data) == "string") {
            try {
                data = JSON.parse(data);
            }
            catch(error) {
                this.graph.y = [];
                return;
            }
        }
        if (data._attr) {
            this.setStyle(data._attr);
        }
        if (data._stat) {
            this.setStat(data._stat);
        }
        if (! (data.y?.length > 0)) {
            this.graph.y = [];
            return;
        }
        
        const y = data.y ? data.y : []
        const x = (data.x?.length == y.length) ? data.x : [... Array(y.length)].map((_, i)=>i);
        this.graph.x = x;
        this.graph.y = y;
        if (data.x_err?.length == y.length) {
            this.graph.x_err = data.x_err;
        }
        if (data.y_err?.length == y.length) {
            this.graph.y_err = data.y_err;
        }
            
        let [xmin, xmax, ymin, ymax] = [null, null, null, null];
        for (let k = 0; k < x.length; k++) {
            const xk_err = this.graph?.x_err ? this.graph.x_err[k] : 0;
            const yk_err = this.graph?.y_err ? this.graph.y_err[k] : 0;
            if (! isNaN(x[k]) && ! isNaN(y[k])) {
                [ xmin, xmax ] = [ Math.min(xmin??x[k], x[k]-xk_err), Math.max(xmax??x[k], x[k]+xk_err) ];
                [ ymin, ymax ] = [ Math.min(ymin??y[k], y[k]-yk_err), Math.max(ymax??y[k], y[k]+yk_err) ];
            }
        }
        if ((xmin === null) || (ymin === null)) {
            [xmin, xmax, ymin, ymax] = [0, 1, 0, 1];
        }
        this.valueRange = {xmin: xmin, xmax: xmax, ymin: ymin, ymax: ymax};
    }

    getXRange() {
        return [this.valueRange.xmin, this.valueRange.xmax];
    }
    getYRange() {
        return [this.valueRange.ymin, this.valueRange.ymax];
    }
};


class LineMarkerPlot extends GraphPlot {
    configure(config, axes, legend, panel) {
        super.configure(config, axes, legend, panel);
        if (! config.marker_type) {
            config.marker_type = 'circle';
        }
        if (config.marker_size === undefined) {
            config.marker_size = 2;
        }
        if (config.line_width === undefined) {
            config.line_width = 1;
        }
        if (config.line_type === undefined) {
            config.line_type = 'connect';
        }
        if (config.fill_opacity === undefined) {
            config.fill_opacity = 0;
        }
        if (config.fill_baseline === undefined) {
            config.fill_baseline = 1e-100;
        }

        this.graph.style = {
            lineWidth: config.line_width, lineColor: config.color,
            markerType: config.marker_type, markerSize: config.marker_size, 
            markerColor: config.color, markerOpacity: config.opacity,
            lineType: config.line_type,
            fillColor: config.color, fillOpacity: config.fill_opacity, fillBaseline: config.fill_baseline,
        };
        this.axes.addGraph(this.graph);
    }

    setStyle(style) {
        super.setStyle(style);
        if (style?.color) {
            let color = parseInt(style.color);
            color = isNaN(color) ? style.color : getPaletteColor(color);
            this.graph.style.lineColor = color;
            this.graph.style.fillColor = color;
            this.graph.style.markerColor = color;
            this.label.css('color', color);
        }
        if (style?.line_width) {
            this.graph.style.lineWidth = line_width;
        }
        if (style?.marker_type) {
            this.graph.style.markerType = marker_type;
        }
        if (style?.marker_size) {
            this.graph.style.markerSize = marker_size;
        }
        if (style.opacity) {
            this.graph.style.markerOpacity = style.opacity;
        }
        if (style.fill_opacity) {
            this.graph.style.fillOpacity = style.fill_opacity;
        }
    }

    openSettings(div) {
        super.openSettings(div);
        let table = div.find('table');
        let k = table.find('input').size();
        table.append($('<tr>').html(`
            <td>Marker</td><td>type: <select>
                <option value="circle">circle</option>
                <option value="square">square</option>
                <option value="diamond">diamond</option>
                <option value="triangle">triangle</option>
                <option value="opencircle">opencircle</option>
                <option value="opensquare">opensquare</option>
                <option value="opendiamond">opendiamond</option>
                <option value="opentriangle">opentriangle</option>
            </select>,
            size: <input type="number" step="any" min="0"></td>
        `));
        table.append($('<tr>').html(`
            <td>Line</td><td>width: <input type="number" step="any" min="0">, 
            type: <select>
                <option value="connect">connect</option>
                <option value="last">last</option>
            </select></td>
        `));
        table.append($('<tr>').html(`
            <td>Fill</td><td>opacity: <input type="number" step="0.05" min="0" max="1">, baseline: <input type="number" step="any"></td>
        `));

        bindInput(this.config, 'marker_type', div.find('select').at(0).css('width', '7em'));
        bindInput(this.config, 'marker_size', div.find('input').at(k++).css('width', '5em'));
        bindInput(this.config, 'line_width', div.find('input').at(k++).css('width', '5em'));
        bindInput(this.config, 'line_type', div.find('select').at(1).css('width', '7em'));
        bindInput(this.config, 'fill_opacity', div.find('input').at(k++).css('width', '5em'));
        bindInput(this.config, 'fill_baseline', div.find('input').at(k++).css('width', '5em'));
    }
};


class BarChartPlot extends GraphPlot {
    configure(config, axes, legend, panel) {
        super.configure(config, axes, legend, panel);

        this.graph.style = {
            barWidth: config.bar_width, fillColor: config.color, fillOpacity: config.opacity,
        };
        this.axes.addBarChart(this.graph);
    }

    setStyle(style) {
        super.setStyle(style);
        if (style?.color) {
            let color = parseInt(style.color);
            color = isNaN(color) ? style.color : getPaletteColor(color);
            this.graph.style.fillColor = color;
        }
        if (style?.bar_width) {
            this.graph.style.barWidth = bar_width;
        }
        if (style.opacity) {
            this.graph.style.fillOpacity = style.opacity;
        }
    }

    openSettings(div) {
        super.openSettings(div);
        let table = div.find('table');
        let k = table.find('input').size();
        table.append($('<tr>').html(`<td>Bar</td><td>width: <input></td>`));
        table.append($('<tr>').html(`<td>Bar Label</td><td>format: <input></td>`));

        bindInput(this.config, 'bar_width', div.find('input').at(k++).css('width', '5em'));
        bindInput(this.config, 'bar_label_format', div.find('input').at(k++).css('width', '5em'));
    }
};


class TimeseriesScatterPlot extends GraphPlot {
    configure(config, axes, legend, panel) {        
        if (! (config.opacity >= 0)) {
            config.opacity = 0.5;
        }
        if (! config.marker_type) {
            config.marker_type = 'circle';
        }
        if (! (config.marker_size > 0)) {
            config.marker_size = 3;
        }
        if (! config.format || config.format.length == 0) {
            config.format = '%f, %f';
        }
        if (config.line_width === undefined) {
            config.line_width = 0;
        }

        super.configure(config, axes, legend, panel);
        
        this.graph.style = {
            lineWidth: config.line_width, lineColor: config.color, lineOpacity: config.opacity,
            markerType: config.marker_type, markerSize: config.marker_size, 
            markerColor: config.color, markerOpacity: config.opacity,
        };
        this.axes.addGraph(this.graph);
    }

    setStyle(style) {
        super.setStyle(style);
        if (style?.color) {
            let color = parseInt(style.color);
            color = isNaN(color) ? style.color : getPaletteColor(color);
            this.graph.style.lineColor = color;
            this.graph.style.markerColor = color;
            this.label.css('color', color);
        }
        if (style?.line_width) {
            this.graph.style.lineWidth = line_width;
        }
        if (style?.marker_type) {
            this.graph.style.markerType = marker_type;
        }
        if (style?.marker_size) {
            this.graph.style.markerSize = marker_size;
        }
        if (style.opacity) {
            this.graph.style.markerOpacity = style.opacity;
        }
    }

    openSettings(div) {
        super.openSettings(div);
        let table = div.find('table');
        let k = table.find('input').size();
        table.append($('<tr>').html(`
            <td>Marker</td><td>type: <select>
                <option value="circle">circle</option>
                <option value="square">square</option>
                <option value="diamond">diamond</option>
                <option value="triangle">triangle</option>
                <option value="opencircle">opencircle</option>
                <option value="opensquare">opensquare</option>
                <option value="opendiamond">opendiamond</option>
                <option value="opentriangle">opentriangle</option>
            </select>,
            size: <input type="number" step="any" min="0"></td>
        `));
        table.append($('<tr>').html(`
            <td>Line</td><td>width: <input type="number" step="any" min="0"></td>
        `));

        bindInput(this.config, 'marker_type', div.find('select').at(0).css('width', '7em'));
        bindInput(this.config, 'marker_size', div.find('input').at(k++).css('width', '5em'));
        bindInput(this.config, 'line_width', div.find('input').at(k++).css('width', '5em'));
    }


    
    draw(dataPacket) {
        let ts0 = dataPacket.data[this.config.channelX];
        let ts1 = dataPacket.data[this.config.channelY];
        if (! ts0 || ! ts1) {
            if (! dataPacket.isTransitional) {
                this.setStat('---');
                this.graph.x = [];
                this.graph.y = [];
            }
            return;
        }
        this.setStat('---');
        this.graph.x = [];
        this.graph.y = [];
        if (
            ((ts0?.x === undefined) || (ts0.x.length <= 0)) ||
            ((ts1?.x === undefined) || (ts1.x.length <= 0))
        ){
            return;
        }

        const n = Math.min(ts0.x.length, ts1.x.length);
        
        let [xmin, xmax, ymin, ymax] = [null, null, null, null];
        for (let k = 0; k < n; k++) {
            if ((ts0.x[k] === null) || (ts1.x[k] === null)) {
                continue;
            }
            const [xk, yk] = [ts0.x[k], ts1.x[k]];
            this.graph.x.push(xk);
            this.graph.y.push(yk);
            [ xmin, xmax ] = [ Math.min(xmin??xk, xk), Math.max(xmax??xk, xk) ];
            [ ymin, ymax ] = [ Math.min(ymin??yk, yk), Math.max(ymax??yk, yk) ];
        }
        
        if (this.graph.x.length < 1) {
            [xmin, xmax, ymin, ymax] = [0, 1, 0, 1];
        }
        this.valueRange = {xmin: xmin, xmax: xmax, ymin: ymin, ymax: ymax};

        if (this.graph.x.length > 0) {
            const xn = this.graph.x[this.graph.x.length-1];
            const yn = this.graph.y[this.graph.y.length-1];
            this.setStat($.sprintf(this.config.format || '%f, %f', xn, yn));
        }
    }
};



class TimeseriesPlot extends LineMarkerPlot {
    configure(config, axes, legend, panel) {
        super.configure(config, axes, legend, panel);
    }
    
    draw(dataPacket) {
        let ts = dataPacket.data[this.config.channel];
        if (! ts) {
            if (! dataPacket.isTransitional) {
                this.setStat('---');
                this.graph.x = [];
                this.graph.y = [];
            }
            return;
        }
        if ((ts?.x === undefined) || (Array.isArray(ts.x) && (ts.x.length <= 0))) {
            this.setStat('---');
            return;
        }
        if (! (Array.isArray(ts.x))) {
            ts.t = [ ts.t ];
            ts.x = [ ts.x ];
        }

        const t0 = dataPacket.data[this.config.channel].start;
        this.graph.x = [];
        this.graph.y = [];

        let [xmin, xmax, ymin, ymax] = [null, null, null, null];
        for (let k = 0; k < ts.x.length; k++) {
            const [xk, yk] = [t0 + ts.t[k], parseFloat(ts.x[k])];
            if (isNaN(yk)) {
                continue;
            }
            this.graph.x.push(xk);
            this.graph.y.push(yk);
            [ xmin, xmax ] = [ Math.min(xmin??xk, xk), Math.max(xmax??xk, xk) ];
            [ ymin, ymax ] = [ Math.min(ymin??yk, yk), Math.max(ymax??yk, yk) ];
        }
        
        if (this.graph.x.length < 1) {
            [xmin, xmax, ymin, ymax] = [t0, t0+3600, 0, 1];
        }
        this.valueRange = {xmin: xmin, xmax: xmax, ymin: ymin, ymax: ymax};

        if (this.graph.x.length > 0) {
            this.setStat($.sprintf(this.config.format || '%f', this.graph.y[this.graph.y.length-1]));
        }
    }
};



class PlotPanel extends Panel {
    static describe() {
        return { type: 'plot', label: 'XY Plot (Histograms and Graphs)' };
    }
    
    static buildConstructRows(table, on_done=config=>{}) {
        let tr1 = $('<tr>').html(`
            <td>Drawing</td><td>
            <select style="font-size:130%">
              <option hidden>Select...</option>
              <option value="histogram">Histogram Object</options>
              <option value="histogram2d">2D Histogram Object</options>
              <option value="graph">Graph Object</options>
              <option value="bar">Bar-Chart of Graph Object</options>
              <option value="ts-histogram">Histogram of Time-Series Values</options>
              <option value="ts-scatter">Scatter Plot of Time-Series Value Pairs</options>
            </select></td>
       `).appendTo(table);

        function updateSelection() {
            while (table.find('tr').size() > 2) {
                table.find('tr').at(2).remove();
            }
            let drawing = tr1.find('select').selected().attr('value');
            if (drawing == 'histogram') {
                let tr2 = $('<tr>').html(`
                    <td>Channel</td><td><input list="sd-histogram-datalist"></td>
                `).appendTo(table);
            }
            else if (drawing == 'histogram2d') {
                let tr2 = $('<tr>').html(`
                    <td>Channel</td><td><input list="sd-histogram2d-datalist"></td>
                `).appendTo(table);
            }
            else if (drawing == 'graph') {
                let tr2 = $('<tr>').html(`
                    <td>Channel</td><td><input list="sd-graph-datalist"></td>
                `).appendTo(table);
            }
            else if (drawing == 'bar') {
                let tr2 = $('<tr>').html(`
                    <td>Channel</td><td><input list="sd-graph-datalist"></td>
                `).appendTo(table);
            }
            else if (drawing == 'ts-histogram') {
                let tr2 = $('<tr>').html(`
                    <td>Channel</td><td><input list="sd-numeric-datalist"></td>
                `).appendTo(table);
            }
            else if (drawing == 'ts-scatter') {
                let tr2a = $('<tr>').html(`
                    <td>Channel-X</td><td><input list="sd-numeric-datalist"></td>
                `).appendTo(table);
                let tr2b = $('<tr>').html(`
                    <td>Channel-Y</td><td><input list="sd-numeric-datalist"></td>
                `).appendTo(table);
            }
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
                    type: 'plot',
                    plots: [{ type: drawing }]
                };
                if (drawing == 'ts-scatter') {
                    config.plots[0].channelX = table.find('input').at(0).val();
                    config.plots[0].channelY = table.find('input').at(1).val();
                }
                else {
                    config.plots[0].channel = table.find('input').val();
                }
                on_done(config);
            });
        }
        tr1.find('select').bind('change', e=>{ updateSelection(); });
    }

    
    constructor(div, style) {
        super(div, style);
        this.currentDataTimeRange = null;
    }

    
    configure(config, callbacks={}) {
        super.configure(config, callbacks);
        
        // defaults: not to make a copy of 'config', do not use $.extend() here
        if (this.config.plots === undefined) {
            this.config.plots = [];
        }
        if (this.config.axes === undefined) {
            this.config.axes = {};
        }
        if (this.config.axes.xfixed === undefined) {
            this.config.axes.xfixed = false;
        }
        if (this.config.axes.yfixed === undefined) {
            this.config.axes.yfixed = false;
        }
        if (this.config.axes.xlog === undefined) {
            this.config.axes.xlog = false;
        }
        if (this.config.axes.ylog === undefined) {
            this.config.axes.ylog = false;
        }
        if (this.config.axes.zlog === undefined) {
            this.config.axes.zlog = false;
        }
        if (this.config.legend === undefined) {
            this.config.legend = { style: null };
        }
        if (! ['side', 'box', 'transparent', 'hidden', 'none'].includes(this.config.legend.style)) {
            this.config.legend.style = 'side';
        }

        const legendWidthFraction = 0.3;
        const divWidth = this.div.boundingClientWidth();
        const legendDivWidth = divWidth * legendWidthFraction;
        const plotDivWidth = divWidth * (1 - ((config.legend?.style == 'side') ? legendWidthFraction : 0.0));
        let legendFontSize = window.getComputedStyle(this.div.get()).getPropertyValue('font-size');
        if (! (legendDivWidth / parseFloat(legendFontSize) > 16)) {
            legendFontSize = legendDivWidth / 16.0 + "px";
        }
        
        const panelStyle = {
            frameDiv: {
                'position': 'relative',
            },
            plotDiv: {
                'width': plotDivWidth + 'px',
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
        };
        
        let downloadBtn = $('<button>').html('&#x1f4e5;').prependTo(this.ctrlDiv);
        downloadBtn.attr('title', 'Download').bind('click', e=>{
            this.download();
        });
        let captureBtn = $('<button>').html('&#x1f4f8;').prependTo(this.ctrlDiv);
        captureBtn.attr('title', 'Save Image').bind('click', e=>{
            this.capture();
        });
        let snapBtn = $('<button>').html('&#x1f504;').prependTo(this.ctrlDiv);
        snapBtn.attr('title', 'Reset Zoom').bind('click', e=>{
            this.resetRange();
        });
        
        if (this.frameDiv) {
            this.frameDiv.empty();
        }
        else {
            this.frameDiv = $('<div>').css(panelStyle.frameDiv).appendTo(this.div);
        }
        this.plotDiv = $('<div>').css(panelStyle.plotDiv).appendTo(this.frameDiv);
        this.legendDiv = $('<div>').css(panelStyle.legendDiv).appendTo(this.frameDiv);

        if (this.config.legend.style == 'none') {
            this.legendDiv.css('display', 'none');
        }
        else if (this.config.legend.style !== 'side') {
            this.legendDiv.css({
                top: '40px',
                left: `calc(${divWidth-legendDivWidth}px - 3em)`,
                padding: '0.5em',
                background: this.style.pageBackgroundColor, 
                border: '1px solid gray',
                'border-radius': '7px',
            });
            if (this.config.legend.style == 'hidden') {
                new JGInvisibleWidget(this.legendDiv, { sensingObj: this.div, group: 'legend', opacity: 1 });
            }
            if (this.config.legend.style == 'transparent') {
                let color = this.style.pageBackgroundColor;
                const colorPattern = /rgb.*\( *([0-9\.]+), *([0-9\.]+), *([0-9\.]+)/;
                const c = color.match(colorPattern);
                if (c) {
                    color = `rgba(${c[1]},${c[2]},${c[3]},0.5)`;
                }
                else {
                    color = '';
                }
                this.legendDiv.css({ 'background': color });
            }
        }
        
        const w = plotDivWidth;
        const h = this.div.get().offsetHeight;
        const referencePlotWidth = 640, referencePlotHeight = 480;
        const sizeRatio = Math.min(w / referencePlotWidth, h / referencePlotHeight);
        const plotScaling = sizeRatio > 0.7 ? 1 : sizeRatio / 0.7;

        this.currentDataTimeRange = null;
        this.isTimeSeriesPlot = true;
        this.isQuadMeshPlot = false;
        
        this.plots = [];
        for (const plotconf of this.config.plots) {
            let plot = null;
            if (plotconf.type == 'timeseries') {
                plot = new TimeseriesPlot();
            }
            else if (plotconf.type == 'histogram') {
                plot = new HistogramPlot();
                this.isTimeSeriesPlot = false;
            }
            else if (plotconf.type == 'histogram2d') {
                plot = new Histogram2dPlot();
                this.isTimeSeriesPlot = false;
                this.isQuadMeshPlot = true;
            }
            else if (plotconf.type == 'ts-histogram') {
                plot = new TimeseriesHistogramPlot();
            }
            else if (plotconf.type == 'ts-scatter') {
                plot = new TimeseriesScatterPlot();
            }
            else if (plotconf.type == 'graph') {
                plot = new LineMarkerPlot();
                this.isTimeSeriesPlot = false;
            }
            else if (plotconf.type == 'bar') {
                plot = new BarChartPlot();
                this.isTimeSeriesPlot = false;
            }
            if (plot) {
                if (this.isQuadMeshPlot) {
                    if (this.config.axes.colorscale === undefined) {
                        this.config.axes.colorscale = 'Parula';
                    }
                }
                else if (plotconf.color === undefined) {
                    plotconf.color = getPaletteColor(this.plots.length);
                }
            }
            this.plots.push(plot);
        }
        
        this.axes = new JGPlotWidget(this.plotDiv, {
            width: w, height: h, labelScaling: plotScaling,
            colorScale: this.config.axes.colorscale,
            cursorDigits: 6,
            logX: this.config.axes.xlog,
            logY: this.config.axes.ylog,
            logZ: this.config.axes.zlog,
            ticksX: Math.floor(divWidth/300) + 2,
            ticksY: 4,
            ticksOutwards: this.style.plotTicksOutwards,
            grid: this.style.plotGridEnabled,
            plotAreaColor: this.style.plotBackgroundColor,
            plotMarginColor: this.style.plotMarginColor,
            frameColor: this.style.plotFrameColor,
            frameThickness: this.style.plotFrameThickness,
            labelColor: this.style.plotLabelColor,
            gridColor : this.style.plotGridColor,
            rangeSelect: (p, x0, x1, y0, y1) => { this.rangeSelect(x0, x1, y0, y1); },
        });

        for (let i = 0; i < this.plots.length; i++) {
            if (this.plots[i]) {
                let legendEntry = $('<div>').appendTo(this.legendDiv);
                this.plots[i].configure(this.config.plots[i], this.axes, legendEntry, this);
            }
        }
        
        let title = this.config.axes.title ?? '';
        if (title === '') {
            if (this.plots.length == 1) {
                title = this.plots[0].getLabel();
            }
        }
        this.axes.setTitle(title);
        this.axes.setXTitle(this.config.axes.xtitle ?? '');
        this.axes.setYTitle(this.config.axes.ytitle ?? '');
        this.axes.setZTitle(this.config.axes.ztitle ?? '');
    }


    openSettings(div) {
        div.css('display', 'flex');
        const boxStyle = {
            'border': 'thin solid',
            'border-radius': '5px',
            'margin': '5px',
            'padding': '5px',
        };
        
        let inputsDiv = $('<div>').appendTo(div).css(boxStyle);
        inputsDiv.html(`
            <span style="font-size:130%;font-weight:bold">Axes</span>
            <hr style="margin-bottom:2ex">
            <table style="margin-top:1em">
              <tr><th>Frame</th><td></td></tr>
              <tr><td>Title</td><td><input placeholder="auto"></td></tr>
              <tr><td>Legend</td><td><select>
                <option value="side">Side Panel</option>
                <option value="box">Corner Box</option>
                <option value="transparent">Transparent Corner Box</option>
                <option value="hidden">Hidden Corner Box</option>
                <option value="none">None</option>
              </select></td></tr>

              <tr><th>X Axis</th><td></td></tr>
              <tr><td>Title</td><td><input placeholder="empty"></td></tr>
              <tr><td>Range</td><td>
                  <label><input type="radio" name="xrange">Auto</label>
                  <label><input type="radio" name="xrange">Fixed</label>: <input type="number" step="any">-<input type="number" step="any">
              </td></tr>
              <tr><td></td><td><label><input type="checkbox">log</label></td></tr>

              <tr><th>Y Axis</th><td></td></tr>
              <tr><td>Title</td><td><input placeholder="empty"></td></tr>
              <tr><td>Range</td><td>
                  <label><input type="radio" name="yrange">Auto</label>
                  <label><input type="radio" name="yrange">Fixed</label>: <input type="number" step="any">-<input type="number" step="any">
              </td></tr>
              <tr><td></td><td><label><input type="checkbox">log</label></td></tr>

              <tr><th>Z Axis</th><td></td></tr>
              <tr><td>Color Coding</td><td><select>
                  <option value="">(None)</option>
                  <hr/>
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
              <tr><td>Title</td><td><input placeholder="empty"></td></tr>
              <tr><td>Range</td><td><label>
                  <label><input type="radio" name="zrange">Auto</label>
                  <input type="radio" name="zrange">Fixed</label>: <input type="number" step="any">-<input type="number" step="any">
              </td></tr>
              <tr><td></td><td><label><input type="checkbox">log</label></td></tr>
            </table>
        `);

        let axes = this.config.axes;
        let [xmin, xmax] = [axes.xmin ?? '', axes.xmax ?? ''];
        let [ymin, ymax] = [axes.ymin ?? '', axes.ymax ?? ''];
        let [zmin, zmax] = [axes.zmin ?? '', axes.zmax ?? ''];
        if ((xmin === '') || (xmax === '')) {
            let currentRange = this.axes.getRange();
            [ xmin, xmax ] = this.trimRange(currentRange.xmin, currentRange.xmax, axes.xlog);
        }
        if ((ymin === '') || (ymax === '')) {
            let currentRange = this.axes.getRange();
            [ ymin, ymax ] = this.trimRange(currentRange.ymin, currentRange.ymax, axes.ylog);
        }
        if ((zmin === '') || (zmax === '')) {
            let currentRange = this.axes.getRange();
            [ zmin, zmax ] = this.trimRange(currentRange.zmin, currentRange.zmax, axes.zlog);
        }
        axes.xmin = xmin; axes.xmax = xmax;
        axes.ymin = ymin; axes.ymax = ymax;
        axes.zmin = zmin; axes.zmax = zmax;

        let legend = this.config.legend;
        
        let k = 0;
        bindInput(axes, 'title', inputsDiv.find('input').at(k++).css('width', '20em'));
        bindInput(axes, 'xtitle', inputsDiv.find('input').at(k++).css('width', '20em'));
        bindInput(axes, 'xfixed', inputsDiv.find('input').at(k++), false);
        bindInput(axes, 'xfixed', inputsDiv.find('input').at(k++), true);
        bindInput(axes, 'xmin', inputsDiv.find('input').at(k++).css('width', '5em'));
        bindInput(axes, 'xmax', inputsDiv.find('input').at(k++).css('width', '5em'));
        bindInput(axes, 'xlog', inputsDiv.find('input').at(k++), true);
        bindInput(axes, 'ytitle', inputsDiv.find('input').at(k++).css('width', '20em'));
        bindInput(axes, 'yfixed', inputsDiv.find('input').at(k++), false);
        bindInput(axes, 'yfixed', inputsDiv.find('input').at(k++), true);
        bindInput(axes, 'ymin', inputsDiv.find('input').at(k++).css('width', '5em'));
        bindInput(axes, 'ymax', inputsDiv.find('input').at(k++).css('width', '5em'));
        bindInput(axes, 'ylog', inputsDiv.find('input').at(k++), true);
        bindInput(axes, 'ztitle', inputsDiv.find('input').at(k++).css('width', '20em'));
        bindInput(axes, 'zfixed', inputsDiv.find('input').at(k++), false);
        bindInput(axes, 'zfixed', inputsDiv.find('input').at(k++), true);
        bindInput(axes, 'zmin', inputsDiv.find('input').at(k++).css('width', '5em'));
        bindInput(axes, 'zmax', inputsDiv.find('input').at(k++).css('width', '5em'));
        bindInput(axes, 'zlog', inputsDiv.find('input').at(k++), true);
        bindInput(legend, 'style', inputsDiv.find('select').at(0));
        bindInput(axes, 'colorscale', inputsDiv.find('select').at(1));

        let drawingsDiv = $('<div>').appendTo(div).css(boxStyle);
        drawingsDiv.html(`
            <span style="font-size:130%;font-weight:bold">Drawing Elements</span>
            <hr style="margin-bottom:2ex">
        `);
        let tabsDiv = $('<div>').appendTo(drawingsDiv);
        for (let plot of this.plots) {
            let label = plot.getLabel();
            let pageDiv = $('<div>').addClass('jaga-tabPage').attr('label', label).appendTo(tabsDiv);
            plot.openSettings(pageDiv);
        }
        let tabs = new JGTabWidget(tabsDiv);
        tabs.openPage(-1);

        let addDiv = $('<div>').appendTo(div).css(boxStyle);
        addDiv.html(`
            <span style="font-size:130%;font-weight:bold">Add New</span>
            <hr style="margin-bottom:2ex">
            <table style="margin-top:1em">
              <tr><td>Type</td><td>Histograms and Graphs</td></tr>
            </table>
        `);
        PlotPanel.buildConstructRows(addDiv.find('table'), config=>{
            this.config.plots.push(config.plots[0]);
            this.configure(this.config, this.callbacks);
            this.openSettings(div.empty());
        });
    }


    fillInputChannels(inputChannels) {
        for (const p of this.plots) {
            p.fillInputChannels(inputChannels);
        }
    }
    
    
    drawRange(dataPacket, displayTimeRange) {
        if (dataPacket?.range) {
            this.currentDataTimeRange = { from: dataPacket.range.from, to: dataPacket.range.to };
        }
        for (const p of this.plots) {
            p.draw(dataPacket);
        }
        const [xmin, xmax] = this.adjustXRange(false);
        const [ymin, ymax] = this.adjustYRange(false);
        const [zmin, zmax] = this.adjustZRange(false);
        this.axes.setRange(xmin, xmax, ymin, ymax, zmin, zmax);
    }

    
    download() {
        let channels = [];
        this.fillInputChannels(channels);
        let opts = [
            'channels=' + channels.join(','),
            'length=' + (this.currentDataTimeRange.to - this.currentDataTimeRange.from),
            'to=' + (this.currentDataTimeRange.to),
        ];
        window.open('./slowdown.html?' + opts.join('&'));
    }

    
    capture(withLegend=true) {
        let download = (href, name) => {
            let link = document.createElement('a');
            link.download = name;
            link.style.opacity = 0;
            this.div.append(link);
            link.href = href;
            link.click();
            link.remove();
        }
        
        let svg = this.axes.svg.get().outerHTML;
        const svgWidth = this.axes.svg.attr('width');
        const svgHeight = this.axes.svg.attr('height');
        const name = 'SlowDash-' + (new JGDateTime()).asString('%y%m%d-%H%M%S');
        
        let svgBlob = new Blob([svg], {type:'image/svg+xml;charset=utf-8'});
        let svgUrl = URL.createObjectURL(svgBlob);
        //download(svgUrl, name + '.svg');
        
        let canvas = document.createElement('canvas');
        canvas.width = this.div.boundingClientWidth();
        canvas.height = this.div.boundingClientHeight();
        let ctx = canvas.getContext('2d');
        ctx.fillStyle = 'white';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        const legend = (new XMLSerializer()).serializeToString(this.legendDiv.get());
        const legendSvg = (`
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0,0,${canvas.width},${canvas.height}" width="${canvas.width}" height="${canvas.height}">
            <foreignObject width="${canvas.width}" height="${canvas.height}">
              ${legend}
            </foreignObject>
          </svg>
        `);
        /* Blob of SVG that contains a foregin object is marked as "tainted" by Chrome etc. */
        //let legendSvgBlob = new Blob([legendSvg], {type:'image/svg+xml;charset=utf-8'});
        //let legendSvgUrl = URL.createObjectURL(legendSvgBlob);
        /* Data URL seems to be accepted at least by Chrome */
        let legendSvgUrl = 'data:image/svg+xml; charset=utf-8, ' + encodeURIComponent(legendSvg);
        
        let img = new Image();
        img.onload = ()=>{
            ctx.drawImage(img, 0, 0, svgWidth, svgHeight);
            let legendImg = new Image();
            legendImg.onload = ()=>{
                if (withLegend) {
                    ctx.drawImage(legendImg, 0, 0, canvas.width, canvas.height);
                }

                try {
                    canvas.toBlob(pngBlob => {
                        //navigator.clipboard.write([new ClipboardItem({'image/png':pngBlob})]);
                    
                        let pngUrl = URL.createObjectURL(pngBlob);
                        download(pngUrl, name + '.png');
                        
                        URL.revokeObjectURL(svgUrl);
                        URL.revokeObjectURL(legendSvgUrl);
                        URL.revokeObjectURL(pngUrl);
                    }, 'image/png', 1.0);
                }
                catch(e) {
                    // Some browsers (e.g., Chrome) mark SVG "tainted" if it includes a ForeginObject
                    if (withLegend) {
                        this.capture(false);
                    }
                }
            };
            legendImg.onerror = e=> console.log(e);
            legendImg.src = legendSvgUrl;
        }
        img.onerror = e=> console.log(e);
        img.src = svgUrl;
    }

    
    adjustXRange(updateAxes=true) {
        if (this.config.axes.xfixed) {
            if (this.config.axes.xmin < this.config.axes.xmax) {
                this.axes.setRange(this.config.axes.xmin, this.config.axes.xmax);
                return [ this.config.axes.xmin, this.config.axes.xmax ];
            }
        }
        
        let min = null, max = null;
        for (const p of this.plots) {
            const range = p.getXRange();
            min = Math.min(min??range[0], range[0]);
            max = Math.max(max??range[0], range[1]);
        }
        if ((min === null) || (max === null)) {
            return [ null, null ];
        }
        [min, max] = JGPlotAxisScale.findRangeFromValues(min, max, {
            upperMargin: (this.isQuadMeshPlot??false) ? 0 : 0.05,
            lowerMargin: (this.isQuadMeshPlot??false) ? 0 : 0.05,
            isLog: this.config.axes.xlog,
            stickyZero: false,
        });
        
        if (this.config.axes.xfixed) {
            this.config.axes.xmin = min;
            this.config.axes.xmax = max;
        }
        if (updateAxes) {
            this.axes.setRange(min, max);
        }

        return [min, max];
    }
    
    adjustYRange(updateAxes=true) {
        if (this.config.axes.yfixed) {
            if (this.config.axes.ymin < this.config.axes.ymax) {
                this.axes.setRange(null, null, this.config.axes.ymin, this.config.axes.ymax);
                return [ this.config.axes.ymin, this.config.axes.ymax ];
            }
        }
        
        let min = null, max = null;
        for (const p of this.plots) {
            const range = p.getYRange();
            min = Math.min(min??range[0], range[0]);
            max = Math.max(max??range[1], range[1]);
        }
        if ((min === null) || (max === null)) {
            return [ null, null ];
        }        
        [min, max] = JGPlotAxisScale.findRangeFromValues(min, max, {
            upperMargin: (this.isQuadMeshPlot??false) ? 0 : 0.1,
            lowerMargin: (this.isQuadMeshPlot??false) ? 0 : 0.1,
            isLog: this.config.axes.ylog,
            stickyZero: true,
        });

        if (this.config.axes.yfixed) {
            this.config.axes.ymin = min;
            this.config.axes.ymax = max;
        }
        if (updateAxes) {
            this.axes.setRange(null, null, min, max);
        }

        return [min, max];
    }

    adjustZRange(updateAxes=true) {
        if (this.config.axes.zfixed) {
            if (this.config.axes.zmin < this.config.axes.zmax) {
                this.axes.setRange(null, null, null, null, this.config.axes.zmin, this.config.axes.zmax);
                return [ this.config.axes.zmin, this.config.axes.zmax ];
            }
        }
        
        let min = null, max = null;
        for (const p of this.plots) {
            const range = p.getZRange();
            min = Math.min(min??range[0], range[0]);
            max = Math.max(max??range[1], range[1]);
        }
        if ((min === null) || (max === null)) {
            return [ null, null ];
        }        
        [min, max] = JGPlotAxisScale.findRangeFromValues(
            min, max,
            { upperMargin: 0, lowerMargin: 0, isLog: this.config.axes.zlog }
        );
        
        if (this.config.axes.zfixed) {
            this.config.axes.zmin = min;
            this.config.axes.zmax = max;
        }
        if (updateAxes) {
            this.axes.setRange(null, null, null, null, min, max);
        }

        return [min, max];
    }

    trimRange(min, max, isLog=false) {
        if (isLog && (max > 100*min)) {
            min = 10**Math.floor(Math.log10(min));
            max = 10**Math.ceil(Math.log10(max));
            return [min, max];
        }
        
        function trim(x, numberOfDigits, roundingFunc) {
            if ((x === undefined) || (x === null) || (x === 0)) return x;
            let order = Math.floor(Math.log10(Math.abs(x)));
            let orderShift = Math.pow(10, numberOfDigits-1);
            let base = Math.pow(10, order);
            x = roundingFunc((orderShift*x)/base)/orderShift * base;
            let precision = numberOfDigits;
            if ((order+1 > numberOfDigits) && (order+1 < 8)) {
                precision = order+1;
            }
            return parseFloat(x.toPrecision(precision));
        }

        for (let numberOfDigits = 1; numberOfDigits < 10; numberOfDigits++) {
            let tmin = trim(min, numberOfDigits, Math.floor);
            let tmax = trim(max, numberOfDigits, Math.floor);
            if (tmax > tmin) {
                min = trim(min, numberOfDigits, Math.floor);
                max = trim(max, numberOfDigits, Math.ceil);
                break;
            }
        }

        return [min, max];
    }
    
    resetRange() {
        const [xmin, xmax] = this.adjustXRange(false);
        const [ymin, ymax] = this.adjustYRange(false);
        const [zmin, zmax] = this.adjustZRange(false);
        this.axes.setRange(xmin, xmax, ymin, ymax, zmin, zmax);
        this.callbacks.suspendUpdate(0);
    }
    
    rangeSelect(x0, x1, y0, y1) {
        this.axes.setRange(x0, x1, y0, y1, {xlog: this.config.axes.xlog, ylog: this.config.axes.ylog});
        this.callbacks.suspendUpdate();
    }
};



class TimeAxisPlotPanel extends PlotPanel {
    static describe() {
        return { type: 'timeaxis', label: 'Time-Axis Plot (Time-Series)' };
    }
    
    static buildConstructRows(table, on_done=config=>{}) {
        let tr1 = $('<tr>').html(`
            <td>Channel</td><td><input list="sd-numeric-datalist"></td>
       `).appendTo(table);
        let tr2 = $('<tr>').html(`
            <td style="padding-top:1em"><button hidden style="font-size:130%">Create</button></td><td></td>
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
                type: 'timeseries',
                plots: [{ type: 'timeseries', channel: table.find('input').val() }]
            };
            on_done(config);
        });
    }

    
    constructor(div, style) {
        super(div, style);
    }

    
    configure(config, callbacks={}) {
        super.configure(config, callbacks);
        this.currentDataTimeRange = null;
        this.currentDisplayTimeRange = null;
    }

    
    openSettings(div) {
        div.css('display', 'flex');
        const boxStyle = {
            'border': 'thin solid',
            'border-radius': '5px',
            'margin': '5px',
            'padding': '5px',
        };
        
        let inputsDiv = $('<div>').appendTo(div).css(boxStyle);
        inputsDiv.html(`
            <span style="font-size:130%;font-weight:bold">Axes</span>
            <hr style="margin-bottom:2ex">
            <table style="margin-top:1em">
              <tr><th>Title</th><td><input placeholder="auto"></td></tr>
              <tr><th>Y Axis</th><td></td></tr>
              <tr><td>Title</td><td><input placeholder="empty"></td></tr>
              <tr><td>Range</td><td><label><input type="radio" name="yrange">Fixed</label>: <input type="number" step="any">-<input type="number" step="any"></td></tr>
              <tr><td></td><td><label><input type="radio" name="yrange">Auto</label></td></tr>
              <tr><td></td><td><label><input type="checkbox">log</label></td></tr>
              <tr><th>Legend</th><td></td></tr>
              <tr><td>Style</td><td><select>
                <option value="side">Side Panel</option>
                <option value="box">Corner Box</option>
                <option value="transparent">Transparent Corner Box</option>
                <option value="hidden">Hidden Corner Box</option>
                <option value="none">None</option>
              </select></td></tr>
            </table>
        `);

        let axes = this.config.axes;
        let [ymin, ymax] = [axes.ymin ?? '', axes.ymax ?? ''];
        if ((ymin === '') || (ymax === '')) {
            let currentRange = this.axes.getRange();
            [ ymin, ymax ] = this.trimRange(currentRange.ymin, currentRange.ymax, axes.ylog);
        }
        axes.ymin = ymin; axes.ymax = ymax;
        
        let legend = this.config.legend;
        
        let k = 0;
        bindInput(axes, 'title', inputsDiv.find('input').at(k++).css('width', '20em'));
        bindInput(axes, 'ytitle', inputsDiv.find('input').at(k++).css('width', '20em'));
        bindInput(axes, 'yfixed', inputsDiv.find('input').at(k++), true);
        bindInput(axes, 'ymin', inputsDiv.find('input').at(k++).css('width', '5em'));
        bindInput(axes, 'ymax', inputsDiv.find('input').at(k++).css('width', '5em'));
        bindInput(axes, 'yfixed', inputsDiv.find('input').at(k++), false);
        bindInput(axes, 'ylog', inputsDiv.find('input').at(k++), true);
        bindInput(legend, 'style', inputsDiv.find('select').at(0));

        let drawingsDiv = $('<div>').appendTo(div).css(boxStyle);
        drawingsDiv.html(`
            <span style="font-size:130%;font-weight:bold">Drawing Elements</span>
            <hr style="margin-bottom:2ex">
        `);
        let tabsDiv = $('<div>').appendTo(drawingsDiv);
        for (let plot of this.plots) {
            let label = plot.getLabel();
            let pageDiv = $('<div>').addClass('jaga-tabPage').attr('label', label).appendTo(tabsDiv);
            plot.openSettings(pageDiv);
        }
        let tabs = new JGTabWidget(tabsDiv);
        tabs.openPage(-1);

        let addDiv = $('<div>').appendTo(div).css(boxStyle);
        addDiv.html(`
            <span style="font-size:130%;font-weight:bold">Add New</span>
            <hr style="margin-bottom:2ex">
            <table style="margin-top:1em">
              <tr><td>Type</td><td>Time-Axes Plot</td></tr>
            </table>
        `);
        TimeAxisPlotPanel.buildConstructRows(addDiv.find('table'), config=>{
            this.config.plots.push(config.plots[0]);
            this.configure(this.config, this.callbacks);
            this.openSettings(div.empty());
        });
    }

    
    drawRange(dataPacket, displayTimeRange) {
        if (dataPacket?.range) {
            this.currentDataTimeRange = { from: dataPacket.range.from, to: dataPacket.range.to };
        }
        this.currentDisplayTimeRange = displayTimeRange ?? this.currentDataTimeRange ?? null;
        if (this.currentDisplayTimeRange === null) {
            let currentAxesRange = this.axes.getRange();
            this.currentDisplayTimeRange = { from:currentAxesRange.xmin, to:currentAxesRange.xmax };
        }
        this.adjustXRange();
        
        for (const p of this.plots) {
            p.draw(dataPacket);
        }
        this.adjustYRange();
    }

    adjustXRange(updateAxes=true) {
        let range = this.currentDisplayTimeRange;
        if (! range) {
            return;
        }
            
        const length = (range.to - range.from);
        const margin = 0.03*length;
        if (updateAxes) {
            this.axes.setRange(range.from-margin, range.to+margin);
        }
        
        let tickFormat, labelFormat=null;
        if (length < 300) {
            tickFormat = '%H:%M:%S';            
            labelFormat = '%a, %b %d %Y %Z';
        }
        else if (length <= 86400) {
            tickFormat = '%H:%M';
            labelFormat = '%a, %b %d %Y %Z';
        }
        else if (length < 5*86400) {
            tickFormat = '%a, %H:%M';
            labelFormat = '%a, %b %d %Y %Z';
        }
        else if (length < 180*86400) {
            tickFormat = '%b %d';
            labelFormat = '%Y UTC%:z';
        }
        else if (length < 3*366*86400) {
            tickFormat = '%b %Y';
            labelFormat = 'UTC%:z';
        }
        else {
            tickFormat = '%Y';
        }
        this.axes.setXDateFormat(tickFormat);
        if (labelFormat) {
            this.axes.setXTitle((new JGDateTime(range.to)).asString(labelFormat));
        }
        else {
            this.axes.setXTitle('');
        }

        return [range.from-margin, range.to+margin];
    }
    
    resetRange() {
        this.currentDisplayTimeRange = this.currentDataTimeRange;
        const [xmin, xmax] = this.adjustXRange(false);
        const [ymin, ymax] = this.adjustYRange(false);
        this.axes.setRange(xmin, xmax, ymin, ymax);
        this.callbacks.changeDisplayTimeRange(null);
        this.callbacks.suspendUpdate(0);
    }
    
    rangeSelect(x0, x1, y0, y1) {
        const from = Math.min(x0, x1);
        const to = Math.max(x0, x1);
        this.callbacks.changeDisplayTimeRange({from:from, to:to});
        this.callbacks.suspendUpdate();
        
        // The call-back above will call this.axes.setRange() which then calls this.adjustYRange().
        // Here we set the selected Y range.
        // For the X range, the call-back will call this.adjustXRange() with some margins.
        // We keep the margins so that the X range becomes aligned with other time-series plots.
        this.axes.setRange(NaN, NaN, y0, y1, {ylog: this.config.axes.ylog});
    }
    
};
