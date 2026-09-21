---
type: concept
domain: cross-cutting
aliases: [shift-factor, gsf, generation-shift-factor, otdf, transfer-sensitivity, directions]
tags: [ptdf, shift-factor, otdf, sensitivities, powerworld, dcpf, cross-cutting]
---

# PTDF, Shift Factor, and OTDF — what transaction the number is actually modeling

## Abstract

`pw.ptdf()`/`pw.lodf()` call mechanics and the seller==buyer failure mode are covered in
[power-flow-and-sensitivities](../demos/power-flow-and-sensitivities.md); LODF as a
fast N-1 engine is covered in [lodf](lodf.md). Neither says what the *transaction* behind
a PTDF number represents, and the gap bites in three places: loss allocation between
seller and buyer is asymmetric, not symmetric; the transactor type (Bus vs Area/Zone vs
Injection Group) silently changes which generators can move; and an interface holding a
contingent element can report a PTDF that ignores the very outage you're studying unless
one non-default option is set. This page is about that transaction semantics — for the
outage-pairing and per-violation sensitivity tooling built on top of it, see
[contingency-linked-sensitivities](contingency-linked-sensitivities.md).

## Connections

**Up:** [Home](../index.md) · **Across:** [lodf](lodf.md) ·
[power-flow-and-sensitivities](../demos/power-flow-and-sensitivities.md) ·
[pw-injection-groups](pw-injection-groups.md) ·
[injection-group-participation](injection-group-participation.md) (how an Injection Group
transactor's own factors are defined and renormalized, underneath the transaction semantics
this page covers) ·
[contingency-linked-sensitivities](contingency-linked-sensitivities.md) ·
[glossary](glossary.md) · **Deeper:** [pw-power-flow](pw-power-flow.md)

## Content

### PTDF and Shift Factor are the same math, transposed

A PTDF run fixes one transaction (a seller and a buyer) and reports the sensitivity of
*every* monitored branch to it. A Shift Factor run fixes one monitored branch and reports
its sensitivity to *every* possible transaction, one transactor at a time against a
reference. A "Generation Shift Factor" is a Shift Factor run where the buyer side is
pinned to the system slack — no separate calculation, just one transactor fixed instead
of free.

### Loss allocation is asymmetric — do not assert MW balance from symmetry

The seller is modeled as injecting 100% of the transacted MW. The buyer absorbs the
transfer **minus** the resulting change in system losses. So the buyer's injection change
is not the negative of the seller's — the residual shows up as a "% Losses" field, and
that field can go negative (a transfer that *reduces* total losses gives the buyer more
than 100% of what the seller put in). Any check written as
`abs(seller_delta + buyer_delta) < tol` is wrong on its face; the correct check nets in
the reported loss term.

### The calculation method changes what "loss" even means, and can silently ride on `pw.dc_mode`

Three PTDF/Shift-Factor methods give different answers to the same request:

- **Linearized AC Approximation** — includes voltage/reactive effects and real losses,
  and exposes an "Increase in Losses" field.
- **Lossless DC Approximation** — pure angle-difference, no losses at all.
- **Lossless DC with Phase Shifters** — DC plus a constraint holding net flow across
  active phase shifters at zero.

Both Lossless variants read from the case's DC Power Flow Model options. That means the
`pw.dc_mode` one-way trap documented in [lodf](lodf.md) doesn't just affect the power-flow
solve — it silently changes which sensitivity method you're actually getting when you
asked for a Lossless one.

### Transactor type decides which generators can even move

Seller/Buyer aren't only buses — they can be Area, Zone, Super Area, Injection Group, or
the system Slack. Area/Zone/Super-Area transactions scale only AGC-eligible generators,
weighted by participation factor, so a dispatchable generator with `AGC=NO` is invisible
to the transaction even though it could physically respond. Injection Groups ignore AGC
status entirely and can include buses or loads with no generation attached — that's the
only way to force a transaction onto a specific generator or the load side, when an
Area/Zone transactor can't express it. See [pw-injection-groups](pw-injection-groups.md)
for how those groups and their participation factors are built.

### The interface blind spot: "Assumed Location of Injection for Bus"

When a monitored interface contains a contingent generator or load and the transactor is
a plain Bus, the default setting ("Always Bus") does not reflect that the generator or
load would be outaged — it silently understates the interface's exposure. Switching to
"Online Generator" / "Online Load" / "Online Gen or Load" fixes the modeling, but even
then the post-outage make-up-power model (carried over from contingency analysis' own
make-up-power setting) can leave a nonzero shift factor on the very element being
outaged. That's expected behavior, not a bug, but it looks wrong if you don't already
know the make-up-power setting is in play.

### OTDF: PTDF for an interface with a contingent element

`OTDFx = PTDFx + LODFx,y * PTDFy` — the outage transfer distribution factor for monitored
branch `x` given a single-branch outage `y`, combining a base PTDF with the LODF share of
the outage. `CTGCalculateOTDF` computes this directly, but it does not compute the PTDFs
it needs — it **reuses** whatever PTDFs were last calculated for the transfer direction of
interest. Run the PTDF dialog/script action first, and treat a stale PTDF calculation as
something that silently poisons every OTDF built from it afterward.

### Directions: scanning many transactor pairs at once

The "Directions" feature runs multi-pair PTDF in one pass — Area-to-Area, Zone-to-Zone,
Injection-Group-to-Injection-Group, or "X to Reference" (slack) — instead of hardcoding
one seller/buyer pair per script call. Useful for scanning all pairwise transfers rather
than looping a single-pair PTDF call yourself.

### Line Loading Replicator: the inverse problem, with its own gotcha

Given a target MW flow on one branch or interface, the Replicator back-computes which
generator/load injections within an Injection Group (respecting each member's Min/Max MW)
would achieve it, and can optionally apply the change and re-solve. It **ignores the
Injection Group's own participation factors** and solves its own optimal allocation
instead — don't expect it to honor a group's configured weighting. If group MW limits
bind, it reports a "Flow Achieved" short of the requested "Desired Flow" rather than
erroring.

### MW-Distance: a downstream consumer, with a length precondition

MW-Distance is built on top of an already-calculated PTDF and additionally needs branch
`Length` populated. Simulator can estimate missing lengths from an ohms/length table or a
load file, but only on request — either "Always Estimate Length" or "only fill unset
lengths."

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*
