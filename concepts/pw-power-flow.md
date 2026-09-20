---
type: concept
domain: tooling
aliases: [pw-powerflow, powerflow-solution, simulator-power-flow]
tags: [powerworld, manual, power-flow, solver, voltage-control]
---

# PowerWorld: Power flow

## Abstract

How Simulator solves the AC and DC power flow, and every control that acts during the solve — remote regulation, Mvar sharing, line-drop compensation, droop with deadband, island AGC. Read it before touching solver options or asking why a case converged differently than expected.

**49 topics across 14 chapter files.**

## Connections

**Up:** [pw-manual-map](pw-manual-map.md) · **Corpus:** [powerworld-help-corpus](powerworld-help-corpus.md)

**Across:** pw-opf · [pw-pv-qv](pw-pv-qv.md) · pw-topology · [pw-timestep-sim](pw-timestep-sim.md)

**Research pages that use this:** [esapp](esapp.md) · [powerworld-simauto](powerworld-simauto.md)

## Content

### What it covers

- Solution theory: bus equations, bus categories, the voltage/reactive equation choice
- Solver options — common, advanced, DC, island creation, post-solution actions
- Voltage and reactive control: remote regulation, Mvar sharing, setpoint tolerance, droop with deadband
- Transformer control, AVR and Mvar control dialogs; generator Q capability curves
- Ybus, Jacobian and admittance-matrix export; bus mismatches
- Governor power flow and island-based AGC

### Where it lives

| Chapter file | Topics | Holds |
|---|--:|---|
| `10-power-flow-solution-and-options-part2.md` | 10 | Power flow solution theory, simulator options, and solution and control settings. |
| `10-power-flow-solution-and-options-part1.md` | 9 | Power flow solution theory, simulator options, and solution and control settings. |
| `05-case-information-displays-by-object-part3.md` | 5 | The per-object case information displays: buses, generators, loads, lines, transformers, shunts, interfaces, ownership and more. |
| `05-case-information-displays-by-object-part1.md` | 4 | The per-object case information displays: buses, generators, loads, lines, transformers, shunts, interfaces, ownership and more. |
| `06-object-properties-edit-mode-part1.md` | 4 | Edit-mode property dialogs for every Simulator object type. |
| `10-power-flow-solution-and-options-part3.md` | 4 | Power flow solution theory, simulator options, and solution and control settings. |
| `18-general-tools.md` | 4 | Limit monitoring, difference case, scale case, connections tools and other general-purpose tools. |
| `06-object-properties-edit-mode-part2.md` | 2 | Edit-mode property dialogs for every Simulator object type. |
| `52-additional-linked-topics-part2.md` | 2 | Topics reachable from links inside the manual but not listed in the help system's table of contents. |
| `03-cases-files-and-formats.md` | 1 | Opening, creating, closing and saving cases; every supported file format; project files. |
| `05-case-information-displays-by-object-part2.md` | 1 | The per-object case information displays: buses, generators, loads, lines, transformers, shunts, interfaces, ownership and more. |
| `06-object-properties-edit-mode-part3.md` | 1 | Edit-mode property dialogs for every Simulator object type. |
| `07-object-properties-run-mode-and-general-part2.md` | 1 | Run-mode and general property dialogs, object groups, supplemental data and data maintainers. |
| `52-additional-linked-topics-part1.md` | 1 | Topics reachable from links inside the manual but not listed in the help system's table of contents. |

Serves: `contingency-work`, `esapp-automation`, `reactive-power-planning`, `time-step-simulation`, `transfer-and-dispatch`.

### What bites

- The chapter mixes real solver content with generic application options — Environment, File Management and Message Log Options sit in the same file and are filed elsewhere here.
- Voltage Conditioning is the tool that moves generator setpoints *and* switched shunts to hit bus targets; it is easy to miss because its title names neither.

---

*Subject page over the PowerWorld Simulator help corpus. Describes and routes; reproduces
no manual text. Topic-level detail is in `powerworld-help-index/ROUTING.md`.*

---

*Ported from the research vault. Describes and routes over the PowerWorld Simulator help corpus; reproduces no manual text.*
