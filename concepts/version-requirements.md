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
24.2026.7.22** — 13 of 14 feature areas confirmed working. Version matters more than it
looks: field availability and script-action behaviour both shift between releases, and
they shift *silently*.

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
| **`esapp`** | 0.1.3 |
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
