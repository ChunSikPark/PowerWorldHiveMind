---
type: method
domain: cross-cutting
aliases: [timestep-setup, ts-setup, timestep-simulation-howto]
tags: [powerworld, simauto, timestep, simulation, weather, renewables, pww]
---

# Method: Writing a timestep simulation

## Abstract

How to drive PowerWorld's TimeStep simulation — turning `.pww` weather files into hourly solar/wind generation CSVs. Covers the prerequisites a case must satisfy per renewable generator (`GenFuelType` WND/SUN, valid Lat/Lon, ISO in `CustomString:2`, a `TSPFWModelString` PFW model), the one-time ISO insertion step, and the `_simulation_worker` function sequence. This is Step 2 of the flagship trail; for the PWW weather files see [pww-data](../concepts/pww-data.md).

> 🔧 **Writing the backend code?** → **[time-step-simulation-backend](../references/time-step-simulation-backend.md)** has the full `_simulation_worker` call sequence, the required `TIMESTEPSaveSelectedModifyStart/Finish` wrapper, the `_GEN_PARAM` field list, and the key-field rule. That page is the *rebuild-the-code* reference; this page is the *write-it* guide.

## Connections

- **Up:** [Home](../index.md) · time step simulation
- **Deeper (backend code):** [time-step-simulation-backend](../references/time-step-simulation-backend.md) — exact call sequence, field lists, gotchas (read this for the backend, not just running it)
- **Across:** [timestep-simulation](../concepts/timestep-simulation.md) · pfw copperplate · [esapp](../concepts/esapp.md) · flagship step 2 — prev: [esapp-overview](esapp-overview.md) · next: [pww-data](../concepts/pww-data.md) · final: [how-to-analyze-results](how-to-analyze-results.md)

## Content

**Step 2 of the flagship trail.** ← prev: [esapp-overview](esapp-overview.md) · next: [pww-data](../concepts/pww-data.md).
Owning project: time step simulation. The concept behind it: [timestep-simulation](../concepts/timestep-simulation.md).

This is the how-to for **writing** a PowerWorld TimeStep simulation — code that drives PowerWorld through SimAuto to turn weather files (`.pww`) into hourly solar/wind generation CSVs. It is *not* a transient-stability study.

> **Library note — prefer `esapp` over `esa`.** Older repos import the standalone `esa` (Easy SimAuto) package. `esapp` (ESA++) is the updated, better-documented version of the same thing — write esapp. Every `RunScriptCommand` / `TimeStep*` script command is identical via `pw.esa.RunScriptCommand(...)`, and the bracket interface (`pw[Type, fields]`, `pw[Type] = df`) replaces esa's `GetParametersMultipleElement` / `change_parameters_multiple_element_df`. See [esapp-overview](esapp-overview.md). (Library choice only — unrelated to the TimeStep-vs-Transient-Stability distinction.)

## 0. Prerequisites

The case must already have, on each renewable generator: a `GenFuelType` of `WND`
or `SUN`, valid `Latitude`/`Longitude`, an ISO assigned in `CustomString:2`, and a
PFW model string (`TSPFWModelString`). The ISO is filled in by the one-time
case-prep step below.

## 1. (One time) Insert ISO regions into the case

`PFW_Insertion/ISO_Insertion_code_shape_file.ipynb` does a geopandas spatial join
of every generator's lat/long against ISO-region shapefiles (nearest-neighbor for
units outside any boundary) and writes the ISO assignment back into the case. This
populates the ISO that later appears as the first metadata header row. Run it once
per case; skip it if the case already has ISO assignments.

> **Resolved:** `PFW_Insertion` (`ISO_Insertion_code_shape_file.ipynb`) writes
> **only `CustomString:2`** (the ISO region via geopandas spatial join). It does
> **not** touch `TSPFWModelString`. PFW model strings are assumed already present in
> the case — they are assigned by pfw copperplate as a separate one-time step
> before this pipeline is run.

## 2. What your code does (`_simulation_worker`)

`_simulation_worker(case, pww_list, result_csv)` is the core function to implement:
1. Copies the case to a temp `.pwb`, opens it with `PowerWorld(tmp_case)` from esapp.
2. Pulls generator metadata (`GetParametersMultipleElement('gen', ...)` / `pw[Gen, fields]`).
3. Loads weather: `TimeStepLoadPWW("...","Weather Only")` then
   `TimeStepAppendPWW(...)` for any additional files.
4. Selects renewables (`GenFuelType` contains `WND|SUN`) and marks them
   `TimeDomainSelected`.
5. Picks the saved fields:
   `TimeStepSaveFieldsSet(GEN, [BGGenMWFuelTypeGeneric:10, BGGenMWFuelTypeGeneric:12], SELECTED)`.
6. Runs `TimeStepDoRun()` and exports via `TimeStepSaveResultsByTypeCSV(gen, ...)`.

> The simulation is **generator-level** by construction — `TimeStepSaveFieldsSet`
> targets `GEN`. Area/substation-level output is a noted future extension.

## 3. Inputs and outputs

- **In:** one case + one or more `.pww` weather files ([pww-data](../concepts/pww-data.md)).
- **Out:** per run, two CSVs (solar + wind). Historical quarter files grouped by
  year are named `Historical_{year}_solar.csv` / `_wind.csv`; a forecast file is
  named after its stem. Resume-safe: a run is skipped if both its CSVs already
  exist (delete them to re-run).

## Next

- Get the weather inputs → [pww-data](../concepts/pww-data.md)
- Analyze the CSVs → [how-to-analyze-results](how-to-analyze-results.md)
