// panel-table.mjs //
// Author: Sanshiro Enomoto <sanshiro@uw.edu> //
// Created on 18 June 2022 //


export { TablePanel as Panel1, TreePanel as Panel2, BlobPanel as Panel3 };


import { JG as $, JGDateTime } from './jagaimo/jagaimo.mjs';
import { Panel, bindInput } from './panel.mjs';



class TablePanel extends Panel {
    static describe() {
        return { type: 'table', label: 'Table (Data-Frame, Summary, Logs)' };
    }
    
    static buildConstructRows(table, on_done=config=>{}) {
        let tr1 = $('<tr>').html(`
            <td>Channel</td><td><input list="sd-table-datalist"></td>
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
                type: 'table',
                channel: table.find('input').val(),
                reversed: false,
            };
            on_done(config);
        });
    }

    
    constructor(div, style) {
        super(div, style);
        
        this.titleDiv = $('<div>').appendTo(div);
        this.contentDiv = $('<div>').appendTo(div);        
        this.table = $('<table>').appendTo(this.contentDiv);

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
            width:'calc(100% - 12px)',
            height:'calc(100% - 20px - 2em)',
            'margin-top': '10px',
            'margin-left': '10px',
            padding:0,
            overflow:'auto',
        });
        this.table.addClass('sd-data-table').css({
            width:'100%',
            margin: 0,
            'margin-bottom': '5em',
            padding: 0,
            border: 'none',
        });
    }

    
    async configure(config, options, callbacks) {
        super.configure(config, options, callbacks);
        this.titleDiv.text(this.config.title);
    }

    
    openSettings(div) {
        let inputsDiv = $('<div>').appendTo(div);
        inputsDiv.html(`
            <table style="margin-top:1em">
              <tr><th>channel</th><td><input list="sd-table-datalist"></td></tr>
              <tr><th>Title</th><td><input placeholder="empty"></td></tr>
            </table>
        `);

        let k = 0;
        bindInput(this.config, 'channel', inputsDiv.find('input').at(k++).css('width', '20em'));
        bindInput(this.config, 'title', inputsDiv.find('input').at(k++).css('width', '20em'));
    }

    
    fillInputChannels(inputChannels) {
        if (this.config.channel) {
            inputChannels.push(this.config.channel);
        }
    }
    

    drawRange(dataPacket, displayTimeRange) {
        let data = dataPacket.data[this.config.channel]?.x;
        if (! data) {
            if (! dataPacket.isTransitional) {
                this.table.empty();
                this.table.html('<tr><td>No Table Data</td></tr>');
            }
            return;
        }
        
        this.table.empty();
        if (Array.isArray(data)) {
            if (data.length < 1) {
                this.table.html('<tr><td>Empty Table</td></tr>');		
                return;
            }
            data = data[data.length-1];
        }
        if (typeof(data) == "string") {
            try {
                data = JSON.parse(data);
            }
            catch(error) {
                this.table.html('<tr><td>Table Data Error: ' + error.message + '</td></tr>');		
                return;
            }
        }
        if (! data.table) {
            this.table.html('<tr><td>No Table Content</td></tr>');		
            return;
        }
        const table = data;

        if (table.columns) {
            let tr = $('<tr>').appendTo(this.table);
            const bg = window.getComputedStyle(tr.get()).getPropertyValue('background-color');
            for (let col of table.columns) {
                let th = $('<th>').text(col).appendTo(tr);
                th.css({position: 'sticky', top:0, left:0, background: bg});
            }
        }

        const n = table.table.length;
        for (let k = 0; k < n; k++) {
            let tr = $('<tr>').appendTo(this.table);
            for (let col of table.table[(this.config.reversed ?? false) ? n-k-1 : k]) {
                $('<td>').text(col??'').appendTo(tr);
            }
        }
    }
};



class TreePanel extends Panel {
    static describe() {
        return { type: 'tree', label: 'Tree (JSON/YAML, Key-Value pairs, ...)' };
    }
    
    static buildConstructRows(table, on_done=config=>{}) {
        let tr1 = $('<tr>').html(`
            <td>Channel</td><td><input list="sd-tree-datalist"></td>
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
                type: 'tree',
                channel: table.find('input').val(),
            };
            on_done(config);
        });
    }

    
    constructor(div, style) {
        super(div, style);

        this.titleDiv = $('<div>').appendTo(div);
        this.contentDiv = $('<div>').appendTo(div);        

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
            width:'calc(100% - 12px)',
            height:'calc(100% - 20px - 2em)',
            'margin-top': '10px',
            'margin-left': '10px',
            'margin-bottom': '5em',
            padding:0,
            overflow:'auto',
        });
    }

    
    configure(config, options, callbacks) {
        super.configure(config, options, callbacks);
        this.titleDiv.text(this.config.title);
    }

    
    openSettings(div) {
        let inputsDiv = $('<div>').appendTo(div);
        inputsDiv.html(`
            <table style="margin-top:1em">
              <tr><th>channel</th><td><input list="sd-tree-datalist"></td></tr>
              <tr><th>Title</th><td><input placeholder="empty"></td></tr>
            </table>
        `);

        let k = 0;
        bindInput(this.config, 'channel', inputsDiv.find('input').at(k++).css('width', '20em'));
        bindInput(this.config, 'title', inputsDiv.find('input').at(k++).css('width', '20em'));
    }

    
    fillInputChannels(inputChannels) {
        if (this.config.channel) {
            inputChannels.push(this.config.channel);
        }
    }
    

    drawRange(dataPacket, displayTimeRange) {
        let data = dataPacket.data[this.config.channel]?.x;
        if (! data) {
            if (! dataPacket.isTransitional) {
                this.contentDiv.empty();
                this.contentDiv.html('No Tree Data');
            }
            return;
        }
        
        this.contentDiv.empty();
        if (Array.isArray(data)) {
            if (data.length < 1) {
                this.contentDiv.html('Empty Tree Data');
                return;
            }
            data = data[data.length-1];
        }
        if (typeof(data) == "string") {
            try {
                data = JSON.parse(data);
            }
            catch(error) {
                this.contentDiv.html('Tree Data Error: ' + error.message);
                return;
            }
        }
        if (! data.tree) {
            this.contentDiv.html('No Tree Content');
            return;
        }
        const tree = data.tree;

        function scan_depth(node, base=0) {
            if (! $.isDict(node)) {
                return [base];
            }
            let depth_list = [];
            for (let [key, child] of Object.entries(node)) {
                depth_list = depth_list.concat(scan_depth(child, base+1));
            }
            return depth_list;
        }
        const depth_list = scan_depth(tree);
        const max_depth = depth_list.reduce((a,b)=>Math.max(a,b), 0);
        const min_depth = depth_list.reduce((a,b)=>Math.min(a,b), max_depth);
        
        if (max_depth == 1) {
            // simple list of key-value pairs
            let table = $('<table>').addClass('sd-data-table').appendTo(this.contentDiv);
            let tr = $('<tr>').appendTo(table);
            for (let [key, value] of Object.entries(tree)) {
                let tr = $('<tr>').appendTo(table);
                tr.append($('<th>').text(key).css('text-align', 'left'));
                tr.append($('<td>').text(value??''));
            }
        }
        else if ((min_depth == 2) && (max_depth == 2)) {
            // multiple lists of key-value pairs => sections
            let table = $('<table>').addClass('sd-data-table').appendTo(this.contentDiv);
            let tr = $('<tr>').appendTo(table);
            for (let [section, subtree] of Object.entries(tree)) {
                let tr = $('<tr>').addClass('sd-data-tree-header').appendTo(table);
                tr.append($('<th>').attr('colspan', 2).css('text-align', 'center').text(section));
                for (let [key, value] of Object.entries(subtree)) {
                    let tr = $('<tr>').appendTo(table);
                    tr.append($('<th>').text(key).css('text-align', 'left'));
                    tr.append($('<td>').text(value??''));
                }
            }
        }
        else {
            // general tree
            let table = $('<table>').addClass('sd-data-table').appendTo(this.contentDiv);
            let tr = $('<tr>').appendTo(table);
            for (let [key, value] of Object.entries(tree)) {
                let tr = $('<tr>').appendTo(table);
                tr.append($('<th>').text(key));
                tr.append($('<td>').text(JSON.stringify(value)));
            }
        }
    }
};



