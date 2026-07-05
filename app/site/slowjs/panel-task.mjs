// panel-task.mjs //
// Created by Sanshiro Enomoto on 4 July 2026

export { TaskPanel };


import { JG as $ } from './jagaimo/jagaimo.mjs';
import { JGIndicatorWidget } from './jagaimo/jagawidgets.mjs';
import { Panel } from './panel.mjs';


class TaskPanel extends Panel {
    static describe() {
        return { type: 'task', label: '' };
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
        
        this.table = $('<table>').appendTo(this.tableDiv);
        this.table.html('<tr><td></td></tr><tr><td>loading task list...</td></tr>');
        this.indicator = new JGIndicatorWidget($('<div>').appendTo(div));

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
        this.table.addClass('sd-data-table').css({
            width: '100%',
            margin: 0,
            padding: 0,
            border: 'none',
        });
        
        this.titleDiv.html('SlowTask Status');
    }

    
    configure(config, options={}, callbacks={}) {
        super.configure(config, options, callbacks);
        this.is_secure = options.is_secure;
    }


    draw(data, displayTimeRange=null) {
        this._load_tasklist();
    }

    
    async _load_tasklist() {
        try {
            // this is a long poll (if the SlowDash server is ASGI)
            let response = await fetch('api/task/specs');
            let record = await response.json();
            this._render_task_table(record);
        }
        catch (e) {
            console.log("Error on fetching taskspec: ", e);
        }
    }

    
    _render_task_table(record) {
        this.table.empty();
        let tr = $('<tr>');
        $('<th>').text("Name").appendTo(tr);
        $('<th>').text("Mesh ID").appendTo(tr);
        tr.appendTo(this.table);
        const bg = window.getComputedStyle(tr.get()).getPropertyValue('background-color');
        tr.find('th').css({position: 'sticky', top:0, left:0, background: bg});

        for (let spec of record) {
            let tr = $('<tr>');
            $('<td>').appendTo(tr).html(spec.name);
            $('<td>').appendTo(tr).html(spec.mesh_id);
            tr.appendTo(this.table);
        }
    }
}
