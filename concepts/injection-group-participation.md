---
type: concept
domain: tooling
aliases: [participation-factor, parfac, autocalc, injection-group-normalization]
tags: [powerworld, injection-group, participation-factor, autocalc, normalization]
---

# Injection group participation mechanics

## Abstract

A generator's raw participation factor is almost never the number that actually gets used —
every time an injection group is consumed, its factors are silently renormalized over
whatever subset of members the calling tool considers eligible. A group that "looks" like a
70/30 split can distribute 100/0 in one tool and 70/30 in another, with no error either way.
This page is the mechanism behind the routing page at [pw-injection-groups](pw-injection-groups.md):
how a factor is defined per element type, how normalization and exclusion work, and how
`AutoCalc` decides whether the stored number is live or frozen.

## Connections

**Up:** [pw-injection-groups](pw-injection-groups.md) · **Across:**
[ptdf-shift-factor-otdf](ptdf-shift-factor-otdf.md) (how a PTDF/Shift-Factor transaction
consumes an injection group as a transactor — that page covers the transfer-sensitivity
angle, this one covers the group's own factor math) ·
[applying-a-dispatch-to-a-case](../methods/applying-a-dispatch-to-a-case.md) (writing a
dispatch directly by key field, without going through a participation-factor scaling tool
at all) ·
[generator-dispatch-and-diagnostics](generator-dispatch-and-diagnostics.md) (its merit-order
dispatch algorithms are one of the consumers that renormalizes this page's factors) ·
[interface-elements-and-monitoring](interface-elements-and-monitoring.md) (an injection group
can itself be composed into an interface's monitored flow) · **Deeper:** [pw-power-flow](pw-power-flow.md)

## Content

### Every use renormalizes, and exclusion happens first

An injection group is a named list of participation points — generators, loads, switched
shunts, buses, or nested injection groups — each carrying its own participation factor.
Whenever a tool (Scaling, PV/QV ramping, ATC, Time Step scaling, Island-Based AGC,
Injection Group Area Slack, or a linear sensitivity run) actually consumes the group, it
does two things before touching a single MW: it drops the points that tool considers
ineligible, then renormalizes the survivors' factors to sum to 100%. Reading the raw
stored factors and assuming that's the effective split skips both steps and gets the
answer wrong with no warning.

Exclusion rules that matter:

- A generator not on AGC, or already sitting at a min/max limit, drops out.
- Bus participation points are excluded from every tool that actually moves the system —
  Scaling, PV ramping, ATC's iterated methods, Time Step scaling, Island-Based AGC, and
  Injection Group Area Slack all ignore them. They only count in linear sensitivity tools
  and in ATC's Single Linear Step method. The same group definition therefore behaves
  differently depending on which tool is pointed at it — there's no single "the group's
  effective split," only "the split for this consumer."

### AutoCalc decides whether the factor is live or frozen

Each point's `ParFac` is either a fixed number (`AutoCalc = NO`, directly editable) or a
formula re-evaluated from an `AutoCalc Method` every time the point is used
(`AutoCalc = YES`). The available methods depend on element type:

| Element type | Methods |
|---|---|
| Generator | `SPECIFIED` (constant) · `MAX GEN INC` (max minus present output, floored at 0) · `MAX GEN DEC` (present minus min output, floored at 0) · `MAX GEN MW` (= max output) · Field/Model Expression |
| Load | `SPECIFIED` · `LOAD MW` (= load size) · Field/Model Expression |
| Switched shunt | `SPECIFIED` · `MAX SHUNT INC` · `MAX SHUNT DEC` · `MAX SHUNT MVAR` · Field/Model Expression |
| Nested injection group | `SPECIFIED` or Field/Model Expression only |
| Bus | Field/Model Expression only — no `SPECIFIED` |

This is what makes an injection group portable across cases on purpose: an aux file built
with `MAX GEN INC` re-derives each generator's factor from whatever reserve exists in the
case it's loaded into, rather than carrying over a number computed against a different
dispatch. A reusable transfer template relies on this; a one-off group meant to reproduce
one exact split should use `SPECIFIED` instead, or it will quietly reweight itself on a
different case. One more trap: **toggling the `AutoCalc Method` recomputes `ParFac`
immediately**, regardless of whether `AutoCalc` itself is YES or NO — changing the method
alone mutates the stored factor even on a "frozen" point.

### Auto-insert and PTI import have their own silent drops

Auto-inserting injection groups (by Area, Zone, Super Area, Owner, or a custom field)
processes one element type at a time — generators, loads, or shunts never mix within a
single pass — and a custom-field grouping silently skips any element whose field is blank.

Importing a PTI subsystem (`.sub`) file hits the same ambiguity from a different angle:
a participation-point bus with both load and generation, or with neither, either prompts
per-subsystem or, by configured default, splits the point equally across every device at
the bus (all generators regardless of online status, all loads regardless of connection
status) or fabricates a dummy 0 MW/0 Mvar load (ID `'99'`) to hang the point on. A script
reading an imported group's points should not assume they map cleanly back to the source
subsystem's intent.

### Rollup display fields are a different, coarser number

The Injection Group Display's `% MW Gen ParFac`, `% MW Load ParFac`, `% Mvar Load ParFac`,
and `% Mvar Shunt ParFac` fields describe the group's coarse generation-vs-load and
load-vs-shunt split — computed on top of the per-point normalization above, not a
substitute for it. Don't read these as the per-point factors.

### Nesting a group inside a group

A nested injection group can be included two ways, and they behave differently: as a
single point of type `INJECTIONGROUP` (it follows its own normalization when consumed), or
via "Include Individual Group Points" (the member points are copied in directly, with a
chosen participation-factor source). A script assembling group definitions programmatically
needs to pick one deliberately rather than treating them as equivalent.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*
