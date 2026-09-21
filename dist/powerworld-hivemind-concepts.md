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

# ==== builtin-distributed-computing.md ====

---
type: concept
domain: tooling
aliases: [distributed-computing-add-on, distributed-computer-list, verify-computers-available, ds-server]
tags: [powerworld, distributed-computing, contingency, atc, transient-stability, pv-qv, silent-failure]
---

# Simulator's built-in Distributed Computing add-on

## Abstract

[Parallel N-1 contingency solve](parallel-contingency-solve.md) exists because
Simulator's own Distributed Computing add-on silently fell back to single-process
serial on this machine. This page is the checklist that workaround never needed to
follow through on: what the built-in feature actually requires before it will run
anything on a remote or even a local core, and the specific settings that make it
degrade quietly rather than error. It is a paid add-on, separate from SimAuto,
configured once as global Simulator options rather than per-case.

## Connections

**Up:** [Home](../index.md) · **Across:** [parallel-contingency-solve](parallel-contingency-solve.md) · [lodf](lodf.md) ·
[post-contingency-aux-state-carryover](post-contingency-aux-state-carryover.md) (a different
Contingency Analysis batch-run hazard — that page's per-contingency aux hooks leak state
across a serial run, this page's worker chunking is what makes the run parallel in the
first place) · **Deeper:** [esapp](esapp.md)

## Content

### One shared computer list, several consumers

Distributed Computing is configured once, in Simulator Options, as a single
**Distributed Computer List** — not per-tool and not per-case. Contingency
Analysis, ATC, Transient Stability, and QV Curves (added in version 24) all read
the same list. Power flow itself does not participate. Using local CPU cores
instead of a remote machine is not a different mode — it means adding a computer
to the list named `localhost`.

### Authentication is the first silent trap

Every non-local entry needs domain/username/password credentials, which Simulator
stores encrypted and unlocks at runtime with a user-set **Master Password**. The
trap: adding authentication for the *local* machine causes Windows to return an
"Access is denied" error instead of running locally. If a local-only distributed
run fails outright rather than degrading, stray local credentials are the first
thing to check.

### Verify before trusting the run

A **Verify Computers Available** action populates `Enabled`, `Available`, and
`Cores` per machine. Nothing else in the dialog confirms a machine will actually
pick up work — skipping this step and assuming the list is live is a plausible
reason a run stays serial with no error raised.

### Errors silently retire a worker for the rest of the run

Each computer entry carries a **Max # Errors** setting that defaults to **1**.
Once a machine hits that many failures, Simulator stops sending it work for the
remainder of the run and does not retry — a single transient network blip can
permanently drop a worker mid-sweep, with the run finishing on whatever machines
are left and no indication that capacity was lost partway through. **Processes**
(worker processes to start on that machine) can also be set above the core count,
which is a separate knob from `Cores` reported by Verify Computers Available.

### Chunking is configured per tool, not globally

The unit of work handed to each machine differs by tool:

- **Contingency Analysis** — `Number of Contingencies per Process`: contingencies
  are grouped into batches of this size and doled out as machines finish.
- **ATC** — `Number of Directions per Process`, which only applies to
  multiple-direction ATC runs, not multiple-scenario ones.
- **QV Curves (v24+)** — scenarios are bus x contingency combinations; Simulator
  picks whether to chunk by bus count or contingency count based on `ChunkSize`
  versus whichever count is larger, as an explicit fallback rule.
- **Transient Stability** — a plain on/off toggle with no chunk-size control at
  all; TS distributes whole contingencies with no tunable batch size.

An aux script driving any of these should set the matching per-tool field, not
assume one setting covers all four.

### Nothing here is a case object

None of this — the computer list, credentials, Max # Errors, per-tool chunk
sizes — is exposed as a Python object in [esapp](esapp.md) or serialized into the
`.pwb`. It lives entirely in Simulator's global options and per-dialog fields, so
it cannot be scripted through case data the way most of this kit's other settings
are; it has to be set up once in the Simulator UI (or via SCRIPT actions against
those same global options) before any distributed run will do anything at all.

### Relationship to this kit's own workaround

[parallel-contingency-solve](parallel-contingency-solve.md) exists precisely
because this feature was never configured to the point of Verify Computers
Available reporting live workers — it documents an OS-process-level substitute,
not a diagnosis of why the built-in feature failed. If the built-in feature is
ever revisited instead of the workaround, the checklist is: computer list entries
(including `localhost` if wanted) -> correct authentication (never on the local
entry) -> Verify Computers Available actually showing available cores -> Max #
Errors raised from its default of 1 if the network is at all lossy. For a
different way to avoid a large-N-1 solve entirely rather than parallelizing it,
see [lodf](lodf.md).

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*


---

# ==== buscat-and-voltage-control.md ====

---
type: concept
domain: tooling
aliases: [BusCat, bus-category, remote-voltage-regulation, ZBR, PVTol, voltage-droop-control]
tags: [powerworld, manual, power-flow, voltage-control, bus-category, remote-regulation]
---

# PowerWorld: bus category and voltage control

## Abstract

Explains the `BusCat`/`Type` string PowerWorld assigns every bus during a solve — the single
best diagnostic for "why didn't this case solve the way I expected" — and the control
mechanisms that decide it: remote regulation, Mvar sharing, line-drop compensation, setpoint
tolerance, voltage droop, and ZBR grouping. Read it when a solved case reports a control mode
you don't recognize, or before writing esapp code that toggles voltage-control fields.

## Connections

**Up:** [pw-power-flow](pw-power-flow.md) · **Corpus:** [powerworld-help-corpus](powerworld-help-corpus.md)

