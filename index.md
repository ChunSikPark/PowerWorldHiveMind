# Index — every page in PowerWorldHiveMind

One line per page. Read this to decide what to open; do not open everything.

## Demos — worked examples with real output

Complete runs on a real 37-bus case, including what goes wrong and how it was fixed.

| Page | What it covers |
|---|---|
| [adding-a-device](demos/adding-a-device.md) | A complete worked run on a real 37-bus case. **Everything below actually happened**, including three failed attempts that raised no error at all. This is the single most important demo in the kit: `CreateData` accepts a... |
| [comparing-planning-cases](demos/comparing-planning-cases.md) | Two vintages of the same system — a 2016 summer peak and a 2024 summer peak — diffed to find what the plan actually builds, then a contingency set generated for **only the new devices** and solved. Real numbers... |
| [contingency-and-aux](demos/contingency-and-aux.md) | Running N-1 from nothing on a real 37-bus case, then **writing a filter and contingency `.aux` automatically** from the analysis result and loading it back. All numbers are from an actual run: 89 auto-inserted... |
| [power-flow-and-sensitivities](demos/power-flow-and-sensitivities.md) | Solving a case and asking the three standard sensitivity questions, on a real 37-bus system. Includes the `1e8` sentinel that makes LODF results look insane, and a PTDF failure whose obvious recovery **also fails** —... |
| [start-here](demos/start-here.md) | Worked runs on a real 37-bus case (Synth40: 37 buses, 89 branches, 45 generators). Every number on these pages came from an actual run — including the failures, which were left in on purpose. Start with the one-line... |
| [timestep-and-pfw](demos/timestep-and-pfw.md) | Turning a weather file into hourly wind and solar output. Covers the check that decides whether the case can do this at all — **do its renewable units carry PFW model strings?** — verified on a real case where 9 of 45... |
| [violation-remediation](demos/violation-remediation.md) | The full study, not a readout: find the N-1 violations, work out *why* they happen, propose candidate reinforcements, test each one independently, and rank them by measured effect. Real numbers from a real 37-bus case.... |

## Methods — how to do a thing

Step-by-step procedures. Read the one that matches your task.

