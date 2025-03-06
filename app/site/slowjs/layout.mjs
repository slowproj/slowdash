// layout.mjs //
// Author: Sanshiro Enomoto <sanshiro@uw.edu> //
// Created on 18 November 2021 //
// Refactored on 18 June 2022 //
// Refactored on 5 March 2025 //


import { JG as $ } from './jagaimo/jagaimo.mjs';
import { JGInvisibleWidget, JGDialogWidget } from './jagaimo/jagawidgets.mjs';
import { PanelPluginLoader } from './panel-plugin-loader.mjs';


export class Layout {
    constructor(div, style={}) {
        this.layoutDiv = div;
        this.PanelClassList = null;
        this.panels = [];
        
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
    }


    async configure(config=null, callbacks={}) {
        const default_callbacks = {
            changeDisplayTimeRange: (range) => {},
            reconfigure: () => { this.configure(); },
            forceUpdate: () => {},
            suspend: (duration) => {},
            popoutPanel: (index) => {},
            publish: (topic, message) => {},
        };
        if (config !== null) {
            this.config = config;
            this.callbacks = $.extend({}, default_callbacks, this.callbacks ?? {}, callbacks);
        }
        if (this.config.control === undefined) {
            this.config.control = {};
        }
        if ((this.config.control.grid?.columns ?? 0) < 1) {
            this.config.control.grid = { columns: 1, rows: 1 };
        }
        if (this.config.panels === undefined) {
            this.config.panels = [];
        }

        this.style = $.extend({}, this.defaultStyle, this.config._project?.style?.panel ?? {});
        this.dimension = {
            layoutWidth: null,
            layoutHeight: null,
            panelWidth: null,
            panelHeight: null,
            fontScaling: 100.0,
        };

        if (! this.PanelClassList) {
            const loader = new PanelPluginLoader();
            this.PanelClassList = await loader.load();
        }

        this._purgePanels();
        
        if (config !== null) {
            this.layoutDiv.empty();
            this.panels = [];

            this._setupDimensions();
            this._buildPanels();
            await this._configurePanels();

            if (! this.config.control.immutable) {
                this._buildAddNewPanel();
            }
        }
        else {
            this._setupDimensions();
            await this._configurePanels();
            this._configureAddNewPanel();
        }
    }


    fillInputChannels(inputChannels) {
        for (let panel of this.panels) {
            panel.fillInputChannels(inputChannels);
        }
    }


    drawRange(dataPacket, displayTimeRange) {
        for (let panel of this.panels) {
            panel.drawRange(dataPacket, displayTimeRange);
        }
    }
    

    _setupDimensions() {
        this.dimension.layoutWidth = document.documentElement.clientWidth;
        this.dimension.layoutHeight = document.documentElement.clientHeight - this.layoutDiv.pageY();

        const scrollBarWidth = 20; // this does not exist yet, so <html>.clientWidth does not include it
        const layoutInnerWidth = this.dimension.layoutWidth - scrollBarWidth;
        const layoutInnerHeight = this.dimension.layoutHeight /*- scrollBarWidth */ - 2; // 4 for panel border on hover
        
        const ncols = parseInt(this.config.control.grid.columns ?? 1);
        const nrows = parseInt(this.config.control.grid.rows ?? 1);
        this.dimension.panelWidth = Math.floor(layoutInnerWidth / ncols);
        this.dimension.panelHeight = Math.floor(layoutInnerHeight / nrows);

        if (ncols < 3) {
            this.dimension.fontScaling = 100.0;
        }
        else if (ncols == 3) {
            this.dimension.fontScaling = 80;
        }
        else {
            this.dimension.fontScaling = 100.0 / (ncols-2);
        }

        this.layoutDiv.css({
            'position': 'relative',
            'width': this.dimension.layoutWidth + 'px',
            'height': this.dimension.layoutHeight + 'px',
            'overflow': 'auto',
            'display': 'flex',
            'flex-wrap': 'wrap',
        });
    }


    async _buildPanels() {        
        this.panels = [];
        for (const entry of this.config.panels) {
            const panelDiv = this._createPanelDiv();
            const panel = this._createPanel(panelDiv, entry.type);
            this.panels.push(panel);
        }
        
    }