class BlobPanel extends Panel {
    static describe() {
        return { type: 'blob', label: 'Blob (image, doc, data, ...)' };
    }
    
    static buildConstructRows(table, on_done=config=>{}) {
        let tr1 = $('<tr>').html(`
            <td>Channel</td><td><input list="sd-blob-datalist"></td>
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
                type: 'blob',
                channel: table.find('input').val(),
            };
            on_done(config);
        });
    }

    
    constructor(div, style) {
        super(div, style);
        
        this.titleDiv = $('<div>').appendTo(div);
        this.contentDiv = $('<div>').appendTo(div);        

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
            width:'calc(100% - 12px)',
            height:'calc(100% - 20px - 2em)',
            'margin-top': '10px',
            'margin-left': '10px',
            padding:0,
            overflow:'auto',
        });
    }

    
    configure(config, options, callbacks) {
        super.configure(config, options, callbacks);
        this.titleDiv.text(this.config.title);
    }

    
    openSettings(div) {
        let inputsDiv = $('<div>').appendTo(div);
        inputsDiv.html(`
            <table style="margin-top:1em">
              <tr><th>channel</th><td><input list="sd-blob-datalist"></td></tr>
              <tr><th>Title</th><td><input placeholder="empty"></td></tr>
            </table>
        `);

        let k = 0;
        bindInput(this.config, 'channel', inputsDiv.find('input').at(k++).css('width', '20em'));
        bindInput(this.config, 'title', inputsDiv.find('input').at(k++).css('width', '20em'));
    }

    
    fillInputChannels(inputChannels) {
        if (this.config.channel) {
            inputChannels.push(this.config.channel);
        }
    }
    

    drawRange(dataPacket, displayTimeRange) {
        let data = dataPacket.data[this.config.channel];
        if (! data) {
            if (! dataPacket.isTransitional) {
                this.contentDiv.empty();
                this.contentDiv.html('No Blob Data');
            }
            return;
        }

        this.contentDiv.empty();
        
        let t = null, x = null;
        if (Array.isArray(data.x)) {
            if (data.x.length < 1) {
                this.contentDiv.html('Empty Blob Data');
                return;
            }
            t = data.start + data.t[data.t.length-1];
            x = data.x[data.x.length-1];
        }
        else {
            t = data.start + data.t;
            x = data.x;
        }

        this.titleDiv.text(new JGDateTime(t).asString(this.config.title));
        if (! x?.mime || ! x?.id) {
            this.contentDiv.text(JSON.stringify(x));
            return;
        }

        const url = './api/blob/' + x.id;
        if (x.mime.split('/')[0].toLowerCase() == 'image') {
            let a = $('<a>').appendTo(this.contentDiv);
            a.attr({'href': url, 'target': '_blank'});
            let img = $('<img>').appendTo(a);
            img.attr({'src': url, 'height': '99%'});
        }
        else if (true) {
            $('<iframe>').appendTo(this.contentDiv).css({
                position: 'relative',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                border: 'none',
            }).attr('src', url);
        }
        else {
            let a = $('<a>').appendTo(this.contentDiv);
            a.attr({'href': url, 'target': '_blank'});
            a.append($('<span>').text(url));
        }
    }
};
