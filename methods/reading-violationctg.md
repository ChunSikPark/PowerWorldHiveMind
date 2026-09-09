---
type: method
domain: tooling
aliases: [violationctg, per-contingency-violations, limviolcat, limviolpct, areanum-tie-line, branch-amp]
tags: [esapp, powerworld, simauto, contingency, violations, limitset, n-1, synth2k]
---

# Reading Per-Contingency Violations (`ViolationCTG`)

## Abstract

How to get **which contingency caused which violation** out of PowerWorld — thermal, voltage
and interface, keyed by `CTGLabel` — by reading the `ViolationCTG` object after
`CTGSolveAll()`. This is the only read path that gives per-contingency attribution from a
single solve; the per-bus envelope (`BusMin/MaxVoltageContingency`) collapses everything to
one worst case and cannot say *which* outage did it.

Five traps, each of which produces a **plausible wrong answer rather than an error**. The
first four were live-measured on `Synth2k_case` on 2026-08-16; the
fifth only appears on a case Synth2k cannot produce, which is the point of it:

1. **`AreaNum` is the branch's OWN area and reads `0` on a tie-line.** Filtering on it
   silently drops every cross-area violation. The endpoint areas are `AreaNum:1` / `:2`.
2. **`LimViolPct` polarity is three-way, not two-way.** `Bus Low Volts` is a violation
   where *lower* pct is worse; `Bus High Volts` inverts. One sort key ranks one of them
   backwards.
3. **Results persist in the `.pwb`** and read back fine with no solve at all. 148 stale
   rows came out of a freshly-opened case.
4. **A bare `pw[ViolationCTG]` returns 2 columns.** You must pass an explicit field list.
5. **The `LimViolCat` vocabulary is case-dependent, not fixed.** An amp-rated branch
   reports `Branch Amp`, which Synth2k never emits — so a classifier measured there drops
   every one of those overloads as an unknown category and still completes, still writes
   plausible CSVs, and still reports a grid it never screened.

Also settled here: the claim in `contingency_esapp.py`'s module docstring that esapp's typed
read of `ViolationCTG` errors *"interface unknown"* on Synth2k **does not reproduce**.

## Connections

- **Up:** [esapp](../concepts/esapp.md) · esapp package
- **Across:** [new-device-contingency-aux](new-device-contingency-aux.md) (building the set you solve, and scoping
  monitoring to an area) · [powerworld-limitset-setdata](powerworld-limitset-setdata.md) · [parallel-contingency-solve](../concepts/parallel-contingency-solve.md) · [lodf](../concepts/lodf.md) ·
  [powerworld-simauto](../concepts/powerworld-simauto.md) · reactive power planning · critical branch screening
- **Deeper:** [esapp-package-backend](../references/esapp-package-backend.md) · reactive power planning backend

## Content

### The read

```python
from esapp.components import ViolationCTG

VIOLATION_FIELDS = [
    "CTGLabel", "LimViolCat", "LimViolValue", "LimViolLimit", "LimViolPct",
    "AreaNum", "AreaNum:1", "AreaNum:2", "BusNum", "BusNum:1", "BusNum:2",
    "LineCircuit", "CTGViol", "CTGNVoltViol", "LimViolID",
]

pw.esa.SetData("Sim_Solution_Options", ["DCApprox"], ["NO"])
pw.esa.SetData("CTG_Options", ["CTG_CalculationMethod"], ["AC"])
pw.esa.SolvePowerFlow()
pw.esa.CTGClearAllResults()          # MANDATORY -- see trap 3
pw.esa.CTGSolveAll()

violations = pw[ViolationCTG, VIOLATION_FIELDS]
```

**Field spelling is `AreaNum:1`, with a colon.** `ViolationCTG.fields()` has 394 entries and
none of them use a `__1` double-underscore form. There is no `ObjectString` field on
`ContingencyElement` either, despite what you may have been told.

### `LimViolCat` — the vocabulary

