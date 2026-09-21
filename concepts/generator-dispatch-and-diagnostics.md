---
type: concept
domain: tooling
aliases: [area-agc, economic-merit-order-dispatch, voltage-conditioning, island-based-agc, circulating-flows]
tags: [powerworld, manual, power-flow, agc, dispatch, diagnostics, voltage-conditioning]
---

# PowerWorld: generator dispatch methods and diagnostic tools

## Abstract

The 6 ways Area AGC can redispatch generation to meet ACE, the two merit-order dispatch
algorithms used across PV/QV/ATC/scaling tools, the Voltage Conditioning tool's actual
multi-solve mechanism, and the diagnostic displays for debugging a solved case. Read it
before scripting a dispatch scan or wondering why generator setpoints changed after running a
tool that doesn't mention generators in its name.

## Connections

**Up:** [pw-power-flow](pw-power-flow.md) · **Corpus:** [powerworld-help-corpus](powerworld-help-corpus.md)

**Across:** [buscat-and-voltage-control](buscat-and-voltage-control.md) · [solver-mechanics-and-failure-modes](solver-mechanics-and-failure-modes.md) · [pw-pv-qv](pw-pv-qv.md) ·
[injection-group-participation](injection-group-participation.md) (the merit-order algorithms
here are one of the "calling tools" that page's participation-factor renormalization talks
about) · [limit-monitoring-and-scaling](limit-monitoring-and-scaling.md) (that page's four
dispatch methods for scaling overlap this page's two merit-order algorithms but are not the
same list)

**Deeper:** [pw-injection-groups](pw-injection-groups.md)

## Content

### Area AGC has 6 modes

- **No control** — all mismatch is dumped onto the slack bus.
- **Participation Factor** — ACE is split across AGC generators by participation factor;
  it only fires when the system actually changes, not continuously.
- **Economic Dispatch** — drives all AGC generators' incremental cost to equality; needs
  real cost curves or the result is meaningless.
- **Area Slack Bus** — only the slack absorbs ACE; the manual itself flags this as unreliable
  for large disturbances.
- **Injection Group Area Slack.**
- **OPF.**

Island-based AGC is a separate dispatch axis (by island rather than by area), with its own 4
sub-modes, including a two-level "Calculate Participation Factors from Area Make Up Power
Values" mode that computes an area-level factor and then a generator-level factor within it.
The Governor Power Flow dialog exposes this same island-based AGC control, just under a
different framing — same mechanism, no separate write-up needed.

### Voltage Conditioning moves generators and shunts permanently, not just for one solve

The kit's [pw-power-flow](pw-power-flow.md) page already flags Voltage Conditioning as a
trap because its name mentions neither generators nor shunts. Here is the mechanism: it
temporarily forces every eligible generator (`ConditioningAvailable=YES`) onto AVR at a
computed voltage target found by a breadth-first search from the generator terminal out to
the nearest transmission-level bus (using `TransmissionNomkV` and
`StopSearchImpedanceThresh` to know where to stop), re-solves, then iteratively steps
switched shunts one block at a time — tracking an oscillation counter that locks a shunt out
after 3 direction reversals — until no further shunt move helps. It finally restores each
generator's original AVR/RegBus/VoltSetTol settings, but with a **new** `VoltSet` computed
from wherever the generator ended up. Net effect: this tool changes generator setpoints and
shunt positions permanently. Code driving it needs to treat it as a multi-solve iterative
process, not a single call.

### Two merit-order dispatch algorithms give different intermediate points

Both are used by PV/QV curves, Scaling, ATC, and time-step injection-group scaling:

- **Merit Order Close Dispatch** fully commits each generator to its economic MW limit, in
  ranked order, before touching the next.
- **Economic Merit Order Dispatch** instead keeps all active generators at the same relative
  point within their economic MW range, simultaneously.

For the same total MW target these produce very different intermediate dispatch points —
relevant to anything scripting a scan across transfer or injection levels. Both can silently
open or close generator breakers to energize or de-energize units, restricted to breakers
that solely energize the target device.

### Diagnostic tools worth knowing by name

- **Find Circulating MW/Mvar Flows** — detects loop flows caused by mismatched parallel
  transformer taps or phase shifts, ranked by estimated loss reduction.
- **Bus Mismatches Display** — shows the `BusCat`/`Type` string per bus; see
  [buscat-and-voltage-control](buscat-and-voltage-control.md) for what the values mean.
- **Remotely Regulated Bus Display** — shows aggregate Mvar min/max/actual and the list of
  regulating devices for any remotely-controlled bus.
- **Long Line Voltage Profile** — a 100-point per-unit voltage profile along a line's length,
  needed because terminal-bus voltages can hide much higher or lower midpoint voltages on
  lines with large charging susceptance.
- **Saving Admittance Matrix and Jacobian Information** — exports Ybus/Jacobian to
  MATLAB-format text for external research code; rectangular vs polar Jacobian form is a
  user choice that changes what the exported file means.

### Reactive capability curves make static Mvar limits stale

A generator with `UseCapCurve=YES` has a piecewise-linear Mvar-vs-MW envelope (up to 50
points) that changes `MvarMax`/`MvarMin` dynamically with MW output. Code that reads the
static `MvarMax`/`MvarMin` fields (see
[esapp-schema-reference](../references/esapp-schema-reference.md)) without checking
`UseCapCurve` first will get stale limits for any generator carrying a capability curve.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*
