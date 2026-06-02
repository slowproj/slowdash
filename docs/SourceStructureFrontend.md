---
title: Source Structure - JavaScript Frontend
---

This document describes the current JavaScript and HTML structure under `app/site` as of the latest `develop` branch checked on 2026-06-01. It covers the built-in SlowDash site modules, the `jagaimo` and `autocruise` submodules, and the browser-to-server communication flows.

# High-Level Structure

The `app/site` frontend is a browser-side application built from static HTML entry pages and ES modules under `app/site/slowjs`.

```text
HTML entry pages
    |
    v
slowjs core modules
    - platform/config loading
    - dashboard orchestration
    - scheduler/controller
    - layout and panel management
    |
    v
panel modules
    - plots
    - canvas views
    - tables/trees/blobs
    - HTML/href panels
    - catalogs/download/tools/task manager
    |
    v
submodules and external browser libraries
    - jagaimo DOM/widget/plot helpers
    - autocruise rotating dashboard viewer
    - ace-builds editor bundle
```

The main dashboard path is:

```text
slowdash.html or slowplot.html
    -> slowjs/slowdash.mjs
    -> Platform
    -> SlowDash
    -> Layout
    -> Controller
    -> Scheduler
    -> Panel modules
```

# Important Files

### HTML entry pages

`app/site` contains several page-level entry points:

- `slowdash.html`: main dashboard viewer/editor entry point.
- `slowplot.html`: plot-focused entry point.
- `slowhome.html`: home/content list page.
- `slowdown.html`: layout/dashboard display page.
- `slowedit.html`: config editor using Ace.
- `slowfile.html`: file-oriented page.
- `slowplan.html`: planning page.
- `slowcruise.html`: autocruise entry point.
- `welcome.html`: welcome page.

Most pages load `slowjs/slowdash.css` and use `<script type="module">` to import ES modules from `slowjs`.

`slowcruise.html` is different: it loads `slowjs/autocruise/autocruise.js` as a classic script.

### Core `slowjs` modules

- `slowdash.mjs`: top-level dashboard coordinator.
- `platform.mjs`: project/page config loading, theme loading, data list setup, upload/save dialogs.
- `control.mjs`: `DataRequest`, `Controller`, `Scheduler`, update loop, API fetching, websocket streaming.
- `layout.mjs`: panel grid layout, panel creation, panel configuration, redraw.
- `frame.mjs`: page frame widgets, time range controls, grid controls.
- `panel.mjs`: base `Panel` class and common panel helpers.
- `panel-plugin-loader.mjs`: dynamic loader for built-in and optional panel modules.
- `transformer.mjs`: value transformation functions used by panels.

### Built-in panel modules

- `panel-plot.mjs`: time-series, histogram, graph, scatter, marker, bar, and time-axis plot panels.
- `panel-singles.mjs`: single-value displays and status-like square displays.
- `panel-canvas.mjs`: canvas-based process-display panels with shapes, buttons, images, microplots, and viewlets.
- `panel-map.mjs`: map panel support.
- `panel-table.mjs`: table, tree, and blob panels.
- `panel-html.mjs`: embedded HTML and hyperlink panels.
- `panel-catalog.mjs`: content catalog and channel list panels.
- `panel-download.mjs`: data download and SlowPy helper panels.
- `panel-misc.mjs`: welcome, tools, file manager, task manager, cruise planner, config editor panels.

### Styles and assets

- `slowjs/slowdash.css`: common frontend styling.
- `slowjs/slowdash-light.css`: light theme.
- `slowjs/slowdash-dark.css`: dark theme.
- `slowjs/Warning.png`: warning icon used by canvas/panel code.
- `favicon.png`: site favicon.

### Submodules and external dependencies

The repository declares three frontend submodules in `.gitmodules`:

```text
app/site/slow-extern/ace-builds
app/site/slowjs/jagaimo
app/site/slowjs/autocruise
```

This document focuses on `jagaimo` and `autocruise` because they are directly part of the SlowDash browser UI model. `ace-builds` is used by `slowedit.html` as the editor bundle.

# Entry Page Patterns

### Dashboard-style pages

Dashboard-style pages import `SlowDash`, `Frame`, and sometimes additional control widgets:

```text
slowdash.html
slowplot.html
slowfile.html
slowhome.html
slowplan.html
```

The typical pattern is:

1. Import `JG` from `jagaimo`.
2. Import `SlowDash` from `slowdash.mjs`.
3. Import `Frame` or time/grid controls.
4. Read URL options.
5. Create frame/header/body elements.
6. Create a `SlowDash` instance.
7. Configure it with a config file name, URL query, or inline config data.
8. Start the scheduler/controller loop.

### Config editor pages

`slowedit.html` and `slowedit2.html` are editor pages.

- `slowedit.html` uses local `slow-extern/ace-builds`.
- `slowedit2.html` loads Monaco from `https://unpkg.com/monaco-editor/...`.

Both pages call SlowDash config APIs such as:

```text
GET /api/config/file/{filename}
GET /api/config/contentlist
POST /api/config/file/{filename}
```

### Autocruise page

`slowcruise.html` loads the `autocruise` submodule:

```html
<script type="text/javascript" src="slowjs/autocruise/autocruise.js"></script>
<body autocruise-configbase="api/config/content/" autocruise-interval="10">
```

It uses `autocruise.js` to rotate through multiple dashboard/config pages.

# Main Dashboard Runtime Flow

The main dashboard object is `SlowDash` in `slowdash.mjs`.

```text
new SlowDash(div, config, options)
    |
    +-- creates Layout
    +-- creates Controller
    +-- creates Scheduler
```

### Configuration flow

```text
SlowDash.configure(config, options)
    |
    v
_buildConfig(...)
    |
    v
Platform.initialize(defaults, options, args)
    |
    +-- GET ./api/config
    +-- optional GET ./api/config/content/{config_file}
    +-- load theme CSS slowjs/slowdash-{theme}.css
    |
    v
merged config object
```

`config` can be:

- a URL query string;
- a config file name;
- a config object.

If a config contains `items` instead of `panels`, `SlowDash` treats it as a canvas-style config and wraps it into a single canvas panel.

### Start flow

```text
SlowDash.start()
    |
    v
configure if needed
    |
    v
Controller.configure(config)
    |
    v
Layout.configure(config)
    |
    v
PanelPluginLoader.load()
    |
    v
build and configure panel instances
    |
    v
Scheduler.start()
```

# Platform Module

`platform.mjs` centralizes project/page setup.

Main responsibilities:

- Parse URL options.
- Fetch project config from `./api/config`.
- Fetch page config from `./api/config/content/{config_file}`.
- Decode inline base64 config data from the URL.
- Load theme CSS dynamically.
- Build `<datalist>` elements for channel and content selectors.
- Upload files or configs to server endpoints.
- Provide `SaveConfigDialog`.

Important server calls:

```text
GET  ./api/config
GET  ./api/config/content/{filename}
GET  api/channels?fields=name
GET  ./api/config/contentlist
POST ./api/{filename}
```

The final configuration is built by deep-merging:

```text
defaults
project/page config
explicit args
```

# Controller, Scheduler, and Data Requests

### `DataRequest`

`DataRequest` builds a set of channel requests for `GET /api/data`.

It stores:

- default request options;
- default channel requests;
- custom channel requests.

It can combine multiple default channel requests into a single API call when the time range is not too long:

```text
api/data/ch1,ch2,ch3?length=...&to=...&resample=...
```

Custom requests are kept separate so panel-specific options do not interfere with default requests.

### `Controller`

`Controller` is the runtime bridge between layout/panels and server data.

Main responsibilities:

- Configure the `Layout`.
- Build a `DataRequest` by asking panels what data they need.
- Fetch data from `api/data/...`.
- Merge received data into `currentData`.
- Ask the `Layout` to draw panels.
- Emit messages to `/api/emit/{topic}`.
- Maintain websocket streaming for `current_data`.

Data update flow:

```text
Scheduler.update()
    |
    v
Controller.update()
    |
    v
Layout.fillDataRequest(dataRequest)
    |
    v
DataRequest.queryList(existingData)
    |
    v
fetch('api/data/' + query)
    |
    v
merge JSON response into currentData
    |
    v
Layout.draw(currentData)
```

Emit flow:

```text
Panel or view callback
    |
    v
Controller.emit(topic, doc)
    |
    +-- if websocket is open and topic == current_data:
    |       socket.send(message)
    |
    +-- otherwise:
            POST ./api/emit/{topic}
```

### WebSocket streaming

`Controller` attempts to attach to:

```text
ws://.../ws/attach/current_data
wss://.../ws/attach/current_data
```

The URL is derived from the current page URL. When websocket setup fails, data streaming is disabled and the dashboard continues to use HTTP polling.

