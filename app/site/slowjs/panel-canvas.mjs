// panel-canvas.mjs //
// Author: Sanshiro Enomoto <sanshiro@uw.edu> //
// Created on 29 July 2021 //


import { JG as $, JGDateTime } from './jagaimo/jagaimo.mjs';
import { JGPopupWidget, JGDraggable, JGIndicatorWidget } from './jagaimo/jagawidgets.mjs';
import { JGPlotWidget, JGPlot, JGPlotAxisScale } from './jagaimo/jagaplot.mjs';
import { Panel, bindInput } from './panel.mjs';


const defaultStyle = {
    fontFamily: "sans-serif",
    fontWeight: "normal",
    fontSize: "11pt",
    dataFontFamily: "sans-serif",
    dataFontWeight: "normal",
    dataFontSize: "11pt",
    labelFontFamily: "sans-serif",
    labelFontWeight: "normal",
    labelFontSize: "12pt",
    dataColor: '#009090', // teal (008080)
    "color-active": "orange",
    "color-inactive": "skyblue",
    "color-dead": "lightgray",
    "color-none": "none",
};



class CanvasItem {
    static defaults = {
        'tolerable-gap': 60,
    };
    
    constructor(svgParent, style) {
        this.parent = svgParent;
        this.style = $.extend({}, defaultStyle, style);
        
        this.elem = null;
        this.last_tx = [null, null];
        this.alarmLevels = [];
    }
        
    configure(config, click_handler) {
        if (! this.configure_this) {
            return;
        }
        this.attr = $.extend({}, this.get_defaults(), config.attr);
        this.metric = config.metric;
        this.action = config.action;
        if (this.metric && (this.metric.alarmLevels === undefined)) {
            this.metric.alarmLevels = [];
        }
        
        if (this.attr.x === null) this.attr.x = this.attr.y ?? 100;
        if (this.attr.y === null) this.attr.y = this.attr.x;
        if (! this.attr.width) this.attr.width = this.attr.height || 100;
        if (! this.attr.height) this.attr.height = this.attr.width;
            
        this.elem = this.configure_this().appendTo(this.parent);
        if (! this.elem) {
            return;
        }
        
        if (this.attr.help) {
            this.elem.append($('<title>', 'svg').text(this.attr.help));
        }
        else if (this.metric?.channel) {
            this.elem.append($('<title>', 'svg').text(this.metric.channel));
        }
        else if (this.action?.open) {
            this.elem.append($('<title>', 'svg').text(this.action.open));
        }
        
        if ((this.update_this !== undefined) && (this.metric !== undefined)) {
            this.update_this(null, 'dead', 'good');
        }

        if ((this.metric || this.action) && click_handler) {
            this.elem.css({'cursor': 'pointer'});
            this.elem.click(event => {
                click_handler(event, config);
            });
        }
    }
    
    update(dataPacket) {        
        if ((this.update_this == null) || (this.metric?.channel == null)) {
            return;
        }

        const ts = dataPacket[this.metric.channel];
        const isPartial = (dataPacket?.meta?.isPartial ?? false) || (dataPacket?.meta?.isCurrent ?? false);
        if (! ts && isPartial) {
            return;
        }
        
        let [time, value] = Panel._getLastTX(ts);
        if (time == null) {
            [time, value] = this.last_tx;
        }
        else {
            this.last_tx = [time, value];
        }
        
        const tolerable_gap = this.metric['tolerable-gap'] ?? CanvasItem.defaults['tolerable-gap'];
        let to = dataPacket?.__meta?.range?.to;
        if (to <= 0) {
            to += $.time();
        }
        if ((time == null) || (to == null) || (time + tolerable_gap < to)) {
            if (isPartial) {
                return;  // no gap check for partial or current packets
            }
            [time, value] = [null, null];
        }

        let status = 'none';
        if (value === null) {
            status = 'dead';
        }
        else if (this.metric['active-above'] !== undefined) {
            status = (value >= this.metric['active-above']) ? 'active' : 'inactive';
        }
        else if (this.metric['active-below'] !== undefined) {
            status = (value < this.metric['active-below']) ? 'active' : 'inactive';
        }
        
        let alarm = 0;
        if (value === null) {
            alarm = 1;
        }
        else {
            for (let entry of this.metric.alarmLevels) {
                if ((value < entry.low) || (value >= entry.high)) {
                    alarm = 1;
                }
            }
        }
        
        if ((this.metric.format !== undefined) && (value !== null)) {
            value = $.sprintf(this.metric.format, value);
        }
        
        this.update_this(value, status, alarm);
    }
};


