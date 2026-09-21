---
type: concept
domain: tooling
aliases: [difference-case, diff-case, removedbus, removedgen, complete-model-export, diffchangetolerance]
tags: [powerworld, difference-case, simauto, aux, case-diff, scripting]
---

# The built-in Difference Case tool

## Abstract

PowerWorld ships a case-comparison engine of its own — SimAuto-queryable `Removed<Type>` object
types, per-field change tolerances, and a "Complete Model" AUX export that turns a base case into a
present case — that a hand-rolled pandas diff duplicates without knowing it exists. It doesn't
replace project-specific diff logic (renumber pairing, retirement classification, and similar business
rules have no native equivalent), but it answers "what changed" and "what's new since base" with
built-in tolerance handling that a naive numeric comparison gets wrong.

## Connections

**Up:** [pw-manual-map](pw-manual-map.md) · **Across:** [case-to-case-device-transplant](case-to-case-device-transplant.md) · [comparing-planning-cases](../demos/comparing-planning-cases.md) ·
[raw-epc-roundtrip-traps](raw-epc-roundtrip-traps.md) (a diff run across a RAW/EPC round-trip
can flag reinterpreted-but-unchanged fields as real differences unless tolerance handling
absorbs them)

## Content

### Base and Present, and how objects are matched

The tool compares a **Base** case (set via "Set Present as Base") against the **Present** case
currently in memory. Matching between the two uses one of the same three key schemes used
elsewhere in Simulator: primary keys (bus numbers), secondary keys (name + kV), or labels — chosen
up front, not inferred per-object.

### Four display modes

- **Present** and **Base** — each case's own values.
- **Difference** (Present − Base) — numeric fields show the delta; status fields show `OPEN|CLOSED`
  style before/after pairs.
- **Change** (added in V20) — shows a value only where something actually changed, blank otherwise.

### Numeric "changed" is a tolerance decision, not exact equality

The default threshold is 0.0001% relative, overridable per object-type/field via `DiffChangeTolerance`
objects (Absolute / Percent / Perc-or-Abs / Perc-and-Abs). This matters beyond the built-in tool: any
home-grown comparison of solved AC quantities across two solves should expect meaningless float noise
unless it respects an equivalent tolerance — treating a `1e-12` delta as a real change is a common
false positive in ad hoc diffs.

Blank-vs-defined values (e.g. Latitude/Longitude, where blank is itself a meaningful "undefined"
state) get special handling in Change Mode: the literal string `"_same_"` is shown when nothing
actually changed, to disambiguate from "the value became blank."

### Topological differences are a separate dialog

The plain Difference Case display only shows value deltas on objects that match in both cases — it
cannot show additions or removals. That's a distinct dialog, "Present Topological Differences from
Base."

### Querying what's gone, without writing your own key-diff

Removed objects are exposed as their own SimAuto object types, named `Removed<Type>`
(`RemovedBus`, `RemovedGen`, etc.), queryable via `GetParametersMultipleElement` — or esapp's
bracket interface — like any other object type. Loading these back into Simulator in Edit Mode
**deletes** the corresponding objects, which is a scriptable way to get "what disappeared between
base and present" without writing a key-based diff by hand.

There's also a boolean field, `Difference Case\In Diff Base`, on every difference-case-eligible
object type — usable directly in ordinary filters and scripts to select "new since base" (`NO`) vs.
"existed in base" (`YES`) without opening the dialog at all.

### The Complete Model export — a native alternative to a hand-built transplant AUX

[case-to-case-device-transplant](case-to-case-device-transplant.md) builds its transplant AUX by hand:
dump the source with `SaveCase(AUX)`, filter by key, and reload with `LoadAux(create_if_not_found=True)`.
The **Complete Model** export produces the equivalent artifact natively: a single AUX file that, loaded
back into the original base case, transforms it into the present case. It deletes removed objects
(`Delete(objecttype, SELECTED)`), inserts new objects, and writes only the changed fields for objects
present in both (via Change Mode).

Two special-case sections are auto-inserted ahead of the new-object inserts, to avoid corrupting
per-unit impedance or clobbering ownership:
1. Nominal-voltage changes on a shared terminal bus are applied first — branch impedance is stored on
   transformer base, and applying it after new devices exist would silently rebase it.
2. Owner/area/zone reassignment is written before device creation, so auto-synchronization doesn't
   clobber an unrelated device's ownership.

**Where this fits next to the hand-built transplant, not instead of it:** the two are complements.
Complete Model gives you PowerWorld's own field-complete diff/apply mechanics; it has no equivalent
for project-specific business logic — renumber pairing, retirement classification, area/voltage
scoping — which is exactly the part [case-to-case-device-transplant](case-to-case-device-transplant.md)
and [comparing-planning-cases](../demos/comparing-planning-cases.md) build by hand. Consider Complete
Model when you want a native, tolerance-aware apply step and don't need custom matching rules; keep
the pandas/AUX-filter approach when you do.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*
