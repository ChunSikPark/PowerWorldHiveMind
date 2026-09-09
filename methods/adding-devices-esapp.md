---
type: method
domain: tooling
aliases: [add-devices, create-devices, createdata, add-buses-branches]
tags: [esapp, powerworld, createdata, device-creation, dcopf, contingency, n-1]
---

# Adding devices to a PowerWorld case via esapp

## Abstract

How to programmatically create buses, branches (lines/transformers) and set loads in an open
PowerWorld case with `esapp`, then solve a DC OPF and screen N-1 — the write-side mechanics the
read-focused [esapp-overview](esapp-overview.md) doesn't cover. Read this before writing any transmission-expansion /
what-if code. The headline gotcha: `CreateData` **silently no-ops** unless every primary + secondary
+ required key field is supplied, and PowerWorld truncates `LineCircuit` to **2 characters**. All
symbols below were live-verified against the installed package (not guessed).

## Connections

- **Up:** [esapp](../concepts/esapp.md) · esa pp llm
- **Across:** [esapp-overview](esapp-overview.md) · [esapp-schema-reference](../references/esapp-schema-reference.md) · [powerworld-simauto](../concepts/powerworld-simauto.md)
- **Deeper:** esa pp llm backend

## Content

### The write path: `pw.esa.CreateData` (not the bracket writer)

The bracket writer `pw[GType] = df` rejects read-only key/status fields, so for creating objects use
the SAW script command `CreateData` on `pw.esa`. Wrap creation in EDIT mode:

```python
pw.edit_mode()
pw.esa.CreateData("Bus", ["BusNum", "BusName", "BusNomVolt", "AreaNum", "ZoneNum"],
                  [9100, "NEW500", 500.0, 1, 1])
pw.run_mode()
```

**The #1 gotcha — silent no-op on missing key fields.** `CreateData` writes nothing (no error, no
change) unless EVERY *primary + secondary + required* field for that object type is present. For a
**Branch** that means all of:

- primary: `BusNum`, `BusNum:1`, `LineCircuit`
- secondary/composite: `BusName_NomVolt`, `BusName_NomVolt:1` (the "name_nomvolt" bus identifiers)
- required: `LineR`, `LineX`, `LineAMVA`, **`LineAMVA:1`, `LineAMVA:2`** — all THREE MVA limits, even
  if the study only uses the A limit. Supplying only `LineAMVA` silently skips the branch.

```python
# build the BusName_NomVolt map AFTER creating any new buses so both ends resolve
nv = {int(x["BusNum"]): x["BusName_NomVolt"] for _, x in pw[Bus, ["BusName_NomVolt"]].iterrows()}
pw.esa.CreateData(
    "Branch",
    ["BusNum", "BusName_NomVolt", "BusNum:1", "BusName_NomVolt:1", "LineCircuit",
     "LineR", "LineX", "LineAMVA", "LineAMVA:1", "LineAMVA:2", "LineStatus"],
    [frm, nv[frm], to, nv[to], "N1", 0.0, x_pu, mva, mva, mva, "Closed"])
```

Check `GType.keys()` / `.secondary()` / `.identifiers()` (classmethods, call with `()`) to see the
full required set for any type — see [esapp-schema-reference](../references/esapp-schema-reference.md).

**Always verify the count went up.** Because failures are silent, assert `pw.n_bus` / `pw.n_branch`
increased by the expected amount after creation and raise otherwise — never solve a partially-applied
design:

```python
n0 = int(pw.n_branch)
# ... create branches ...
assert int(pw.n_branch) - n0 == n_expected, "CreateData silently skipped devices — check key fields"
```

### Parallel-circuit IDs: any distinct short string (mind the 2-char cap)

Parallel circuits between the same bus pair just need **distinct** `LineCircuit` IDs — any short
string works: `1`, `2`, `11`, `22`, `33`. The only trap is PowerWorld's ~2-char cap: a 3-char ID gets
truncated, so distinct-*looking* IDs can collide — `NE1` and `NE2` both become `NE`, and the second
silently no-ops. Keep circuit IDs ≤ 2 chars and distinct per pair.

> The `esa_pp_llm` pipeline tagged its new circuits with an `N` prefix (`N1`, `N2`) **only** so its
> own code could detect which devices were new — that prefix is a project convention, not a
> PowerWorld requirement.

### Setting a load: write `LoadSMW`

`LoadSMW` is the scheduled ("pure") load value — the constant-power setpoint you specify. `LoadMW` is
the load's actual MW **when it is connected / in service**. So to place or change a load, write
`LoadSMW`; read `LoadMW` for the connected value.

