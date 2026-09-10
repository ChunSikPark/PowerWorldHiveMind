---
type: concept
domain: cross-cutting
aliases: [TSH, GenMCost, GenInertia, inertia constant]
tags: [powerworld, inertia, cost-curve, dynamics, gotcha]
---

# PowerWorld inertia (`TSH`) and cost (`GenMCost`) field semantics

## Abstract

Four non-obvious PowerWorld/esapp case-data facts, all discovered the hard way while
building a generator dispatch algorithm and worth knowing before any project touches
generator inertia or cost data: (1) `Gen.TSH` is H on a **100 MVA system base**, not
the generator's own `GenMVABase` — **and the "don't multiply by `GenMVABase`" rule that
follows from it inverts the moment you synthesize H yourself instead of reading it**
(this bit a second time on 2026-07-27; see the ⛔ box in §1 before writing any inertia
code); (2) `Gen.GenMCost` is a **live** cost-curve
evaluation at the case's *current* `GenMW`, not a fixed per-unit rate; (3) ERCOT's 8
weather zones are already modeled natively as `AreaNum`/`AreaName` on Synth2k-series
cases — no spatial join needed; (4) a sibling project's fuel-category *name* doesn't
always match its actual `GenFuelType` mapping — verify against source code, not the
label. Read the Content section before writing any code that sums inertia, ranks
generators by cost, needs zonal load data on a Synth2k case, or reconstructs
per-generator detail from another project's category-level summary.

## Connections
- **Up:** [Home](../index.md)
- **Across:** [esapp](esapp.md) · [powerworld-simauto](powerworld-simauto.md) ·
  [per-unit-basis-discipline](per-unit-basis-discipline.md) (the transferable rule)
- **Found in:** a generator dispatch study, where §1's original wording failed in practice
  and the fuel-mapping trap below cost a rebuild.

## Content

### 1. `Gen.TSH` (inertia constant H) is on a 100 MVA system base

`esapp` has no `GenInertia` attribute — inertia lives on the `Gen` object as `TSH`.
But `Gen.TSH`, read via `pw[Gen, ["TSH", "GenMVABase"]]`, is **not** the per-unit
inertia constant on the generator's own MVA base — it's H expressed on a fixed
**100 MVA system base**, a standard PSS/E-style dynamics convention. Confirmed two
independent ways on a real Synth2k case:

- **Round-number test:** converting via `H = TSH * 100 / GenMVABase` lands every
  nuclear unit and 19/21 coal units on exactly `4.00` seconds, squarely inside
  ERCOT's published Table 1 ranges (Nuclear 3.8–4.34s, Coal 2.9–4.5s) — not a
  coincidence at that precision.
- **Direct cross-check:** the case's own `MachineModel_GENROU` (round-rotor) and
  `MachineModel_GENSAL` (salient-pole, e.g. hydro) dynamic model objects expose a
  `TSH` field of their own, and it reads the true per-unit H **directly, no
  conversion needed** — e.g. `4.0` for the same generator whose `Gen.TSH` reads
  `56.888`. The ratio between the two paths is exactly `GenMVABase/100` for every
  unit tested, confirming the basis rather than just approximating it.

**Correct formula** for total system inertia (GW·s) over online synchronous units,
**when `TSH` is read from the case**:
```
GW·s = Σ(Gen.TSH) * 100 / 1000     # do NOT multiply by GenMVABase -- already implicit
```
Multiplying `TSH * GenMVABase` (the intuitive-looking but wrong formula) overstates
inertia by roughly `GenMVABase/100` per unit — ~13x too high for a ~1,400 MVA nuclear
unit.

> #### ⛔ The precondition on that rule — read before reusing the formula
>
> **"Do NOT multiply by `GenMVABase`" holds only because real `Gen.TSH` has already been
> multiplied by it.** That is a property of *the field*, not of inertia. If you are
> **synthesizing** H yourself — assumed values from ERCOT's Table 1, a textbook, or any
> per-machine source — H is on the **machine's own base** and you **MUST** multiply:
>
> ```python
> gens["H_assumed"] = gens["GenFuelType"].map(INERTIA_ASSUMED_BY_FUEL)
> gens["TSH"] = gens["H_assumed"] * gens["GenMVABase"] / 100.0   # re-base, THEN use the formula
> ```
>
> Writing assumed H straight into a column named `TSH` silently asserts every generator is
> 100 MVA. **This exact regression happened** on 2026-07-27, on a Synth8k
> case with *no* measured `TSH` — so all three notebook builders took the assumed-data path,
> which this page's original wording did not cover. Fleet inertia came out 240.5 GW·s
> instead of 470.3, nuclear 2.04 instead of 22.58; and because the error scales with machine
> size it was **non-uniform**, so unit *commitment order* was wrong too, not just totals.
>
> Physically: **H alone is not an inertia quantity.** ERCOT defines system inertia as
> `M_sys = Σ Hᵢ · MVAᵢ` — seconds must be weighted by machine size before they mean anything
> at system level. Corollary for any downstream analysis: **unit count is not a proxy for
> inertia**; many small machines can carry less than a few large ones.
>
> The general lesson — guidance inherits the preconditions of the data it was derived from —
> is [per-unit-basis-discipline](per-unit-basis-discipline.md).