**Across:** [solver-mechanics-and-failure-modes](solver-mechanics-and-failure-modes.md) · [shunt-transformer-dfacts-control](shunt-transformer-dfacts-control.md) · [pw-pv-qv](pw-pv-qv.md) · [generator-dispatch-and-diagnostics](generator-dispatch-and-diagnostics.md) (the Bus Mismatches Display reads this page's `BusCat`/`Type` values)

**Deeper:** [esapp](esapp.md)

## Content

### The bus equation, and why the type string matters

Every bus has 4 unknowns — voltage magnitude, angle, real power, reactive power — and needs
exactly 2 equations to be solvable; PowerWorld picks which 2 automatically per bus and reports
the choice as a `BusCat` (also shown as `Type`) string, visible by default on the Bus
Mismatches display. This one field is the fastest way to see why a bus behaved unexpectedly,
and it currently has no other documentation in this kit.

Core values: `PQ` (no voltage control), `PV` (local voltage control), `Slack` (one per island,
fixed voltage and angle). Modifier suffixes mean a device fell off its expected classification
because it hit a limit: `(Gens at Var Limit)`, `(SVC)`, `(SVC at Limit)`, `(Continuous Shunts at
Var Limit)`.

### Remote regulation hides the controlling bus

When several generators at different buses jointly hold one remote bus's voltage, PowerWorld
silently designates one "Primary" bus (`PV (Remote Reg Primary)`), turns the others into
`PQ (Remote Reg Secondary)`, and — this is the trap — the regulated bus itself shows as
`PQ (Remotely Regulated)`, not `PV`, because the enforcing equation lives elsewhere. Searching
for "PV bus" at a remotely-controlled bus will not find it.

Remote regulation also fails silently: if no transmission path to the regulated bus avoids
crossing another PV bus, PowerWorld disables the regulation with only a message-log line — no
error, no flag on the device.

### Mvar sharing across a regulation group

When multiple generators share one regulated bus, PowerWorld splits the Mvar output between
them using one of three selectable algorithms (`MvarSharingAllocation` field): `RegPerc`,
`MinMaxRange`, `SumRegPerc`. These give materially different dispatch for the same total Mvar
need. PowerWorld's own recommendation is `MinMaxRange`, because it needs no `RegFactor` input
and drives every generator to its limit together; the other two can hit limits asymmetrically
and require renormalizing across the whole group.

### Line-drop compensation and voltage-setpoint tolerance

Line Drop Compensation (`UseLineDrop=YES`, with `Rcomp`/`Xcomp` on the generator) makes a unit
regulate an estimated point behind its terminal rather than an actual bus; `BusCat` shows
`PQ (Line Drop Comp)`.

Voltage Setpoint Tolerance (`VoltSetTol`, added v21) replaces the hard voltage-setpoint
equation with a sloped one between `(MvarMax, VoltSet−Tol)` and `(MvarMin, VoltSet+Tol)`,
shown as the `PVTol` family. Without knowing this exists, a converged case whose voltage isn't
exactly at setpoint reads as an error when it is working as designed.

### Voltage droop control with deadband

Added v21, `VoltageDroopControl` models aggregated wind/solar plants that regulate a
point-of-interconnection bus using the branch flow arriving there — not generator Mvar
output directly — against a QV droop curve with a deadband. Generators are grouped into a
droop control automatically, by topology plus shared assignment. Invalid configurations are
detected and reported with specific error strings: "Overlapping Voltage Droop Networks",
"Can not reach RegBus", "Conflicting Gen on Voltage Setpoint" — worth matching on verbatim if
you're parsing the message log.

### Precedence order for a generator's control mode

Checked top to bottom, first match wins: `AVR=NO` or a fixed `WindControlMode` or
`MvarMax=MvarMin` fixes Mvar output; else `UseLineDrop=YES`; else `VoltageDroopControl`
membership; else ordinary voltage regulation (possibly remote, possibly with tolerance).
Code that toggles these fields without respecting this order will silently produce the wrong
control behavior.

### ZBR grouping redirects regulation without saying so

Buses joined by branches under the ZBR Threshold (default 0.0002 pu) are merged into one
control group for both voltage regulation and parallel-transformer tap balancing. A generator
or shunt regulating any bus in the group gets silently redirected to the group's chosen
Primary bus — its `RegBusNumUsed` differs from its `RegBusNum`. This is why a solved voltage
can land at 1.05021 instead of exactly 1.05000 with no tolerance set anywhere.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*


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

# ==== case-restructuring-tools.md ====

---
type: concept
domain: tooling
aliases: [equivalencing, network-reduction, bus-merge, bus-split, line-tap, bus-renumbering]
tags: [powerworld, equivalencing, bus-splitting, bus-merging, renumbering, edit-mode, case-editing]
---

# Case Restructuring Tools

## Abstract

Six Edit-Mode tools reshape a case's topology in place rather than reading or transplanting
devices between cases: equivalencing (shrink), merging/splitting a bus (collapse or divide a
node), tapping a line (insert a bus), and renumbering buses/areas/zones/substations. Each has
a silent-failure mode a script needs to know about — equivalencing permanently deletes what it
reduces, merging can silently drop a multi-section-line's grouping record, splitting fabricates
a fault-analysis impedance value out of nothing, and renumbering reads its target number from a
field you have to populate yourself.

## Connections

**Up:** [pw-power-flow](pw-power-flow.md) · **Across:** [case-to-case-device-transplant](case-to-case-device-transplant.md) · [case-impedance-completeness](case-impedance-completeness.md) ·
[topology-consolidation-and-derived-status](topology-consolidation-and-derived-status.md) (an
adjacent way a case's topology changes underneath a script — that page's remap is dynamic and
per-solve, this page's tools rewrite the case on disk) ·
[network-cut-and-query-tools](network-cut-and-query-tools.md) (shares the bus-selection
mechanism equivalencing uses to pick "which system") ·
[fixednumbus-and-raw-v34](fixednumbus-and-raw-v34.md) (renumbering here changes plain
`BusNum`; that page covers a second, RAW-driven numbering scheme layered on top) ·
**Deeper:** [references/aux-script-commands](../references/aux-script-commands.md)

## Content

### Equivalencing: a permanent, bus-by-bus reduction — not area/zone-by-area/zone

Equivalencing partitions the case bus-by-bus into a Study system (retained) and an External
system (reduced away), including a "tiers of neighbors" expansion and a network-cut-based way
to pick the boundary. Building the equivalent runs a Ybus matrix reduction and materializes the
result as new equivalent branches (by convention circuit ID 97/98/99/EQ) and equivalent shunts/
loads at the retained boundary buses.

**This permanently deletes the External system.** There is a non-destructive path — save the
External system to a file before deleting, so it can be reconstructed later via an append-case
operation — but it has to be taken deliberately; it is not the default behavior.

Two traps compound this:

- **Net-interchange imbalance lands on the slack bus** unless "Adjust Area Unspecified
  Interchange to Zero Out ACE" is explicitly checked when reducing an area with nonzero net
  interchange. Skip it and a reduced-order case built for repeated fast solves ends up with a
  slack bus absorbing an artifact of the reduction rather than a real imbalance.
- **Near-open-circuit equivalent branches are not dropped automatically.** "Max Per Unit
  Impedance for Equivalent Lines" has to be set explicitly, or the matrix reduction leaves the
  reduced case bloated with electrically meaningless near-infinite-impedance branches.

### Merging buses is not network reduction, and can silently drop grouping records

Merging two buses deletes the branches directly between them and reroutes everything else onto
the surviving bus — this is a distinct operation from equivalencing, meant for eliminating a
zero- or near-zero-impedance tie rather than for reducing a subsystem. A multi-section-line
record survives a merge only if **all four** hold: every merged bus belongs to the same
multi-section line, they're contiguous within it, at most one is a true terminal of that line,
and at least two sections remain afterward. Miss any one and the grouping record is silently
dropped even though the underlying devices remain in the case.

Merging from the oneline updates both the case and the oneline; merging from the bus grid
updates only the case, which can leave oneline display objects orphaned from their bus records.

### Splitting a bus fabricates a fault-impedance value, and always launches a follow-on step

Splitting a bus creates a new bus and, optionally, a near-zero-impedance tie (`0 + j0.0001` pu)
between old and new. If sequence data exists, the split recomputes it for both resulting buses
and assigns the new tie branch a **hardcoded** `j0.0001` zero-sequence impedance — a script
relying on fault-analysis results across a bus-split needs to know this value is synthetic, not
derived from anything physical. The split has its own multi-section-line survival logic,
symmetric to merging's.

Bus splitting always launches the Equipment Mover as its final step. A script driving a split
programmatically should expect to also need an explicit equipment-transfer step to move loads,
generators, or shunts onto the new bus — the split alone just creates an electrically-tied twin
bus with nothing assigned to it.

### Tapping a line: the shunt-charging treatment is a modeling choice, not a default

Tapping a transmission line splits its impedance by percentage-along-line. What happens to the
line's shunt charging (B/G) is a genuine modeling choice, not automatic: the default recomputes
a long-line PI-equivalent B/G for the two new segments (more accurate), or the alternative dumps
the entire original line's charging capacitance as lumped shunts at the two original terminal
buses and zeros B/G on the new segments. Which one was used changes the resulting case's
reactive balance at those buses — a script generating many taps (e.g., synthetic feeder
buildout) should choose deliberately rather than accept whatever the dialog last remembered.

### Renumbering reads its target from a field you populate first

`RenumberBuses`, `RenumberAreas`, `RenumberZones`, and `RenumberSubs` all take the new number
from each object's Custom Integer field, not from a direct parameter — a script must write that
field for every object to be renumbered, then invoke the renumber action. `RenumberCase` is
different: it executes a full pre-built swap list already held in memory. A number collision
surfaces as a dialog prompt in the GUI tool; the scripted equivalent's collision behavior should
be verified rather than assumed benign.

### Merge Line Terminals: which bus survives depends on multi-section-line position

Merge Line Terminals removes a line while preserving connectivity — the two terminal buses
become one — and is the mechanism for "delete this line but keep the topology connected," as
opposed to simply opening the line, which keeps the bus split. It takes a filter name or the
literal string `SELECTED`. The FROM bus survives as the merged bus **except** when the removed
line was the first or last segment of a multi-section line, in which case that line's own
terminal bus is kept instead — worth checking before assuming a fixed bus-numbering convention
downstream.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*


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

# ==== contingency-linked-sensitivities.md ====

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

# ==== data-check-objects.md ====

---
type: concept
domain: tooling
aliases: [datacheck, data-check-exemption, reusable-case-check, violation-rollup]
tags: [powerworld, data-model, filters, violations, data-quality]
---

# PowerWorld: DataCheck objects

## Abstract

A `DataCheck` is a named, reusable pass/fail rule against case data — an object type plus
an Advanced Filter or inline comparison — that shows up as its own field on every object
of that type and rolls up into per-area/zone/owner counts. It replaces hand-rolling the
same one-off filter every time a script needs to ask "how many objects fail this rule right
now."

## Connections

**Up:** [pw-data-model](pw-data-model.md) · **Across:** [filter-expression-language](filter-expression-language.md) · [datamaintainer-and-object-groups](datamaintainer-and-object-groups.md)

## Content

### What a DataCheck is

A `DataCheck` (added in v20) combines an `ObjectType`, a condition — either a named
Advanced Filter or an inline single-comparison string such as `"Vpu < 0.94"`, which needs
no separate filter object — and display strings shown for the pass and fail cases. Its
`Name` field only needs to be unique within its `ObjectType`, not case-wide.

### The per-object result field

Once a DataCheck is defined, every object of its `ObjectType` gains an addressable field
`DataCheck:<location-or-name>` — either an integer index into that type's DataCheck array,
or the literal form, e.g. `"DataCheck:NERC at Mvar Limit"`. Reading it returns whichever of
the `FilterMeetsString`/`FilterNotMeetsString` display strings applies to that object.

### Aggregated rollups

Counts don't live on the DataCheck itself — they live as separate fields on the
*aggregating* object types: Area, Zone, Owner, DataMaintainer. These are addressed as
`DataCheckAggr:<location>` or `DataCheckAggr:<ObjectType> '<DataCheckName>'`, reusing the
same aggregation machinery as Calculated Fields. Each DataCheck's `Aggregation Format`
setting controls whether the rollup reports as `Meets`, `Meets/Total`, or
`Meets:NotMeets`.

### DataCheckExemption — a per-object override, not a filter edit

`DataCheckExemption` (added in v23) pairs one specific object with one specific DataCheck
so that object is permanently excluded from ever reporting as meeting that check again,
regardless of later data changes. This is distinct from editing the DataCheck's filter —
the filter still evaluates the same way for every other object, only this one object's
result is overridden. Its `Object` key field uses the same ObjectID string syntax
(primary/secondary/label, configurable) used elsewhere for identifying objects in aux
files.

A script that counts outstanding violations by evaluating DataCheck fields directly, without
also reading DataCheckExemption records, will double-count exempted objects as still
failing — the exemption suppresses the *display*, not the underlying filter evaluation that
a naive re-check would repeat.

### Shared with Dynamic Formatting

A DataCheck's filter can also be reused directly as a Dynamic Formatting rule on onelines
and displays — one filter object, two independent consumers.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*


---

# ==== datamaintainer-and-object-groups.md ====

---
type: concept
domain: tooling
aliases: [datamaintainer, object-group, data-maintainer-inheritance, supplemental-data]
tags: [powerworld, data-model, filters, ownership, silent-failure]
---

# PowerWorld: DataMaintainer and ObjectGroup

## Abstract

`DataMaintainer` records who owns a slice of case data and lets that slice be filtered or
exported on its own; `ObjectGroup` is a lightweight named tag usable as a device filter.
Both let code slice a case along lines that aren't Area/Zone/Owner, and both have an
inheritance or auto-creation behavior that can change what a read or write touches without
any visible change to the script that issued it.

## Connections

**Up:** [pw-data-model](pw-data-model.md) · **Across:** [filter-expression-language](filter-expression-language.md) · [data-check-objects](data-check-objects.md) · **Deeper:** [esapp](esapp.md)

## Content

### DataMaintainer: what it is

`DataMaintainer` (added in v19) records a responsible contact for a slice of case data and
lets that slice be exported or written to an aux file on its own. Each object belongs to
at most one DataMaintainer.

### Assign vs. Inherit, and the fields that carry each

Every object type has two independent yes/no capabilities: whether a DataMaintainer can be
**assigned** to it directly, and whether it can **inherit** one from a related object.
Four fields matter for code that reads or sets this:

- `DataMaintainerAssign` — the direct-set field; writing a blank value clears it.
- `DataMaintainer` — read-only, and gives the *effective* value, which may have been
  inherited rather than assigned.
- `DataMaintainerInherit` — a YES/NO toggle, enterable only on the object types that
  support both assign and inherit: Bus, Gen, Load, Shunt, LineShunt, Branch, 3WXFormer,
  DFACTS, DCTransmissionLine, MTDCRecord, VSCDCLine.
- `DataMaintainerInheritBlock` — Bus and Substation only; setting it YES stops objects
  attached beyond that point from inheriting further up the chain.

### Inheritance order matters for automation

Each object type that inherits does so along a fixed precedence chain, and the chain isn't
symmetric. A Gen inherits from its Bus first, then that Bus's Substation. A Branch inherits
from its **NonMetered** bus first, then that bus's Substation, then the **Metered** bus,
then its Substation. On a tie line, which end is marked "metered" therefore silently
decides which DataMaintainer the branch ends up inheriting — a fact worth checking before
relying on a branch's effective `DataMaintainer` value.

### Objects that can never carry one

Solution/environment option objects, software-maintained objects (Island, ZoneTieLine,
AreaTieLine, SuperBus), and calculation results (ViolationCTG) are NO/NO on both
capabilities. Attempting to set `DataMaintainerAssign` on one of these hits a field that
is not enterable rather than raising an error — check whether the field is settable for
that type before writing to it, the same discipline described for any field in
[esapp](esapp.md).

### DataMaintainer filtering can silently shrink a read

Options → "Use Data Maintainers Filtering on Case Information Displays" ANDs DataMaintainer
filtering onto whatever Area/Zone/Owner filter is already active. Turning this option on,
with no change to any filter definition, can shrink the row count of a case-information
read that used to return everything. If a read count changes unexpectedly, this option is
one of the first things to check.

### ObjectGroup: a lightweight scriptable tag

`ObjectGroup` (added in v24) is a named tag usable as a device filter anywhere a
case-information display or aux script command accepts one, written as
`<DEVICE> ObjectGroup 'GroupName'` (see [filter-expression-language](filter-expression-language.md)
for device-filter syntax generally).

Membership in a group comes in two forms:

- **Assigned** — explicit membership, set through the `ObjectGroup\Assign Names` or
  `ObjectGroup\Append Names` fields. These are comma-delimited, and an object can belong to
  multiple groups.
- **Contained** — inherited membership. Assigning Areas to a group makes every generator
  inside those areas "contained" in the group, even though no generator was individually
  assigned.

### The silent-creation trap

Writing a group name into `ObjectGroup\Append Names` for a group that doesn't exist yet
**creates that group on the spot** — there is no separate create step and no error. Code
that generates an aux file with a typo'd or dynamically-built group name will create a new,
unintended group rather than failing to find the one it meant.

### Relationship to SupplementalData

`ObjectGroup` is functionally the same mechanism as `SupplementalData`/
`SupplementalClassification` configured with `Inherit=YES, Multiple=YES`, documented in the
manual as a topology-tools feature. `ObjectGroup` is the simpler path to the same behavior
when scripting, since it needs no separate classification-definition step.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*


---

# ==== difference-case-tool.md ====

---
type: concept
domain: tooling
aliases: [difference-case, diff-case, removedbus, removedgen, complete-model-export, diffchangetolerance]
tags: [powerworld, difference-case, simauto, aux, case-diff, scripting]
---

# The built-in Difference Case tool

## Abstract

PowerWorld ships a case-comparison engine of its own — SimAuto-queryable `Removed<Type>` object
types, per-field change tolerances, and a "Complete Model" AUX export that turns a base case into a
present case — that a hand-rolled pandas diff duplicates without knowing it exists. It doesn't
replace project-specific diff logic (renumber pairing, retirement classification, and similar business
rules have no native equivalent), but it answers "what changed" and "what's new since base" with
built-in tolerance handling that a naive numeric comparison gets wrong.

## Connections

**Up:** [pw-manual-map](pw-manual-map.md) · **Across:** [case-to-case-device-transplant](case-to-case-device-transplant.md) · [comparing-planning-cases](../demos/comparing-planning-cases.md) ·
[raw-epc-roundtrip-traps](raw-epc-roundtrip-traps.md) (a diff run across a RAW/EPC round-trip
can flag reinterpreted-but-unchanged fields as real differences unless tolerance handling
absorbs them)

## Content

### Base and Present, and how objects are matched

The tool compares a **Base** case (set via "Set Present as Base") against the **Present** case
currently in memory. Matching between the two uses one of the same three key schemes used
elsewhere in Simulator: primary keys (bus numbers), secondary keys (name + kV), or labels — chosen
up front, not inferred per-object.

### Four display modes

- **Present** and **Base** — each case's own values.
- **Difference** (Present − Base) — numeric fields show the delta; status fields show `OPEN|CLOSED`
  style before/after pairs.
- **Change** (added in V20) — shows a value only where something actually changed, blank otherwise.

### Numeric "changed" is a tolerance decision, not exact equality

The default threshold is 0.0001% relative, overridable per object-type/field via `DiffChangeTolerance`
objects (Absolute / Percent / Perc-or-Abs / Perc-and-Abs). This matters beyond the built-in tool: any
home-grown comparison of solved AC quantities across two solves should expect meaningless float noise
unless it respects an equivalent tolerance — treating a `1e-12` delta as a real change is a common
false positive in ad hoc diffs.

Blank-vs-defined values (e.g. Latitude/Longitude, where blank is itself a meaningful "undefined"
state) get special handling in Change Mode: the literal string `"_same_"` is shown when nothing
actually changed, to disambiguate from "the value became blank."

### Topological differences are a separate dialog

The plain Difference Case display only shows value deltas on objects that match in both cases — it
cannot show additions or removals. That's a distinct dialog, "Present Topological Differences from
Base."

### Querying what's gone, without writing your own key-diff

Removed objects are exposed as their own SimAuto object types, named `Removed<Type>`
(`RemovedBus`, `RemovedGen`, etc.), queryable via `GetParametersMultipleElement` — or esapp's
bracket interface — like any other object type. Loading these back into Simulator in Edit Mode
**deletes** the corresponding objects, which is a scriptable way to get "what disappeared between
base and present" without writing a key-based diff by hand.

There's also a boolean field, `Difference Case\In Diff Base`, on every difference-case-eligible
object type — usable directly in ordinary filters and scripts to select "new since base" (`NO`) vs.
"existed in base" (`YES`) without opening the dialog at all.

### The Complete Model export — a native alternative to a hand-built transplant AUX

[case-to-case-device-transplant](case-to-case-device-transplant.md) builds its transplant AUX by hand:
dump the source with `SaveCase(AUX)`, filter by key, and reload with `LoadAux(create_if_not_found=True)`.
The **Complete Model** export produces the equivalent artifact natively: a single AUX file that, loaded
back into the original base case, transforms it into the present case. It deletes removed objects
(`Delete(objecttype, SELECTED)`), inserts new objects, and writes only the changed fields for objects
present in both (via Change Mode).

Two special-case sections are auto-inserted ahead of the new-object inserts, to avoid corrupting
per-unit impedance or clobbering ownership:
1. Nominal-voltage changes on a shared terminal bus are applied first — branch impedance is stored on
   transformer base, and applying it after new devices exist would silently rebase it.
2. Owner/area/zone reassignment is written before device creation, so auto-synchronization doesn't
   clobber an unrelated device's ownership.

**Where this fits next to the hand-built transplant, not instead of it:** the two are complements.
Complete Model gives you PowerWorld's own field-complete diff/apply mechanics; it has no equivalent
for project-specific business logic — renumber pairing, retirement classification, area/voltage
scoping — which is exactly the part [case-to-case-device-transplant](case-to-case-device-transplant.md)
and [comparing-planning-cases](../demos/comparing-planning-cases.md) build by hand. Consider Complete
Model when you want a native, tolerance-aware apply step and don't need custom matching rules; keep
the pandas/AUX-filter approach when you do.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*


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

# ==== filter-expression-language.md ====

---
type: concept
domain: tooling
aliases: [advanced-filter, device-filter, model-expression, string-expression, filter-syntax]
tags: [powerworld, filters, expressions, data-model, silent-failure]
---

# PowerWorld: the filter and expression language

## Abstract

One grammar underlies Advanced Filters, Model Expressions, String Expressions, and
`DataCheck` conditions in PowerWorld — the same operators and functions, reused across
every place a case-information display, aux script, or `GetParametersMultipleElement`
call needs to select or compute over rows. Read this page before writing a `FilterName`
string, a device filter, or an inline comparison expression: the syntax has several traps
where a malformed filter does not error, it just silently matches nothing.

## Connections

**Up:** [pw-data-model](pw-data-model.md) · **Across:** [data-check-objects](data-check-objects.md) · [datamaintainer-and-object-groups](datamaintainer-and-object-groups.md) · **Deeper:** [esapp](esapp.md)

## Content

### Naming a filter that belongs to another object type

A filter is defined against one object type. Referencing it from a script command or aux
block that targets a *different* type requires prefixing the filter name with the target
type in angle brackets, no space: `<BUS>MyFilter` used where a Gen-scoped filter is
expected. Omit the prefix and PowerWorld looks for a same-named filter on the wrong type —
it will not find one, and the filter that "runs" simply returns nothing.

### Device filters — using one object type to filter another

A **device filter** selects rows of one object type based on membership in a *different*
object (an Injection Group, a `DataCheck`, an `ObjectGroup`; see
[datamaintainer-and-object-groups](datamaintainer-and-object-groups.md)). The form is:

```
<DEVICE> objecttype 'key1' 'key2' 'key3'
```

Its semantics are relational, not literal. An Injection Group used to filter Branches
does not return the group's member objects — it returns the branches connected to any
member's terminal bus. Reading a device filter as "give me the members" instead of "give
me what's related to the members" is the most common misreading.

### Combining conditions: one operator per filter, nest for the rest

A single Advanced Filter combines its conditions with exactly one logical operator: AND,
OR, XOR, NOT AND, NOT OR, One TRUE, or Num TRUE (the last two added in v19/v21
respectively). There is no mixed-operator form inside one filter — `A AND (B OR C)` does
not have a single-filter syntax. Build it by nesting: define one filter for the inner
group (`AF1 = B OR C`), then reference it from the outer filter as a condition
(`AF2 = A AND (meets filter AF1)`).

### The "Pre-Filter using Area/Zone/Owner Filters" checkbox

Every Advanced Filter carries a checkbox, off by default in the sense that its state is
whatever was last set, that pre-restricts the filter's candidate rows to whatever the
live Area/Zone/Owner/DataMaintainer filter currently shows. With it on, the filter's
result depends on UI-level filter state that isn't part of the filter definition itself —
running the identical named filter in two sessions (or two points in a batch run) can
return different rows with no change to the filter. Leave it off for anything that needs
to be reproducible from the filter definition alone.

### Field-to-field comparisons

"Enable Field to Field Comparisons" switches a condition's right-hand side from a
hardcoded constant to another field on the same device, or to a named Model Expression.
This is what makes a filter like "MW output > MW rated capacity" possible without
encoding a plant's capacity as a magic number in the filter itself.

### Range-of-numbers fields

Anywhere a filter, scaling dialog, or "within integer range list" comparison accepts a
list of bus/area/zone numbers, it accepts the same compact format: comma-separated
singles mixed with dashed ranges, no spaces required — `1-5,21,23-25`. This format is
shared across every field of this kind, not per-dialog.

### The shared expression grammar

Expressions, String Expressions, and Model Expressions all evaluate with one
function/operator set:

- Trig functions operate in radians.
- Comparison and bitwise operators: `==`, `<>`, `bitor`, `bitand`, `bitxor`, `shl`, `shr`,
  `MOD`, `!` (factorial), `^` (power).
- String-relevant functions: `Str(x, minlen, decimals)` (a negative `decimals` truncates
  trailing zeros instead of rounding), `Find`/`Search` (case-sensitive exact substring vs.
  wildcard, case-insensitive substring), and `IsTrue`, which normalizes any of
  T/TRUE/CONNECTED/CLOSED/YES/Y/1 to `1` and everything else to `0` — useful because
  status fields spell "on" differently across object types.

**Booleans are C-style, not 0/1.** A `true` result is "not exactly zero" — often literally
the numeric difference the expression computed — and `false` is exactly `0`. Code that
reads back an expression's numeric result and tests `== 1` for truth will be wrong for any
expression whose true branch doesn't happen to evaluate to exactly 1.

### Date/time functions and PowerWorld's date encoding

`TEXT`, `DATETIMEVALUE`, `DATEVALUE`, and `TIMEVALUE` convert between formatted date
strings and PowerWorld's internal date representation: days since 1899-12-30, with the
fractional part encoding time-of-day at roughly 1 ms precision as a double. Any aux file
or weather/TimeStep pipeline that embeds a formatted date string and needs it to round-trip
through PowerWorld goes through these functions.

### Interpolating a Model Expression into text — and its staleness trap

A saved Model Expression can be embedded directly in a case-information display or aux
file using the literal token `&ExprName:digits:decimals`, e.g. `&NetGeneration:5:2`. The
link is a snapshot taken at the point the token was typed, not a live reference — editing
the Model Expression afterward does not update text that already embeds `&ExprName`. Each
embedded reference has to be re-entered, or the file reloaded, for the new definition to
take effect. Generated aux files that embed expression references are exposed to this: a
regeneration step that doesn't force re-entry will keep emitting stale values.

### Verifying a filter matched what you meant

Because none of the failure modes above raise an error — a bad angle-bracket prefix, a
device filter with reversed relational logic, an unintentionally-enabled pre-filter
checkbox — the only reliable check is to count rows. Run the filter, read the resulting
row count (or the objects themselves) back through `esapp`, and compare against an
independent expectation before trusting a downstream call that consumes the filtered set.
A filter that matches zero objects looks, to every caller downstream, exactly like a
successful call over an empty set.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*


---

# ==== fixednumbus-and-raw-v34.md ====

---
type: concept
domain: tooling
aliases: [fixednumbus, subnodenum, psse-full-topology, raw-v34, substation-node-bus]
tags: [powerworld, psse, raw, fixednumbus, subnodenum, substation, scripting]
---

# FixedNumBus and full-topology RAW (v34+)

## Abstract

RAW v34+ and other full-topology PSS/E-style models split each electrical bus into a substation-level
node structure, and PowerWorld's bus-numbering, ID-renaming, and validation rules around
`FixedNumBus`/`SubNodeNum` all follow from that split. An agent that assumes "bus number equals the
PSS/E bus number" or that IDs stay stable across a `FixedNumBus` assignment will get silently wrong
answers — the failures here don't raise exceptions, they log a message and move on.

## Connections

**Up:** [pw-manual-map](pw-manual-map.md) · **Across:** [raw-epc-roundtrip-traps](raw-epc-roundtrip-traps.md) · [pw-data-model](pw-data-model.md) ·
[case-restructuring-tools](case-restructuring-tools.md) (`RenumberBuses` operates on the plain
`BusNum` this page derives from `SubNodeNum`/`FixedNumBus` — renumbering one doesn't touch the
other) · [difference-case-tool](difference-case-tool.md) (a diff across a full-topology RAW
read/write can register `FixedNumBus`-driven ID renaming as a device change)

## Content

### PSSE_Bus vs. Node vs. PowerWorld Bus

Full-topology PSS/E models distinguish a **PSSE_Bus** (1–999999, which can represent multiple
electrical points — voltage phasors — if a substation is split internally by open switches) from a
**Node** (1–999, unique only within its substation). PowerWorld reads this into one `Bus` object per
node, synthesizing the PowerWorld bus number as:

```
BusNum = SubNodeNum * 1000000 + FixedNumBus
```

with a special case: when `SubNodeNum = 1`, the bus number is just `FixedNumBus`. Any code that
assumes the PowerWorld bus number equals the source PSS/E bus number will be wrong for every split
bus in the case — this is not an edge case on a post-2020 utility EMS export, where full-topology RAW
is increasingly the default.

### `FixedNumBus` grouping — silent rejection, not an exception

`FixedNumBus` is a grouping field on `Bus`; by default every bus points to itself. Before accepting a
`FixedNumBus` assignment, PowerWorld requires that **no branch connect two buses inside the same
grouping** — a violating assignment is rejected with only a message-log line, no exception raised. A
script that sets `FixedNumBus` and doesn't check the message log can believe an assignment succeeded
when it silently didn't.

### Assigning into a group cascades edits you didn't ask for

Assigning a bus into a `FixedNumBus` group forces `NomkV`/`Substation`/`Area`/`Zone`/`Owner` on that
bus to match the group, and **auto-renames** Load/Gen/Shunt/Branch 2-character ID strings to avoid
collisions with existing IDs elsewhere in the same group. A script relying on IDs staying stable
across a `FixedNumBus` assignment will see them change without being told.

### Object-identifier strings accept either form — except mixed on one branch

AUX files, `.con`/`.mon` files, and ObjectID strings accept either the real bus number or its
`FixedNumBus` interchangeably — `"Load 3002425 1"` and `"Load 2425 1"` can resolve to the same
device. The exception: for a **Branch**, if one terminal uses the `FixedNumBus` form, **the other
terminal must too** — mixing forms on the same branch string is invalid. This is a real trap for
hand-written AUX filters or contingency definitions built against a full-topology case.

### Collapsing back to a "regular" case

`File > Save Merged FixedNumBus Case` collapses split PSSE_Bus points into `FixedNumBus`-only
topology — useful for producing a non-full-topology export for tools or studies that don't need
node-level detail. Note it can *add* buses relative to what looks like a single grouping visually: if
a `FixedNumBus` group was electrically split by open devices, each split point needs its own voltage
phasor in the merged output, so "merged" doesn't always mean "fewer buses."

### Oneline display (lower priority for scripting)

`DisplayBus.AllowFixedNum` controls whether a oneline display object represents the terminal bus or
its `FixedNumBus` for auto-insertion/anchoring purposes. This is a GUI-only concern, relevant mainly
if you're generating onelines programmatically against full-topology cases.

### Practical checklist before scripting against a full-topology case

1. Don't assume `BusNum` matches the source PSS/E bus number — check `SubNodeNum` first.
2. After any `FixedNumBus` assignment, check the message log, not just the return value — rejection
   is silent otherwise.
3. Snapshot device IDs before a `FixedNumBus` assignment if your code depends on them, since
   collision-avoidance renaming can change them.
4. In hand-written AUX/CON/MON branch references, use the same numbering form (real or `FixedNumBus`)
   on both terminals.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*


---

# ==== generator-dispatch-and-diagnostics.md ====

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


---

# ==== gic-modeling-heuristics.md ====

---
type: concept
domain: tooling
aliases: [gic-defaults, autotransformer-detection, gsu-detection, grounding-resistance-approximation, gic-core-type]
tags: [gic, gmd, powerworld, transformer, grounding, silent-input]
---

# GIC modeling heuristics and silent inputs

## Abstract

[gic](gic.md) already warns that placeholder grounding data produces plausible but
meaningless results. This page is the mechanism behind that warning: the specific
fallback rules Simulator applies when autotransformer status, winding
configuration, core type, or substation grounding resistance are left at their
`Unknown`/zero defaults. None of these fallbacks error — each one silently
substitutes an assumption that changes whether a transformer carries GIC current
at all, or how much Mvar loss it reports.

## Connections

**Up:** [Home](../index.md) · **Across:** [gic](gic.md) · [lodf](lodf.md) · **Deeper:** [aux-script-commands](../references/aux-script-commands.md)

## Content

### Autotransformer status is inferred, not just missing

The `Is AutoTransformer` field defaults to *Unknown*. When it is, Simulator
infers "yes" only if all of the following hold: the device is not a phase
shifter, its From/To nominal voltages differ, its turns ratio does not exceed a
configurable **Maximum Turns Ratio**, and its medium-side nominal voltage is
below a configurable **Minimum Medium Voltage**. Any one of those thresholds
being wrong for an unusual voltage class silently misclassifies the transformer's
GIC path.

### GSU status is a second, chained heuristic

If winding configuration is also *Unknown*, Simulator separately checks whether
the transformer looks like a generator step-up unit: medium-side voltage below
the Minimum Medium Voltage threshold, a generator present on the medium bus, and
high-side voltage above a configurable **Minimum High Side Winding Voltage**. If
all three hold, it assumes a GSU with high-side grounded-wye / medium-side delta
winding — a specific, silently-applied configuration that decides whether the
unit carries GIC current at all.

### Implicit GSUs can be assumed from generator wiring alone

When "Include Implicit GSU" is left at *Default*, Simulator assumes a generator
has an unmodeled step-up transformer whenever either its fault-page R/X fields
are non-zero, or it connects directly to a bus above 30 kV. When R is zero, a
fixed, non-configurable per-phase conductance is used instead. A generator sitting
directly on a high-voltage bus with no explicit GSU record gets a phantom GIC
path assumed for it regardless of whether one physically exists.

### Core Type sets the Mvar-loss scaling factor

Core Type (also defaulting to *Unknown*, alongside Single Phase / Three-Phase
Shell / 3-Legged / 5-Legged / 7-Legged / Core-Generic) is only consulted when GIC
Model Type is *Default*. The resulting per-unit K-factor is normalized to a 500 kV
transformer and then rescaled linearly by the transformer's own maximum nominal
kV. Reproducing or sanity-checking a reported Mvar loss requires this exact
relationship: a base K-factor of 0.80 on a 345/138 kV unit rescales to
`0.80 x 345/500 = 0.552`, so a 100 A effective GIC current yields 55.2 Mvar of
reactive loss.

### Grounding resistance is approximated, not zero

If a substation's `Grounding Resistance` field is left at 0, Simulator does not
treat that as "no grounding" — it approximates a resistance from the
substation's highest bus voltage and its bus count, on the reasoning that
larger, higher-voltage substations have a bigger physical footprint and
therefore lower resistance. The approximated value is written back into `GIC
Used Grounding Resistance`, so it is inspectable after the fact, but the rule
that produced it — voltage- and bus-count-driven, not user-configurable — is not
visible from the field alone.

### Missing substations can be synthesized outright

A bus with no substation record does not block a GIC calculation. With
"Automatic Insertion of Substations for Buses without Substations" enabled,
Simulator creates a synthetic substation purely to have somewhere to model
common neutral grounding. A case with incomplete substation records gets
invented topology rather than an error.

### Geometry validation exists but is not automatic

A "Validate Input Data for GIC" action flags any line longer than 776.5 miles —
a quarter-wavelength at 60 Hz, past which the line's electric-field-integral
assumption breaks down. This check has to be run deliberately; it does not fire
before a GIC calculation.

### Area-level loss suppression can be left on by accident

`Ignore GIC Losses` is settable per Area, for both lines/transformers and
implicitly-modeled GSUs, meant to exclude electrically distant areas from a large
case's AC-coupled loss total. Left enabled from an earlier, narrower-scope study,
it silently drops a whole area's worth of Mvar losses from a later, wider run
with no warning that anything was excluded.

### Sensitivity analysis for prioritizing real measurements

Two sensitivity modes — `Line Amp Input Sensitivity` and `Transformer
Ieffective GIC Sensitivity` (dIGIC/dEfield) — identify which lines most affect a
given transformer's GIC current. A **Calculate Sub Driving Point Values** option
extends this to per-substation sensitivity, useful for ranking which of many
substations most need a real grounding-resistance measurement instead of the
approximated default above.

### Non-uniform field input needs four files, not one

Driving `GICLoad3DEfield` or a time-varying non-uniform field (rather than the
uniform storm direction/magnitude that [gic](gic.md) already documents) requires
four separate CSV files: a coarse grid file carrying origin, spacing, and field
values, plus fine-grid location, east-component, and north-component files.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*


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

# ==== injection-group-participation.md ====

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


---

# ==== interface-elements-and-monitoring.md ====

---
type: concept
domain: tooling
aliases: [interface-elements, monitor-direction, nomogram-mechanics, flowgate-mechanics]
tags: [powerworld, interface, nomogram, flowgate, monitoring, aux-script]
---

# Interface element types and monitoring mechanics

## Abstract

An interface's reported flow depends on two independent direction settings and on which
element types were used to build it — get either wrong and the number is still real, it
just measures something other than what the caller thinks it measures. An unrated
auto-inserted interface doesn't error either; its limit silently defaults to 0. This page
is the mechanism behind the routing page at [pw-interfaces](pw-interfaces.md): the
aux-script element-type syntax, how sign and direction compose, what the contingency-aware
fields mean, and how nomograms build on top of a plain interface.

## Connections

**Up:** [pw-interfaces](pw-interfaces.md) · **Across:**
[ptdf-shift-factor-otdf](ptdf-shift-factor-otdf.md) (the interface as the *monitored*
branch/element in a PTDF or OTDF calculation — that page covers the transaction math, this
one covers the interface object itself) ·
[injection-group-participation](injection-group-participation.md) (an injection group can
itself be one of the elements composed into an interface) · **Deeper:**
[pw-power-flow](pw-power-flow.md)

## Content

### What can go into an interface, and the aux-script tokens for each

An interface aggregates flow across a mix of element types in one object: AC/DC branches,
inter-area ties, inter-zone ties, generators, loads, injection groups, multi-section lines,
other interfaces (nested), and contingency actions. The aux-file tokens are exact and
load-bearing for hand-written or generated scripts:

| Token | Meaning |
|---|---|
| `BRANCH num1 num2 ckt` | Monitor MW flow from bus `num1` to `num2`; the bus order sets the sign convention |
| `AREA num1 num2` / `ZONE num1 num2` | Sum of AC branches tying the two areas/zones |
| `BRANCHOPEN` / `BRANCHCLOSE num1 num2 ckt` | Monitor the interface as if this branch were opened/closed — a contingency-conditioned member, not a static one |
| `DCLINE num1 num2 ckt` | DC line flow |
| `INJECTIONGROUP 'name'` | Net injection — generation positive, load negative |
| `GEN num1 id` | Positive injection |
| `LOAD num1 id` | Negative injection |
| `MSLINE num1 num2 ckt` | Multi-section line flow |
| `INTERFACE 'name'` | Nest another interface's flow into this one |
| `GENOPEN` / `LOADOPEN num1 id` | Contingency-conditioned generator/load closing (added Simulator v20, Jan 2018) |

### Two independent direction settings compose

Sign is set per element, not just per interface. For a branch, transformer, or DC-line
element, flow is measured near-bus → far-bus, positive in that direction; which bus counts
as "near" is a choice made when the element is added. A separate **Monitor Flow at To End**
toggle picks which end's flow *magnitude* is reported for that element — relevant when the
two ends disagree because of losses or shunts.

On top of that, the interface as a whole carries its own **Monitor Direction** (From→To or
To→From) plus a **Monitor Both** toggle that overrides it. That's two settings that both
affect the sign of the number coming back — a script reading interface flow needs to know
which end and which overall direction it's getting, not just the raw magnitude.

### Contingency-aware fields bake in a hypothetical outage

- `Has Contingency` — YES if any member element sits at a device limit.
- `Base MW Flow` — the pre-contingency flow.
- `Contingent MW Flow` — the flow that *would be added* if the interface's own defined
  contingency occurred.
- `Interface MW` = Base + Contingent.

`Interface MW` is not the live flow — it already includes a hypothetical contingency
addition. Reading it as "the current flow" overstates what's actually flowing right now.

### Limits: up to eight, and which set is active matters

Interfaces support up to eight limits (`Lim MW A/B/C` in the display, the same scheme used
for lines and transformers), and which one is the *effective* limit depends on the case's
Limits tab / Line-Transformer Limit Violations settings. An interface's MW limit is not a
single static number independent of that configuration.

### Auto-insertion is restricted to adjacency, and silently under-limits

Bulk auto-insertion only works for area-to-area or zone-to-zone interfaces that share at
least one tie line; a single bus-to-bus interface has to be built through the line-insertion
options instead. Auto-inserted interfaces default to overwriting any existing interface with
the same name unless "Delete Existing Interfaces" is unchecked. If no rating source is
selected during auto-insertion, the new interface's limit silently defaults to 0 — read
downstream as "no limit," not as an error.

### Nomograms: a convex boundary between two interfaces

A nomogram pairs exactly two interfaces and defines an allowed joint-flow region as a
convex piecewise-linear boundary, built from ordered breakpoints (each one a flow pair on
Interface A and Interface B). The breakpoints must be entered in the order that keeps the
boundary convex. A script generating nomogram breakpoints programmatically has to preserve
that ordering/convexity constraint itself — nothing in the object enforces it after the
fact, and a wrong order produces a limit shape that doesn't match the intended region.

### Percent reads as zero, not undefined, on an unrated interface

The oneline-drawing `Interface Field Information` / `Interface Pie Chart Information`
objects are cosmetic (rotation, sparkline toggle, anchoring), with one exception worth
keeping: the `Percent` field is defined as exactly 0 whenever the MW rating is 0, so a
pie-chart or field read on an unrated interface comes back as a clean zero instead of
`NaN` or an error.

### NERC flowgates are interfaces, not a separate object

Loading or saving NERC flowgates (Excel, requires a NERC-supplied login) is a thin wrapper
around interface records — the interface *is* PowerWorld's flowgate model. There is no
separate flowgate object to reconcile against.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*


---

# ==== island-and-breaker-grouping.md ====

---
type: concept
domain: tooling
aliases: [island-display, breaker-isolated-groups, branches-that-create-islands, create-new-areas-for-islands, topological-diff]
tags: [powerworld, topology, islands, breakers, areas, contingency]
---

# Island and breaker grouping tools

## Abstract

Four PowerWorld tools compute island and breaker-boundary structure without needing the paid Integrated Topology Processing add-on — the free islanding detector documented in [lodf](lodf.md) is a DC-linear-algebra shortcut for one of the same questions these tools answer natively in Simulator. Two silent-failure traps sit inside them: an Area whose buses span more than one island gets AGC turned off with no error, and a case-to-case topology diff can flag pure bus-renumbering as a real topology change.

## Connections

**Up:** [pw-manual-map](pw-manual-map.md) · **Across:** [lodf](lodf.md) (the DC-linear-algebra islanding detector — this page covers Simulator-native island tooling instead) · [topology-consolidation-and-derived-status](topology-consolidation-and-derived-status.md) ·
[scheduled-actions-scripting](scheduled-actions-scripting.md) (shares the `Origin`/breaker-
identification taxonomy idea — that page's is per scheduled action, this page's Breaker
Isolated Groups is per bus) · **Deeper:** [pw-contingency](pw-contingency.md)

## Content

### Island Display — the cheap sanity check

An **Island** is an AC-connected group of buses; a DC line can bridge two islands without merging them into one, and every island needs its own slack bus. The Island Display (Model Explorer → Aggregations → Islands, run-mode only, read-only) lists per island: the slack bus, total bus count, an `Energized` flag, aggregate Gen/Load MW and Mvar, and scheduled exports. It's a cheap check that a case actually solved as one connected system — a scripted power-flow solve does not error out just because the case quietly split into multiple islands during a build or edit step.

This is a different tool from the LODF-based free islanding detector in [lodf](lodf.md): that one finds islands that would be *created by a single branch outage*, computed as a side effect of building the PTDF matrix for DC contingency screening. Island Display reports the islands that already exist in the *current* case state. Neither substitutes for the other.

### Create New Areas for Islands — the silent AGC trap

If an Area's buses span more than one island, PowerWorld has no way to know which island a scheduled interchange transaction should flow through, so it cannot perform AGC or area-interchange control for that area — and it **silently turns AGC off** for any area meeting this condition, with no error raised. A script that reassigns bus-area membership — during case building, a merge, or a topology edit — without checking the resulting island membership can disable AGC on an area and never see a warning.

### Branches that Create Islands — a rigorous replacement for eyeballing radial lines

This tool (Tools → Connections) enumerates every AC branch whose removal would split an existing island into two: genuine single-point-of-failure, radial branches. It has an option to suppress the trivial case of a branch that only islands a single bus. It does **not** require the ITP add-on, and it's a cheaper and more rigorous way to find these branches than visually scanning a oneline for lines that "look radial."

### Breaker Isolated Groups — approximate breaker detail without full node-breaker modeling

This buckets every bus by boundary crossings of three kinds: explicit breakers (`BranchDeviceType`=Breaker), **implicit breakers** (a per-bus flag meaning "treat every branch touching this bus as if it had a breaker, even though none is modeled" — a way to approximate breaker-level detail without building it out fully), and currently-open branches — or, if "Use Branch Normal Status for Groupings" is toggled on, branches whose `Normal Status` is Open rather than their current `Status`. Every bus ends up with a `Breaker Group Number`.

This grouping also drives **Auto Insert Contingencies → Bus grouping**, which generates contingencies per boundary-crossing type with different naming and action rules depending on whether a group's boundary is all-implicit, all-explicit, or mixed. That makes it a way to auto-generate realistic N-1-style contingencies from a case that only has partial — or purely implicit — breaker detail, again with no ITP add-on required. See [pw-contingency](pw-contingency.md) for contingency mechanics generally.

### Present Topological Differences from Base Case — the renumbering trap

This diffs two cases and reports New / Removed / Both-matched object counts per object type, with a Present/Base/Difference/Change display-mode toggle, and can export the diff as an executable AUX script. Prefer the modern "Complete Model" export over "Legacy Complete Model" — the legacy form is explicitly deprecated and can't filter by Area, Zone, Owner, or Data Maintainer.

Two traps matter directly for any case-to-case device-transplant workflow:

1. **Topology discrepancies between two cases are sometimes purely an artifact of different bus-numbering schemes, not real topology differences.** The tool ships a **Create Bus Swap List** helper specifically to resolve this — renumber one case to match the other's scheme before re-diffing, rather than reading a renumbering as a structural change.
2. **The AUX export has special-cased handling that naive field-by-field diffing would get wrong**: bus nominal-voltage changes on newly-added branches, area/zone/owner ownership changes where a device's own owner differs from its bus's changed owner (an explicit order-of-operations case), and three-winding-transformer star-bus renumbering when writing out "Both Elements" changes.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*


---

# ==== limit-monitoring-and-scaling.md ====

---
type: concept
domain: tooling
aliases: [limit-monitoring, monitor-flag, limit-group, agc-scaling, scale-to-ace, merit-order-dispatch]
tags: [powerworld, limits, monitoring, scaling, dispatch, contingency, violations]
---

# Limit Monitoring and Scaling

## Abstract

Why does an obviously-overloaded branch never show up in `overloads()`, contingency analysis,
ATC, or OPF? Reporting a violation is gated by a chain of flags upstream of the device's own
rating, and any single link being wrong makes the device invisible to every consumer at once —
not just one tool. Scaling load or generation to a target level has the same shape of trap:
the dispatch method and starting-point choice change *which* result you get, not just how fast
you get there, and one AGC-filtering option silently strands the remainder on the slack bus
instead of redistributing it.

## Connections

**Up:** [pw-power-flow](pw-power-flow.md) · **Across:** [methods/reading-violationctg](../methods/reading-violationctg.md) · [methods/powerworld-limitset-setdata](../methods/powerworld-limitset-setdata.md) · [methods/ranking-new-devices-by-severity](../methods/ranking-new-devices-by-severity.md) ·
[weather-dependent-limits](weather-dependent-limits.md) (a different way a device's effective
rating can silently go stale or wrong before this page's gate chain ever sees it) ·
[generator-dispatch-and-diagnostics](generator-dispatch-and-diagnostics.md) (its two
merit-order algorithms overlap, but aren't identical to, this page's four scaling dispatch
methods) · [interface-elements-and-monitoring](interface-elements-and-monitoring.md) (an
unrated auto-inserted interface silently defaulting its limit to 0 is the interface-object
analogue of this page's monitor-gate chain) ·
**Deeper:** [references/aux-script-commands](../references/aux-script-commands.md)

## Content

### The four-gate chain that decides whether a device is even eligible to be reported

A device's limit is enforced and reported only if **all four** of these hold at once:

1. the device's own `Monitor` field is YES
2. its assigned Limit Group is not Disabled
3. its Area has area-level limit reporting enabled, and the device's kV falls inside that
   area's reporting kV range
4. the same reporting check passes at the Zone level

Any one of these being wrong makes the device invisible to `overloads()`, contingency
analysis, ATC, OPF, and PV/QV alike — because they all read from the same upstream gate, not
from independent logic. This is a different, earlier mechanism than the per-violation limit
override read in [methods/reading-violationctg](../methods/reading-violationctg.md); that page
covers the `ViolationCTG` record once a violation has already been reported, not whether it
gets reported at all. A case assembled or edited programmatically (synthetic-grid generation,
transplanting a device from another case) can easily leave a new device's Area/Zone reporting
settings unset, or its Limit Group Disabled, and silently stop monitoring an entire area — not
just the one device. Debugging "why doesn't this clearly-overloaded branch show up" means
checking all four gates, not just the branch's own flag.

### A Limit Group also indirects which rating actually applies

A device's own rating fields aren't necessarily "the" limit. Each Limit Group selects, from up
to 15 (line) / 8 (bus) / 4 (bus-pair) predefined rating sets, which one is used for normal-state
reporting and which for contingency reporting. Reading a device's nominal rating field without
first checking which rating set its Limit Group currently points to can silently read the wrong
number.

### MVA% and Amp% disagree by design, and DC solves only ever report one of them

`Amp% = MVA% / (per-unit voltage at the limiting bus)`. The two percentages are not the same
number, and a Limit Group's "Treat Line Limits as Equivalent Amps" toggle controls which one a
given group reports — this is intentional, not a bug. A script comparing loading percentages
across a Limit Group boundary can legitimately see two different numbers for what is physically
the same constraint. **DC power flow and DC contingency solves always report line limits in
MVA and ignore this toggle entirely** — code that branches on "Amps vs MVA" mode without also
checking whether the case is currently in DC mode will misread the units.

### Two different meanings of "radial," easy to conflate

"Do not monitor radial lines and buses" is a live, simple single-line-in/out rule, and it is
ignored entirely when Integrated Topology Processing is active. "Branches that Create Islands"
is a separate, coarser N-1 radial/tree-forming detector. A device can be structurally radial by
one definition and not the other, especially on a case with parallel circuits — the two names
sound interchangeable and aren't.

### Scaling silently follows the device's own Area/Zone, not its bus's

Scaling by Area, Zone, or Owner uses the device's *own* area/zone assignment — a generator or
load can carry an area or zone different from the bus it sits on. "Scale by Bus→Area" and
"Scale by Area" therefore pick up genuinely different device sets on such a case. This is the
same area-vs-bus mismatch already known from PTDF/shift-factor semantics, recurring here in a
different tool.

### Injection-group scaling: the starting point changes the answer, not just the path

Scaling an Injection Group offers **Scale from Present Value** (adds an incremental delta,
split by participation factor) versus **Scale from Zero** (re-splits the entire new total by
participation factor from scratch). These only agree when the starting shares already equal
the participation factors — otherwise they're different answers, not different routes to the
same one. `Scale from Zero` additionally only works one injection group at a time.

### Four dispatch methods, four structurally different results

- **Proportional** — a normalized participation-factor split.
- **Merit Order** — fills each element to its MW limit, in participation-factor rank order,
  before touching the next element. This is a bang-bang allocation, not a smooth one, and it
  always enforces generator MW limits regardless of whether "Enforce Gen MW Limits" is checked.
- **Economic Merit Order** and **Merit Order Close** — cost-based dispatch, structurally
  different again from rank-order Merit Order.

Picking a method is picking a physical story, not a speed/precision tradeoff — "scale up load
and re-dispatch generation" needs the method matched to the intended story rather than left at
the Proportional default.

### The AGC-filtering trap: shares computed from everyone, moved by only some

"Ignore AGC flag to calculate participation but use AGC flag to scale individual loads/
generators" computes participation shares from **all** elements, AGC-eligible or not, but then
only actually moves the AGC-eligible ones. The remainder that a non-AGC element "should" have
taken is not redistributed to the AGC-eligible set — it is silently absorbed elsewhere,
ultimately by the slack bus. This is a different, narrower option than "Scale Only AGCable
Generation and Load," which excludes non-AGC elements from the participation calculation
itself rather than just from the move.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*


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

# ==== loss-voltage-driving-point-sensitivities.md ====

---
type: concept
domain: cross-cutting
aliases: [loss-sensitivity, flow-voltage-sensitivity, driving-point-impedance, self-sensitivity, penalty-factor]
tags: [loss-sensitivity, voltage-sensitivity, driving-point-impedance, sensitivities, powerworld, cross-cutting]
---

# Loss, flow/voltage, and driving-point sensitivities — reference frames that trap unwary reads

## Abstract

Three sensitivity families that share nothing with PTDF/LODF except the word
"sensitivity": loss sensitivities, whose absolute value is meaningless outside a
differenced pair; flow/voltage sensitivities, which read zero at every PV bus unless AVR
is temporarily disabled; and driving-point impedance, whose answer depends entirely on
which of three Ybus models it's built from. Each has a silent-failure mode that produces
a plausible-looking wrong number rather than an error. For transaction-based sensitivities
(PTDF/shift factor/OTDF), see [ptdf-shift-factor-otdf](ptdf-shift-factor-otdf.md); for
fast N-1 flow redistribution, see [lodf](lodf.md).

## Connections

**Up:** [Home](../index.md) · **Across:** [ptdf-shift-factor-otdf](ptdf-shift-factor-otdf.md) ·
[lodf](lodf.md) · **Deeper:** [pw-power-flow](pw-power-flow.md)

## Content

### Loss sensitivities: only differences are meaningful

Every loss sensitivity is computed the same way underneath — model a 1 MW/1 Mvar
injection at bus `i` and see how it's absorbed at the island slack — regardless of which
"Loss Function Type" you picked for reporting (Each Island / Each Area / Each
Area-or-Super-Area / a user-specified list). The Loss Function Type only chooses which
aggregate loss total the number is expressed against; the underlying calculation is
always slack-referenced. That means reporting a single sensitivity value as an absolute
fact — "bus A's loss sensitivity is -0.04 MW/MW" — is wrong on its face. Only a
*difference* between two buses' sensitivities, used through superposition for a specific
transfer (`Σ(MW_i × sens_i)` across the transfer's participants), means anything.

**"User-Specified" freezes stale values.** Selecting that Loss Function Type does not
trigger a recalculation — it locks in whatever sensitivities were last computed under a
*different* type. Before trusting a read, confirm which type is currently active and
whether a calculate action has actually run since the last topology or dispatch change.

### Flow/voltage sensitivities: PV buses read zero by construction, not by insensitivity

In the base Single-Meter/Multiple-Transfers and Self-Sensitivity calculations, a PV bus's
voltage is pinned by AVR control in the Jacobian, so a change in real or reactive
injection there produces no voltage change — that's the model, not evidence the bus is
insensitive. Getting a real voltage sensitivity at a generator bus requires temporarily
converting participating PV buses to PQ (fixed Mvar, AVR off): the "Set generators off
AVR... to fixed" option on Single-Transfer/Multiple-Meters does this by turning off AVR,
re-solving, computing the sensitivity, then restoring AVR and re-solving again. A script
driving this should expect **two power-flow solves per call**, and that the case's
dispatch afterward is not guaranteed identical to before (re-convergence, not exact
restoration).

Five tabs cover different (source, target) shapes:

- **Single Meter/Multiple Transfers** — one flow, injection tested at every bus.
- **Single Transfer/Multiple Meters** — one seller/buyer transfer, voltage read at every
  bus.
- **Self Sensitivity** — a bus's own `dV/dP`, `dV/dQ`; fast, restricted to displayed
  buses.
- **Multiple Meters/Single Control Change** — one control device (generator setpoint,
  transformer tap, phase shifter angle, switched shunt Mvar, or branch series reactance
  `Xinj`) against every bus/branch/interface. The `Xinj` control type is the scriptable
  way to ask "what if I added series compensation here" without editing the branch.
- **Multiple Meters/Multiple Control Change** — a full control × meter matrix, exposed
  via SimAuto as `MULTMETERMULTCONTROLSENS`.

### Driving-point impedance: the answer depends on which Ybus you point it at

Three model choices produce three different numbers for the same bus:

1. **Power Flow Ybus** — built from power-flow data only, no generator/motor internal
   impedance, referenced to the power-flow slack.
2. **Transient Stability, including bus local shunts** — the TS Ybus with shunts and
   generator/motor internal impedance left in.
3. **Transient Stability, without bus local shunts** — the same TS Ybus but with the
   local bus's own shunt/generator/motor impedance subtracted out before inverting. This
   is the two-bus-equivalent / SMIB convention.

Both TS-based options require transient stability data to already be loaded — calling
them without it is a precondition failure, not an automatic fallback to power-flow data.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*


---

# ==== network-cut-and-query-tools.md ====

---
type: concept
domain: tooling
aliases: [network-cut, facility-analysis, min-cut, max-flow, graph-flow, shortest-path, radial-bus-paths]
tags: [powerworld, network-cut, facility-analysis, max-flow, min-cut, shortest-path, topology, edit-mode]
---

# Network Cut and Topological Query Tools

## Abstract

Four tools answer different topological questions but share underlying primitives that are
easy to conflate: a Network Cut is a manually-chosen boundary (the same bus-selection mechanism
scaling and equivalencing use to pick "which system"), Facility Analysis is an actual min-cut
computation over a pure connectivity graph (not power flow), Radial Bus Paths and Shortest
Path/Set-Bus-Field share one distance-measure abstraction that silently clamps negative field
values, and none of these verify a definition is complete before running — an ill-defined
boundary just fails to bisect the system rather than erroring up front.

## Connections

**Up:** [pw-power-flow](pw-power-flow.md) · **Across:** [limit-monitoring-and-scaling](limit-monitoring-and-scaling.md) · [case-restructuring-tools](case-restructuring-tools.md) · **Deeper:** [references/aux-script-commands](../references/aux-script-commands.md)

## Content

### A Network Cut is a manual boundary that isn't verified for completeness

A Network Cut is a manually-chosen set of branches, interfaces, and DC lines that is supposed
to form a topologically complete separation of the system. The tool does not verify closure
beyond failing on an obviously ill-defined attempt — a partial cut plane silently fails to
bisect the system rather than erroring at definition time. Once a valid cut exists, a reference
bus on one side selects which side is "of interest," and an optional "tiers of neighbors"
parameter extends inclusion across the boundary. This is the same selection primitive that
underlies both scaling's "select buses using a network cut" option and equivalencing's "which
system" bus assignment described in [limit-monitoring-and-scaling](limit-monitoring-and-scaling.md)
and [case-restructuring-tools](case-restructuring-tools.md) — one mechanism, multiple consumers.

### Facility Analysis is an actual min-cut, not "the branches you'd guess"

Facility Analysis takes an explicit Facility bus set and External bus set (via the same
bus-selection mechanism equivalencing uses) and computes the **minimum number of branches**
whose removal electrically isolates one from the other — a real max-flow/min-cut computation
via an augmenting-path algorithm, with every branch treated as unit capacity and each named
group collapsed into a single supernode. It runs only in Edit Mode, respects present open/
closed branch status (open branches are treated as absent), and reports an incomplete graph
structure if a bus is assigned to both sets at once.

**"Graph Flow" here is a pure connectivity abstraction, not power flow** — every branch gets
capacity 1 regardless of its real electrical rating, purely to make the isolation problem
solvable as max-flow/min-cut. A Facility Analysis "capacity" number should never be read as an
MW/MVA capacity.

### Radial Bus Paths: two toggles can change the reported radial group drastically

Find Radial Bus Paths has a Bus-vs-SuperBus traversal mode and a parallel-branch policy, and
both change which buses and branches get reported as radial — sometimes drastically, with the
same topology reporting different path lengths purely depending on these two settings. A script
consuming the radial-path result fields must fix both options deliberately; the same underlying
topology does not yield one canonical radial grouping.

### Shortest Path and Set-Bus-Field share a distance measure that silently clamps negative values

Shortest Path Between Buses and Set Bus Field From Closest Bus share one distance-measure
abstraction — reactance, impedance magnitude, the `Length` field, unweighted hop count ("Number
of Nodes"), or any other numeric branch field — and one branch-traversal filter (`All`, `Only
Closed`, an advanced `Meets Filter`, and for Set-Bus-Field also `Selected`). **Negative field
values are silently clamped to "extremely small" rather than rejected** — a distance
computation built on a field that happens to carry negative entries (a signed custom field, for
example) will be distorted with no warning.

### Unused Bus Numbers writes to a file, not to memory

`Unused Bus Numbers` only writes its result to a text file — there is no in-session query that
returns "N free bus numbers" directly. A script that needs new bus numbers (a synthetic-grid
generator inserting substations, for example) has to either read this exported file or compute
unused numbers itself from the existing bus list, and should not expect a script-command form
that returns numbers as a value.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*


---

# ==== objectid-identification-traps.md ====

---
type: concept
domain: tooling
aliases: [objectid-traps, multi-section-line-identifier, three-winding-objectid, star-bus-identification]
tags: [powerworld, objectid, aux, multi-section-line, three-winding-transformer, identification]
---

# ObjectID identification traps: multi-section lines and 3-winding transformers

## Abstract

Two branch shapes need extra identifiers that a normal 3-field `ObjectID` doesn't carry, and
getting the field count wrong doesn't error — the parser accepts both the 3-field and
4-field shapes contextually, so a missing or extra identifier resolves to **the wrong
section or the wrong winding, silently**, with a plausible-looking row coming back. This
page exists to make that failure concrete and give the check to run before trusting an
ObjectID match.

## Connections

**Up:** [powerworld-script-transfer](powerworld-script-transfer.md) (ObjectID compact single-field syntax) ·
[aux-only-powerworld](aux-only-powerworld.md) (field-name provenance rule) ·
**Across:** [simauto-output-shapes-and-discovery](simauto-output-shapes-and-discovery.md) (raw field discovery) ·
[topology-consolidation-and-derived-status](topology-consolidation-and-derived-status.md)
(a different way an object's identity silently shifts — there it's `BusNum` moving under ITP
consolidation, here it's the wrong section/winding resolving from a malformed ObjectID) ·
[required-fields-for-object-creation](required-fields-for-object-creation.md) (a sibling
silent-failure gate on the write path — that one skips creating an object outright, this one
matches the wrong existing one) ·
**Deeper:** Simulator's *Auxiliary Files and Script Commands* manual chapter (Help menu)

## Content

### Resolution order, and what it can't do

`ObjectID` resolves against a fixed precedence: ObjectID string itself → Label → Primary
Keys → Secondary Keys. Loading by ObjectID or Label can never create a new object, only
match an existing one — relevant if `SetElseCreateData` or any `CreateIfNotFound`-driven
write is keyed off ObjectID/Label rather than raw primary keys, since that path will never
create the row it can't find.

### Multi-section lines need a 4th identifier

A normal branch has 3 identifiers — from bus, to bus, circuit ID:

```
BRANCH 23 29 'AB'
```

A branch that is part of a **multi-section line** needs a 4th identifier, the section
number, appended at the end:

```
BRANCH 23 29 'AB' 4
```

**The trap:** using 3 identifiers when the branch needs 4 (or the reverse) does not error —
the parser accepts both shapes contextually and resolves to the wrong section rather than
refusing the match. A `LineShunt` attached to a branch inside a multi-section line follows
the same pattern one level up: 6 identifiers instead of the normal 5 (from bus, to bus,
terminal bus, circuit ID, shunt ID, + section ID appended last), e.g.
`LineShunt 40489 40687 40489 2 A 6`. The terminal-bus field (3rd) must be the bus on the same
side as the shunt.

### Three-winding transformer windings: two identification schemes

A winding of a three-winding transformer can be named two ways:

- **Legacy star-bus form** — `BRANCH 10001 10004 'AB'` — where `10001`/`10004` are the
  internal star-bus number and one terminal bus. **Not portable**: PSS/E RAW files don't
  persist star-bus numbers across a load, and PowerWorld can renumber star buses on every
  RAW read according to its NEAR/MAX/VALUE setting for star-bus numbering.
- **4-identifier terminal-bus form** — `BRANCH 10001 10002 10003 'AB'` — all three terminal
  buses plus circuit ID. The branch is interpreted as the winding at the *first* listed
  terminal bus; the order of the 2nd and 3rd bus numbers doesn't matter.

Prefer the 4-identifier form for anything that must survive a PTI RAW round-trip, since the
star-bus numbers the legacy form depends on aren't stable across reads.

### FixedNumBus (Version 24+) changes what the integers mean

If a bus carries a FixedNumBus designation, an ObjectID's bus-number fields may be given as
FixedNumBus integers instead of live bus numbers — but if you do this, **every** integer in
that ObjectID string must be a FixedNumBus integer, not a mix of the two numbering schemes.
When writing an AUX file, FixedNumBus integers used to specify an object are also what gets
written back out, so a file already written this way stays self-consistent — but reading a
mixed-numbering ObjectID string is another way to silently resolve to the wrong object.

### Before trusting a match

Given the silent-wrong-match failure mode above, verify identity rather than assume it:
read the resolved row back and check its own key fields (from/to bus, circuit ID, and
section or star-bus number as applicable) against what you intended, rather than trusting
that a returned row belongs to the object you asked for.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*


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

# ==== post-contingency-aux-state-carryover.md ====

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


---

# ==== powerworld-help-corpus.md ====

---
type: dataset
domain: tooling
aliases: [powerworld-webhelp, webhelp, simulator-help, PowerWorld-Help, help-corpus]
tags: [powerworld, documentation, retrieval, agent-workflow, knowledge-base, simauto]
---

# PowerWorld help corpus

## Abstract

**The PowerWorld Simulator WebHelp, captured as 80 offline Markdown chapter files holding 1,670 topics —
and the reason you cannot navigate it by its own table of contents.** The manual is organised the
way the *program* is organised (ribbon tabs, dialogs, add-ons), so every research subject is split
across chapters that the contents page never puts side by side. Three splits bite repeatedly:
time-step work, switched-shunt/reactive work, and anything that has both a dialog and a script
command. A topic-level index that re-cuts the corpus by research domain lives outside the wiki;
this page is the *why*, the retrieval gotchas, and the one provenance rule the help system itself
states.

Read this before searching the help for anything. It costs less than one wrong grep.

## Connections

**Up:** [Home](../index.md) ·
**Across:** [aux-only-powerworld](aux-only-powerworld.md) (the field-name provenance rule this page confirms from a second
source), [aux-script-catalog](../references/aux-script-commands.md) (the SCRIPT action catalog, condensed from the *other* manual),
[esapp](esapp.md), [powerworld-simauto](powerworld-simauto.md) ·
**Distilled from this corpus:** [solver-mechanics-and-failure-modes](solver-mechanics-and-failure-modes.md),
[filter-expression-language](filter-expression-language.md), [simauto-output-shapes-and-discovery](simauto-output-shapes-and-discovery.md),
[raw-epc-roundtrip-traps](raw-epc-roundtrip-traps.md) — a sample of the content pages now carrying manual
material directly; each subject routing page below names its own full set ·
**Deeper:** [timestep-simulation](timestep-simulation.md), [gic](gic.md)

## Content

### What it is

An offline Markdown capture of `powerworld.com/WebHelp`, the Simulator manual. As captured
2026-09-18: **1,670 topics in 80 chapter files (~6.6 MB) and 3 PDFs.** Internal links are in good
order — measured on the pinned commit, **zero broken anchors**.

**But the figures are missing.** The chapters carry 1,120 `images/*.gif` references and the
repository contains no `images/` directory, so every figure reference is broken in a clone. The
corpus's own README describes 1,097 figures at 273 MB; they were never committed. Where a topic
explains itself with a block diagram — most of the dynamic-model catalog — the offline copy does
not carry the explanation. It ships a `manifest.json` (chapter list, sizes,
cross-reference graph) and a `toc.json` (the help system's own contents tree).

It is **the program's documentation, not a textbook.** It describes dialogs, fields and options.
Where it states theory it is brief and worth reading — the power-flow solution chapter is the
main place it does ([pw-power-flow](pw-power-flow.md) lists what) — but the bulk is reference material for a UI.

### Why its own categories cut the wrong way

The corpus groups its chapters into the manual's parts: *Getting Started*, *Viewing Case Data*,
*Contingency Analysis*, *Add-Ons*, *Transient Models*, and so on. Those are the program's
divisions. A research question crosses them:

- **Running a time-step study** spans four chapters — tool, script commands, programmatic entry
  point and batch engine ([pw-timestep-sim](pw-timestep-sim.md) names them).
- **Reactive support** — switched-shunt material is spread over the power-flow chapter, *both*
  object-property chapters (edit mode and run mode have separate pages for the same object), the
  contingency-options chapter (post-contingency shunt behaviour), the time-step chapter (shunt
  control time-step options) and the SVC control-mode topics, which sit in the appendix described
  below.
- **Anything with both a dialog and a command** — the dialog is documented in its feature chapter,
  the command that does the same thing is in the scripting chapter, and neither page is obliged
  to mention the other.

The practical consequence: **finding the feature chapter is not finding the answer.** Expect a
subject to live in three or four files and plan the read accordingly.

### The appendix that is not in the table of contents

Roughly 4% of topics — 67 in this capture — are reachable **only by cross-link**, never by the
contents tree. In the capture they are swept into a trailing "additional linked topics" chapter,
which is consequently a grab bag spanning half a dozen unrelated subjects under no useful
heading — each subject page flags its own stranded topics. This is real content, not scraps:
several of those pages are the only description of their mechanism anywhere in the manual.

**So a table-of-contents-shaped search misses them.** Grep the whole corpus, not the contents.

### The legacy-duplicate trap

The help ships current API pages *and* the version-9 pages for the same functions, with nearly
identical titles. A grep for a SimAuto function name returns both, and the old page will look
plausible. **Check the title for a version marker before trusting an automation page** — and
prefer the current chapter, which documents the typed and flat-output variants the legacy pages
predate.

### The field-name provenance rule, confirmed twice

[aux-only-powerworld](aux-only-powerworld.md) established that the Auxiliary File Format manual contains **no per-object
field catalog**. The WebHelp says the same thing about itself, explicitly: it names field variables
as the basis of every automation call, gives `GenMW` and `BusNum` as examples, and then states that
rather than list them, Simulator will **generate the list on demand from its Help menu**.

So there are two manuals and neither one holds the field names. The rule stands and now has two
sources: **verify a field name against the live schema — `esapp`'s field metadata, or
`GetFieldList` — never against prose in a manual.** A page that names a field is illustrating a
concept, not publishing a catalog.

### Roughly a tenth of the topics say nothing

**164 of the 1,670 topics (9.8%) carry no usable body.** 76 hold the capture's own marker
*"This topic has no body text in the source help file"* — the vendor's table of contents lists a
topic the vendor never wrote. The other 88 are under 150 characters, usually nothing but an
auto-correction block reading *"To be documented."*

They are concentrated in the dynamic-model chapters and **interleaved with fully-documented
models in the same file**, so nothing about a topic's position or title tells you which kind it
is. Every one costs a read to discover it is empty. A model name appearing in the manual is
therefore **not** evidence that the model is documented.

### Six copies of the release notes are 6% of the corpus

The manual's *"What's New"* topic appears **six times** in the capture and together those six
hold about **92k tokens — 6.2% of all body text in the corpus**, making them the largest topics
in it by a wide margin. They are version history, not reference material.

This generalises past this one corpus: **in a converted vendor manual, the largest topics are
usually the least useful ones.** Release notes, licence text and "what's new" pages are long,
highly duplicated, and answer no question anyone asks. Check a topic's size before opening it and
treat the big ones with suspicion rather than deference.

### What its AI-readiness scores actually measure

Scored with the `ai-readiness-audit` rubric (measured 2026-09-20, all chapter files), the corpus
lands around 60/100 overall, and **most of that gap is genre, not defect**. The heuristics flagged
*"instructions read as descriptive, not actionable"* on **every** file and *"no gotchas section"* on
every file; median imperative ratio across the corpus is **0.00**. That is what a reference manual
is. Its "undefined terminology" signal is also largely artefact — the detector counts `AND`, `NOT`,
`YES`, `ACOS` and model parameter names among hundreds of "undefined acronyms", of which only a
couple of dozen are real domain terms.

The lesson is about the measurement, not the manual, and it generalises to any scored corpus:
**a readiness rubric built for instruction docs will mark a reference corpus down for being a
reference corpus.** Three findings survive that correction and are real — oversized sections
(282 across the chapter files, the worst a single ~19.7k-token section), heavy duplication, and
the stub topics above. Those are worth acting on; the actionability score is not.
writing-ai-ready-claude-md already states the principle as a house rule — *"actionability is
genre-capped… respect the genre"* and *"don't score-game"* — and this is what it looks like at
corpus scale.

### Why this corpus is cheap to search

what-drives-hop-count measured that hop count tracks the **number of candidate pages** a search
works through, not total bytes — so splitting a long page in two can make retrieval *more*
expensive. This capture was built the same way round: chapters are cut at roughly 150 KB, each
sized to fit in one context window, and a chapter is split only when it exceeds that. 1,670 topics
compressed into 80 files is the shape that measurement predicts will retrieve cheaply, which is
consistent with the hop counts the kit posted in that benchmark.

The corollary for anyone tempted to "improve" it: **do not explode it into one file per topic.**
That is 1,670 candidates for the same bytes.

### What an index over it buys

Chapter-level categories already ship in the corpus manifest, so the value of re-indexing is
entirely at **topic level**: tagging each of the 1,670 topics with the research domain it serves,
plus cross-cutting tags that ignore chapter boundaries, so a domain question resolves to the two
or three files that actually hold it. That artifact is a repo index, not wiki content — the wiki
carries the reasoning, the repo carries the 1,670 rows.

---

*Ported from the research vault. Describes and routes over the PowerWorld Simulator help corpus; reproduces no manual text.*


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

# ==== ptdf-shift-factor-otdf.md ====

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


---

# ==== pw-contingency.md ====

---
type: concept
domain: tooling
aliases: [pw-ctg, contingency-analysis, pw-contingency-analysis]
tags: [powerworld, manual, contingency, ras, limits]
---

# PowerWorld: Contingency analysis

## Abstract

Contingency analysis end to end: how contingencies are defined, what an element can do, every option that changes the result, and how results are read back. The largest single analysis subject in the manual after dynamics.

**Two traps this kit now covers inline:** the aux-hook state-carryover bug in
[post-contingency-aux-state-carryover](post-contingency-aux-state-carryover.md), and the batch/ranking
tools built on top of ordinary contingency analysis in
[contingency-linked-sensitivities](contingency-linked-sensitivities.md). Read this page for the
chapter map — **96 topics across 7 chapter files.**

## Connections

**Up:** [pw-manual-map](pw-manual-map.md) · **Corpus:** [powerworld-help-corpus](powerworld-help-corpus.md)

**Across:** [pw-interfaces](pw-interfaces.md) ·
[ptdf-shift-factor-otdf](ptdf-shift-factor-otdf.md) ·
[topology-consolidation-and-derived-status](topology-consolidation-and-derived-status.md) ·
[pw-scripting-automation](pw-scripting-automation.md)

**Now covered inline:** [post-contingency-aux-state-carryover](post-contingency-aux-state-carryover.md) ·
[contingency-linked-sensitivities](contingency-linked-sensitivities.md)

## Content

### What it covers

- Defining contingencies: auto-generation, PSS/E and PSLF list formats, the concise RAS format
- The contingency element dialog — one topic per element type, from branch to script
- Options that change the answer: DC and screening, post-contingency AGC, load throw-over, switched-shunt post-CTG behaviour, limit monitoring and monitoring exceptions
- Remedial action schemes and global actions
- Running, results by element, violation notes, report writing, comparing two runs
- CTG combination analysis

### Where it lives

| Chapter file | Topics | Holds |
|---|--:|---|
| `22-contingency-analysis-options.md` | 26 | The Contingency Analysis dialog: Contingencies tab and the full Options tab. |
| `24-contingency-element-dialog.md` | 24 | The Contingency Element dialog and every element action type. |
| `21-contingency-analysis-overview-and-records.md` | 19 | What contingency analysis does, available contingency actions, case references and contingency records. |
| `23-contingency-analysis-running-and-results.md` | 16 | Running contingency analysis, file formats, sensitivity analysis, results and comparing runs. |
| `52-additional-linked-topics-part1.md` | 7 | Topics reachable from links inside the manual but not listed in the help system's table of contents. |
| `25-ctg-combo-analysis.md` | 3 | Contingency combination analysis and the combination element dialog. |
| `05-case-information-displays-by-object-part1.md` | 1 | The per-object case information displays: buses, generators, loads, lines, transformers, shunts, interfaces, ownership and more. |

### What bites

- Reference-state handling is its own set of topics and is easy to skip; it decides what the violations are measured *against*.
- Several contingency options live one link away in the appendix chapter — stuck-breaker creation, legacy definitions, and the relationship between contingencies, model conditions and model filters.

---

*Subject page over the PowerWorld Simulator help corpus. Describes and routes; reproduces
no manual text. Topic-level detail is in `powerworld-help-index/ROUTING.md`.*

---

*Ported from the research vault. Describes and routes over the PowerWorld Simulator help corpus; reproduces no manual text.*


---

# ==== pw-data-model.md ====

---
type: concept
domain: tooling
aliases: [pw-fields, pw-case-information, object-field-reference]
tags: [powerworld, manual, fields, case-information, object-properties, filters]
---

# PowerWorld: Objects and fields

## Abstract

The object and field reference: every case-information display, every object property dialog, and the filtering and expression machinery that selects rows. This is where you find out what a field is called and whether you can write to it.

**The filtering/expression grammar and the object-creation gotchas are now documented inline** —
[filter-expression-language](filter-expression-language.md),
[datamaintainer-and-object-groups](datamaintainer-and-object-groups.md),
[data-check-objects](data-check-objects.md) and
[required-fields-for-object-creation](required-fields-for-object-creation.md) cover that ground
without a manual detour. Read this page for the chapter map — **177 topics across 15 chapter
files.**

## Connections

**Up:** [pw-manual-map](pw-manual-map.md) · **Corpus:** [powerworld-help-corpus](powerworld-help-corpus.md)

**Across:** [pw-scripting-automation](pw-scripting-automation.md) · [pw-power-flow](pw-power-flow.md) ·
[pw-interfaces](pw-interfaces.md) · [raw-epc-roundtrip-traps](raw-epc-roundtrip-traps.md)

**Now covered inline:** [filter-expression-language](filter-expression-language.md) ·
[datamaintainer-and-object-groups](datamaintainer-and-object-groups.md) ·
[data-check-objects](data-check-objects.md) ·
[required-fields-for-object-creation](required-fields-for-object-creation.md)

**Research pages that use this:** [esapp](esapp.md)

## Content

### What it covers

- Model Explorer and case information display mechanics: columns, sorting, formats, custom fields
- Filtering: the filterbar, area/zone/owner filters, advanced filters, model conditions and filters
- Expressions, model expressions, string expressions, functions and operators
- Key fields and required fields
- Displays by object: bus, generator, load, line, transformer, DC line, shunt, island, owner
- Object property dialogs in both edit mode and run mode — the same object documented twice
- Generator cost models and economic curves; data checks and the difference case

### Where it lives

| Chapter file | Topics | Holds |
|---|--:|---|
| `04-model-explorer-and-case-information-part3.md` | 26 | Model Explorer and the mechanics of case information displays: filtering, sorting, columns, formats. |
| `04-model-explorer-and-case-information-part1.md` | 24 | Model Explorer and the mechanics of case information displays: filtering, sorting, columns, formats. |
| `06-object-properties-edit-mode-part3.md` | 16 | Edit-mode property dialogs for every Simulator object type. |
| `05-case-information-displays-by-object-part2.md` | 15 | The per-object case information displays: buses, generators, loads, lines, transformers, shunts, interfaces, ownership and more. |
| `06-object-properties-edit-mode-part1.md` | 14 | Edit-mode property dialogs for every Simulator object type. |
| `07-object-properties-run-mode-and-general-part2.md` | 14 | Run-mode and general property dialogs, object groups, supplemental data and data maintainers. |
| `04-model-explorer-and-case-information-part2.md` | 13 | Model Explorer and the mechanics of case information displays: filtering, sorting, columns, formats. |
| `05-case-information-displays-by-object-part1.md` | 13 | The per-object case information displays: buses, generators, loads, lines, transformers, shunts, interfaces, ownership and more. |
| `05-case-information-displays-by-object-part3.md` | 12 | The per-object case information displays: buses, generators, loads, lines, transformers, shunts, interfaces, ownership and more. |
| `07-object-properties-run-mode-and-general-part1.md` | 11 | Run-mode and general property dialogs, object groups, supplemental data and data maintainers. |
| `06-object-properties-edit-mode-part2.md` | 8 | Edit-mode property dialogs for every Simulator object type. |
| `08-view-case-data-tools.md` | 7 | Data View, Data Check, Bus View, Substation View, Spatial View, labels, difference case and fixed-number buses. |
| `52-additional-linked-topics-part1.md` | 2 | Topics reachable from links inside the manual but not listed in the help system's table of contents. |
| `10-power-flow-solution-and-options-part2.md` | 1 | Power flow solution theory, simulator options, and solution and control settings. |
| `18-general-tools.md` | 1 | Limit monitoring, difference case, scale case, connections tools and other general-purpose tools. |

### What bites

- Edit mode and run mode have **separate pages for the same object**; the field sets differ and so does what is writable.
- Key fields are the load-bearing concept for any automation. **A write that omits them silently does nothing** — no error, no change ([esapp](esapp.md), [adding-devices-esapp](../methods/adding-devices-esapp.md)). Required fields are the separate, smaller gate on *creating* a new object; see [required-fields-for-object-creation](required-fields-for-object-creation.md).

---

*Subject page over the PowerWorld Simulator help corpus. Describes and routes; reproduces
no manual text. Topic-level detail is in `powerworld-help-index/ROUTING.md`.*

---

*Ported from the research vault. Describes and routes over the PowerWorld Simulator help corpus; reproduces no manual text.*


---

# ==== pw-injection-groups.md ====

---
type: concept
domain: tooling
aliases: [pw-injection-group, participation-points]
tags: [powerworld, manual, injection-group, participation-point, transfer]
---

# PowerWorld: Injection groups

## Abstract

Injection groups and participation points — the object that says *which* generators and loads move, and in what proportion, when a transfer is scaled or ramped. The input side of every PV, QV and ATC study.

**The normalization and exclusion mechanics behind a stored participation factor are now
documented inline** — see [injection-group-participation](injection-group-participation.md). Read
this page for the chapter map — **10 topics across 3 chapter files.**

## Connections

**Up:** [pw-manual-map](pw-manual-map.md) · **Corpus:** [powerworld-help-corpus](powerworld-help-corpus.md)

**Across:** [pw-pv-qv](pw-pv-qv.md) · [pw-interfaces](pw-interfaces.md) · [pw-power-flow](pw-power-flow.md)

**Now covered inline:** [injection-group-participation](injection-group-participation.md)

## Content

### What it covers

- Injection group overview, creation, deletion and auto-insertion
- The injection group display and dialog
- Participation points: overview, records display, add dialog
- The injection group file format

### Where it lives

| Chapter file | Topics | Holds |
|---|--:|---|
| `07-object-properties-run-mode-and-general-part2.md` | 6 | Run-mode and general property dialogs, object groups, supplemental data and data maintainers. |
| `05-case-information-displays-by-object-part3.md` | 3 | The per-object case information displays: buses, generators, loads, lines, transformers, shunts, interfaces, ownership and more. |
| `03-cases-files-and-formats.md` | 1 | Opening, creating, closing and saving cases; every supported file format; project files. |

### What bites

- Like interfaces, this has no chapter of its own and is gathered here.
- An ATC or PV run silently depends on how these are defined; the study chapters reference the object without documenting it.

---

*Subject page over the PowerWorld Simulator help corpus. Describes and routes; reproduces
no manual text. Topic-level detail is in `powerworld-help-index/ROUTING.md`.*

---

*Ported from the research vault. Describes and routes over the PowerWorld Simulator help corpus; reproduces no manual text.*


---

# ==== pw-interfaces.md ====

---
type: concept
domain: tooling
aliases: [pw-interface, flowgates, nomograms]
tags: [powerworld, manual, interface, flowgate, nomogram]
---

# PowerWorld: Interfaces and flowgates

## Abstract

The interface object — a named group of monitored branches — plus flowgates and nomograms. Small subject, disproportionate importance: the interface is the monitored element for every transfer, flowgate and nomogram study.

**The direction/sign and element-type mechanics behind a reported flow are now documented
inline** — see [interface-elements-and-monitoring](interface-elements-and-monitoring.md). Read
this page for the chapter map — **11 topics across 4 chapter files.**

## Connections

**Up:** [pw-manual-map](pw-manual-map.md) · **Corpus:** [powerworld-help-corpus](powerworld-help-corpus.md)

**Across:** [pw-contingency](pw-contingency.md) · [pw-injection-groups](pw-injection-groups.md) ·
[pw-data-model](pw-data-model.md)

**Now covered inline:** [interface-elements-and-monitoring](interface-elements-and-monitoring.md)

## Content

### What it covers

- Interface records, element, field and pie-chart information
- Auto-inserting interfaces into a case
- Nomogram records and dialog
- The interface data file format
- Loading and saving NERC flowgates as Excel

### Where it lives

| Chapter file | Topics | Holds |
|---|--:|---|
| `07-object-properties-run-mode-and-general-part2.md` | 6 | Run-mode and general property dialogs, object groups, supplemental data and data maintainers. |
| `05-case-information-displays-by-object-part3.md` | 2 | The per-object case information displays: buses, generators, loads, lines, transformers, shunts, interfaces, ownership and more. |
| `12-building-onelines-branches-and-devices.md` | 2 | Inserting transmission lines, transformers, series capacitors, switched shunts, interfaces, injection groups and oneline links. |
| `03-cases-files-and-formats.md` | 1 | Opening, creating, closing and saving cases; every supported file format; project files. |

### What bites

- This subject has no chapter of its own in the manual — it is scattered across the case-information, object-property, oneline and file-format chapters, which is why it is gathered into one page here.
- The NERC flowgate load/save topics sit in the oneline-drawing chapter despite having nothing to do with onelines: they read and write interface records via Excel.

---

*Subject page over the PowerWorld Simulator help corpus. Describes and routes; reproduces
no manual text. Topic-level detail is in `powerworld-help-index/ROUTING.md`.*

---

*Ported from the research vault. Describes and routes over the PowerWorld Simulator help corpus; reproduces no manual text.*


---

# ==== pw-manual-map.md ====

---
type: concept
domain: tooling
aliases: [pw-manual, powerworld-manual-map, pw-subjects, simulator-manual-map]
tags: [powerworld, manual, navigation, moc, documentation]
---

# PowerWorld manual — subject map

## Abstract

**Twenty-five subject pages over the PowerWorld Simulator manual, cut by what you are trying to
do rather than by how the program is organised.** The manual groups its 1670 topics by ribbon tab
and dialog, so a research subject lands in three or four chapters its contents page never shows
together. Start here, pick the subject, and the page names the chapter files to open.

These pages describe and route. They reproduce no manual text — the corpus itself lives in
[powerworld-help-corpus](powerworld-help-corpus.md), and topic-level detail in the routing index beside it.

## Connections

**Up:** [Home](../index.md) · **Corpus:** [powerworld-help-corpus](powerworld-help-corpus.md) ·
**Research:** [esapp](esapp.md) · [powerworld-simauto](powerworld-simauto.md)

## Content

### Start here

| If you want to… | Open |
|---|---|
| solve a case, or understand a control acting during the solve | [pw-power-flow](pw-power-flow.md) |
| run or interpret contingencies | [pw-contingency](pw-contingency.md) |
| run a quasi-static study across time | [pw-timestep-sim](pw-timestep-sim.md) |
| find a field name, or work out if it is writable | [pw-data-model](pw-data-model.md) |
| automate anything from Python | [pw-scripting-automation](pw-scripting-automation.md) |
| work on reactive support or voltage margin | [pw-pv-qv](pw-pv-qv.md) · [pw-power-flow](pw-power-flow.md) |
| look up a dynamic model | `38-ts-models-machine` … `46-ts-models-other` (21 files) |
| find out what a chapter file contains | the routing index, not these pages |

### Studies you run

| Subject | Topics | Files | Note |
|---|--:|--:|---|
| [Power flow](pw-power-flow.md) | 49 | 14 |  |
| [Contingency analysis](pw-contingency.md) | 96 | 7 |  |
| [Time Step Simulation](pw-timestep-sim.md) | 32 | 2 |  |
| [PV and QV curves](pw-pv-qv.md) | 25 | 1 |  |
| Optimal power flow | 44 | 7 | `30-optimal-power-flow-part1`, `30-optimal-power-flow-part2`, `06-object-properties-edit-mode-part1`, +4 more |
| SCOPF and OPF reserves | 29 | 1 | `31-scopf-and-opf-reserves` |
| Available Transfer Capability | 22 | 1 | `32-available-transfer-capability` |
| Fault analysis | 13 | 4 | `27-fault-analysis`, `52-additional-linked-topics-part1`, `03-cases-files-and-formats`, +1 more |
| GIC analysis | 7 | 2 | `47-geomagnetically-induced-currents`, `52-additional-linked-topics-part1` |

### Objects a study consumes

| Subject | Topics | Files | Note |
|---|--:|--:|---|
| [Interfaces and flowgates](pw-interfaces.md) | 11 | 4 |  |
| [Injection groups](pw-injection-groups.md) | 10 | 3 |  |
| Weather-dependent ratings | 14 | 2 | `28-weather`, `52-additional-linked-topics-part2` |
| Sensitivities | 27 | 4 | `20-sensitivities`, `23-contingency-analysis-running-and-results`, `22-contingency-analysis-options`, +1 more |
| Topology processing | 28 | 5 | `35-integrated-topology-processing`, `18-general-tools`, `52-additional-linked-topics-part1`, +2 more |

### Dynamics

| Subject | Topics | Files | Note |
|---|--:|--:|---|
| Transient stability | 90 | 9 | `36-transient-stability-overview-and-data-part1`, `37-transient-stability-analysis-dialog-part2`, `52-additional-linked-topics-part2`, +6 more |
| Dynamic model catalog | 580 | 21 | **155 say nothing** |

### Driving it from code

| Subject | Topics | Files | Note |
|---|--:|--:|---|
| [AUX files and SimAuto](pw-scripting-automation.md) | 99 | 8 |  |
| [Objects and fields](pw-data-model.md) | 177 | 15 |  |
| Cases and file formats | 30 | 7 | `03-cases-files-and-formats`, `08-view-case-data-tools`, `07-object-properties-run-mode-and-general-part2`, +4 more |
| Cruncher and distributed computing | 24 | 7 | `50-cruncher`, `10-power-flow-solution-and-options-part2`, `22-contingency-analysis-options`, +4 more |
| Scheduled actions | 5 | 1 | `48-scheduled-actions` |

### Editing and drawing

| Subject | Topics | Files | Note |
|---|--:|--:|---|
| Network tools | 30 | 5 | `19-edit-mode-tools`, `18-general-tools`, `06-object-properties-edit-mode-part2`, +2 more |
| Oneline diagrams | 175 | 14 | `13-building-onelines-graphics-and-insertion`, `11-building-onelines-network-objects`, `12-building-onelines-branches-and-devices`, +11 more |
| The Simulator interface | 39 | 4 | `02-simulator-ribbon`, `01-getting-started`, `10-power-flow-solution-and-options-part2`, +1 more |
| Licences and release notes | 14 | 3 | **8 say nothing** |

**Nine subjects have a detail page in this kit** — the ones linked above. The rest are
listed with the chapter files that hold them, which is the routing you actually need; their
detail pages live in the research vault this kit was extracted from.

### Before you trust anything in it

Four properties of this corpus decide whether an answer you find is real. They are stated once,
in [powerworld-help-corpus](powerworld-help-corpus.md), and not repeated here: **a subject is never one chapter**, **164
topics carry no usable body**, **superseded API pages sit beside current ones**, and **the manual
holds no per-object field catalog**. Read that page before your first serious search; each subject
page below carries only its own local traps.

### What these pages are not

They route; they do not teach. For the engineering, follow the **Research** links on each subject
page back into the vault. For topic-level detail — every one of the 1,670 topics with its anchor,
tags and size — use the routing index in `powerworld-help-index`, not these pages.

---

*Ported from the research vault. Describes and routes over the PowerWorld Simulator help corpus; reproduces no manual text.*


---

# ==== pw-power-flow.md ====

---
type: concept
domain: tooling
aliases: [pw-powerflow, powerflow-solution, simulator-power-flow]
tags: [powerworld, manual, power-flow, solver, voltage-control]
---

# PowerWorld: Power flow

## Abstract

How Simulator solves the AC and DC power flow, and every control that acts during the solve — remote regulation, Mvar sharing, line-drop compensation, droop with deadband, island AGC. Read it before touching solver options or asking why a case converged differently than expected.

**This kit now documents the mechanism inline** — [buscat-and-voltage-control](buscat-and-voltage-control.md),
[solver-mechanics-and-failure-modes](solver-mechanics-and-failure-modes.md),
[shunt-transformer-dfacts-control](shunt-transformer-dfacts-control.md) and
[generator-dispatch-and-diagnostics](generator-dispatch-and-diagnostics.md) cover the solve loop,
voltage/reactive control and dispatch without a manual detour. Read this page instead when you need
the chapter map: which of the 49 manual topics across 14 files holds a dialog or option this kit
doesn't cover yet.

## Connections

**Up:** [pw-manual-map](pw-manual-map.md) · **Corpus:** [powerworld-help-corpus](powerworld-help-corpus.md)

**Across:** [pw-pv-qv](pw-pv-qv.md) · [topology-consolidation-and-derived-status](topology-consolidation-and-derived-status.md) ·
[pw-timestep-sim](pw-timestep-sim.md)

**Now covered inline:** [buscat-and-voltage-control](buscat-and-voltage-control.md) ·
[solver-mechanics-and-failure-modes](solver-mechanics-and-failure-modes.md) ·
[shunt-transformer-dfacts-control](shunt-transformer-dfacts-control.md) ·
[generator-dispatch-and-diagnostics](generator-dispatch-and-diagnostics.md)

**Research pages that use this:** [esapp](esapp.md) · [powerworld-simauto](powerworld-simauto.md)

## Content

### What it covers

- Solution theory: bus equations, bus categories, the voltage/reactive equation choice
- Solver options — common, advanced, DC, island creation, post-solution actions
- Voltage and reactive control: remote regulation, Mvar sharing, setpoint tolerance, droop with deadband
- Transformer control, AVR and Mvar control dialogs; generator Q capability curves
- Ybus, Jacobian and admittance-matrix export; bus mismatches
- Governor power flow and island-based AGC

### Where it lives

| Chapter file | Topics | Holds |
|---|--:|---|
| `10-power-flow-solution-and-options-part2.md` | 10 | Power flow solution theory, simulator options, and solution and control settings. |
| `10-power-flow-solution-and-options-part1.md` | 9 | Power flow solution theory, simulator options, and solution and control settings. |
| `05-case-information-displays-by-object-part3.md` | 5 | The per-object case information displays: buses, generators, loads, lines, transformers, shunts, interfaces, ownership and more. |
| `05-case-information-displays-by-object-part1.md` | 4 | The per-object case information displays: buses, generators, loads, lines, transformers, shunts, interfaces, ownership and more. |
| `06-object-properties-edit-mode-part1.md` | 4 | Edit-mode property dialogs for every Simulator object type. |
| `10-power-flow-solution-and-options-part3.md` | 4 | Power flow solution theory, simulator options, and solution and control settings. |
| `18-general-tools.md` | 4 | Limit monitoring, difference case, scale case, connections tools and other general-purpose tools. |
| `06-object-properties-edit-mode-part2.md` | 2 | Edit-mode property dialogs for every Simulator object type. |
| `52-additional-linked-topics-part2.md` | 2 | Topics reachable from links inside the manual but not listed in the help system's table of contents. |
| `03-cases-files-and-formats.md` | 1 | Opening, creating, closing and saving cases; every supported file format; project files. |
| `05-case-information-displays-by-object-part2.md` | 1 | The per-object case information displays: buses, generators, loads, lines, transformers, shunts, interfaces, ownership and more. |
| `06-object-properties-edit-mode-part3.md` | 1 | Edit-mode property dialogs for every Simulator object type. |
| `07-object-properties-run-mode-and-general-part2.md` | 1 | Run-mode and general property dialogs, object groups, supplemental data and data maintainers. |
| `52-additional-linked-topics-part1.md` | 1 | Topics reachable from links inside the manual but not listed in the help system's table of contents. |

### What bites

- The chapter mixes real solver content with generic application options — Environment, File Management and Message Log Options sit in the same file and are filed elsewhere here.
- Voltage Conditioning is the tool that moves generator setpoints *and* switched shunts to hit bus targets; it is easy to miss because its title names neither.

---

*Subject page over the PowerWorld Simulator help corpus. Describes and routes; reproduces
no manual text. Topic-level detail is in `powerworld-help-index/ROUTING.md`.*

---

*Ported from the research vault. Describes and routes over the PowerWorld Simulator help corpus; reproduces no manual text.*


---

# ==== pw-pv-qv.md ====

---
type: concept
domain: tooling
aliases: [pw-pvqv, pv-curves, qv-curves, voltage-stability-curves]
tags: [powerworld, manual, voltage-stability, pv-curve, qv-curve, reactive]
---

# PowerWorld: PV and QV curves

## Abstract

PV and QV curve analysis — real-power transfer margin and reactive margin at a bus. One chapter, and the most directly reactive-planning-relevant subject in the manual.

**25 topics across 1 chapter file.**

## Connections

**Up:** [pw-manual-map](pw-manual-map.md) · **Corpus:** [powerworld-help-corpus](powerworld-help-corpus.md)

**Across:** [pw-power-flow](pw-power-flow.md) · [pw-injection-groups](pw-injection-groups.md) ·
[ptdf-shift-factor-otdf](ptdf-shift-factor-otdf.md)

## Content

### What it covers

- PV curves: setup, injection-group and interface ramping, quantities to track, limit violations
- QV curves: bus selection, solution options, contingencies sub-tab, results and listing
- Output, plotting and tracked limits for both
- PV/QV refine model

### Where it lives

| Chapter file | Topics | Holds |
|---|--:|---|
| `29-pv-and-qv-curves.md` | 25 | PV curves, QV curves and the PV/QV refine model. |

### What bites

- Many topic titles here are bare dialog-tab names — Setup, Options, Results, Plot, Output — so a title search will not find them. Search by the curve type, or use the index.
- The Contingencies sub-tab is part of QV, not contingency analysis; it decides which outages the margin is computed against.

---

*Subject page over the PowerWorld Simulator help corpus. Describes and routes; reproduces
no manual text. Topic-level detail is in `powerworld-help-index/ROUTING.md`.*

---

*Ported from the research vault. Describes and routes over the PowerWorld Simulator help corpus; reproduces no manual text.*


---

# ==== pw-scripting-automation.md ====

---
type: concept
domain: tooling
aliases: [pw-simauto, pw-aux, auxiliary-files-and-script]
tags: [powerworld, manual, aux, script, simauto, automation]
---

# PowerWorld: AUX files and SimAuto

## Abstract

Driving Simulator from outside: the auxiliary file format, script command execution, and the SimAuto automation server with one topic per function. The chapter to open before writing any PowerWorld automation.

**The SimAuto call mechanics beyond esapp's wrapper are now documented inline** —
[simauto-output-shapes-and-discovery](simauto-output-shapes-and-discovery.md) covers the raw
output envelope, [objectid-identification-traps](objectid-identification-traps.md) covers the
branch-ObjectID field-count trap, and [post-contingency-aux-state-carryover](post-contingency-aux-state-carryover.md)
covers the per-contingency aux/script hooks. Read this page for the chapter map — **99 topics
across 8 chapter files.**

## Connections

**Up:** [pw-manual-map](pw-manual-map.md) · **Corpus:** [powerworld-help-corpus](powerworld-help-corpus.md)

**Across:** [pw-data-model](pw-data-model.md) · [raw-epc-roundtrip-traps](raw-epc-roundtrip-traps.md) ·
[pw-timestep-sim](pw-timestep-sim.md) · [builtin-distributed-computing](builtin-distributed-computing.md)

**Now covered inline:** [simauto-output-shapes-and-discovery](simauto-output-shapes-and-discovery.md) ·
[objectid-identification-traps](objectid-identification-traps.md) ·
[post-contingency-aux-state-carryover](post-contingency-aux-state-carryover.md)

**Research pages that use this:** [esapp](esapp.md) · [powerworld-simauto](powerworld-simauto.md) · [aux-only-powerworld](aux-only-powerworld.md) · [aux-script-catalog](../references/aux-script-commands.md)

## Content

### What it covers

- Auxiliary file export formats — display, power system, complete case, network model
- Object field variable names and the ObjectID field
- Script command execution dialog and quick auxiliary files
- SimAuto setup: installing, connecting, passing and getting data, ExcelApp, ProcessID
- SimAuto functions with sample code: Get/ChangeParameters in all their variants, ListOfDevices, OpenCase, SaveCase, SaveState/LoadState, ProcessAuxFile, RunScriptCommand, WriteAuxFile, TSGetContingencyResults

### Where it lives

| Chapter file | Topics | Holds |
|---|--:|---|
| `34-simauto-functions.md` | 55 | Every SimAuto function, with signature, parameters and examples. |
| `33-simauto-overview-and-setup.md` | 16 | Starting SimAuto, accessing data, properties and object variables. |
| `52-additional-linked-topics-part1.md` | 15 | Topics reachable from links inside the manual but not listed in the help system's table of contents. |
| `09-auxiliary-files-and-script-commands.md` | 8 | Auxiliary file format, script commands, export format descriptions and object field variable names. |
| `03-cases-files-and-formats.md` | 2 | Opening, creating, closing and saving cases; every supported file format; project files. |
| `22-contingency-analysis-options.md` | 1 | The Contingency Analysis dialog: Contingencies tab and the full Options tab. |
| `23-contingency-analysis-running-and-results.md` | 1 | Running contingency analysis, file formats, sensitivity analysis, results and comparing runs. |
| `52-additional-linked-topics-part3.md` | 1 | Topics reachable from links inside the manual but not listed in the help system's table of contents. |

### What bites

- **Field names are not in this manual, and never were in the other one.** The provenance rule and what to verify against are in [aux-only-powerworld](aux-only-powerworld.md); that the WebHelp declines too is recorded in [powerworld-help-corpus](powerworld-help-corpus.md). Do not look for a field catalog here.
- **This is the subject the legacy-duplicate trap actually bites.** Version-9 pages for these same functions sit in the appendix with near-identical titles; the rule is in [powerworld-help-corpus](powerworld-help-corpus.md).
- The core AUX format spec is a bundled PDF, not inline markdown.

---

*Subject page over the PowerWorld Simulator help corpus. Describes and routes; reproduces
no manual text. Topic-level detail is in `powerworld-help-index/ROUTING.md`.*

---

*Ported from the research vault. Describes and routes over the PowerWorld Simulator help corpus; reproduces no manual text.*


---

# ==== pw-timestep-sim.md ====

---
type: concept
domain: tooling
aliases: [pw-timestep, time-step-simulation-manual, pw-tsb]
tags: [powerworld, manual, timestep, schedules, quasi-static]
---

# PowerWorld: Time Step Simulation

## Abstract

Time Step Simulation: the quasi-static tool that solves a case repeatedly across a list of timepoints with scheduled inputs. Two chapter files hold all of it, but the commands that drive it and the batch engine that scales it are elsewhere.

**The input and solve mechanics beyond a plain `.pww` load are now documented inline** —
[timestep-schedules-and-delays](timestep-schedules-and-delays.md) covers Schedules, Schedule
Subscriptions and controller time delays; [timestep-opf-and-storage](timestep-opf-and-storage.md)
covers the OPF/SCOPF solve modes and result-storage opt-ins. Read this page for the chapter map —
**32 topics across 2 chapter files.**

## Connections

**Up:** [pw-manual-map](pw-manual-map.md) · **Corpus:** [powerworld-help-corpus](powerworld-help-corpus.md)

**Across:** [pw-scripting-automation](pw-scripting-automation.md) ·
[builtin-distributed-computing](builtin-distributed-computing.md) ·
[weather-dependent-limits](weather-dependent-limits.md) ·
[scheduled-actions-scripting](scheduled-actions-scripting.md)

**Now covered inline:** [timestep-schedules-and-delays](timestep-schedules-and-delays.md) ·
[timestep-opf-and-storage](timestep-opf-and-storage.md)

**Research pages that use this:** [timestep-simulation](timestep-simulation.md) · [pww-data](pww-data.md)

## Content

### What it covers

- The dialog, its pages and toolbar; timepoint lists and scheduled input data
- Schedules, schedule subscriptions and controller time delays
- Switched-shunt and transformer control options specific to time step
- Results: hourly summary, constraints, binding elements, custom result selection
- Running a timed simulation; storing input data and results

### Where it lives

| Chapter file | Topics | Holds |
|---|--:|---|
| `26-time-step-simulation-part1.md` | 22 | Time step simulation setup, schedules, controller time delays and running the simulation. |
| `26-time-step-simulation-part2.md` | 10 | Time step simulation setup, schedules, controller time delays and running the simulation. |

### What bites

- The tool is only a quarter of the story — the script commands that launch a run are in the auxiliary-file chapter, the programmatic entry point in SimAuto, and unattended batch runs in the Cruncher. Opening only this subject will not get a run automated.
- Controller time delays and the per-device time-step control options are what make results differ from a plain repeated solve.

---

*Subject page over the PowerWorld Simulator help corpus. Describes and routes; reproduces
no manual text. Topic-level detail is in `powerworld-help-index/ROUTING.md`.*

---

*Ported from the research vault. Describes and routes over the PowerWorld Simulator help corpus; reproduces no manual text.*


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

# ==== raw-epc-roundtrip-traps.md ====

---
type: concept
domain: tooling
aliases: [raw-roundtrip, epc-roundtrip, psse-raw-traps, pslf-epc-traps, raw-epc-silent-loss]
tags: [powerworld, raw, epc, pti, pslf, roundtrip, data-loss, gic]
---

# RAW/EPC round-trip traps

## Abstract

Reading or writing a PTI RAW or GE EPC file through PowerWorld is not a lossless transcription —
Simulator reinterprets, discards, or silently converts fields on both the read and the write side,
and none of it raises an error or a warning. A model saved to RAW or EPC and reloaded is not
guaranteed to match the model you started with, even without touching it in between. This matters
most for anyone scripting a save/reload cycle, or comparing a case before and after a round-trip and
trusting the diff to be empty when it isn't.

## Connections

**Up:** [pw-manual-map](pw-manual-map.md) · **Across:** [save-powerworld-case](../methods/save-powerworld-case.md) · [case-to-case-device-transplant](case-to-case-device-transplant.md) · [case-impedance-completeness](case-impedance-completeness.md) ·
[fixednumbus-and-raw-v34](fixednumbus-and-raw-v34.md) (full-topology RAW v34+ layers its own
`FixedNumBus`/`SubNodeNum` numbering scheme on top of the round-trip behavior documented here) ·
[difference-case-tool](difference-case-tool.md) (its tolerance-aware diff is the practical
way to check whether a round-trip actually changed anything, rather than trusting a naive diff)

## Content

### Why this is different from the PWB `SaveCase` trap

[save-powerworld-case](../methods/save-powerworld-case.md) documents a PWB save that reports success
and writes nothing. RAW/EPC is a different failure shape entirely: the file **is** written, and it
**does** reload — but the model it describes has changed underneath you, because RAW and EPC cannot
represent everything Simulator's internal model can. There is no missing-file check that catches
this; the only defense is knowing what each format silently reinterprets.

### On RAW read — values Simulator overwrites or reclassifies, not what the file says

- **Radial-bus voltages are overwritten.** A bus with no shunt/conductance, no online device, and
  reached by exactly one non-transformer branch has its voltage silently replaced by the far-end
  bus's voltage — a convergence aid, not the source value. Never trust a post-load voltage on such a
  bus as data you supplied.
- **Generator participation factors come from PMax MW, not MVA base.** If your source data assumed
  participation tracked MVA capacity, the loaded value won't match.
- **Switched shunt modes 4 and 5 have no Simulator equivalent** and downgrade to a constant-Mvar
  fixed shunt; mode 3 becomes "controlling Mvar output of generation." Both are lossy conversions
  with no warning.
- **Any non-transformer branch with R=0, B=0, and X<0 is auto-flagged as a series capacitor** — this
  matters directly for GIC work, since a series cap blocks DC GIC flow. A branch that only
  *coincidentally* matches those three parameters gets reclassified regardless of intent.
- **Three-winding transformer star-bus voltage/angle can be silently overridden** by Simulator's own
  estimate, if that estimate produces smaller terminal-bus mismatches than the value in the file. A
  re-read of a file you just wrote is not guaranteed bit-identical even without any edits of your own.
- **Bus rating sets are reassigned on read**: Normal ratings land in set A, Contingency ratings in
  set B, regardless of how the source file tagged them.
- **An unexpected trailing field on a Bus/Gen/Load/Line/Transformer record is opportunistically read
  as a memo or label** rather than raising a parse error — malformed-looking data is silently
  absorbed instead of rejected.

### On RAW read — one field that is lost outright

Inline comments on a data line load into the `Memo` field on read, but **that Memo is never written
back out on a RAW save** — a one-way loss. If you depend on preserving those comments across a
round-trip, capture them separately before the first read.

### On RAW write — what gets synthesized or converted away

- **A switched shunt with no defined blocks does not round-trip as-is.** RAW write always emits at
  least one block; if none exists, a single 1-step block sized to the present output is synthesized.
- **Line-drop and reactive-current-compensation control on a generator has no RAW representation.**
  On write, such a generator is silently rewritten to instead regulate its own terminal bus at that
  bus's present voltage — a real control-behavior change for anything that later reads the file.
- **Labels are lost on write unless you opt in.** They can optionally be embedded as
  `/* [label] */` comments; without that, labels do not survive the trip to RAW at all.

### On EPC read — flags and fields with no direct PowerWorld equivalent

- **PSLF's "Baseload Flag" maps into two different Simulator concepts from one source flag**: the
  `Governor Response Limits` field (Normal / Down Only / Fixed) and, depending on an interpretation
  option, Post-Contingency-Prevent-AGC as well.
- **AVR on/off is inferred, not read directly** — PSLF has no explicit AVR flag, so Simulator derives
  it from `Qmax − Qmin` against a default 2.0 Mvar deadband. A unit with a narrow reactive range can
  come in as AVR=NO even if the source model intended AVR on.
- **`aloss` (loss allocation) is rounded onto whichever bus is "From End Metered"** — an
  approximation of PSLF's semantics, not a preserved value.

### On EPC write — modes and units that don't survive

- **Switched shunts on Generator-Mvar or Wind-Mvar control are written as fixed (locked) control.**
  EPC has no representation for those control modes, so exporting freezes them silently.
- **If `GE Ohmic Data Flag`=1, R/X are written in ohms and B in microMhos instead of per-unit** — a
  units trap for any downstream code that assumes per-unit throughout.

### Common to both formats

- **Appending to an existing case overwrites by key**, not merges: a record sharing the same bus
  number completely replaces the existing one. A branch is only appended if **both** its terminal
  buses already exist in the target case — a branch pointing at a not-yet-created bus is silently
  dropped, not deferred until that bus appears.
- **Newly appended buses/branches are flagged "just added"** so the power-flow pre-processing step
  auto-estimates their voltage/angle — appended data does not need to arrive pre-solved to converge.

### Formats that are one-way or lossy by design

- **Areva HDBExport (`.csv`) can only be read, never saved** by Simulator — it's a full-topology
  import for the Integrated Topology Processing add-on, not a general exchange format.
- **UCTE (`.uct`) and IEEE Common Format are input-oriented and lossy.** IEEE CF in particular does
  not support multiple loads or generators at a single bus.

### How to catch the loss instead of discovering it later

There is no single flag that surfaces these. The practical defenses:
1. **Never treat a reloaded RAW/EPC file as identical to what you saved** — diff key fields (voltage,
   participation factors, shunt mode, control mode) explicitly rather than assuming equality.
2. **Snapshot anything format-specific before the round-trip** — memos, labels, line-drop/RCC control
   settings, shunt control modes — and reapply if these matter downstream.
3. **Check series-capacitor reclassification explicitly** before a GIC study on any case that passed
   through RAW: `R=0, B=0, X<0` branches may not be capacitors you intended.
4. For a lossless in-Simulator round-trip, prefer PowerWorld's own AUX export
   ([case-to-case-device-transplant](case-to-case-device-transplant.md)) over RAW/EPC — AUX carries
   Simulator's full field set, not a third-party format's subset.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*


---

# ==== required-fields-for-object-creation.md ====

---
type: concept
domain: tooling
aliases: [required-fields, object-creation-gate, accidental-creation-guard, paste-import-fields]
tags: [powerworld, data-model, key-fields, silent-failure, csv-import]
---

# PowerWorld: required fields for object creation

## Abstract

Key fields identify a row; **required fields** are the separate, smaller set PowerWorld
demands before it will actually create a *new* object from a paste, an aux `INSERT`-style
block, or a CSV import. The gate exists on purpose, as a guard against a row full of key
fields accidentally fabricating an object nobody meant to create. Missing a required field
doesn't error — it skips the creation silently.

## Connections

**Up:** [pw-data-model](pw-data-model.md) · **Across:** [aux-only-powerworld](aux-only-powerworld.md) ·
[objectid-identification-traps](objectid-identification-traps.md) (the write-path counterpart
to this page's read-path gate — that page's malformed ObjectID resolves to the wrong existing
object, this page's missing required field silently skips creating a new one) ·
**Deeper:** [adding-devices-esapp](../methods/adding-devices-esapp.md) · [esapp-schema-reference](../references/esapp-schema-reference.md)

## Content

### Two separate gates, two separate failure modes

Loading a row through paste, aux, or CSV import checks two things in sequence:

1. **Key fields missing** → the row is ignored outright; PowerWorld can't identify any
   object, new or existing, without them. This is the same key-field write-back rule
   already covered for read-modify-write in [esapp-schema-reference](../references/esapp-schema-reference.md)
   and [aux-only-powerworld](aux-only-powerworld.md).
2. **Key fields present, but the object doesn't exist yet, and required fields are
   missing** → PowerWorld treats the row as referring to a record that isn't there, and
   silently declines to create it. Only once every required field also has a value does it
   create the new object.

### Why the gate exists: it's a guard, not a data-quality nicety

The manual's own example makes the intent explicit: an aux file sets `Monitor=YES/NO` on
every branch in a case. If that file also contains a line for a from/to/circuit tuple that
doesn't exist in the target case, no branch gets fabricated from it — because the required
fields (impedance and ratings) were never given, only the monitoring flag. The required-field
gate is what stops a maintenance script that's only supposed to *update* existing objects
from accidentally *creating* new ones when case data has drifted.

### Worked example: Branch

Key fields for a Branch are from-bus, to-bus, and circuit ID. Beyond those, the **required**
fields are R, X, B (impedance) and Ratings A/B/C. Supplying only the keys — even with other
non-required fields set — will not create a new branch; every required field needs a value
first. This matches the field list `adding-devices-esapp` already gives for actually driving
branch creation through `esapp`'s `CreateData`.

### Finding the current required-field set for any type

The required-field set can change between Simulator versions, so there's no static list
worth keeping here. The authoritative, always-current source is the same one already used
for key/enterable fields: `pw.esa.GetFieldList(<type>)` (see [esapp](esapp.md)), or, from
the GUI, Help menu → "Export Object Fields" (text or Excel), which dumps the key/required
table for every object type in the running Simulator version. In case-information column
headers and the Display/Column Options dialog, key fields are highlighted yellow and
required fields green — useful for a human debugging a failed load, not for code.

### A separate paste trap: redundant columns, second one wins

Distinct from required fields: pasting two enterable columns that represent the same
underlying value — bus per-unit voltage and bus kV, for instance — applies them in column
order, and whichever one is positioned second **silently overwrites** the first. There is
no error or warning; the outcome depends purely on column order in the pasted data.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*


---

# ==== scheduled-actions-scripting.md ====

---
type: concept
domain: tooling
aliases: [scheduled-actions, schedule-add-on, apply-scheduled-actions-at, gantt-outages]
tags: [powerworld, scheduling, scripting, topology, outages]
---

# Scheduled Actions scripting

## Abstract

Scheduled Actions is Simulator's paid Gantt-chart add-on for planned-outage topology
changes, and it has four SCRIPT commands that drive it headlessly. The trap: a
Scheduled Action Group can sit in the case, inside its time window, looking ready to
fire — and never apply, because a separate `Status` flag on the group is Inactive. Code
that walks the action list and assumes "in window" means "will run" gets silently wrong
topology. This page covers the apply/revert state mechanic those four commands drive
and the breaker-identification taxonomy they produce, none of which is explained beyond
a one-line name in the existing script references.

## Connections

**Up:** [pw-manual-map](pw-manual-map.md#scheduled-actions) · **Across:**
[aux-script-commands](../references/aux-script-commands.md) ·
[the named-wrapper-over-RunScriptCommand rule](../AGENTS.md) ·
[island-and-breaker-grouping](island-and-breaker-grouping.md) (that page's Breaker Isolated
Groups taxonomy is the per-bus analogue of this page's per-action `Origin` tagging) ·
**Deeper:**
[powerworld-limitset-setdata](../methods/powerworld-limitset-setdata.md) (a different
per-object SetData gotcha, same "silent success" family)

## Content

### What a Scheduled Action is

A Scheduled Action targets one Branch, Shunt, Load, or Generator with an action type —
Open, Close, Open with Breakers, Close with Breakers, or (generators only) Set To /
Changed By a field value. Individual actions belong to a **Scheduled Action Group**,
which owns the Start/End time window shown on the Gantt chart.

### The activation gate: Status is separate from the time window

A group also carries a `Status` (itself a reusable object, Active or Inactive).
**Only Active groups are ever applied** — an Inactive group still renders on the Gantt
chart inside its window but has zero effect on the case. Don't infer "will fire" from
the time window alone; check the group's Status.

### The four script commands and the reference-state cycle

The GUI's "Apply Actions" checkbox snapshots system state the instant it's checked and
restores that exact snapshot the instant it's unchecked. The four SCRIPT actions map
onto that same mechanic:

- `ScheduledActionsSetReference` — captures the state that will be restored before
  applying a given timestamp.
- `ApplyScheduledActionsAt` — applies whatever actions are Active within a filtered time
  window.
- `RevertScheduledActionsAt` — applies the *opposite* of those same actions.
- `IdentifyBreakersForScheduledActions` — expands an Open/Close-Breakers action into
  individual breaker actions (see below).

Driving a sweep of scheduled outages by script means calling these in the right order —
set reference, apply at T, do work, revert at T (or re-set reference before the next T)
— otherwise state accumulates across steps instead of giving a clean per-timestep
snapshot.

Two options change what "within the window" and "reverted" mean:

- **Apply All Within Resolution**: given a Resolution (time-slider step) and the current
  View Time, every action inside `[View Time, View Time + Resolution)` counts as active
  for that step — a coarse resolution can pull in actions nominally scheduled somewhat
  later than the view time.
- **Use Normal Status**: on revert, restores each device's *Normal Status* field instead
  of whatever state the previous action left it in — matters when action groups overlap
  or sit adjacent in the sweep.

### Breaker identification produces a taxonomy, not a boolean

Running "Identify Breakers" on an Open/Close-Breakers action converts it into individual
breaker Open/Close actions, each tagged with an `Origin`:

- `User` — hand-authored.
- `Added` — synthesized to actually achieve the requested topology.
- `Extra` — a device incidentally isolated or connected as a side effect.

**`Extra` actions default to `Allow Active = No`** — they exist for audit visibility and
will not be applied even though they appear in the action list. Code that walks the
action list and applies everything present must check `Allow Active`, not just
presence, or it silently over-applies.

A related gap: Breaker actions typically don't carry their associated Disconnect
switches along. The "Switch Disconnects to Normal Status in Open and Close Breakers
Actions" option exists to patch this — without it, and without the case's disconnects
already at normal status, the resulting topology after a breaker action can be wrong
even though the action reports success.

### Conflicts are opt-in, not automatic

`Check Conflicts` populates a `Conflicts` field when two different Scheduled Actions
target the same device with different actions. This must be run explicitly —
conflicting actions are not rejected at authoring time.

### CROW CSV import is a labeling precondition, not a plug-in path

CROW (Control Room Operations Window) outage schedules can be imported as CSV, but
resolving CROW's device identifiers against PowerWorld objects requires case-specific
labeling conventions set up in advance — not an out-of-the-box import.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*


---

# ==== shunt-transformer-dfacts-control.md ====

---
type: concept
domain: tooling
aliases: [switched-shunt-control, svc-control-mode, transformer-avr, dfacts-control, SVSMO]
tags: [powerworld, manual, power-flow, voltage-control, switched-shunt, transformer, dfacts]
---

# PowerWorld: shunt, transformer and D-FACTS automatic control

## Abstract

How switched shunts, SVCs, transformer AVR/Mvar/phase control, and D-FACTS devices coordinate
and move during a power flow solve — and the several ways each silently disables itself with
only a log message. Read it before scripting anything that expects a shunt or transformer to
respond to a voltage or Mvar target.

## Connections

**Up:** [pw-power-flow](pw-power-flow.md) · **Corpus:** [powerworld-help-corpus](powerworld-help-corpus.md)

**Across:** [buscat-and-voltage-control](buscat-and-voltage-control.md) · [solver-mechanics-and-failure-modes](solver-mechanics-and-failure-modes.md) · [generator-dispatch-and-diagnostics](generator-dispatch-and-diagnostics.md)

## Content

### Switched shunts need four conditions all true, or they silently sit fixed

Automatic control on a switched shunt requires: the shunt's own Control Mode is set, the
area's Auto Shunts flag is true, the case-wide "Disable Switched Shunt Control" box is
unchecked, and the shunt's own Auto Control flag is true. If any one is off, the shunt does
not move and nothing reports why — a classic "why isn't this shunt responding" case for
esapp automation.

### Control groups, and how they can disable themselves

Shunts regulating the same bus (or ZBR-grouped buses — see
[buscat-and-voltage-control](buscat-and-voltage-control.md)) form a control group
automatically. If two separate control groups end up inside the same ZBR group, or the
shunts in one group have mismatched regulation types (Voltage vs Generator Mvar vs Wind
Mvar), PowerWorld disables automatic control for the **whole group**, again with only a log
message.

Within a working group, dispatch order is specific: discrete shunts are exhausted
highest-to-lowest by their `Var Regulation Sharing` value, one at a time, until the group's
need is met or all discrete shunts are used; only the remainder is then proportioned across
continuous shunts by their sharing values.

### Generator Mvar Regulation mode on a shunt is a documented workaround

Setting a switched shunt to Generator Mvar Regulation mode disables generator var-limit
checking in the first inner loop specifically so the shunt's reactive range gets used before
generators clamp at their own Mvar limits — it exists to fix cases that otherwise fail to
solve because generators hit their limits while reactive support was still available
elsewhere.

### SVC control mode and the Xc offset trap

SVC Control Mode (`SVSMO1`/`SVSMO2`/`SVSMO3`) lets one continuous or discrete element control
up to 8 other fixed shunts as a group; `SVSMO3` is unusual in expressing its limits as
per-unit reactive current rather than Mvar. The compensating-reactance parameter `Xc` means
an SVC does **not** hold its nominal regulated-bus voltage — it holds a computed value
`Vcomp = Vbus + Vbus * Bsvc * Xc` instead. Code that expects bus voltage to equal `Vsched`
on an SVC-controlled bus will be wrong whenever `Xc` is nonzero.

Voltage Control Groups (v19+) are a separate coordination mechanism: they process shunts
group-by-group, moving only the single largest kV deviation (not per-unit) one step per pass,
and carry a `FORCEON` status that overrides even the global "disable switched shunt control"
setting — useful when contingency-analysis automation needs a shunt to respond regardless of
global disables.

### Transformer control shares the same enable chain, plus a sensitivity self-disable

LTC-AVR, Reactive-Power-Control, and Phase-Shift-Control are mutually exclusive per
transformer, and each requires the same three-level enable chain as shunts (device flag +
area flag + case-wide flag). Beyond that, a transformer silently self-disables control if its
voltage/Mvar-to-tap sensitivity drops below a configurable threshold — a common real case is
a generator step-up transformer trying to control high-side voltage while its generator is
offline, where sensitivity collapses toward zero and control turns off with no error.

Reactive Power Control on a transformer always regulates flow at the FROM (tapped) side, not
a bus, so `RegBus` is unused in this mode — code that assumes `RegBus` is meaningful for any
"voltage-controlling" transformer needs to check the control-type field first.

### D-FACTS oscillation lockout

D-FACTS devices support four modes: Bypass, Limit, Fixed, Regulate. If a device is caught
oscillating on and off within the solve loop, PowerWorld silently force-switches it to Fixed
mode to stop the oscillation — another case of the solver quietly changing device behavior in
order to converge.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*


---

# ==== simauto-output-shapes-and-discovery.md ====

---
type: concept
domain: tooling
aliases: [simauto-raw-output, flat-output-shape, getspecificfieldlist, field-family-discovery]
tags: [powerworld, simauto, esapp, com, discovery, field-metadata]
---

# SimAuto raw output shapes and field discovery

## Abstract

Below esapp's DataFrame conversion, every `pw.esa.*` SimAuto call returns the same envelope,
and a handful of raw functions never made it into esapp's wrapper set at all. This page
covers that envelope, the "flat" array layout used by three of those functions, and two
field-discovery calls that answer questions `GetFieldList` cannot: how many indexed slots a
repeatable field family has, and how to look up specific fields by name instead of pulling
the whole list. Useful when a raw COM call is unavoidable, or when `is_settable()` and
friends aren't enough to know what a field family actually contains.

## Connections

**Up:** [powerworld-simauto](powerworld-simauto.md) · [esapp-schema-reference](../references/esapp-schema-reference.md) ·
**Across:** [aux-only-powerworld](aux-only-powerworld.md) (field-name provenance rule) ·
[esapp-script-command-wrappers](esapp-script-command-wrappers.md) (the `SaveCase` COM exception this page's FileType table supports) ·
[objectid-identification-traps](objectid-identification-traps.md) (that page's silent-wrong-match
failure mode is exactly the kind of thing worth double-checking with this page's raw field
discovery calls) ·
**Deeper:** Simulator's *SimAuto Functions* manual chapter (Help menu)

## Content

### Every function's Output starts the same way

Whatever a SimAuto call returns, slot 0 of the `Output` variant array is always the error
string, empty on success. This is the shape under every raw `pw.esa.*` call, wrapped by
esapp or not — worth knowing when debugging a raw call by inspecting `Output` directly
rather than through an esapp exception.

### Three ways to discover field metadata — not interchangeable

`GetFieldList(ObjectType)` is esapp's existing authority for `is_settable()`, returning
every field's key designator, legacy `variablename:location` form, data type, description,
and an enterable flag, in a fixed six-column layout. Two more functions answer different
questions:

- `GetSpecificFieldList(ObjectType, FieldList)` looks up only the fields you name, and adds
  the GUI column header alongside the variable name — pass `"ALL"` for every field, or
  `"variablename:ALL"` to expand one repeatable field family (e.g. `CustomInteger:ALL`,
  `PTDFMult:ALL`) into all of its indexed instances.
- `GetSpecificFieldMaxNum(ObjectType, "variablename")` returns the highest location index a
  given field name uses for that object type — the way to learn in code how many
  `CustomInteger`/`CustomString`/`PTDFMult`-style slots exist before iterating them, instead
  of guessing a cutoff.

Neither appears in esapp's mixin table today; only `GetFieldList` does.

### ListOfDevices vs ListOfDevicesAsVariantStrings

`ListOfDevices` is the one SimAuto function that returns strongly-typed values — bus numbers
as Long Integers, IDs as strings — instead of variant-of-string like everything else, a
long-standing quirk PowerWorld can no longer change without breaking existing callers.
`ListOfDevicesAsVariantStrings` is the corrected twin, returning variant-of-string
consistently. This only matters if code inspects `pw.esa.ListOfDevices` output types
directly rather than going through esapp's DataFrame conversion.

### The flat output/input layout

`GetParametersMultipleElementFlatOutput`, `ListOfDevicesFlatOutput`, and the input-side
`ChangeParametersMultipleElementFlatInput` exist for callers without good multi-dimensional
array support. All three share one layout:

```
[errorString, NumberOfObjectsReturned, NumberOfFieldsPerObject,
 Obj1Field1, Obj1Field2, ..., ObjNFieldM]
```

fields for object 1 first, then object 2, and so on. `ChangeParametersMultipleElementFlatInput`
aborts the whole call — loudly, not silently — if `NoOfObjects × len(ParamList) !=
len(ValueList)`, so a ragged flat array fails fast rather than misaligning fields silently.

### Typed column retrieval and its failure mode

`GetParamsRectTyped`/`GetParamsTypedCols` let you request a COM VARENUM type
(`VT_I2`/`VT_I4`/`VT_R4`/`VT_R8`/`VT_BSTR`/`VT_VARIANT`) per column instead of getting
everything back as a string. Requesting a non-scalar-convertible field — a string ID field
as `VT_R8`, say — is a hard error naming the offending field, not a silent NaN or garbage
value. `VT_VARIANT` is the safe fallback: it returns natively-typed values with no
conversion contract to violate.

### SaveCase FileType values

`SaveCase(FileName, FileType, Overwrite)` accepts: `"PTI23"`–`"PTI35"` (raw), `"GE14"`–`"GE23"`
(epc), `"IEEE"`, `"UCTE"`, `"PWB5"`–`"PWB24"` or `"PWB"` (most recent). For aux output
specifically, `"AUXNETWORK"` (network data only) is PowerWorld's recommended type;
`"AUX"`/`"AUXSECOND"`/`"AUXLABEL"` (whole-case, keyed on primary/secondary/label keys
respectively) are kept for backward compatibility. Since the kit already documents COM
`SaveCase` as a silent no-op and routes callers to the script-command `SaveCase(...)`
instead (see [esapp-script-command-wrappers](esapp-script-command-wrappers.md)), this table
is the reference for choosing a non-PWB FileType with that script command.

### RunScriptCommand2's extra signal

`RunScriptCommand2(Statements, out StatusMessage)` returns a Boolean success flag plus an
out-parameter message string that carries informational text even on success — unlike plain
`RunScriptCommand`, whose return value only ever carries an error string. Useful when a
script action's own success message carries information (e.g. a row count) worth capturing
without a separate `LogSave`.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*


---

# ==== solver-mechanics-and-failure-modes.md ====

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


---

# ==== timestep-opf-and-storage.md ====

---
type: concept
domain: tooling
aliases: [timestep-scopf, timestep-results-storage, tsb-file, timestep-solution-types]
tags: [powerworld, timestep, opf, scopf, tsb, results-storage]
---

# Time Step OPF/SCOPF and results storage

## Abstract

Beyond plain power flow, Time Step Simulation can solve each timepoint as an
Unconstrained OPF, OPF, or SCOPF, and the storage of its results is opt-in and
configurable rather than automatic. A run that "succeeds" can still produce an empty
result grid, and the `.tsb` file that saves all of this can be set to auto-load — and
auto-run — the moment a `.pwb` is opened. None of this is reachable from the CSV-export
shape the weather-to-MW pipeline already documents.

## Connections

**Up:** [timestep-workflow](timestep-workflow.md) · [pw-timestep-sim](pw-timestep-sim.md)

**Across:** [timestep-schedules-and-delays](timestep-schedules-and-delays.md) · [copper-plate](copper-plate.md)

**Deeper:** [how-to-analyze-results](../methods/how-to-analyze-results.md) · [time-step-simulation-backend](../references/time-step-simulation-backend.md)

## Content

### Four solution types, settable per timepoint

Each timepoint independently selects a Solution Type — Power Flow, Unconstrained OPF
(economic dispatch), OPF, or SCOPF — and each point's solved state becomes the initial
condition for the next point in the run. OPF and SCOPF require the corresponding
Simulator add-on license. AC or DC solving can also be chosen independently for the
power flow stage, the contingency-analysis stage, and the SCOPF stage; using DC for
contingency analysis specifically is the single biggest speed lever for a slow SCOPF
timestep run.

### Results are opt-in — a run can succeed and store nothing

**Custom Results Selection** must be configured before a run: a field on an object type
is stored only once explicitly marked (selected + `Time Selected = YES`). A run without
this configured completes without error and produces no usable results grid. This is
the same underlying mechanism as the `TimeStepSaveFieldsSet` requirement documented in
[timestep-workflow](timestep-workflow.md), generalized here to any object type, not
just generators — worth restating because it is easy to assume results are captured by
default.

Storage itself has three modes with a real tradeoff:

- **Memory only** — populates the result grids; risks running out of memory on a large
  field set times a long run.
- **CSV only** — avoids the memory pressure entirely, but leaves the result grids
  empty, so a script that checks grid contents after a CSV-only run sees nothing.
- **Both.**

CSV filenames combine a user-set identifier prefix with the result type (e.g.
`<prefix>_Buses.csv`); object IDs in those files can be Primary (number), Secondary
(name), or Label — see [how-to-analyze-results](../methods/how-to-analyze-results.md)
for the export shape the weather pipeline already uses.

### SCOPF-specific results

LMPs (average/std dev/min/max), initial/unconstrained/final cost, and binding
line/interface/contingency constraints with marginal costs are all available, plus a
count of unsolvable contingencies. Binding constraints are reachable through the
Results: Constraints grids or the equivalent SimAuto-queryable fields; a per-constraint
detail view (type, ID, contingency name, marginal cost) is navigable timepoint by
timepoint.

### The `.tsb` file — and its auto-run trap

A `.tsb` (Time Series Binary) file is the complete save/restore unit for a Time Step
Simulation: all input data (both time-point-based and scheduled), simulation options
except "Auto Load TSB" (which lives in the `.pwb` itself), custom-results definitions,
and any already-computed results.

A `.pwb` can be configured to auto-load its default `.tsb` on open, and optionally
auto-run it — something a script or agent opening an unfamiliar case should account
for, since it can kick off a long simulation as a side effect of simply opening the
file. Custom-results *definitions* alone (without data) can be saved and reloaded
separately as a `.tsc` file, letting a results configuration be reused across different
cases or runs.

### Reset Run captures its reference case once

"Reset Run" reverts to a **Reset Reference Case** captured once, when the Time Step
Simulation dialog first opens — it is not re-captured automatically afterward. If the
in-memory case changes while the dialog stays open, a script relying on Reset Run to
return to the *current* case state must explicitly re-arm this reference first, or it
will reset to a stale snapshot from before those changes.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*


---

# ==== timestep-schedules-and-delays.md ====

---
type: concept
domain: weather
aliases: [schedule-subscriptions, controller-time-delays, timestep-actions, tsb-schedules]
tags: [powerworld, timestep, schedules, controller-time-delays, silent-failure]
---

# Time Step schedules and controller time delays

## Abstract

The weather-to-MW workflow only ever feeds Time Step Simulation through one input
channel — a loaded `.pww`. The engine underneath it has two others: per-timepoint data
columns, and reusable **Schedules** attached to a field via a **Schedule Subscription**.
Neither is wrong to ignore for the renewable pipeline, but a case that already has
schedules, controller time delays, or Time Step Actions configured will not behave like
a plain repeated power-flow solve, and nothing in a script's output will say so — a
misread delay or an interrupted run shifts results in time or reverts a device's
behavior without raising an error.

## Connections

**Up:** [timestep-workflow](timestep-workflow.md) · [pw-timestep-sim](pw-timestep-sim.md)

**Across:** [timestep-simulation](timestep-simulation.md) · [pww-data](pww-data.md) ·
[timestep-opf-and-storage](timestep-opf-and-storage.md) (OPF/SCOPF solving is one more
per-timepoint pipeline stage, sequenced right after this page's time-delay/Time Step Action
step) ·
[weather-dependent-limits](weather-dependent-limits.md) (a separate, non-`.pww` mechanism
computing the same kind of weather-driven values this page's `WeatherStation`-adjacent
schedule inputs might otherwise be confused with)

**Deeper:** [timestep-simulation-setup](../methods/timestep-simulation-setup.md) · [time-step-simulation-backend](../references/time-step-simulation-backend.md)

## Content

### The object model: a Timepoint list

A run iterates a **Timepoint list** — up to 100,000 points, timestamped to 1-second
precision, always kept sorted by date/time regardless of insertion order. Each
timepoint carries its own input values and, once solved, its own results. This list is
the thing everything below attaches to, and it exists independently of weather data:
the PWW-loading path used by [timestep-workflow](timestep-workflow.md) is one way to
populate it, not the only way.

### Three separate input channels

- **PWW-loaded weather** — the channel the renewable pipeline uses exclusively.
- **Time-point-based data** — a value entered directly per timepoint (an hourly column
  built by scaling or deriving from another column).
- **Scheduled data** — a `Schedule` (a reusable list of datetime/value pairs — a
  "shape") attached to a specific object's field through a **Schedule Subscription**.
  One schedule can drive many devices via multiple subscriptions, each with its own
  multiplier, shift, and time offset — e.g. one maintenance-outage shape reused across
  several generators with a per-generator delay instead of duplicating the data.

A subscription is **Absolute** (the field takes the schedule's value directly) or
**Relative** (`Actual = Multiplier * ScheduleValue + ValueShift`).

### The default that silently overwrites your data

Schedules can be periodic (repeating every N days/hours/minutes/seconds) and can
interpolate between defined points, or apply only at points that exactly match a
schedule-defined datetime. Which of these is active is controlled by **"Apply Schedule
Points as Events,"** and it is **off by default** — meaning a schedule's value
re-applies at *every* timepoint, including ones between its own definition points, and
will overwrite anything else that changed the same field in between. If a field is
subscribed to a schedule and also being driven by time-point-based data, whichever
applies later in the pipeline wins, silently, with no warning that a value was
clobbered.

### Controller time delays only exist during a complete run

Switched shunts and transformers under automatic control can be configured with time
delays: a device must stay outside its regulation range for a specified duration
(separate First-Move and Next-Move delays, optionally with secondary/wider regulation
bands carrying their own delays) before it is allowed to switch or tap.

**This delay logic only activates during a "complete run"** — one started with Do Run
and allowed to finish without skipping or reordering points. Solving points
individually or out of order (e.g. while stepping through timepoints manually to debug
one) silently reverts these devices to ordinary, non-delayed automatic control for that
solve. There is no error — the case just behaves differently, and a script comparing a
manual single-point solve against a full run's result for the same timepoint can
legitimately disagree.

Normally only one switched shunt per bus may run on automatic control at a time; time
delay simulation relaxes this by iterating — fixing all but one controlled shunt at a
bus per pass, in ascending bus-number order — so a case that has genuinely never seen
more than one auto-controlled shunt per bus is not the case to test this logic against.

### Time Step Actions

Time Step Actions are contingency-action-like operations (open a branch, change
dispatch, move load, etc.) gated on a Model Criteria expression holding true
continuously for a specified delay. Like controller time delays, they are **only
evaluated during a complete run**, and each action fires at most once per run.

### Pipeline order per timepoint

Knowing the order matters for placing a pre/post script command correctly:

1. Pre-script (before or after input application, per option)
2. Apply time-point data and schedule input
3. Solve power flow
4. Check and apply time-delay devices and Time Step Actions, re-solving if anything
   changed
5. OPF/SCOPF, if the run isn't plain power flow — see
   [timestep-opf-and-storage](timestep-opf-and-storage.md)
6. Contingency analysis, if enabled
7. Post-script (before or after storing results, per option)
8. Store results

### Timed vs. Continuous

**Timed Simulation** replays timepoints at a real-time-proportional pace (a Time Scale
setting is seconds of wall-clock time per hour of sim-time) and can drive live oneline
animation. This matters only for interactive/demo use, but explains a "Timed" vs.
"Continuous" toggle a script might encounter already set in an inherited case.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*


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

# ==== topology-consolidation-and-derived-status.md ====

---
type: concept
domain: tooling
aliases: [integrated-topology-processing, itp, superbus-consolidation, derived-status, full-topology-model, primary-bus]
tags: [powerworld, topology, breakers, superbus, derived-status, key-fields, contingency]
---

# Topology consolidation and derived status

## Abstract

A full-topology (node-breaker) case cannot be solved directly — breaker impedances sit orders of magnitude away from real line reactances and wreck the Jacobian. PowerWorld's Integrated Topology Processing (ITP) works around this by silently remapping every device onto a single representative bus per closed-switching group before every solve, then mapping back after. That remap changes which `BusNum` a device reports, on every solve, and `Status` stops meaning "energized." Anything that reads a device's key fields or trusts `Status` in a breaker-modeled case is reading a moving target.

## Connections

**Up:** [pw-manual-map](pw-manual-map.md) · **Across:** [pw-data-model](pw-data-model.md) (key-field write-back rule) · [pw-contingency](pw-contingency.md) (breaker-to-device contingency conversion) · [glossary](glossary.md) ("Super bus") ·
[case-restructuring-tools](case-restructuring-tools.md) (a different, permanent way a case's
topology changes, versus this page's dynamic per-solve remap) ·
[network-cut-and-query-tools](network-cut-and-query-tools.md) (Facility Analysis's connectivity
graph sits one layer below the Superbus/Subnet grouping this page describes) ·
[objectid-identification-traps](objectid-identification-traps.md) (a second, unrelated way an
object's identity silently resolves wrong — there from a malformed ObjectID string, here from
a stale `BusNum` read across a topology change) ·
**Deeper:** [island-and-breaker-grouping](island-and-breaker-grouping.md)

## Content

### The problem consolidation solves

A node-breaker (full-topology) model represents breakers and disconnects as real branches with near-zero impedance. Solved as-is, those branches sit many orders of magnitude away from a transmission line's reactance, which produces an **ill-conditioned Jacobian** — the power flow won't converge, and the failure looks like a generic solver problem rather than a topology setting. ITP avoids this entirely: before each power flow, sensitivity, or contingency solve, it groups buses connected by *currently closed* switching devices into a **Superbus**, temporarily moves every device's connection pointer onto one **Primary Bus** per superbus, solves the reduced network, then de-consolidates results back onto the original devices. Nothing is converted or rewritten in the case file — this happens in memory, every solve, and reverses itself afterward.

A **Subnet** is the static version of the same grouping: buses joined by switching devices regardless of open/closed state. Subnets only change when equipment is physically added or removed. Superbuses are dynamic — they merge and split as breaker status changes, and each superbus belongs to exactly one subnet. Code that assumes bus grouping is stable across a contingency is implicitly assuming subnet structure; if it's actually reading superbus structure, a single breaker flip changes the grouping out from under it.

### What decides the Primary Bus — and what that means for `BusNum`

Primary Bus selection runs an 18-tier priority list: the slack bus wins outright; then multi-terminal DC terminals, generator-regulated bus, switched-shunt-regulated bus, LTC-regulated bus, DC terminal, generator terminal, switched-shunt terminal, load terminal; then a run of branch-type tiers from series-capacitor terminals down to ground-disconnect terminals at the bottom. Ties break on lowest bus number, and a per-bus `Topology\Node Priority` field can override the automatic ranking.

**The consequence that matters for automation:** with ITP consolidation active, a `BusNum` read off a device is not necessarily the bus it is physically wired to — it's whichever bus won the priority contest for that device's current superbus. Superbuses are recomputed at the start of every solve, so the winning bus can change the moment any breaker in the group changes status. A DataFrame of device rows captured before a topology change, then written back after one, is keying against buses that may no longer be the ones a live read would return — the write can silently land on the wrong object, or on nothing, and still report success. This is the same failure mode the kit's key-field rule describes (see [pw-data-model](pw-data-model.md)), except here the *trigger* is a topology change rather than an omitted column: **re-read key fields after any breaker status change or topology-processing event, and never carry a device DataFrame across one.**

### `Status` lies; `Derived Status` is the real answer

In a full-topology model, `Status` on a non-switching device (generator, load, line, transformer) typically just reflects whether the device itself is set `Closed`, independent of whether a path of closed breakers actually connects it to anything energized. The field that answers the real question is **Derived Status**: it traces outward from the device's terminals across closed branches looking for a closed breaker path to a generator (or, since a later version, other energization sources), returning `Closed`, `Open To`, `Open From`, or `Open` (immediately `Open` if `Status` itself is `Open`). `Derived Online` folds the `Online` field into the same traversal.

**The derivation rule itself changed between manual versions 19 and 20** — version 20 treats a discovered load or switched shunt as sufficient for energization in more cases, and excludes breakers that sit strictly in series with switched shunts, generators, or loads from the traversal (so opening a line doesn't accidentally read as tripping a radially-tapped shunt or load's own breaker). Check which version's rule produced a Derived Status value before trusting one computed on an older case export — the same case can yield a different answer depending on which version wrote it.

### What consolidation can and can't eliminate

A branch is only a consolidation candidate if `AllowConsolidation`=YES and its `Branch Device Type` is one of Breaker, Load Break Disconnect, Disconnect, ZBR, or Fuse (Ground Disconnect also qualifies). Even then, it survives un-consolidated if it's an area tie line, touches a multi-terminal DC converter, participates in a Model Condition, Model Expression, post-power-flow action, or transient-stability event, is part of a contingency action not using incremental processing, or is an interface branch not in series with a non-consolidatable device (interfaces instead auto-retarget to whatever device is in series). A switching device wired in direct parallel with a non-switching device — a series-capacitor bypass breaker is the canonical example — is deliberately excluded too, so consolidation never silently deletes the series cap from the effective model.

### Saving a consolidated case as a Planning Case is one-way and lossy

Ordinary Planning Cases — what `esapp`/aux automation normally assumes — use `BusNum` as the sole key with no switching devices at all. Full-Topology Models are structurally different: breakers and disconnects are modeled as real objects. Saving a consolidated full-topology model out as a Planning Case collapses that structure permanently, with choices that change the result: **Open Non-Energized Branches** (treats a line with an unenergized terminal as open), **Convert Shunts to Blocks** (aggregates multiple per-bus shunts, since planning formats generally allow only one), and a choice between discarding contingencies (smallest resulting file) or preserving them (which requires retaining every breaker any contingency touches).

**Run Breaker-to-Device Contingency Conversion before this save.** Skipping it leaves saved contingencies carrying raw breaker-open actions on a case that no longer models those breakers as distinct objects — a case that downstream tooling, and any script expecting device-level contingency actions (`OPEN LINE`, `OPEN GEN`, etc.), generally can't handle. The conversion (Contingency Analysis dialog → Other → Convert to Device Contingencies) is documented further, alongside contingency mechanics generally, in [pw-contingency](pw-contingency.md); some breaker contingencies can't be fully reduced and keep a residual `Breaker` action alongside the converted device action in the same contingency.

### The "Use Consolidation" checkbox, and getting it backward

Checking "Use Consolidation" is correct for a real full-topology case and simply irrelevant on an ordinary planning case with no switching devices. Getting it backward — leaving it unchecked on a genuine full-topology case — forces the solver onto the raw near-zero-impedance branches directly, which is exactly the ill-conditioned-Jacobian failure described above. The failure mode gives no hint that a topology-processing checkbox is the cause; it looks like an ordinary convergence problem.

### Contingency analysis has two consolidation modes with different failure surfaces

**Preserve All Breakers Included in Contingencies** consolidates once up front and reuses that result for every contingency in the run — simpler, but the effective case stays larger, and a run with a high volume of breaker-touching contingencies can itself produce ill-conditioning. **Incremental Topology Processing** instead re-processes only the affected Subnets per contingency, on the order of milliseconds, and is the manual's preferred mode for throughput. The tradeoff that matters for tool selection: **incremental mode cannot be used by anything that needs a fixed-size bus array for linearization** — sensitivity analysis is the example, and ATC automatically falls back to Preserve-Breakers mode for exactly this reason. A script that assumes ITP settings apply uniformly across every analysis tool in a case will hit this silently.

### Primary Bus Mapping is not one crosswalk

The Power Flow solution, Contingency Analysis, and a Saved Consolidated Case can each preserve a different set of breakers, and therefore each produces its own, potentially different, superbus-to-bus mapping. All three are separately viewable and exportable (as an aux file) from the Topology Processing Dialog's Primary Bus Mapping tab. This matters whenever results computed at a primary bus need to be posted back onto the original per-device topology — use the mapping produced by the specific tool that generated the result, not one borrowed from another tool's run.

### "Open with Breakers" has a hard cutoff and a version-dependent exclusion

Used by contingency actions, and separately available standalone via "Open Breakers to Isolate" (no ITP add-on required for the standalone use), this traverses outward from a device's terminals flagging closed breakers to open. It **aborts entirely, doing nothing,** if isolating the device would require passing more than 10 online-generation buses, logging that the device cannot be isolated from online generation — a hard limit, not a warning. It also drops any flagged breaker whose both terminal buses ended up already visited, since opening it would isolate nothing. Since version 20, breakers and disconnects purely in series with switched shunts (and, per a later patch, also generators and loads) are excluded from the switching set, so opening a line doesn't inadvertently trip a radially-tapped shunt's, generator's, or load's own breaker as a side effect.

### A related but separate grouping: ZBRBus

Distinct from Superbus and Subnet, PowerWorld also tracks **ZBRBus groups** — buses joined by branches under a configurable zero-impedance-branch threshold set in Power Flow Solution Advanced Options. These drive the **Find Parallel AC Branches** tool, which flags branch groups running between the same two ZBRBus groups. One real defect pattern it surfaces: parallel transformers with **conflicting From/To tap orientation** — the software allows this, it is essentially never physically real, and it's a strong signal of bad input data, since a transformer's variable tap is always modeled on the FROM side.

### One more bus-grouping concept, not covered here

A later manual version introduces `FixedNumBus`, a fourth user-defined bus-grouping concept alongside Bus/Superbus/Subnet, described as an extension of the Superbus/Subnet mechanism above. It isn't covered by this page — flagged here as the likely next stop after Superbus/Subnet.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*


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

# ==== weather-dependent-limits.md ====

---
type: concept
domain: weather
aliases: [weatherstation, xycurve, native-dynamic-line-rating, weather-mw-limits, update-branch-limits]
tags: [powerworld, weather, ratings, branches, generators, dlr]
---

# Native weather-dependent branch and generator limits

## Abstract

Simulator (Version 23+) has its own in-case mechanism for weather-adjusted branch MVA
limits and generator MW limits — `WeatherStation` objects feeding `XYCurve` lookups,
entirely separate from any external IEEE-738 dynamic-line-rating pipeline and from the
`.pww` timestep workflow. The trap
that motivates this page: the computed limit fields are pure lookups that never write
themselves anywhere — a case can carry stale ratings computed from weather that hasn't
been refreshed in months, report no error, and look exactly like a case with live data.

## Connections

**Up:** [pw-manual-map](pw-manual-map.md#weather-dependent-ratings) · **Across:**
[pww-data](pww-data.md) (a different, time-series representation of the same physical
variables — see below) · [timestep-workflow](timestep-workflow.md) and
[timestep-simulation-setup](../methods/timestep-simulation-setup.md) (the `.pww` →
hourly-MW pipeline this feature does not use) ·
[timestep-schedules-and-delays](timestep-schedules-and-delays.md) (that page's per-timepoint
data channels are a separate, `.pww`-adjacent way weather-like values enter a case — worth
telling apart from this page's single-valued `WeatherStation` lookups) ·
[limit-monitoring-and-scaling](limit-monitoring-and-scaling.md) (this page's computed rating
is only one input to whether that page's four-gate chain ever reports a violation on it) ·
**Deeper:**
[powerworld-limitset-setdata](../methods/powerworld-limitset-setdata.md) (a sibling
"scripted threshold change" mechanic — `LimitSet` sets the pass/fail band a flow is
checked against; this feature computes the numeric rating itself)

## Content

> This kit does not cover weather science — IEEE 738 thermal modeling, conductor
> physics, dynamic-line-rating theory. This page documents what Simulator's native
> feature computes and assumes as a black box, and where it can silently diverge from
> reality. If your workflow runs an external DLR pipeline that computes ratings in
> Python, treat this feature as a **different code path** — the two don't share
> objects, and nothing here implies one feeds the other.

### The two things it computes

- **Branch MVA limits** — `TemperatureLimitNormal`/`TemperatureLimitCTG`, looked up from
  the branch's resolved temperature.
- **Generator MW limits** — `WeatherMWMax`/`WeatherMWMin`, looked up from a
  caller-selected weather variable (temperature, wind, or insolation).

Both work the same way: resolve a weather value for the object, feed it into an
`XYCurve`, get a number.

### WeatherStation holds one observation, not a series

A `WeatherStation` is a named location (`Latitude`/`Longitude`) carrying single-valued,
last-write-wins fields — `TempF`/`C`, `DewPointF`/`C`, `CloudCoverPerc`,
`WindSpeedmph`/`Knots`/`Msec`/`kmph`, `WindDirection` — plus computed fields
(`Humidity`, `WindChillF/C`, `HeatIndexF/C`, solar geometry: `SolarElevation`,
`SolarAzimuth`, `AtmosphericTransmittance`, `InsolationPerc`). It is **not** a
time-series store; driving it through a sequence of hourly values means repeated
writes, not loading a `.pww` file. Don't conflate this with [pww-data](pww-data.md) —
same physical quantities, a completely different, single-valued-in-case
representation.

### XYCurve is a generic lookup, and it can go silently inert

`XYCurve`/`XYCurvePoint` define a one-input/one-output function. An `IntermediateType`
(`AtOrAbove`, `AtOrBelow`, `Closest`, `Interpolate`) controls between-points behavior.
Critically, `Enabled = No` makes any caller **ignore the curve entirely** — a branch
pointed at a disabled curve silently falls back to its static rating, with no error.

An `XYCurveX` object can override the normal "caller supplies X" behavior by pointing
the curve's X input at a specific `WeatherStation` field instead. When several
`XYCurveX` rows feed one curve, the curve's `XType` (`Ignore`/`Max`/`Min`/`EvalMax`/
`EvalMin`) decides whether to take the extreme X value or evaluate at every X and take
the extreme output.

### Assignment falls back three levels, and the last one blends unintuitively

A branch or generator can name a `WeatherStation` directly. If it doesn't, the
**substation's** `WeatherStation` (inherited by attached objects with no override) is
the fallback. If *neither* is set and a branch spans two different substations, values
combine per field with a different rule each:

- Temperature-like fields: **maximum** of the two ends (or whichever end is valid).
- Cloud cover: **average**.
- Wind speed/direction: **vector sum**, magnitude halved, direction from the resultant.

A branch between two substations with different weather can get rated off a blended
value that matches neither endpoint's actual reading — and the blend rule silently
differs by field.

### Multi-curve fields and blank-is-not-zero

`TemperatureLimitNormalName`/`CTGName` (branches) and `WeatherMWMaxName`/`MinName`
(generators) each take a comma-delimited list of `XYCurve` names — e.g. a conductor
limit alongside a separate CT limit. The combining rule differs by field:
`TemperatureLimitNormal`/`CTG` and `WeatherMWMax` take the **minimum** across listed
curves; `WeatherMWMin` takes the **maximum**. `WeatherMWMaxField`/`MinField` pick which
WeatherStation-derived quantity is the X input, so the same mechanism serves
temperature-, wind-, or insolation-dependent generator limits just by changing that
selector.

If a name list is empty, the computed field is **blank — not an error, and not zero**.
That distinction matters for the write step below.

### Nothing updates automatically — an explicit action copies the lookup into a live field

The computed fields are always-live lookups; they are not what the power flow actually
uses. An explicit **Update Branch Limits** / **Update Generator Limits** action (a
dialog button, or the `TemperatureLimitsBranchUpdate(RatingSetPrecedence,
NormalRatingSet, CTGRatingSet)` script command) copies the computed value into one of a
branch's 15 numbered rating sets (`LimitMVAA`...`LimitMVAO`) or into a generator's live
`MWMax`/`MWMin`.

**This is the headline silent-input trap**: a case whose `WeatherStation` temperatures
have drifted since the last update call keeps reporting the old rating, with no
warning, until that action (or the equivalent `SetData` pattern) runs again. A blank
`TemperatureLimitNormal`/`CTG` (no curve assigned) is documented as safe to write
across the whole case with this pattern, because pasting a blank leaves the existing
numeric value untouched — but the same behavior means a *broken* curve assignment
(wrong `WeatherStation` name) degrades to "did nothing," not an error.

### Bulk import: Areva DLR CSV

Tools → Other Tools → Weather → Load Areva DLR (*.csv) builds the whole object graph
from an Areva EMS `hdbexport` extract in one pass: `DYNELE` rows map to branches
(matched by EMS line/substation identifiers — **unmatched rows are silently skipped**,
though a warning is logged), `SEG` rows become paired Normal/CTG `XYCurve` objects,
`RATING` rows become `XYCurvePoint`s (temperature units controlled by a global
Fahrenheit/Celsius setting, since curves store X in Celsius internally), `WST` rows
become `WeatherStation`s, and `SEGWST` rows tie a curve to a station. A `DYNELE` with no
usable `SEG`/`RATING` rows produces no log line at all — an empty or malformed source
extract can silently yield zero weather-dependent limits.

### A related native generator model worth knowing about

`GenMWMaxMinXYCurve` is the most generic of Simulator's native PFW generator models —
just an `XYCurve` keyed on the generator's own resolved temperature. If a project ever
wants a temperature-derated generation limit, this native mechanism already exists and
may be preferable to a bespoke calculation.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*


---
