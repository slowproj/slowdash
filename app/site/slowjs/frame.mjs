// frame.mjs //
// Author: Sanshiro Enomoto <sanshiro@uw.edu> //
// Created on 3 May 2022 //

import { JG as $, JGDateTime,  } from './jagaimo/jagaimo.mjs';
import { JGPullDownWidget, JGDialogWidget } from './jagaimo/jagawidgets.mjs';
import { lengthString } from './control.mjs';


export class Frame {
    constructor(obj, options={}) {
        const defaults = {
            title: "SlowDash",
            initialStatus: "loading...",
            initialBeat: "",
            initialReloadInterval: 60,
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
            reloadIntervalSelection: [ 0, -1, 2, 5, 10, 30, 60, 5*60, 15*60, 30*60, 60*60 ],
            reloadIntervalChange: (interval) => {},
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
        
        this.reloadInterval = this.options.initialReloadInterval;
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
                        // reload now, w/o changing the settings
                        setReloadLabel(this.reloadPulldown, this.reloadInterval);
                    }
                    else if (length < 0) {
                        // suspend auto reloading
                        this.reloadInterval = -1;
                        this.reloadPulldown.setLabel(heading + 'Auto Reload Off');
                    }
                    else {
                        // reload periodically
                        this.reloadInterval = length;
                    }
                    this.suspendUntil = 0;
                    this.options.reloadIntervalChange(length);
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

    
    setStatus(html) {
        this.statusSpan.html(html);
    }
    
    setBeatText(text) {
        this.beatSpan.text(text);
    }
    
    setBeatTime(time) {
        this.clockDiv.text((new JGDateTime(time)).asString('%a, %b %d %H:%M %Z'));
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
            items: [ '1x1', '1x2', '2x1', '2x2', '2x3', '3x1', '3x2', '3x3', '3x4', '4x1', '4x2', '4x3', '4x4', 'Other...' ],
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