class ImageItem extends CanvasItem {
    constructor(svgParent, style) {
        super(svgParent, style);
    }
    
    get_defaults() {
        return {
            "x": null, "y": null, "height": null, "width": null,
            "href": null
        };
    }

    configure_this() {
        let attr = $.extend({}, this.attr);
        let filename = attr.href;
        if (filename) {
            attr["href"] = "./api/config/file/" + filename;
            if (
                (filename === this.style.negatingImages) ||
                (Array.isArray(this.style.negatingImages) && this.style.negatingImages.includes(filename))
            ){
                attr["filter"] = 'url(#sd-NegatingFilter)';
            }
        }
        return $('<image>', 'svg').attr(attr);
    }
};


class TextItem extends CanvasItem {
    constructor(svgParent, style) {
        super(svgParent, style);
    }
    
    get_defaults() {
        return {
            "x": null, "y": null, "text": "",
            "font-family": this.style.fontFamily,
            "font-weight": this.style.fontWeight,
            "font-size": this.style.fontSize,
            "fill": this.style.strokeColor,
            "data-color": this.style.dataColor
        };
    }
    
    configure_this() {
        let elem = $('<text>', 'svg').attr(this.attr).text(this.attr.text);
        if ((this.action?.open !== undefined) || (this.action?.form !== undefined)) {
            elem.addClass('clickable');
        }
        return elem;
    }

    update_this(value, status, alarm) {
        this.elem.attr({'fill': this.attr['data-color']}).text(value ?? '---');
    }
};


class ShapeItem extends CanvasItem {
    constructor(svgParent, style) {
        super(svgParent, style);
    }
    
    get_defaults() {
        return {
            "x": null, "y": null, "height": null, "width": null,
            "label": null,
            "stroke": this.style.strokeColor,
            "fill": "none",
            'data-dx': null, 'data-dy': null,
            'label-dx': null, 'label-dy': null,
            'data-color': this.style.dataColor,
            'data-font-family': this.style.dataFontFamily,
            'data-font-weight': this.style.dataFontWeight,
            'data-font-size': this.style.dataFontSize,
            'data-dominant-baseline': undefined,
            'data-text-anchor': undefined,
            'label-color': this.style.strokeColor,
            'label-font-family': this.style.labelFontFamily,
            'label-font-weight': this.style.labelFontWeight,
            'label-font-size': this.style.labelFontSize,
            'label-dominant-baseline': 'central',
            'label-text-anchor': 'middle',
        };
    }
    
    configure_this() {
        let elem = $('<g>', 'svg');
        if (true) {
            // invisible box to respond to clicks
            elem.append($('<rect>', 'svg').attr({
                x: this.attr.x,
                y: this.attr.y,
                width: this.attr.width,
                height: this.attr.height,
                fill: 'black',
                'fill-opacity': 0
            }));
        }
        this.path = this.create_path().appendTo(elem);
        this.label = null;
        this.text = null;
        this.alarm = null;
        if (this.attr.label) {
            let [dx, dy] = [this.attr['label-dx'], this.attr['label-dy']];
            let labelAttr = $.extend({}, this.attr, {
                stroke: 'null',
                fill: this.attr['label-color'],
                x: this.attr.x + (dx ?? this.attr.width/2),
                y: this.attr.y + (dy ?? this.attr.height/2),
                'font-family': this.attr['label-font-family'],
                'font-weight': this.attr['label-font-weight'],
                'font-size': this.attr['label-font-size'],
                'dominant-baseline': this.attr['label-dominant-baseline'],
                'text-anchor': this.attr['label-text-anchor']
            });
            this.label = $('<text>', 'svg').attr(labelAttr).text(this.attr.label);
            elem.append(this.label);
        }
        if (this.metric && this.metric.format) {
            let [dx, dy] = [this.attr['data-dx'], this.attr['data-dy']];
            let base = this.attr['data-dominant-baseline'];
            let anchor = this.attr['data-text-anchor'];
            if ((dx === null) && (dy === null) && (base === undefined)  && (anchor === undefined)) {
                dx = this.attr.width * 0.75;
                dy = this.attr.height;
                base = 'hanging';
                anchor = 'start';
            }
            let textAttr = $.extend({}, this.attr, {
                stroke: 'none',
                fill: this.attr['data-color'],
                x: this.attr.x + (dx ?? 0),
                y: this.attr.y + (dy ?? 0),
                'font-family': this.attr['data-font-family'],
                'font-weight': this.attr['data-font-weight'],
                'font-size': this.attr['data-font-size'],
                'dominant-baseline': base ?? 'auto',
                'text-anchor': anchor ?? 'start'
            });
            this.text = $('<text>', 'svg').attr(textAttr).text('---');
            elem.append(this.text);
        }
        if (this.metric && this.metric.alarmLevels) {
            let size = 30;
            this.alarm = $('<image>', 'svg').attr({
                x: this.attr.x - 0.75*size, y: this.attr.y - 0.75*size,
                href: "slowjs/Warning.png", height: size, width: size,
                visibility: 'visible',
            });
            elem.append(this.alarm);
        }
        return elem;
    }
    
