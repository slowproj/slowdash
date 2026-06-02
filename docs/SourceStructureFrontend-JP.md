---
title: ソース構造 - JavaScript フロントエンド
---

この文書は，2026-06-01 に確認した最新 `develop` ブランチ時点の `app/site` 以下の JavaScript と HTML 構造を説明するものです．組み込みの SlowDash site module，`jagaimo` と `autocruise` の submodule，および browser と server の通信フローを対象にします．

# 全体構造

`app/site` の frontend は，static HTML entry page と `app/site/slowjs` 以下の ES module で構成された browser-side application です．

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

Main dashboard の経路は次のようになります．

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

# 主要ファイル

### HTML entry pages

`app/site` には複数の page-level entry point があります．

- `slowdash.html`: main dashboard viewer/editor entry point．
- `slowplot.html`: plot-focused entry point．
- `slowhome.html`: home/content list page．
- `slowdown.html`: layout/dashboard display page．
- `slowedit.html`: Ace を使う config editor．
- `slowfile.html`: file-oriented page．
- `slowplan.html`: planning page．
- `slowcruise.html`: autocruise entry point．
- `welcome.html`: welcome page．

ほとんどの page は `slowjs/slowdash.css` を読み込み，`<script type="module">` で `slowjs` から ES module を import します．

`slowcruise.html` だけは少し異なり，`slowjs/autocruise/autocruise.js` を classic script として読み込みます．

### Core `slowjs` modules

- `slowdash.mjs`: dashboard 全体の coordinator．
- `platform.mjs`: project/page config loading，theme loading，data list setup，upload/save dialog．
- `control.mjs`: `DataRequest`，`Controller`，`Scheduler`，update loop，API fetching，websocket streaming．
- `layout.mjs`: panel grid layout，panel creation，panel configuration，redraw．
- `frame.mjs`: page frame widget，time range control，grid control．
- `panel.mjs`: base `Panel` class と共通 panel helper．
- `panel-plugin-loader.mjs`: built-in および optional panel module の dynamic loader．
- `transformer.mjs`: panel で使う value transformation function．

### Built-in panel modules

- `panel-plot.mjs`: time-series，histogram，graph，scatter，marker，bar，time-axis plot panel．
- `panel-singles.mjs`: single-value display と status-like square display．
- `panel-canvas.mjs`: shape，button，image，microplot，viewlet などを含む canvas-based process-display panel．
- `panel-map.mjs`: map panel support．
- `panel-table.mjs`: table，tree，blob panel．
- `panel-html.mjs`: embedded HTML と hyperlink panel．
- `panel-catalog.mjs`: content catalog と channel list panel．
- `panel-download.mjs`: data download と SlowPy helper panel．
- `panel-misc.mjs`: welcome，tools，file manager，task manager，cruise planner，config editor panel．

### Styles and assets

- `slowjs/slowdash.css`: 共通 frontend style．
- `slowjs/slowdash-light.css`: light theme．
- `slowjs/slowdash-dark.css`: dark theme．
- `slowjs/Warning.png`: canvas/panel code で使う warning icon．
- `favicon.png`: site favicon．

### Submodules and external dependencies

Repository の `.gitmodules` では，frontend 用に次の 3 つの submodule が宣言されています．

```text
app/site/slow-extern/ace-builds
app/site/slowjs/jagaimo
app/site/slowjs/autocruise
```

この文書では，SlowDash browser UI model に直接関わる `jagaimo` と `autocruise` を中心に扱います．`ace-builds` は `slowedit.html` で editor bundle として使われます．

# Entry Page Patterns

### Dashboard-style pages

Dashboard-style page は `SlowDash`，`Frame`，必要に応じて追加の control widget を import します．

```text
slowdash.html
slowplot.html
slowfile.html
slowhome.html
slowplan.html
```

典型的な pattern は次のとおりです．

1. `jagaimo` から `JG` を import する．
2. `slowdash.mjs` から `SlowDash` を import する．
3. `Frame` または time/grid control を import する．
4. URL option を読む．
5. frame/header/body element を作る．
6. `SlowDash` instance を作る．
7. config file name，URL query，または inline config data で configure する．
8. scheduler/controller loop を start する．

### Config editor pages

`slowedit.html` と `slowedit2.html` は editor page です．

- `slowedit.html` は local の `slow-extern/ace-builds` を使います．
- `slowedit2.html` は `https://unpkg.com/monaco-editor/...` から Monaco を読み込みます．

どちらも次のような SlowDash config API を呼びます．