| `LimViolCat` | means | first seen on |
|---|---|---|
| `Branch MVA` | thermal overload, branch rated in MVA | Synth2k |
| `Branch Amp` | thermal overload, branch rated in **amps** | planning model |
| `Bus Low Volts` | undervoltage | Synth2k |
| `Bus High Volts` | overvoltage | Synth2k |
| `Interface MW` | interface flow (Synth2k carries weather-zone interfaces natively) | Synth2k |
| `Unsolved` | pseudo-row for a contingency that did not solve — a divergence, **not** a violation | planning model |

The original four were observed by squeezing both bands on Synth2k until every category had
to appear, with the note *"treat this as a vocabulary to fail loudly against, not an
exhaustive enum."* **That note was right, and ignoring it cost a wrong answer.** Synth2k
rates every branch in MVA, so `Branch Amp` was never seen there; a real utility planning
model rates part of its system in amps and PowerWorld emits **both strings from the same
solve**, on disjoint sets of branches. See
2026 08 22 branch amp thermal rows discarded — 2,972 real overloads on a planning model
(101.7%–240.7% of rating, all 297 contingencies) were classified `unknown` and dropped
while the run reported 18 violations and looked clean.

Two rules follow, and they are not the same rule:

- **`Branch Amp` is thermal.** Score it off `LimViolPct` exactly as `Branch MVA` — percent
  is percent regardless of the rating's unit, so the two never need an exchange rate. But
  `LimViolValue` / `LimViolLimit` on those rows **are amps** (284–2,176 A on that model) and
  must never be compared against an MVA row's.
- **`Unsolved` is not.** It is `CTGSolved = NO` arriving through the violation table.
  Ranking it as a violation scores a contingency the run established *nothing* about.

Before trusting a thermal count on a new case, check what the case rates in:
`LimitSet.LSAmpMVA` says which, and `LSEndMonitor` says which end.

### Trap 1 — `AreaNum` is the branch's own area, and it is `0` on a tie-line

This is the expensive one. The four `AreaNum` slots are not four copies of the same thing:

| slot | meaning |
|---|---|
| `AreaNum` | the **object's own** area — `0` when a branch spans two areas |
| `AreaNum:1` | the FROM-bus's area |
| `AreaNum:2` | the TO-bus's area |
| `AreaNum:3` | tracked `AreaNum:1` on every observed row |

Measured on branch 1004 (Far West) → 3133 (West):
`AreaNum=0, AreaNum:1=1, AreaNum:2=3, AreaNum:3=1`.

On an intra-area branch all four read the same number, which is exactly why this is easy to
miss — you have to look at a tie-line to see the difference at all. **1,933 of 36,122
thermal rows** on the observed run were tie-lines, i.e. `AreaNum == 0`.

> **A region filter written as `AreaNum in R` drops every tie-line violation and looks
> completely correct while doing it.** The safe rule is to join `BusNum` / `BusNum:1` to
> the `Bus` table and use those areas; keep `AreaNum:1` / `:2` only as a cross-check.

### Trap 2 — `LimViolPct` polarity is three-way

| category | value vs limit | worse means | observed pct range |
|---|---|---|---|
| `Branch MVA` | above | **higher** pct | >100 |
| `Bus Low Volts` | below (6,385/6,385 rows) | **lower** pct | 94.06 – 100 |
| `Bus High Volts` | above (7,956/7,956 rows) | **higher** pct | 100 – 102.97 |

So a `{thermal, voltage}` two-way split ranks over-voltages backwards. Rank **thermal on
`LimViolPct`** (percent of its own rating is what makes differently-rated branches
comparable) and **voltage on the signed pu deviation** from `LimViolValue`. Per-bus rate
sets (`LSCtgBusLowRateSet` / `LSCtgBusHighRateSet`) also mean `LimViolLimit` need not be
constant across rows, so percent is not comparable bus-to-bus either.

`LimViolValue == LimViolLimit * LimViolPct / 100` held on **120,428 of 120,428 rows** — so
the typed value is trustworthy, and the arithmetic is a good cross-check assertion.