    update_this(value, status, alarm) {
        if (this.path) {
            this.path.attr('fill', this.style['color-'+status]);
        }
        if (this.text) {
            this.text.text(value === null ? "---" : value);
        };
        if (this.alarm) {
            this.alarm.attr('visibility', (alarm > 0 ? 'visible' : 'hidden'));
        }
    }
};


class InvisibleItem extends ShapeItem {
    constructor(svgParent, style) {
        super(svgParent, style);
    }
    create_path() {
        return $('<g>', 'svg');
    }
};


class BoxItem extends ShapeItem {
    constructor(svgParent, style) {
        super(svgParent, style);
    }
    get_defaults() {
        return $.extend({}, super.get_defaults(), {
            width: 30, height: 30
        });
    }
    create_path() {
        return $('<rect>', 'svg').attr(this.attr);
    }
};


class CircleItem extends ShapeItem {
    constructor(svgParent, style) {
        super(svgParent, style);
    }
    get_defaults() {
        return $.extend({}, super.get_defaults(), {
            width: 30, height: 30
        });
    }
    create_path() {
        let circleAttr = $.extend({}, this.attr, {
            cx: this.attr.x + this.attr.width/2,
            cy: this.attr.y + this.attr.height/2,
            rx: this.attr.width/2,
            ry: this.attr.height/2
        });
        return $('<ellipse>', 'svg').attr(circleAttr);
    }
};


class ValveItem extends ShapeItem {
    constructor(svgParent, style) {
        super(svgParent, style);
    }
    get_defaults() {
        return $.extend({}, super.get_defaults(), {
            width: 30, height: 30, orientation: 'horizontal'
        });
    }
    create_path() {
        let [x0, y0] = [this.attr.x, this.attr.y];
        let [x1, y1] = [x0 + this.attr.width, y0 + this.attr.height];
        let points = (
            (this.attr.orientation[0] == 'v') ?
            `${x0},${y0} ${x1},${y0} ${x0},${y1} ${x1},${y1} ${x0},${y0}` :
            `${x0},${y0} ${x0},${y1} ${x1},${y0} ${x1},${y1} ${x0},${y0}`
        );
        return $('<polyline>', 'svg').attr(this.attr).attr({'points': points});
    }
};


class SolenoidItem extends ShapeItem {
    constructor(svgParent, style) {
        super(svgParent, style);
    }
    get_defaults() {
        return $.extend({}, super.get_defaults(), {
            width: 50, height: 30, fill: 'none', "stroke-width": 3, turns: 12
        });
    }
    create_path() {
        let d = '';
        let n = this.attr.turns;
        for (let i = 0; i < n; i++) {
            let [x0, y0] = [this.attr.x + i * this.attr.width / n, this.attr.y + this.attr.height];
            let [x1, y1] = [x0 + this.attr.width/n, y0 - this.attr.height];
            d += `M ${x0} ${y0} L ${x1} ${y1} `;
        }
        return $('<path>', 'svg').attr(this.attr).attr({'d': d});
    }
    update_this(value, status, alarm) {
        if (this.path) {
            this.path.attr('stroke', this.style['color-'+status]);
        }
        if (this.text) {
            this.text.text(value === null ? "---" : value);
        };
        if (this.alarm) {
            this.alarm.attr('visibility', (alarm > 0 ? 'visible' : 'hidden'));
        }
    }
};


