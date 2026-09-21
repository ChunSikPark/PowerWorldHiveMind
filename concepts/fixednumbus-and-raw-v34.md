---
type: concept
domain: tooling
aliases: [fixednumbus, subnodenum, psse-full-topology, raw-v34, substation-node-bus]
tags: [powerworld, psse, raw, fixednumbus, subnodenum, substation, scripting]
---

# FixedNumBus and full-topology RAW (v34+)

## Abstract

RAW v34+ and other full-topology PSS/E-style models split each electrical bus into a substation-level
node structure, and PowerWorld's bus-numbering, ID-renaming, and validation rules around
`FixedNumBus`/`SubNodeNum` all follow from that split. An agent that assumes "bus number equals the
PSS/E bus number" or that IDs stay stable across a `FixedNumBus` assignment will get silently wrong
answers — the failures here don't raise exceptions, they log a message and move on.

## Connections

**Up:** [pw-manual-map](pw-manual-map.md) · **Across:** [raw-epc-roundtrip-traps](raw-epc-roundtrip-traps.md) · [pw-data-model](pw-data-model.md) ·
[case-restructuring-tools](case-restructuring-tools.md) (`RenumberBuses` operates on the plain
`BusNum` this page derives from `SubNodeNum`/`FixedNumBus` — renumbering one doesn't touch the
other) · [difference-case-tool](difference-case-tool.md) (a diff across a full-topology RAW
read/write can register `FixedNumBus`-driven ID renaming as a device change)

## Content

### PSSE_Bus vs. Node vs. PowerWorld Bus

Full-topology PSS/E models distinguish a **PSSE_Bus** (1–999999, which can represent multiple
electrical points — voltage phasors — if a substation is split internally by open switches) from a
**Node** (1–999, unique only within its substation). PowerWorld reads this into one `Bus` object per
node, synthesizing the PowerWorld bus number as:

```
BusNum = SubNodeNum * 1000000 + FixedNumBus
```

with a special case: when `SubNodeNum = 1`, the bus number is just `FixedNumBus`. Any code that
assumes the PowerWorld bus number equals the source PSS/E bus number will be wrong for every split
bus in the case — this is not an edge case on a post-2020 utility EMS export, where full-topology RAW
is increasingly the default.

### `FixedNumBus` grouping — silent rejection, not an exception

`FixedNumBus` is a grouping field on `Bus`; by default every bus points to itself. Before accepting a
`FixedNumBus` assignment, PowerWorld requires that **no branch connect two buses inside the same
grouping** — a violating assignment is rejected with only a message-log line, no exception raised. A
script that sets `FixedNumBus` and doesn't check the message log can believe an assignment succeeded
when it silently didn't.

### Assigning into a group cascades edits you didn't ask for

Assigning a bus into a `FixedNumBus` group forces `NomkV`/`Substation`/`Area`/`Zone`/`Owner` on that
bus to match the group, and **auto-renames** Load/Gen/Shunt/Branch 2-character ID strings to avoid
collisions with existing IDs elsewhere in the same group. A script relying on IDs staying stable
across a `FixedNumBus` assignment will see them change without being told.

### Object-identifier strings accept either form — except mixed on one branch

AUX files, `.con`/`.mon` files, and ObjectID strings accept either the real bus number or its
`FixedNumBus` interchangeably — `"Load 3002425 1"` and `"Load 2425 1"` can resolve to the same
device. The exception: for a **Branch**, if one terminal uses the `FixedNumBus` form, **the other
terminal must too** — mixing forms on the same branch string is invalid. This is a real trap for
hand-written AUX filters or contingency definitions built against a full-topology case.

### Collapsing back to a "regular" case

`File > Save Merged FixedNumBus Case` collapses split PSSE_Bus points into `FixedNumBus`-only
topology — useful for producing a non-full-topology export for tools or studies that don't need
node-level detail. Note it can *add* buses relative to what looks like a single grouping visually: if
a `FixedNumBus` group was electrically split by open devices, each split point needs its own voltage
phasor in the merged output, so "merged" doesn't always mean "fewer buses."

### Oneline display (lower priority for scripting)

`DisplayBus.AllowFixedNum` controls whether a oneline display object represents the terminal bus or
its `FixedNumBus` for auto-insertion/anchoring purposes. This is a GUI-only concern, relevant mainly
if you're generating onelines programmatically against full-topology cases.

### Practical checklist before scripting against a full-topology case

1. Don't assume `BusNum` matches the source PSS/E bus number — check `SubNodeNum` first.
2. After any `FixedNumBus` assignment, check the message log, not just the return value — rejection
   is silent otherwise.
3. Snapshot device IDs before a `FixedNumBus` assignment if your code depends on them, since
   collision-avoidance renaming can change them.
4. In hand-written AUX/CON/MON branch references, use the same numbering form (real or `FixedNumBus`)
   on both terminals.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*
