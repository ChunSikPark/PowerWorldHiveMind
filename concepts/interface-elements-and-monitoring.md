---
type: concept
domain: tooling
aliases: [interface-elements, monitor-direction, nomogram-mechanics, flowgate-mechanics]
tags: [powerworld, interface, nomogram, flowgate, monitoring, aux-script]
---

# Interface element types and monitoring mechanics

## Abstract

An interface's reported flow depends on two independent direction settings and on which
element types were used to build it — get either wrong and the number is still real, it
just measures something other than what the caller thinks it measures. An unrated
auto-inserted interface doesn't error either; its limit silently defaults to 0. This page
is the mechanism behind the routing page at [pw-interfaces](pw-interfaces.md): the
aux-script element-type syntax, how sign and direction compose, what the contingency-aware
fields mean, and how nomograms build on top of a plain interface.

## Connections

**Up:** [pw-interfaces](pw-interfaces.md) · **Across:**
[ptdf-shift-factor-otdf](ptdf-shift-factor-otdf.md) (the interface as the *monitored*
branch/element in a PTDF or OTDF calculation — that page covers the transaction math, this
one covers the interface object itself) ·
[injection-group-participation](injection-group-participation.md) (an injection group can
itself be one of the elements composed into an interface) · **Deeper:**
[pw-power-flow](pw-power-flow.md)

## Content

### What can go into an interface, and the aux-script tokens for each

An interface aggregates flow across a mix of element types in one object: AC/DC branches,
inter-area ties, inter-zone ties, generators, loads, injection groups, multi-section lines,
other interfaces (nested), and contingency actions. The aux-file tokens are exact and
load-bearing for hand-written or generated scripts:

| Token | Meaning |
|---|---|
| `BRANCH num1 num2 ckt` | Monitor MW flow from bus `num1` to `num2`; the bus order sets the sign convention |
| `AREA num1 num2` / `ZONE num1 num2` | Sum of AC branches tying the two areas/zones |
| `BRANCHOPEN` / `BRANCHCLOSE num1 num2 ckt` | Monitor the interface as if this branch were opened/closed — a contingency-conditioned member, not a static one |
| `DCLINE num1 num2 ckt` | DC line flow |
| `INJECTIONGROUP 'name'` | Net injection — generation positive, load negative |
| `GEN num1 id` | Positive injection |
| `LOAD num1 id` | Negative injection |
| `MSLINE num1 num2 ckt` | Multi-section line flow |
| `INTERFACE 'name'` | Nest another interface's flow into this one |
| `GENOPEN` / `LOADOPEN num1 id` | Contingency-conditioned generator/load closing (added Simulator v20, Jan 2018) |

### Two independent direction settings compose

Sign is set per element, not just per interface. For a branch, transformer, or DC-line
element, flow is measured near-bus → far-bus, positive in that direction; which bus counts
as "near" is a choice made when the element is added. A separate **Monitor Flow at To End**
toggle picks which end's flow *magnitude* is reported for that element — relevant when the
two ends disagree because of losses or shunts.

On top of that, the interface as a whole carries its own **Monitor Direction** (From→To or
To→From) plus a **Monitor Both** toggle that overrides it. That's two settings that both
affect the sign of the number coming back — a script reading interface flow needs to know
which end and which overall direction it's getting, not just the raw magnitude.

### Contingency-aware fields bake in a hypothetical outage

- `Has Contingency` — YES if any member element sits at a device limit.
- `Base MW Flow` — the pre-contingency flow.
- `Contingent MW Flow` — the flow that *would be added* if the interface's own defined
  contingency occurred.
- `Interface MW` = Base + Contingent.

`Interface MW` is not the live flow — it already includes a hypothetical contingency
addition. Reading it as "the current flow" overstates what's actually flowing right now.

### Limits: up to eight, and which set is active matters

Interfaces support up to eight limits (`Lim MW A/B/C` in the display, the same scheme used
for lines and transformers), and which one is the *effective* limit depends on the case's
Limits tab / Line-Transformer Limit Violations settings. An interface's MW limit is not a
single static number independent of that configuration.

### Auto-insertion is restricted to adjacency, and silently under-limits

Bulk auto-insertion only works for area-to-area or zone-to-zone interfaces that share at
least one tie line; a single bus-to-bus interface has to be built through the line-insertion
options instead. Auto-inserted interfaces default to overwriting any existing interface with
the same name unless "Delete Existing Interfaces" is unchecked. If no rating source is
selected during auto-insertion, the new interface's limit silently defaults to 0 — read
downstream as "no limit," not as an error.

### Nomograms: a convex boundary between two interfaces

A nomogram pairs exactly two interfaces and defines an allowed joint-flow region as a
convex piecewise-linear boundary, built from ordered breakpoints (each one a flow pair on
Interface A and Interface B). The breakpoints must be entered in the order that keeps the
boundary convex. A script generating nomogram breakpoints programmatically has to preserve
that ordering/convexity constraint itself — nothing in the object enforces it after the
fact, and a wrong order produces a limit shape that doesn't match the intended region.

### Percent reads as zero, not undefined, on an unrated interface

The oneline-drawing `Interface Field Information` / `Interface Pie Chart Information`
objects are cosmetic (rotation, sparkline toggle, anchoring), with one exception worth
keeping: the `Percent` field is defined as exactly 0 whenever the MW rating is 0, so a
pie-chart or field read on an unrated interface comes back as a clean zero instead of
`NaN` or an error.

### NERC flowgates are interfaces, not a separate object

Loading or saving NERC flowgates (Excel, requires a NERC-supplied login) is a thin wrapper
around interface records — the interface *is* PowerWorld's flowgate model. There is no
separate flowgate object to reconcile against.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*