    _purgePanels() {
        for (let panel of this.panels) {
            if (panel.config?.deleted ?? false) {
                panel.deleted = true;
            }
        }
        
        const removeDeleted = () => {
            for (let i = 0; i < this.panels.length; i++) {
                if (this.panels[i].deleted ?? false) {
                    this.panels[i].div.remove();
                    this.panels.splice(i, 1);
                    removeDeleted();
                    return;
                }
            }
        }
        removeDeleted();

        this.config.panels = this.config.panels.filter(p => !(p.deleted ?? false));
    }
    
        
    _createPanelDiv() {
        let panelDiv = $('<div>').addClass('sd-panel');
        
        const addnewPanel = this.layoutDiv.find('.sd-addnew-panel');
        if (addnewPanel.size() > 0) {
            this.layoutDiv.insertBefore(panelDiv, addnewPanel);
        }
        else {
            this.layoutDiv.append(panelDiv);
        }
        
        if (this.config.layout?.focus_highlight !== false) {
            panelDiv.bind('pointerenter', e => {
                const target = $(e.target);
                target.css('border', '1px solid rgba(128,128,128,0.7)');
                
                const duration = parseInt(this.config.layout?.focus_highlight ?? 10);
                if (duration > 0) {
                    let timeoutId = target.attr('sd-timeoutId');
                    if (timeoutId) {
                        clearTimeout(timeoutId);
                    }
                    timeoutId = setTimeout(() => {
                        target.css('border', '1px solid rgba(128,128,128,0)');
                    }, duration*1000);
                    target.attr('sd-timeoutId', timeoutId);
                }
            });
            
            panelDiv.bind('mouseleave', e=>{
                $(e.target).css('border', '1px solid rgba(128,128,128,0)');
            });
        }

        return panelDiv;
    }

    
    _createPanel(div, panelType) {
        //... backwards compatibility
        if ((panelType === undefined) || (panelType == 'timeseries')) {
            panelType = 'timeaxis';
        }
        
        for (let PanelClass of this.PanelClassList) {
            if (panelType == PanelClass.describe().type) {
                return new PanelClass(div, this.style);
            }
        }
        if (panel === null) {
            console.log('unable to find panel type: ' + panelType);
        }
    }

    
    async _configurePanels() {
        $('.sd-panel').css({
            'width': (this.dimension.panelWidth-12)+'px',
            'height': (this.dimension.panelHeight-12)+'px',
            'position': 'relative',
            'margin': '5px',
            'padding': 0,
            'border-radius': '10px',
            'font-size': this.dimension.fontScaling + '%',
        });

        const callbacks = {
            changeDisplayTimeRange: range => {
                this.callbacks.changeDisplayTimeRange(range);
            },
            reconfigure: () => {
                this.callbacks.reconfigure();
            },
            forceUpdate: () => {
                this.callbacks.forceUpdate();
            },
            suspendUpdate: (duration) => {
                this.callbacks.suspend(duration);
            },
            popout: (p) => {
                for (let i = 0; i < this.panels.length; i++) {
                    if (this.panels[i] === p) {
                        this.callbacks.popoutPanel(i);
                    }
                }
            },
            publish: (topic, message) => {
                this.callbacks.publish(topic, message);
            },
        };

        const options = {
            project_name: this.config._project?.project?.name,
            is_display: this.config.control.immutable || ((this.config.control.mode ?? '') === 'display'),
            is_protected: (this.config.control.mode ?? '') === 'protected',
            is_secure: this.config._project?.project?.is_secure ?? false,
        };
        
        for (let i = 0; i < this.panels.length; i++) {
            if (this.panels[i]) {
                await this.panels[i].configure(this.config.panels[i], options, callbacks);
            }
        }
    }


    _buildAddNewPanel() {
        const divStyle = {
            'width': (this.dimension.panelWidth-100)+'px',
            'height': (this.dimension.panelHeight-80)+'px',
            'border-width': 'thin',
            'border-style': 'solid',
            'border-radius': '10px',
            'padding': '20px',
            'margin-left': '40px',
            'margin-top': '20px',
        };
        const buttonStyle = {
            'font-size': '120%',
        };
        const div = $('<div>').addClass('sd-pad').addClass('sd-addnew-panel').css(divStyle).appendTo(this.layoutDiv);
        if (this.config.panels.length > 0) {
            new JGInvisibleWidget(div);
        }

        const dialogDiv = $('<div>').addClass('sd-pad').css({'display':'none'});
        // cannot be layoutDiv, as 'position:fiexed' does not work under an element with transform
        dialogDiv.appendTo(this.layoutDiv.closest('body'));
        
        const dialog = new JGDialogWidget(dialogDiv, {
            title: 'Add a New Panel',
            closeOnGlobalClick: false,   // keep this false, otherwise not all inputs will be handled
            closeButton: true,
        });
        $('<button>').text('Add a New Panel').css(buttonStyle).appendTo(div).click(e=>{
            dialog.open();
        });

        this._buildAddNewDialog(dialogDiv.find('.jaga-dialog-content'), dialog);
        this._configureAddNewPanel();
    }

    
    _configureAddNewPanel() {
        const divStyle = {
            'width': (this.dimension.panelWidth-100)+'px',
            'height': (this.dimension.panelHeight-80)+'px',
        };
        let div = this.layoutDiv.find('.sd-addnew-panel');
        div.css(divStyle);
    }

    
    _buildAddNewDialog(div, dialog) {
        div.css({
            'font-size': '130%'
        });
        div.html(`
            <span style="font-size:140%">Create a New Panel</span>
            <table style="margin-top:1em;margin-left:1em">
              <tr><td>Type</td><td>
                <select style="font-size:130%">
                  <option hidden>Select...</option>
                </select>
              </td></tr>
            </table>
        `);

        const select = div.find('select');
        let PanelClassTable = {};
        for (const PanelClass of this.PanelClassList) {
            const desc = PanelClass.describe();
            if (desc.label) {
                select.append($('<option>').attr('value', desc.type).attr('label', desc.label).text(desc.label));
                PanelClassTable[desc.type] = PanelClass;
            }
        }
        
        let table = div.find('table');
        const addPanel = async config => {
            if (config) {
                this.config.panels.push(config);
                const panelDiv = this._createPanelDiv();
                const panel = this._createPanel(panelDiv, config.type);
                this.panels.push(panel);
                this.callbacks.reconfigure();
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
        select.bind('change', e=>{updateSelection();});
    }
};
