// panel-misc.mjs //
// Author: Sanshiro Enomoto <sanshiro@uw.edu> //
// Created on 24 July 2022 //

import { JG as $, JGDateTime } from './jagaimo/jagaimo.mjs';
import { Panel, bindInput } from './panel.mjs';


export class CatalogPanel extends Panel {
    static describe() {
        return { type: 'catalog', label: '' };
    }
    
    static buildConstructRows(table, on_done=config=>{}) {
        let tr1 = $('<tr>').html(`
            <td>Type</td><td><input></td>
       `).appendTo(table);
        let tr2 = $('<tr>').html(`
            <td style="padding-top:1em"><button hidden style="font-size:x-large">Create</button></td><td></td>
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
                type: 'catalog',
                catalog_type: table.find('input').val(),
            };
            on_done(config);
        });
    }

    
    constructor(div, style) {
        super(div, style);        
        this.frameDiv = $('<div>').appendTo(div);        
        this.frameDiv.text("loading catalog...");

        this.frameDiv.css({
            width:'calc(100% - 44px)',
            height:'calc(100% - 44px)',
            margin: '10px 10px 10px 10px',
            padding:'10px',
            border: 'thin solid',
            'border-radius': '5px',
            overflow:'auto',
        });
        this.titleDiv_css = {
            width:'calc(100% - 10px)',
            'font-family': 'sans-serif',
            'font-size': '20px',
            'font-weight': 'normal',
            'margin-bottom': '0',
            'white-space': 'nowrap',
            'overflow': 'hidden',
        };
        this.contentDiv_css = {
            position: 'relative',
            width:'calc(100% - 10px)',
            'margin-top': '10px',
            padding:0,
        };
        this.table_css = {
            'width': '100%',
            margin: 0,
            padding: 0,
            border: 'none',
            'margin-bottom': '2em',
            'white-space': 'nowrap',
        };
    }

    
    configure(config, callbacks={}, project_config=null) {
        super.configure(config, callbacks);

        if (project_config?.project?.name) {
            this.cachePath = `slowdash-${project_config.project.name}-Catalog`;
        }
        else {
            this.cachePath = null;
        }
        
        this.content_types = this.config.catalog_type.split(/[ ,;]+/);
        this._load();
    }

    
    openSettings(div) {
        let inputsDiv = $('<div>').appendTo(div);
        inputsDiv.html(`
            <table style="margin-top:1em">
              <tr><th>type</th><td><input></td></tr>
            </table>
        `);

        let k = 0;
        bindInput(this.config, 'catalog_type', inputsDiv.find('input').at(k++).css('width', '20em'));
    }

    
    _load() {
        let processDoc = (doc) => {
            for (const content_type of this.content_types) {
                let catalog = [];
                for (let entry of doc[content_type] ?? []) {
                    if (entry.config_file) {
                        let href = './' + content_type + '.html?config=' + entry.config_file;
                        catalog.push({
                            name: entry.name,
                            href: href,
                            title: entry.title || entry.name,
                            description: entry.description ?? '',
                            file: entry.config_file ?? null,
                            error: entry.config_error ?? null,
                            mtime: entry.mtime || null,
                        });
                    }
                }
                this._render(content_type, catalog);
            }
        };
        
        if (this.cachePath) {
            const cacheTime = localStorage.getItem(this.cachePath + '-cachetime');
            if (parseFloat(cacheTime ?? 0) > $.time() - 3600) {
                let cachedDoc = localStorage.getItem(this.cachePath + '-doc');
                if (cachedDoc) {
                    processDoc(JSON.parse(cachedDoc));
                    return;
                }
            }
        }

        fetch('./api/config/list')
            .then(response => {
                if (! response.ok) {
                    throw new Error(response.status + " " + response.statusText);
                }
                return response.json();
            })
            .catch(e => {
                return null;
            })
            .then(proj_config => {
                if (! proj_config?.contents) {
                    for (const content_type of content_types) {
                        this._render(content_type, proj_config === null ? null : []);
                    }
                    return;
                }
                else {
                    processDoc(proj_config.contents);
                    if (this.cachePath) {
                        localStorage.setItem(this.cachePath + '-cachetime', $.time());
                        localStorage.setItem(this.cachePath + '-doc', JSON.stringify(proj_config.contents));
                    }
                }
            });
    }

    
    _render(content_type, catalog) {
        if (this.frameDiv.find('div').size() == 0) {
            this.frameDiv.empty();
        }

        let title = content_type.substr(0,1).toUpperCase() + content_type.substr(1);
        if (title.length > 4 && title.substr(0,4) == 'Slow') {
            title = 'Slow' + title[4].toUpperCase() + title.substr(5);
        }
        
        let headDiv = $('<div>').appendTo(this.frameDiv).css(this.titleDiv_css).css('display','flex');
        $('<span>').appendTo(headDiv).text(title);
        let updateButton = $('<span>').attr('title', 'update').html('&#x1f504;').appendTo(headDiv).css({
            'margin-left': 'auto',
            'margin-top': '0.2em',
            'filter': 'grayscale(80%)',
            'cursor': 'pointer'
        });
        let uploadButton = $('<span>').attr('title', 'upload').html('&#x1f4e4;').appendTo(headDiv).css({
            'margin-left': '0.5em',
            'margin-top': '0.2em',
            'filter': 'grayscale(80%)',
            'cursor': 'pointer'
        });
        updateButton.bind('click', e=>{
            localStorage.setItem(this.cachePath + '-cachetime', 0);
            this.frameDiv.empty().text("loading catalog...");
            this._load();
            fetch('api/channels');  // update the channel list on the server (new scripts might need it)
        });
        uploadButton.bind('click', e=>{
            window.location = './slowfile.html';
        });
        
        let contentDiv = $('<div>').appendTo(this.frameDiv).css(this.contentDiv_css);
        if (catalog === null) {
            contentDiv.html('<div style="color:gray;padding-bottom:3em">Content loading error');
            return;
        }
        
        let table = $('<table>').addClass('sd-data-table').appendTo(contentDiv).css(this.table_css);
        let tr = $('<tr>').appendTo(table);
        $('<th>').text("Name").css({'width':'20%'}).appendTo(tr);
        $('<th>').text("Last Modified").css({'width':'6em'}).appendTo(tr);
        $('<th>').text("Description").appendTo(tr);
        $('<th>').text("Edit").css({'width':'1em'}).appendTo(tr);

        if (content_type == "slowplot") {
            catalog.unshift({
                name: 'Blank',
                href: './slowplot.html',
                title: 'Blank',
                description: 'blank plot page',
                file: null, error: null, mtime: null,
            });
            catalog.unshift({
                name: 'Blank2x2',
                href: './slowplot.html?grid=2x2',
                title: 'Blank 2x2',
                description: 'blank plot page, 2x2 Grid',
                file: null, error: null, mtime: null,
            });
        }
        
        for (const entry of catalog) {
            const open = $('<a>').text(entry.title).attr('href', entry.href);
            const edit = $('<a>').html('&#x1f4dd;').attr({
                href: `slowedit.html?filename=${entry.file}`,
                target: '_blank',
            }).css({
                'margin-left': '0.2em',
                'filter': 'grayscale(50%)',
                'text-decoration': 'none',
            });
            const download = $('<a>').html('&#x1f4e5;').attr({
                href: `api/config/file/${entry.file}`,
                download: entry.file,
            }).css({
                'margin-left': '0.5em',
                'filter': 'grayscale(50%)',
                'text-decoration': 'none',
            });
            let tr = $('<tr>').appendTo(table);
            let td =$('<td>');
            if (entry.error !== null) {
                td.append('<span>').html("&#x26d4; ");
            }
            td.append(open).appendTo(tr);
            if (parseFloat(entry.mtime) > 0) {
                $('<td>').text((new JGDateTime(entry.mtime)).asString('%b %d, %Y')).appendTo(tr);
                $('<td>').text(entry.description).appendTo(tr);
                $('<td>').append(edit).append(download).appendTo(tr);
            }                    
            else {
                $('<td>').text('').appendTo(tr);
                $('<td>').text(entry.description).appendTo(tr);
                $('<td>').text('').appendTo(tr);
            }
        }
    }
}



export class ChannelListPanel extends Panel {
    static describe() {
        return { type: 'channellist', label: '' };
    }
    
    static buildConstructRows(table, on_done=config=>{}) {
        let tr = $('<tr>').html(`
            <td style="padding-top:1em"><button hidden style="font-size:x-large">Create</button></td><td></td>
        `).appendTo(table);

        let button = tr.find('button');
        button.bind('click', e=>{
            let config = {
                default_filter: '',
                case_sensitive: true,
            };
            on_done(config);
        });
    }

    
    constructor(div, style) {
        super(div, style);
        
        this.frameDiv = $('<div>').appendTo(div);        
        this.titleDiv = $('<div>').appendTo(this.frameDiv);
        this.searchDiv = $('<div>').appendTo(this.frameDiv);
        this.contentDiv = $('<div>').appendTo(this.frameDiv);
        
        this.table = $('<table>').appendTo(this.contentDiv);
        this.table.html('<tr><td></td></tr><tr><td>loading channel list...</td></tr>');

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
        this.searchDiv.css({
            'margin-bottom': '0.5em',
        });
        this.contentDiv.css({
            position: 'relative',
            width:'calc(100% - 10px)',
            height:'calc(100% - 10px - 4.5em)',
            margin: 0,
            padding:0,
            overflow:'auto',
        });
        this.table.addClass('sd-data-table').css({
            width: '100%',
            margin: 0,
            padding: 0,
            border: 'none',
        });
    }

    
    configure(config, callbacks={}, project_config=null) {
        super.configure(config, callbacks);
        
        if (project_config?.project?.name) {
            this.cachePath = `slowdash-${project_config.project.name}-ChanneList`;
        }
        else {
            this.cachePath = null;
        }
        
        this.titleDiv.css('display','flex');
        $('<span>').appendTo(this.titleDiv).text('Channel List');
        let updateButton = $('<span>').html('&#x1f504;').appendTo(this.titleDiv).css({
            'margin-left': 'auto',
            'margin-top': '0.2em',
            'filter':'grayscale(80%)',
            'cursor': 'pointer'
        });
        updateButton.bind('click', e=>{
            localStorage.setItem(this.cachePath + '-cachetime', 0);
            this.table.empty();
            this._load(config);
        });
        
        this.searchDiv.html(`
            <span style="white-space:nowrap">
            Channel Filter: <input style="width:50%"></input>
            <label><input type="checkbox">case sensitive</label>
            </span>
        `);

        let filterInput = this.searchDiv.find('input').at(0).val(config.default_filter);;
        let caseSensitiveInput = this.searchDiv.find('input').at(1).val(config.case_sensitive);
        filterInput.bind(/**/'keyup'/*/'change'/**/, e=>{
            this._applyFilter(this.table, filterInput.val(), caseSensitiveInput.val());
        });
        caseSensitiveInput.bind('change', e=>{
            this._applyFilter(this.table, filterInput.val(), caseSensitiveInput.val());
        });

        this._load(config);
    }


    openSettings(div) {
        let inputsDiv = $('<div>').appendTo(div);
        inputsDiv.html(`
            <table style="margin-top:1em">
              <tr><th>Default Filter </th><td><label><input></input></td></tr>
            </table>
        `);

        let k = 0;
        bindInput(this.config, 'default_filter', inputsDiv.find('input').at(k++), false);
    }


    _load(config) {
        if (this.cachePath) {
            const cacheTime = localStorage.getItem(this.cachePath + '-cachetime');
            if (parseFloat(cacheTime ?? 0) > $.time() - 3600) {
                let cachedDoc = localStorage.getItem(this.cachePath + '-doc');
                if (cachedDoc) {
                    this._render(config, JSON.parse(cachedDoc));
                    return;
                }
            }
        }

        fetch('api/channels')
            .then(response => {
                if (response.ok) return response.json();
            })
            .then(record => {
                if (record) {
                    this._render(config, record);
                    if (this.cachePath) {
                        localStorage.setItem(this.cachePath + '-cachetime', $.time());
                        localStorage.setItem(this.cachePath + '-doc', JSON.stringify(record));
                    }
                }
            });
    }

    
    _applyFilter(table, patterns, case_sensitive) {
        for (let tr of table.find('tr').enumerate()) {
            const channel = tr.data('channel');
            if (channel) {
                let isMatch = true;
                for (const pattern of patterns.split(/ +/)) {
                    const pos = (case_sensitive
                        ? channel.indexOf(pattern)
                        : channel.toLowerCase().indexOf(pattern.toLowerCase())
                    );
                    if (pos < 0) {
                        isMatch = false;
                        break;
                    }
                }
                tr.css('display', isMatch ? 'table-row' : 'none');
            }
        }
    }

    
    _render(config, record) {
        this.table.html('<tr><th>Channel Name</th><th>Data Type</th><th>Description</th></tr>');
        let tr = this.table.find('tr');
        const bg = window.getComputedStyle(tr.get()).getPropertyValue('background-color');
        tr.find('th').css({position: 'sticky', top:0, left:0, background: bg});
        
        for (let entry of record) {
            if (! entry.name) {
                continue;
            }
            let tr = $('<tr>').data('channel', entry.name).appendTo(this.table);
            if ((entry.type || 'timeseries') == 'timeseries') {
                let href = './slowplot.html?channel=' + entry.name;
                href += '&length=3600&reload=60&grid=2x1';
                let a = $('<a>').attr('href', href).text(entry.name).attr('target', '_blank');
                $('<td>').append(a).appendTo(tr);
            }
            else if (['histogram', 'ts-histogram', 'histogram2d', 'graph', 'table', 'tree', 'blob'].includes(entry.type)) {
                let href = './slowplot.html?channel=' + entry.name + '/' + entry.type;
                href += '&length=3600&reload=60&grid=1x1';
                let a = $('<a>').attr('href', href).text(entry.name).attr('target', '_blank');
                $('<td>').append(a).appendTo(tr);
            }
            else {
                $('<td>').text(entry.name).appendTo(tr);
            }
            $('<td>').text(entry.type ?? 'timeseries').appendTo(tr);
            $('<td>').text(entry.label ?? '').appendTo(tr);
        }
        
        this._applyFilter(this.table, config.default_filter);
    }
}
