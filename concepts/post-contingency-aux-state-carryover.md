---
type: concept
domain: tooling
aliases: [post-contingency-aux-file, post-contingency-solution-aux-file, ctg-reference-state-restore, linear-dc-ctg-carryover]
tags: [powerworld, contingency-analysis, aux, reference-state, linear-method, dc-power-flow]
---

# Post-contingency auxiliary file state carryover under linear/DC methods

## Abstract

Contingency Analysis has two auxiliary-file hooks that run custom aux/script content
per contingency instead of hand-writing every contingency's actions, and the reference-state
restore between contingencies behaves differently depending on which hook and which solve
method is active. Under a linear method or DC power flow, the second hook's state is **never
restored between contingencies at all** — any state change it makes, not just its intended
output, silently carries forward and contaminates every later contingency in the same batch
run.

## Connections

**Up:** [powerworld-simauto](powerworld-simauto.md) ·
**Across:** [aux-only-powerworld](aux-only-powerworld.md) (`SCRIPT{}` inline-statement mechanics these hooks reuse) ·
[esapp-script-command-wrappers](esapp-script-command-wrappers.md) ·
[builtin-distributed-computing](builtin-distributed-computing.md) (a batch CTG run driving
one of these hooks under linear/DC methods carries the same cross-contingency contamination
risk whether it's chunked serially or across the Distributed Computing add-on's workers) ·
**Deeper:** Simulator's *Contingency Analysis Options* manual chapter (Help menu)

## Content

### Two hook points, two timings

Configured under Contingency Analysis → Options → Modeling:

- **Post Contingency Auxiliary File** — loads *before* contingency actions are applied, per
  contingency (or with a per-contingency override if that contingency defines its own).
  File lookup order is the present working directory first, then the directory the loaded
  case came from.
- **Post Contingency Solution Auxiliary File** (added Version 20) — loads *after*
  contingency actions are applied and the power flow has solved, on every contingency, with
  no per-contingency override.

Either slot accepts inline script commands instead of a filename: a semicolon-separated
statement string behaves exactly like the contents of a `SCRIPT{}` block, no file on disk
required — a lighter path than a full aux file for short per-contingency logic.

### Reference-state restore only covers what the reference state tracks

Only data that is part of the contingency's reference-state snapshot gets reset when that
reference state is restored between contingencies. Loading arbitrary data through the Post
Contingency Auxiliary File that isn't part of that snapshot persists across contingencies
rather than resetting — which is why the intended use of this hook is to load only
reference-state data.

### The Solution Auxiliary File is riskier for the same reason, and worse under linear/DC

The Post Contingency Solution Auxiliary File carries the same non-reset risk, but under a
linear solve method or DC power flow, **the contingency reference state is never restored
between contingencies at all**. Any state change made while loading this file — not just
custom results — carries forward and contaminates every subsequent contingency in the same
batch run. The intended use of this hook is saving custom results only (e.g.
`SaveData`/`WriteAuxFile`-style export), never making state changes, precisely because there
is no automatic reset to catch a mistake when solving with linear/DC methods.

### What this means for a batch CTG driver

If a batch contingency run uses a linear method or DC power flow and drives a "solution aux
file" that does anything beyond exporting results, treat every contingency after the first
as suspect: a state change from contingency N can still be in effect when contingency N+1
solves. Keep this hook read-only (export/report actions only) under linear/DC solving, and
reserve state-changing actions for the Post Contingency Auxiliary File, which runs before
contingency actions apply rather than after.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*