### Trap 3 — results persist in the `.pwb`

`ViolationCTG` survives in the saved case. Opening a case and reading it immediately
returned **148 rows** from some previous run, full of real-looking numbers.

Call `CTGClearAllResults()` before every solve, and assert every returned `CTGLabel` is in
the set you meant to solve.

### Trap 4 — never use a bare read

```python
pw[ViolationCTG]                    # -> 2 columns: CTGLabel, LimViolID:1
pw[ViolationCTG, VIOLATION_FIELDS]  # -> everything you asked for
```

### The per-category column contract

Which identity slots are populated, by category (`1.0` = always, `0.0` = never):

| `LimViolCat` | `AreaNum` | `AreaNum:1` | `AreaNum:2` | `BusNum` | `BusNum:1` | `BusNum:2` | `LineCircuit` |
|---|---|---|---|---|---|---|---|
| `Branch MVA` | 1.0 intra / **0 tie** | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| `Branch Amp` | 1.0 intra / **0 tie** | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| `Bus High Volts` | 1.0 | 1.0 | 0.0 | 1.0 | **0.0** | 1.0 | 0.0 |
| `Bus Low Volts` | 1.0 | 1.0 | 0.0 | 1.0 | **0.0** | 1.0 | 0.0 |
| `Interface MW` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

Two consequences worth internalising:

- **A bus violation carries a populated `AreaNum:1`.** So a two-endpoint OR applied
  unconditionally attributes a bus to an unrelated area. `BusNum:1` is the clean
  discriminator — populated for branch rows, empty for bus rows.
- **Interface rows carry no identity at all.** They cannot be attributed to a region; drop
  them deliberately and print the count.

### Row-count integrity, and why not to deduplicate

`rows_per_label == CTGViol` held exactly on **40/40** labels. Assert it — it catches
duplication *and* dropped rows for free.

**But it does NOT hold on every model, and the reason matters.** On a regional
planning model (2026-08-17) a label returned 1 row while its own `CTGViol` read `0`.

The tempting explanation — that `CTGViol` counts only branch violations, so a voltage-only
contingency reads 0 — is **wrong, and was tested**:

- esapp's schema defines `CTGViol` as *"the number of violations that occurred under this
  contingency"*, unqualified (`esapp/components/grid.py`, class `Contingency`), while
  `CTGNBranchViol` / `CTGNVoltViol` / `CTGNInterfaceViol` are the branch / **bus** /
  interface counts.
- Synth2k confirms it is the sum: `3010 + 1 + 1195 = 4206` exactly, on a label carrying all
  three kinds (Stage 0b, Q4).

So `CTGViol` **does** include voltage violations, and a disagreement is a real signal rather
than a scope quirk. The live candidates are a **stale or duplicate-labelled `Contingency`
record** — a label-keyed join silently collapses duplicates to whichever side wins, and
`Contingency` aggregates persist in the `.pwb` exactly like `ViolationCTG` does (trap 3) —
or rows genuinely dropped.

The discriminating probe, from data you have already read:

| check | what it means |
|---|---|
| more than one `Contingency` row shares the label | duplicate record; the count you read is the wrong record's |
| `rows == 0` while `CTGViol > 0` | rows were dropped — and that device will read as causing nothing |
| `CTGViol != CTGNBranchViol + CTGNVoltViol + CTGNInterfaceViol` | the aggregate is stale for that label |

Note the guard is worth keeping but **not worth aborting on after an expensive solve** —
report the evidence and mark the run unverified instead, or you destroy the rows you would
need to tell these three apart.

