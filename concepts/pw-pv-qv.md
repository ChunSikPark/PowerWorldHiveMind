---
type: concept
domain: tooling
aliases: [pw-pvqv, pv-curves, qv-curves, voltage-stability-curves]
tags: [powerworld, manual, voltage-stability, pv-curve, qv-curve, reactive]
---

# PowerWorld: PV and QV curves

## Abstract

PV and QV curve analysis — real-power transfer margin and reactive margin at a bus. One chapter, and the most directly reactive-planning-relevant subject in the manual.

**25 topics across 1 chapter file.**

## Connections

**Up:** [pw-manual-map](pw-manual-map.md) · **Corpus:** [powerworld-help-corpus](powerworld-help-corpus.md)

**Across:** [pw-power-flow](pw-power-flow.md) · [pw-injection-groups](pw-injection-groups.md) · pw-atc · pw-sensitivities

## Content

### What it covers

- PV curves: setup, injection-group and interface ramping, quantities to track, limit violations
- QV curves: bus selection, solution options, contingencies sub-tab, results and listing
- Output, plotting and tracked limits for both
- PV/QV refine model

### Where it lives

| Chapter file | Topics | Holds |
|---|--:|---|
| `29-pv-and-qv-curves.md` | 25 | PV curves, QV curves and the PV/QV refine model. |

Serves: `contingency-work`, `esapp-automation`, `reactive-power-planning`.

### What bites

- Many topic titles here are bare dialog-tab names — Setup, Options, Results, Plot, Output — so a title search will not find them. Search by the curve type, or use the index.
- The Contingencies sub-tab is part of QV, not contingency analysis; it decides which outages the margin is computed against.

---

*Subject page over the PowerWorld Simulator help corpus. Describes and routes; reproduces
no manual text. Topic-level detail is in `powerworld-help-index/ROUTING.md`.*

---

*Ported from the research vault. Describes and routes over the PowerWorld Simulator help corpus; reproduces no manual text.*
