// panel-misc.mjs //
// Author: Sanshiro Enomoto <sanshiro@uw.edu> //
// Created on 24 July 2022 //

import { JG as $ } from './jagaimo/jagaimo.mjs';
import { Panel } from './panel.mjs';
import { upload } from './controlframe.mjs';


export class WelcomePanel extends Panel {
    static describe() {
        return { type: 'welcome', label: '' };
    }
    
    static buildConstructRows(table, on_done=config=>{}) {
    }

    
    constructor(div, style) {
        super(div, style);
        this.contentDiv = $('<div>').appendTo(div);        
        this.contentDiv.css({
            position: 'relative',
            width:'calc(100% - 35px)',
            height:'calc(100% - 35px)',
            margin: '0px 10px 10px 10px',
            padding:'5px',
            overflow:'auto',
        });
    }

    
    configure(config, callbacks={}) {
        super.configure(config, callbacks);
        this.contentDiv.html(`
            <h3>To get started, create a new project</h3>
            See <a href="./docs/index.html">SlowDash Documentation</a> for how to do it.
            <p>
            <h3>Seeing this page unexpectedly?</h3>
            Check the project configuration:
            <ol>
               <li> A dedicated project directory must be created.
               <li> The <tt>SlowdashConfig.yaml</tt> file must exist at the project directory.
               <li> The project directry must be specified to <tt>slowdash</tt>:
               <ul>
                 <li> For standard installation (bare metal), do one of:
                 <ul>
                   <li> <tt>--project-dir=DIR</tt> option,
                   <li> <tt>SLOWDASH_PROJECT</tt> environmental variable, or
                   <li> running the <tt>slowdash</tt> command at the project directory.
                 </ul>
                 Configuration can be tested by running the <tt>slowdash</tt> command locally without the <tt>--port</tt> option.
                 <li> For Docker installation,
                 <ul>
                   <li> mount the project directory to <tt>/project</tt> by <tt>-v PROJECTDIR:/project</tt>
                 </ul>
             </ol>
        `);
    }
}



export class ConfigEditorPanel extends Panel {
    static describe() {
        return { type: 'config_editor', label: '' };
    }
    
    static buildConstructRows(table, on_done=config=>{}) {
    }

    
    constructor(div, style) {
        super(div, style);
        this.titleDiv = $('<div>').appendTo(div).text('File Editor');
        this.contentDiv = $('<div>').appendTo(div);
        
        this.nameDiv = $('<div>').appendTo(this.contentDiv);
        this.statusDiv = $('<pre>').appendTo(this.contentDiv);
        this.textarea = $('<textarea>').appendTo(this.contentDiv);
        this.buttonDiv = $('<div>').appendTo(this.contentDiv);
        this.buttonDiv.css('display', 'flex').html(`
            <div style="margin:10px; margin-left:auto;">
              <div class="jaga-dialog-button-pane">
                <button>Go Back</button>
                <button>Open SlowEdit</button>
                <button>Save and Reload</button>
              </div>
            </div>
            <dialog class="sd-pad"></dialog>
        `);

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
            width: 'calc(100% - 12px)',
            height: 'calc(100% - 20px - 2em)',
            margin: '10px',
            padding: '5px',
            overflow: 'auto',
        });
        this.nameDiv.css({
            width: 'calc(100% - 30px)',
            height: '2em',
            margin: 0,
            padding: 0,
        });
        this.statusDiv.css({
            width: 'calc(100% - 30px)',
            height: '2em',
            margin: 0,
            padding: 0,
        });
        this.textarea.css({
            width: 'calc(100% - 10px)',
            height: 'calc(100% - 10em)',
            wrap: 'off',
            'white-space': 'pre',
            'font-family': 'monospace',
            'font-size': '120%',
            color: 'purple',
            'overflow': 'auto',
            'resize': 'none',
        }).attr({
            spellcheck: false,
            autocomplete:"off",
        });

        this.buttonDiv.find('button').at(0).click(e=>{
            history.back();
        });
        this.buttonDiv.find('button').at(1).click(e=>{
            const filename = this.nameDiv.text();
            if (filename && filename.length < 3) {
                return;
            }
            window.location.href = `slowedit.html?filename=${filename}`;
        });
        this.buttonDiv.find('button').at(2).click(e=>{
            const filename = this.nameDiv.text();
            if (filename && filename.length < 3) {
                return;
            }
            upload(this.buttonDiv.find('dialog'), 'config/file/' + filename, this.textarea.val(), {
                contentType: 'text/plain; charset=utf-8',
                overwritable: true,
                quietOnSuccess: true,
                on_success: () => {
                    location.reload();
                }
            });
        });
    }

    configure(config, callbacks={}) {
        super.configure(config, callbacks);
        const defaults = {
            title: 'File Editor',
            file: null,
        }
        let thisconfig = $.extend({}, defaults, config);

        if (! thisconfig.file) {
            return;
        }
        this.titleDiv.text(thisconfig.title);
        this.nameDiv.text(thisconfig.file);
        
        fetch('./api/config/file/' + thisconfig.file + '?content=raw')
            .then(response => {
                if (! response.ok) {
                    throw new Error(response.status + " " + response.statusText);
                }
                return response.text();
            })
            .catch(error => {
                this.statusDiv.text(`Server Error: ${error.message}`);
            })
            .then(content => {
                this.textarea.val(content);
                
                fetch('./api/config/file/' + thisconfig.file + '?content=meta')
                    .then(response => {
                        if (! response.ok) {
                            throw new Error(response.status + " " + response.statusText);
                        }
                        return response.json();
                    })
                    .catch(error => {
                        this.statusDiv.text(`Server Error: ${error.message}`);
                    })
                    .then(doc => {
                        if (doc.error) {
                            this.statusDiv.text(doc.error);
                            if (doc.error_line > 0) {
                                const lines = content.split('\n');
                                const pos1 = lines.slice(0, doc.error_line-1).join('\n').length;
                                const pos2 = pos1 + lines[doc.error_line-1].length;
                                this.textarea.focus();
                                this.textarea.get().setSelectionRange(pos1, pos2);
                            }
                        }
                    });
            });
    }
}
