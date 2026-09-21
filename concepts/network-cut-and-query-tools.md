---
type: concept
domain: tooling
aliases: [network-cut, facility-analysis, min-cut, max-flow, graph-flow, shortest-path, radial-bus-paths]
tags: [powerworld, network-cut, facility-analysis, max-flow, min-cut, shortest-path, topology, edit-mode]
---

# Network Cut and Topological Query Tools

## Abstract

Four tools answer different topological questions but share underlying primitives that are
easy to conflate: a Network Cut is a manually-chosen boundary (the same bus-selection mechanism
scaling and equivalencing use to pick "which system"), Facility Analysis is an actual min-cut
computation over a pure connectivity graph (not power flow), Radial Bus Paths and Shortest
Path/Set-Bus-Field share one distance-measure abstraction that silently clamps negative field
values, and none of these verify a definition is complete before running — an ill-defined
boundary just fails to bisect the system rather than erroring up front.

## Connections

**Up:** [pw-power-flow](pw-power-flow.md) · **Across:** [limit-monitoring-and-scaling](limit-monitoring-and-scaling.md) · [case-restructuring-tools](case-restructuring-tools.md) · **Deeper:** [references/aux-script-commands](../references/aux-script-commands.md)

## Content

### A Network Cut is a manual boundary that isn't verified for completeness

A Network Cut is a manually-chosen set of branches, interfaces, and DC lines that is supposed
to form a topologically complete separation of the system. The tool does not verify closure
beyond failing on an obviously ill-defined attempt — a partial cut plane silently fails to
bisect the system rather than erroring at definition time. Once a valid cut exists, a reference
bus on one side selects which side is "of interest," and an optional "tiers of neighbors"
parameter extends inclusion across the boundary. This is the same selection primitive that
underlies both scaling's "select buses using a network cut" option and equivalencing's "which
system" bus assignment described in [limit-monitoring-and-scaling](limit-monitoring-and-scaling.md)
and [case-restructuring-tools](case-restructuring-tools.md) — one mechanism, multiple consumers.

### Facility Analysis is an actual min-cut, not "the branches you'd guess"

Facility Analysis takes an explicit Facility bus set and External bus set (via the same
bus-selection mechanism equivalencing uses) and computes the **minimum number of branches**
whose removal electrically isolates one from the other — a real max-flow/min-cut computation
via an augmenting-path algorithm, with every branch treated as unit capacity and each named
group collapsed into a single supernode. It runs only in Edit Mode, respects present open/
closed branch status (open branches are treated as absent), and reports an incomplete graph
structure if a bus is assigned to both sets at once.

**"Graph Flow" here is a pure connectivity abstraction, not power flow** — every branch gets
capacity 1 regardless of its real electrical rating, purely to make the isolation problem
solvable as max-flow/min-cut. A Facility Analysis "capacity" number should never be read as an
MW/MVA capacity.

### Radial Bus Paths: two toggles can change the reported radial group drastically

Find Radial Bus Paths has a Bus-vs-SuperBus traversal mode and a parallel-branch policy, and
both change which buses and branches get reported as radial — sometimes drastically, with the
same topology reporting different path lengths purely depending on these two settings. A script
consuming the radial-path result fields must fix both options deliberately; the same underlying
topology does not yield one canonical radial grouping.

### Shortest Path and Set-Bus-Field share a distance measure that silently clamps negative values

Shortest Path Between Buses and Set Bus Field From Closest Bus share one distance-measure
abstraction — reactance, impedance magnitude, the `Length` field, unweighted hop count ("Number
of Nodes"), or any other numeric branch field — and one branch-traversal filter (`All`, `Only
Closed`, an advanced `Meets Filter`, and for Set-Bus-Field also `Selected`). **Negative field
values are silently clamped to "extremely small" rather than rejected** — a distance
computation built on a field that happens to carry negative entries (a signed custom field, for
example) will be distorted with no warning.

### Unused Bus Numbers writes to a file, not to memory

`Unused Bus Numbers` only writes its result to a text file — there is no in-session query that
returns "N free bus numbers" directly. A script that needs new bus numbers (a synthetic-grid
generator inserting substations, for example) has to either read this exported file or compute
unused numbers itself from the existing bus list, and should not expect a script-command form
that returns numbers as a value.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*
