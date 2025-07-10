---
title: User HTML
---

# Overview
Files placed under the project's `userhtml` directory are accessible through the SlowDash Web API of `/userhtml/{filename}`.
If an HTML file is placed, it can use the full functionality of HTML, such as applying user CSS, embedding JavaScript, and importing external JavaScript libraries. HTML files located immediately under the `userhtml` directory will be listed on the SlowDash catalog panel, alongside the SlowDash standard dashboards and plot layouts.

The SlowDash JavaScript library, SlowJS, can be accessed at `/userhtml/slowjs`, as if the `slowjs` directory exists under the User HTML directory, allowing the user HTML scripts to use the SlowDash functionality. The user HTML directory cannot contain a file named `slowjs`.

# Examples
Some examples can be found in the `ExampleProjects/Advanced/UserHTML` directory.

### Using an External JavaScript Library (Chart.js)
This example fetches data using the SlowDash Web API and makes a pie chart using the Chart.js library.
```javascript
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

### Embedding SlowDash Layout
```javascript
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