```text
GET /api/config/file/{filename}
GET /api/config/contentlist
POST /api/config/file/{filename}
```

### Autocruise page

`slowcruise.html` は `autocruise` submodule を読み込みます．

```html
<script type="text/javascript" src="slowjs/autocruise/autocruise.js"></script>
<body autocruise-configbase="api/config/content/" autocruise-interval="10">
```

これは `autocruise.js` を使って複数の dashboard/config page を巡回表示します．

# Main Dashboard Runtime Flow

Main dashboard object は `slowdash.mjs` の `SlowDash` です．

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

`config` には次の形式を使えます．

- URL query string．
- config file name．
- config object．

Config が `panels` ではなく `items` を持つ場合，`SlowDash` はそれを canvas-style config とみなし，単一の canvas panel に wrap します．

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

`platform.mjs` は project/page setup を集約します．

主な責務:

- URL option を parse する．
- `./api/config` から project config を fetch する．
- `./api/config/content/{config_file}` から page config を fetch する．
- URL 中の inline base64 config data を decode する．
- theme CSS を dynamic に読み込む．
- channel selector や content selector 用の `<datalist>` を作る．
- file や config を server endpoint に upload する．
- `SaveConfigDialog` を提供する．

主な server call:

```text
GET  ./api/config
GET  ./api/config/content/{filename}
GET  api/channels?fields=name
GET  ./api/config/contentlist
POST ./api/{filename}
```

最終 config は次を deep-merge して作られます．

```text
defaults
project/page config
explicit args
```

# Controller，Scheduler，Data Requests

### `DataRequest`

`DataRequest` は `GET /api/data` 用の channel request 群を作ります．

保持するもの:

- default request option．
- default channel request．
- custom channel request．

Time range が長すぎない場合，複数の default channel request を 1 つの API call にまとめられます．

```text
api/data/ch1,ch2,ch3?length=...&to=...&resample=...
```

Custom request は，panel-specific option が default request と干渉しないよう，個別 request のまま扱われます．

### `Controller`

`Controller` は layout/panel と server data の runtime bridge です．

主な責務:

- `Layout` を configure する．
- panel に必要 data を問い合わせて `DataRequest` を作る．
- `api/data/...` から data を fetch する．
- 受け取った data を `currentData` に merge する．
- `Layout` に panel 描画を依頼する．
- `/api/emit/{topic}` に message を emit する．
- `current_data` 用 websocket streaming を維持する．

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

`Controller` は次の websocket に attach しようとします．

```text
ws://.../ws/attach/current_data
wss://.../ws/attach/current_data
```

URL は現在の page URL から作られます．WebSocket setup に失敗した場合，data streaming は無効化され，dashboard は HTTP polling を継続します．

Incoming websocket message は current data として parse され，active view に渡されます．

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

`Scheduler` は periodic update，pending update request，reset timing，suspend behavior，status/progress callback を制御します．

`SlowDash.configure()` により次を渡して initialize されます．

- update interval．
- reset delay．
- `SlowDash._update()` への callback．
- status/progress/beat-time callback．

# Layout and Panel Model

### `Layout`

`Layout` は visual panel grid を管理します．

主な責務:

- `PanelPluginLoader` で panel class を読み込む．
- config structure を normalize する．
- grid と panel dimension を計算する．
- panel `<div>` element を作る．
- config entry ごとに適切な panel class を instantiate する．
- 各 panel を configure する．
- current data packet で全 panel を draw する．
- editing が許可されている場合，add/delete/reconfigure interaction を提供する．

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

`panel.mjs` は base `Panel` class を定義します．

Panel の責務:

- panel config/options/callbacks を保持する．
- standard configure/draw hook を提供する．
- settings dialog behavior を提供する．
- delete/reconfigure callback を提供する．
- 各 panel が `DataRequest` に必要 data を追加できるようにする．

重要 method:

```text
configure(config, options, callbacks)
fillDataRequest(dataRequest)
draw(dataPacket, displayTimeRange)
```

Subclass はこれらを override し，具体的な display type を実装します．

### `PanelPluginLoader`

`panel-plugin-loader.mjs` は panel module を dynamic import し，`Panel` を継承した exported class を抽出します．

Core module は「add panel」UI の表示順を安定させるため，固定順で読み込まれます．

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

追加 panel plugin file は `add_plugin(filepath)` で追加できます．

# Built-In Panel Modules

### Plot panels

`panel-plot.mjs` は次を export します．

- `TimeAxisPlotPanel`
- `PlotPanel`

