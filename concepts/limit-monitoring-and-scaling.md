---
type: concept
domain: tooling
aliases: [limit-monitoring, monitor-flag, limit-group, agc-scaling, scale-to-ace, merit-order-dispatch]
tags: [powerworld, limits, monitoring, scaling, dispatch, contingency, violations]
---

# Limit Monitoring and Scaling

## Abstract

Why does an obviously-overloaded branch never show up in `overloads()`, contingency analysis,
ATC, or OPF? Reporting a violation is gated by a chain of flags upstream of the device's own
rating, and any single link being wrong makes the device invisible to every consumer at once —
not just one tool. Scaling load or generation to a target level has the same shape of trap:
the dispatch method and starting-point choice change *which* result you get, not just how fast
you get there, and one AGC-filtering option silently strands the remainder on the slack bus
instead of redistributing it.

## Connections

**Up:** [pw-power-flow](pw-power-flow.md) · **Across:** [methods/reading-violationctg](../methods/reading-violationctg.md) · [methods/powerworld-limitset-setdata](../methods/powerworld-limitset-setdata.md) · [methods/ranking-new-devices-by-severity](../methods/ranking-new-devices-by-severity.md) ·
[weather-dependent-limits](weather-dependent-limits.md) (a different way a device's effective
rating can silently go stale or wrong before this page's gate chain ever sees it) ·
[generator-dispatch-and-diagnostics](generator-dispatch-and-diagnostics.md) (its two
merit-order algorithms overlap, but aren't identical to, this page's four scaling dispatch
methods) · [interface-elements-and-monitoring](interface-elements-and-monitoring.md) (an
unrated auto-inserted interface silently defaulting its limit to 0 is the interface-object
analogue of this page's monitor-gate chain) ·
**Deeper:** [references/aux-script-commands](../references/aux-script-commands.md)

## Content

### The four-gate chain that decides whether a device is even eligible to be reported

A device's limit is enforced and reported only if **all four** of these hold at once:

1. the device's own `Monitor` field is YES
2. its assigned Limit Group is not Disabled
3. its Area has area-level limit reporting enabled, and the device's kV falls inside that
   area's reporting kV range
4. the same reporting check passes at the Zone level

Any one of these being wrong makes the device invisible to `overloads()`, contingency
analysis, ATC, OPF, and PV/QV alike — because they all read from the same upstream gate, not
from independent logic. This is a different, earlier mechanism than the per-violation limit
override read in [methods/reading-violationctg](../methods/reading-violationctg.md); that page
covers the `ViolationCTG` record once a violation has already been reported, not whether it
gets reported at all. A case assembled or edited programmatically (synthetic-grid generation,
transplanting a device from another case) can easily leave a new device's Area/Zone reporting
settings unset, or its Limit Group Disabled, and silently stop monitoring an entire area — not
just the one device. Debugging "why doesn't this clearly-overloaded branch show up" means
checking all four gates, not just the branch's own flag.

### A Limit Group also indirects which rating actually applies

A device's own rating fields aren't necessarily "the" limit. Each Limit Group selects, from up
to 15 (line) / 8 (bus) / 4 (bus-pair) predefined rating sets, which one is used for normal-state
reporting and which for contingency reporting. Reading a device's nominal rating field without
first checking which rating set its Limit Group currently points to can silently read the wrong
number.

### MVA% and Amp% disagree by design, and DC solves only ever report one of them

`Amp% = MVA% / (per-unit voltage at the limiting bus)`. The two percentages are not the same
number, and a Limit Group's "Treat Line Limits as Equivalent Amps" toggle controls which one a
given group reports — this is intentional, not a bug. A script comparing loading percentages
across a Limit Group boundary can legitimately see two different numbers for what is physically
the same constraint. **DC power flow and DC contingency solves always report line limits in
MVA and ignore this toggle entirely** — code that branches on "Amps vs MVA" mode without also
checking whether the case is currently in DC mode will misread the units.

### Two different meanings of "radial," easy to conflate

"Do not monitor radial lines and buses" is a live, simple single-line-in/out rule, and it is
ignored entirely when Integrated Topology Processing is active. "Branches that Create Islands"
is a separate, coarser N-1 radial/tree-forming detector. A device can be structurally radial by
one definition and not the other, especially on a case with parallel circuits — the two names
sound interchangeable and aren't.

### Scaling silently follows the device's own Area/Zone, not its bus's

Scaling by Area, Zone, or Owner uses the device's *own* area/zone assignment — a generator or
load can carry an area or zone different from the bus it sits on. "Scale by Bus→Area" and
"Scale by Area" therefore pick up genuinely different device sets on such a case. This is the
same area-vs-bus mismatch already known from PTDF/shift-factor semantics, recurring here in a
different tool.

### Injection-group scaling: the starting point changes the answer, not just the path

Scaling an Injection Group offers **Scale from Present Value** (adds an incremental delta,
split by participation factor) versus **Scale from Zero** (re-splits the entire new total by
participation factor from scratch). These only agree when the starting shares already equal
the participation factors — otherwise they're different answers, not different routes to the
same one. `Scale from Zero` additionally only works one injection group at a time.

### Four dispatch methods, four structurally different results

- **Proportional** — a normalized participation-factor split.
- **Merit Order** — fills each element to its MW limit, in participation-factor rank order,
  before touching the next element. This is a bang-bang allocation, not a smooth one, and it
  always enforces generator MW limits regardless of whether "Enforce Gen MW Limits" is checked.
- **Economic Merit Order** and **Merit Order Close** — cost-based dispatch, structurally
  different again from rank-order Merit Order.

Picking a method is picking a physical story, not a speed/precision tradeoff — "scale up load
and re-dispatch generation" needs the method matched to the intended story rather than left at
the Proportional default.

### The AGC-filtering trap: shares computed from everyone, moved by only some

"Ignore AGC flag to calculate participation but use AGC flag to scale individual loads/
generators" computes participation shares from **all** elements, AGC-eligible or not, but then
only actually moves the AGC-eligible ones. The remainder that a non-AGC element "should" have
taken is not redistributed to the AGC-eligible set — it is silently absorbed elsewhere,
ultimately by the slack bus. This is a different, narrower option than "Scale Only AGCable
Generation and Load," which excludes non-AGC elements from the participation calculation
itself rather than just from the move.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*
