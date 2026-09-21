---
type: concept
domain: tooling
aliases: [pw-manual, powerworld-manual-map, pw-subjects, simulator-manual-map]
tags: [powerworld, manual, navigation, moc, documentation]
---

# PowerWorld manual — subject map

## Abstract

**Twenty-five subject pages over the PowerWorld Simulator manual, cut by what you are trying to
do rather than by how the program is organised.** The manual groups its 1670 topics by ribbon tab
and dialog, so a research subject lands in three or four chapters its contents page never shows
together. Start here, pick the subject, and the page names the chapter files to open.

These pages describe and route. They reproduce no manual text — the corpus itself lives in
[powerworld-help-corpus](powerworld-help-corpus.md), and topic-level detail in the routing index beside it.

## Connections

**Up:** [Home](../index.md) · **Corpus:** [powerworld-help-corpus](powerworld-help-corpus.md) ·
**Research:** [esapp](esapp.md) · [powerworld-simauto](powerworld-simauto.md)

## Content

### Start here

| If you want to… | Open |
|---|---|
| solve a case, or understand a control acting during the solve | [pw-power-flow](pw-power-flow.md) |
| run or interpret contingencies | [pw-contingency](pw-contingency.md) |
| run a quasi-static study across time | [pw-timestep-sim](pw-timestep-sim.md) |
| find a field name, or work out if it is writable | [pw-data-model](pw-data-model.md) |
| automate anything from Python | [pw-scripting-automation](pw-scripting-automation.md) |
| work on reactive support or voltage margin | [pw-pv-qv](pw-pv-qv.md) · [pw-power-flow](pw-power-flow.md) |
| look up a dynamic model | `38-ts-models-machine` … `46-ts-models-other` (21 files) |
| find out what a chapter file contains | the routing index, not these pages |

### Studies you run

| Subject | Topics | Files | Note |
|---|--:|--:|---|
| [Power flow](pw-power-flow.md) | 49 | 14 |  |
| [Contingency analysis](pw-contingency.md) | 96 | 7 |  |
| [Time Step Simulation](pw-timestep-sim.md) | 32 | 2 |  |
| [PV and QV curves](pw-pv-qv.md) | 25 | 1 |  |
| Optimal power flow | 44 | 7 | `30-optimal-power-flow-part1`, `30-optimal-power-flow-part2`, `06-object-properties-edit-mode-part1`, +4 more |
| SCOPF and OPF reserves | 29 | 1 | `31-scopf-and-opf-reserves` |
| Available Transfer Capability | 22 | 1 | `32-available-transfer-capability` |
| Fault analysis | 13 | 4 | `27-fault-analysis`, `52-additional-linked-topics-part1`, `03-cases-files-and-formats`, +1 more |
| GIC analysis | 7 | 2 | `47-geomagnetically-induced-currents`, `52-additional-linked-topics-part1` |

### Objects a study consumes

| Subject | Topics | Files | Note |
|---|--:|--:|---|
| [Interfaces and flowgates](pw-interfaces.md) | 11 | 4 |  |
| [Injection groups](pw-injection-groups.md) | 10 | 3 |  |
| Weather-dependent ratings | 14 | 2 | `28-weather`, `52-additional-linked-topics-part2` |
| Sensitivities | 27 | 4 | `20-sensitivities`, `23-contingency-analysis-running-and-results`, `22-contingency-analysis-options`, +1 more |
| Topology processing | 28 | 5 | `35-integrated-topology-processing`, `18-general-tools`, `52-additional-linked-topics-part1`, +2 more |

### Dynamics

| Subject | Topics | Files | Note |
|---|--:|--:|---|
| Transient stability | 90 | 9 | `36-transient-stability-overview-and-data-part1`, `37-transient-stability-analysis-dialog-part2`, `52-additional-linked-topics-part2`, +6 more |
| Dynamic model catalog | 580 | 21 | **155 say nothing** |

### Driving it from code

| Subject | Topics | Files | Note |
|---|--:|--:|---|
| [AUX files and SimAuto](pw-scripting-automation.md) | 99 | 8 |  |
| [Objects and fields](pw-data-model.md) | 177 | 15 |  |
| Cases and file formats | 30 | 7 | `03-cases-files-and-formats`, `08-view-case-data-tools`, `07-object-properties-run-mode-and-general-part2`, +4 more |
| Cruncher and distributed computing | 24 | 7 | `50-cruncher`, `10-power-flow-solution-and-options-part2`, `22-contingency-analysis-options`, +4 more |
| Scheduled actions | 5 | 1 | `48-scheduled-actions` |

### Editing and drawing

| Subject | Topics | Files | Note |
|---|--:|--:|---|
| Network tools | 30 | 5 | `19-edit-mode-tools`, `18-general-tools`, `06-object-properties-edit-mode-part2`, +2 more |
| Oneline diagrams | 175 | 14 | `13-building-onelines-graphics-and-insertion`, `11-building-onelines-network-objects`, `12-building-onelines-branches-and-devices`, +11 more |
| The Simulator interface | 39 | 4 | `02-simulator-ribbon`, `01-getting-started`, `10-power-flow-solution-and-options-part2`, +1 more |
| Licences and release notes | 14 | 3 | **8 say nothing** |

**Nine subjects have a detail page in this kit** — the ones linked above. The rest are
listed with the chapter files that hold them, which is the routing you actually need; their
detail pages live in the research vault this kit was extracted from.

### Before you trust anything in it

Four properties of this corpus decide whether an answer you find is real. They are stated once,
in [powerworld-help-corpus](powerworld-help-corpus.md), and not repeated here: **a subject is never one chapter**, **164
topics carry no usable body**, **superseded API pages sit beside current ones**, and **the manual
holds no per-object field catalog**. Read that page before your first serious search; each subject
page below carries only its own local traps.

### What these pages are not

They route; they do not teach. For the engineering, follow the **Research** links on each subject
page back into the vault. For topic-level detail — every one of the 1,670 topics with its anchor,
tags and size — use the routing index in `powerworld-help-index`, not these pages.

---

*Ported from the research vault. Describes and routes over the PowerWorld Simulator help corpus; reproduces no manual text.*