内部には次の plot implementation があります．

- time-series plot．
- histogram．
- 2D histogram．
- graph．
- line/marker plot．
- bar chart．
- time-series scatter plot．

Plot widget と axis scaling には `jagaimo/jagaplot.mjs` を使います．

### Singles panels

`panel-singles.mjs` は single-value と status display panel を実装します．

使用するもの:

- value conversion 用の `Transformer`．
- visual scaling 用の `JGPlotAxisScale`．
- configuration UI 用の tab widget．

### Canvas panels

`panel-canvas.mjs` は canvas/process-view style dashboard を実装します．

含まれる item class:

- image．
- text．
- shape．
- box と circle．
- valve と solenoid．
- grid．
- button．
- plot と microplot．
- viewlet．

Canvas item は data を読み，SVG/HTML element を描画し，callback 経由で control message を emit できます．

### Map panels

`panel-map.mjs` は次の endpoint から map configuration を読み込みます．

```text
GET ./api/config/file/map-{name}.json
```

Map geometry と color scale を使い，channel-based map display を描画します．

### Table，tree，blob panels

`panel-table.mjs` は 3 つの panel class を alias 付きで export します．

```text
TablePanel as Panel1
TreePanel  as Panel2
BlobPanel  as Panel3
```

`BlobPanel` は次の API で blob content を fetch できます．

```text
GET ./api/blob/{channel}?id={id}
```

### HTML and href panels

`panel-html.mjs` は次を export します．

```text
HtmlPanel as Panel1
HrefPanel as Panel2
```

できること:

- project config content から HTML content を読み込む．
- system または external content を読み込む．
- display 用に value を transform する．
- `./api/control` に control message を送る．

### Catalog and channel-list panels

`panel-catalog.mjs` は次を提供します．

- `CatalogPanel`
- `ChannelListPanel`

設定済み SlowDash content を list/open するため，次を使います．

```text
GET ./api/config/contentlist
GET ./api/config/content/{filename}
```

### Download and SlowPy panels

`panel-download.mjs` は次を含みます．

- `DownloadPanel`
- `SlowpyPanel`

Channel を list し，export/download request を作り，downloadable data product 用の server request を送れます．

### Miscellaneous panels

`panel-misc.mjs` は次を export します．

- `WelcomePanel`
- `ToolsPanel`
- `FileManagerPanel`
- `TaskManagerPanel`
- `CruisePlannerPanel`
- `ConfigEditorPanel`

これらの panel は次の API を使います．

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

`transformer.mjs` は composable な value transformation system を提供します．

内部 functor class は次のような操作を扱います．

- scalar conversion．
- offset．
- scale．
- formatting．
- matching．
- replacement．
- equality comparison．
- greater-than comparison．
- inversion．
- default value．
- "last" extraction．
- object field lookup．

`Transformer` は display panel で，raw channel value を text，color，threshold，label，その他の presentation value に変換するために使われます．

# Frame Module

`frame.mjs` は page-level UI control を提供します．

Export:

- `Frame`
- `TimePullDown`
- `TimeRangePullDown`
- `GridPullDown`

これらは dashboard page で次を管理するために使われます．

- page header と status area．
- time selection．
- time-range selection．
- grid selection．
- layout frame behavior．

# Jagaimo Submodule

`app/site/slowjs/jagaimo` は次の repository を指す submodule です．

```text
https://github.com/SanshiroEnomoto/jagaimo.git
```

SlowDash はこれを local frontend library として import します．

### `jagaimo.mjs`

`jagaimo.mjs` は `JG` helper と `JGElement` wrapper を提供します．

これは小さな DOM utility library のような役割です．

- element を select する．
- element を create する．
- DOM object を wrap する．
- element を append/prepend/remove する．
- descendant を search する．
- HTML，text，value，attribute，style，data を get/set する．
- event を bind する．
- `JGDateTime` などの date/time helper を提供する．

SlowDash では次のように import されます．

```javascript
import { JG as $, JGDateTime } from './jagaimo/jagaimo.mjs';
```

`$` alias は `slowjs` 全体で DOM creation/manipulation に使われます．

### `jagawidgets.mjs`

`jagawidgets.mjs` は reusable UI widget を提供します．

よく使われる import:

- `JGTabWidget`
- `JGDialogWidget`
- `JGInvisibleWidget`
- `JGPopupWidget`
- `JGDraggable`
- `JGIndicatorWidget`
- `JGFileIconWidget`
- `JGHiddenWidget`

