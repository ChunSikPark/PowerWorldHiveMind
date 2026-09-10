---
type: concept
domain: cross-cutting
aliases: [lodf, line-outage-distribution-factor, line-outage-distribution-factors, ptdf, isf, dc-contingency-screening]
tags: [contingency, n-1, dcpf, lodf, ptdf, powerworld, esapp, screening, technique, cross-cutting]
---

# LODF — Line Outage Distribution Factors (DC N-1 in one factorization)

## Abstract

LODF gives **every branch's post-outage MW flow for every single-branch outage** from one
matrix factorization — no per-contingency power-flow solve. It is not an approximation of
DC contingency analysis; measured live it **IS** DC contingency analysis
(`corr = 1.00000000`, `max|err| = 0.0000 MW` vs PowerWorld's own DC CTG), computed ~190×
faster. On Synth8k: the full 13,050-outage table in **5.8 s** versus **1,101 s** for the
10-worker parallel AC sweep ([parallel-contingency-solve](parallel-contingency-solve.md)). Read on for the mechanism, the
free islanding detector that falls out of it, what it structurally cannot do (voltage,
reactive power, losses, control limits, divergence), and the measured verdict that it was
**evaluated and NOT adopted** for reactive power planning — because RPP's binding
constraint is local reactive adequacy, not MW redistribution.

## Connections

- **Up:** [Home](../index.md)
- **Measured in:** a reactive planning study, 2026-08-10, in a LODF-versus-contingency
  comparison — **measured and rejected** for the removal-stage screen; see the verdict below.
- **💡 Could apply to (idea transfer):**
  real power planning — its 70-iteration DCPF conductor-resizing loop is a *pure MW*
  problem, which is exactly LODF's home ground: N-1 flows for every candidate resize with no
  extra solves ·
  dynamic line rating — the Impact×Likelihood branch screening needs post-outage loading,
  which is a LODF column ·
  critical branch screening — LODF is the natural engine underneath it ·
  grid statistics — an N-1-secure-by-construction check on synthetic cases (see below)
- **Across:** [parallel-contingency-solve](parallel-contingency-solve.md) (what you still need when the question is
  *voltage*, not MW) · [esapp](esapp.md) (topology + base flows come from here) ·
  [powerworld-simauto](powerworld-simauto.md) (the COM server; note the `SetData` / `dc_mode` traps below) ·
  centrality (both are topology-derived signals built from the network's own matrices)

## Content

### The idea

Contingency analysis **simulates**: open branch k, re-solve the whole network with
Newton-Raphson, read the result. LODF **precomputes the redistribution**.

It works because **DC power flow is linear** (`f = H·P` — angles and reactances only; no
voltage magnitude, no reactive power, no losses), and linear systems obey superposition.

The trick: instead of *removing* branch k, leave it in place and **inject power at its two
endpoints that exactly cancels its flow**. Electrically identical — a branch carrying zero
current may as well be absent. But an *injection* is something whose response you can
precompute once (that is what PTDF/ISF is). So knowing the response to injections gives you
the response to every outage.

### The formula

```
f_l(after k trips)  =  f_l  +  LODF[l,k] · f_k
                                └──────┘   └─┘
                                 share    orphaned flow
```

`LODF[l,k]` is the fraction of the **outaged** branch's flow that lands on branch `l` — not a
percentage increase of `l`'s own flow. Column `k` is the entire grid's response to losing
`k`, which is why one column answers "what happens everywhere."

**The danger is the product `LODF × f_k`, not the factor alone.** A 0.20 share of a 100 MW
line adds 20 MW; the same 0.20 share of a 400 MW line adds 80 MW. Same factor, opposite
verdict. LODF is also **signed** — always evaluate `|f_new| / limit`.

Where the shares come from:

```
LODF[l,k] = ψ[l,k] / (1 − ψ[k,k])          ψ = diag(b)·A·Xbus   (the ISF / PTDF matrix)
```

The denominator is a **feedback term**. When k's power pushes onto its neighbours, their
changes feed back onto k's own terminals, which pushes again. Expanded,
`1/(1−ψ_kk) = 1 + ψ_kk + ψ_kk² + …` — a geometric series summing every round of
redistribution in closed form.

### Free islanding detection (the part worth keeping regardless)

When `ψ_kk → 1` the denominator → 0 and the shares blow up. Physically: the feedback never
damps because **there is no alternate path** — outaging `k` splits the network. The math
flags it before any solve is attempted. On Synth8k: **420 of 13,470** outages, found in the
~6 s it takes to build the PTDF.

This is a **correctness fix, not a speed optimisation**, and it plugs a real hole: in a
PowerWorld CTG sweep, islanded buses read 0 and get skipped, so stranding a 138 kV pocket
**reports CLEAN**. A free connectivity check turns that silent failure into an explicit list.

### Building it (measured recipe, Synth8k: 8,483 buses / 13,470 branches)

```
A     = incidence (L×N, +1 from / −1 to)      b = 1/x, floor |x| at 1e-5
B'    = Aᵀ·diag(b)·A , delete the slack row/col, factorize (scipy splu)   ~6 s
Xbus  = B'⁻¹ (slack row/col zero-filled)
ψ     = diag(b)·A·Xbus                        (L×N = 0.91 GB float64)
Φ[:,k]= ψ[:,from_k] − ψ[:,to_k]               → LODF[:,k] = Φ[:,k] / (1 − Φ[k,k])
```

Φ is just **column differences of ψ** at the branch endpoints — cheap. Stream the L×L table
in column chunks (512 works) and accumulate statistics rather than materialising it (0.73 GB
in float32 if you do want it whole).

**Take base flows from PowerWorld's own DC solve — do not reconstruct the injection vector.**
On a real case, generation exceeds load by the AC loss provision (4,548 MW on Synth8k). A
hand-built `P` dumps that entire imbalance on the single slack bus while PowerWorld
distributes it, giving a **220 MW max discrepancy**. LODF needs only base flows + topology,
so reading the base flows removes the question. A DC solve is still shunt-blind, so the
property that makes this usable for siting work survives.

### Measured verdict (Synth8k, 2026-08-10)

**1 — LODF *is* DC contingency analysis, exactly.**

| | |
|---|---|
| LODF vs PowerWorld DC CTG | `corr = 1.00000000`, `max\|err\| = 0.0000 MW` |

Not "a good approximation" — within DC's linear world, "delete the branch and re-solve" and
"apply the compensating injection by superposition" are the *same algebraic operation*
(Sherman–Morrison). Same answer, far less arithmetic.

**2 — Cost.**

| Method | Full 13,050-outage sweep |
|---|---|
| **LODF** (+6.0 s PTDF, once per topology) | **5.8 s** |
| PowerWorld DC, serial | 2,106 s |
| PowerWorld AC, serial | 6,025 s |
| PowerWorld AC, 10-worker parallel | 1,101 s |

PTDF depends **only on topology**, so it is built once and reused: **each additional scenario
costs one matrix-vector product**, not another sweep. That is the property that answers
"more scenarios = linearly more time."

**3 — Rank fidelity vs AC is high, and the residual is DC's fault, not LODF's.**

```
per-substation stress, Spearman:   ρ(LODF, AC) = 0.9929
                                   ρ(PW_DC, AC) = 0.9929   ← identical to 4 dp
top-k set agreement (LODF vs AC):  top 5% J=0.936 · top 22% J=0.920 · top 50% J=0.955
```

LODF gives up **literally nothing** versus running the real DC sweep. The whole gap to AC is
the DC/AC modelling gap (base flows: `corr 0.981`, mean 5.5 MW, **8.5 % mean relative**).

**4 — Predicting individual AC flow *changes* is mediocre**, and again identical for both:

| mover threshold | 1 MW | 5 | 10 | 25 | 50 | 100 |
|---|---|---|---|---|---|---|
| `corr(ΔLODF, ΔAC)` | .6430 | .6493 | .6592 | .6990 | .7733 | .8492 |
| `corr(ΔPW-DC, ΔAC)` | .6430 | .6493 | .6592 | .6990 | .7733 | .8492 |

Good enough to **rank**; not good enough to read a post-contingency loading number off.

### UPDATE 2026-08-25 — the "does not compose" limitation is SOLVED in the literature

An earlier corridor-collapse study dropped LODF partly because *"single-row LODF does
not compose across simultaneous outages, and 209 corridors go out together."* **That is true for
chaining rank-1 updates one at a time — and that is not the only way to do it.**

**Ronellenfitsch, Manik, Hörsch, Brown, Witthaut, *"Dual theory of transmission line outages"*,
arXiv:1606.07276v2** (primary text verified 2026-08-25). Abstract:

> *"a new formula for the computation of Line Outage Distribution Factors (LODFs) is derived,
> which is not only computationally faster than existing methods, but also generalizes easily for
> multiple line outages and **arbitrary changes to line series reactance**."*

- **Eq. (28) — ARBITRARY REACTANCE CHANGE, not just outage.** For `x_ℓ -> x_ℓ + ξ_ℓ`:
  `ΔF = [ -ξ_ℓ F_ℓ / (1 + ξ_ℓ u_ℓᵀ M u_ℓ) ] · M u_ℓ`, with `M = C A⁻¹ Cᵀ`. Ordinary LODF is the
  `ξ→∞` limit (Eq. 29). The paper flags this generality for *"series compensation devices... or
  adjustable inductors"*. **A new parallel circuit is exactly this case**: two lines of `x` in
  parallel give `x/2`, i.e. `ξ = -x/2` — finite and negative.
- **Eq. (35) — M SIMULTANEOUS changes, JOINTLY:**
  `ΔF = -CA⁻¹Cᵀ U (𝟙 + Ξ UᵀMU)⁻¹ Ξ UᵀF`
  One **joint low-rank correction** via a single M×M inverse — NOT a sequential composition of M
  rank-1 updates, so **no accumulated chaining error**. Exact within DC linearity.

**Scope limits, precisely.** "Exact" removes the SEQUENTIAL-COMPOSITION error, not the DC
linearisation itself. The paper does NOT cover adding a corridor where no branch existed (that
needs the cycle basis extended, not a row perturbed). And **no literature was found** bounding a
linear pre-screen's error as a function of the NUMBER of simultaneous changes — so use it to
SHRINK a candidate list, then confirm the shortlist with a real solve.

**Where this lands:** the composition objection does not block LODF for
contingency remediation's DC subsystem. Its ~93 changes are all reactance perturbations on
EXISTING corridors (measured: 42 single-circuit, 3 double), and its 454 rating bumps do not touch
these matrices at all — a rating change moves no flow, only the limit you compare against. Both
reasons LODF was rejected for RPP also **invert** there: that case has 482 corridors over 100%
(worst 296%) rather than 2, and it is a DC study by design so DC's blindness costs it nothing.
See `RESEARCH-2026-08-25.md` in that repo.

### Why it was NOT adopted for RPP

Two independent reasons, both measured — neither is "LODF is inaccurate":

1. **No thermal headroom to discriminate on.** Across all outages, exactly **2 branches**
   exceed 100 % loading (max `1.000014`). TAMU synthetic grids are built N-1 thermally
   secure, so a correct detector runs on a grid engineered to have no positives. *(This is
   itself a reusable validation check for grid statistics: does a synthetic case's rating
   set actually satisfy N-1?)*
2. **N-1 barely moves the ranking.** `Spearman(base-case stress, full-N-1 stress) = 0.8893` —
   the contingency dimension mostly reproduces the base-case stress signal already computed.

And the structural reason it can never carry RPP's late stage: **LODF inherits all of DC's
blindness** — no voltage (every bus pinned at 1.0 pu), no reactive power, no losses, no
generator VAr limits / tap changes / switched-shunt action, and it can never return "did not
converge," which is sometimes the physically meaningful answer. RPP's real violations are
69/138 kV low-side buses sagging from a **local MVAr deficit**; exact MW bookkeeping cannot
see that. Voltage security still needs [parallel-contingency-solve](parallel-contingency-solve.md).

> **Open question, unresolved:** median *relative* error on movers is 100.0 % at **every**
> threshold for both LODF and PowerWorld DC — i.e. for the median branch that moves under AC,
> DC predicts no change at all — yet correlation reaches 0.85. Not explained. The AC re-solve
> jitter floor was also never measured (the case stopped solving after ~300 open/close
> cycles), so some small-mover "change" may be re-convergence noise.

### PowerWorld / esapp traps found while measuring this

Each cost real time; all measured 2026-08-10.

- **`pw.dc_mode` is effectively one-way.** Setting it `False` moves the case to AC; setting it
  `True` does **not** move it back, so every later "DC" solve silently stays AC. Use the
  explicit script commands and verify: `SolvePowerFlow(DC);` vs
  `SolvePowerFlow(POLARNEWT);`. **The only unambiguous test is that a real DC solve pins every
  bus to exactly 1.0 pu** — check it, don't trust the flag.
- **`Branch.LineStatus` is not settable through the bracket writer, and what that costs you
  depends on your esapp version.** esapp's schema marks it read-only (`Branch.is_settable`
  returns `False`). Through 0.1.x, `pw[Branch] = df` raised `Cannot set read-only field(s)`,
  which is what the 2026-08-10 runs above hit. **On 0.2.1 it only warns** — `UserWarning:
  Read-only field(s) on Branch: ['LineStatus']` — **and attempts the write regardless.** That
  is the more dangerous shape of the two: the warning scrolls past and you cannot tell from
  the call whether the status actually changed. See
  [esapp-script-command-wrappers](esapp-script-command-wrappers.md) for the change and for
  the `python -W error::UserWarning` mitigation that turns it back into a failure.

  Be explicit instead of relying on either behaviour:

  ```python
  pw.esa.SetData("Branch", ["BusNum", "BusNum:1", "LineCircuit", "LineStatus"],
                 [f, t, "ckt", "Open"])
  ```

  `SetData` is a typed wrapper in 0.2.1, so this obeys the call-the-named-method rule and is
  consistent with [powerworld-limitset-setdata](../methods/powerworld-limitset-setdata.md).
  `OpenBranch(...)` and `Open(...)` have no esapp wrapper at all and are reachable only as
  `RunScriptCommand` strings. **Assert the effect whichever route you take** — read the
  branch's status back, or check its flow went to zero. Never the absence of an exception.
- **`pw.lodf(branch)` exists in esapp but is per-branch** — 13k COM round-trips. Build the
  matrix yourself.
- **Always confirm the case solves before analysing it.** A freshly-opened `.pwb` returns
  plausible-looking `LineMW` from its *saved* state, so an analysis that never calls a solve
  will read sane numbers off an unsolvable case. A **DC solve is a linear system and cannot
  legitimately fail** — if it does, the case is broken, not the contingency.
- **Do not average error over the whole (branch × outage) table.** ~2 M entries are dominated
  by branches far from the outage that trivially do not move, which flatters any method to
  `mean |err| ≈ 0`. Measure error on the **flow change**, restricted to branches that actually
  moved, and against **each solver's own base** (mixing a DC base with an AC result folds the
  792 MW DC/AC gap into the thing being tested).