```python
pw.esa.CreateData("Load", ["BusNum", "LoadID", "LoadSMW", "LoadSMVR", "LoadStatus"],
                  [bus, "1", 1000.0, 0.0, "Closed"])
```

### Creating a switched shunt: the bracket writer DOES work, and three fields are traps

Measured 2026-09-07 on Synth9k (10,476 buses, 1,187 existing shunts), adding 11 capacitor banks.

**`ChangeParametersMultipleElement` cannot create a shunt** - it answers `Object not found` for
every row, because it only modifies objects that already exist. Creation goes through the bracket
writer, which despite this page's general advice above *does* work for `Shunt`:

```python
from esapp.components import Shunt
pw.edit_mode()
pw[Shunt] = df          # one row per new bank
pw.run_mode()
assert len(pw.esa.GetParametersMultipleElement("Shunt", ["BusNum","ShuntID"])) - n0 == n_expected
```

**`SSMinMVR` and `SSMaxMVR` are NOT writable.** They are *derived* from the blocks - pass them and
the bracket writer raises `Cannot set read-only field(s)`. Size the bank through the block instead
and read the limits back afterwards.

**The block spelling is `SSBlockMVarPerStep` - capital V, and block 0 carries NO `:0` suffix**
(`:1` through `:9` are blocks 1-9). Same for `SSBlockNumSteps`. This is settled by esapp's own
`Shunt.settable()`, not inferred: `SSBlockMvarPerStep:0` is tolerated on the READ side, which is
exactly what makes the wrong spelling survive - PowerWorld accepts an unrecognised field silently,
so a misspelled block name leaves a shunt with capacity and no block definition and no error.

A complete, working continuous capacitor bank regulating its own bus:

```python
{"BusNum": n, "ShuntID": "1", "BusName_NomVolt": name_nomvolt[n],
 "SSStatus": "Closed", "SSCMode": "Continuous", "AutoControl": "YES",
 "SSRegulates": "Volt", "SSRegNum": n,          # SSRegNum, not SSRegBusNum
 "SSVLow": 0.96, "SSVHigh": 1.06,               # SSVLow < SSVHigh is mandatory
 "SSBlockMVarPerStep": mvar, "SSBlockNumSteps": 1,
 "SSNMVR": mvar,                                # seed to dispatch, NEVER 0
 "AreaNum": area, "ZoneNum": zone}
```

`SSNMVR` seeded at 0 can diverge a stressed case by yanking reactive sources to zero as the
solver's initial guess - see remediating base case violations.

**Sizing: let PowerWorld measure it, do not estimate.** Install a deliberately oversized continuous
bank, solve, and read back `SSNMVR` - the dispatched value IS the requirement. Then reinstall at
that value (rounded up to a standard bank size) and confirm nothing rails at its own cap, which
would mean the requirement was truncated by the probe. Required MVAr does not track depth of
violation: on Synth9k a bus needing +0.0335 pu took 10 MVAr while one needing +0.0277 took 50,
because the difference is system strength at the bus, not how far it had sagged.

**Regulation is a deadband, not a target.** With `[SSVLow, SSVHigh] = [0.96, 1.06]`, a bank that
lands the bus anywhere inside that band has no reason to back off, so the final dispatch depends on
where the solve started. If you need provably-minimal dispatch, tighten the band - do not shrink
the bank.

### Transformer vs line: you MUST flag it — kV mismatch is not enough

A branch whose two ends sit at different nominal kV is *physically* a transformer, but PowerWorld will
**not** infer that. `BranchDeviceType` is **read-only** ("determined by other settings"), so a plain
`CreateData` with only line fields lands the device as a `Line` even across a 500→230 kV step — the
exact bug that put 500/230 transformers into a case as lines. Flag it explicitly with `LineXfmr="YES"`
plus the transformer nominal fields:

```python
fields = [..., "LineStatus"]                       # the usual line fields
values = [..., "Closed"]
if from_kv != to_kv:                               # or a design "Xfrmr"/"DeviceType" flag
    fields += ["LineXfmr", "XFNominalKV", "XFNominalKV:1", "XFMVABase", "LineTap"]
    values += ["YES", from_kv, to_kv, mva, 1.0]    # XFNominalKV per side; tap ratio 1.0
pw.esa.CreateData("Branch", fields, values)
```

