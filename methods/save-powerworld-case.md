---
type: method
domain: tooling
aliases: [save-case, savecase, save-pwb, write-case, export-pwb]
tags: [esapp, powerworld, simauto, savecase, runscriptcommand, pwb]
---

# Saving a PowerWorld case (.pwb) from esapp

## Abstract

How to write an open PowerWorld case back to disk as a `.pwb` so it can be reopened and inspected in
the GUI. The headline gotcha: **do NOT use the SimAuto `SaveCase` COM function** (`pw.esa.SaveCase(...)`)
— on our setup it returns success (`('',)`, no error raised) yet **silently writes no file**. Use the
PowerWorld aux **script** command `SaveCase` via `RunScriptCommand` instead, which actually writes.
The second trap: the aux `SaveCase` takes **exactly two parameters** `(FileName, FileType)` — adding a
third overwrite/`YES` arg raises `Invalid number of parameters`. All behavior below was live-verified
against the installed package.

## Connections

- **Up:** [esapp](../concepts/esapp.md) · esa pp llm
- **Across:** [adding-devices-esapp](adding-devices-esapp.md) · [esapp-overview](esapp-overview.md) · [powerworld-simauto](../concepts/powerworld-simauto.md) · [powerworld-limitset-setdata](powerworld-limitset-setdata.md) · [converting-lines-to-transformers](converting-lines-to-transformers.md)
- **Deeper:** [esapp-package-backend](../references/esapp-package-backend.md)

## Content

### The one-liner that works

```python
import os
out = os.path.abspath(r"D:\path\to\Outputs\case_out.pwb")
os.makedirs(os.path.dirname(out), exist_ok=True)
pw.esa.RunScriptCommand(f'SaveCase("{out}", PWB);')   # 2 args only; overwrites by default
assert os.path.exists(out), "SaveCase reported success but wrote nothing"
```

- `FileType` is the bare keyword `PWB` (unquoted also works; `"PWB"` is accepted too). This saves the
  current binary format for the running Simulator version.
- The command **overwrites** an existing file silently — there is no separate overwrite flag.
- Use an **absolute** path (`os.path.abspath`). The SimAuto server is a separate process; a relative
  path resolves against *its* working directory — the PowerWorld **install folder** — not your
  script's. Symptom when you forget: `RunScriptCommand: Exception: Access is denied` (PowerWorld can't
  write into its own program dir). A relative-path arg from a README example or CLI is the usual cause;
  `abspath` the output path inside any save wrapper so a caller can pass a relative path safely.

### Why not `pw.esa.SaveCase(...)` (the COM function)

esapp exposes a COM wrapper `SaveCase(FileName, FileType="PWB", Overwrite=True)` in
`saw/case_actions.py`. It looks right and raises nothing, but on this machine it is a **silent no-op**:

```python
pw.esa.SaveCase(out, "PWB", True)     # returns None, no exception
pw.esa._pwcom.SaveCase(out, "PWB", True)  # raw COM returns ('',) == "success"
os.path.exists(out)                    # -> False.  No file. No error.
```

Because `_com_call` only raises when SimAuto returns a non-empty error string, a "success" that writes
nothing sails straight through. **Always `assert os.path.exists(out)` after any save** — a save that
"worked" but produced no file is the failure mode to guard against, mirroring the silent-no-op
discipline in [adding-devices-esapp](adding-devices-esapp.md).

### The 2-parameter rule (the other silent trap)

The aux script command signature is `SaveCase(FileName, FileType);`. Live-probed on the Synth2k case:

| Statement | Result |
|---|---|
| `SaveCase("out.pwb", PWB);` | ✅ file written |
| `SaveCase("out.pwb", "PWB");` | ✅ file written |
| `SaveCase("out.pwb", PWB, YES);` | ❌ `RunScriptCommand: Error in script action validation: Invalid number of parameters.` |

So the aux command does not take an overwrite argument — it always overwrites. (This differs from the
COM function's 3-arg `(FileName, FileType, Overwrite)` shape, which is another reason the two are easy
to confuse.)

### Typical use: save a solved design so a human can open it

Open the base case, apply a design, solve, then save — the pattern used by
`esa_pp_llm/Functions/save_cases.py` to emit inspectable cases for the agent-vs-expert demo:

```python
pw = tep.open_case(scenario_path)
try:
    tep.set_target_loads(pw)
    tep.apply_design(pw, design)     # CreateData buses/branches/loads — see methods/adding-devices-esapp.md
    tep.solve_dcopf(pw)
    out = os.path.abspath(r"D:\...\Outputs\Synth2k_scenarioA.pwb")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    pw.esa.RunScriptCommand(f'SaveCase("{out}", PWB);')
    assert os.path.exists(out)
finally:
    pw.close()
```

Saving before `pw.close()` captures the in-memory edits (new devices + solved state); the reopened
`.pwb` shows exactly what the pipeline built.

> House rules honored: drive SimAuto via `esapp` `RunScriptCommand` (not raw `esa`, not the flaky COM
> `SaveCase`); verify the artifact exists before claiming success (see [esapp](../concepts/esapp.md)).
