---
type: concept
domain: tooling
aliases: [pw-injection-group, participation-points]
tags: [powerworld, manual, injection-group, participation-point, transfer]
---

# PowerWorld: Injection groups

## Abstract

Injection groups and participation points — the object that says *which* generators and loads move, and in what proportion, when a transfer is scaled or ramped. The input side of every PV, QV and ATC study.

**10 topics across 3 chapter files.**

## Connections

**Up:** [pw-manual-map](pw-manual-map.md) · **Corpus:** [powerworld-help-corpus](powerworld-help-corpus.md)

**Across:** pw-atc · [pw-pv-qv](pw-pv-qv.md) · [pw-interfaces](pw-interfaces.md) · [pw-power-flow](pw-power-flow.md)

## Content

### What it covers

- Injection group overview, creation, deletion and auto-insertion
- The injection group display and dialog
- Participation points: overview, records display, add dialog
- The injection group file format

### Where it lives

| Chapter file | Topics | Holds |
|---|--:|---|
| `07-object-properties-run-mode-and-general-part2.md` | 6 | Run-mode and general property dialogs, object groups, supplemental data and data maintainers. |
| `05-case-information-displays-by-object-part3.md` | 3 | The per-object case information displays: buses, generators, loads, lines, transformers, shunts, interfaces, ownership and more. |
| `03-cases-files-and-formats.md` | 1 | Opening, creating, closing and saving cases; every supported file format; project files. |

### What bites

- Like interfaces, this has no chapter of its own and is gathered here.
- An ATC or PV run silently depends on how these are defined; the study chapters reference the object without documenting it.

---

*Subject page over the PowerWorld Simulator help corpus. Describes and routes; reproduces
no manual text. Topic-level detail is in `powerworld-help-index/ROUTING.md`.*

---

*Ported from the research vault. Describes and routes over the PowerWorld Simulator help corpus; reproduces no manual text.*