class GridItem extends ShapeItem {
    constructor(svgParent, style) {
        super(svgParent, style);
    }
    get_defaults() {
        return $.extend({}, super.get_defaults(), {
            width: 10000, height: 10000, dx: 50, dy: 50,
            "stroke": "lightgray", "stroke-width": 1, fill: 'none'
        });
    }
    create_path() {
        const text_attr = {
            "font-family": "sans-serif",
            "font-weight": "normal",
            "font-size": "x-small",
            "color": "lightgray"
        };
        let elem = $('<g>', 'svg');
        let d = '';
        for (let x = this.attr.dx; x < this.attr.width; x += this.attr.dx) {
            d += `M ${x} 0 L ${x} ${this.attr.height} `;
            let label = $('<text>', 'svg').attr({"x":x,"y":10}).text(x);
            elem.append(label.attr(text_attr));
        }
        for (let y = this.attr.dy; y < this.attr.height; y += this.attr.dy) {
            d += `M 0 ${y} L ${this.attr.width} ${y}`;
            let label = $('<text>', 'svg').attr({"x":0,"y":y}).text(y);
            elem.append(label.attr(text_attr));
        }
        $('<path>', 'svg').attr(this.attr).attr({'d': d}).appendTo(elem);
        return elem;
    }
};


class ButtonItem extends CanvasItem {
    constructor(svgParent, style) {
        super(svgParent, style);
    }
    
    get_defaults() {
        return {
            "x": null, "y": null, 
            "width": 120, "height": 30,
            "rx": 5, "ry": 5,
            "label": "",
            "stroke": this.style.strokeColor,
            "font-family": this.style.fontFamily,
            "font-weight": this.style.fontWeight,
            "font-size": this.style.fontSize,
            'dominant-baseline': 'central',
            'text-anchor': 'middle',
        };
    }
    
    configure_this() {
        let elem = $('<g>', 'svg');
        elem.addClass('clickableShape');

        // invisible box to respond to clicks
        elem.append($('<rect>', 'svg').attr({
            x: this.attr.x,
            y: this.attr.y,
            width: this.attr.width,
            height: this.attr.height,
            fill: 'black',
            'fill-opacity': 0
        }));
        
        let boxAttr = $.extend({}, this.attr, {
            x: this.attr.x, y: this.attr.y,
            width: this.attr.width,
            height: this.attr.height,
            stroke: this.attr.stroke,
            fill: 'none',
        });
        this.box = $('<rect>', 'svg').attr(boxAttr);
        elem.append(this.box);
        
        let labelAttr = $.extend({}, this.attr, {
            stroke: 'none',
            fill: this.attr.stroke,
            x: this.attr.x + this.attr.width/2,
            y: this.attr.y + this.attr.height/2,
        });
        this.label = $('<text>', 'svg').attr(labelAttr).text(this.attr.label);
        elem.append(this.label);
        
        return elem;
    }

    update_this(value, status, alarm) {
    }
};


class PlotItem extends CanvasItem {
    constructor(svgParent, style) {
        super(svgParent, style);
        this.plot = undefined;
    }
    
    get_defaults() {
        return {
            "x": 0, "y": 0, "width": 100, "height": 100, "labelScaling": 0.8,
            "length": 3600, "dateFormat": null, "label": null,
            "ticksX": 5, "ticksY": 2, "grid": true,
            "min": null, "max": null, "logY": false,
            "marginTop": 0,
            "data-color": this.style.dataColor,
            "marker-type": "circle", "marker-size": 2,
            "line-width": 0.1,
            "fill-opacity": 0, "fill-baseline": 1e-100,
            "timerange-margin-percent": 3,
            "frame-thickness": 1,
        };
    }
    
