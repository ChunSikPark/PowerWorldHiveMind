---
type: concept
domain: weather
aliases: [schedule-subscriptions, controller-time-delays, timestep-actions, tsb-schedules]
tags: [powerworld, timestep, schedules, controller-time-delays, silent-failure]
---

# Time Step schedules and controller time delays

## Abstract

The weather-to-MW workflow only ever feeds Time Step Simulation through one input
channel — a loaded `.pww`. The engine underneath it has two others: per-timepoint data
columns, and reusable **Schedules** attached to a field via a **Schedule Subscription**.
Neither is wrong to ignore for the renewable pipeline, but a case that already has
schedules, controller time delays, or Time Step Actions configured will not behave like
a plain repeated power-flow solve, and nothing in a script's output will say so — a
misread delay or an interrupted run shifts results in time or reverts a device's
behavior without raising an error.

## Connections

**Up:** [timestep-workflow](timestep-workflow.md) · [pw-timestep-sim](pw-timestep-sim.md)

**Across:** [timestep-simulation](timestep-simulation.md) · [pww-data](pww-data.md) ·
[timestep-opf-and-storage](timestep-opf-and-storage.md) (OPF/SCOPF solving is one more
per-timepoint pipeline stage, sequenced right after this page's time-delay/Time Step Action
step) ·
[weather-dependent-limits](weather-dependent-limits.md) (a separate, non-`.pww` mechanism
computing the same kind of weather-driven values this page's `WeatherStation`-adjacent
schedule inputs might otherwise be confused with)

**Deeper:** [timestep-simulation-setup](../methods/timestep-simulation-setup.md) · [time-step-simulation-backend](../references/time-step-simulation-backend.md)

## Content

### The object model: a Timepoint list

A run iterates a **Timepoint list** — up to 100,000 points, timestamped to 1-second
precision, always kept sorted by date/time regardless of insertion order. Each
timepoint carries its own input values and, once solved, its own results. This list is
the thing everything below attaches to, and it exists independently of weather data:
the PWW-loading path used by [timestep-workflow](timestep-workflow.md) is one way to
populate it, not the only way.

### Three separate input channels

- **PWW-loaded weather** — the channel the renewable pipeline uses exclusively.
- **Time-point-based data** — a value entered directly per timepoint (an hourly column
  built by scaling or deriving from another column).
- **Scheduled data** — a `Schedule` (a reusable list of datetime/value pairs — a
  "shape") attached to a specific object's field through a **Schedule Subscription**.
  One schedule can drive many devices via multiple subscriptions, each with its own
  multiplier, shift, and time offset — e.g. one maintenance-outage shape reused across
  several generators with a per-generator delay instead of duplicating the data.

A subscription is **Absolute** (the field takes the schedule's value directly) or
**Relative** (`Actual = Multiplier * ScheduleValue + ValueShift`).

### The default that silently overwrites your data

Schedules can be periodic (repeating every N days/hours/minutes/seconds) and can
interpolate between defined points, or apply only at points that exactly match a
schedule-defined datetime. Which of these is active is controlled by **"Apply Schedule
Points as Events,"** and it is **off by default** — meaning a schedule's value
re-applies at *every* timepoint, including ones between its own definition points, and
will overwrite anything else that changed the same field in between. If a field is
subscribed to a schedule and also being driven by time-point-based data, whichever
applies later in the pipeline wins, silently, with no warning that a value was
clobbered.

### Controller time delays only exist during a complete run

Switched shunts and transformers under automatic control can be configured with time
delays: a device must stay outside its regulation range for a specified duration
(separate First-Move and Next-Move delays, optionally with secondary/wider regulation
bands carrying their own delays) before it is allowed to switch or tap.

**This delay logic only activates during a "complete run"** — one started with Do Run
and allowed to finish without skipping or reordering points. Solving points
individually or out of order (e.g. while stepping through timepoints manually to debug
one) silently reverts these devices to ordinary, non-delayed automatic control for that
solve. There is no error — the case just behaves differently, and a script comparing a
manual single-point solve against a full run's result for the same timepoint can
legitimately disagree.

Normally only one switched shunt per bus may run on automatic control at a time; time
delay simulation relaxes this by iterating — fixing all but one controlled shunt at a
bus per pass, in ascending bus-number order — so a case that has genuinely never seen
more than one auto-controlled shunt per bus is not the case to test this logic against.

### Time Step Actions

Time Step Actions are contingency-action-like operations (open a branch, change
dispatch, move load, etc.) gated on a Model Criteria expression holding true
continuously for a specified delay. Like controller time delays, they are **only
evaluated during a complete run**, and each action fires at most once per run.

### Pipeline order per timepoint

Knowing the order matters for placing a pre/post script command correctly:

1. Pre-script (before or after input application, per option)
2. Apply time-point data and schedule input
3. Solve power flow
4. Check and apply time-delay devices and Time Step Actions, re-solving if anything
   changed
5. OPF/SCOPF, if the run isn't plain power flow — see
   [timestep-opf-and-storage](timestep-opf-and-storage.md)
6. Contingency analysis, if enabled
7. Post-script (before or after storing results, per option)
8. Store results

### Timed vs. Continuous

**Timed Simulation** replays timepoints at a real-time-proportional pace (a Time Scale
setting is seconds of wall-clock time per hour of sim-time) and can drive live oneline
animation. This matters only for interactive/demo use, but explains a "Timed" vs.
"Continuous" toggle a script might encounter already set in an inherited case.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*
