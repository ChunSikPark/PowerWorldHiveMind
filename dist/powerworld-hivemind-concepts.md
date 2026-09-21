# PowerWorldHiveMind - CONCEPTS

# ==== aux-only-powerworld.md ====

---
type: concept
domain: tooling
aliases: [aux-only, aux-without-esapp, aux-without-simauto, headless-aux, pure-aux]
tags: [powerworld, aux, script, simauto, esapp, provenance, house-rule]
---

# Driving PowerWorld with aux files alone

## Abstract

A PowerWorld `.aux` file is a complete program, not a fragment: one loaded file can open a
case, edit it, solve it, export results to CSV, write the message log to a text file and
exit, with **no Python and no SimAuto call of your own**. Live-verified 2026-09-11 on a
regional synthetic planning model. This page records what the aux language can do
unaided, the capabilities it structurally lacks (no return values, almost no control flow,
no assertions) and the read-back discipline that substitutes for them, the two conditional
constructs it *does* have — the solve-failure `STOP` slots and, since the September 2026
patch, `SetElseCreateData`'s exists-check — the syntax traps
measured the same day, and — most importantly — **the field-name provenance rule**: the
*Auxiliary File Format* manual is a syntax manual with no per-object field catalog, so
field names must come from esapp's generated schema or PowerWorld's own field export,
never from the manual and never from memory. Read before writing any `.aux` by hand.

## Connections

- **Up:** [powerworld-simauto](powerworld-simauto.md) · esapp package · [Home](../index.md)
- **Across:** aux script catalog (the 344-action name index) ·
  [esapp-script-command-wrappers](esapp-script-command-wrappers.md) (the inverse house rule for the *Python* side) ·
  [opf-preconditions](opf-preconditions.md) (the first real study run this way) ·
  artifact level validation (the "it reported success and wrote nothing" family this
  page's read-back rule belongs to) · esapp settable vs enterable
- **Applied in:** [new-device-contingency-aux](../methods/new-device-contingency-aux.md) · [case-to-case-device-transplant](case-to-case-device-transplant.md)
- **Across:** [powerworld-script-transfer](powerworld-script-transfer.md) (the same aux text, delivered by drop file instead of a launcher)
- **Deeper:** [esapp-schema-reference](../references/esapp-schema-reference.md) · Simulator's *Auxiliary File Format* manual (Help menu)

## Content

### It works, and the whole loop closes

Verified 2026-09-11, ~9k-bus synthetic planning model, Simulator 24 build 577. A single
`.aux` loaded through the GUI performed, unattended, in file order:

```
OpenCase -> EnterMode(RUN) -> SolvePowerFlow(RECTNEWT) -> SaveData x2 -> LogSave
```

The log recorded `Simulation: Successful Power Flow Solution` and both CSVs landed on
disk. Nothing in the chain went through `pw.esa`, `RunScriptCommand`, `LoadAux` or
`ProcessAuxFile` from the caller's side — the file was simply opened.

The self-contained shape is:

```
SCRIPT
{
  LogClear;  LogAdd("start");  LogAddDateTime;
  OpenCase("<absolute path>.pwb");
  EnterMode(RUN);
  SolvePowerFlow(RECTNEWT);
  SaveData("<absolute path>.csv", CSV, Branch, [<fields>], [], "", [], NO, NO);
  LogSave("<absolute path>.txt", NO);
  ExitProgram;                     // omit to leave the GUI open
}
```

`LogSave` is the cheapest and only general feedback channel — everything PowerWorld says
during the run, including warnings you would otherwise never see, lands in that text file.

**Unnamed `SCRIPT { }` blocks auto-execute on load.** The manual never says so in a
positive sentence, but `StopAuxFile` is documented as suppressing every later SCRIPT and
DATA block in the file (which presupposes they would otherwise run), and `LoadScript` is
described as executing only the section it names — a restriction stated against normal
open-the-file behaviour. Naming a block makes it
*additionally* addressable via `LoadScript`; it does not gate it. Several `SCRIPT` blocks
interleaved with `DATA` blocks in one file is the manual's own canonical layout.

### The one branch aux does have: conditional-response slots

Several analysis actions take a pair of optional filename slots that fire on success and
on failure, and either slot accepts the literal `STOP`, which halts **all** aux execution:

```
SolvePrimalLP("", STOP);        // succeed: continue.  fail: halt the file.
```

The manual describes all four parameters as optional, and says they specify what should
happen conditionally on whether a solution was found. `InitializePrimalLP`,
`SolveSinglePrimalLPOuterLoop` and `SolveFullSCOPF` carry the same slots.

**Use them on every solve whose failure would invalidate what follows.** The bare form has
no failure handler, so a solve that does not converge lets every later stage run against
an unsolved case and write plausible-looking numbers to correctly-named files — the exact
silent failure this page's read-back rule exists to catch, arriving through the one door a
read-back does not cover.

### What the aux language cannot do, and what to do instead

Beyond those slots and `SetElseCreateData` below: no return values, no general branching,
no arithmetic over a table, no assertions. Consequently:

- **A failed edit is indistinguishable from a successful one at runtime.** The same family
  as [case-to-case-device-transplant](case-to-case-device-transplant.md)'s `ProcessAuxFile` trap — reports success, changes
  nothing.
- **Substitute a read-back CSV for every assertion.** After a write, `SaveData` the fields
  you just wrote, *before* any solve, to a file named for the check. Then read it. A run
  whose edit silently no-opped otherwise produces the unchanged case under new filenames,
  with plausible numbers throughout — the failure mode that ruins a study quietly.
- **Per-object arithmetic is impossible.** `SetData` writes one literal to every object
  matching a filter, so "set each unit to 80% of its own maximum" cannot be expressed.
  That is the honest boundary at which to go back to Python.

### The one exists-check: `SetElseCreateData`

Added in the **September 2026 patch of Simulator 24** — older builds do not have it, and
the aux will fail on a machine running one. PowerWorld's own justification names the gap
this page describes: *"Because AUX scripts provide no process control to determine if a
power flow case contains a particular object, this command provides a way to do that."*

```
SetElseCreateData(objecttype, [fieldlist], [SetValueList], [DefaultValueList]);
```

If the object exists it is updated; if it does not, it is created, and **Simulator switches
itself to EDIT mode to do so**. It affects exactly one object — there is no filter form, so
this is not a way to conditionally update a set.

The two value lists are where it goes wrong quietly:

- `[fieldlist]` must carry the key fields, and `[SetValueList]` must give them non-blank
  values. Same rule as everywhere else in this kit.
- **A blank entry (nothing between the commas) means "fall through to the default".** An
  empty pair of double-quotes `""` does *not* — it is a real value and suppresses the
  default. PowerWorld's own worked example turns on exactly this distinction: with
  `Status` written as `""` the command errors when the generator is absent, and with
  `Status` left blank it creates the generator using the default `"Closed"`.
- `[DefaultValueList]` is optional; omit it and Simulator's own defaults apply. Key fields
  in it are ignored.
- Creation still needs every **required** field to end up non-blank across the two lists.
  Most object types silently decline to create when a required field is blank.

```
SetElseCreateData(Bus, [Number, Name, AreaNumber, ZoneNumber, NomkV],
                       [1,,,3,], [1, "NewBus", 1, 3, 138]);
```

It does not lift the read-back rule. It tells you nothing about which branch it took, so
if the distinction matters, `SaveData` the object afterwards and look.

### The field-name provenance rule

**Simulator's own *Auxiliary File Format* manual documents script syntax and contains no
per-object field catalog.** Measured 2026-09-11: across ~10,300 lines, zero hits for any of
the Area or generator field names needed for an OPF setup. Re-confirmed 2026-09-12 against
the **September 1, 2026** edition — same result. **Check the `Last Updated` line on page 1
before trusting a claim sourced from it**: the manual gains actions between editions, and
the November 6, 2025 edition is missing four that exist by September 2026,
`SetElseCreateData` among them. The manual says so itself — it directs
you to *Window → Export Case Object Fields* in the GUI instead. It therefore cannot confirm
or refute a field name, ever.

So do not guess field names, and do not take them from prose pages in this vault either —
one such page in this wiki carried an Area field name that does not exist in the schema.

**Verify against esapp's generated schema first, then emit the aux.** This costs seconds,
needs no PowerWorld session, and is the correct workflow for authoring aux by hand:

```python
from esapp.components import Area
[f for f in Area.fields() if "AGC" in f.upper()]   # does the name exist?
Area.is_editable("BGAGC")                           # can it be written?
Area.is_edit_mode_only("BGAGC")                     # does it need EnterMode(EDIT)?
Area.keys()                                         # what identifies the object?
```

`is_edit_mode_only` is the one that decides whether an `EnterMode(EDIT)` wrapper is
required or merely noise. `keys()` matters because a `SetData` with no filter needs the
full key row (see below). Within a script, `SaveObjectFields` gets the same metadata —
variable name, field, column header and description — straight from the running program.

### Syntax traps, all measured 2026-09-11 against the manual

| Trap | Correct form |
|---|---|
| `SetData`'s "all objects" token is the **bare keyword** `ALL`. `""` is not legal — the quotes make it parse as a filter *named* empty string | `SetData(Area, [Field], ["Value"], ALL);` |
| With **no** filter, `SetData` requires the object's full key row in the field list | see `Type.keys()` |
| `SaveObjectFields` takes **three required** arguments; the field list is not optional | `SaveObjectFields("f.csv", Area, [FieldA, FieldB]);` |
| `SaveData`'s `Transpose` and `Append` are **scalars**, not lists — a `[]` there is wrong even when it appears to work | `..., filter, [SortFieldList], NO, NO);` |
| `SaveData`'s filter *may* be blank (unlike `SetData`'s) — blank means all objects | `..., [], "", [], NO, NO);` |
| The `ALL` keyword is documented as usable "instead of a list of fields" on the Save commands, but the manual gives **no worked example anywhere** — bare `ALL` vs `[ALL]` is undocumented | use an explicit field list |
| Every file path must be **absolute**; a relative path resolves against `pwrworld.exe`'s working directory, not yours | — |
| **Smart quotes silently break a script.** Straight quotes only | never paste from Word or a PDF |
| Solver token is `POLARNEWTON`, not the commonly written `POLARNEWT` | `RECTNEWT`, `POLARNEWTON`, `GAUSSSEIDEL`, `FASTDEC`, `ROBUST`, `DC` |
| `EnterMode(EDIT)` is required only to **create** topology objects. Modifying an existing one is not documented as needing it | keep the wrapper anyway; it costs nothing and the manual never positively blesses modify-in-RUN |

`DATA (Object, [fields]) { rows }` is the legacy header form and is correct; omitting the
file-type specifier means space-delimited rows. `BusNum:1` is the to-bus (`variablename:location`,
where `:0` may be omitted). Quoting string values is optional but advisable.

### When to use this, and when not to

Aux-only is right when the logic is declarative and the value is auditability: the whole
study is one reviewable text file, diffable and version-controllable, with no Python
environment to reproduce. It is wrong the moment you need to branch on a result, compute
per-object values, or assert anything beyond "read it back and look".

The middle path costs five lines and keeps both: author the whole study as `.aux` text and
use Python purely as the launcher via `exec_aux`, which buys back the read-back assertion
without moving any logic into Python. stochastic model backend already runs this way.


---

# ==== case-impedance-completeness.md ====

---
type: concept
domain: cross-cutting
aliases: [case-impedance-completeness, dc-only-skeleton, missing-r-and-b, impedance-health-check]
tags: [technique, cross-cutting, validation, powerworld, impedance, case-quality, acpf]
---

# Case impedance completeness — a case that solves in DC may carry no R and no B at all

## Abstract

A PowerWorld case can solve DC power flow perfectly, report sensible flows, and be handed
between projects for years while carrying **no resistance and no line charging whatsoever**.
DC power flow reads only `X`, so nothing in a DC pipeline ever touches `R` or `C` and nothing
complains. The Synth9k 2031 case had `LineR ≤ 1e-6` and `LineC == 0` on **97.2% of its closed
lines** — undetected because every consumer up to that point was DC. **Check X/R before
trusting any case you did not build**, and especially before promising anyone an AC study.

## Connections

- **Up:** [Home](../index.md)
- **Found in:** a real-power planning study — the Synth9k 2031 case, 2026-08-18 — and
  independently confirmed on a second lineage the same day: `LineR <= 1e-6`
  and `LineC == 0` on **97.5%** of `Synth9k_case` and
  **100.0%** of `Synth8k_draft` (median X/R 100,010 and 113,465), so the five
  scenario cases built from them in [applying-a-dispatch-to-a-case](../methods/applying-a-dispatch-to-a-case.md) inherit it
- **💡 Applies to:** any study whose input is exactly such a case · synthetic case
  construction, where the handoff between build stages is where this is introduced · case
  diffing, since a diff that ignores R/C will not see it · grid statistics · any project
  that receives a `.pwb` from another project or vintage
- **Across:** deriving a quantity by ratio (a ratio on a placeholder zero stays zero —
  check this first) · artifact-level validation (same family: the artifact exists, but is
  it real?)

## Content

### The check

One line, and it is decisive:

```python
xr = (br.LineX / br.LineR.replace(0, np.nan)).median()      # closed, non-transformer lines
```

| median X/R | verdict |
|---|---|
| **2 – 20** | normal overhead transmission |
| **> 1000** | R is placeholder. The case cannot do losses, and AC will not mean anything. |
| **74,195** | what the Synth9k 2031 case actually measured |

Alongside it, count `LineC == 0`. Legitimate zeros exist — genuine intra-substation bus ties,
3,474 of them in this case — so compare the count against the number of zero-length branches
rather than expecting zero.

### Why it survives so long

**DC power flow reads only `X`.** Losses, charging, voltage and reactive power are the only
things that read `R` and `B`, and none of them appear in a DC pipeline. So a case can pass
through case-building, dispatch, DC screening and a conductor-planning loop with two-thirds of
its impedance missing, and every stage reports success.

The failure surfaces only when someone finally runs AC — typically a different person, in a
different project, months later, who then debugs *their* code.

### The trap inside the trap

A conductor-resizing or reinforcement loop **does not fix this**, even though it writes
impedance. It only writes R/X/C on the lines it upgrades — 335 of 11,888 in the Aug-13
Synth9k run, 2.8%. Running it and declaring the case AC-ready is exactly wrong: you get a case
that is 97% DC-skeleton and 3% real, with **no way to tell the two apart** by inspection.

### The fix is usually a restore, not a model

Do not model R and B back in if they exist somewhere. In this case the same 13,470 branch keys
had healthy impedance in an older vintage of the same network, whose `X` agreed with the
current case on **96.2%** of lines — so the repair was a keyed copy of R and C, not a
reconstruction. Median X/R went 74,195 → 5.40.

