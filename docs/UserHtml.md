---
title: User HTML
---

# Overview
Files placed under the project's `userhtml` directory are accessible through the SlowDash Web API at `/userhtml/{filename}`.
If an HTML file is placed, it can use the full functionality of HTML, such as applying user CSS, embedding JavaScript, and importing external JavaScript libraries. HTML files located immediately under the `userhtml` directory will be listed on the SlowDash catalog panel, alongside the SlowDash standard dashboards and plot layouts.

The SlowDash JavaScript library, SlowJS, can be accessed at `/userhtml/slowjs`, as if the `slowjs` directory exists under the User HTML directory, allowing the user HTML scripts to use the SlowDash functionality. The user HTML directory cannot contain a file named `slowjs`.

# URL Routing
When a user HTML page is served at `/userhtml/{filename}`, the browser treats `/userhtml/` as its base directory. Relative URLs in the page are resolved against this base, so `./api/data/channels` becomes `/userhtml/api/data/channels`, and `./slowjs/layout.mjs` becomes `/userhtml/slowjs/layout.mjs`. SlowDash intercepts these URL patterns and handles them as follows:

| URL pattern | Handled as |
|---|---|
| `/userhtml/{filename}` | File served from the project's `userhtml/` directory |
| `/userhtml/slowjs/{script}` | SlowJS script served from the SlowDash installation |
| `/userhtml/api/{endpoint}` | Redirected (HTTP 307) to `/api/{endpoint}` |
| `/userhtml/event/{endpoint}` | Proxied internally to `/event/{endpoint}` |

API requests (GET and POST) are redirected with HTTP 307 (Temporary Redirect), which preserves the original HTTP method and request body. This means `fetch()` calls with `method: 'POST'` work correctly through the redirect. This allows user HTML pages to use relative paths like `./api/data/channels` to access data without needing to know the absolute URL of the SlowDash server.

Server-Sent Event streams (`./event/...`) are handled differently: because the browser's `EventSource` API does not follow HTTP redirects, the event stream is proxied internally rather than redirected.

Absolute paths (e.g., `/api/data/channels`) also work and are equivalent to using the SlowDash API directly, bypassing the userhtml routing entirely.

# Using SlowJS
SlowJS is the JavaScript library bundled with SlowDash. It provides modules for building dashboards, embedding plots, and accessing the SlowDash data API. From a user HTML page, SlowJS modules are imported using paths relative to `./slowjs/`:

```javascript
import { Layout } from './slowjs/layout.mjs';         // Dashboard layout engine
import { TimeAxisPlotPanel } from './slowjs/panel-plot.mjs'; // Individual plot panel
import { SlowDash } from './slowjs/slowdash.mjs';     // Full SlowDash application object
```

The SlowDash CSS stylesheet can be included as:
```html
<link rel="stylesheet" type="text/css" href="slowjs/slowdash.css">
```

# Examples
Some examples can be found in the `ExampleProjects/Advanced/UserHTML` directory.

### Using an External JavaScript Library (Chart.js)
This example fetches data using the SlowDash Web API and makes a pie chart using the Chart.js library. The data is fetched with a relative URL `./api/data/...`, which SlowDash transparently redirects to the actual API endpoint.

```html
<!DOCTYPE HTML>
<html lang="en">
<head>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>

<body>
  <h3>This is an example of using a JavaScript library with SlowDash data</h3>
  <canvas id="chart_pie"></canvas>
  
  <script type="module">
    async function main() {
        const response = await fetch('./api/data/ch0,ch1,ch2,ch3?length=60');
        if (! response.ok) {
            return;
        }
        const data = await response.json();
        
        const labels = ['ch0', 'ch1', 'ch2', 'ch3'];
        const values = Array.from({length:labels.length}, (_,i)=>data[labels[i]].x.at(-1));
        new Chart(document.getElementById('chart_pie'), {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{ data: values }]
            },
        });
    }
    window.addEventListener('DOMContentLoaded', main);
  </script>    
</body>
```

### Embedding a SlowDash Layout
This example embeds a SlowDash plot panel using the `Layout` module from SlowJS. The layout is configured programmatically and rendered with data fetched from the SlowDash API.

```html
<!DOCTYPE HTML>
<html lang="en">
<head>
  <meta http-equiv="content-type" content="text/html; charset=UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" type="text/css" href="slowjs/slowdash.css">
</head>

<body style="overflow:auto">
  <h3>This is an example of embedding SlowDash layout</h3>
  <div id="layout" style="width:50vw;height:30vw;margin:2rem"></div>

  <script type="module">
    import { Layout } from './slowjs/layout.mjs';
        
    async function main() {
        const config = {
            panels: [{
                type: "timeaxis",
                plots: [
                    { type: "timeseries", channel: "ch0" },
                    { type: "timeseries", channel: "ch1" }
                ],
                legend: { style: "box" }
            }]
        };
        let layout = new Layout('#layout');
        await layout.configure(config);
        
        const response = await fetch('./api/data/ch0,ch1,ch2,ch3?length=86400&resample=300');
        if (! response.ok) {
            return;
        }
        const data = await response.json();
        layout.draw(data);
    }

    window.addEventListener('DOMContentLoaded', main);
  </script>    
</body>
```

### Using the Full SlowDash Application Object
The `SlowDash` module provides a self-contained application object that handles auto-updating, layout loading from JSON files, and channel management. This is the highest-level interface, equivalent to running a standard SlowDash dashboard.

```html
<!DOCTYPE HTML>
<html lang="en">
<head>
  <meta http-equiv="content-type" content="text/html; charset=UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" type="text/css" href="slowjs/slowdash.css">
</head>

<body>
  <div id="layout"></div>

  <script type="module">
    import { SlowDash } from './slowjs/slowdash.mjs';

    const slowdash = new SlowDash('#layout', 'my-layout.json');
    slowdash.start();
  </script>
</body>
```

Here `my-layout.json` is a SlowDash layout file placed in the project directory (not in `userhtml/`), accessible via the SlowDash file API.