    configure_this() {
        let g = $('<g>', 'svg');
        let attr = $.extend({}, this.attr, {
            "x0": $.time() - this.attr.length,
            "x1": $.time(),
            "y0": this.attr.min ?? -10,
            "y1": this.attr.max ?? +10,
            plotAreaColor: this.style.plotBackgroundColor,
            plotMarginColor: this.style.plotMarginColor,
            frameColor: this.style.plotFrameColor,
            gridColor: this.style.plotGridColor,
            labelColor: this.style.plotLabelColor,
            ticksOutwards: false,
            frameThickness: this.attr["frame-thickness"],
        });
        if (attr.dateFormat === null) {
            if (attr.length < 300) {
                attr.dateFormat = "%H:%M:%S";
            }
            else if (attr.length < 86400) {
                attr.dateFormat = "%H:%M";
            }
            else {
                attr.dateFormat = "%d,%H:%M";
            }
        }
        this.plot = new JGPlot(g, attr);
        this.graph = {
            x: [],
            y: [],
            style: { 
                lineWidth: this.attr["line-width"],
                lineColor: this.attr["data-color"],
                markerType: this.attr["marker-type"],
                markerSize: this.attr["marker-size"],
                markerColor: this.attr["data-color"],
                fillColor: this.attr["data-color"],
                fillOpacity: this.attr["fill-opacity"],
                fillBaseline: this.attr["fill-baseline"],
            }
        };
        return g;
    }

    update(dataPacket) {
        if (this.metric?.channel === undefined) {
            return;
        }
        let ts = dataPacket[this.metric.channel];

        if (! ts?.t || ! (ts.t.length > 0)) {
            if (dataPacket?.__meta?.isCurrent ?? false) {
                return;
            }
            else {
                ts = { t: [], x: [] };
            }
            //TODO: also check the case that the last "current" value is still valid
        }

        let to = dataPacket?.__meta?.range?.to ?? $.time();
        let from = dataPacket?.__meta?.range?.from ?? -3600;
        if (to <= 0) {
            to = $.time() + to;
        }
        if (from <= 0) {
            from = to + from;
        }
        
        let xmax = to;
        let xmin = (this.attr.length > 0) ? (xmax - this.attr.length) : from;
        const marginFraction = parseFloat(this.attr['timerange-margin-percent'])*0.01;
        let xmargin = (marginFraction > 0 && marginFraction < 1) ? marginFraction*(xmax - xmin) : 0;
        this.plot.setRange(xmin-xmargin, xmax+xmargin);

        this.graph.x = [];
        this.graph.y = [];
        this.plot.clear();
            
        let [ ymin, ymax ] = [ null, null ];
        for (let k = 0; k < ts.x.length; k++) {
            if (ts.x[k] !== null && ! isNaN(ts.x[k])) {
                this.graph.x.push(ts.start + ts.t[k]);
                this.graph.y.push(ts.x[k]);
                ymin = Math.min((ymin ?? ts.x[k]), ts.x[k]);
                ymax = Math.max((ymax ?? ts.x[k]), ts.x[k]);
            }
        }
        [ymin, ymax] = JGPlotAxisScale.findRangeFromValues(ymin, ymax);
        this.plot.setRange(null, null, this.attr.min ?? ymin, this.attr.max ?? ymax);
        
        this.plot.drawGraph(this.graph);
        let geom = this.plot.geom;
        let x = (geom.xmin + 0.02*(geom.xmax-geom.xmin));
        let y = (geom.ymin + 0.95*(geom.ymax-geom.ymin));
        if (geom.ylog && (geom.ymin > 0) && (geom.ymax > geom.ymin)) {
            y = 10**(Math.log10(geom.ymin) + 0.95*(Math.log10(geom.ymax/geom.ymin)))
        }
        
        this.plot.drawText({
            x: x, y: y,
            text: this.attr.label ?? this.metric.channel,
            style: {
                "dominant-baseline": "hanging", "font-size": "small",
                "textColor": this.style.strokeColor
            }
        });
    }
};


class MicroPlotItem extends PlotItem {
    constructor(svgParent, style) {
        super(svgParent, style);
    }
    
    get_defaults() {
        return $.extend({}, super.get_defaults(), {
            "width": 50, "height": 30, "labelScaling": 0.2,
            "marker-size": 0, "line-width": 0, "fill-opacity": 0.3,
            "ticksX": 0, "ticksY": 0, "grid": false,
            "marginTop": 0, "marginBottom": 0, "marginLeft": 0, "marginRight": 0,
            "label": "", "frame-thickness": 0.5, "axis-thickness": null,
            "timerange-margin-percent": 0,
        });
    }
};




let CanvasItemClassCollection = {
    image: ImageItem,
    grid: GridItem,
    text: TextItem,
    invisible: InvisibleItem,
    box: BoxItem,
    circle: CircleItem,
    valve: ValveItem,
    solenoid: SolenoidItem,
    button:ButtonItem,
    plot: PlotItem,
    micro_plot: MicroPlotItem,
};