`LimViolCTGSpecifiedLimit` (*"If YES, Limit was specified during a contingency action. This
Limit overrides all Limit Monitoring Settings."*) is a separate, real mechanism for a
violation whose limit differs from the standing `LimitSet`. It read `NO` on those rows
above, so it did not explain them — but it is not in the default field list and is worth
reading when limits and violations disagree.

Do **not** deduplicate on `(label, category, element)`. Repeated-looking rows are usually
real: four parallel circuits on one bus pair produce one contingency each, and outaging any
one overloads the other three. That is 3 rows per label with identical bus numbers and
*different* `LineCircuit` values — a dedup on the bus pair would silently eat them.

### `ContingencyElement` has no `LineCircuit`

To map a branch to its auto-inserted contingency label, the third key comes from
**`ElementID`**, verified to distinguish parallel circuits on three bus pairs including a
three-circuit transformer bank (`'1'`, `'10'`, `'20'`). `Object` (`"BRANCH 1001 1064 1"`)
works equally well.

**Never parse the `CTGLabel` string.** It embeds *truncated* substation names
(`L_001068MIDLAND10-001016GARDENCITY0C1`) and truncation collides.

### Islanding is not detectable from `CTGSolveAll`

`CTGSolved` catches divergence reliably. Islanding it does not, and neither does anything
else that was probed against eight outages that provably island a bus:

- `BusMinVoltageContingency == 0` is **not** an islanding signal — 1,466 of 2,000 buses read
  0.0 on an ordinary run. It means "the band was never breached in that direction for that
  bus". (This is the same `0.0` that `n1_voltage_violations` already treats as
  "not evaluated".)
- All eight islanding contingencies reported `CTGSolved='YES'` with thousands of ordinary
  violations — indistinguishable from any other contingency.
- `CTGWhatOccurredCount`/`:1`/`:2`, `CTGAltPFBusCount`, `CTGAltPFPossible` and
  `CTGRemedialActionApplied` are identically zero/`"Not Checked"` either way.
- No `Bus Low Volts` row anywhere read near 0 pu (minimum 0.9312) — **islanded buses emit no
  violation rows at all.**

If you need islanding detection, `CTGSolveAll` alone will not give it to you — **but
[lodf](../concepts/lodf.md) will, for free and without a solve.** When the LODF denominator `1 − ψ_kk → 0`
there is no alternate path, i.e. outaging that branch splits the network; the math flags it
before any solve is attempted. Measured on Synth8k: **420 of 13,470** outages, found in the
~6 s it takes to build the PTDF. That page reached the same conclusion from the other
direction — *"in a PowerWorld CTG sweep, islanded buses read 0 and get skipped, so stranding
a 138 kV pocket reports CLEAN"* — and this page is the independent confirmation of that hole
from inside `ViolationCTG`.

**So the correct pairing is: `CTGSolveAll` for the violations, the LODF denominator for the
islanding list.** Neither one covers the other.

### Rate sets on Synth2k series-24

Only rate set **A** carries any limit — 3,911 branches, median 221 MVA, max 4,352. `LineAMVA:1`
through `:7` (B–H) are entirely unpopulated, and the case ships monitoring `LSLineRateSet="A"`.

**There is no separate emergency rating on these cases.** Do not assume `"B"`; read
`LineAMVA:N` and see which letters actually carry numbers before claiming a result is against
an emergency criterion.

### Aggregates you get for free

`Contingency` also carries per-contingency aggregates PowerWorld computes itself:
`CTGViolMaxLine`, `CTGViolMaxVolt`, `CTGViolMinVolt`, `CTGNBranchViol`, `CTGNInterfaceViol`,
`AggrMVAOverload`, `AggrPercentOverload`. They are **not** region-filtered, so they cannot
replace a regional study — but they are a free whole-system cross-check on a ranking.

## Provenance

Measured live on 2026-08-16 against
`Synth2k_case.PWB` by the Stage-0 spike of
`C:\path\to\regional-contingency` — `spike/stage0_spike.py` and
`spike/stage0b_spike.py`, with the full output tables in that repo's
`docs/stage0_findings.md` and `docs/stage0b_findings.md`.

Numbers quoted here come from a run with the bands deliberately squeezed
(`LSLinePercent=25`, band `[0.99, 1.01]`) so that every category was forced to appear.
