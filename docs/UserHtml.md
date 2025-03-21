---
title: User HTML
---

# Overview
Files placed under project's `userhtml` directory are accessible though the SlowDash Web API of `/api/userhtml/{filename}`.
If a HTML file is placed, it can use the full functionality of HTML, such as applying user CSS, embedding Javascript, and importing external JavaScript libraries. HTML files immediately under the `userhtml` directory will be listed on the SlowDash catalog panel, together with the SlowDash standard dashboards and plot layouts.

If a requested file does not exist, then the file is searched for from the SlowDash web directory (`slowdash/app/sites`); 
in this way, user HTML can use the SlowDash API and Javascript library (SlowJS) as if they exist under the user HTML directory (therefore those are accessible with relative URL in user pages).
This, on the other hand, may cause name conflicts. All names starting with "slow" are reserved, and should not be used in user HTML.

# Examles
Some examples can be found at `ExampleProjects/Advanced/UserHTML`.

### Using an External Javascript Library (Chart.js)
This examples fetches data using the SlowDash Web API and makes a pie chart using the Chart.js library.
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
