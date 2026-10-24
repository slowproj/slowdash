---
title: Data Centric Controls and Monitor
---


# Overview
In SlowMesh/SlowTask, control is driven by PubSub messages rather than RPC.
The idea is to specify a "desired state," and then expect the individual tasks that make up the system to cooperate to achieve it. The issuing side does not specify exactly "who" does "what."
This is fundamentally different from the conventional approach of using RPC or similar mechanisms to send a command to a specific target.
The SlowDash philosophy is essentially: "do only what you want," "don't worry about who is around or what they are doing," and "expect that someone will fulfill your request."
This achieves independence for each task (doing and reporting only what it wants) and loose coupling (trusting that some unknown entity will take care of things).

Unlike RPC-based control, PubSub message-based control has no return value, so command success or failure cannot be obtained directly.
Whether a control succeeded is determined by a monitor task that watches whether the system transitions to the desired state.

Typically, the task issuing the control publishes an intent; when the monitor intercepts it, it notifies the issuing task and takes on responsibility from that point on.
The control message includes not only the direct target of the operation but also the expected system state that should result from it.
This mechanism allows the monitoring conditions to change in response to controls, even when the system state the monitor is watching changes.

Once a monitor starts, the data indicating the state is monitored continuously.
The monitoring interval, after the first data point, is advertised by the data producer.
Normally, the data producer knows the read interval for its own data, so this eliminates the need to communicate the data interval to the monitor in advance.
The time until the first data point is specified by the control side.


### Example: Setting HV, but wire is broken — voltage appears but no current flows
A control is triggered by publishing an intent message:
```
{
    "desire":      "Set output voltage to 2000 V",
    "consequence": [
        "OUTPUT status is ON (within 10 seconds)",
        "Output voltage readback is 2000 V with 0.1 V precision (within 20 seconds)",
        "Output current is between 0.1 uA and 0.5 uA (within 20 seconds)",
    ],

    "effective_at": "08:00",
    "deadline":     "08:01"
}
```

The task responsible for HV receives the intent and configures the device.
That same task probably also reads the output values periodically and publishes them as data.

A data message looks like:
```
{
    "timestamp":     <timestamp>,
    "channel":       "output_current",
    "value":         <output current value>,

    "next_delivery": "10 seconds later"
}
```

The monitor task reads the `consequences` from the intent, updates the normal conditions, and then compares them against data that arrives within the specified time window.

The key point is that even though you are setting the voltage, you can monitor the current.
If the wire is broken, voltage will read back normally even though no current flows — with conventional RPC-based control, everything appears to succeed (command execution, readback confirmation, etc.).
Because the normal current value depends on the voltage state (On/Off), if a conventional monitor tried to track the appropriate normal value based on the situation, the condition descriptions would become increasingly complex, potentially requiring something like a global "run mode," with control logic spread across multiple places.
With this approach, there is no need to describe value conditions, data intervals, and so on in the monitor task's configuration in advance.

In addition, when an error appears in the monitoring data, it can be correlated with the operation that caused it. This resembles the recently popular concept of Observability/Traceability, but the trace can be carried through hardware as well. (Conventional Observability techniques — such as attaching Trace-ID / Span-IDs — cannot track the causal relationship between an operation and its result across a device boundary.)

For continuous readout without control (e.g., ambient temperature), you can inject conditions into the monitor by publishing only the `consequences`.
Also, for many simple devices, the `consequences` section should be auto-generatable to a reasonable degree.

# Implementation
## Control Message
### Topic: `control.intent.{target}`
```json
{
    "target": target,
    "desire": {
        "value": value
     },
    
    "effective_at": timestamp,
    "deadline": timestamp,
    
    "consequences": [
        {
            "topic": data_topic, 
            "condition": {
                "range": [low, high]
            },
            "delay": max_time_to_data
        }
        ...
    ],
    
    "issued_by": mesh_id,
    "timestamp": timestamp
}
```

- `effective_at` specifies when to execute the command. If not specified, executed immediately.
- If command execution cannot be completed by `deadline`, it is treated as an error. If not specified, the deadline is not enforced.

- `consequences` is used by the monitor. Of course, if a device communication error occurs, the control execution task is free to emit an error or alarm.
- Data checking in `consequences/condition`:
  - ` ` (empty): Any data value is acceptable as long as data arrives.
  - `"range": [low, high]`: Range check.
  - `"value": value` / `"values": [values]`: Exact match check for integer or string.
  - `"match": pattern`: Regular expression check for string values.
  - `"bits": mask` / `"zero_bits": mask`: Bit check for integer values.
  - `"custom": { "type": {name}, "params": {...} }`: Custom check.
  - Other Data Conditions supported by the monitor system can also be used.

- Additional parameters available in `consequences/condition`:
  - `severity`: Severity level when the condition is not met beyond `grace`. Default: `error`.
  - `grace`: Maximum number of consecutive allowable failures before the condition is considered unmet. Default: `0`.

- If data does not arrive within `delay`, it is treated as an error. If not specified, the monitor waits indefinitely.

- If there are multiple consequences for the same `topic`, the later-arriving one overwrites the earlier one.
  - However, if a `name` is specified in a `consequence`, the overwrite applies to `{name}.{topic}` instead.


## Data Format
### Topic: `data.{category}.{channel}`
- `category` indicates how the data producer expects the data to be used.
  - `monitor`: High-frequency data intended primarily for real-time monitoring.
  - `store`: Essential data expected to be recorded in a persistent storage.
  
```json
{
    "channel": channel,
    "timestamp": timestamp,
    "value": value,
    
    "next_delivery": max_time_to_next_data
}
```

- The same data monitoring as in `consequences` of a control message is applied.
- The monitor treats it as an error if data does not arrive within `next_delivery`.
- If `next_delivery` is absent, the monitor does not perform a timeout check.
- Setting `next_delivery` to `None`/`null` or a non-positive value stops monitoring for that topic.


## Monitor
A monitor task subscribes to both `control.intent.>` and `data.>`, and checks the state.
If an expected state or state transition does not occur, it outputs an error.

- When the monitor intercepts an intent, it sends an Observed message back to the issuer.
  - This lets the issuing side confirm that the intent is now being monitored, giving it confidence.
  - If no Observed arrives, it means the mesh is down or the monitor has died.
- The monitor outputs error states as time-series data.
  - `monitor.{category}.{channel}`
  - For each data point (even if no data arrives), a point representing the error state is generated.
  - An Alarm task watches this and handles alarm processing.
  - A Store task may also record this, enabling retrieval of error states for historical data.

An error is a state; alarm issuance is triggered by a state transition.


### Topic: `control.observed.{mesh_id}`
```json
{
    "intent_id": intent_id,
    "issued_by": self.mesh_id,
    "timestamp": timestamp
}
```
- `intent_id` is the Message ID of the intent message, obtained from the header.

### Topic: `monitor.{category}.{channel}`
- `category` is the same as in the `data` topic.

```json
{
    "timestamp": timestamp,
    "channel": channel,
    "intent_id": intent_id,
    "severity": severity,
    "message": message
}
```