これらは panel settings dialog，tabbed configuration UI，popup，indicator，draggable canvas element，file/content control に使われます．

### `jagaplot.mjs`

`jagaplot.mjs` は plotting helper を提供します．

SlowDash が使うもの:

- `JGPlotWidget`
- `JGPlot`
- `JGPlotAxisScale`
- `JGPlotColorBarScale`

これらは plot panel，canvas microplot，map/color-scale panel で使われます．

### Role in SlowDash

Jagaimo は application entry point ではありません．SlowDash module が使う browser utility layer です．

```text
slowjs modules
    |
    +-- DOM manipulation via JG/$
    +-- dialogs/widgets via jagawidgets
    +-- plotting primitives via jagaplot
```

# Autocruise Submodule

`app/site/slowjs/autocruise` は次の repository を指す submodule です．

```text
https://github.com/SanshiroEnomoto/autocruise.git
```

SlowDash は `slowcruise.html` からこれを使います．

### Purpose

`autocruise.js` は，通常 dashboard page の list を順番に巡回表示する single-file JavaScript library です．

Page list は次から読み込めます．

- HTML body 内の `<a>` link．
- URL parameter で指定された JSON config file．
- `autocruise-` prefix を持つ body attribute．
- URL parameter．

SlowDash は次のように設定します．

```html
<body autocruise-configbase="api/config/content/" autocruise-interval="10">
```

これにより，たとえば次のような cruise page を開けます．

```text
slowcruise.html?config=slowcruise-example.json
```

その場合，`autocruise.js` は次を fetch します．

```text
api/config/content/slowcruise-example.json
```

### Runtime model

Autocruise は page body を自分の UI で置き換えます．

- header/status bar．
- pause/reload/popout control．
- configured page ごとの iframe．
- cycle または tile view mode．
- `interval` に基づく timed switching．

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

Autocruise は main の `slowjs/slowdash.mjs` dashboard runtime から独立しています．Dashboard を iframe 内の page として扱います．

# Browser-to-Server API Flow

Frontend は主に relative URL で SlowDash server と通信します．

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

Dashboard は可能なら websocket streaming を使いますが，HTTP data polling に fallback できます．

# Data Flow into Panels

Panel data flow は，historical data については pull-based，current data については optional push-assisted です．

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

Current-data streaming の場合:

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

Panel は，自身の configured channel と data type を解釈する責任を持ちます．

# Configuration Flow into Panels

Page config は通常 `/api/config/content/{filename}` から来て，次のような構造を持ちます．

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

各 panel は次を受け取ります．

- 自身の config entry．
- options 経由で継承される layout/style 情報．
- reconfigure，force update，suspend，popout，emit，display range change 用 callback．

# Extension Points

### Adding a new HTML entry page

新しい page は既存 module を import できます．

```javascript
import { JG as $ } from './slowjs/jagaimo/jagaimo.mjs';
import { SlowDash } from './slowjs/slowdash.mjs';
import { Frame } from './slowjs/frame.mjs';
```

その後，`SlowDash` instance を作り，`configure()` / `start()` を呼べます．

### Adding a new panel type

`Panel` を継承する class を export する module を作ります．

その class は次の panel contract を実装する必要があります．

```text
configure(config, options, callbacks)
fillDataRequest(dataRequest)
draw(dataPacket, displayTimeRange)
```

Core loader に見つけさせるには，file を `PanelPluginLoader.core_files` に追加するか，`add_plugin(filepath)` で登録します．

### Adding a new value transform

`transformer.mjs` に functor class を追加し，`Transformer` がその config syntax を認識するようにします．

### Adding a new theme

次の名前の CSS file を追加します．

```text
slowjs/slowdash-{theme}.css
```

その後，project または page config で `style.theme` を設定します．

# Main Flow Summary

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

- 通常の dashboard startup を理解する入口は `slowdash.mjs` が最適です．
- API polling，websocket streaming，scheduler behavior を理解する入口は `control.mjs` が最適です．
- Panel lifecycle は `layout.mjs` と `panel.mjs` が定義します．
- 通常 dashboard に組み込まれる panel module は `panel-plugin-loader.mjs` が定義します．
- Project/page config loading と theme selection は `platform.mjs` が担当します．
- `jagaimo` は local DOM/widget/plot layer を提供し，ほとんどの `slowjs` module が依存しています．
- `autocruise` は独立した page-cycling runtime であり，main の `SlowDash` class flow の一部ではありません．
- Relative API path は意図的に使われています．同じ static file が異なる deployment base path で動作できるようにするためです．