class Viewlet {
    constructor(div, options={}) {
        this.div = div.css({
            'margin': 0,
            'padding': '1em',
        });
        this.div.empty();
        this.style = $.extend({}, defaultStyle, options.style);

        this.plotDiv = $('<div>').css('margin-bottom', '2em').appendTo(this.div);
        this.plotDiv.html(`
          <div style="font-size:130%;font-weight:bold"></div>
          <div style="margin:2em;padding:0"></div>
          <ul class="clickables-ul" style="margin-left:2em">
            <a href="#" target="_blank" style="font-size:130%">&rarr; SlowPlot Interactive Display</a>
          </ul>
        `);
        
        this.formDiv = $('<div>').appendTo(this.div);
        this.formDiv.html(`
          <div style="font-size:130%;font-weight:bold"></div>
          <form></form>
        `);
        
        const contextColor = getComputedStyle(div.get()).color;
        const contextBackgroundColor = getComputedStyle(div.get()).backgroundColor;
        const plotZoom = window.innerWidth > 720 ? 1 : window.innerWidth / 800.0;
        this.miniplot = new JGPlotWidget(this.plotDiv.find('div').at(1), {
            width: 640*plotZoom, height: 240*plotZoom, labelScaling: plotZoom,
            marginLeft: 100,
            ticksX: 5, ticksY: 2,
            dateFormat: '%H:%M',
            grid: true, 
            cursorDigits: 0, rangeSelect: null,
            plotAreaColor: this.style?.plotBackgroundColor ?? contextBackgroundColor,
            plotMarginColor: this.style?.plotMarginColor ?? contextBackgroundColor,
            frameColor: this.style?.plotFrameColor ?? contextColor,
            labelColor: this.style?.plotLabelColor ?? contextColor,
        });
        this.graph = {
            x: [],
            y: [],
            style: { 
                lineWidth: 1, markerSize: 2, markerType: 'circle',
                lineColor: this.style?.dataColor ??  contextColor,
                markerColor: this.style?.dataColor ?? contextColor,
            }
        };
        this.miniplot.addGraph(this.graph);
        
        this.popup = new JGPopupWidget(this.div, {
            closeOnGlobalClick: true
        });
        new JGDraggable(this.div, {
            handle: this.div,
            preventDefault: false,
            stopPropagation: false,
        });
    }
    
    fillData(channel, dataPacket) {
        if (! channel) {
            this.plotDiv.css('display', 'none');
            return;
        }
        
        this.plotDiv.css('display', 'block');
        this.plotDiv.find('div').at(0).text(channel);

        let to = dataPacket?.__meta?.range?.to ?? $.time();
        let from = dataPacket?.__meta?.range?.from ?? (to - 3600);
        if (to <= 0) {
            to = $.time() + to;
        }
        if (from <= 0) {
            from = to + from;
        }
        
        let slowplotUrl = './slowplot.html?';
        slowplotUrl += [
            'channel=' + channel,
            'length=' + (to - from),
            'to=' + (new JGDateTime(to)).asUTCString('%Y-%m-%dT%H:%M:%SZ'),
            'reload=0', 'grid=2x1'
        ].join('&');
        this.plotDiv.find('a').attr('href', slowplotUrl);
        
        let [ xmin, xmax ] = [ from, to ];
        const xmargin = 0.03*(xmax - xmin);
        this.miniplot.setRange(xmin-xmargin, xmax+xmargin);
        
        let ts = dataPacket ? dataPacket[channel] : null;
        if ((ts === undefined) || (ts === null) || (ts.t.length <= 0)) {
            this.miniplot.clear(false);
            return;
        }
        let [ ymin, ymax ] = [ null, null ];
        this.graph.x = [];
        this.graph.y = [];
        for (let k = 0; k < ts.x.length; k++) {
            if (ts.x[k] !== null && ! isNaN(ts.x[k])) {
                this.graph.x.push(ts.start + ts.t[k]);
                this.graph.y.push(ts.x[k]);
                ymin = Math.min((ymin ?? ts.x[k]), ts.x[k]);
                ymax = Math.max((ymax ?? ts.x[k]), ts.x[k]);
            }
        }
        [ymin, ymax] = JGPlotAxisScale.findRangeFromValues(ymin, ymax);
        this.miniplot.setRange(null, null, ymin, ymax);
    }
    