Checklist for a restore:
1. **Key on the real key fields** (`BusNum`, `BusNum:1`, `LineCircuit` as a *stripped string* —
   see [per-unit-basis-discipline](per-unit-basis-discipline.md)'s cousin trap, a CSV round-trip turns `'01'` into `1`).
2. **Assert zero unmatched rows on both sides.** A partial join silently leaves placeholders.
3. **Check the donor's `X` agrees** with the target's. If it does not, you are transplanting
   R and C onto a different network's reactance — count and list those lines rather than
   hiding them (448 of 11,888 here).
4. **Prefer a donor untouched by known-buggy code.** 352 lines in the chosen donor carried R/C
   written by a defective recomputation and were sourced from its pre-upgrade ancestor instead.

### Do not confuse "solves" with "is physical"

The 2031 case solved DC fine throughout. Convergence is not evidence of a complete model — it
is evidence that the subset of the model your solver reads is self-consistent.


---

# ==== case-to-case-device-transplant.md ====

---
type: concept
domain: cross-cutting
aliases: [AUX transplant, device delta transplant, LoadAux create]
tags: [powerworld, esapp, aux, technique, case-diff]
---

# Case-to-case device transplant

## Abstract

How to copy a set of devices from one PowerWorld case into another without rebuilding the chain
that produced them — useful whenever a feature was developed on one scenario and the others are
stranded behind unscripted stages. Carve a **filtered AUX out of the source case's own
`SaveCase(AUX)` dump** so the field lists are PowerWorld's rather than hand-written, and load it
with `LoadAux(create_if_not_found=True)`. To *move* a device between buses, carve its record out
of the **target** case and re-point the bus number, so the whole schema transfers by construction.
Proven 2026-09-01 on four Synth9k scenarios: 869 buses, 1,207 shunts, 1,019 branches, 724 gen
moves, 147 load moves, criterion-10 clean on all four.

## Connections

- Used in a scenario-envelope study, to answer an accepted migration risk.
- Complements reading a case diff — that is about *reading* a diff across two model
  vintages, this one is about *applying* one.
- Depends on the same key-field constraint as circuit-ID renaming: some fields can only be changed
  through an AUX text round-trip, never by a write.
- 💡 **Could transfer to:** any study where one scenario got a
  feature and the rest need it, or where a chain is unreproducible and only the *result* survives.

## Content

### The method

1. `SaveCase(AUX)` the **source** case. Its per-object blocks (`Bus (…) { … }`) carry PowerWorld's
   own complete field lists — never hand-write one, and never assume a field name.
2. Keep only the records you want, by key. Watch for **duplicate blocks**: a full dump writes
   `Bus`, `Gen`, `Load` and `Branch` more than once (the extras carry cost / OPF fields). Filter
   every occurrence, not the first.
3. Write them back out ordered **Bus → Shunt → Branch → Transformer** so references resolve.
4. Load into the **target** with `LoadAux(path, create_if_not_found=True)`.

### The trap that eats an hour

**`ProcessAuxFile` on a data aux creates nothing and reports success.** No error, no warning, and
the device counts are simply unchanged. `LoadAux(..., create_if_not_found=True)` is the working
call; the create flag is the entire difference. Assert on device counts after the load, never on
the absence of an exception — a discipline guards that report evidence they did not gather
argues for generally.

### Moving a device between buses

There is no move operation. Delete-and-recreate risks dropping fields silently — the
`LoadGrounded` bug hit all 147 loads in the original migration and was invisible to a diff over
the write set, because a dropped field is by definition absent from it.

**Carve the record out of the TARGET case's own aux and re-point only the leading bus-number
token, then delete the original.** The whole schema then transfers by construction: there is no
field list to get wrong, and no value from the source case can leak in. This is what makes the
technique safe across scenarios — a moved generator keeps *its own* scenario's dispatch, not the
donor's.

### Always undo the text rounding

The aux writes R/X/C to 6 decimals and MW / limits to 3. Snapshot exact values before the
round-trip and write them back afterwards, confirming on read-back. Skipping this left 147 moved
loads 7.3e-3 MW light — small enough to pass a loose tolerance and wrong enough to poison a
conservation check later.

### esapp notes

- esapp has **no `change_and_confirm_params_multiple_element`** (the older `esa` package does).
  Write with `ChangeParametersMultipleElement`, then read back and compare yourself.
- `GetParametersMultipleElement` returns **`None`**, not an empty frame, for an object type with
  zero instances — a case with no shunts will crash a naive `len()`.
- See [esapp](esapp.md) and the `SaveCase` script-command trap: `pw.save()` writes nothing silently.

### When the numbering cooperates, check for it first

The Synth9k transplant needed **no renumbering at all**, because the target topped out at bus 8528
and every new bus in the source was 8529–9397. That is worth two minutes of checking before
designing a remap: disjoint ranges turn a hard problem into a copy.


---

# ==== copper-plate.md ====

---
type: concept
domain: cross-cutting
aliases: [copper-plate, copperplate, copper-plate-model, network-collapse, unconstrained-dispatch]
tags: [copper-plate, dispatch, transmission, network, slack-bus, power-flow, technique, cross-cutting]
---

# Copper-Plate Model

## Abstract
Collapse the entire transmission network — strip all branches, loads, and shunts, then add a single slack bus — so generators dispatch to serve total system load **without any transmission constraints**. Every generator sees infinite capacity between itself and every other bus; hence "copper plate" (ideal conductor). Used in pfw copperplate to let weather-driven renewable output dispatch freely, isolating the weather → MW signal from network topology artifacts. The build sequence (delete Branch/Load/Shunt → add slack bus 999999 → large slack gen) is documented in pfw copperplate backend.

## Connections
- **Up:** [Home](../index.md)
- **Used in:** pfw copperplate (weather-driven renewable dispatch without network limits — see pfw copperplate backend for exact build steps)
- **💡 Could apply to (idea transfer):** renewable resource/potential assessment · max-generation studies · isolating a weather → MW signal from any network study
- **Across:** time step simulation (copper-plate runs are typically time-step simulations over a weather period)

## Content

### What it does and why

A full power-flow model enforces transmission constraints: a wind farm may be curtailed because a nearby line is at thermal limit, even if the wind is blowing. For studies that ask "how much energy could these generators produce given this weather?" — not "how much does the network allow?" — those constraints are noise. Copper-plate removes them.

With all branches deleted:
- No line flow limits to violate.
- No voltage constraints (no shunts, no reactive power coupling).
- Total generation = total load, balanced by the slack bus.
- Each generator dispatches to its weather-driven maximum (wind speed → MW, solar irradiance → MW).

The slack bus absorbs any imbalance (positive or negative), so the power balance always closes regardless of the renewable dispatch profile.

### Build steps (from pfw copperplate backend)

Starting from a full PowerWorld case:
1. **Delete Branch objects** — removes all transmission lines and transformers, eliminating all flow constraints.
2. **Delete Load objects** — removes all bus loads (load is represented as a net system-wide value, served by the slack).
3. **Delete Shunt objects** — removes all capacitors/reactors (no reactive power devices needed in a copper-plate model).
4. **Add slack bus 999999** — a synthetic bus that acts as the infinite balancing node.
5. **Add large slack generator at bus 999999** — set to AGC/slack mode with very large MW limits (e.g., ±99999 MW) so it can absorb any imbalance.

The result is a star topology: every original generator bus connects to the slack, and the slack sets system frequency/voltage reference.

### Use in pfw copperplate

The PowerFlow Weather (PFW) copper-plate model drives weather-dependent renewable generators (wind, solar) through a time-step simulation over a historical weather period. Because the network is gone, the MW output of each generator in each time step is determined purely by the weather at its location — wind speed for wind, GHI/DNI for solar. This isolates the **weather → MW** relationship and produces a clean time series of potential (unconstrained) renewable generation.

Downstream studies can then take this unconstrained generation signal and apply network constraints separately — a decomposition that keeps the weather modeling and the network modeling cleanly separated.

### 💡 Idea-transfer targets

- **Renewable resource/potential assessment:** "How much energy could all the wind and solar in a region produce over a 20-year climate?" Copper-plate gives you the unconstrained answer; the gap between copper-plate and network-constrained output quantifies curtailment potential.
- **Max-generation studies:** "What is the theoretical maximum MW this fleet could produce on any hour?" Strip the network, dispatch everything to maximum, read the total.
- **Weather → MW signal isolation for dynamic line rating:** DLR studies need to know how wind-driven generation affects line loading. A copper-plate pre-pass isolates the weather → generation relationship before layering in network effects.
- **Benchmarking network congestion:** the difference between copper-plate dispatch and constrained dispatch quantifies how much transmission is limiting renewable utilization — a useful metric for real power planning.

### What copper-plate does NOT give you

- **Voltage profiles** — no branches means no voltage drops, no reactive coupling.
- **Line loading** — by construction there are no lines.
- **Congestion signals** — the whole point is to remove them.
- **Locational marginal prices** — no network, no transmission component to the LMP.

If you need any of these, you need the full network model. Copper-plate is specifically for studies where the question is about energy potential, not delivery constraints.

### Relationship to time step simulation

Copper-plate models are almost always run as time-step simulations: the weather input changes each time step, the renewable dispatch updates, and the slack absorbs the balance. The time-step simulation framework in time step simulation is the computational engine; the copper-plate topology is the network configuration. They compose naturally.


---

# ==== esapp-environment.md ====

---
type: concept
domain: tooling
aliases: [esapp-environment, esapp-setup, esapp-install, esapp-package]
tags: [esapp, powerworld, simauto, setup, environment, install]
---

# Concept: The esapp environment

## Abstract

What `esapp` is, what it needs to run, and how its pieces fit together. `esapp` (ESA++)
is a Pythonic wrapper over PowerWorld Simulator's SimAuto COM server: a `PowerWorld`
entry point, a bracket interface that returns pandas DataFrames, and a `SAW` wrapper
exposing the raw SimAuto surface underneath. Read this once when setting up; read
[esapp-overview](../methods/esapp-overview.md) to actually drive a case.

## Connections

- **Up:** [Home](../index.md)
- **Across:** [esapp](esapp.md) · [powerworld-simauto](powerworld-simauto.md) · [preflight-powerworld](../methods/preflight-powerworld.md) · [esapp-overview](../methods/esapp-overview.md)
- **Deeper:** [esapp-package-backend](../references/esapp-package-backend.md) · [esapp-schema-reference](../references/esapp-schema-reference.md)

## Content

### Install

```bash
pip install esapp
```

Pulls in `pandas`, `numpy`, `scipy`, `matplotlib`, `geopandas`, and `pywin32`. The last
one is the COM bridge and is why this is Windows-only.

Before writing anything, run [preflight-powerworld](../methods/preflight-powerworld.md). It takes five seconds and
distinguishes "my code is wrong" from "this machine cannot run PowerWorld at all",
which are very different problems.

### What you actually need

| Requirement | Why | If missing |
|---|---|---|
| Windows | SimAuto is a COM server with no cross-platform equivalent | The weather half of this kit still works — see [teamoverbyeweather-client](../methods/teamoverbyeweather-client.md) |
| PowerWorld Simulator, installed | esapp drives it; it does not reimplement it | Nothing in the PowerWorld half functions |
| **The SimAuto add-on, licensed** | Automation is licensed separately from Simulator itself | Simulator's GUI works fine and every script fails. See [preflight-powerworld](../methods/preflight-powerworld.md) |
| Matching bitness | A 32-bit Simulator will not serve a 64-bit Python | `Class not registered` at dispatch time |

The licensing point is the one that surprises people. A perfectly good Simulator
installation can be completely unable to run a single line of automation, and nothing in
the GUI hints at it.

### Contributing to esapp

`esapp` is open source (Apache-2.0) and developed at Texas A&M:
**https://github.com/lukelowry/ESApp**

Found a bug, a missing field, or an undocumented behaviour while using this knowledge
base? Two places to send it: a defect in the **package** goes to the esapp repository
above; a defect in a **page** here goes to this repository's issues. They are different
problems with different fixes.

### Prefer `esapp` over `esa`

There is an older standalone `esa` package wrapping the same SimAuto server. Both work;
`esapp` is better documented and is what this kit's pages assume. Mixing them in one
project buys nothing and creates two mental models of the same COM object.

### The three layers

```
your code
    |
    v
PowerWorld          <- the entry point; open a case, get a summary
    |
    v
Indexable           <- the bracket interface: pw[Bus, "BusPUVolt"] -> DataFrame
    |
    v
SAW                 <- the SimAuto wrapper; RunScriptCommand and friends
    |
    v
pwrworld.SimulatorAuto   <- the COM server, i.e. PowerWorld itself
```

Most work happens in the bracket interface. Drop to `SAW` when you need a SCRIPT action
that has no bracket equivalent — see [aux-script-commands](../references/aux-script-commands.md) for the catalogue. Drop
below that essentially never.

### Use the high-level helpers before reaching for script commands

`PowerWorld` exposes worked-out helpers for the things people actually do. Verified
against esapp 0.1.3 by calling them:

```python
pw.pflow(getvolts=True, method="POLARNEWT")   # solve
pw.mismatch(asComplex=False)                  # per-bus P and Q mismatch
pw.overloads(threshold=100.0)                 # branches above a % of rating
pw.violations(v_min=0.9, v_max=1.1)           # limit violations
pw.flows()                                    # branch flows
pw.lodf((frm, to, ckt), method="DC")          # line outage distribution factors
pw.ptdf(seller, buyer, method="DC")           # transfer distribution factors
pw.ybus(dense=False)                          # admittance matrix (scipy sparse)
pw.jacobian(dense=False, form="R")            # the Jacobian
pw.gens(); pw.lines(); pw.loads()             # convenience tables
pw.voltage(complex=True, pu=True)
pw.save(filename=None)                        # write the case back
pw.snapshot()                                 # restore point
pw.run_mode(); pw.edit_mode()                 # switch modes
```

**Every one of these is a method — call it.** Referencing `pw.overloads` or `pw.flows`
without parentheses hands you a bound method where you expected a DataFrame, and the
failure surfaces somewhere further down looking like something else entirely.

Solver settings are the opposite: they are **assignable options**, not methods.

```python
pw.dc_mode = True          # NOT pw.dc_mode(True) -> TypeError: 'bool' object is not callable
pw.flat_start = True
pw.max_iterations = 50
pw.enforce_gen_mw_limits = True
```

Reach for a raw SCRIPT action only when no helper covers what you need.

### Getting at SimAuto directly

When you do need a raw SCRIPT action, the SimAuto wrapper is on the `.esa` attribute,
**not** on `PowerWorld` itself:

```python
pw.esa.RunScriptCommand('SolvePowerFlow(RECTNEWT)')
pw.esa.RunScriptCommand(r'SaveCase("C:\out\case.pwb", PWB, YES)')
```

`pw.RunScriptCommand(...)` raises `AttributeError`. This is the single most common
first-attempt mistake with esapp, because every PowerWorld example you will find online
is written against the SAW object directly.

See [aux-script-commands](../references/aux-script-commands.md) for which action to use.

### Components and schema

Object types are importable classes rather than magic strings:

```python
from esapp.components import Bus, Gen, Load, Branch, Shunt, Area, Zone
```

The component schema is generated from PowerWorld's own field definitions, so field
names track Simulator rather than being hand-maintained. The full field map lives in
[esapp-schema-reference](../references/esapp-schema-reference.md).

### The rule that silently ruins writes

**Always keep an object's key fields in any DataFrame you write back.** For a generator
that is `BusNum` plus `GenID`; for a branch it includes the circuit identifier. Without
the key fields PowerWorld cannot tell which row you mean, and the write does not error —
it simply does nothing.

A second, related trap: `pw[Obj, field] = values` is **positional over the entire
table**. Assigning to a filtered subset writes nothing at all, silently. See
[applying-a-dispatch-to-a-case](../methods/applying-a-dispatch-to-a-case.md).

These two are responsible for more wasted debugging than every other esapp behaviour
combined, because both fail without raising.

### Snapshots

`snapshot()` gives you a restore point for safe experimentation, which is much cheaper
than reloading a large case between scenarios. PowerWorld's own `StoreState` /
`RestoreState` script actions do the same at the solver level.

### Verifying your setup

```python
from esapp import PowerWorld

pw = PowerWorld(r"C:\path\to\case.pwb")
print(pw.summary())    # n_bus, n_branch, n_gen, n_load, totals, v_min, v_max, sbase
```

If that prints a sensible dictionary, the environment is good and you can start at
[esapp-overview](../methods/esapp-overview.md).


---

# ==== esapp-script-command-wrappers.md ====

---
type: concept
domain: tooling
aliases: [esapp-wrappers, runscriptcommand-vs-named-method, esapp-named-methods]
tags: [esapp, powerworld, simauto, script-commands, runscriptcommand, api-drift, house-rule]
---

# Named SAW methods vs. `RunScriptCommand`

## Abstract

House rule for every line of PowerWorld-from-Python code: call the named esapp method
(`pw.esa.TimeStepDoRun()`), not the hand-written script string
(`pw.esa.RunScriptCommand("TimeStepDoRun;")`). 310 of esapp 0.2.1's SAW methods wrap a
PowerWorld SCRIPT command, and both forms reach the same COM call — the named method
buys a Python-side signature check, correct argument-string construction, and, above all,
**one place the maintainer can patch when PowerWorld changes a command's syntax**. This
page records the rule, the exact mechanism (so nobody overclaims it as runtime
validation), the two live-probed exceptions already settled elsewhere in this wiki, and
the related 0.2.1 change that turned a write-time `ValueError` into a warning. Origin:
feedback from the esapp author on the author's `pw.esa.RunScriptCommand` usage, verified
against the 0.2.1 source on 2026-09-08.

## Connections

- **Up:** [esapp](esapp.md) · esapp package · [Home](../index.md)
- **Across:** [powerworld-simauto](powerworld-simauto.md) · aux script catalog (raw SCRIPT name index) ·
  [esapp-overview](../methods/esapp-overview.md) · the "it reported success and wrote
  nothing" family this belongs to
- **Exceptions to this rule:** [save-powerworld-case](../methods/save-powerworld-case.md) (COM `SaveCase` is a silent
  no-op; the *script* `SaveCase` is the one that writes)
- **Obsoleted by 0.2.1, needs re-check:** [converting-lines-to-transformers](../methods/converting-lines-to-transformers.md)
- **Deeper:** [esapp-package-backend](../references/esapp-package-backend.md)

## Content

### The rule

```python
pw.esa.TimeStepDoRun()                       # correct
pw.esa.RunScriptCommand("TimeStepDoRun;")    # wrong
```

Applies to every SCRIPT command esapp wraps — 310 named methods across 20 SAW mixins in
0.2.1, covering roughly 300 of the ~370 SCRIPT actions Simulator defines.

### Why — the actual mechanism

Both forms end at the same COM call. `SAWBase._run_script` (`esapp/saw/base.py:185`) is
a thin builder:

```python
arg_list = list(args)
while arg_list and arg_list[-1] is None:   # strip trailing Nones
    arg_list.pop()
stmt = f"{command}({arg_str});" if arg_list else f"{command};"
return self.RunScriptCommand(stmt)
```

`TimeStepDoRun` (`saw/timestep.py:10`) is literally
`self._run_script("TimeStepDoRun", start_time or None, end_time or None)`. So the win is
not that the wrapper does something exotic at the COM boundary. It is three ordinary
things:

1. **The signature is checked in Python, before COM.** `TimeStepDoRun(start_time: str =
   "", end_time: str = "")` is typed. A wrong arg count is a `TypeError` on your machine,
   not a misbehaviour inside Simulator.
2. **The argument string is built correctly.** Trailing-`None` stripping, `format_list()`
   bracket lists with proper quoting, `format_filter()` and the `_enums` types
   (`FilterKeyword`, `SolverMethod`, `TSGetResultsMode`, …) — so a bogus filter name or
   solver method cannot reach PowerWorld. Hand-rolled f-strings get exactly this wrong.
3. **One patch point.** When PowerWorld changes a command's syntax, the fix lands in
   esapp and `pip install -U esapp` repairs every call site at once. A hand-written
   string is a call site the maintainer can never reach. **This is the whole argument.**

### What it does NOT do — do not overclaim this

esapp does **not** introspect PowerWorld's live command table, does **not** check the
installed Simulator version, and does **not** auto-correct a stale command at runtime.
Confirmed byte-identical in `_run_script` across 0.1.3 and 0.2.1. The guarantee is an
**upgrade path, not a runtime check.**

A related half-truth worth being precise about: a hand-written string does not vanish
silently *if PowerWorld reports an error* — `_com_call` (`saw/base.py:378-387`) raises
`PowerWorldError` on any non-empty error string, specialised by
`PowerWorldError.from_message` into `SimAutoFeatureError`, `PowerWorldPrerequisiteError`,
or `PowerWorldAddonError`. The genuinely dangerous case is narrower and worse: **a
command whose name stays valid but whose parameter order or meaning changes.** The string
"succeeds" and does the wrong thing. That is what the typed wrapper prevents.

(`CommandNotRespectedError` was **removed in 0.2.0** — do not reference it.)

### When `RunScriptCommand` is correct

Only when no named wrapper exists. About 41 of the catalogued actions have none —
largely oneline/GUI actions (`OpenOneline`, `ExportOneline`, `Animate`), dialogs
(`MessageBox`, `ObjectFieldsInputDialog`), and a few writers
(`ATCWriteToExcel`, `SaveDataUsingExportFormat`).

Look the command up in the **SCRIPT command → esapp method index** at the bottom of the
esapp package's own method list before concluding one is missing — absence from
[aux-script-commands](../references/aux-script-commands.md) proves nothing, since that
page is a task-organized working subset rather than a complete index.

Leave a comment saying why whenever you do call `RunScriptCommand`.

### Exception: `SaveCase` — the script command beats the COM method

[save-powerworld-case](../methods/save-powerworld-case.md) is live-probed and still stands: `pw.esa.SaveCase(...)` is a
**silent no-op** on this machine (returns `None`, raw COM returns `('',)` = success, no
file appears), while the aux script form writes:

```python
pw.esa.RunScriptCommand(f'SaveCase("{out}", PWB);')   # exactly 2 params
assert os.path.exists(out), "SaveCase reported success but wrote nothing"
```

This is consistent, not contradictory: esapp routes `SaveCase` through `_com_call`, not
`_run_script`, so it is not one of the 310 SCRIPT wrappers this rule governs. The rule
says *prefer the named wrapper over a hand-written string for the same command*; here the
COM method and the script command are different code paths with different behaviour, and
the script path is the one that works. Same for `OpenCase`/`CloseCase` being absent from
the SCRIPT index.

### Related: 0.2.1 turned a write-time `ValueError` into a warning

Not the same rule, same underlying philosophy — esapp treats PowerWorld as the authority
and refuses to let its own generated schema block you.

Through 0.1.x, writing an unknown or read-only column raised
(`indexable.py:228`, `:280`):

```
ValueError: Cannot set read-only field(s) on Branch: [...]
```

In 0.2.1 that became `warnings.warn` and **the write is still attempted**
(`indexable.py:198-210`): *"PowerWorld is the authority, and the generated schema may lag
the installed Simulator version."*

Two consequences:

- **A field-name typo no longer raises.** `pw[Gen, "GenMWW"] = 100` emits a warning to
  stderr and writes nothing useful. This joins the same silent-no-op
  family as dropping an object's key fields ([applying-a-dispatch-to-a-case](../methods/applying-a-dispatch-to-a-case.md)) and as
  the COM `SaveCase` above: the call reports success and the effect never happens.
  **Do not reach for `python -W error::UserWarning` to fix this** — that was the advice
  here through 2026-09-09 and it backfires, because the *same* warning fires on ~150
  fields that write perfectly well (below). Assert the effect instead: read the field back
  and compare.
- **`Read-only field(s)` is usually a false alarm.** The flag comes from esapp's generated
  schema, which keeps only fields whose `enterable` is an unconditional `Yes` and discards
  every conditional one. PowerWorld's own answer for `LineStatus` is *"Depends: Normally
  enterable except when field Lockout is YES"* — so esapp calls it read-only and the write
  works anyway. Counted against build 2026-07-22: **112 Branch fields, 33 Bus, 5 Gen
  (including `GenMVR`), 1 Load** are enterable in PowerWorld but `is_settable() == False`.
  The authority is `pw.esa.GetFieldList(<type>)`, whose `enterable` column is PowerWorld's,
  not esapp's.
- **The `XF*` bypass in [converting-lines-to-transformers](../methods/converting-lines-to-transformers.md) is now confirmed
  unnecessary.** ✅ **Verified live 2026-09-10** on a ~2,000-bus synthetic case, Simulator build 2026-07-22,
  esapp 0.2.1: `pw[Branch] = df` carrying `LineXFMR='YES'` warns and goes through —
  `BranchDeviceType` flips `Line` → `Transformer`, on a 2-row subset, no exception. That
  page has been rewritten accordingly.

### Provenance

Author feedback relayed by the author, 2026-09-08. Verified against the esapp 0.2.1 source
(`github.com/lukelowry/ESApp`, `VERSION` 0.2.1, 2026-09-01) and diffed against the 0.1.3
build then installed in site-packages. The readthedocs `api/saw.html` page states none of
this — it documents `RunScriptCommand` neutrally and offers no preference, so this page is
the only written record of the rule.


---

# ==== esapp.md ====

---
type: tool
domain: tooling
aliases: [ESA++, esa_pp, esapp-api]
tags: [esapp, powerworld, simauto, python, tool]
---

# ESA++ (esapp) — tool reference

## Abstract

`esapp` (ESA++) is a Python toolkit that gives a Pythonic, pandas-flavored interface to PowerWorld Simulator's Automation Server (SimAuto) over COM. It is Windows-only and requires PowerWorld locally. This page is the full API map: top-level imports, architecture (mixin-built `SAW`, `PowerWorld` workbench, embedded modules), the bracket read/write interface, all `pw.*` methods, transient-stability helpers, and the GObject schema accessors. For how to drive it in practice, start at [esapp-overview](../methods/esapp-overview.md).

## Connections

- **Up:** [Home](../index.md) · esapp package
- **Across:** [powerworld-simauto](powerworld-simauto.md) · [esapp-overview](../methods/esapp-overview.md) · esa pp llm · time step simulation · dynamic line rating · reactive power planning · real power planning · synthetic creation · [gic](gic.md)
- **Field schema + commands:** [esapp-schema-reference](../references/esapp-schema-reference.md) — exact object key/identifier fields + SimAuto command catalog for writing esapp code
- **SCRIPT action catalog:** aux script catalog — task-organized PowerWorld SCRIPT-command index (198 actions), for anything not yet wrapped by a named SAW method
- **House rule for calling them:** [esapp-script-command-wrappers](esapp-script-command-wrappers.md) — call `pw.esa.TimeStepDoRun()`, never `RunScriptCommand("TimeStepDoRun;")`; also the 0.2.1 change that made a bad write warn instead of raise

## Content

`esapp` (ESA++) is a Python toolkit that gives a Pythonic, pandas-flavored
interface to **PowerWorld Simulator's Automation Server (SimAuto)** over COM
(see [powerworld-simauto](powerworld-simauto.md)). It is **Windows-only** (depends on `pywin32` for
COM interop) and requires PowerWorld Simulator installed locally. This page is
*what it is* — the API map. For *how to drive it*, start at [esapp-overview](../methods/esapp-overview.md).
The project that maintains/extends the package is esapp package.

> Source of truth: `C:\path\to\esapp`. Every symbol below was
> read out of that tree. Validate against `esapp` source (or the `esapp` skill)
> before shipping any `methods/` page that calls the API.

## Top-level imports

```python
from esapp import PowerWorld          # main entry point
from esapp import SAW                 # low-level SimAuto wrapper (usually via pw.esa)
from esapp import TS, TSField         # transient-stability field constants
from esapp.components import Bus, Gen, Load, Branch, Shunt, Area, Zone  # GObject types
from esapp.utils import TSWatch, ContingencyBuilder, SimAction, BranchType  # helpers
```

`esapp/__init__.py` exports `PowerWorld`, `SAW`, `TS`, `TSField`, and the
exception hierarchy (`PowerWorldError`, `COMError`, `SimAutoFeatureError`,
`PowerWorldPrerequisiteError`, `PowerWorldAddonError`). `CommandNotRespectedError` was
**removed in 0.2.0** — do not reference it.
Note: `TSWatch` / `ContingencyBuilder` are **not** top-level — import them from
`esapp.utils`.

## Architecture (real)

- **`PowerWorld`** — `esapp/workbench.py`. The user-facing class; subclass of
  `Indexable`. Holds the live SimAuto connection on `pw.esa` and three embedded
  application modules: `pw.network`, `pw.gic`, `pw.buscat`.
- **`Indexable`** — `esapp/indexable.py`. Implements the bracket read/write
  interface (`__getitem__` / `__setitem__`) and `open()`.
- **`SAW` (SimAuto Wrapper)** — `esapp/saw/saw.py`. Built by the **mixin
  pattern** from `SAWBase` (`saw/base.py`) plus ~20 focused mixins:
  `DataMixin`, `PowerflowMixin`, `MatrixMixin`, `ContingencyMixin`,
  `TransientMixin`, `SensitivityMixin`, `GICMixin`, `OPFMixin`, `PVMixin`,
  `QVMixin`, `ATCMixin`, `FaultMixin`, `TopologyMixin`, `RegionsMixin`,
  `ModifyMixin`, `GeneralMixin`, `CaseActionsMixin`, `ScheduledActionsMixin`,
  `TimeStepMixin`, `WeatherMixin`. This is the raw COM layer — reach it via
  `pw.esa`.
- **Components** — `esapp/components/`. `grid.py` (auto-generated, large) holds
  a `GObject` subclass per PowerWorld object type; `ts_fields.py` holds the
  `TS` / `TSField` constants; `gobject.py` is the base class;
  `generate_components.py` regenerates both from the `PWRaw` TSV schema. **Do
  not hand-edit `grid.py` / `ts_fields.py` — regenerate them.**
- **Utils** — `esapp/utils/`: `network.py` (`Network`), `gic.py` (`GIC`),
  `dynamics.py` (`TSWatch`, TS result processing), `contingency.py`
  (`ContingencyBuilder`, `SimAction`), `b3d.py` (`B3D` field-file I/O),
  `buscat.py` (`BusCat`).
- **Enums / descriptors / exceptions** — `saw/_enums.py` (`SolverMethod`,
  `JacobianForm`, `LinearMethod`, `PowerWorldMode`, filter keywords, …),
  `_descriptors.py` (`SolverOption`, `GICOption` descriptors), and
  `saw/_exceptions.py` (`PowerWorldError` hierarchy).

## Bracket data interface (the core idiom)

```python
pw[Bus]                              # primary-key columns only
pw[Bus, "BusPUVolt"]                 # keys + one field
pw[Gen, ["GenMW", "GenMVR", "GenStatus"]]   # keys + several
pw[Bus, :]                           # keys + EVERY defined field
```

Reads go through `esa.GetParamsRectTyped` and return a typed `DataFrame`.
Writes use the same brackets:

```python
pw[Gen, "GenMW"] = 100.0             # broadcast scalar to existing gens
pw[Gen, "GenMW"] = [100, 150, 200]   # per-element list
pw[Bus] = df                         # bulk update from a DataFrame (must carry primary keys)
pw[Gen, "GenStatus"] = True          # bools are serialized -> "Closed" (0.2.1)
```

**Status fields accept Python bools** as of 0.2.1 — `_serialize_bools` maps them through
`BOOL_FIELD_VOCAB` (`components/gobject.py:39`), so you no longer have to remember which
string a given field wants:

| Field | `True` | `False` |
|---|---|---|
| `GenStatus`, `LineStatus`, `LoadStatus`, `SSStatus` | `Closed` | `Open` |
| `BusStatus` | `Connected` | `Disconnected` |
| `BusSlack`, `GenAGCAble`, `GenAVRAble` | `YES` | `NO` |

Indexed variants resolve to their base name, so `LineStatus:1` works too. A bool aimed at
an **unregistered** field raises `ValueError` rather than guessing — pass PowerWorld's
string, or add the field to `BOOL_FIELD_VOCAB`. The plain strings still work everywhere,
and most pages in this kit still use them.

`pw[Type] = df` can also **create** objects when the case is in EDIT mode and
the SAW was opened with `CreateIfNotFound=True`.

> ⚠️ **Changed in 0.2.1.** Unknown and read-only columns used to raise
> `ValueError: Cannot set read-only field(s)` (`indexable.py:228`/`:280` in 0.1.x). They
> now emit a `warnings.warn` and the write is **still attempted** — PowerWorld is treated
> as the authority so a lagging generated schema can't block a newer Simulator's fields.
> The cost: a field-name typo no longer raises.
> See [esapp-script-command-wrappers](esapp-script-command-wrappers.md).

> 🚫 **Do not run `python -W error::UserWarning` to get the old strictness back.** That
> advice was here through 2026-09-09 and it is wrong: esapp's read-only flag is a *stale
> generated whitelist*, not PowerWorld truth, so promoting the warning to an error breaks
> writes that work. Measured on Simulator build 2026-07-22, the count of fields PowerWorld
> reports as enterable but `is_settable()` calls read-only: **112 on Branch, 33 on Bus,
> 5 on Gen (including `GenMVR`), 1 on Load**. `pw[Branch, 'LineStatus'] = 'Open'` warns,
> succeeds on all 3950 branches — and dies under `-W error`. PowerWorld's own answer for
> `LineStatus` is *"Depends: Normally enterable except when field Lockout is YES"*; esapp
> drops every conditional field. To check settability, ask PowerWorld, not the schema:
>
> ```python
> fl = pw.esa.GetFieldList('branch')          # authoritative
> fl[fl.internal_field_name == 'LineStatus'][['enterable']]
> ```
>
> Catch typos by asserting the *effect* (read the field back and compare), which is the
> rule everywhere else in this kit anyway.

> ⚠️ **Key fields are mandatory for writes.** PowerWorld matches each row back to an
> object by its **key field(s)** (e.g. `BusNum`+`GenID` for a Gen). The bracket read
> includes the keys automatically, so a read-modify-write round-trip keeps them — but if
> you build a DataFrame by hand, or drop columns, it **must still carry the key columns**
> or the write silently does nothing (no error, no change applied). On the raw `esa`/SAW
> path you must prepend them yourself: `Gen.keys() + [<fields>]` (or read them off
> PowerWorld with `pw.esa.GetFieldList('gen')`, whose `key_field` column marks them
> `*1*`, `*2*`, …). Rule of thumb: never strip key columns from a DataFrame you intend
> to push back.
>
> `pw.esa.get_key_field_list(...)` does **not** exist — it was named here in error through
> 2026-09-09 and raises `AttributeError`.

## PowerWorld API surface (`pw.*`, from workbench.py)

- **State / case** — `pw.open()`, `pw.save(filename=None)` ⚠️ **silent no-op, see below**,
  `pw.close()`, `pw.edit_mode()`, `pw.run_mode()`, `pw.flatstart()`, `pw.snapshot()`
  (context manager: `SaveState` on enter, `LoadState` on exit),
  `pw.log(msg)`, `pw.print_log(...)`.

> 🚫 **`pw.save()` writes nothing and reports success.** It is a one-line passthrough to
> `self.esa.SaveCase(filename)`, so it inherits the `SaveCase` no-op documented in
> [save-powerworld-case](../methods/save-powerworld-case.md) — this is the same trap, not
> a second one. The no-op is below esapp: the raw COM call
> `SimAuto.SaveCase(path, "PWB", True)` returns `('',)` (SimAuto's success convention) and
> creates no file. Measured on build 2026-07-22, absolute path, both slash styles.
> Use the script form and assert the file exists:
>
> ```python
> pw.esa.RunScriptCommand(f'SaveCase("{out}", PWB);')
> assert os.path.exists(out), "SaveCase reported success but wrote nothing"
> ```
- **Solve** — `pw.pflow(getvolts=True, method=SolverMethod.POLARNEWT)` returns a
  complex voltage Series; `pw.ts_solve(ctgs, fields)` runs transient stability
  and returns `(metadata, timeseries)` DataFrames.
- **Voltages / power** — `pw.voltage(complex=True, pu=True)`,
  `pw.set_voltages(V)`, `pw.mismatch(asComplex=False)`, `pw.netinj(...)`,
  `pw.violations(v_min=0.9, v_max=1.1)`.
- **Matrices / topology** — `pw.ybus(dense=False)`,
  `pw.jacobian(dense=False, form=JacobianForm.RECTANGULAR, ids=False)`,
  `pw.busmap()`, `pw.buscoords(astuple=True)` (returns a `(Longitude,
  Latitude)` tuple by default — **not** a DataFrame).
- **Convenience tables** — `pw.gens()`, `pw.loads()`, `pw.shunts()`,
  `pw.lines()`, `pw.transformers()`, `pw.areas()`, `pw.zones()`,
  `pw.flows()`, `pw.overloads(threshold=100.0)`.
- **Sensitivities** — `pw.ptdf(seller, buyer, method=LinearMethod.DC)`,
  `pw.lodf(branch, method=LinearMethod.DC)`.
- **Quick props** — `pw.n_bus`, `pw.n_branch`, `pw.n_gen`, `pw.sbase`,
  `pw.summary()` (dict of counts + totals + v_min/v_max).
- **Solver options as descriptors** — set them like attributes:
  `pw.flat_start = True`, `pw.max_iterations = 30`, `pw.convergence_tol = 1e-4`,
  `pw.dc_mode = True`, … (each is a `SolverOption` mapping to a PowerWorld
  Sim_Solution_Options field).

## Embedded modules

- **`pw.network`** (`utils/network.py`) — `incidence()`, `laplacian(weights,
  ...)`, `lengths()`, `zmag()`, `ybranch()`, `yshunt()`, `gamma()`, `delay()`,
  `busmap()`, `buscoords()`; `BranchType.{LENGTH, RES_DIST, DELAY}` weighting.
- **`pw.gic`** (`utils/gic.py`) — `configure()`, `storm(maxfield, direction,
  solvepf=True)`, `model()`, `gmatrix(sparse=True)`, `settings()`,
  `cleargic()`, `loadb3d()`, `timevary_csv()`; result matrices on properties
  `A, G, H, zeta, Px, eff`; options via descriptors `pf_include`, `efield_mag`,
  `efield_angle`, `calc_mode`, … See [gic](gic.md).
- **`pw.buscat`** (`utils/buscat.py`) — bus classification.

## Transient stability (TS)

> ⚠️ **"TS" disambiguation — do not conflate.** Here `TS` = **Transient Stability**: a
> dynamics study of faults, generator trips, rotor angles, and frequency over
> milliseconds-to-seconds (`pw.ts_solve`, `TSWatch`, `ContingencyBuilder`, `TS.*` field
> constants). This is **completely unrelated** to the `time-step-simulation` project
> (PowerWorld's **TimeStep** weather feature: `.pww` weather → hourly solar/wind MW),
> which uses the low-level `esa` `TimeStep*` script commands, NOT this `ts_solve` API.
> (Intentionally NOT wikilinked — there is no relationship to graph.) The shared letters
> are a coincidence; the
> `TSPFWModelString` field's "TS" likewise means *TimeStep*, not Transient Stability.
> These two never reference each other.

```python
from esapp.utils import TSWatch, ContingencyBuilder
tsw = TSWatch().watch(Gen, [TS.Gen.P, TS.Gen.W])
fields = tsw.prepare(pw)
ctg = ContingencyBuilder("GenTrip", runtime=5.0).at(1.0).fault_bus("101").at(1.1).clear_fault("101")
meta, data = pw.ts_solve("GenTrip", fields)
```

`TSWatch` registers result fields; `ContingencyBuilder` fluently builds transient-stability
event sequences (`SimAction` enum). For dynamics studies only — see [powerworld-simauto](powerworld-simauto.md)
for the underlying `TransientMixin`.

## GObject schema access

Every component class exposes `@classmethod` schema accessors (call with `()`):
`Bus.TYPE()`, `Bus.keys()`, `Bus.fields()`, `Bus.secondary()`,
`Bus.editable()`, `Bus.identifiers()`, `Bus.settable()`.

## Used across

esapp package · esa pp llm · time step simulation ·
reactive power planning · real power planning · synthetic creation ·
dynamic line rating — most PowerWorld work in this wiki routes through it.

## Related

- How-to entry: [esapp-overview](../methods/esapp-overview.md) · underlying COM server: [powerworld-simauto](powerworld-simauto.md)
- Writing devices + DC OPF + N-1 (write-side mechanics): [adding-devices-esapp](../methods/adding-devices-esapp.md)
- Feeds the esa pp llm agent's knowledge base.


---

# ==== gic.md ====

---
type: concept
domain: tooling
aliases: [gic, geomagnetically-induced-current, gmd, geomagnetic-disturbance]
tags: [gic, gmd, powerworld, esapp, transformer, solar-storm]
---

# Concept: GIC — geomagnetically induced current

## Abstract

Geomagnetically induced currents are quasi-DC currents driven into the grid during a
geomagnetic disturbance, flowing through long transmission lines and transformer
neutrals. They cause half-cycle transformer saturation, harmonics, reactive-power
absorption, and in severe cases thermal damage. PowerWorld models GIC natively, and
`esapp` exposes it through `esapp.utils.GIC`. Verified against esapp 0.1.3.

## Connections

- **Up:** [Home](../index.md)
- **Across:** [esapp](esapp.md) · [powerworld-simauto](powerworld-simauto.md) · [glossary](glossary.md)
- **Deeper:** [aux-script-commands](../references/aux-script-commands.md) for the underlying `GIC*` SCRIPT actions

## Content

### The physics, briefly

A changing geomagnetic field induces a geoelectric field at the earth's surface. That
field drives quasi-DC current through any long conductor grounded at both ends — which
describes a transmission line with grounded-wye transformers at each end.

The current is quasi-DC relative to 60 Hz, so it biases the transformer core into
half-cycle saturation. Consequences, in the order they usually matter:

- **Reactive power absorption** rises sharply, depressing voltage
- **Harmonics** appear and can trip protective relays
- **Transformer heating**, which is the damage mechanism in a severe storm

### The API, and the mistake to avoid

**There is no `pw.gic`.** GIC lives in `esapp.utils` as a class you construct with the
`PowerWorld` object:

```python
from esapp import PowerWorld
from esapp.utils import GIC

pw = PowerWorld(r"C:\path\to\case.pwb")
g = GIC(pw)
```

Then:

```python
g.configure(pf_include=True, ts_include=False, calc_mode="SnapShot")
g.storm(maxfield=100.0, direction=90.0, solvepf=True)   # V/km, degrees
g.model()                                               # build the GIC model
G = g.gmatrix(sparse=True)                              # conductance matrix
```

Verified signatures:

| Call | Signature |
|---|---|
| `GIC(pw)` | `__init__(self, pw=None)` |
| `configure` | `(pf_include: bool = True, ts_include: bool = False, calc_mode: str = 'SnapShot') -> None` |
| `storm` | `(maxfield: float, direction: float, solvepf: bool = True) -> None` |
| `model` | `() -> GIC` |
| `gmatrix` | `(sparse: bool = True) -> csr_matrix | ndarray` |

### Other settings on the object

The `GIC` object exposes the modelling knobs as attributes rather than arguments:

| Attribute | Controls |
|---|---|
| `efield_mag`, `efield_angle` | The geoelectric field magnitude and direction |
| `min_kv` | Voltage floor below which branches are excluded |
| `skip_low_r_lines`, `skip_equiv_lines` | Exclude low-resistance or equivalenced branches |
| `segment_length_km` | Line segmentation length for the field integral |
| `hotspot_include` | Include transformer hot-spot heating |
| `pf_include`, `ts_include` | Couple GIC into the power flow and/or transient stability |
| `calc_mode` | `SnapShot` and related calculation modes |
| `zeta`, `eff`, `Px` | Model coefficients |
| `bus_no_sub` | Buses without an assigned substation |
| `update_line_volts` | Whether induced line voltages are refreshed |
| `timevary_csv`, `loadb3d` | Time-varying field input and B3D field data |
| `calc_max_direction` | Solve for the worst-case field direction |
| `A`, `G`, `H` | The assembled model matrices |
| `cleargic` | Clear GIC results |

### Substation grounding is the input that matters most

GIC results are dominated by substation grounding resistance and transformer winding
configuration. A case that has never been prepared for GIC study will have placeholder
grounding data, and it will still produce numbers — plausible-looking, and meaningless.

Before trusting any GIC result, confirm the case actually carries substation grounding
resistances and correct transformer configurations. This is the GIC equivalent of the
silent failures elsewhere in this knowledge base: nothing errors, the answer is simply
not about your system.

### Direction matters, and the worst case is not obvious

GIC magnitude depends on the angle between the geoelectric field and each line. The
worst direction for one transformer is rarely the worst for another, so a single
assumed direction under-reports system risk. Use `calc_max_direction` rather than
guessing, or sweep the direction and keep the envelope.

### Script-level access

Everything above maps to PowerWorld `GIC*` SCRIPT actions — `GICCalculate`,
`GICTimeVaryingCalculate`, `GICSaveGMatrix`, and the PTI/PSLF exchange actions. See
[aux-script-commands](../references/aux-script-commands.md). Reach for those only when the `esapp.utils.GIC` surface does
not cover what you need.

### Scope

This page covers **driving PowerWorld's GIC feature**. It does not teach geomagnetic
hazard assessment, earth-conductivity modelling, or how to choose a storm scenario. For
those, go to the GMD literature and the relevant NERC standards.


---

# ==== glossary.md ====

---
type: concept
domain: tooling
aliases: [glossary, terminology, acronyms, definitions, jargon]
tags: [glossary, terminology, powerworld, esapp, reference]
---

# Concept: Glossary

## Abstract

Every acronym and piece of jargon this knowledge base uses, defined once. Read the
**Pairs that get confused** section even if you skip the rest — `PWW` versus `PFW` alone
has cost people entire afternoons, and mixing them produces results that look right.

## Connections

- **Up:** [Home](../index.md)
- **Across:** [esapp](esapp.md) · [powerworld-simauto](powerworld-simauto.md) · [pww-data](pww-data.md)

## Content

### Pairs that get confused

Read this table before the alphabetical list. These are near-identical names for
entirely different things, and confusing them produces plausible-looking wrong answers
rather than errors.

| These two | Are not the same |
|---|---|
| **PWW** vs **PFW** | `PWW` is a **weather data file** — measurements at stations over time. `PFW` (Power Flow Weather) is a **model string embedded in a generator** that converts weather into MW for that unit. You load a PWW; a PFW is already inside the case. One letter apart, unrelated |
| **`esapp`** vs **`esa`** | Two different Python packages wrapping the same SimAuto server. This kit assumes `esapp`. Do not mix them |
| **`PowerWorld`** vs **`SAW`** | `PowerWorld` is esapp's high-level entry point. `SAW` is the raw SimAuto wrapper beneath it, reached as `pw.esa`. `pw.RunScriptCommand(...)` does not exist; `pw.esa.RunScriptCommand(...)` does |
| **TimeStep** vs **Transient Stability** | *TimeStep* solves a sequence of independent steady-state points across a weather series — a production study. *Transient stability* (the `TS*` actions) simulates sub-second dynamics. Completely different machinery |
| **`Simulator`** vs **`SimAuto`** | Simulator is the program. SimAuto is its automation interface, **licensed separately**. Having one does not mean having the other |
| **`LimViolPct`** on thermal vs voltage rows | The polarity differs between the two. Never rank the two kinds of violation on this field directly — see [reading-violationctg](../methods/reading-violationctg.md) |
| **`.pwb`** vs **`.aux`** | `.pwb` is the binary case file. `.aux` is a text file of data and/or SCRIPT actions that is **merged into** an open case |

### Alphabetical

| Term | Meaning |
|---|---|
| **AC** | Alternating current. An "AC solve" solves the full nonlinear power flow, unlike a DC approximation |
| **ACSR** | Aluminium Conductor Steel Reinforced — the common transmission conductor type |
| **AGC** | Automatic Generation Control — how generation follows load in real time |
| **`.aux`** | PowerWorld Auxiliary file. Text format carrying object data and/or `SCRIPT` action blocks. `LoadAux` **merges** it into the open case rather than replacing anything |
| **Branch** | A transmission line or transformer. Keyed by its two bus numbers plus a circuit identifier |
| **`BusNum`** | A bus's primary key. `BusNum:1` denotes the far end of a branch |
| **CIM** | Common Information Model — a utility data-exchange standard |
| **COM** | Component Object Model, the Windows mechanism SimAuto is built on. A `com_error` is a Windows-level failure, usually meaning SimAuto is unregistered or unlicensed |
| **Contingency / CTG** | A modelled outage. `CTGLabel` is its key. PowerWorld **trims whitespace from `CTGLabel` on load**, so the label you wrote is not always the one you get back |
| **DC solve** | The linearized power-flow approximation. Fast, ignores voltage and reactive power, and **always reports zero mismatch** — it cannot tell you a generation schedule is short |
| **DHI / DNI / GHI** | Diffuse Horizontal, Direct Normal, and Global Horizontal Irradiance. Three different solar measurements; models usually want a specific one |
| **EDIT mode / RUN mode** | PowerWorld's two operating modes. Many data writes are rejected outside EDIT. Switch with `EnterMode` |
| **ERA5** | ECMWF's hourly reanalysis dataset, roughly 0.25° resolution. Good for long historical records |
| **`esapp`** | ESA++, the Python package this kit uses to drive PowerWorld. Provides `PowerWorld`, a bracket interface returning DataFrames, and `SAW` underneath |
| **GIC** | Geomagnetically Induced Current — quasi-DC current driven through the grid by geomagnetic disturbance |
| **HRRR** | NOAA's High-Resolution Rapid Refresh, ~3 km and sub-hourly. Use it to refine a specific window, not to scan a year |
| **Injection group** | A named collection of injections treated as one source or sink in transfer studies |
| **Interface** | A named set of branches whose combined flow is monitored against a limit |
| **Key field** | The column(s) identifying an object: `BusNum` for a bus, `BusNum` + `GenID` for a generator. **Omit them from a DataFrame you write back and the write silently does nothing** |
| **kcmil** | Thousand circular mils — a conductor size unit |
| **LODF** | Line Outage Distribution Factor. How flow redistributes onto other branches when one branch is outaged |
| **Mismatch** | Residual power imbalance at a bus after solving. Near zero means converged — but see *DC solve* |
| **MOC** | Map of Content — a hub page linking a domain's pages. A convention from the source wiki, not a PowerWorld term |
| **MVA / MW / MVAR** | Apparent, real, and reactive power. Branch limits are usually MVA; dispatch is in MW |
| **N-1** | The reliability criterion that the system must survive the loss of any single element |
| **OPF / SCOPF** | Optimal Power Flow, and its Security-Constrained form which additionally respects contingency limits |
| **`.pwb`** | PowerWorld Binary case file — the case itself |
| **PFW** | Power Flow Weather. The model **inside a generator** converting weather to MW. Not a file |
| **Per unit (pu)** | Values normalized to a base. Voltage near 1.0 pu is nominal. Changing the system base re-derives these — see [per-unit-basis-discipline](per-unit-basis-discipline.md) |
| **PTDF** | Power Transfer Distribution Factor. How a transfer between two points distributes across branches |
| **PV / QV study** | Nose-curve and reactive-margin voltage stability analyses. This kit tells you which action runs them, not what they mean |
| **PWW** | PowerWorld Weather file. Station measurements over time — the input to TimeStep |
| **`SAW`** | The SimAuto wrapper object inside esapp, reached as `pw.esa`. Where `RunScriptCommand` lives |
| **SCRIPT action** | A named PowerWorld command such as `SolvePowerFlow` or `SaveCase`, runnable from an `.aux` file or via `RunScriptCommand`. Catalogue: [aux-script-commands](../references/aux-script-commands.md) |
| **Shift factor** | Sensitivity of a branch's flow to a change in injection |
| **SimAuto** | PowerWorld's COM automation server. **Licensed separately from Simulator** |
| **Slack bus** | The bus absorbing system imbalance. It will silently absorb an enormous shortfall and report success, which is why a DC mismatch of zero proves nothing |
| **Super bus** | A group of buses merged by topology processing into one electrical node |
| **TimeStep** | PowerWorld's feature for solving a series of steady-state points across a weather time series. Not dynamics |
| **TS** | Transient Stability. The `TS*` script actions. Genuinely dynamics |
| **UTC** | Coordinated Universal Time. Weather data is usually UTC while case data may be local — check before joining them |

### Terms this kit deliberately does not define

Contingency analysis fundamentals, OPF formulation, PV/QV curve theory, transient
stability theory, and weather science such as dynamic line ratings. This kit is about
**operating PowerWorld**, not teaching power systems. When a task needs that theory, say
so rather than improvising.


---

# ==== lodf.md ====

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
**evaluated and NOT adopted** for reactive power planning — because that work's binding
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
reasons LODF was rejected for reactive planning also **invert** there: that case has 482 corridors over 100%
(worst 296%) rather than 2, and it is a DC study by design so DC's blindness costs it nothing.
See `RESEARCH-2026-08-25.md` in that repo.

### Why it was NOT adopted for reactive power planning

Two independent reasons, both measured — neither is "LODF is inaccurate":

1. **No thermal headroom to discriminate on.** Across all outages, exactly **2 branches**
   exceed 100 % loading (max `1.000014`). TAMU synthetic grids are built N-1 thermally
   secure, so a correct detector runs on a grid engineered to have no positives. *(This is
   itself a reusable validation check for grid statistics: does a synthetic case's rating
   set actually satisfy N-1?)*
2. **N-1 barely moves the ranking.** `Spearman(base-case stress, full-N-1 stress) = 0.8893` —
   the contingency dimension mostly reproduces the base-case stress signal already computed.

And the structural reason it can never carry that work's late stage: **LODF inherits all of DC's
blindness** — no voltage (every bus pinned at 1.0 pu), no reactive power, no losses, no
generator VAr limits / tap changes / switched-shunt action, and it can never return "did not
converge," which is sometimes the physically meaningful answer. Its real violations are
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
- **esapp calls `Branch.LineStatus` read-only. esapp is wrong — but what that costs you
  depends on your version.** `Branch.is_settable('LineStatus')` returns `False`, and that
  flag is a stale generated whitelist, not PowerWorld's answer. PowerWorld's own
  `GetFieldList('branch')` reports `enterable` as *"Depends: Normally enterable except when
  field Lockout is YES"* — esapp's generator keeps only unconditional `Yes` fields and drops
  every conditional one. Through 0.1.x that bad flag *blocked* the write: `pw[Branch] = df`
  raised `Cannot set read-only field(s)`, which is what the 2026-08-10 runs above hit.

  **On 0.2.1 it only warns** — `UserWarning: Read-only field(s) on Branch: ['LineStatus']` —
  **and the write goes through.** ✅ **Verified live 2026-09-10** (~2,000-bus synthetic case, Simulator build
  2026-07-22): `pw[Branch, 'LineStatus'] = 'Open'` opened all 3950 branches; the per-element
  list form opened exactly the one branch intended. So the bracket writer is usable. The
  real hazard is only that the warning scrolls past and looks like a failure when it isn't.

  Do **not** apply the `-W error::UserWarning` mitigation that older revisions of this kit
  suggested — it turns this false alarm into a hard failure on 112 `Branch` fields that
  write fine. See [esapp](esapp.md) for the full count and
  [esapp-script-command-wrappers](esapp-script-command-wrappers.md) for the 0.2.1 change.

  If you would rather not have the warning in your logs at all, `SetData` is equivalent and
  silent:

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


---

# ==== opf-preconditions.md ====

---
type: concept
domain: tooling
aliases: [SolvePrimalLP, DCOPF preconditions, OPF constraints, BGAGC, opf-area-control]
tags: [powerworld, opf, dcopf, scopf, agc, cost-curve, gotcha, synthetic-grid]
---

# What an OPF needs before `SolvePrimalLP` will run at all

## Abstract

PowerWorld's LP OPF refuses to start unless **three** independent preconditions hold at
once: some area under OPF control (`Area.BGAGC = "OPF"`), some generators AGC-able
(`Gen.GenAGCAble = "YES"`), and those generators carrying a cost model that is not NONE.
Miss any one and you get a fatal error, not a degraded solve — which is the good news,
because the third condition is *data* and cannot be switched on honestly. Synthetic cases
routinely ship with all three off, so this is the first wall any OPF work on that case
family hits. This page records the three conditions, the confirmed field names and how
they were confirmed, the integrity trap in "just set a cost model", and the DC power flow
fallback that answers a thermal question without needing any of it. Verified 2026-09-11
on a regional synthetic planning model, Simulator 24.

## Connections

- **Up:** [powerworld-simauto](powerworld-simauto.md) · esapp package · [Home](../index.md)
- **Across:** [aux-only-powerworld](aux-only-powerworld.md) (how this was driven, and the provenance rule that
  settled the field names) · [powerworld-inertia-and-cost-data](powerworld-inertia-and-cost-data.md) (the cost-curve
  silent-zero traps) · [applying-a-dispatch-to-a-case](../methods/applying-a-dispatch-to-a-case.md) (same case family, AGC off) ·
  artifact level validation
- **Deeper:** [esapp-schema-reference](../references/esapp-schema-reference.md) · esa pp llm backend (the SCOPF call sequence)

## Content

### The error, and what it actually means

```
Fatal Error: No Areas or Super Areas set as OPF Constraints
  To correct, on the OPF Area Records (or OPF Super Area Records) display
  toggle the AGC Status field to "OPF" for some areas/super areas
  Also, make sure some generators are set to AGC = YES and have a Cost Model
  that is not NONE.
```

The headline names one condition; the message body names two more. All three are
required. The OPF is not a solver you point at a case — it is a solver that optimises
*specific controls under specific constraints*, and with none declared it has nothing to
do and says so.

| # | Condition | Field | Nature |
|---|---|---|---|
| 1 | an area (or super area) under OPF control | `Area.BGAGC` = `"OPF"` | switch |
| 2 | generators the OPF may move | `Gen.GenAGCAble` = `"YES"` | switch |
| 3 | those generators priced | `Gen.GenCostModel` ≠ NONE | **data** |

### The field names, and how they were confirmed

`BGAGC` is **not** in the *Auxiliary File Format* manual — nor is any other field name,
because that manual carries no per-object catalog (see [aux-only-powerworld](aux-only-powerworld.md)). It was
confirmed instead against esapp 0.2.1's generated schema, offline, without a PowerWorld
session:

```python
from esapp.components import Area
"BGAGC" in Area.fields()          # True  -- one of Area's 444 fields
Area.is_editable("BGAGC")         # True
Area.is_edit_mode_only("BGAGC")   # False -- writable in RUN mode, no EnterMode(EDIT)
```

`Gen.GenAGCAble`, `Gen.GenCostModel`, `Gen.GenCostCurvePoints` and `Gen.GenMCost` all
confirm the same way: real, editable, not edit-mode-only.

⚠ **`AGC_AGCStatus` is not an Area field.** It appears in this vault's prose
([applying-a-dispatch-to-a-case](../methods/applying-a-dispatch-to-a-case.md)) as the area AGC-status field name and does not exist in
esapp's schema. Do not use it. A field name read out of a prose page is a lead, not a fact
— check it against the schema before writing it into a script.

esapp declares no value vocabulary for `BGAGC`, so the literal `"OPF"` rests on
PowerWorld's own error text. If a write does not take, read the field's current value back
and match the spelling you see.

In aux, with `ALL` as the filter keyword (`""` is not legal — see [aux-only-powerworld](aux-only-powerworld.md)):

```
SetData(Area, [BGAGC], ["OPF"], ALL);
SetData(Gen, [GenAGCAble], ["YES"], ALL);
```

Then read both back before believing either. `SetData` reports success on writes that
change nothing.

### Condition 3 is data, and forcing it is a research-integrity failure

Conditions 1 and 2 are switches and may be flipped freely — they change what the OPF is
*allowed* to do, not what the answer is. Condition 3 is different. Setting `GenCostModel`
to something non-NONE without real cost curves means inventing fuel costs, and the
resulting dispatch is then driven entirely by fabricated numbers. It will look like an
economic dispatch, produce a cost column, and mean nothing. **Check whether the case
carries cost data; do not manufacture it.**

Per [powerworld-inertia-and-cost-data](powerworld-inertia-and-cost-data.md), the guard is
`GenCostCurvePoints > 0 AND GenMCost > 0`. `GenCostCurvePoints == 0` means no curve was
ever fit and the cost fields read `0` — which is *no data*, never *free*. A handful of
units can also report `GenMCost == 0` with curve points defined.

Synthetic cases are the live hazard here. A generation pipeline may assign piecewise cost
curves at build time, but whether they survived into the dated case you are holding is a
question about that file, not about the pipeline — so measure it.

**And the measurement can come back unsatisfiable.** On a ~9k-bus synthetic planning model,
2026-09-11:

| Field | Reading |
|---|---|
| `GenCostModel` | `"None"` on **every** unit |
| `GenCostCurvePoints` | `0` on every unit |
| `GenMCost` | zero nonzero values |
| `GenAGCAble` | `"NO"` on all but one |
| `Area.BGAGC` | one area, `"Off AGC"` |

Conditions 1 and 2 were one `SetData` each. Condition 3 had nothing to switch on: the case
simply carries no cost data. **DC OPF is therefore not available on that case at all** until
cost models are populated upstream — not a tuning problem, not a settings problem, an
absent-data problem. Budget for discovering this *before* designing a study around an OPF,
because the recon that answers it costs seconds and the alternative is discovering it at the
solve.

This also fixes the shape of the value vocabulary: `BGAGC` reads back as the
human-readable string `"Off AGC"`, spaces included, which makes `"OPF"` from PowerWorld's
error text the right shape to write.

### `Sim_Solution_Options` is the lowest-priority place to set a solve mode

`SetData(Sim_Solution_Options, [DCApprox], [YES]);` is how the DC approximation gets set in
an aux, and it works — but note the manual documents `Sim_Solution_Options` only as a
SUBDATA section nested inside `Contingency`, `CTG_Options` and `QVCurve_Options`, never as a
standalone `SetData` target. The shape is an analogy to the sibling `Equiv_Options` (which
the manual explicitly says may be set "using the SetData action, or a DATA section"), not a
citation.

What the manual does settle is **precedence**, and it bites the moment OPF meets
contingency analysis:

The manual states that contingency analysis reads power flow solution options from three
places, and applies them in this order of precedence:

1. options stored on the individual contingency record
2. options stored on the contingency tool (`CTG_Options`)
3. the global solution options

**Global solution options rank last.** Setting DC once at the top of an aux does not make it
true during contingency analysis — anything the contingency record or `CTG_Options` carries
overrides it. This is why esa pp llm backend's SCOPF sequence sets both
`Sim_Solution_Options.DCApprox` *and* `CTG_Options.CTG_CalculationMethod`.

### Always give the solve a failure handler

`SolvePrimalLP` takes four optional arguments — a success slot, a failure slot, and two
create-if-not-found flags — and either filename slot accepts the literal `STOP`, meaning
halt all aux execution:

```
InitializePrimalLP("", STOP);
SolvePrimalLP("", STOP);
```

Bare `SolvePrimalLP;` has no failure handler. A refused or non-converged OPF then becomes
one line in the log while every later stage runs against an **unsolved case** and writes
plausible numbers into correctly-named files. `SolveSinglePrimalLPOuterLoop` and
`SolveFullSCOPF` carry the same slots. See [aux-only-powerworld](aux-only-powerworld.md).

### Flipping condition 2 globally is blunt

`GenAGCAble = "YES"` on every unit lets the OPF redispatch the entire fleet, including
units that would never move in operation. Acceptable for a first look; narrow it before
any result is reported.

### The fallback that needs none of this

If the question is *thermal* — what happens to branch loadings when an element is removed —
a **DC power flow** answers it and requires no area control, no AGC flags and no cost data:

```
SetData(Sim_Solution_Options, [DCApprox], [YES]);
SolvePowerFlow(DC);
```

What is lost versus a DC OPF is economic redispatch. On a case whose areas are off AGC
and whose units are almost entirely not AGC-able, very little was being redispatched
anyway, so the gap between the two is far smaller than it sounds.

Two things to carry into the comparison:

- **A DC solve pins every bus to exactly 1.0 pu** ([lodf](lodf.md)). So neither DC OPF nor DC
  power flow yields any voltage answer — a before/after voltage table from a DC run is
  identically zero change. Voltage requires an AC re-solve at the post-change dispatch,
  compared against an AC baseline.
- `pw.dc_mode` is effectively one-way ([lodf](lodf.md)); prefer the explicit script form above and
  verify by checking that the bus voltages really did go to 1.0.


---

# ==== parallel-contingency-solve.md ====

---
type: concept
domain: cross-cutting
aliases: [parallel-contingency-solve, parallel-ctg, os-process-n1-sweep, contingency-parallel]
tags: [contingency, n-1, ctgsolveall, esapp, powerworld, multiprocessing, technique, cross-cutting]
---

# Parallel N-1 Contingency Solve (OS-process level)

## Abstract

A workaround for PowerWorld's own distributed `CTGSolveAll` being non-functional in this
environment: instead of relying on PowerWorld's DS server + registered compute hosts (which never
spawn workers here — it silently degrades to single-process serial), split the case's contingency
set into N chunks and run N independent `pwrworld.exe`/esapp instances as separate OS processes
(Python `concurrent.futures.ProcessPoolExecutor`), each solving a plain serial `CTGSolveAll` on
only its own chunk, then merge the per-bus voltage envelopes. Built for reactive power planning
to unblock a Synth8k N-1 sweep, which was timing out at 7200s
(2 hrs) serial. Live-measured: **~6-7x faster on the 8k case** (18.4 min vs. the 2-hr timeout,
13,470+ contingencies), but only **~1.7-1.8x on a smaller 2k case** (5,344 contingencies) — the
speedup scales with per-contingency solve cost because each worker pays a fixed ~20-45 sec
`open()` overhead that does not parallelize away.

## Connections

- **Up:** [Home](../index.md)
- **Used in:** a reactive planning study, as a parallel contingency-solve wrapper
- **💡 Could apply to (idea transfer):** any PowerWorld study that leans on `CTGSolveAll` for a
  large N-k contingency set — dynamic line rating branch-outage screening, any N-k security
  study; more generally, any SimAuto/COM-driven batch analysis where PowerWorld's own distributed
  computing can't be relied on (no DS server infrastructure).
- **Across:** [esapp](esapp.md) (the SimAuto wrapper each worker process opens independently) ·
  [powerworld-simauto](powerworld-simauto.md) (the COM server underneath — proven safe to open multiple independent
  instances concurrently, the real rule is just "never call `.exit()`")

## Content

### Why PowerWorld's own distributed computing doesn't help here

`CTGSolveAll(distributed=True)` requires a running DS (distributed-solve) server plus registered
compute hosts already set up in PowerWorld Simulator. On this machine, `VerifyDistributedComputersAvailable`
confirms the server is reachable but **zero workers ever actually spawn** — PowerWorld silently
falls back to single-process serial. That's a real, previously-diagnosed blocker: the Synth8k
case's ~13,470-contingency N-1 set was timing out at 7200s (2 hrs) running serial. Distributed
computing settings are also GLOBAL Simulator settings, not serialized into the `.pwb` — so there is
no case-level fix, only an infrastructure one (standing up a real DS server), which is out of scope.

### The workaround: OS-process-level parallelism, not PowerWorld-level

Sidestep PowerWorld's distributed-computing feature entirely and parallelize one level up, at the
OS process level:

```
Case's existing CTGLabel set (already autoinserted + saved to a case file)
        │
        ▼  split into N chunks (np.array_split)
  N independent OS processes, each:
    - opens its OWN esapp/PowerWorld instance on the SAME case file
    - sets CTGSkip=NO only for its own chunk's labels, YES for everything else
    - runs a plain serial CTGSolveAll on just its chunk
    - returns its own per-bus Bus.BusMin/MaxVoltageContingency envelope
        │
        ▼  merge (pure function, no PowerWorld)
  min-of-mins on BusMinVoltageContingency, max-of-maxes on BusMaxVoltageContingency,
  joined on BusNum → same output shape as the serial function
```

This works because concurrent *independent* PowerWorld/esapp instances are safe on this machine —
the earlier assumption of "single-instance SimAuto" was proven wrong by a live probe (3 concurrent
handles, isolated reads+writes); the real rule is just **never call `.exit()`** on a shared/ambient
instance, not "one instance only." Each worker here opens and owns its own instance for its own
process lifetime, so that's a non-issue.

### CPU/RAM headroom — don't naively use `os.cpu_count()` workers

Live-measured on an i9-12900K (16 physical / 24 logical cores): 10 worker processes pegged the
**whole machine** near 100% CPU. Each `pwrworld.exe` worker burns **more than one logical core
internally** (PowerWorld's own sparse-solver threading is not user-controllable or documented), so
"1 worker == 1 logical core" is the wrong mental model — observed ratio was roughly 2.4 logical
threads per worker at `n_workers=10`. A `recommended_workers()` helper computes a conservative
default from both CPU headroom (`(logical_cores − reserve) // per_worker_cores`, defaults
`reserve=2`, `per_worker_cores=3`) and RAM headroom (`available_mb // per_worker_mb`, default
700 MB/worker, measured from the 8k run's actual `pwrworld.exe` footprints of ~150-600 MB each),
returning whichever bound is tighter. On this machine that resolves to **7**, not 10.

### GPU is not an option

PowerWorld's solver (`pwrworld.exe`) is a closed-source CPU sparse-LU Newton-Raphson engine
accessed only through the SimAuto/COM interface. There is no GPU path in PowerWorld itself, and
[esapp](esapp.md) is a thin Python wrapper around that COM interface — it cannot inject GPU acceleration
into solver internals it doesn't control. The only real lever for CTG solve speed here is OS-level
process parallelism (this technique), not GPU offload.

### Correctness check + measured numbers

Because this changes *how* the sweep runs but not the physics, the parallel result should exactly
match the serial baseline's violating-bus set — verified live (`ctg_parallel_demo.ipynb`, both
sweeps run back to back on the same case + same contingency set):

| Case | Contingencies | Serial | Parallel | Workers | Speedup | Match? |
|---|---|---|---|---|---|---|
| Synth2k series25 summerpeak | 5,344 (3,993 line + 1,351 xfmr) | 196-266 s | 107-152 s | 10 | 1.75-1.84x | Yes, exact violating-bus set |
| Synth8k (a ~13.5k-bus working model) | ~13,520 | ~7200 s (prior timeout, never completed) | 1,101 s (18.4 min) | 10 | ~6-7x vs. the timeout budget | 149 violating buses found |

The speedup ratio is **not constant** — it grows with case size / per-contingency solve cost,
because the fixed per-worker `open()` overhead (20-45 sec, does not parallelize away) is a much
smaller fraction of total time on the bigger, slower-per-contingency 8k case than on the smaller 2k
case. Run-to-run variance on the identical 2k case was also notable (196 s vs 266 s, ~35%) — likely
machine/process contention, not a code issue; don't trust a single sample when planning capacity
for a big sweep.

### Scope limitation (deliberate)

This technique parallelizes ONLY the base N-1 voltage sweep, not any per-contingency remediation
walk that mutates a shared base fleet sequentially (e.g. an after-removal security loop) —
that kind of loop can't be split this way since each fix changes state the next step depends on.
It also does not autoinsert contingencies itself — the case must already carry its N-1 set before
the parallel sweep opens it (autoinsert once, save, then hand that saved case path to the workers).


---

# ==== per-unit-basis-discipline.md ====

---
type: concept
domain: cross-cutting
aliases: [per-unit basis, base conversion, normalization base, basis discipline]
tags: [per-unit, normalization, powerworld, gotcha, data-provenance, technique]
---

# Per-unit basis discipline — a normalized number is meaningless without its base

## Abstract

A per-unit or normalized quantity is a **pair**: the number *and* the base it was
normalized against. Store only the number and you have stored nothing recoverable — yet
per-unit values look like plain scalars, so they get copied between sources, written into
shared columns, and summed, with the base silently changing underneath. This page is the
reusable form of a mistake that hit dispatch twice: the second time *because* the
documented fix was written down without its precondition. Read it before mixing a
case-read normalized quantity with a synthesized or textbook one, and before trusting any
"correct formula" recorded from a previous session.

## Connections
- **Up:** [Home](../index.md)
- **Across:** [powerworld-inertia-and-cost-data](powerworld-inertia-and-cost-data.md) (the concrete `TSH` case) ·
  [esapp](esapp.md)
- **Found in:** a generator dispatch study — an inertia-basis regression, and a later round
  of dispatch corrections with the same cause.
- **💡 Applies to:** reactive planning (synchronous-condenser and SVC machine bases) ·
  real-power planning (per-unit r/x/b) · normalized load fractions, where the per-zone and
  whole-system denominators differ · [gic](gic.md) · any study that sums or ranks a
  normalized quantity across heterogeneous equipment

## Content

### The rule

> A per-unit value carries an implicit denominator. Two per-unit numbers are only
> comparable — and only **summable** — if they share a base.

Three failure shapes, in increasing order of nastiness:

1. **Wrong base, uniformly.** Everything is off by one constant factor. Bad, but the error
   is visible in totals and usually caught by a sanity check.
2. **Wrong base, non-uniformly.** The base varies per device, so the error varies per
   device. Totals are wrong *and* any **ordering, ranking, or selection** built on the
   values is wrong. This is far worse, and much harder to spot, because nothing looks
   obviously broken — it just quietly picks the wrong equipment.
3. **Two different bases in one column.** A field populated from two code paths — read
   from source on one, synthesized on the other — where only one path re-bases. The column
   name is now a lie for half its rows.

### The worked case: PowerWorld `TSH`

The inertia constant H (seconds) is per-unit on **each machine's own MVA base**.
PowerWorld's `Gen.TSH` is the same H re-based onto a fixed **100 MVA system base**:

```
TSH = H · GenMVABase / 100          system inertia (GW·s) = Σ TSH · 100 / 1000
```

Both expressions are "inertia in seconds." Neither is wrong. They are not interchangeable.

On the Synth8k case `GenMVABase` spans **2.2 – 1,444.4 MVA (median 170)**, so treating
assumed H as if it were `TSH` produced failure shape **2**: fleet inertia read 240.5 GW·s
instead of 470.3, nuclear 2.04 instead of 22.58, and the unit-commitment order in the
dispatch algorithm was silently wrong.

The physical statement underneath: **H alone is not an inertia quantity.** System inertia is
`M_sys = Σ Hᵢ · MVAᵢ`. Seconds must be size-weighted before they mean anything at system
level — which is also why *unit count is not a proxy for system inertia*.

### The meta-lesson: guidance inherits preconditions

This is the part worth carrying to every other project, and it is why the bug recurred.

The 2026-07-14 session found the original inertia error and recorded the fix as a rule:

> `GW·s = Σ(Gen.TSH) · 100 / 1000` — **do NOT multiply by `GenMVABase`, it's already
> implicit.**

That is correct — *for values read out of a case*. It was written down without the
qualifier, because at the time only one data path existed. Later a case arrived with **no
measured `TSH` at all**, so H had to be synthesized from published typical values. On that
path the rule **inverts**: you must multiply. Anyone — human or agent — following the
recorded guidance while writing the new path would produce exactly the bug that shipped.
And one did, in all three builders.

> **A documented correction is only valid under the conditions of the data it was derived
> from.** When you record a rule, record what made it true. When you *apply* a recorded
> rule, check that its precondition still holds — especially if the data source changed.

Practical habit: state the rule's scope in the same sentence as the rule.
"Don't multiply by the base" → "don't multiply by the base **when reading `Gen.TSH` from
the case, because it is already re-based**."

### How to make it stick (what actually worked)

Documentation alone demonstrably failed here — it was written down and the bug still
recurred. Two mechanical guards were added instead, and both earn their keep:

- **Assert on the physical magnitude, at compute time.** `assert 460 <= fleet_gws <= 480`
  in the notebook cell catches every wrong-base variant regardless of how it was
  introduced, because it checks the *answer*, not the code. Cheap and high-yield.
- **Assert on the code shape, in CI.** A source-level test that greps the conversion works
  without a PowerWorld licence — but write it **precisely**. The first version accepted
  `/ 1000` (because `"100" in "1000"`) and an inverted `H · 100 / GenMVABase`. Anchor the
  regex and mutation-test the guard by reintroducing the bug and confirming it fails. A
  guard that silently accepts the defect is worse than none: it advertises coverage it
  doesn't have.

Prefer the magnitude assert if you only do one. It is source-agnostic and it fires before
a wrong number reaches a document.

### Checklist when a normalized quantity enters a project

- What is the base — system-wide constant, per-device, or per-zone?
- Does every row in this column share it? If the column is populated from more than one
  source, the answer is probably no.
- Does the base *vary across devices*? If yes, a wrong base corrupts **ordering**, not just
  totals — check any ranking or selection downstream.
- Is there a physical sanity band (a published typical range) to assert against?
- If I am reusing a recorded formula: what data path was it derived for, and am I on it?


---

# ==== powerworld-inertia-and-cost-data.md ====

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
evaluation at the case's *current* `GenMW`, not a fixed per-unit rate; (3) a system's official
zonal scheme may already be modelled natively as `AreaNum`/`AreaName`, in which case no
spatial join is needed; (4) a sibling project's fuel-category *name* doesn't
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
  nuclear unit and nearly every coal unit on exactly `4.00` seconds, squarely inside
  the published per-technology ranges operators tabulate (nuclear and coal both sit
  around 3–4.5 s) — not a coincidence at that precision.
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
> **synthesizing** H yourself — assumed values from an operator's published table, a textbook, or any
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
> Physically: **H alone is not an inertia quantity.** System inertia is defined as
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

### 3. Check `AreaNum`/`AreaName` before doing a spatial join

`AreaNum`/`AreaName` are native PowerWorld fields carried on **both `Gen` and `Load`**
objects, and a case is often built with the system operator's own zonal scheme already
encoded in them. Verify that before writing any geographic join: where it is populated,
zonal load and generation analysis needs no spatial work at all.

Don't confuse it with a **custom region field** — typically something like
`CustomString:2`, written by a case-specific spatial join against a boundary shapefile.
Two things regularly make such a field the wrong key: it is usually **generator-scoped
only**, never written to loads, and its distribution can be so dominated by a single
bucket that it differentiates nothing. Check the value distribution before you group by
it. `AreaNum` is the right key for zonal granularity *inside* one system; a region field
is right only when the analysis genuinely spans regions.

### 4. Another project's fuel-category name doesn't always mean what it says

Not a PowerWorld field-semantics gotcha but the same *don't-take-a-label-at-face-value*
family: a companion dispatch script's `"GAS_CT"` category actually maps to Synth8k's
`GenFuelType == "DFO (Distillate Fuel Oil)"`, not `"NG (Natural Gas)"` — confirmed by
reading the source's own fuel-classification code, not inferred from the name.
Conflating the two misassigns `TSH`/cost and mis-totals capacity. General lesson: when
reconstructing per-generator detail from another project's per-category summary
output, verify the category↔`GenFuelType` mapping against that project's actual
classification code, never the category's plain-English name.


---

# ==== powerworld-script-transfer.md ====

---
type: concept
domain: tooling
aliases: [script-transfer, drop-file-aux, SimulatorScriptInput, SimulatorScriptOutput, external-script-control, sced]
tags: [powerworld, aux, script, external-program, llm, simulator-25, undocumented]
---

# Drop-file script transfer: driving Simulator without SimAuto

## Abstract

Simulator 25 beta can watch a directory and execute any `.aux` dropped into it, writing
back the message-log slice produced by that load. Write a file, read a file — **no COM, no
SimAuto call, and therefore no SimAuto licence.** This is the cheapest channel an external
program (an LLM among them) has ever had into PowerWorld, and it is the first one that
needs nothing installed on the caller's side.

**It is not in the *Auxiliary File Format* manual.** Searched 2026-09-12 against the
September 1, 2026 edition: zero hits for `ScriptTransfer`, `SimulatorScriptInput`,
`SimulatorScriptOutput`, `ScriptInputOutputPollSec` and "drop file". The only source is
Overbye's September 2026 slide deck *Recent Modifications to PowerWorld Simulator to Allow
for More Interaction with External Programs*, which describes the functionality as new and
"probably evolving". Everything below is from that deck; nothing here is measured yet.

## Connections

- **Up:** [powerworld-simauto](powerworld-simauto.md) · [Home](../index.md)
- **Across:** [aux-only-powerworld](aux-only-powerworld.md) (what to write *inside* the dropped file — every trap
  and the read-back rule apply unchanged) · [aux-script-commands](../references/aux-script-commands.md) ·
  [esapp-script-command-wrappers](esapp-script-command-wrappers.md) (the Python-side channel this one bypasses)
- **Deeper:** [esapp-schema-reference](../references/esapp-schema-reference.md) (field-name provenance — still mandatory here)

## Content

### What it does

With the feature enabled, every `ScriptInputOutputPollSec` Simulator checks the configured
directory for a file named exactly **`SimulatorScriptInput.aux`**. If it is there:

1. the aux file is **loaded** (i.e. executed — unnamed `SCRIPT{}` blocks auto-run, see
   [aux-only-powerworld](aux-only-powerworld.md)),
2. the input file is **deleted**,
3. **`SimulatorScriptOutput.txt`** is written into the same directory, containing the new
   message-log entries associated with that load.

That is the whole protocol. Request is a file appearing; response is a file appearing; the
deletion of the request is the acknowledgement.

### Turning it on

Two preconditions the deck states explicitly, and both are real constraints rather than
setup steps: **a case must already be loaded**, and **the Script Command Execution Dialog
(SCED) must be visible**. Tools → Script opens it.

In the SCED:

| Field | Registry name (PowerWorld section) |
|---|---|
| Enabled External Script Control | `ScriptTransferFileEnabled` |
| ScriptTransferFileDirectory | `ScriptTransferFileDirectory` |
| Script File Poll Interval | `ScriptInputOutputPollSec` |

Settings persist in the registry, so this is configurable ahead of a session rather than
only through the dialog.

### The shape of a request

From the deck's worked example, on PowerWorld's own shipped `B7Flat` case:

```
// First change the generator status
DATA (Gen [ObjectID, STATUS])
{
"Gen 1 '1'" "Open"
}
// Then solve the power flow
SCRIPT{SolvePowerFlow;}
```

Two things to copy from this rather than invent:

- **`DATA` + `ObjectID` is a compact one-field key.** `"Gen 1 '1'"` identifies the unit
  without a separate `BusNum`/`GenID` pair. The manual documents `ObjectID` as an
  identifier form on several commands, so this is not deck-only syntax.
- **A single dropped file mixes `DATA` and `SCRIPT` blocks and they run in file order.**
  The edit lands, then the solve runs against it.

The corresponding `SimulatorScriptOutput.txt` is the raw log slice — `1 records read from
file.`, the AGC adjustments, the mismatch iterations, `Simulation: Successful Power Flow
Solution`, bracketed by `Starting load of auxiliary file:` and `Finished load of auxiliary
file:` lines.

### Write it elsewhere, then copy it in

The deck says to create `SimulatorScriptInput.aux` and "store it somewhere other than in
this directory", then copy it into the watched directory. Treat that as mandatory. The
poller has no way to tell a finished file from one still being written, so authoring in
place races the poll interval and can feed Simulator half an aux — which, given that a
truncated script is still a *valid* script up to the truncation point, is the silent
failure this whole vault exists to prevent.

An atomic move within the same volume is the safer version of the same idea.

### What it does not give you

The output is a **log transcript, not a return value.** `SolvePowerFlow` succeeding or
failing shows up as English in a text file, not as a status your caller can branch on
without parsing. So:

- **The read-back discipline from [aux-only-powerworld](aux-only-powerworld.md) applies unchanged.** If the
  answer matters, `SaveData` it to a CSV and read the CSV. Do not infer success from the
  output file merely existing.
- `Simulation: Successful Power Flow Solution` is the string worth grepping for, but its
  absence is not the same as a specific diagnosis.
- This is **not headless**. A visible GUI dialog is required, so it does not replace
  [esapp](esapp.md) for batch or parallel work — see [parallel-contingency-solve](parallel-contingency-solve.md).

### Open questions to settle by experiment

None of these are answered by the deck, and each one changes how a caller must be written:

- Is `SimulatorScriptOutput.txt` **overwritten or appended** on each cycle?
- Is there any signal that the output file is **complete**, or must the caller poll for
  size stability?
- What happens when the aux **fails to parse** — is an output file written at all, and does
  the input file still get deleted?
- Does `StopAuxFile` or `ExitProgram` inside a dropped file behave sanely here?
- What is the **minimum usable poll interval**, and does a short one cost anything?
- Does a second `SimulatorScriptInput.aux` dropped mid-execution get picked up, queued, or
  lost?

### Version floor

**Simulator 25 beta, build date on or after September 12, 2026.** Earlier builds do not
have it, including every Simulator 24 build regardless of patch date. See
[version-requirements](version-requirements.md).


---

# ==== powerworld-simauto.md ====

---
type: tool
domain: tooling
aliases: [simauto, simauto-com, powerworld-com, saw]
tags: [powerworld, simauto, com, tool]
---

# PowerWorld SimAuto

## Abstract

SimAuto is PowerWorld Simulator's COM Automation Server — the Windows-only layer that all PowerWorld Python scripts ultimately talk to. In esapp it is wrapped by the `SAW` class (assembled via ~20 mixins) and reached through `pw.esa`. This page covers the SAW mixin architecture, verified raw COM method signatures for data, scripting, solving, and state management, and the exception hierarchy. Use it when the high-level `pw[...]` bracket API isn't sufficient and you need to call `pw.esa` directly.

## Connections

- **Up:** [Home](../index.md)
- **Across:** [esapp](esapp.md) · esapp package · [esapp-overview](../methods/esapp-overview.md) · esa pp llm · aux script catalog · [esapp-script-command-wrappers](esapp-script-command-wrappers.md) (named wrapper over `RunScriptCommand`, the house rule)

## Content

**SimAuto** is PowerWorld Simulator's COM **Automation Server** — it exposes the
running simulator to external scripts (open cases, read/write objects, solve
power flow, run script commands, switch EDIT/RUN modes). It is the layer
*underneath* [esapp](esapp.md). In esapp it is wrapped by the **`SAW` (SimAuto Wrapper)**
class and reached through `pw.esa`. Because it is a COM server, everything here
is **Windows-only** (esapp talks to it via `pywin32`).

## SAW — the wrapper esapp puts on top

`SAW` lives in `esapp/saw/saw.py` and is assembled by the **mixin pattern**:
`SAWBase` (`saw/base.py`, core COM interface + case management + generic data
retrieval) plus ~20 capability mixins — `DataMixin`, `PowerflowMixin`,
`MatrixMixin`, `ContingencyMixin`, `TransientMixin`, `SensitivityMixin`,
`GICMixin`, `OPFMixin`, `PVMixin`, `QVMixin`, `ATCMixin`, `FaultMixin`,
`TopologyMixin`, `RegionsMixin`, `ModifyMixin`, `GeneralMixin`,
`CaseActionsMixin`, `ScheduledActionsMixin`, `TimeStepMixin`, `WeatherMixin`.

You rarely instantiate `SAW` directly — `PowerWorld.open()` does
`SAW(fname, CreateIfNotFound=True, early_bind=True)` and stores it on `pw.esa`.

## Raw calls (when the bracket interface isn't enough)

Real method names, verified in `esapp/saw/`:

```python
# Generic read/write (esapp/saw/data.py)
pw.esa.GetParametersMultipleElement("Bus", ["BusNum", "BusPUVolt"])
pw.esa.GetParamsRectTyped("Bus", ["BusNum", "BusPUVolt"])          # typed DataFrame; backs pw[...]
pw.esa.ChangeParametersSingleElement("Gen", ["BusNum","GenID","GenMW"], ["1","1","100"])
pw.esa.ChangeParametersMultipleElement("Gen", cols, values)
pw.esa.ChangeParametersMultipleElementRect("Bus", cols, df)        # backs pw[Type] = df

# Mode + scripting (saw/general.py, saw/base.py)
pw.esa.EnterMode("EDIT"); pw.esa.EnterMode("RUN")                  # or PowerWorldMode.EDIT/.RUN
pw.esa.SolvePowerFlow()          # call the NAMED wrapper, not RunScriptCommand: 310
                                 # SCRIPT commands are wrapped, and the wrapper gives you a
                                 # typed signature plus correct argument-string building.
                                 # The real win is ONE PATCH POINT — a hand-written string
                                 # is a call site the esapp maintainer can never reach when
                                 # PowerWorld changes a command's syntax. esapp does NOT
                                 # introspect PowerWorld's command table or check the
                                 # Simulator version; this is an upgrade path, not a
                                 # runtime check.

# Solve / matrices / TS (saw/powerflow.py, matrices.py, transient.py)
pw.esa.SolvePowerFlow(SolverMethod.RECTNEWT)
pw.esa.get_ybus(); pw.esa.get_jacobian()
pw.esa.TSInitialize(); pw.esa.TSSolve(ctg); pw.esa.TSGetResults(...)

# State save/restore (used by pw.snapshot())
pw.esa.SaveState(); pw.esa.LoadState()
```

`EnterMode` accepts the `PowerWorldMode` enum or the raw strings `"EDIT"` /
`"RUN"`. Object creation through the bracket interface needs **EDIT mode** plus
`CreateIfNotFound=True` on the SAW.

## Why it matters here

Everything in this wiki that touches a `.pwb` case ultimately goes through
SimAuto. esapp wraps it so you almost always use `pw[...]` and `pw.pflow()`
instead of raw COM, but the raw calls remain available on `pw.esa` for anything
the high-level API doesn't cover (time-step runs via `TimeStepMixin`, weather
via `WeatherMixin`, OPF/PV/QV, fault analysis, etc.).

## Exceptions

SAW raises a typed hierarchy rooted at `PowerWorldError` (`saw/_exceptions.py`):
`COMError`, `CommandNotRespectedError`, `SimAutoFeatureError`,
`PowerWorldPrerequisiteError`, `PowerWorldAddonError`. The bracket-write path
keys off `PowerWorldPrerequisiteError` ("not found") to decide whether to create
new objects.

## Related

- Wrapped by [esapp](esapp.md) · used by esapp package
- How-to: [esapp-overview](../methods/esapp-overview.md) · feeds esa pp llm


---

# ==== pww-data.md ====

---
type: dataset
domain: weather
aliases: [pww, pww-file, powerworld-weather, powerworld-weather-data]
tags: [pww, weather, dataset, binary-format, era5, hrrr, noaa]
---

# PWW data (PowerWorld Weather)

## Abstract

PWW (PowerWorld Weather) is a custom byte-packed binary format produced by weather auto and consumed by PowerWorld Simulator's TimeStep Simulation engine. It encodes gridded weather variables as uint8 values (0–254) per timestep and grid point, with 255 as the NaN sentinel. This page covers the VERSION 2 binary spec, variable encoding formulas, per-source production pipelines (ERA5, HRRR, GFS, WRF), and verification procedures. Drill deeper when writing or debugging a PWW file, or tracing weather data into a timestep study.

## Connections

- **Up:** [Home](../index.md)
- **Across:** weather sources · weather auto · [timestep-simulation](timestep-simulation.md) · dynamic line rating · extreme temperature · pfw copperplate · flagship step 3 — prev: [timestep-simulation-setup](../methods/timestep-simulation-setup.md) · next: [how-to-analyze-results](../methods/how-to-analyze-results.md)

## Content

**Step 3 of the flagship trail.** ← prev: [timestep-simulation-setup](../methods/timestep-simulation-setup.md) · next: [how-to-analyze-results](../methods/how-to-analyze-results.md).

> **Firewall: PWW ≠ PFW.** PWW = weather *data* files (this page). PFW = the PowerFlow Weather *model* used in pfw copperplate. Never cross-link their aliases.

PWW is a **custom byte-packed binary format** produced by weather auto and consumed by PowerWorld Simulator's TimeStep Simulation engine. It encodes gridded weather variables at discrete timesteps as uint8 values, one byte per variable per grid point per timestep.

## Binary Format (VERSION 2)

All values are **little-endian**. Types: `h`=int16, `i`=int32, `d`=float64, `u8`=uint8.

```
Offset  Type    Field
──────  ──────  ───────────────────────────────────────────────────────────
0       h       KEY1 = 2001
2       h       KEY2 = 8066  (8065 = VERSION 1; 8066 signals VERSION 2)
4       h       VERSION = 2
6       d       date_min  (OLE automation date — days since 1899-12-30)
14      d       date_max
22      d       lat_min / lat_max / lon_min / lon_max   (4 × d = 32 bytes)
54      h       META_STRINGS  (≥ 1 for VERSION 2)
56      cstr[]  meta_strings[META_STRINGS]  — "PowerWorld Timestep Simulation Weather\0"
─       i       COUNT       (number of timesteps)
─       i       SAMPLE_seconds  (3600=hourly, 900=15-min subh, 0=irregular)
─       i       LOC         (number of stations / grid points)
─       h       LOC_FC = 0
─       h       VARCOUNT
─       h[]     var_codes[VARCOUNT]
─       h       BYTECOUNT = VARCOUNT  (always VARCOUNT when all vars are uint8)
─       i[]     valid_counts[VARCOUNT]   ← VERSION 2 only — non-255 count per variable
─               station_records[LOC]   lat(d), lon(d), elev(h), who(cstr), country(cstr), region(cstr)
─       u8[]    data_array[COUNT × VARCOUNT × n_lat × n_lon]  — C order, 255 = NaN sentinel
```

**Grid dimensions** are derived from header bounds (ERA5 grid is 0.25°):
```python
n_lat = round((lat_max - lat_min) / 0.25) + 1
n_lon = round((lon_max - lon_min) / 0.25) + 1
```

**Longitude convention:** descending east→west (e.g. −60 → −130 for CONUS). Lat is ascending south→north.

**OLE epoch:** 1899-12-30. Timestamps before this date encode as negative and PowerWorld rejects the file — pre-1900 data must be re-based forward (the WRF 1899 job shifted to 1999, +100 years, preserving month/day/hour).

## VERSION 2 Traps (undocumented — the spec doc only covers VERSION 1)

Three requirements that are silently missing from the format doc but are critical for PowerWorld to parse the file correctly:

1. **KEY2 = 8066** (not 8065 — this magic number signals VERSION 2 to the loader)
2. **META_STRINGS ≥ 1** with at least one description string
3. **VARCOUNT × int32 valid_count block** between BYTECOUNT and station data — counts non-255 values per variable

Without all three, PowerWorld misaligns the byte stream: station block bytes are read as valid counts, producing nonsense `ValidPercent*` values (e.g. 1267%, 990%) and shifted variable readings (temperature showing cloud cover bytes, etc.).

## Variable Codes and Encoding

All values stored as **uint8 (0–254)**; **255 = NaN sentinel** (excluded from valid counts).

| Code | Variable | Encoding formula | Unit stored |
|------|----------|-----------------|-------------|
| 102 | tempF | `round(°F + 115)` | °F+115 offset |
| 104 | DewPointF | `round(°F + 115)` | °F+115 offset |
| 106 | WindSpeedmph | `round(m/s × 2.236936)` | mph (10 m) |
| 107 | WindDirection | `round(degrees / 5)` — division INSIDE round() | ×5 to decode |
| 119 | CloudCoverPerc | `round(fraction × 100)` — GFS/ERA5 tcc is 0.0–1.0, must ×100 | % |
| 110 | WindSpeed100mph | `round(m/s × 2.236936)` | mph (100 m) — ERA5, GFS |
| 112 | WindSpeed80mph | `round(m/s × 2.236936)` | mph (80 m) — HRRR only |
| 120 | GHI | `round(W/m² / 5)` | ×5 to decode |
| 121 | DHI | `round(W/m² / 5)` | ×5 to decode |
| 136 | WindGust | `round(m/s × 2.236936)` | mph |
| 151 | PrecipitationRate | `round(kg/m²/s × 3600)` | mm/hr |
| 150 | PercentFrozenPrecip | direct percent byte | % — HRRR only |
| 122 | VerticallyIntegratedSmoke | `round(40 × log10(colmd × 1e6))` | dBZ-equiv — HRRR only |

**Wind direction encoding trap:** the division MUST be inside `round()` — `round(degrees / 5)`, never `round(degrees) / 5`. The latter truncates (not rounds) on uint8 cast, causing up to 4° systematic error.

**Code-112 PowerWorld bug:** PowerWorld's TimeStep loader throws an access violation on code 112 (no loadable 80 m wind field in PowerWorld). HRRR pipelines deliberately keep 112 because their wind is genuinely 80 m — this is a confirmed vendor bug under pursuit. Do NOT remap 112→110.

## How PWW Is Produced

weather auto runs four Docker pipelines, each writing a different PWW flavor:

| Pipeline | SAMPLE_sec | Variables | Output naming |
|----------|-----------|-----------|---------------|
| ERA5/CDS | 3600 (hourly) | 9 (no precip/smoke) | `{Region}{YYYY}_Q{Q}.pww` |
| NOAA/GFS forecast | 3600 | 8 (no DHI — written as 255) | `Forecast_{Region}_Run{YYYY-MM-DD}T{HH}Z.pww` |
| HRRR Forecast | 3600 | 10 | `{YYYY-MM-DD}T{HH}Z_sfc_48_CONUS.pww` |
| HRRR History (15-min) | 900 | 10 | `{YYYY-MM-DD}_Q{1..4}_subh_15min_CONUS.pww` |
| HRRR History (hourly) | 3600 | 10 | `{YYYY-MM-DD}_hourly_CONUS.pww` |
| WRF (Dr. Bailey) | varies | 9 (no precip) | `WRF_{period}_{Region}.pww` |

ERA5 also emits a human-readable `.parquet` alongside the PWW.

## Who Consumes PWW

- dynamic line rating — weather around each line for IEEE 738 thermal rating
- extreme temperature — hottest/coldest scenario identification
- pfw copperplate — weather inputs for the PFW model on renewables
- Any [timestep-simulation](timestep-simulation.md) study needing time-varying weather driving

## Using PWW in a Study

1. Pick spatial/temporal crop (via weather website API or weather extract)
2. Map weather to case elements (lines, renewable units, load zones)
3. Feed per-timestep into the run — see [timestep-simulation-setup](../methods/timestep-simulation-setup.md)
4. Analyze → [how-to-analyze-results](../methods/how-to-analyze-results.md)

## Verifying a PWW (do both before trusting a new file)

1. **Structural + positional round-trip** (offline): parse header, assert KEY2=8066, VERSION=2, ≥1 meta string, valid_count block length == VARCOUNT, data size == COUNT × VARCOUNT × LOC. Then pick a few stations and confirm decoded bytes match the source grid cell at that (lat, lon).
2. **PowerWorld load test:** `TimeStepLoadPWW(file, "Weather Only")` via ESA/SimAuto — exit 0 = file loads cleanly. Pass absolute paths (PowerWorld resolves relative paths against its own working dir). Script: `DrBailey_WRF_pww/pww_powerworld_smoketest.py`.

## Related

- weather sources — upstream ERA5 / HRRR / NOAA feeds
- weather auto — pipeline that builds and stores PWW
- [Home](../index.md)


---

# ==== timestep-simulation.md ====

---
type: concept
domain: cross-cutting
aliases: [timestep-simulation, time-step-simulation-concept, temporal-simulation]
tags: [timestep, simulation, powerworld, weather, renewables, concept]
---

# Timestep simulation (concept)

## Abstract

A timestep simulation (in this project's sense) is PowerWorld's built-in TimeStep feature run over a weather time series: each renewable generator's hourly solar or wind MW output is computed quasi-statically from PWW weather data via its embedded PFW model. This is not a transient-stability study — it has nothing to do with faults or rotor angles. For how to set one up and run it see [timestep-simulation-setup](../methods/timestep-simulation-setup.md); for the code see time step simulation.

## Connections

- **Up:** [Home](../index.md) · time step simulation
- **Across:** [pww-data](pww-data.md) · [timestep-simulation-setup](../methods/timestep-simulation-setup.md) · [how-to-analyze-results](../methods/how-to-analyze-results.md)

## Content

In **this project's** sense, a "timestep simulation" is a run of PowerWorld's
built-in **TimeStep** feature: a power-system case is stepped through a sequence of
weather timestamps so PowerWorld computes, for each renewable generator, how much
**solar** or **wind** MW it would produce at every hour. This is *not* a
transient-stability / dynamics study and has nothing to do with faults or rotor
angles — it is a quasi-static, hour-by-hour weather-to-generation evaluation.

This page is **what it is**; for **how to set one up and run it** see the method
[timestep-simulation-setup](../methods/timestep-simulation-setup.md); for the engine/code see the project
time step simulation.

## How it works conceptually
1. A weather time series ([pww-data](pww-data.md)) is loaded into the case
   (`TimeStepLoadPWW`).
2. Each renewable generator carries an embedded **PFW (PowerFlow Weather) model**
   that maps weather (irradiance, wind speed, etc.) to MW.
3. PowerWorld walks every timestep, applies the weather, and records each
   generator's output (`TimeStepDoRun`).
4. The result is an hourly MW table per generator, split into solar and wind.

## Why it matters
- Converts gridded weather into grid-relevant generation numbers, hour by hour.
- Lets historical years (ERA5 quarter files) and forecast files alike be turned
  into generation profiles for downstream studies.
- Feeds extreme-scenario and renewable-integration analysis.

## Series vs parallel
The time step simulation project runs it **series** (slow, for testing) and
**parallel** (fast, many sims at once). Output resolution is currently
**generator-level** — area/substation-level aggregation is a noted future extension.

## Related
- [timestep-simulation-setup](../methods/timestep-simulation-setup.md) · [how-to-analyze-results](../methods/how-to-analyze-results.md) · [pww-data](pww-data.md) · [Home](../index.md)


---

# ==== timestep-workflow.md ====

---
type: concept
domain: cross-cutting
aliases: [timestep-workflow, time-step-simulation, timestep-engine, weather-to-mw]
tags: [timestep, simulation, powerworld, weather, renewables, pww, parallel]
---

# Concept: The weather-to-MW timestep workflow

## Abstract

The end-to-end chain that turns a weather file into hourly solar and wind output for
every renewable generator in a case: open the case, load a `.pww`, select the renewable
units, tell PowerWorld which fields to save, run its built-in TimeStep simulation, and
export per-generator CSVs. PowerWorld does the weather-to-MW conversion itself using
each unit's embedded PFW model. This is a quasi-static production study, **not** a
transient stability run.

## Connections

- **Up:** [Home](../index.md)
- **Across:** [timestep-simulation](timestep-simulation.md) · [pww-data](pww-data.md) · [copper-plate](copper-plate.md) · [teamoverbyeweather-client](../methods/teamoverbyeweather-client.md)
- **Next:** [timestep-simulation-setup](../methods/timestep-simulation-setup.md) to write the code, then [how-to-analyze-results](../methods/how-to-analyze-results.md)
- **Deeper:** [time-step-simulation-backend](../references/time-step-simulation-backend.md)

## Content

### What it is, and what it is not

PowerWorld's TimeStep feature solves a sequence of independent steady-state points, one
per timestamp. It is a production-cost-style study, not dynamics: there is no swing
equation, no machine model, no sub-second behaviour. If you want transient stability,
that is the `TS*` family of script actions and a completely different setup.

The name collision causes real confusion. "Timestep simulation" here means hourly
snapshots across a weather series.

### The chain

1. **Copy the case to a temporary `.pwb`.** The run mutates the case; work on a copy so
   a failed run does not leave your original in a strange state.
2. **Open it** with `esapp`.
3. **Load weather** with `TimeStepLoadPWW`, or `TimeStepLoadPWWRangeLatLon` to crop to a
   lat/lon box at load time. Append further files with `TimeStepAppendPWW`.
4. **Select the renewable generators** — typically those whose fuel type contains `WND`
   or `SUN`. Only selected units produce output.
5. **Declare the fields to save** with `TimeStepSaveFieldsSet(GEN, ...)`. Fields not
   declared here are simply absent from the results, with no warning.
6. **Run** with `TimeStepDoRun()`. Debug a broken setup with
   `TimeStepDoSinglePoint()` first — it solves one timestamp and fails in seconds
   rather than after a long run.
7. **Export** with `TimeStepSaveResultsByTypeCSV`.

### PowerWorld does the conversion

You do not compute power curves. Each renewable unit carries an embedded **PFW** (Power
Flow Weather) model string, and PowerWorld applies it to convert weather into MW for
that specific unit. Your job is to supply weather and select units; the physics is
already in the case.

If a unit produces nothing, the usual cause is that it has no PFW model rather than
anything wrong with your weather.

**PWW and PFW are different things.** PWW is the weather data file; PFW is the
generator's weather-to-power model. The names are one letter apart and confusing them
wastes an afternoon. See [pww-data](pww-data.md).

### Reading the output

The exported CSVs are not plain tables. Expect **eight metadata header rows** before the
data begins — read past them or every column parses as text. Timestamps commonly need
a timezone conversion, and the natural final step is splitting the table into a solar
file and a wind file.

Details in [how-to-analyze-results](../methods/how-to-analyze-results.md).

### Series and parallel

A series runner processes timestamps one at a time: slow, but its errors are legible.
A parallel runner using a process pool is dramatically faster because each timestamp is
independent, which makes this an unusually clean parallel problem.

Develop against the series runner and switch to parallel for production. Debugging a
process pool that is failing on one timestamp out of eight thousand is a bad way to
spend a day.

### Copper-plate cases

These studies often run on a copper-plate version of the case — transmission constraints
removed — because the question is usually "what could these renewables have produced?"
rather than "what could have been delivered?" See [copper-plate](copper-plate.md).

Deciding which question you are asking, before the run rather than after, saves
rerunning it.

### Granularity

The workflow is generator-level. Aggregating to area or substation is a post-processing
step on the exported CSVs, not something to ask PowerWorld for during the run.


---

# ==== version-requirements.md ====

---
type: concept
domain: tooling
aliases: [version-requirements, powerworld-version, simulator-version, compatibility, version-check]
tags: [version, compatibility, simulator, simauto, requirements, preflight]
---

# Concept: PowerWorld version requirements

## Abstract

Which PowerWorld version you need, how to find out which one you have, and what this
knowledge base was verified against. Everything here was tested on **Simulator 24, build
24.2026.7.22** — 13 of 14 feature areas confirmed working. Field availability and
script-action behaviour both shift between releases, and they shift *silently*.

## Connections

- **Up:** [Home](../index.md)
- **Across:** [preflight-powerworld](../methods/preflight-powerworld.md) · [esapp-environment](esapp-environment.md) · [powerworld-simauto](powerworld-simauto.md) · [glossary](glossary.md)

## Content

### Find your version — three ways

**1. From Python, during preflight** — no admin rights needed:

```python
import win32com.client
from datetime import date, timedelta

sa = win32com.client.Dispatch("pwrworld.SimulatorAuto")
build = date(1899, 12, 30) + timedelta(days=int(sa.RequestBuildDate))
print("PowerWorld build date:", build.isoformat())
```

`RequestBuildDate` is a Delphi serial date — days since 1899-12-30, not a version number.
`46225` decodes to `2026-07-22`.

**2. From the executable** (PowerShell), which gives the real version string:

```powershell
Get-ChildItem 'C:\Program Files\PowerWorld\Simulator*\pwrworld.exe' |
  ForEach-Object { $_.VersionInfo.ProductVersion }
# 24.2026.7.22
```

The format is `<major>.<year>.<month>.<day>` — major version 24, built 2026-07-22.

**3. From the registry**, which also reveals where SimAuto actually points:

```powershell
(Get-ItemProperty 'HKLM:\SOFTWARE\Classes\pwrworld.SimulatorAuto\CLSID').'(default)'
```

Then look up that CLSID's `LocalServer32` to see the exact `pwrworld.exe` being served.

**Watch for stale registry keys.** A machine can carry `Simulator 22` and `Simulator 23`
keys from previous installs while SimAuto actually serves Simulator 24. The CLSID lookup
is authoritative; the version-numbered keys are not.

### What this kit was verified against

| | |
|---|---|
| **Simulator** | 24, build `24.2026.7.22` |
| **`esapp`** | 0.1.3 — what the pages here were live-tested against. 0.2.1 is current and changes write behaviour; see [esapp-script-command-wrappers](esapp-script-command-wrappers.md) |
| **`TeamOverbyeWeather`** | 0.4.0 |
| **Python** | 3.13, 64-bit |
| **Platform** | Windows |

### Feature probe results on that install

| Feature | Pages | Result |
|---|---|---|
| AC power flow | [esapp-overview](../methods/esapp-overview.md) | OK |
| DC mode | [power-flow-and-sensitivities](../demos/power-flow-and-sensitivities.md) | OK |
| LODF | [lodf](lodf.md) | OK — 89 rows |
| PTDF | [power-flow-and-sensitivities](../demos/power-flow-and-sensitivities.md) | OK — 89 rows |
| Ybus | [esapp](esapp.md) | OK — (37, 37) sparse |
| Jacobian | [esapp](esapp.md) | OK |
| `CTGAutoInsert` | [contingency-and-aux](../demos/contingency-and-aux.md) | OK — 89 contingencies |
| `CTGSolveAll` | [reading-violationctg](../methods/reading-violationctg.md) | OK — 12 violation rows |
| `CreateData` (Branch) | [adding-a-device](../demos/adding-a-device.md) | OK — 89 → 90 |
| `SaveCase` script action | [save-powerworld-case](../methods/save-powerworld-case.md) | OK |
| `LimitSet` `SetData` | [powerworld-limitset-setdata](../methods/powerworld-limitset-setdata.md) | OK |
| GIC | [gic](gic.md) | OK |
| `LoadAux` | [contingency-and-aux](../demos/contingency-and-aux.md) | OK — merged 89 → 94 |
| TimeStep family | [timestep-workflow](timestep-workflow.md) | Prerequisite error on an empty case (expected) |

That last row is worth reading correctly. `TimeStepClearResults` raised
`PowerWorldPrerequisiteError` because there were no TimeStep results to clear — that is
the feature working, not a version problem. Prerequisite errors are about **case state**,
not capability.

### Minimum versions

**Not tested here.** Only Simulator 24 was available, so every claim above is about 24.

What can be said honestly:

- The core surface — power flow, contingency analysis, `CreateData`, `SaveCase`,
  sensitivities, TimeStep, GIC — has been present in Simulator for many releases. It is
  very unlikely you need 24 specifically.
- The [aux-script-commands](../references/aux-script-commands.md) index was compiled against Simulator 24's action set. Older
  releases have fewer actions; newer ones may add some.
- **If you are on an older version and something in this kit fails, the version is a
  plausible cause.** Say so rather than assuming the page is wrong — and if you confirm
  it, that is worth an issue on the repository.

### Version-sensitive behaviour to watch for

These shift between releases and fail *silently*, which is what makes them dangerous:

| Behaviour | Why version matters |
|---|---|
| **Field availability** | A field can exist and return blank in one release and be populated in another. Derived weather fields have done exactly this. Check for all-null columns before trusting any derived field |
| **Script action names and arguments** | Actions are added, and argument lists occasionally change. An unrecognised action is not always a loud failure |
| **Required key fields for `CreateData`** | The required set is version-specific. A call that worked on an older release can silently no-op on a newer one — which is why [adding-a-device](../demos/adding-a-device.md) insists on asserting the object count |
| **Default limit sets and monitoring** | Defaults change, which changes what counts as a violation without changing your code |

### The SimAuto licence is not a version question

Worth separating, because people conflate them: **SimAuto is licensed separately from
Simulator**, and having the newest Simulator does not mean you have automation. A perfect
Simulator 24 install can fail every script in this kit.

On a working install you will see `PWSimAutoService.exe` alongside `pwrworld.exe` in the
Simulator directory, and `Dispatch("pwrworld.SimulatorAuto")` will succeed. If it raises,
see [preflight-powerworld](../methods/preflight-powerworld.md) — no code change fixes a licence.

### What to do at the start of a session

Run [preflight-powerworld](../methods/preflight-powerworld.md). It reports the build date along with the five checks, so
the version is on the record before any analysis is written. If a later result looks
wrong, that line is the first thing to check.


---
