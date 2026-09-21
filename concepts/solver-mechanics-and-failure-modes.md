---
type: concept
domain: tooling
aliases: [solver-loops, red-green-blue-loops, island-slack-selection, angle-smoothing, dc-solve-trap]
tags: [powerworld, manual, power-flow, solver, convergence, dc-power-flow, islands]
---

# PowerWorld: solver mechanics and failure modes

## Abstract

The nested loop structure PowerWorld runs on every AC solve, the options that change
convergence without erroring, and the deterministic algorithm behind island slack
selection. Read it when a case won't converge, converges to an unexpected answer, or when
writing code that catches or interprets solve failures.

## Connections

**Up:** [pw-power-flow](pw-power-flow.md) · **Corpus:** [powerworld-help-corpus](powerworld-help-corpus.md)

**Across:** [buscat-and-voltage-control](buscat-and-voltage-control.md) · [shunt-transformer-dfacts-control](shunt-transformer-dfacts-control.md) · [generator-dispatch-and-diagnostics](generator-dispatch-and-diagnostics.md)

**Deeper:** [glossary](glossary.md)

## Content

### Three nested loops, always in this order

- **Power Flow (Inner) / Red** — solves the Newton-Raphson matrix equations only.
- **Controller (Middle) / Green** — checks and applies generator Mvar limits, DC line
  solution, switched shunt control, and LTC/phase-shifter/D-FACTS movement, then re-solves
  Red.
- **MW Control (Outer) / Blue** — area or island AGC redispatch, then re-runs Green and Red.

The message log color-codes which loop produced each line, and that coloring is the primary
tool for diagnosing a non-convergent case — presently undocumented anywhere else in this kit.

### The DC solve reports zero mismatch even when the schedule is wrong

The kit's [glossary](glossary.md) already flags that a DC solve always reports zero
mismatch, because it is lossless by construction and carries no Q at all. What that entry
doesn't say: `Compensate for Losses by Adjusting the Load` exists specifically to paper over
this by inflating load artificially, and it is **off by default** — so a case can be solving
"clean" while its generation schedule is genuinely short or long. Separately, DC power flow
has an unresolved modeling ambiguity baked into an option: "ignore series resistance" vs
"ignore series conductance" produce different B values for the same line data, and PowerWorld
defaults to ignoring resistance.

### Mvar-limit check timing changes which solution you land on

`Check Immediately` vs `Check Back Off Immediately` (the latter is the default and
recommended setting since v20, with an added asymmetric behavior from the v23 patch)
controls whether generator Mvar-limit hits and releases are checked inside every inner-loop
iteration, or only between outer passes. Getting this backwards is a known cause of spurious
convergence to a bad high- or low-voltage solution — worth checking before tuning solver
options on a stubborn case.

### Optimal multiplier abort is itself a diagnostic

`Disable Power Flow Optimal Multiplier` controls the mechanism that stops Newton's method
from diverging on a bad step. When the multiplier shrinks toward zero, PowerWorld aborts
rather than let mismatches blow up — that abort is a signal the case is heading toward
non-convergence, worth surfacing in any code that catches solve failures rather than treating
it as a generic error.

### Angle smoothing and tap balancing act without saying so, unless you read the log

Angle Smoothing activates automatically whenever a branch reconnects across a large angle
gap, to avoid inner-loop divergence, and can misbehave when many electrically-close branches
close together in the same pass — it logs a line when it fires, but nothing else surfaces it.

Parallel-transformer tap balancing uses 4x the ZBR Threshold (see
[buscat-and-voltage-control](buscat-and-voltage-control.md)) as its own impedance criterion
for deciding which transformers must agree, and will silently switch a transformer off
automatic control — logging only a message — if parallel transformers don't regulate a
consistent bus group.

### Island creation and slack selection is a strict, deterministic order

1. Build islands from closed AC branches only — DC ties do not count for grouping.
2. Within an island, pick the user-designated `Slack=YES` bus if exactly one exists.
3. Otherwise pick by `SlackPriority`, then by five further tie-break criteria in strict order.
4. An island with no load, no DC tie, and only one bus is discarded as non-viable.

Debugging "why did PowerWorld choose bus X as slack" requires this order; nothing else in the
kit states it.

`Evaluate Power Flow Solution for Each Island` (v20+) matters for multi-island cases: without
it, one non-converging island fails the solve for the **entire** case, even when the rest of
a large system is fine — an easy gotcha with cases carrying small disconnected fragments.

### Load voltage-dependence (ZIP) is a real equation behind opaque fields

The kit's schema exposes load voltage-dependence only as raw fields
(`LoadSMW` and the implicit IMW/ZMW percentages — see
[esapp-schema-reference](../references/esapp-schema-reference.md)) with no equation. The
actual model is `MW = mult * (S + I*V + Z*V^2)`, and below a configurable minimum per-unit
voltage (default 0.5 for constant-current, 0.7 for constant-power) load rolls off smoothly to
zero rather than diverging. This interacts directly with low-voltage and blackout debugging
and is invisible without knowing the formula.

### Post-solution actions run automatically and can be recursive

A script-triggered action list with CHECK/ALWAYS/NEVER/POSTCHECK status runs after every AC
solve, and POSTCHECK actions can trigger further POSTCHECK actions recursively. A case can be
taking actions after every solve that inspecting only the base case data would never reveal —
worth checking before assuming a case's post-solve state matches what was saved.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*
