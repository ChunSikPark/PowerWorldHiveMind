---
type: concept
domain: tooling
aliases: [pw-ctg, contingency-analysis, pw-contingency-analysis]
tags: [powerworld, manual, contingency, ras, limits]
---

# PowerWorld: Contingency analysis

## Abstract

Contingency analysis end to end: how contingencies are defined, what an element can do, every option that changes the result, and how results are read back. The largest single analysis subject in the manual after dynamics.

**96 topics across 7 chapter files.**

## Connections

**Up:** [pw-manual-map](pw-manual-map.md) · **Corpus:** [powerworld-help-corpus](powerworld-help-corpus.md)

**Across:** [pw-interfaces](pw-interfaces.md) · pw-sensitivities · pw-topology · [pw-scripting-automation](pw-scripting-automation.md)

## Content

### What it covers

- Defining contingencies: auto-generation, PSS/E and PSLF list formats, the concise RAS format
- The contingency element dialog — one topic per element type, from branch to script
- Options that change the answer: DC and screening, post-contingency AGC, load throw-over, switched-shunt post-CTG behaviour, limit monitoring and monitoring exceptions
- Remedial action schemes and global actions
- Running, results by element, violation notes, report writing, comparing two runs
- CTG combination analysis

### Where it lives

| Chapter file | Topics | Holds |
|---|--:|---|
| `22-contingency-analysis-options.md` | 26 | The Contingency Analysis dialog: Contingencies tab and the full Options tab. |
| `24-contingency-element-dialog.md` | 24 | The Contingency Element dialog and every element action type. |
| `21-contingency-analysis-overview-and-records.md` | 19 | What contingency analysis does, available contingency actions, case references and contingency records. |
| `23-contingency-analysis-running-and-results.md` | 16 | Running contingency analysis, file formats, sensitivity analysis, results and comparing runs. |
| `52-additional-linked-topics-part1.md` | 7 | Topics reachable from links inside the manual but not listed in the help system's table of contents. |
| `25-ctg-combo-analysis.md` | 3 | Contingency combination analysis and the combination element dialog. |
| `05-case-information-displays-by-object-part1.md` | 1 | The per-object case information displays: buses, generators, loads, lines, transformers, shunts, interfaces, ownership and more. |

### What bites

- Reference-state handling is its own set of topics and is easy to skip; it decides what the violations are measured *against*.
- Several contingency options live one link away in the appendix chapter — stuck-breaker creation, legacy definitions, and the relationship between contingencies, model conditions and model filters.

---

*Subject page over the PowerWorld Simulator help corpus. Describes and routes; reproduces
no manual text. Topic-level detail is in `powerworld-help-index/ROUTING.md`.*

---

*Ported from the research vault. Describes and routes over the PowerWorld Simulator help corpus; reproduces no manual text.*
