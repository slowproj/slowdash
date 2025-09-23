// panel.mjs //
// Author: Sanshiro Enomoto <sanshiro@uw.edu> //
// Created on 18 November 2021 //
// Refactored on 18 June 2022 //
// Refactored on 5 March 2025 //

 
import { JG as $, JGDateTime } from './jagaimo/jagaimo.mjs';
import { JGInvisibleWidget, JGDialogWidget } from './jagaimo/jagawidgets.mjs';


export function getPaletteColor(index) {
    const colorPalette = [
        '#009090', // teal (008080)
        '#dd8000', // orange (ff8c00)
        '#4169e1', // blue
        '#b030b0', // purple (a020a0)
        '#a06058', // brown (905a50)
        '#e074c0', // pink
        '#b5b620', // olive (bcbd22)
        '#56bf40', // green
    ];

    return colorPalette[index % colorPalette.length];
}



export function bindInput(object, member, element, isCheckInputNotNagated=true) {
    if (element.get().tagName == 'SELECT') {
        element.val(object[member] ?? element.find('option').val());
        element.bind('change', e=>{
            object[member] = element.val();
        });
    }
    else if ((element.attr('type') == 'checkbox') || (element.attr('type') == 'radio')) {
        if (isCheckInputNotNagated) {
            element.checked(object[member] ?? false);
            element.bind('change', e=>{
                object[member] = $(e.target).checked();
            });
        }
        else {
            element.checked(! (object[member] ?? false));
            element.bind('change', e=>{
                object[member] = ! $(e.target).checked();
            });
        }
    }
    else if ((element.attr('type') == 'datetime-local') && (typeof object[member] == 'number')) {
        element.val(new JGDateTime(object[member]).asString('%Y-%m-%dT%H:%M'));
        element.bind('change', e=>{
            object[member] = (new JGDateTime(new Date($(e.target).val()))).asInt();
        });
    }
    else {
        element.val(object[member] ?? '');
        element.bind('change', e=>{
            if ((typeof object[member] == 'number') || (element.attr('type') == 'number')) {
                const value = Number($(e.target).val());
                object[member] = (isNaN(value) ? null : value);
            }
            else {
                object[member] = $(e.target).val();
            }
        });
    }
}



export class Panel {
    static describe() { return { type: null, label: '' }; }
    static buildConstructRows(table, on_done=config=>{}) {}

