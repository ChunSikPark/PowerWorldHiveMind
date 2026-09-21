---
type: concept
domain: tooling
aliases: [pw-timestep, time-step-simulation-manual, pw-tsb]
tags: [powerworld, manual, timestep, schedules, quasi-static]
---

# PowerWorld: Time Step Simulation

## Abstract

Time Step Simulation: the quasi-static tool that solves a case repeatedly across a list of timepoints with scheduled inputs. Two chapter files hold all of it, but the commands that drive it and the batch engine that scales it are elsewhere.

## Connections

**Up:** [pw-manual-map](pw-manual-map.md) · **Corpus:** [powerworld-help-corpus](powerworld-help-corpus.md)

**Across:** [pw-scripting-automation](pw-scripting-automation.md)

**Research pages that use this:** [timestep-simulation](timestep-simulation.md) · [pww-data](pww-data.md)

## Content

### What it covers

- The dialog, its pages and toolbar; timepoint lists and scheduled input data
- Schedules, schedule subscriptions and controller time delays
- Switched-shunt and transformer control options specific to time step
- Results: hourly summary, constraints, binding elements, custom result selection
- Running a timed simulation; storing input data and results

### Where it lives

| Chapter file | Topics | Holds |
|---|--:|---|
| `26-time-step-simulation-part1.md` | 22 | Time step simulation setup, schedules, controller time delays and running the simulation. |
| `26-time-step-simulation-part2.md` | 10 | Time step simulation setup, schedules, controller time delays and running the simulation. |

### What bites

- The tool is only a quarter of the story — the script commands that launch a run are in the auxiliary-file chapter, the programmatic entry point in SimAuto, and unattended batch runs in the Cruncher. Opening only this subject will not get a run automated.
- Controller time delays and the per-device time-step control options are what make results differ from a plain repeated solve.

---

*Subject page over the PowerWorld Simulator help corpus. Describes and routes; reproduces
no manual text. Topic-level detail is in `powerworld-help-index/ROUTING.md`.*

---

*Ported from the research vault. Describes and routes over the PowerWorld Simulator help corpus; reproduces no manual text.*