    buildForm(formName, config, submit_func) {
        if (! formName) {
            this.formDiv.css('display', 'none');
            return;
        }
        this.formDiv.css('display', 'block');
        let form = this.formDiv.find('form');
        form.html(`
            <table></table>
            <div class="jaga-dialog-button-pane" style="margin:5px"></div>
        `);

        if (! config.forms) {
            return;
        }
        const formConfig = config.forms[formName];
        if (! formConfig) {
            return;
        }
        this.formDiv.find('div').at(0).text(formConfig.title ?? formName);

        let table = form.find('table');
        for (let entry of formConfig.inputs ?? []) {
            if (! entry.name) {
                continue;
            }
            let tr = $('<tr>').appendTo(table);
            $('<td>').appendTo(tr).text(entry.label || entry.name);
            let input = $('<input>').appendTo($('<td>').appendTo(tr));
            input.attr({
                'name':  entry.name,
                'type': entry.type ?? 'number',
                'step': entry.step ?? 'any',
            });
            input.val(entry.initial ?? (formConfig.initial ? formConfig.initial[entry.name] : ''));
        }
        let buttonDiv = form.find('div');
        for (const btn of formConfig.buttons ?? [ {'name': 'apply', 'label': 'Apply'} ]) {
            if (! btn.name) {
                btn.name = 'apply';
            }
            $('<button>').appendTo(buttonDiv).text(btn.label || btn.name).data('name', btn.name).bind('click', e=>{
                e.preventDefault();
                let doc = {}
                let button = $(e.target).closest('button');
                doc[button.data('name')] = true;
                $.extend(doc, formConfig.initial ?? {});
                submit_func(doc, button.closest('form'), e);
            });
        }
        if (buttonDiv.find('button').size() < 4) {
            buttonDiv.find('button').css('flex-basis', '30%');
        }
    }
    
    openNear(x, y) {
        this.popup.openNear(x, y);
        let inputs = this.formDiv.find('input,select');
        if (inputs.size() > 0) {
            inputs.at(0).get().focus();
        }
    }
};



export class CanvasPanel extends Panel {
    static describe() {
        return { type: 'canvas', label: 'Dashboard Canvas' };
    }
    
