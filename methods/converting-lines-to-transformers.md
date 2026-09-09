---
type: method
domain: tooling
aliases: [line-to-transformer, linexfmr, make-branch-a-transformer, branchdevicetype]
tags: [esapp, powerworld, simauto, branch, transformer, linexfmr, editmode]
---

# Converting a PowerWorld branch from Line to Transformer

## Abstract

How to reclassify existing `Branch` objects as transformers when a case models every branch as a
line even where the two ends sit at different nominal kV. Two gotchas, both live-verified on
Synth8k: **(1)** `BranchDeviceType` is derived and read-only — the real switch is `LineXFMR = "YES"`
plus `XFNominalKV`/`XFNominalKV:1`; **(2)** esapp's bracket writer rejects every `XF*` field as
read-only from its own **static whitelist**, which is wrong — the fields are writable in PowerWorld
EDIT mode, so go around esapp via `pw.esa.ChangeParametersMultipleElement`. With `XFFixedTap = 1.0`
and `LineC = 0`, the conversion is electrically a **no-op** (verified: max |ΔV| = 0.0 pu,
max |ΔMW| = 0.0) — pure reclassification, R+jX untouched.

## Connections

- **Up:** [esapp](../concepts/esapp.md) · esapp package
- **Across:** [adding-devices-esapp](adding-devices-esapp.md) · [save-powerworld-case](save-powerworld-case.md) · [powerworld-limitset-setdata](powerworld-limitset-setdata.md) · [esapp-overview](esapp-overview.md)
- **Deeper:** reactive power planning backend · [esapp-package-backend](../references/esapp-package-backend.md)

## Content

### When you need this

A case where transmission was built branch-by-branch (synthetic-grid pipelines do this) can end up
with every branch typed `Line`, including the step-down connections. Symptom: `pw.transformers()`
returns empty and `BranchDeviceType.value_counts()` is 100% `Line`, yet many branches have
`BusNomVolt != BusNomVolt:1`.

The mismatched-nominal-kV test is the right detector — check the pairs it finds are sane step-downs
before trusting it. On Synth8k the only pairs were 765/345, 345/138, 138/69 (1586 of 13523 branches).

### The two traps

**`BranchDeviceType` is derived.** You cannot set it. It reports `Transformer` once `LineXFMR` is
`YES`. Setting `LineXFMR` alone is the switch; the `XF*` fields are the transformer's parameters.

**esapp's read-only list is a static whitelist, not PowerWorld truth.** This fails:

```python
pw[Branch] = df   # ValueError: Cannot set read-only field(s) on Branch:
                  # ['LineXFMR', 'XFAuto', 'XFNominalKV', 'XFNominalKV:1', 'XFFixedTap',
                  #  'XFMVABase', 'XFTapMin', 'XFTapMax', 'XFStep', 'XFTapDegree',
                  #  'XFRegMin', 'XFRegMax', 'XFRegBus', 'XFUseLineZ', 'XFPhaseType']
```

`indexable._bulk_update_from_df` validates against `gtype.is_settable(c)` **before** any COM call, so
esapp never even asks PowerWorld. The fields write fine in EDIT mode via raw SimAuto.

### The recipe

```python
pw.edit_mode()                     # required — these are EDIT-mode fields
pw.esa.ChangeParametersMultipleElement("Branch", fields, values)
pw.esa.EnterMode("RUN")
```

with `fields` (keys first, as always):

```python
["BusNum", "BusNum:1", "LineCircuit",      # keys — omit and it silently no-ops
 "LineXFMR", "XFAuto",                     # "YES", "NO"
 "XFNominalKV", "XFNominalKV:1",           # = each end's BusNomVolt
 "XFTapPos", "XFFixedTap", "XFMVABase",    # 0.0, 1.0, 100.0
 "XFTapMin", "XFTapMax", "XFStep",         # 0.51, 1.5, 0.00625
 "XFTapDegree", "XFRegMin", "XFRegMax"]    # 0.0, 0.51, 1.5
```

`LineCircuit` must be a **string** (`"1"`, not `1`). `XFConfiguration` is derived — it self-populates
to `Unknown`; don't try to set it.

### House defaults (from Synth2k_series2)

Worth knowing these are not invented: all 1351 transformers in
`Synth2k_series2_case1` share **identical** settings, so this is the series' convention:

| Field | Value | Meaning |
|---|---|---|
| `LineXFMR` | `YES` | the actual type switch |
| `XFAuto` | `NO` | not an autotransformer |
| `XFNominalKV` / `:1` | each end's `BusNomVolt` | |
| `XFFixedTap` | `1.0` | **fixed tap** — no LTC control |
| `XFTapPos` | `0.0` | |
| `XFMVABase` | `100.0` | matches system base |
| `XFTapMin` / `XFTapMax` / `XFStep` | `0.51` / `1.5` / `0.00625` | 160 steps |
| `XFRegMin` / `XFRegMax` | `0.51` / `1.5` | regulation range |
| `XFTapDegree`, `XFUseLineZ`, `XFPhaseType`, `XFRegBus` | `0` | not a phase shifter |
| `LineC` | `0.0` | transformers carry no line charging |

`XFAuto=NO` + `XFTapPos=0` + `XFFixedTap=1.0` means **fixed-tap, non-regulating**. If a study needs
these regulating voltage (e.g. reactive power planning), that is a separate setup — regulated bus
and setpoint scheme — not covered here.

### Verify it was a no-op

The whole point of copying `XFFixedTap = 1.0` is that the power flow should not move. Solve before
and after and assert it:

```python
pw.pflow(); before = pw[Branch, "LineMW"]["LineMW"]; vb = pw.voltage(complex=False)[0]
# ...convert...
pw.pflow(); after = pw[Branch, "LineMW"]["LineMW"]; va = pw.voltage(complex=False)[0]
assert (va - vb).abs().max() == 0.0 and (after - before).abs().max() == 0.0
```

This holds **only if** the converted branches already had `LineC == 0`. Check that first — a branch
with real line charging will move when reclassified, because a transformer's `LineC` is magnetizing
susceptance, not π-model charging. Zeroing nonzero charging is a modelling decision, not a cleanup;
surface it rather than doing it silently.

Then save via the aux script command, never the COM function — see [save-powerworld-case](save-powerworld-case.md):

```python
pw.esa.RunScriptCommand(f'SaveCase("{out}", PWB);')
assert os.path.exists(out)
```

Reopen the saved file and re-check `BranchDeviceType.value_counts()`; EDIT-mode writes that look fine
in-session are worth confirming survived the round-trip.

### Worked application

an 8,000-bus working model (reactive power planning inputs):
13523 branches, all typed `Line`, 1586 with mismatched nominal kV and all with `LineC = 0`.
Converted to 1586 transformers with the table above; power flow bit-identical; written to
`..._xfmr.pwb` (a new file — the source WIP case was left untouched).
