---
type: concept
domain: tooling
aliases: [equivalencing, network-reduction, bus-merge, bus-split, line-tap, bus-renumbering]
tags: [powerworld, equivalencing, bus-splitting, bus-merging, renumbering, edit-mode, case-editing]
---

# Case Restructuring Tools

## Abstract

Six Edit-Mode tools reshape a case's topology in place rather than reading or transplanting
devices between cases: equivalencing (shrink), merging/splitting a bus (collapse or divide a
node), tapping a line (insert a bus), and renumbering buses/areas/zones/substations. Each has
a silent-failure mode a script needs to know about — equivalencing permanently deletes what it
reduces, merging can silently drop a multi-section-line's grouping record, splitting fabricates
a fault-analysis impedance value out of nothing, and renumbering reads its target number from a
field you have to populate yourself.

## Connections

**Up:** [pw-power-flow](pw-power-flow.md) · **Across:** [case-to-case-device-transplant](case-to-case-device-transplant.md) · [case-impedance-completeness](case-impedance-completeness.md) ·
[topology-consolidation-and-derived-status](topology-consolidation-and-derived-status.md) (an
adjacent way a case's topology changes underneath a script — that page's remap is dynamic and
per-solve, this page's tools rewrite the case on disk) ·
[network-cut-and-query-tools](network-cut-and-query-tools.md) (shares the bus-selection
mechanism equivalencing uses to pick "which system") ·
[fixednumbus-and-raw-v34](fixednumbus-and-raw-v34.md) (renumbering here changes plain
`BusNum`; that page covers a second, RAW-driven numbering scheme layered on top) ·
**Deeper:** [references/aux-script-commands](../references/aux-script-commands.md)

## Content

### Equivalencing: a permanent, bus-by-bus reduction — not area/zone-by-area/zone

Equivalencing partitions the case bus-by-bus into a Study system (retained) and an External
system (reduced away), including a "tiers of neighbors" expansion and a network-cut-based way
to pick the boundary. Building the equivalent runs a Ybus matrix reduction and materializes the
result as new equivalent branches (by convention circuit ID 97/98/99/EQ) and equivalent shunts/
loads at the retained boundary buses.

**This permanently deletes the External system.** There is a non-destructive path — save the
External system to a file before deleting, so it can be reconstructed later via an append-case
operation — but it has to be taken deliberately; it is not the default behavior.

Two traps compound this:

- **Net-interchange imbalance lands on the slack bus** unless "Adjust Area Unspecified
  Interchange to Zero Out ACE" is explicitly checked when reducing an area with nonzero net
  interchange. Skip it and a reduced-order case built for repeated fast solves ends up with a
  slack bus absorbing an artifact of the reduction rather than a real imbalance.
- **Near-open-circuit equivalent branches are not dropped automatically.** "Max Per Unit
  Impedance for Equivalent Lines" has to be set explicitly, or the matrix reduction leaves the
  reduced case bloated with electrically meaningless near-infinite-impedance branches.

### Merging buses is not network reduction, and can silently drop grouping records

Merging two buses deletes the branches directly between them and reroutes everything else onto
the surviving bus — this is a distinct operation from equivalencing, meant for eliminating a
zero- or near-zero-impedance tie rather than for reducing a subsystem. A multi-section-line
record survives a merge only if **all four** hold: every merged bus belongs to the same
multi-section line, they're contiguous within it, at most one is a true terminal of that line,
and at least two sections remain afterward. Miss any one and the grouping record is silently
dropped even though the underlying devices remain in the case.

Merging from the oneline updates both the case and the oneline; merging from the bus grid
updates only the case, which can leave oneline display objects orphaned from their bus records.

### Splitting a bus fabricates a fault-impedance value, and always launches a follow-on step

Splitting a bus creates a new bus and, optionally, a near-zero-impedance tie (`0 + j0.0001` pu)
between old and new. If sequence data exists, the split recomputes it for both resulting buses
and assigns the new tie branch a **hardcoded** `j0.0001` zero-sequence impedance — a script
relying on fault-analysis results across a bus-split needs to know this value is synthetic, not
derived from anything physical. The split has its own multi-section-line survival logic,
symmetric to merging's.

Bus splitting always launches the Equipment Mover as its final step. A script driving a split
programmatically should expect to also need an explicit equipment-transfer step to move loads,
generators, or shunts onto the new bus — the split alone just creates an electrically-tied twin
bus with nothing assigned to it.

### Tapping a line: the shunt-charging treatment is a modeling choice, not a default

Tapping a transmission line splits its impedance by percentage-along-line. What happens to the
line's shunt charging (B/G) is a genuine modeling choice, not automatic: the default recomputes
a long-line PI-equivalent B/G for the two new segments (more accurate), or the alternative dumps
the entire original line's charging capacitance as lumped shunts at the two original terminal
buses and zeros B/G on the new segments. Which one was used changes the resulting case's
reactive balance at those buses — a script generating many taps (e.g., synthetic feeder
buildout) should choose deliberately rather than accept whatever the dialog last remembered.

### Renumbering reads its target from a field you populate first

`RenumberBuses`, `RenumberAreas`, `RenumberZones`, and `RenumberSubs` all take the new number
from each object's Custom Integer field, not from a direct parameter — a script must write that
field for every object to be renumbered, then invoke the renumber action. `RenumberCase` is
different: it executes a full pre-built swap list already held in memory. A number collision
surfaces as a dialog prompt in the GUI tool; the scripted equivalent's collision behavior should
be verified rather than assumed benign.

### Merge Line Terminals: which bus survives depends on multi-section-line position

Merge Line Terminals removes a line while preserving connectivity — the two terminal buses
become one — and is the mechanism for "delete this line but keep the topology connected," as
opposed to simply opening the line, which keeps the bus split. It takes a filter name or the
literal string `SELECTED`. The FROM bus survives as the merged bus **except** when the removed
line was the first or last segment of a multi-section line, in which case that line's own
terminal bus is kept instead — worth checking before assuming a fixed bus-numbering convention
downstream.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*