Incoming websocket messages are parsed as current data and pushed to the active view:

```text
WebSocket message
    |
    v
parse JSON
    |
    v
merge/update current data
    |
    v
view.draw(data)
```

### `Scheduler`

`Scheduler` controls periodic updates, pending update requests, reset timing, suspend behavior, and status/progress callbacks.

It is initialized by `SlowDash.configure()` with:

- update interval;
- reset delay;
- callback to `SlowDash._update()`;
- status/progress/beat-time callbacks.

# Layout and Panel Model

### `Layout`

`Layout` manages the visual panel grid.

Main responsibilities:

- Load panel classes through `PanelPluginLoader`.
- Normalize config structure.
- Compute grid and panel dimensions.
- Build panel `<div>` elements.
- Instantiate the appropriate panel class for each config entry.
- Configure each panel.
- Draw all panels with the current data packet.
- Provide add/delete/reconfigure interactions when editing is allowed.

Panel creation flow:

```text
Layout.configure(config)
    |
    v
PanelPluginLoader.load()
    |
    v
_buildPanels()
    |
    v
_createPanel(panelDiv, panelType)
    |
    v
_configurePanels()
```

### `Panel`

`panel.mjs` defines the base `Panel` class.

Panel responsibilities:

- Hold panel config/options/callbacks.
- Provide standard configure/draw hooks.
- Provide settings dialog behavior.
- Provide delete/reconfigure callbacks.
- Allow each panel to contribute to a `DataRequest`.

Important methods:

```text
configure(config, options, callbacks)
fillDataRequest(dataRequest)
draw(dataPacket, displayTimeRange)
```

Subclasses override these methods to implement specific display types.

### `PanelPluginLoader`

`panel-plugin-loader.mjs` dynamically imports panel modules and extracts exported classes that subclass `Panel`.

Core modules are loaded in a fixed order so the "add panel" UI has predictable ordering:

```text
panel-plot.mjs
panel-singles.mjs
panel-canvas.mjs
panel-map.mjs
panel-table.mjs
panel-html.mjs
panel-catalog.mjs
panel-download.mjs
panel-misc.mjs
```

Additional panel plugin files can be appended through `add_plugin(filepath)`.

# Built-In Panel Modules

### Plot panels

`panel-plot.mjs` exports:

- `TimeAxisPlotPanel`
- `PlotPanel`

It contains plot implementations for:

- time-series plots;
- histograms;
- 2D histograms;
- graphs;
- line/marker plots;
- bar charts;
- time-series scatter plots.

It uses `jagaimo/jagaplot.mjs` for plot widgets and axis scaling.

### Singles panels

`panel-singles.mjs` implements single-value and status display panels.

It uses:

- `Transformer` for value conversion;
- `JGPlotAxisScale` for visual scaling;
- tab widgets for configuration UI.

### Canvas panels

`panel-canvas.mjs` implements a canvas/process-view style dashboard.

It includes item classes for:

- images;
- text;
- shapes;
- boxes and circles;
- valves and solenoids;
- grids;
- buttons;
- plots and microplots;
- viewlets.

Canvas items can read data, draw SVG/HTML elements, and emit control messages through callbacks.

### Map panels

`panel-map.mjs` loads map configuration from:

```text
GET ./api/config/file/map-{name}.json
```

It uses map geometry and color scales to draw channel-based map displays.

### Table, tree, and blob panels

`panel-table.mjs` exports three panel classes under aliases:

```text
TablePanel as Panel1
TreePanel  as Panel2
BlobPanel  as Panel3
```

`BlobPanel` can fetch blob content through:

```text
GET ./api/blob/{channel}?id={id}
```

### HTML and href panels

`panel-html.mjs` exports:

```text
HtmlPanel as Panel1
HrefPanel as Panel2
```

It can:

- load HTML content from project config content;
- load system or external content;
- transform values for display;
- send control messages to `./api/control`.

### Catalog and channel-list panels

`panel-catalog.mjs` provides:

- `CatalogPanel`
- `ChannelListPanel`

It uses:

```text
GET ./api/config/contentlist
GET ./api/config/content/{filename}
```

to list and open configured SlowDash content.

### Download and SlowPy panels

`panel-download.mjs` includes:

- `DownloadPanel`
- `SlowpyPanel`

It can list channels, build export/download requests, and send server requests for downloadable data products.

### Miscellaneous panels

`panel-misc.mjs` exports:

- `WelcomePanel`
- `ToolsPanel`
- `FileManagerPanel`
- `TaskManagerPanel`
- `CruisePlannerPanel`
- `ConfigEditorPanel`

These panels use APIs such as:

```text
GET  ./api/config/filelist
GET  ./api/config/file/{filename}
POST ./api/config/file/{filename}
GET  api/control/task?since={revision}
POST ./api/control/task/{taskname}
GET  api/console?since={revision}
POST ./api/console/
```

# Transformer Module

`transformer.mjs` provides a composable value transformation system.

It defines internal functor classes for operations such as:

- scalar conversion;
- offset;
- scale;
- formatting;
- matching;
- replacement;
- equality comparison;
- greater-than comparison;
- inversion;
- default values;
- "last" extraction;
- object field lookup.

`Transformer` is used by display panels to convert raw channel values into text, colors, thresholds, labels, and other presentation values.

# Frame Module

`frame.mjs` provides common page-level UI controls.

Exports include:

- `Frame`
- `TimePullDown`
- `TimeRangePullDown`
- `GridPullDown`

These controls are used by dashboard pages to manage:

- page header and status area;
- time selection;
- time-range selection;
- grid selection;
- layout frame behavior.

# Jagaimo Submodule

`app/site/slowjs/jagaimo` is a submodule pointing to:

```text
https://github.com/SanshiroEnomoto/jagaimo.git
```

SlowDash imports it as a local frontend library.

### `jagaimo.mjs`

`jagaimo.mjs` provides the `JG` helper and `JGElement` wrapper.

Its role is similar to a small DOM utility library:

- select elements;
- create elements;
- wrap DOM objects;
- append/prepend/remove elements;
- search descendants;
- get/set HTML, text, values, attributes, styles, data;
- bind events;
- provide date/time helpers such as `JGDateTime`.

SlowDash imports it as:

```javascript
import { JG as $, JGDateTime } from './jagaimo/jagaimo.mjs';
```

The `$` alias is used throughout `slowjs` for DOM creation and manipulation.

### `jagawidgets.mjs`

`jagawidgets.mjs` provides reusable UI widgets.

Common imports include:

- `JGTabWidget`
- `JGDialogWidget`
- `JGInvisibleWidget`
- `JGPopupWidget`
- `JGDraggable`
- `JGIndicatorWidget`
- `JGFileIconWidget`
- `JGHiddenWidget`

These widgets are used for panel settings dialogs, tabbed configuration UIs, popups, indicators, draggable canvas elements, and file/content controls.

### `jagaplot.mjs`

`jagaplot.mjs` provides plotting helpers.

SlowDash uses:

- `JGPlotWidget`
- `JGPlot`
- `JGPlotAxisScale`
- `JGPlotColorBarScale`

These are used by plot panels, canvas microplots, and map/color-scale panels.

### Role in SlowDash

Jagaimo is not an application entry point. It is the browser utility layer used by SlowDash modules.

```text
slowjs modules
    |
    +-- DOM manipulation via JG/$
    +-- dialogs/widgets via jagawidgets
    +-- plotting primitives via jagaplot
```

# Autocruise Submodule

`app/site/slowjs/autocruise` is a submodule pointing to:

```text
https://github.com/SanshiroEnomoto/autocruise.git
```

SlowDash uses it through `slowcruise.html`.

### Purpose

`autocruise.js` is a single-file JavaScript library that rotates through a list of pages, usually dashboard pages.

It can load page lists from:

- `<a>` links in the HTML body;
- a JSON config file specified by URL parameter;
- body attributes with prefix `autocruise-`;
- URL parameters.

SlowDash configures it with:

```html
<body autocruise-configbase="api/config/content/" autocruise-interval="10">
```

This lets users open a cruise page such as:

```text
slowcruise.html?config=slowcruise-example.json
```

and have `autocruise.js` fetch:

```text
api/config/content/slowcruise-example.json
```

### Runtime model

Autocruise replaces the page body with its own UI:

- a header/status bar;
- pause/reload/popout controls;
- one iframe per configured page;
- cycle or tile view mode;
- timed switching based on `interval`.

Flow:

```text
slowcruise.html
    |
    v
autocruise.js
    |
    +-- read body attributes
    +-- read URL parameters
    +-- optionally fetch config JSON
    +-- build iframe pages
    +-- cycle through pages
```

Autocruise is intentionally independent of the main `slowjs/slowdash.mjs` dashboard runtime. It treats dashboards as pages loaded in iframes.

# Browser-to-Server API Flow

