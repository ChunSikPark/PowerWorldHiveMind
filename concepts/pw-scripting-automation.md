---
type: concept
domain: tooling
aliases: [pw-simauto, pw-aux, auxiliary-files-and-script]
tags: [powerworld, manual, aux, script, simauto, automation]
---

# PowerWorld: AUX files and SimAuto

## Abstract

Driving Simulator from outside: the auxiliary file format, script command execution, and the SimAuto automation server with one topic per function. The chapter to open before writing any PowerWorld automation.

**99 topics across 8 chapter files.**

## Connections

**Up:** [pw-manual-map](pw-manual-map.md) · **Corpus:** [powerworld-help-corpus](powerworld-help-corpus.md)

**Across:** [pw-data-model](pw-data-model.md) · pw-case-data-io · [pw-timestep-sim](pw-timestep-sim.md) · pw-distributed-compute

**Research pages that use this:** [esapp](esapp.md) · [powerworld-simauto](powerworld-simauto.md) · [aux-only-powerworld](aux-only-powerworld.md) · [aux-script-catalog](../references/aux-script-commands.md)

## Content

### What it covers

- Auxiliary file export formats — display, power system, complete case, network model
- Object field variable names and the ObjectID field
- Script command execution dialog and quick auxiliary files
- SimAuto setup: installing, connecting, passing and getting data, ExcelApp, ProcessID
- SimAuto functions with sample code: Get/ChangeParameters in all their variants, ListOfDevices, OpenCase, SaveCase, SaveState/LoadState, ProcessAuxFile, RunScriptCommand, WriteAuxFile, TSGetContingencyResults

### Where it lives

| Chapter file | Topics | Holds |
|---|--:|---|
| `34-simauto-functions.md` | 55 | Every SimAuto function, with signature, parameters and examples. |
| `33-simauto-overview-and-setup.md` | 16 | Starting SimAuto, accessing data, properties and object variables. |
| `52-additional-linked-topics-part1.md` | 15 | Topics reachable from links inside the manual but not listed in the help system's table of contents. |
| `09-auxiliary-files-and-script-commands.md` | 8 | Auxiliary file format, script commands, export format descriptions and object field variable names. |
| `03-cases-files-and-formats.md` | 2 | Opening, creating, closing and saving cases; every supported file format; project files. |
| `22-contingency-analysis-options.md` | 1 | The Contingency Analysis dialog: Contingencies tab and the full Options tab. |
| `23-contingency-analysis-running-and-results.md` | 1 | Running contingency analysis, file formats, sensitivity analysis, results and comparing runs. |
| `52-additional-linked-topics-part3.md` | 1 | Topics reachable from links inside the manual but not listed in the help system's table of contents. |

### What bites

- **Field names are not in this manual, and never were in the other one.** The provenance rule and what to verify against are in [aux-only-powerworld](aux-only-powerworld.md); that the WebHelp declines too is recorded in [powerworld-help-corpus](powerworld-help-corpus.md). Do not look for a field catalog here.
- **This is the subject the legacy-duplicate trap actually bites.** Version-9 pages for these same functions sit in the appendix with near-identical titles; the rule is in [powerworld-help-corpus](powerworld-help-corpus.md).
- The core AUX format spec is a bundled PDF, not inline markdown.

---

*Subject page over the PowerWorld Simulator help corpus. Describes and routes; reproduces
no manual text. Topic-level detail is in `powerworld-help-index/ROUTING.md`.*

---

*Ported from the research vault. Describes and routes over the PowerWorld Simulator help corpus; reproduces no manual text.*