    constructor(div, style={}) {
        this.div = $(div);
        this.style = style;
    }

        
    async configure(config, options={}, callbacks={}) {
        const default_options = {  // defaults when Panel is created directly (e.g., by user HTML)
            inactive: false,   // no control buttons at all
            immutable: true,   // no settings, no deleting
            standalone: true,  // no popout
        }
        const default_callbacks = {
            changeDisplayTimeRange: range => {},
            forceUpdate: () => {},
            suspendUpdate: (duration) => {},
            reconfigure: () => {},
            popout: (p) => {},
            publish: (topic, message) => {},
        };

        this.config = config;
        this.options = $.extend({}, default_options, options);
        this.callbacks = $.extend({}, default_callbacks, callbacks);

        this._setupSettingsDialog();
        if (! this.options.inactive) {
            this._setupControlButtons();
        }
    }

    
    addControlButtons(div) {
        if (! (this.options.standalone??false)) {
            let popoutBtn = $('<button>').html('&#x2197;').appendTo(div);
            popoutBtn.attr('title', 'Pop out').bind('click', e=>{
                this.callbacks.popout(this);
            });
        }

        if (! (this.options.immutable??false)) {
            let configBtn = $('<button>').html('&#x1f6e0;').appendTo(div);
            configBtn.attr('title', 'Configure').bind('click', e=>{
                this.openSettings(this.settingsDialogDiv.find('.jaga-dialog-content').empty());
                this.settingsDialog.open();
            });
            
            let deleteBtn = $('<button>').html('&#x1f5d1;').appendTo(div);
            deleteBtn.attr('title', 'Delete').bind('click', e=>{
                let dialog = div.find('dialog');
                if (dialog.size() == 0) {
                    dialog = $('<dialog>').addClass("sd-pad").appendTo(div);
                    dialog.html(`
                    <h3>Are you sure to delete this panel?</h3>
                    <div class="jaga-dialog-button-pane"><button>Yes</button><button>No</button></div>
                `);
                    dialog.find('button').at(0).click(e=>{
                        dialog.get().close();
                        this.config.deleted = true;
                        this.callbacks.reconfigure();
                    });
                    dialog.find('button').at(1).click(e=>{
                        dialog.get().close();
                    });
                }
                dialog.get().showModal();
            });
        }
    }

    
    openSettings(div) {}

    
    fillInputChannels(dataRequest) {}

    
    draw(dataPacket, displayTimeRange=null) {}

    
    _setupSettingsDialog() {
        this.settingsDialogDiv = $('<div>').addClass('sd-pad').css({'display':'none'}).appendTo(this.div);
        this.settingsDialog = new JGDialogWidget(this.settingsDialogDiv, {
            title: 'Panel Settings',
            closeOnGlobalClick: false,   // keep this false, otherwise not all inputs will be handled
            closeOnEscapeKey: true,
            close: e => { this.callbacks.reconfigure(); },
            buttons: { 'Apply & Close': null }
        });
    }

    
    _setupControlButtons() {
        if (this.div.css('position') == '') {
            this.div.css('position', 'relative');
        }
        const ctrlDivStyle = {
            'margin': '0',
            'padding': '5px',
            'position': 'absolute',
            'right': '0',
            'bottom': '0',
            'z-index': '+1',
            'display': 'flex',
            'flex-wrap': 'wrap',
            'flex-direction': 'column',
            'max-height': '100%',
            'font-size': '1rem',
            'z-index': '+10',
        };
        let ctrlDiv = $('<div>').addClass('sd-buttonchain').css(ctrlDivStyle).appendTo(this.div);
        new JGInvisibleWidget(ctrlDiv, { sensingObj: this.div, group: 'ctrl', opacity: 1, autoHide: 10 });
 
        this.addControlButtons(ctrlDiv);
    }

    
    _findDataTimeRange(data, displayTimeRange=null) {
        let [ from, to ] = [ -3600, 0 ];
        
        if (displayTimeRange) {
            [ from, to ] = [ displayTimeRange.from,  displayTimeRange.to ];
        }
        else if (data) {
            if (data?.__meta?.range) {
                [ from, to ] = [ data.__meta.range.from, data.__meta.range.to ];
            }
            else {
                for (const ch in data) {
                    if (data[ch].start && data[ch].length) {
                        [ from, to ] =  [ data[ch].start, data[ch].start + data[ch].length ];
                        break;
                    }
                }
            }
        }

        if (to <= 0) {
            to = $.time() + to;
        }
        if (from <= 0) {
            from = to + from;
        }
        
        return { from: from, to: to };
    }


    static _dataPacketIncludes(dataPacket, timestamp) {
        const range = dataPacket.__meta?.range ?? null;
        if (range === null) {
            return false;
        }
        
        let [from, to] = [ range.from, range.to ];
        if (to <= 0) {
            to += $.time();
        }
        if (from <= 0) {
            from += to;
        }

        return (from <= timestamp && to >= timestamp);
    }

    static _getLastTX(timeseries, transform=null) {
        let time=null, value=null;

        const [t, x] = [ timeseries?.t, timeseries?.x ];
        if (t == null) {
            return [time, value];
        }
        
        if (Array.isArray(t)) {
            let k = t.length - 1;
            while (k >= 0) {
                if (! Number.isNaN(x[k])) {
                    break;
                }
                k--;
            }
            if (k >= 0) {
                time = t[k] + (timeseries.start ?? 0);
                value = x[k];
            }
        }
        else {
            time = t + (timeseries.start ?? 0);
            value = x;
        }

        if (typeof(value) == "string") {
            try {
                value = JSON.parse(value);
            }
            catch(error) {
                ; // value is a non-JSON string
            }
        }

        if (transform) {
            value = transform.apply(value);
        }

        return [ time, value ];
    }
};