After creation, verify: `pw[Branch, ["BranchDeviceType"]]` should read `Transformer` (not `Line`) for
those rows. `LineXfmr="YES"` alone flips `BranchDeviceType`; `XFNominalKV(:1)`, `XFMVABase`, and
`LineTap=1.0` give it a well-defined turns ratio so the DC OPF solves unchanged. Live-verified on
Synth2k: agent design → 10 lines + 10 transformers; expert → 13 + 12.

### Substations

Substations have **no key fields** and are **not needed for DC power flow** — don't create them for a
DC study. Their lat/lon is only useful for right-of-way / distance (cost) calculations.

### Solving a DC OPF and reading the objective

```python
pw.dc_mode = True          # DC approximation
pw.run_mode()
pw.esa.SolvePrimalLP()     # the LP OPF; with dc_mode this is the DC OPF
tfc = float(pw[OPFSolutionSummary, :]["LPOPFCostFunction"].iloc[0])   # "Total Final Cost"
```

`OPFSolutionSummary.LPOPFCostFunction` is the OPF objective ("Total Final Cost").

### Overloads: tolerate the binding-at-limit edge

`pw.overloads(threshold=100.0)` returns branches at/over `threshold` percent. The LP OPF **binds lines
to exactly 100.000% of rating** at the economic optimum, and solver float noise then reads
~100.000001% — a fully-loaded (not overloaded) line. Use a small tolerance so a binding constraint
isn't misreported as a violation:

```python
overloaded = pw.overloads(threshold=100.1)   # >100.1% = a real overload; <=100.1% = at-limit
```

### N-1 on new devices — just run the contingency analysis (don't hand-roll it)

PowerWorld's built-in **contingency analysis** applies each outare-solves, records
violations/non-convergence, and **restores the base case automatge, ically** — you never open or re-close
anything yourself. Run it in DC mode by setting `DCApprox=YES` and the CTG method to `DC`. Verified
call sequence (from `esa_pp_llm/Functions/contingency.py`):

```python
# DC contingency analysis
pw.esa.SetData("Sim_Solution_Options", ["DCApprox"], ["YES"])          # DC power flow
pw.esa.SetData("CTG_Options", ["CTG_CalculationMethod"], ["DC"])
pw.esa.SolvePowerFlow()
pw.esa.CTGClearAllResults()
pw.esa.CTGSolveAll()                                                    # solves all defined contingencies

# read results (per-contingency solve/violation flags + branch loading)
ctg    = pw[Contingency, [Contingency.CTGSolved, Contingency.CTGViol]]   # CTGSolved=="YES", CTGViol>0
branch = pw[Branch, [Branch.CTGViol, Branch.LineMaxPercentContingency, Branch.CTGSolved]]
n_diverged  = int((ctg["CTGSolved"] != "YES").sum())
n_violating = int((ctg["CTGViol"] > 0).sum())
```

The contingencies themselves must exist in the case first — define one per new device (open that
line/transformer), e.g. via `ContingencyBuilder`/`SimAction` (`esapp.utils`) or by auto-inserting
N-1 branch contingencies. `CTGViol`/`CTGSolved` on the `Contingency` object give per-contingency
violation counts and convergence; `Branch.LineMaxPercentContingency` gives the worst loading seen.

The `esa_pp_llm` bench wraps all of this as **`run_contingency(pw, method="DC", ...)`** →
`solve_contingency` (the `SetData`/`CTGSolveAll` above) + `get_contingency_results` (the result
frames) + an optional summary. For AC, pass `method="AC"` (`DCApprox=NO`). Deeper:
**esa pp llm backend** · **reactive power planning backend**. A manual snapshot→open→re-solve
loop is unnecessary — it just re-implements, worse, what `CTGSolveAll` already does.

### Recovering the devices a case already added (diff a modified vs base case)

To reverse-engineer what a solved/modified case added over its base, diff the branch-key sets:

```python
def branch_keys(pw):
    df = pw[Branch, ["BusNum", "BusNum:1", "LineCircuit"]]
    return {(int(r["BusNum"]), int(r["BusNum:1"]), str(r["LineCircuit"])) for _, r in df.iterrows()}

added_branches = branch_keys(modified_pw) - branch_keys(base_pw)   # (f, t, ckt) tuples
added_buses    = set(bus_kv(modified_pw)) - set(bus_kv(base_pw))
```

A branch whose two endpoint buses have different nominal kV is a transformer; equal kV is a line.

> House rules honored: drive SimAuto via `esapp` (not raw `esa`); always keep an object's key
> field(s) on any write or it silently no-ops (see [esapp](../concepts/esapp.md)).
