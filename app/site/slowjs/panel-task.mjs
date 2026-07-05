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
        this._task_catalog = null;
    }


    draw(data, displayTimeRange=null) {
        this._load_tasklist();
    }

    
    async _load_tasklist() {
        if (this._task_catalog == null) {
            this._task_catalog = {};
            try {
                const response = await fetch('api/control/task?since=0');
                const record = await response.json();
                for (const params of record.tasks) {
                    this._task_catalog[params.name] = {
                        file_name: 'slowtask-' + params.name + '.py',
                    }
                }
            }
            catch (e) {
                console.log("Error on fetching taskspec: ", e);
            }
        }

        let task_list = []; // note that there can exist multiple task instances of a task file
        
        let running_tasks = new Set();
        try {
            const response = await fetch('api/task/specs');
            const record = await response.json();
            const now = $.time();
            for (const task_spec of record) {
                const catalog = this._task_catalog[task_spec.name];
                const running = (task_spec.heartbeat_expire >= now - 1);
                task_list.push({
                    name: task_spec.name,
                    mesh_id: task_spec.mesh_id,
                    file_name: catalog ? catalog.file_name : null,
                    status: running ? 'running' : 'ghost',
                });
                running_tasks.add(task_spec.name);
            }
        }
        catch (e) {
            console.log("Error on fetching taskspec: ", e);
        }

        for (const [task_name, task_params] of Object.entries(this._task_catalog)) {
            if (running_tasks.has(task_name)) {
                continue;
            }
            task_list.push({
                name: task_name,
                mesh_id: null,
                file_name: task_params.file_name,
                status: 'inactive',
            });
        }
        
        this._render_task_table(task_list);
    }

    
    _render_task_table(task_list) {
        this.table.empty();
        let tr = $('<tr>');
        $('<th>').text("Name").appendTo(tr);
        $('<th>').text("Status").appendTo(tr);
        $('<th>').text("Control").appendTo(tr);
        $('<th>').text("Mesh ID").appendTo(tr);
        $('<th>').text("File").appendTo(tr);
        tr.appendTo(this.table);
        const bg = window.getComputedStyle(tr.get()).getPropertyValue('background-color');
        tr.find('th').css({position: 'sticky', top:0, left:0, background: bg});

        for (const task of task_list) {
            let buttons = $('<span>');
            let startButton = $('<button>').text('Start').appendTo(buttons).css('margin-right', '0.5em');
            let stopButton = $('<button>').text('Stop').appendTo(buttons).css('margin-right', '0.5em');
            let killButton = $('<button>').text('Kill').appendTo(buttons).css('margin-right', '0.5em');
            let status_label = task.status;
            if (task.status == 'inactive') {
                stopButton.enabled(false);
                killButton.enabled(false);
                status_label = '&#x2615; inactive';                
            }
            else if (task.status == 'running') {
                startButton.enabled(false);
                status_label = '&#x1f3c3; running';
            }
            else if (task.status == 'ghost') {
                startButton.enabled(false);
                stopButton.enabled(false);
                status_label = '&#x1f47b; ghost';
            }
                
            let tr = $('<tr>');
            $('<td>').appendTo(tr).text(task.name);
            $('<td>').appendTo(tr).html(status_label);
            $('<td>').appendTo(tr).append(buttons);
            $('<td>').appendTo(tr).text(task.mesh_id ?? '-');
            $('<td>').appendTo(tr).text(task.file_name ?? '-');
            tr.appendTo(this.table);
        }
    }
}