    static buildConstructRows(table, on_done=config=>{}) {
        let tr1 = $('<tr>').html(`
            <td>Name</td><td><input list="sd-dashboard-datalist"></td>
       `).appendTo(table);
        let tr2 = $('<tr>').html(`
            <td style="padding-top:1em"><button hidden style="font-size:140%">Create</button></td><td></td>
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
                type: 'canvas',
                config_name: table.find('input').val(),
            };
            on_done(config);
        });
    }

    
    constructor(div, style={}) {
        super(div, style);

        this.svg = $('<svg>', 'svg').appendTo(div).attr({
            "xmlns": "http://www.w3.org/2000/svg",
            "xmlns:xlink": "http://www.w3.org/1999/xlink",
            "version": "1.1",
        });

        let viewletDiv = $('<div>').appendTo(div);
        this.viewlet = new Viewlet(viewletDiv, {
            style: this.style
        });
        this.click_handler = (event, itemConfig) => {
            if (itemConfig.action?.open) {
                window.open(itemConfig.action.open);
            }
            else if (itemConfig.action?.submit) {
                let doc = {};
                if (itemConfig.action.submit.name) {
                    doc[itemConfig.action.submit.name] = true;
                }
                this.submit(doc, null, event);
            }
            else {
                this.viewlet.fillData(itemConfig.metric?.channel, this.currentDataPacket);
                this.viewlet.buildForm(itemConfig.action?.form, this.canvasConfig, (d,f,e) => {this.submit(d,f,e)});
                this.viewlet.openNear(event.clientX+10, event.clientY+10);
            }
        };

        this.indicator = new JGIndicatorWidget($('<div>').appendTo(div));

        this.canvasConfig = {};
        this.items = [];
        this.inputChannels = [];
        this.currentDataPacket = null;
        
        this.loaded_config_name = null;
    }

    
    async configure(config, options={}, callbacks={}) {
        await super.configure(config, options, callbacks);

        // if canvas panel is loaded as a panel in a layout (SlowPlot)
        if (config.config_name) {
            if (config.config_name != this.loaded_config_name) {
                this.loaded_config_name = config.config_name;

                const url ='./api/config/content/slowdash-' + config.config_name + '.json';
                const response = await fetch(url);
                if (! response.ok) {
                    this.div.html(`
                        <h3>Configuration Loading Error</h3>
                        Name: ${config.config_name}<br>
                        <p>
                        URL: ${url}<br>
                        Error: ${response.status} ${response.statusText}
                    `);
                    return null;
                }
                this.canvasConfig = await response.json();
                console.log(url, "loaded");
            }
            else {
                //this.canvasConfig = this.canvasConfig;
            }
        }
        else {
            this.canvasConfig = config;
        }

        this._build();
    }

    
    _build() {
        this.svg.empty();
        this.svg.attr({
            'width': this.div.get().offsetWidth, 
            'height': this.div.get().offsetHeight,
            'preserveAspectRatio': 'xMinYMin meet',
        });
        
        this.svg.attr({"viewBox": this.canvasConfig.viewBox || this.canvasConfig.view_box || "0 0 1024 768"});
        this.svg.append(
            $('<filter>', 'svg').attr('id', 'sd-NegatingFilter').append(
                $('<feColorMatrix>', 'svg').attr({
                    'in': 'SourceGraphic',
                    'type': 'matrix',
                    'values': '-1 0 0 0 1   0 -1 0 0 1   0 0 -1 0 1   0 0 0 1 0'
                })
            )
        );

        // TODO: put default styles here
        CanvasItem.defaults['tolerable-gap'] = (this.canvasConfig.defaults??{})['tolerable-gap'] ?? 60;
        
        this.items = [];
        this.inputChannels = [];
        for (let itemConfig of this.canvasConfig.items ?? []) {
            if (! itemConfig.type) {
                continue;
            }
            let itemClass = CanvasItemClassCollection[itemConfig.type];
            if (itemClass) {
                let item = new itemClass(this.svg, this.style);
                this.items.push(item);
                if (itemConfig.metric?.channel) {
                    this.inputChannels.push(itemConfig.metric.channel);
                }
                item.configure(itemConfig, this.click_handler);
            }
            else {
                console.log('ERROR: unknown CanvasItem: ' + itemConfig.type);
                console.log(itemConfig);
            }
        }
    }

    
    addControlButtons(div) {
        super.addControlButtons(div);

        //let captureBtn = $('<button>').html('&#x1f4f8;').prependTo(div);
        //captureBtn.attr('title', 'Save Image');        
        //captureBtn.css('font-size', '1.5rem').bind('click', e=>{this.capture();});
    }

    
    openSettings(div) {
        let inputsDiv = $('<div>').appendTo(div);
        inputsDiv.html(`
            <table style="margin-top:1em">
              <tr><th>Name</th><td><input list="sd-dashboard-datalist"></td></tr>
            </table>
        `);

        let k = 0;
        bindInput(this.config, 'config_name', inputsDiv.find('input').at(k++).css('width', '20em'));
    }

    
    fillInputChannels(inputChannels) {
        for (let channel of this.inputChannels) {
            inputChannels.push(channel);
        }
    }

    
    draw(data, displayTimeRange=null) {
        this.currentDataPacket = data;
        for (let item of this.items) {
            item.update(data);
        }
    }

    
    //... BUG: this does not work (base image will not be included) //
    capture() {
        let download = (href, name) => {
            let link = document.createElement('a');
            link.download = name;
            link.style.opacity = 0;
            this.div.append(link);
            link.href = href;
            link.click();
            link.remove();
        }
        
        let svg = this.svg.get().outerHTML;
        const svgWidth = this.svg.attr('width');
        const svgHeight = this.svg.attr('height');
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

        let img = new Image();
        img.onload = ()=>{
            ctx.drawImage(img, 0, 0, svgWidth, svgHeight);
            canvas.toBlob(pngBlob => {
                let pngUrl = URL.createObjectURL(pngBlob);
                download(pngUrl, name + '.png');
                URL.revokeObjectURL(svgUrl);
                URL.revokeObjectURL(pngUrl);
            }, 'image/png', 1.0);
        };
        img.onerror = e=> console.log(e);
        img.src = svgUrl;
    }

    
    async submit(doc, form, event=null) {
        if (form) {
            for (let input of form.find('input,select').enumerate()) {
                if (input.attr('type') != 'submit') {
                    const name = input.attr('name');
                    if (name) {
                        doc[name] = input.val();
                    }
                }
            }
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
                throw new Error(`empty response: function might not exist`);
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
};
