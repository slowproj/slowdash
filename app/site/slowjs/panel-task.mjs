// panel-task.mjs //
// Created by Sanshiro Enomoto on 4 July 2026

export { TaskPanel };


import { JG as $, JGDateTime } from './jagaimo/jagaimo.mjs';
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
        this.remarkDiv = $('<div>').appendTo(this.contentDiv);
        this.tableDiv = $('<div>').appendTo(this.contentDiv);
        
        this.remarkDiv.css('margin-bottom','0.5em').html('Work in progress: <span style="color:red">Reload the page to update</span> for now').prependTo(this.tableDiv).hide();

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
        
        this.titleDiv.html('SlowTasks');
    }

    
    configure(config, options={}, callbacks={}) {
        super.configure(config, options, callbacks);

        this._short_form = config.short_form ?? false;
        this.is_secure = options.is_secure;
        this._task_catalog = null;


        if (this._short_form) {
            this.remarkDiv.show();
        }
    }


    draw(data, displayTimeRange=null) {
        this._load_tasklist();
    }

    
    async _load_tasklist() {
        if (this._task_catalog == null) {
            this._task_catalog = {};
            try {
                const response = await fetch('api/task/catalog');
                const doc = await response.json();
                for (const [name, params] of Object.entries(doc)) {
                    this._task_catalog[name] = {
                        file_path: params.file_path,
                        command: params.command,
                    }
                }
            }
            catch (e) {
                console.log("Error on fetching task catalog: ", e);
            }
        }

        let task_list = []; // note that there can exist multiple task instances of a task file
        
        let running_tasks = new Set();
        try {
            const response = await fetch('api/task/status');
            const doc = await response.json();
            const now = $.time();
            for (const task of doc) {
                const catalog = this._task_catalog[task.name];
                const running = (task.heartbeat_expire >= now - 1);
                const heartbeat = task.heartbeat_expire - task.spec.heartbeat_interval;
                task_list.push({
                    name: task.name,
                    status: running ? 'running' : 'ghost',
                    heartbeat: (new JGDateTime(heartbeat)).asString('%a, %H:%M:%S'),
                    file_path: catalog ? catalog.file_path : null,
                    command: catalog ? catalog.command : null,
                    proc_id: task.proc_id,
                    mesh_id: task.spec.mesh_id,
                });
                running_tasks.add(task.name);
            }
        }
        catch (e) {
            console.log("Error on fetching task status: ", e);
        }

        for (const [name, params] of Object.entries(this._task_catalog)) {
            if (! running_tasks.has(name)) {
                task_list.push({
                    name: name,
                    status: 'inactive',
                    heartbeat: null,
                    file_path: params.file_path,
                    command: params.command,
                    proc_id: null,
                    mesh_id: null,
                });
            }
        }

        // fix the order, not to be affected by the running status
        task_list.sort((a,b) => a.name.localeCompare(b.name));
        
        this._render_task_table(task_list);
    }

    
    async _send_control(taskname, action, event=null) {
        const url = `./api/task/control/${taskname}`;
        try {
            this.indicator.open("sending command...", "&#x23f3;", event?.clientX ?? null, event?.clientY ?? null);
            let response = await fetch(url, {
                method: 'POST',
                body: `{"action":"${action}"}`
            });
            if (! response.ok) {
                throw new Error(response.status + " " + response.statusText);
            }
            const reply = await response.json();
            if (reply.status != 'ok') {
                this.indicator.close("error: " + (reply.message ?? 'unknown error'), "&#x274c;", 5000);
            }
            else {
                this.indicator.close("ok", "&#x2705;", 1000);
            }
        }
        catch (e) {
            this.indicator.close("error: " + e.message, "&#x274c;", 5000);
        }
    }

    
    _render_task_table(task_list) {
        this.table.empty();
        let tr = $('<tr>');
        $('<th>').text("Name").appendTo(tr);
        $('<th>').text("Status").appendTo(tr);
        $('<th>').text("Heartbeat").appendTo(tr);
        $('<th>').text("Control").appendTo(tr);
        if (! this._short_form) {
            $('<th>').text("Command").appendTo(tr);
            $('<th>').text("Proc ID").appendTo(tr);
            $('<th>').text("Mesh ID").appendTo(tr);
        }
        tr.appendTo(this.table);
        const bg = window.getComputedStyle(tr.get()).getPropertyValue('background-color');
        tr.find('th').css({position: 'sticky', top:0, left:0, background: bg});

        for (const task of task_list) {
            let buttons = $('<span>');
            let startButton = $('<button>').text('Start').appendTo(buttons).css('margin-right', '0.5em');
            let stopButton = $('<button>').text('Stop').appendTo(buttons).css('margin-right', '0.5em');
            let killButton = $('<button>').text('Kill').appendTo(buttons).css('margin-right', '0.5em');
            let purgeButton = $('<button>').text('Purge').appendTo(buttons).css('margin-right', '0.5em');
            let status_label = task.status;
            if (task.status == 'inactive') {
                status_label = '&#x2615; inactive';                
            }
            else if (task.status == 'running') {
                status_label = '&#x1f3c3; running';
            }
            else if (task.status == 'ghost') {
                status_label = '&#x1f47b; ghost';
            }
            startButton.enabled(task.status == 'inactive');
            stopButton.enabled(task.status == 'running');
            killButton.enabled(task.proc_id != null && task.proc_id.length > 0);
            purgeButton.enabled(task.status == 'ghost');
                
            let tr = $('<tr>');
            $('<td>').appendTo(tr).text(task.name);
            $('<td>').appendTo(tr).html(status_label);
            $('<td>').appendTo(tr).text(task.heartbeat ?? '');
            $('<td>').appendTo(tr).append(buttons);
            if (! this._short_form) {
                $('<td>').appendTo(tr).text(task.command ?? '');
                $('<td>').appendTo(tr).text((task.proc_id ?? []).join(','));
                $('<td>').appendTo(tr).text(task.mesh_id ?? '');
            }
            tr.appendTo(this.table);

            tr.find('button').bind('click', e=>{
                tr.find('button').enabled(false);
                const action = $(e.target).text().toLowerCase();
                this._send_control(task.name, action, e);
            });
        }
    }
}