`MachineModel_GENROU`/`GENSAL`'s own `TSH` is the more robust source (no
conversion arithmetic to get wrong) but only covers round-rotor + salient-pole units —
verify the two object types' record counts sum to the full synchronous fleet before
trusting it on a new case family.

### 2. `Gen.GenMCost` is a live evaluation at the case's *current* `GenMW`

`GenMCost` (marginal cost, $/MWh) is not a fixed per-unit number — it's PowerWorld
re-evaluating each generator's cost curve (`GenCostModel`, `GenCostCurvePoints`) at
whatever `GenMW` the case currently holds. Confirmed: `GenMW` correlates **0.95** with
`GenMCost` in a real case (marginal cost rises with output, as expected for a convex
cost curve).

**Consequence:** if you want to rank generators by cost *at a specific dispatch
point* (e.g. their `GenMWMin`, for a must-run/backstop step), reading `GenMCost` as-is
gives you cost at whatever the base case's *original* operating point was — which can
differ from the true value at your intended dispatch point by double digits of percent
(one tested unit: 6.37 → 5.56 $/MWh, a ~13% swing, when forced from its base-case
`GenMW` down to `GenMWMin`).

**Technique — live re-evaluation without saving:** temporarily overwrite `GenMW` for
the candidates via the bracket write interface, re-read `GenMCost`, then restore the
original `GenMW` — entirely in-memory against the live SimAuto session, nothing ever
written to the `.pwb`:
```python
orig = pw[Gen, ["BusNum", "GenID", "GenMW"]]
mw_at_target = orig["GenMW"].copy()
mw_at_target[mask] = target_values  # e.g. GenMWMin for the units you care about
pw[Gen, "GenMW"] = mw_at_target.tolist()

recomputed_cost = pw[Gen, ["BusNum", "GenID", "GenMCost"]]

pw[Gen, "GenMW"] = orig["GenMW"].tolist()  # restore -- verify max diff == 0.0
```
This generalizes to any PowerWorld field that's live-derived from `GenMW` (or other
mutable state) rather than stored directly — check for this before trusting a
"looks like a fixed property" field.

**Two silent-zero traps:** `GenCostCurvePoints == 0` means no cost curve was ever fit
(cost fields read `0`), and a handful of units can report `GenMCost == 0` even with
curve points defined. Both mean "no real cost data," never "free" — guard explicitly
(`GenCostCurvePoints > 0 AND GenMCost > 0`) before using cost data to rank or select
generators, or a data gap silently becomes "dispatch this first."

### 3. ERCOT's 8 weather zones are already `AreaNum`/`AreaName`

On Synth2k-series cases, `AreaNum`/`AreaName` (native PowerWorld fields, on both
`Gen` and `Load` objects) already encode ERCOT's 8 official weather zones — Far West,
North, West, South, North Central, South Central, Coast, East — verified present and
fully populated on both the summerpeak and low-load Synth2k cases. No spatial join
needed for zonal load/generation analysis on this case family.

Don't confuse this with the separate **ISO-region** field (`CustomString:2`, written
by a case-specific `iso_insertion.py` spatial join against an ISO-boundary shapefile)
— that field is (a) generator-scoped only, never written to loads, and (b) on the
Synth2k case, ~96%/~4%/~0.06% across three ISO regions — one bucket dominates, nearly
useless for zonal differentiation within ERCOT. `AreaNum` is the right key when the
goal is *intra-ERCOT* zonal granularity (e.g. matching a MIN-load case's zonal load
shape); ISO region is the right key only when the analysis genuinely needs
separation between ISO regions.

### 4. Another project's fuel-category name doesn't always mean what it says

Not a PowerWorld field-semantics gotcha but the same *don't-take-a-label-at-face-value*
family: a companion dispatch script's `"GAS_CT"` category actually maps to Synth8k's
`GenFuelType == "DFO (Distillate Fuel Oil)"`, not `"NG (Natural Gas)"` — confirmed by
reading the source's own fuel-classification code, not inferred from the name.
Conflating the two misassigns `TSH`/cost and mis-totals capacity. General lesson: when
reconstructing per-generator detail from another project's per-category summary
output, verify the category↔`GenFuelType` mapping against that project's actual
classification code, never the category's plain-English name.
