---
type: concept
domain: tooling
aliases: [integrated-topology-processing, itp, superbus-consolidation, derived-status, full-topology-model, primary-bus]
tags: [powerworld, topology, breakers, superbus, derived-status, key-fields, contingency]
---

# Topology consolidation and derived status

## Abstract

A full-topology (node-breaker) case cannot be solved directly — breaker impedances sit orders of magnitude away from real line reactances and wreck the Jacobian. PowerWorld's Integrated Topology Processing (ITP) works around this by silently remapping every device onto a single representative bus per closed-switching group before every solve, then mapping back after. That remap changes which `BusNum` a device reports, on every solve, and `Status` stops meaning "energized." Anything that reads a device's key fields or trusts `Status` in a breaker-modeled case is reading a moving target.

## Connections

**Up:** [pw-manual-map](pw-manual-map.md) · **Across:** [pw-data-model](pw-data-model.md) (key-field write-back rule) · [pw-contingency](pw-contingency.md) (breaker-to-device contingency conversion) · [glossary](glossary.md) ("Super bus") ·
[case-restructuring-tools](case-restructuring-tools.md) (a different, permanent way a case's
topology changes, versus this page's dynamic per-solve remap) ·
[network-cut-and-query-tools](network-cut-and-query-tools.md) (Facility Analysis's connectivity
graph sits one layer below the Superbus/Subnet grouping this page describes) ·
[objectid-identification-traps](objectid-identification-traps.md) (a second, unrelated way an
object's identity silently resolves wrong — there from a malformed ObjectID string, here from
a stale `BusNum` read across a topology change) ·
**Deeper:** [island-and-breaker-grouping](island-and-breaker-grouping.md)

## Content

### The problem consolidation solves

A node-breaker (full-topology) model represents breakers and disconnects as real branches with near-zero impedance. Solved as-is, those branches sit many orders of magnitude away from a transmission line's reactance, which produces an **ill-conditioned Jacobian** — the power flow won't converge, and the failure looks like a generic solver problem rather than a topology setting. ITP avoids this entirely: before each power flow, sensitivity, or contingency solve, it groups buses connected by *currently closed* switching devices into a **Superbus**, temporarily moves every device's connection pointer onto one **Primary Bus** per superbus, solves the reduced network, then de-consolidates results back onto the original devices. Nothing is converted or rewritten in the case file — this happens in memory, every solve, and reverses itself afterward.

A **Subnet** is the static version of the same grouping: buses joined by switching devices regardless of open/closed state. Subnets only change when equipment is physically added or removed. Superbuses are dynamic — they merge and split as breaker status changes, and each superbus belongs to exactly one subnet. Code that assumes bus grouping is stable across a contingency is implicitly assuming subnet structure; if it's actually reading superbus structure, a single breaker flip changes the grouping out from under it.

### What decides the Primary Bus — and what that means for `BusNum`

Primary Bus selection runs an 18-tier priority list: the slack bus wins outright; then multi-terminal DC terminals, generator-regulated bus, switched-shunt-regulated bus, LTC-regulated bus, DC terminal, generator terminal, switched-shunt terminal, load terminal; then a run of branch-type tiers from series-capacitor terminals down to ground-disconnect terminals at the bottom. Ties break on lowest bus number, and a per-bus `Topology\Node Priority` field can override the automatic ranking.

**The consequence that matters for automation:** with ITP consolidation active, a `BusNum` read off a device is not necessarily the bus it is physically wired to — it's whichever bus won the priority contest for that device's current superbus. Superbuses are recomputed at the start of every solve, so the winning bus can change the moment any breaker in the group changes status. A DataFrame of device rows captured before a topology change, then written back after one, is keying against buses that may no longer be the ones a live read would return — the write can silently land on the wrong object, or on nothing, and still report success. This is the same failure mode the kit's key-field rule describes (see [pw-data-model](pw-data-model.md)), except here the *trigger* is a topology change rather than an omitted column: **re-read key fields after any breaker status change or topology-processing event, and never carry a device DataFrame across one.**

### `Status` lies; `Derived Status` is the real answer

In a full-topology model, `Status` on a non-switching device (generator, load, line, transformer) typically just reflects whether the device itself is set `Closed`, independent of whether a path of closed breakers actually connects it to anything energized. The field that answers the real question is **Derived Status**: it traces outward from the device's terminals across closed branches looking for a closed breaker path to a generator (or, since a later version, other energization sources), returning `Closed`, `Open To`, `Open From`, or `Open` (immediately `Open` if `Status` itself is `Open`). `Derived Online` folds the `Online` field into the same traversal.

**The derivation rule itself changed between manual versions 19 and 20** — version 20 treats a discovered load or switched shunt as sufficient for energization in more cases, and excludes breakers that sit strictly in series with switched shunts, generators, or loads from the traversal (so opening a line doesn't accidentally read as tripping a radially-tapped shunt or load's own breaker). Check which version's rule produced a Derived Status value before trusting one computed on an older case export — the same case can yield a different answer depending on which version wrote it.

### What consolidation can and can't eliminate

A branch is only a consolidation candidate if `AllowConsolidation`=YES and its `Branch Device Type` is one of Breaker, Load Break Disconnect, Disconnect, ZBR, or Fuse (Ground Disconnect also qualifies). Even then, it survives un-consolidated if it's an area tie line, touches a multi-terminal DC converter, participates in a Model Condition, Model Expression, post-power-flow action, or transient-stability event, is part of a contingency action not using incremental processing, or is an interface branch not in series with a non-consolidatable device (interfaces instead auto-retarget to whatever device is in series). A switching device wired in direct parallel with a non-switching device — a series-capacitor bypass breaker is the canonical example — is deliberately excluded too, so consolidation never silently deletes the series cap from the effective model.

### Saving a consolidated case as a Planning Case is one-way and lossy

Ordinary Planning Cases — what `esapp`/aux automation normally assumes — use `BusNum` as the sole key with no switching devices at all. Full-Topology Models are structurally different: breakers and disconnects are modeled as real objects. Saving a consolidated full-topology model out as a Planning Case collapses that structure permanently, with choices that change the result: **Open Non-Energized Branches** (treats a line with an unenergized terminal as open), **Convert Shunts to Blocks** (aggregates multiple per-bus shunts, since planning formats generally allow only one), and a choice between discarding contingencies (smallest resulting file) or preserving them (which requires retaining every breaker any contingency touches).

**Run Breaker-to-Device Contingency Conversion before this save.** Skipping it leaves saved contingencies carrying raw breaker-open actions on a case that no longer models those breakers as distinct objects — a case that downstream tooling, and any script expecting device-level contingency actions (`OPEN LINE`, `OPEN GEN`, etc.), generally can't handle. The conversion (Contingency Analysis dialog → Other → Convert to Device Contingencies) is documented further, alongside contingency mechanics generally, in [pw-contingency](pw-contingency.md); some breaker contingencies can't be fully reduced and keep a residual `Breaker` action alongside the converted device action in the same contingency.

### The "Use Consolidation" checkbox, and getting it backward

Checking "Use Consolidation" is correct for a real full-topology case and simply irrelevant on an ordinary planning case with no switching devices. Getting it backward — leaving it unchecked on a genuine full-topology case — forces the solver onto the raw near-zero-impedance branches directly, which is exactly the ill-conditioned-Jacobian failure described above. The failure mode gives no hint that a topology-processing checkbox is the cause; it looks like an ordinary convergence problem.

### Contingency analysis has two consolidation modes with different failure surfaces

**Preserve All Breakers Included in Contingencies** consolidates once up front and reuses that result for every contingency in the run — simpler, but the effective case stays larger, and a run with a high volume of breaker-touching contingencies can itself produce ill-conditioning. **Incremental Topology Processing** instead re-processes only the affected Subnets per contingency, on the order of milliseconds, and is the manual's preferred mode for throughput. The tradeoff that matters for tool selection: **incremental mode cannot be used by anything that needs a fixed-size bus array for linearization** — sensitivity analysis is the example, and ATC automatically falls back to Preserve-Breakers mode for exactly this reason. A script that assumes ITP settings apply uniformly across every analysis tool in a case will hit this silently.

### Primary Bus Mapping is not one crosswalk

The Power Flow solution, Contingency Analysis, and a Saved Consolidated Case can each preserve a different set of breakers, and therefore each produces its own, potentially different, superbus-to-bus mapping. All three are separately viewable and exportable (as an aux file) from the Topology Processing Dialog's Primary Bus Mapping tab. This matters whenever results computed at a primary bus need to be posted back onto the original per-device topology — use the mapping produced by the specific tool that generated the result, not one borrowed from another tool's run.

### "Open with Breakers" has a hard cutoff and a version-dependent exclusion

Used by contingency actions, and separately available standalone via "Open Breakers to Isolate" (no ITP add-on required for the standalone use), this traverses outward from a device's terminals flagging closed breakers to open. It **aborts entirely, doing nothing,** if isolating the device would require passing more than 10 online-generation buses, logging that the device cannot be isolated from online generation — a hard limit, not a warning. It also drops any flagged breaker whose both terminal buses ended up already visited, since opening it would isolate nothing. Since version 20, breakers and disconnects purely in series with switched shunts (and, per a later patch, also generators and loads) are excluded from the switching set, so opening a line doesn't inadvertently trip a radially-tapped shunt's, generator's, or load's own breaker as a side effect.

### A related but separate grouping: ZBRBus

Distinct from Superbus and Subnet, PowerWorld also tracks **ZBRBus groups** — buses joined by branches under a configurable zero-impedance-branch threshold set in Power Flow Solution Advanced Options. These drive the **Find Parallel AC Branches** tool, which flags branch groups running between the same two ZBRBus groups. One real defect pattern it surfaces: parallel transformers with **conflicting From/To tap orientation** — the software allows this, it is essentially never physically real, and it's a strong signal of bad input data, since a transformer's variable tap is always modeled on the FROM side.

### One more bus-grouping concept, not covered here

A later manual version introduces `FixedNumBus`, a fourth user-defined bus-grouping concept alongside Bus/Superbus/Subnet, described as an extension of the Superbus/Subnet mechanism above. It isn't covered by this page — flagged here as the likely next stop after Superbus/Subnet.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*
