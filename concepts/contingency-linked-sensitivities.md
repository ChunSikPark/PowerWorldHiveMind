---
type: concept
domain: cross-cutting
aliases: [lodf-screening, injection-sensitivities, contingency-sensitivity-analysis, iterated-linear-analysis, its-ots]
tags: [contingency, screening, lodf, remediation, sensitivities, powerworld, cross-cutting]
---

# Contingency-linked sensitivities — N-2 pre-screening, violation ranking, and where linear CTG lies to you

## Abstract

Four tools that sit on top of ordinary contingency analysis and single-branch LODF: a
batch N-2 pair pre-screen, a per-violation remediation ranking, an interactive
diagnostic that mutates the live case, and a mode that fixes a specific blind spot in
ordinary linear contingency analysis. None of these are in [lodf](lodf.md) or
[pw-contingency](pw-contingency.md), which cover single-outage LODF and the AC
contingency sweep respectively — this page is what sits between them. For transaction
semantics (PTDF/shift factor/OTDF), see [ptdf-shift-factor-otdf](ptdf-shift-factor-otdf.md).

## Connections

**Up:** [Home](../index.md) · **Across:** [lodf](lodf.md) ·
[pw-contingency](pw-contingency.md) · [ptdf-shift-factor-otdf](ptdf-shift-factor-otdf.md) ·
**Deeper:** [parallel-contingency-solve](parallel-contingency-solve.md)

## Content

### LODF Screening: builds N-2 candidate pairs, never solves them

LODF Screening turns single-outage LODFs into candidate N-2 (or N-k) contingency
**pairs** without ever solving the pairs — it's a pre-screen, not a result. Two pairing
methods produce structurally different pair sets from the same inputs:

- **ITS (Impact Tracking Structure)** — flags an outage as significant for a monitored
  line when `|LODF|` exceeds a threshold (minimum 1%), then pairs every significant
  outage for that line with every *other* significant outage for the same line. Pairs
  are "two things that both stress the same line."
- **OTS (Outage Tracking Structure)** — flags an outage significant when the *resulting
  percent loading* on the monitored line (from LODF/LCDF against the line's contingency
  limit) falls in a specified range, then pairs each significant outage with **all**
  other studied outages, not just other significant ones. Pairs are "one stressor paired
  with everything," and the set is much larger than ITS's for the same inputs.

The screening dialog can only emit results **by writing an aux file**
(`LODFScreening.aux` by default) — there's no in-memory contingency-set return value, so
the generated pairs have to be re-imported to actually run them.

The islanding sentinel from [lodf](lodf.md) applies here too: contingencies whose outage
would island the network report the `1e8` sentinel LODF value, and the screening dialog's
"Include Contingencies Creating Islands" toggle, if left on without downstream filtering,
seeds nonsense pairs into the aux file the same way an unfiltered single-outage sweep
does.

### Injection Sensitivities: ranks remediation candidates per violation

This is a Contingency Analysis option, not a standalone tool — it attaches shift-factor
or MW-effect rankings to every violation found during a contingency run, for automated
remediation logic. "Keep Highest Sensitivities" ranks generators/loads by shift-factor
magnitude toward relieving the violated element. "Keep Highest MW Effect" instead ranks
by *achievable* MW change given each injector's actual headroom — for generators that's
Max/Min MW; for loads, headroom is present-load-down-to-zero only, and the load's own
Min/Max MW fields are read but ignored. A remediation script that ranks by shift factor
alone, without checking headroom, can propose a generator that has no MW range left to
move. This is the tool the contested corpus anchor
(`22-contingency-analysis-options.md#injection-sensitivities`) belongs to.

### Contingency Sensitivity Analysis: interactive and stateful, not a batch call

Selecting this for a specific violation **actually applies that contingency to the
in-memory case** — case state changes and stays changed until the reference state is
explicitly restored or another contingency is selected. Driving this via SimAuto means
the script must restore the reference case itself afterward, or every subsequent read
reflects a contingency-perturbed case. It's also gated: only available under Full-AC
contingency runs (not under any Linearized/DC method), and only for branch/interface
violations, never bus violations.

### Iterated Linear Analysis: fixes a blind spot in ordinary linear CTG

Ordinary linear (LODF/shift-factor) contingency analysis evaluates every conditional
action in a contingency against the **pre-contingency reference state**, not the state
after earlier actions in the same contingency. So a contingency with sequential or
conditional actions — e.g. "if branch X's post-outage flow exceeds a threshold, then
also open branch Y" — can be linearly wrong unless Iterated mode is on. Turning it on
requires `Iterate on Action Status`, a Linearized calculation method, and the power flow
itself set to AC. It's strictly slower than the non-iterated linear path, and Simulator
only actually iterates a contingency when a conditional field is "handled" for
iteration — an unhandled field silently falls back to reference-state evaluation with no
error. The manual's own "Verify Contingencies for Iterated Linear Analysis" self-check is
the only way to find out which fields in a given contingency set are silently unhandled.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*
