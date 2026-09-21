---
type: concept
domain: tooling
aliases: [island-display, breaker-isolated-groups, branches-that-create-islands, create-new-areas-for-islands, topological-diff]
tags: [powerworld, topology, islands, breakers, areas, contingency]
---

# Island and breaker grouping tools

## Abstract

Four PowerWorld tools compute island and breaker-boundary structure without needing the paid Integrated Topology Processing add-on — the free islanding detector documented in [lodf](lodf.md) is a DC-linear-algebra shortcut for one of the same questions these tools answer natively in Simulator. Two silent-failure traps sit inside them: an Area whose buses span more than one island gets AGC turned off with no error, and a case-to-case topology diff can flag pure bus-renumbering as a real topology change.

## Connections

**Up:** [pw-manual-map](pw-manual-map.md) · **Across:** [lodf](lodf.md) (the DC-linear-algebra islanding detector — this page covers Simulator-native island tooling instead) · [topology-consolidation-and-derived-status](topology-consolidation-and-derived-status.md) ·
[scheduled-actions-scripting](scheduled-actions-scripting.md) (shares the `Origin`/breaker-
identification taxonomy idea — that page's is per scheduled action, this page's Breaker
Isolated Groups is per bus) · **Deeper:** [pw-contingency](pw-contingency.md)

## Content

### Island Display — the cheap sanity check

An **Island** is an AC-connected group of buses; a DC line can bridge two islands without merging them into one, and every island needs its own slack bus. The Island Display (Model Explorer → Aggregations → Islands, run-mode only, read-only) lists per island: the slack bus, total bus count, an `Energized` flag, aggregate Gen/Load MW and Mvar, and scheduled exports. It's a cheap check that a case actually solved as one connected system — a scripted power-flow solve does not error out just because the case quietly split into multiple islands during a build or edit step.

This is a different tool from the LODF-based free islanding detector in [lodf](lodf.md): that one finds islands that would be *created by a single branch outage*, computed as a side effect of building the PTDF matrix for DC contingency screening. Island Display reports the islands that already exist in the *current* case state. Neither substitutes for the other.

### Create New Areas for Islands — the silent AGC trap

If an Area's buses span more than one island, PowerWorld has no way to know which island a scheduled interchange transaction should flow through, so it cannot perform AGC or area-interchange control for that area — and it **silently turns AGC off** for any area meeting this condition, with no error raised. A script that reassigns bus-area membership — during case building, a merge, or a topology edit — without checking the resulting island membership can disable AGC on an area and never see a warning.

### Branches that Create Islands — a rigorous replacement for eyeballing radial lines

This tool (Tools → Connections) enumerates every AC branch whose removal would split an existing island into two: genuine single-point-of-failure, radial branches. It has an option to suppress the trivial case of a branch that only islands a single bus. It does **not** require the ITP add-on, and it's a cheaper and more rigorous way to find these branches than visually scanning a oneline for lines that "look radial."

### Breaker Isolated Groups — approximate breaker detail without full node-breaker modeling

This buckets every bus by boundary crossings of three kinds: explicit breakers (`BranchDeviceType`=Breaker), **implicit breakers** (a per-bus flag meaning "treat every branch touching this bus as if it had a breaker, even though none is modeled" — a way to approximate breaker-level detail without building it out fully), and currently-open branches — or, if "Use Branch Normal Status for Groupings" is toggled on, branches whose `Normal Status` is Open rather than their current `Status`. Every bus ends up with a `Breaker Group Number`.

This grouping also drives **Auto Insert Contingencies → Bus grouping**, which generates contingencies per boundary-crossing type with different naming and action rules depending on whether a group's boundary is all-implicit, all-explicit, or mixed. That makes it a way to auto-generate realistic N-1-style contingencies from a case that only has partial — or purely implicit — breaker detail, again with no ITP add-on required. See [pw-contingency](pw-contingency.md) for contingency mechanics generally.

### Present Topological Differences from Base Case — the renumbering trap

This diffs two cases and reports New / Removed / Both-matched object counts per object type, with a Present/Base/Difference/Change display-mode toggle, and can export the diff as an executable AUX script. Prefer the modern "Complete Model" export over "Legacy Complete Model" — the legacy form is explicitly deprecated and can't filter by Area, Zone, Owner, or Data Maintainer.

Two traps matter directly for any case-to-case device-transplant workflow:

1. **Topology discrepancies between two cases are sometimes purely an artifact of different bus-numbering schemes, not real topology differences.** The tool ships a **Create Bus Swap List** helper specifically to resolve this — renumber one case to match the other's scheme before re-diffing, rather than reading a renumbering as a structural change.
2. **The AUX export has special-cased handling that naive field-by-field diffing would get wrong**: bus nominal-voltage changes on newly-added branches, area/zone/owner ownership changes where a device's own owner differs from its bus's changed owner (an explicit order-of-operations case), and three-winding-transformer star-bus renumbering when writing out "Both Elements" changes.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*
