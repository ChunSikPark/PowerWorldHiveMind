---
type: concept
domain: tooling
aliases: [required-fields, object-creation-gate, accidental-creation-guard, paste-import-fields]
tags: [powerworld, data-model, key-fields, silent-failure, csv-import]
---

# PowerWorld: required fields for object creation

## Abstract

Key fields identify a row; **required fields** are the separate, smaller set PowerWorld
demands before it will actually create a *new* object from a paste, an aux `INSERT`-style
block, or a CSV import. The gate exists on purpose, as a guard against a row full of key
fields accidentally fabricating an object nobody meant to create. Missing a required field
doesn't error — it skips the creation silently.

## Connections

**Up:** [pw-data-model](pw-data-model.md) · **Across:** [aux-only-powerworld](aux-only-powerworld.md) ·
[objectid-identification-traps](objectid-identification-traps.md) (the write-path counterpart
to this page's read-path gate — that page's malformed ObjectID resolves to the wrong existing
object, this page's missing required field silently skips creating a new one) ·
**Deeper:** [adding-devices-esapp](../methods/adding-devices-esapp.md) · [esapp-schema-reference](../references/esapp-schema-reference.md)

## Content

### Two separate gates, two separate failure modes

Loading a row through paste, aux, or CSV import checks two things in sequence:

1. **Key fields missing** → the row is ignored outright; PowerWorld can't identify any
   object, new or existing, without them. This is the same key-field write-back rule
   already covered for read-modify-write in [esapp-schema-reference](../references/esapp-schema-reference.md)
   and [aux-only-powerworld](aux-only-powerworld.md).
2. **Key fields present, but the object doesn't exist yet, and required fields are
   missing** → PowerWorld treats the row as referring to a record that isn't there, and
   silently declines to create it. Only once every required field also has a value does it
   create the new object.

### Why the gate exists: it's a guard, not a data-quality nicety

The manual's own example makes the intent explicit: an aux file sets `Monitor=YES/NO` on
every branch in a case. If that file also contains a line for a from/to/circuit tuple that
doesn't exist in the target case, no branch gets fabricated from it — because the required
fields (impedance and ratings) were never given, only the monitoring flag. The required-field
gate is what stops a maintenance script that's only supposed to *update* existing objects
from accidentally *creating* new ones when case data has drifted.

### Worked example: Branch

Key fields for a Branch are from-bus, to-bus, and circuit ID. Beyond those, the **required**
fields are R, X, B (impedance) and Ratings A/B/C. Supplying only the keys — even with other
non-required fields set — will not create a new branch; every required field needs a value
first. This matches the field list `adding-devices-esapp` already gives for actually driving
branch creation through `esapp`'s `CreateData`.

### Finding the current required-field set for any type

The required-field set can change between Simulator versions, so there's no static list
worth keeping here. The authoritative, always-current source is the same one already used
for key/enterable fields: `pw.esa.GetFieldList(<type>)` (see [esapp](esapp.md)), or, from
the GUI, Help menu → "Export Object Fields" (text or Excel), which dumps the key/required
table for every object type in the running Simulator version. In case-information column
headers and the Display/Column Options dialog, key fields are highlighted yellow and
required fields green — useful for a human debugging a failed load, not for code.

### A separate paste trap: redundant columns, second one wins

Distinct from required fields: pasting two enterable columns that represent the same
underlying value — bus per-unit voltage and bus kV, for instance — applies them in column
order, and whichever one is positioned second **silently overwrites** the first. There is
no error or warning; the outcome depends purely on column order in the pasted data.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*
