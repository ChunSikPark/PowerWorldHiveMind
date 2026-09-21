---
type: concept
domain: tooling
aliases: [datacheck, data-check-exemption, reusable-case-check, violation-rollup]
tags: [powerworld, data-model, filters, violations, data-quality]
---

# PowerWorld: DataCheck objects

## Abstract

A `DataCheck` is a named, reusable pass/fail rule against case data — an object type plus
an Advanced Filter or inline comparison — that shows up as its own field on every object
of that type and rolls up into per-area/zone/owner counts. It replaces hand-rolling the
same one-off filter every time a script needs to ask "how many objects fail this rule right
now."

## Connections

**Up:** [pw-data-model](pw-data-model.md) · **Across:** [filter-expression-language](filter-expression-language.md) · [datamaintainer-and-object-groups](datamaintainer-and-object-groups.md)

## Content

### What a DataCheck is

A `DataCheck` (added in v20) combines an `ObjectType`, a condition — either a named
Advanced Filter or an inline single-comparison string such as `"Vpu < 0.94"`, which needs
no separate filter object — and display strings shown for the pass and fail cases. Its
`Name` field only needs to be unique within its `ObjectType`, not case-wide.

### The per-object result field

Once a DataCheck is defined, every object of its `ObjectType` gains an addressable field
`DataCheck:<location-or-name>` — either an integer index into that type's DataCheck array,
or the literal form, e.g. `"DataCheck:NERC at Mvar Limit"`. Reading it returns whichever of
the `FilterMeetsString`/`FilterNotMeetsString` display strings applies to that object.

### Aggregated rollups

Counts don't live on the DataCheck itself — they live as separate fields on the
*aggregating* object types: Area, Zone, Owner, DataMaintainer. These are addressed as
`DataCheckAggr:<location>` or `DataCheckAggr:<ObjectType> '<DataCheckName>'`, reusing the
same aggregation machinery as Calculated Fields. Each DataCheck's `Aggregation Format`
setting controls whether the rollup reports as `Meets`, `Meets/Total`, or
`Meets:NotMeets`.

### DataCheckExemption — a per-object override, not a filter edit

`DataCheckExemption` (added in v23) pairs one specific object with one specific DataCheck
so that object is permanently excluded from ever reporting as meeting that check again,
regardless of later data changes. This is distinct from editing the DataCheck's filter —
the filter still evaluates the same way for every other object, only this one object's
result is overridden. Its `Object` key field uses the same ObjectID string syntax
(primary/secondary/label, configurable) used elsewhere for identifying objects in aux
files.

A script that counts outstanding violations by evaluating DataCheck fields directly, without
also reading DataCheckExemption records, will double-count exempted objects as still
failing — the exemption suppresses the *display*, not the underlying filter evaluation that
a naive re-check would repeat.

### Shared with Dynamic Formatting

A DataCheck's filter can also be reused directly as a Dynamic Formatting rule on onelines
and displays — one filter object, two independent consumers.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*
