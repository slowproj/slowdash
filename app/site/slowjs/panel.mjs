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

    constructor(div, style) {
        this.div = div;
        this.style = style;
    }

    
    async configure(config, options, callbacks) {
        const default_callbacks = {
            changeDisplayTimeRange: range => {},
            forceUpdate: () => {},
            suspendUpdate: (duration) => {},
            reconfigure: () => {},
            popout: (p) => {},
            publish: (topic, message) => {},
        };

        this.config = config;
        this.callbacks = $.extend({}, default_callbacks, callbacks);
        this.options = $.extend({}, options);

        this._setupSettingsDialog();
        if (! options.is_display) {
            this._setupControlButtons(options.is_protected);
        }
    }

    
    addControlButtons(div, is_protected) {
        let popoutBtn = $('<button>').html('&#x2197;').appendTo(div);
        popoutBtn.attr('title', 'Pop out').bind('click', e=>{
            this.callbacks.popout(this);
        });

        if (is_protected) {
            return;
        }
        
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

    
    draw(data) {
        let range = {}; 
        const keys = Object.keys(data);
        if (keys.length > 0) {
            const d0 = data[keys[0]];
            range = { from: d0.start, to: d0.start + d0.length };
        }
        else {
            now = $.time();
            range = { from: now - 60, to: now };
        }
            
        this.drawRange({
            isTransitional: true,
            range: range,
            data: data
        });
    }

    
    openSettings(div) {}

    
    fillInputChannels(dataRequest) {}

    
    drawRange(dataPacket, displayTimeRange) {}

    
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

    
    _setupControlButtons(is_protected) {
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
 
        this.addControlButtons(ctrlDiv, is_protected);
    }
};
