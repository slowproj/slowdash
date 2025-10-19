Dripline Console
================
## Features
- Listing sensor values without going through database
- Listing Dripline service heartbeats
- Sending SET/GET/CMD commands to endpoints

| &nbsp; |
|--------|
| <img src="DriplineConsole.png" width="90%" style="border:thin solid black;"> |

## Setup
Copy the `slowdash.d/config/slowtask-DriplineConsole.py` file to your SlowDash configuration directory,
and enable the slowatsk in your `SlowdashProject.yaml`:
```yaml
  task:
    name: DriplineConsole
    auto_load: true
```
