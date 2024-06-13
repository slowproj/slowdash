---
title: Auto-Cruise
---
# Overview
- Cycle View: cycles web pages automatically
  - Top bar shows the current URL and time to switching. Clicking the bar changes the mode to the tile view.
  - Mouse-click on the shown page suspends page switching for 300 seconds.
- Tile View: shows all the pages in a tile, still keeping the pages active

<p>
- Any web sites can be added to the Auto-Cruise list, but for external pages some functions (such as "pausing on mouse-click") are restricted due to security reasons.

# Setup
Place a JSON or YAML configuration file under `PROJECT/config` with name like `slowcruise-NAME.json` (the name must start with `slowcruise-`). The "Cruise Planner" tool available on the home page will provide a web interface for it.

Example of `Projects/ATDS/config/slowcruise-ATDS.yaml`:

```yaml
meta:
    title: ATDS All Plots
    description: Loop over all Dashboards and Plots

interval: 10

pages:
    - slowdash.html?config=slowdash-ATDS.json
    - slowplot.html?config=slowplot-ATDS.json
    - slowplot.html?config=slowplot-RTD_ACC.json
```
