---
type: concept
domain: tooling
aliases: [timestep-scopf, timestep-results-storage, tsb-file, timestep-solution-types]
tags: [powerworld, timestep, opf, scopf, tsb, results-storage]
---

# Time Step OPF/SCOPF and results storage

## Abstract

Beyond plain power flow, Time Step Simulation can solve each timepoint as an
Unconstrained OPF, OPF, or SCOPF, and the storage of its results is opt-in and
configurable rather than automatic. A run that "succeeds" can still produce an empty
result grid, and the `.tsb` file that saves all of this can be set to auto-load — and
auto-run — the moment a `.pwb` is opened. None of this is reachable from the CSV-export
shape the weather-to-MW pipeline already documents.

## Connections

**Up:** [timestep-workflow](timestep-workflow.md) · [pw-timestep-sim](pw-timestep-sim.md)

**Across:** [timestep-schedules-and-delays](timestep-schedules-and-delays.md) · [copper-plate](copper-plate.md)

**Deeper:** [how-to-analyze-results](../methods/how-to-analyze-results.md) · [time-step-simulation-backend](../references/time-step-simulation-backend.md)

## Content

### Four solution types, settable per timepoint

Each timepoint independently selects a Solution Type — Power Flow, Unconstrained OPF
(economic dispatch), OPF, or SCOPF — and each point's solved state becomes the initial
condition for the next point in the run. OPF and SCOPF require the corresponding
Simulator add-on license. AC or DC solving can also be chosen independently for the
power flow stage, the contingency-analysis stage, and the SCOPF stage; using DC for
contingency analysis specifically is the single biggest speed lever for a slow SCOPF
timestep run.

### Results are opt-in — a run can succeed and store nothing

**Custom Results Selection** must be configured before a run: a field on an object type
is stored only once explicitly marked (selected + `Time Selected = YES`). A run without
this configured completes without error and produces no usable results grid. This is
the same underlying mechanism as the `TimeStepSaveFieldsSet` requirement documented in
[timestep-workflow](timestep-workflow.md), generalized here to any object type, not
just generators — worth restating because it is easy to assume results are captured by
default.

Storage itself has three modes with a real tradeoff:

- **Memory only** — populates the result grids; risks running out of memory on a large
  field set times a long run.
- **CSV only** — avoids the memory pressure entirely, but leaves the result grids
  empty, so a script that checks grid contents after a CSV-only run sees nothing.
- **Both.**

CSV filenames combine a user-set identifier prefix with the result type (e.g.
`<prefix>_Buses.csv`); object IDs in those files can be Primary (number), Secondary
(name), or Label — see [how-to-analyze-results](../methods/how-to-analyze-results.md)
for the export shape the weather pipeline already uses.

### SCOPF-specific results

LMPs (average/std dev/min/max), initial/unconstrained/final cost, and binding
line/interface/contingency constraints with marginal costs are all available, plus a
count of unsolvable contingencies. Binding constraints are reachable through the
Results: Constraints grids or the equivalent SimAuto-queryable fields; a per-constraint
detail view (type, ID, contingency name, marginal cost) is navigable timepoint by
timepoint.

### The `.tsb` file — and its auto-run trap

A `.tsb` (Time Series Binary) file is the complete save/restore unit for a Time Step
Simulation: all input data (both time-point-based and scheduled), simulation options
except "Auto Load TSB" (which lives in the `.pwb` itself), custom-results definitions,
and any already-computed results.

A `.pwb` can be configured to auto-load its default `.tsb` on open, and optionally
auto-run it — something a script or agent opening an unfamiliar case should account
for, since it can kick off a long simulation as a side effect of simply opening the
file. Custom-results *definitions* alone (without data) can be saved and reloaded
separately as a `.tsc` file, letting a results configuration be reused across different
cases or runs.

### Reset Run captures its reference case once

"Reset Run" reverts to a **Reset Reference Case** captured once, when the Time Step
Simulation dialog first opens — it is not re-captured automatically afterward. If the
in-memory case changes while the dialog stays open, a script relying on Reset Run to
return to the *current* case state must explicitly re-arm this reference first, or it
will reset to a stale snapshot from before those changes.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*