| Page | What it covers |
|---|---|
| [adding-devices-esapp](methods/adding-devices-esapp.md) | How to programmatically create buses, branches (lines/transformers) and set loads in an open PowerWorld case with `esapp`, then solve a DC OPF and screen N-1 — the write-side mechanics the read-focused esapp-overview... |
| [applying-a-dispatch-to-a-case](methods/applying-a-dispatch-to-a-case.md) | How to turn a computed dispatch (a MW number per generator) into a runnable scenario case: write `GenMW`, switch the unused units `Open`, scale load to the scenario's level, solve DC, and save. The headline gotcha is... |
| [converting-lines-to-transformers](methods/converting-lines-to-transformers.md) | How to reclassify existing `Branch` objects as transformers when a case models every branch as a line even where the two ends sit at different nominal kV. Two gotchas, both live-verified on Synth8k: **(1)**... |
| [esapp-overview](methods/esapp-overview.md) | The entry-point how-to for driving PowerWorld from Python with `esapp`: open a case, read and write data with the bracket interface, solve power flow, inspect results, and use `snapshot()` for safe experimentation. All... |
| [handling-errors](methods/handling-errors.md) | What to do when something fails. Most PowerWorld failures are recoverable by the agent alone, so recover and keep going — the user asked for an analysis, not a running commentary on your debugging. This page sorts... |
| [how-to-analyze-results](methods/how-to-analyze-results.md) | How to write code that reads and analyzes the solar/wind generation CSVs produced by the timestep simulation. Covers the two-CSV-per-run naming convention, the 8-row metadata header layout (ISO, fuel type, PFW model... |
| [new-device-contingency-aux](methods/new-device-contingency-aux.md) | How to turn **a list of devices** (e.g. the branches and generators that are new in a planning case) into a PowerWorld contingency set, restrict violation reporting to **the areas you care about**, and ship both as one... |
| [powerworld-limitset-setdata](methods/powerworld-limitset-setdata.md) | How to change PowerWorld's own limit-monitoring thresholds (`LimitSet` object — normal-ops `LSPULow`/`LSPUHigh` and N-1 contingency `LSCtgPULow`/`LSCtgPUHigh`) from a script command or from esapp. The headline gotcha:... |
| [preflight-powerworld](methods/preflight-powerworld.md) | Run this before writing any analysis code. It takes about five seconds and answers the only question that matters at the start of a session: can this machine drive PowerWorld from Python at all? Five checks, each with... |
| [ranking-new-devices-by-severity](methods/ranking-new-devices-by-severity.md) | Given a contingency AUX built by new-device-contingency-aux — one N-1 contingency per device that is new in a planning case — solve it and answer **which new device is worst**. |
| [reading-violationctg](methods/reading-violationctg.md) | How to get **which contingency caused which violation** out of PowerWorld — thermal, voltage and interface, keyed by `CTGLabel` — by reading the `ViolationCTG` object after `CTGSolveAll()`. This is the only read path... |
| [save-powerworld-case](methods/save-powerworld-case.md) | How to write an open PowerWorld case back to disk as a `.pwb` so it can be reopened and inspected in the GUI. The headline gotcha: **do NOT use the SimAuto `SaveCase` COM function** (`pw.esa.SaveCase(...)`) — on our... |
| [teamoverbyeweather-client](methods/teamoverbyeweather-client.md) | `TeamOverbyeWeather` is a pip-installable Python client for the Team Overbye weather portal. One call downloads a weather dataset, crops it to a region, and crops it to a time window, returning `.pww` files ready for... |
| [timestep-simulation-setup](methods/timestep-simulation-setup.md) | How to drive PowerWorld's TimeStep simulation — turning `.pww` weather files into hourly solar/wind generation CSVs. Covers the prerequisites a case must satisfy per renewable generator (`GenFuelType` WND/SUN, valid... |
| [visualize-renewable-output](methods/visualize-renewable-output.md) | How to write matplotlib code that visualizes the solar/wind CSVs produced by the timestep simulation. Covers loading the 8-row metadata + hourly data structure, parsing timestamps, and the four key plot patterns: fleet... |

## Concepts — what a thing is

Background. Read when a method references something you do not recognise.

| Page | What it covers |
|---|---|
| [case-impedance-completeness](concepts/case-impedance-completeness.md) | A PowerWorld case can solve DC power flow perfectly, report sensible flows, and be handed between projects for years while carrying **no resistance and no line charging whatsoever**. DC power flow reads only `X`, so... |
| [copper-plate](concepts/copper-plate.md) | Collapse the entire transmission network — strip all branches, loads, and shunts, then add a single slack bus — so generators dispatch to serve total system load **without any transmission constraints**. Every generator... |
| [esapp-environment](concepts/esapp-environment.md) | What `esapp` is, what it needs to run, and how its pieces fit together. `esapp` (ESA++) is a Pythonic wrapper over PowerWorld Simulator's SimAuto COM server: a `PowerWorld` entry point, a bracket interface that returns... |
| [esapp](concepts/esapp.md) | `esapp` (ESA++) is a Python toolkit that gives a Pythonic, pandas-flavored interface to PowerWorld Simulator's Automation Server (SimAuto) over COM. It is Windows-only and requires PowerWorld locally. This page is the... |
| [gic](concepts/gic.md) | Geomagnetically induced currents are quasi-DC currents driven into the grid during a geomagnetic disturbance, flowing through long transmission lines and transformer neutrals. They cause half-cycle transformer... |
| [glossary](concepts/glossary.md) | Every acronym and piece of jargon this knowledge base uses, defined once. Read the **Pairs that get confused** section even if you skip the rest — `PWW` versus `PFW` alone has cost people entire afternoons, and mixing... |
| [lodf](concepts/lodf.md) | LODF gives **every branch's post-outage MW flow for every single-branch outage** from one matrix factorization — no per-contingency power-flow solve. It is not an approximation of DC contingency analysis; measured live... |
| [parallel-contingency-solve](concepts/parallel-contingency-solve.md) | A workaround for PowerWorld's own distributed `CTGSolveAll` being non-functional in this environment: instead of relying on PowerWorld's DS server + registered compute hosts (which never spawn workers here — it silently... |
| [per-unit-basis-discipline](concepts/per-unit-basis-discipline.md) | A per-unit or normalized quantity is a **pair**: the number *and* the base it was normalized against. Store only the number and you have stored nothing recoverable — yet per-unit values look like plain scalars, so they... |
| [powerworld-inertia-and-cost-data](concepts/powerworld-inertia-and-cost-data.md) | Four non-obvious PowerWorld/esapp case-data facts, all discovered the hard way while building dispatch's HRML algorithm and worth knowing before any project touches generator inertia or cost data: (1) `Gen.TSH` is H on... |
| [powerworld-simauto](concepts/powerworld-simauto.md) | SimAuto is PowerWorld Simulator's COM Automation Server — the Windows-only layer that all PowerWorld Python scripts ultimately talk to. In esapp it is wrapped by the `SAW` class (assembled via ~20 mixins) and reached... |
| [pww-data](concepts/pww-data.md) | PWW (PowerWorld Weather) is a custom byte-packed binary format produced by weather auto and consumed by PowerWorld Simulator's TimeStep Simulation engine. It encodes gridded weather variables as uint8 values (0–254) per... |
| [timestep-simulation](concepts/timestep-simulation.md) | A timestep simulation (in this project's sense) is PowerWorld's built-in TimeStep feature run over a weather time series: each renewable generator's hourly solar or wind MW output is computed quasi-statically from PWW... |
| [timestep-workflow](concepts/timestep-workflow.md) | The end-to-end chain that turns a weather file into hourly solar and wind output for every renewable generator in a case: open the case, load a `.pww`, select the renewable units, tell PowerWorld which fields to save,... |
| [version-requirements](concepts/version-requirements.md) | Which PowerWorld version you need, how to find out which one you have, and what this knowledge base was verified against. Everything here was tested on **Simulator 24, build 24.2026.7.22** — 13 of 14 feature areas... |

## References — the heavy code layer

Exact backend mechanics. Open ONLY when writing code, and only the one you need.

| Page | What it covers |
|---|---|
| [aux-script-commands](references/aux-script-commands.md) | A task-organized index of the PowerWorld SCRIPT actions this kit's workflows actually use, plus their close neighbours — 198 of the ~370 that Simulator defines. Look here to find *which* command does a job; look in... |
| [esapp-package-backend](references/esapp-package-backend.md) | Internals reference for the esapp package project, covering bracket-interface mechanics (`Indexable.__getitem__`/`__setitem__`), SAW mixin composition, the component-generation pipeline, GObject schema model, embedded... |
| [esapp-schema-reference](references/esapp-schema-reference.md) | This is the field-schema + SimAuto-command lookup for **writing esapp code**: read it when you need an object type's exact **key fields** (so a read-modify-write round-trips) or the **command/method** for an operation.... |
| [time-step-simulation-backend](references/time-step-simulation-backend.md) | Code-reconstruction reference for the time step simulation project — the `_simulation_worker` PowerWorld call sequence (weather load → generator selection → field-save wrapper → run → export), `_GEN_PARAM` field list,... |
