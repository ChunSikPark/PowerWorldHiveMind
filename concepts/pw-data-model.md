---
type: concept
domain: tooling
aliases: [pw-fields, pw-case-information, object-field-reference]
tags: [powerworld, manual, fields, case-information, object-properties, filters]
---

# PowerWorld: Objects and fields

## Abstract

The object and field reference: every case-information display, every object property dialog, and the filtering and expression machinery that selects rows. This is where you find out what a field is called and whether you can write to it.

**177 topics across 15 chapter files.**

## Connections

**Up:** [pw-manual-map](pw-manual-map.md) · **Corpus:** [powerworld-help-corpus](powerworld-help-corpus.md)

**Across:** [pw-scripting-automation](pw-scripting-automation.md) · [pw-power-flow](pw-power-flow.md) · [pw-interfaces](pw-interfaces.md) · pw-case-data-io

**Research pages that use this:** esapp-settable-vs-enterable · [esapp](esapp.md)

## Content

### What it covers

- Model Explorer and case information display mechanics: columns, sorting, formats, custom fields
- Filtering: the filterbar, area/zone/owner filters, advanced filters, model conditions and filters
- Expressions, model expressions, string expressions, functions and operators
- Key fields and required fields
- Displays by object: bus, generator, load, line, transformer, DC line, shunt, island, owner
- Object property dialogs in both edit mode and run mode — the same object documented twice
- Generator cost models and economic curves; data checks and the difference case

### Where it lives

| Chapter file | Topics | Holds |
|---|--:|---|
| `04-model-explorer-and-case-information-part3.md` | 26 | Model Explorer and the mechanics of case information displays: filtering, sorting, columns, formats. |
| `04-model-explorer-and-case-information-part1.md` | 24 | Model Explorer and the mechanics of case information displays: filtering, sorting, columns, formats. |
| `06-object-properties-edit-mode-part3.md` | 16 | Edit-mode property dialogs for every Simulator object type. |
| `05-case-information-displays-by-object-part2.md` | 15 | The per-object case information displays: buses, generators, loads, lines, transformers, shunts, interfaces, ownership and more. |
| `06-object-properties-edit-mode-part1.md` | 14 | Edit-mode property dialogs for every Simulator object type. |
| `07-object-properties-run-mode-and-general-part2.md` | 14 | Run-mode and general property dialogs, object groups, supplemental data and data maintainers. |
| `04-model-explorer-and-case-information-part2.md` | 13 | Model Explorer and the mechanics of case information displays: filtering, sorting, columns, formats. |
| `05-case-information-displays-by-object-part1.md` | 13 | The per-object case information displays: buses, generators, loads, lines, transformers, shunts, interfaces, ownership and more. |
| `05-case-information-displays-by-object-part3.md` | 12 | The per-object case information displays: buses, generators, loads, lines, transformers, shunts, interfaces, ownership and more. |
| `07-object-properties-run-mode-and-general-part1.md` | 11 | Run-mode and general property dialogs, object groups, supplemental data and data maintainers. |
| `06-object-properties-edit-mode-part2.md` | 8 | Edit-mode property dialogs for every Simulator object type. |
| `08-view-case-data-tools.md` | 7 | Data View, Data Check, Bus View, Substation View, Spatial View, labels, difference case and fixed-number buses. |
| `52-additional-linked-topics-part1.md` | 2 | Topics reachable from links inside the manual but not listed in the help system's table of contents. |
| `10-power-flow-solution-and-options-part2.md` | 1 | Power flow solution theory, simulator options, and solution and control settings. |
| `18-general-tools.md` | 1 | Limit monitoring, difference case, scale case, connections tools and other general-purpose tools. |

### What bites

- Edit mode and run mode have **separate pages for the same object**; the field sets differ and so does what is writable.
- Key fields are the load-bearing concept for any automation. **A write that omits them silently does nothing** — no error, no change ([esapp](esapp.md), [adding-devices-esapp](../methods/adding-devices-esapp.md)). Landing on the *wrong rows* is a different bug entirely, from the positional setter form; see esapp-settable-vs-enterable.

---

*Subject page over the PowerWorld Simulator help corpus. Describes and routes; reproduces
no manual text. Topic-level detail is in `powerworld-help-index/ROUTING.md`.*

---

*Ported from the research vault. Describes and routes over the PowerWorld Simulator help corpus; reproduces no manual text.*