The frontend communicates with the SlowDash server mostly through relative URLs.

### Configuration

```text
GET ./api/config
GET ./api/config/content/{filename}
GET ./api/config/contentlist
GET ./api/config/file/{filename}
GET ./api/config/filelist
POST ./api/config/file/{filename}
```

### Data

```text
GET api/channels?fields=name
GET api/data/{channels}?length=...&to=...&resample=...
GET ./api/blob/{channel}?id={id}
```

### Control and task UI

```text
POST ./api/control
GET  api/control/task?since={revision}
POST ./api/control/task/{taskname}
```

### Console

```text
GET  api/console?since={revision}
POST ./api/console/
```

### Current-data streaming and emit

```text
WebSocket /ws/attach/current_data
POST      ./api/emit/{topic}
```

The dashboard prefers websocket streaming when available, but falls back to HTTP data polling.

# Data Flow into Panels

The panel data flow is intentionally pull-based for historical data and optionally push-assisted for current data.

```text
Panel.fillDataRequest(dataRequest)
    |
    v
Controller builds channel queries
    |
    v
GET api/data/...
    |
    v
Controller.currentData
    |
    v
Layout.draw(currentData)
    |
    v
Panel.draw(currentData)
```

For current-data streaming:

```text
server emits current_data
    |
    v
WebSocket /ws/attach/current_data
    |
    v
Controller receives message
    |
    v
currentData update
    |
    v
Layout.draw(...)
```

Panels are responsible for interpreting their configured channels and data types.

# Configuration Flow into Panels

The page config usually comes from `/api/config/content/{filename}` and has a structure containing:

```text
meta
control
style
panels
```

Flow:

```text
Platform.fetchConfig()
    |
    v
SlowDash.configure()
    |
    v
Layout.configure()
    |
    v
one panel config per panel instance
```

Each panel receives:

- its own config entry;
- inherited layout/style information through options;
- callbacks for reconfigure, force update, suspend, popout, emit, and display range changes.

# Extension Points

### Adding a new HTML entry page

A new page can import existing modules:

```javascript
import { JG as $ } from './slowjs/jagaimo/jagaimo.mjs';
import { SlowDash } from './slowjs/slowdash.mjs';
import { Frame } from './slowjs/frame.mjs';
```

Then it can create a `SlowDash` instance and call `configure()` / `start()`.

### Adding a new panel type

Create a module that exports a class extending `Panel`.

The class should implement the panel contract:

```text
configure(config, options, callbacks)
fillDataRequest(dataRequest)
draw(dataPacket, displayTimeRange)
```

To make the core loader discover it, add the file to `PanelPluginLoader.core_files` or register it through `add_plugin(filepath)`.

### Adding a new value transform

Add a functor class in `transformer.mjs` and make `Transformer` recognize its config syntax.

### Adding a new theme

Add a CSS file named:

```text
slowjs/slowdash-{theme}.css
```

Then set `style.theme` in project or page config.

# Summary of Main Flows

### Page load

```text
HTML page
  -> imports slowjs modules
  -> Platform loads project/page config
  -> SlowDash builds Layout/Controller/Scheduler
  -> Layout loads panel modules
  -> Scheduler starts updates
```

### Data update

```text
Scheduler
  -> Controller.update()
  -> panels fill DataRequest
  -> fetch api/data
  -> merge currentData
  -> panels draw
```

### User interaction

```text
panel UI
  -> callback to Layout/Controller
  -> reconfigure, force update, popout, emit, or control API
```

### Streaming

```text
Controller
  -> WebSocket /ws/attach/current_data
  -> receive current_data
  -> redraw panels
```

### Autocruise

```text
slowcruise.html
  -> autocruise.js
  -> load page list/config
  -> build iframes
  -> cycle or tile dashboard pages
```

# Practical Development Notes

- `slowdash.mjs` is the best starting point for understanding normal dashboard startup.
- `control.mjs` is the best starting point for API polling, websocket streaming, and scheduler behavior.
- `layout.mjs` and `panel.mjs` define the panel lifecycle.
- `panel-plugin-loader.mjs` defines which panel modules are built into the normal dashboard.
- `platform.mjs` owns project/page config loading and theme selection.
- `jagaimo` provides the local DOM/widget/plot layer; most `slowjs` modules depend on it.
- `autocruise` is a separate page-cycling runtime, not part of the main `SlowDash` class flow.
- Relative API paths are intentional; the same static files can work under different deployment base paths.
