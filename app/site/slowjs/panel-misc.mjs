// panel-misc.mjs //
// Author: Sanshiro Enomoto <sanshiro@uw.edu> //
// Created on 24 July 2022 //

export { WelcomePanel, ToolsPanel, FileManagerPanel, TaskManagerPanel, CruisePlannerPanel, ConfigEditorPanel };


import { JG as $, JGDateTime } from './jagaimo/jagaimo.mjs';
import { JGIndicatorWidget } from './jagaimo/jagawidgets.mjs';
import { Platform } from './platform.mjs';
import { Panel } from './panel.mjs';


class WelcomePanel extends Panel {
    static describe() {
        return { type: 'welcome', label: '' };
    }
    
    static buildConstructRows(table, on_done=config=>{}) {
    }

    
    constructor(div, style={}) {
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

        this.contentDiv.html(`
            <h3>To get started, create a new project</h3>
            See <a href="./slowdocs/index.html#ProjectSetup">SlowDash Documentation</a> for how to do it.
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

    
    async configure(config, options={}, callbacks={}) {
        await super.configure(config, options, callbacks);
    }
}



class ToolsPanel extends Panel {
    static describe() {
        return { type: 'tools', label: '' };
    }
    
    static buildConstructRows(table, on_done=config=>{}) {
    }

    
    constructor(div, style={}) {
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

        this.contentDiv.html(`
            <h3>Tools</h3>
            <ul>
              <li>&#x1f4c8; <a href="slowplot.html?grid=2x2">New Plot Layout</a>
              <li>&#x1f4e5; <a href="slowdown.html">Data Download</a>
              <li>&#x1f4c1; <a href="slowfile.html">Config File Manager</a>
              <li>&#x1f6f3; <a href="slowplan.html">Cruise Planner</a>
            </ul>
            <h3>Resources</h3>
            <ul>
              <li>&#x2753; <a href="./slowdocs/index.html" target="_blank">Documentation</a>
              <li>&#x1f4f0; <a href="https://github.com/slowproj/slowdash/wiki/Status-and-Updates" target="_blank">Release Note</a>
              <li>&#x1f422; <a href="https://github.com/slowproj/slowdash/" target="_blank">Code Repository</a>
            </ul>
        `);
        this.contentDiv.find('h3').css({
            'font-weight': 'normal',
            'font-size': '130%',
            'margin': '0.5em',
            'padding': '0',
        });
        this.contentDiv.find('ul').css({
            'list-style-type': 'none',
            'margin': '0 0 0 2em',
            'padding': '0 0 2em 0',
        });
        this.contentDiv.find('li').css({
            'padding-top': '0.5em'
        });
    }

    
    configure(config, options={}, callbacks={}) {
        super.configure(config, options, callbacks);
    }
}



class CruisePlannerPanel extends Panel {
    static describe() {
        return { type: 'cruise_planner', label: '' };
    }
    
    static buildConstructRows(table, on_done=config=>{}) {
    }

    
    constructor(div, style={}) {
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

        this.contentDiv.html(`
          <h3>Itinerary Example</h3>
          <div style="margin-left:3em;width:95%">
              <pre style="width:100%;border:thin solid gray;border-radius:5px;padding:0.5em"></pre>
              See <a href="slowdocs/index.html#AutoCruise" target="_blank">Document</a> for details.
          </div>
          <h3>Write Yours Here</h3>
          <div style="margin-left:3em;width:95%">
            <form>
              <textarea spellcheck="false" style="width:100%;height:15em;border-radius:5px;padding:0.5em"></textarea>
              <p>
              slowcruise-<input type="text" name="name" pattern="^[a-zA-Z][a-zA-Z0-9_\\-]*$" required="true" placeholder="name">.yaml 
              <button disabled>Create</button>
              <p>
              (to edit an existing itinerary, use the editor in the <a href="slowfile.html">Config File Manager</a>)
          </div>
        `);
        this.contentDiv.find('h3').css({
            'font-weight': 'normal',
            'font-size': '130%',
            'margin': '0.5em',
            'padding': '0',
        });
        this.contentDiv.find('pre').text(
`title: My Slow Cruise
interval: 10
pages:
  - slowplot.html?config=slowplot-Demo.json
  - slowplot.html?config=slowplot-Summary.json
  - https://github.com/slowproj/slowdash
`       );
        this.contentDiv.find('textarea').val(
`title: My Slow Cruise
interval: 10
pages:
  - slowplot.html?config=slowplot-XXX.json
  - slowplot.html?config=slowplot-XXX.json
`       );

        this.savePopup = $('<dialog>').addClass('sd-pad').appendTo(div);
        let nameInput = this.contentDiv.find('input').at(0).css('width','10em');
        let submitButton = this.contentDiv.find('button').at(0);
        nameInput.bind('input', e=>{
            if (nameInput.get().validity.valid) {
                submitButton.enabled(true);
            }
            else {
                submitButton.enabled(false);
            }
        });
        submitButton.bind('click', e=>{
            e.preventDefault();
            const filename = 'slowcruise-' + nameInput.val() + '.yaml';
            const content = this.contentDiv.find('textarea').val();
            Platform.upload(this.savePopup, 'config/file/' + filename, content);
        });
    }

    
    configure(config, options={}, callbacks={}) {
        super.configure(config, options, callbacks);
        this.contentDiv.find('textarea').focus();
    }
}


class ConfigEditorPanel extends Panel {
    static describe() {
        return { type: 'config_editor', label: '' };
    }
    
    static buildConstructRows(table, on_done=config=>{}) {
    }

    
    constructor(div, style={}) {
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
            Platform.upload(this.buttonDiv.find('dialog'), 'config/file/' + filename, this.textarea.val(), {
                contentType: 'text/plain; charset=utf-8',
                overwritable: true,
                quietOnSuccess: true,
                on_success: () => {
                    location.reload();
                }
            });
        });
    }

    
    configure(config, options={}, callbacks={}) {
        super.configure(config, options, callbacks);
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

        this._load(thisconfig.file);
    }

    
    async _load(filepath) {
        let content = null;
        try {
            let response = await fetch('./api/config/file/' + filepath);
            if (! response.ok) {
                throw new Error(response.status + " " + response.statusText);
            }
            content = await response.text();
        }
        catch (error) {
            this.statusDiv.text(`Server Error: ${error.message}`);
        }
        this.textarea.val(content);

        let contentlist = [];
        try {
            let response = await fetch('./api/config/contentlist/');
            if (! response.ok) {
                throw new Error(response.status + " " + response.statusText);
            }
            contentlist = await response.json();
        }
        catch (error) {
            this.statusDiv.text(`Server Error: ${error.message}`);
        }
        for (const meta of contentlist) {
            if (meta.config_file != filepath) {
                continue;
            }
            if (meta.config_error) {
                this.statusDiv.text(meta.config_error);
                if (meta.config_error_line > 0) {
                    const lines = content.split('\n');
                    const pos1 = lines.slice(0, meta.config_error_line-1).join('\n').length;
                    const pos2 = pos1 + lines[meta.config_error_line-1].length;
                    this.textarea.focus();
                    this.textarea.get().setSelectionRange(pos1, pos2);
                }
            }
        }
    }
}



class FileManagerPanel extends Panel {
    static describe() {
        return { type: 'filemanager', label: '' };
    }
    
    static buildConstructRows(table, on_done=config=>{}) {
    }

    
    constructor(div, style={}) {
        super(div, style);

        const css = {
            titleDiv: {
                width:'calc(100% - 10px)',
                'font-family': 'sans-serif',
                'font-size': '20px',
                'font-weight': 'normal',
                'margin-bottom': '0',
                'white-space': 'nowrap',
                'overflow': 'hidden',
            },
            contentDiv: {
                position: 'relative',
                width:'calc(100% - 35px)',
                height:'calc(100% - 35px)',
                margin: '0px 10px 10px 10px',
                padding:'5px',
                overflow:'auto',
            },
            box: {
                width: 'calc(100% - 16px)',
                margin: '5px',
                border: '2px solid gray',
                color: 'gray',
                'border-radius': '5px',
                cursor: 'pointer',
            },
            box_ready: {
                'border-color': 'gray',
            },
            box_active: {
                'border-color': 'red',
            },
            dropzone: {
                width: '100%',
                height: '8rem',
            },
            tableDiv: {
                position: 'relative',
                width:'calc(100% - 12px)',
                height:'calc(100% - 34px - 10rem - 10em)',
                'margin-top': '10px',
                'margin-left': '10px',
                padding:0,
                overflow:'auto',
            },
            filetable: {
                width: 'calc(100% - 20px)',
                margin: '5px',
                padding: 0,
                border: 'none',
                'white-space': 'nowrap',
            }
        };
        
        this.contentDiv = $('<div>').css(css.contentDiv).appendTo(div);

        $('<div>').css(css.titleDiv).text('Create File').appendTo(this.contentDiv);
        $('<span>').text('Name ').css('margin-left', '5px').appendTo(this.contentDiv);
        this.newFileInput = $('<input>').appendTo(this.contentDiv);
        let newFileButton = $('<button>').text('Create & Edit').appendTo(this.contentDiv);
        this.filetype_comment = $('<span>').text('').appendTo(this.contentDiv);
        
        $('<div>').css(css.titleDiv).css('margin-top','1em').text('Upload Files').appendTo(this.contentDiv);
        let box = $('<div>').css(css.box).appendTo(this.contentDiv);
        let dropzone = $('<div>').css(css.dropzone).appendTo(box);
        let dropInput = $('<input>').attr('type','file').css('display', 'none');
        this.overwritable = $('<div>').appendTo(this.contentDiv).html('<label><input type="checkbox">Overwrite without confirmation</label>').find('input');
        $('<span>').text('Drop a file here, or click this to select a file').appendTo(dropzone);
        
        $('<div>').css(css.titleDiv).css('margin-top', '1em').text('File List').appendTo(this.contentDiv);
        let fileTableDiv = $('<div>').css(css.tableDiv).appendTo(this.contentDiv);
        this.fileTable = $('<table>').addClass('sd-data-table').css(css.filetable).appendTo(fileTableDiv);
        
        this.indicator = new JGIndicatorWidget($('<div>').appendTo(div));
        this.savePopup = $('<dialog>').addClass('sd-pad').appendTo(div);
        this.deletePopup = $('<dialog>').addClass('sd-pad').appendTo(div);
        
        newFileButton.bind('click', e => {
            this._createFile(this.newFileInput.val(), e);
        });
        dropzone.bind('dragenter', e => {
            e.preventDefault();
            box.css(css.box_active);
        });
        dropzone.bind('dragover', e => {
            e.preventDefault();
            box.css(css.box_active);
        });
        dropzone.bind('dragleave', e => {
            e.preventDefault();
            box.css(css.box_ready);
        });
        dropzone.bind('drop', e => {
            e.preventDefault();
            box.css(css.box_ready);
            this._upload(e.dataTransfer.files, e);
        });
        $('body').bind('dragover', e => { e.preventDefault();});
        $('body').bind('drop', e => { e.preventDefault();});
        dropzone.bind('click', e => {
            dropInput.click();
        });
        dropInput.bind('change', e => {
            this._upload(e.target.files ?? [], e);
        });
    }

    
    configure(config, options={}, callbacks={}) {
        super.configure(config, options, callbacks);
        this.is_secure = options.is_secure;
        
        this._updateFileList();
        if (this.is_secure) {
            this.filetype_comment.text(' (allowed file types: json, yaml, csv, html, py, js)');
            this.newFileInput.attr('pattern', '.+\.(json|yaml|csv|html|py|js)')
        }
        else {
            this.filetype_comment.text(' (allowed file types: json, yaml, csv, html)');
            this.newFileInput.attr('pattern', '.+\.(json|yaml|csv|html)')
        }
    }


    _createFile(filename, event=null) {
        if (! filename) {
            return;
        }

        const url = './api/config/file/' + filename;
        this.indicator.open("Sending Command...", "&#x23f3;", event?.clientX ?? null, event?.clientY ?? null);
        fetch(url, {
            method: 'POST',
            body: ''
        })
        .then(response => {
            if (response.status == 202) {
                this.indicator.close("File already exists", "&#x274c;", 5000);
                return;
            }
            if (! response.ok) {
                throw new Error(response.status + " " + response.statusText);
            }
            this.indicator.close("File created", "&#x2705;", 1000);
            this._updateFileList(); // for future "back"
            window.location = `slowedit.html?filename=${filename}`;
        })
        .catch (e => {
            this.indicator.close("Error on file creation: " + e.message, "&#x274c;", 5000);
        });
    }

    
    _upload(files, event=null) {
        for (const file of files) {
            const reader = new FileReader();
            reader.onload = (e) => {
                const content = e.target.result;
                Platform.upload(this.savePopup, 'config/file/' + file.name, content, {
                    contentType: 'application/octet-stream',
                    overwritable: this.overwritable.val(),
                    quietOnSuccess: true,
                    on_success: () => {
                        this.indicator.close("File uploaded", "&#x2705;", 1000);
                        this._updateFileList();
                    },
                    on_cancel: () => {
                        this.indicator.close();
                    },
                    on_error: err => {
                        this.indicator.close();
                    }
                });
            }
            
            this.indicator.open("Uploading " + file.name, "&#x23f3;", event?.clientX ?? null, event?.clientY ?? null);
            reader.readAsArrayBuffer(file);
        }
    }


    _deleteFile(filename) {
        let commitDeletion = (() => {
            this.indicator.open("Deleting " + filename, "&#x23f3;");
            fetch(`./api/config/file/${filename}`, {
                method: 'DELETE',
            })
                .then(response => {
                    if (! response.ok) {
                        throw new Error(response.status + " " + response.statusText);
                    }
                    this.indicator.close("File deleted", "&#x2705;", 1000);
                    this._updateFileList();
                })
                .catch (e => {
                    this.indicator.close("Deletion Failed: " + e.message, "&#x274c;", 5000);
                    return null;
                })
        });
        this.deletePopup.html(`
            <h3>Delete ${filename}?</h3>
            <div class="jaga-dialog-button-pane"><button>Yes</button><button>No</button></div>
        `);
        this.deletePopup.find('button').at(0).click(e=>{
            commitDeletion();
            this.deletePopup.get().close();
        });
        this.deletePopup.find('button').at(1).click(e=>{
            this.deletePopup.get().close();
        });
        this.deletePopup.get().showModal();
    }
        
    async _updateFileList() {
        this.fileTable.empty();
        let tr = $('<tr>').appendTo(this.fileTable);
        $('<th>').text("Name").appendTo(tr);
        $('<th>').css('width', '1em').appendTo(tr);
        $('<th>').text("Last Modified").appendTo(tr);
        $('<th>').text("Size").appendTo(tr);
        $('<th>').text("Owner").appendTo(tr);
        $('<th>').text("Group").appendTo(tr);
        $('<th>').text("Mode").appendTo(tr);

        const css_button = {
            'margin-left': '0.7em',
            'filter': 'grayscale(50%)',
            'text-decoration': 'none',
        };

        let filelist = null;
        try {
            let response = await fetch('./api/config/filelist?sortby=name');
            if (! response.ok) {
                throw new Error(response.status + " " + response.statusText);
            }
            filelist = await response.json();
        }
        catch (e) {
            console.log(e);
            return null;
        }

        let readables = ['json', 'yaml', 'csv', 'html', 'svg', 'jpg', 'jpeg', 'png', 'obj'];
        let editables = ['json', 'yaml', 'html', 'csv', 'svg'];
        if (this.is_secure) {
            readables.push('py', 'js');
            editables.push('py', 'js');
        }

        for (const entry of filelist ?? []) {
            const ext = entry.name.split('.').pop();

            let name;
            if (editables.includes(ext)) {
                name = $('<a>').attr({
                    href: `slowedit.html?filename=${entry.name}`,
                    target: '_blank',
                });
            }
            else if (readables.includes(ext)) {
                name = $('<a>').attr({
                    'href': `./api/config/file/${entry.name}`,
                    'target': '_blank',
                });
            }
            else {
                name = $('<span>');
            }
            name.text(entry.name);

            let trash;
            if (readables.includes(ext)) {
                trash = $('<span>').html('&#x1f5d1').css({
                    cursor: 'pointer',
                }).bind('click', e=>{
                    this._deleteFile(entry.name);
                });
            }
            else {
                trash = $('<span>').html('&#x26d4;');
            }
            
            let tr = $('<tr>');
            $('<td>').appendTo(tr).append(name);
            $('<td>').appendTo(tr).append(trash).css('text-align', 'center').css('padding', 0);
            $('<td>').appendTo(tr).text((new JGDateTime(entry.mtime)).asString('%b %d, %Y %H:%M')).css('text-align', 'center');;
            $('<td>').appendTo(tr).text(Number(entry.size).toLocaleString('en-US')).css('text-align', 'right');
            $('<td>').appendTo(tr).text(entry.owner).css('text-align', 'center');;
            $('<td>').appendTo(tr).text(entry.group).css('text-align', 'center');;
            $('<td>').appendTo(tr).text(entry.mode).css('font-family', 'monospace').css('text-align', 'center');;
            this.fileTable.append(tr);
        }
    }    
}



class TaskManagerPanel extends Panel {
    static describe() {
        return { type: 'taskmanager', label: '' };
    }

    
    static buildConstructRows(table, on_done=config=>{}) {
    }

    
    constructor(div, style={}) {
        super(div, style);
        this.is_secure = false;
        
        this.frameDiv = $('<div>').appendTo(div);        
        this.titleDiv = $('<div>').appendTo(this.frameDiv);
        this.contentDiv = $('<div>').appendTo(this.frameDiv);
        this.tableDiv = $('<div>').appendTo(this.contentDiv);
        this.title2Div = $('<div>').appendTo(this.contentDiv);
        this.consoleDiv = $('<div>').appendTo(this.contentDiv);
        this.inputDiv = $('<div>').appendTo(this.contentDiv);
        
        this.table = $('<table>').appendTo(this.tableDiv);
        this.table.html('<tr><td></td></tr><tr><td>loading task list...</td></tr>');
        this.indicator = new JGIndicatorWidget($('<div>').appendTo(div));
        this.last_text = '';

        this.frameDiv.css({
            width:'calc(100% - 44px)',
            height:'calc(100% - 44px)',
            margin: '10px 10px 10px 10px',
            padding:'10px',
            border: 'thin solid',
            'border-radius': '5px',
            overflow:'auto',
        });
        this.titleDiv.css({
            width:'calc(100% - 10px)',
            'font-family': 'sans-serif',
            'font-size': '20px',
            'font-weight': 'normal',
            'margin': '0',
            'margin-bottom': '10px',
            'white-space': 'nowrap',
            'overflow': 'hidden',
        });
        this.title2Div.css({
            width:'calc(100% - 10px)',
            'font-family': 'sans-serif',
            'font-size': '20px',
            'font-weight': 'normal',
            'margin': '0',
            'margin-bottom': '10px',
            'white-space': 'nowrap',
            'overflow': 'hidden',
        }).html('Console <span style="font-size:60%">for print() and input()</span>');
        this.contentDiv.css({
            position: 'relative',
            width:'100%',
            height:'calc(100% - 10px - 25px)',
            margin: 0,
            padding:0,
            overflow:'hidden',
        });
        this.tableDiv.css({
            position: 'relative',
            width:'calc(100% - 14px)',
            height:'calc(50% - 5px)',
            margin: 0,
            padding:0,
            overflow:'auto',
        });
        this.consoleDiv.css({
            position: 'relative',
            width:'calc(100% - 20px)',
            height:'calc(50% - 15px - 5em)',
            margin: 0,
            padding: '5px',
            overflow:'auto',
            border: 'thin solid gray',
            'border-radius': '5px',
            'white-space': 'pre',
            'font-size': '80%',
        });
        this.inputDiv.css({
            position: 'relative',
            width:'calc(100% - 20px)',
            height:'calc(3em - 10px)',
            margin: 0,
            padding: '5px',
            overflow:'hidden',
        });
        this.table.addClass('sd-data-table').css({
            width: '100%',
            margin: 0,
            padding: 0,
            border: 'none',
        });

        $('<span>').appendTo(this.titleDiv).html('SlowTask Status <span style="font-size:80%">(<a href="slowdocs/index.html#ControlsScript" target="_blank">?</a>)</span>');

        this.inputDiv.html('&gt; <input style="width:calc(100% - 10em)"><button>Send</button>');
        this.inputDiv.find('button').bind('click', e=>{
            const line = $(e.target).closest('div').find('input').val();
            this._send_console(line, e);
        });

        this.tasklist_revision = 0;
        this.console_revision = 0;
        this.is_tasklist_loading = false;
        this.is_console_loading = false;
        this.is_tasklist_error = false;
        this.is_console_error = false;
    }

    
    configure(config, options={}, callbacks={}) {
        super.configure(config, options, callbacks);
        this.is_secure = options.is_secure;
        
        this.tasklist_revision = 0;
        this.console_revision = 0;
        this.is_tasklist_error = false;
        this.is_console_error = false;

        if (! this.is_tasklist_loading) {
            this.is_tasklist_loading = true;
            this._load_tasklist();
        }
        if (! this.is_console_loading) {
            this.is_console_loading = true;
            this._load_console();
        }
    }


    async _load_tasklist() {
        try {
            let response = await fetch('api/control/task?since='+this.tasklist_revision);
            let record = await response.json();
            this._render_task_table(record.tasks);
            this.tasklist_revision = record.revision;
        }
        catch (e) {
            console.log("Error on fetching tasklist: ", e);
            this.is_tasklist_error = true;
        }
        if (! this.is_tasklist_error) {
            setTimeout(()=>this._load_tasklist(), 1000);
        }
    }
        

    async _load_console() {
        try {
            let response = await fetch('api/console?since='+this.console_revision);
            let record = await response.json();
            this._render_console(record.text);
            this.console_revision = record.revision;
        }
        catch (e) {
            console.log("Error on fetching console: ", e);
            this.is_console_error = true;
        }
        if (! this.is_console_error) {
            setTimeout(()=>this._load_console(), 1000);
        }
    }

    
    async _send_console(line, event=null) {
        const url = './api/console/';
        try {
            this.indicator.open("sending command...", "&#x23f3;", event?.clientX ?? null, event?.clientY ?? null);
            let response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json; charset=utf-8' },
                body: line,
            });
            if (! response.ok) {
                throw new Error(response.status + " " + response.statusText);
            }
            this.indicator.close("ok", "&#x2705;", 1000);
        }
        catch (e) {
            console.log(e);
            this.indicator.close("Error: " + e.message, "&#x274c;", 5000);
        }
    }

    
    async _send_control(name, action, event=null) {
        const url = `./api/control/task/${name}`;
        try {
            this.indicator.open("sending command...", "&#x23f3;", event?.clientX ?? null, event?.clientY ?? null);
            let response = await fetch(url, {
                method: 'POST',
                body: `{"action":"${action}"}`
            });
            if (! response.ok) {
                throw new Error(response.status + " " + response.statusText);
            }
            this.indicator.close("ok", "&#x2705;", 1000);
        }
        catch (e) {
            this.indicator.close("error: " + e.message, "&#x274c;", 5000);
        }
    }
    

    _render_task_table(record) {
        this.table.empty();
        let tr = $('<tr>');
        $('<th>').text("Name").appendTo(tr);
        $('<th>').text("Routine Task").css('width','30%').appendTo(tr);
        $('<th>').text("Command Task").css('width','30%').appendTo(tr);
        $('<th>').text("Status").appendTo(tr);
        $('<th>').text("Control").appendTo(tr);
        tr.appendTo(this.table);
        const bg = window.getComputedStyle(tr.get()).getPropertyValue('background-color');
        tr.find('th').css({position: 'sticky', top:0, left:0, background: bg});

        function clip(text, len=16) {
            if (text.length > len) {
                return text.substr(0, len) + '...';
            }
            else {
                return text;
            }
        }

        for (let entry of record) {
            let last_routine = 'none', last_command = 'none', status = '&#x2615; inactive';
            if (entry.last_routine !== null) {
                const since = new JGDateTime(parseInt(entry.last_routine_time)).asString('%a %H:%M');
                last_routine = (
                    (entry.is_routine_running ? 'running ' : 'completed ') +
                    clip(entry.last_routine ?? '') +
                    (entry.is_routine_running ? ', since ' : ', at ') + since
                );
            }
            if (entry.last_command !== null) {
                const since = new JGDateTime(parseInt(entry.last_command_time)).asString('%a %H:%M');
                last_command = (
                    (entry.is_command_running ? 'running ' : 'completed ') +
                    clip(entry.last_command.substr(entry.name.length+1) ?? '') +
                    (entry.is_command_running ? ', since ' : ', at ') + since
                );
            }
            if (entry.has_error) {
                //status = '&#x2757; ERROR';
                status = '&#x1f6a8; ERROR';
            }
            else if (entry.is_stopped) {
                status = '&#x1f425; stopped';
            }
            else if (entry.is_waiting_input) {
                status = '&#x23f3; waiting';
            }
            else if (entry.is_routine_running || entry.is_command_running) {
                status = '&#x1f3c3; running';
            }
            else if (entry.is_loaded) {
                status = '&#x2705; loaded';
            }
            let name;
            if (this.is_secure) {
                name = `<a href="slowedit.html?filename=slowtask-${entry.name}.py" target="_blank">${entry.name}</a>`;
            }
            else {
                name = entry.name;
            }
            let control;
            if (entry.is_routine_running || entry.is_command_running) {
                control = '<button disabled>Start</button><button>Stop</button>';
            }
            else {
                control = '<button>Start</button><button disabled>Stop</button>';
            }
            
            let tr = $('<tr>');
            $('<td>').appendTo(tr).html(name);
            $('<td>').appendTo(tr).text(last_routine);
            $('<td>').appendTo(tr).text(last_command);
            $('<td>').appendTo(tr).html(status);
            $('<td>').appendTo(tr).attr('align','center').html(control);
            tr.find('button').bind('click', e=>{
                const action = $(e.target).text().toLowerCase();
                this._send_control(entry.name, action, e);
            });
            tr.appendTo(this.table);
        }
    }

    _render_console(text) {
        if (text != this.last_text) {
            this.consoleDiv.text(text);
            this.consoleDiv.get().scrollTop = this.consoleDiv.get().scrollHeight;
            this.last_text = text;
        }
    }
}
