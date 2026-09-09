---
type: method
domain: cross-cutting
aliases: [analyze-results, results-analysis, post-processing]
tags: [powerworld, analysis, post-processing, csv, solar, wind, renewables]
---

# Method: Writing code to analyze timestep-simulation results

## Abstract

How to write code that reads and analyzes the solar/wind generation CSVs produced by the timestep simulation. Covers the two-CSV-per-run naming convention, the 8-row metadata header layout (ISO, fuel type, PFW model string, max MW, state, utility, lat, lon), UTC timestamp conversion from PowerWorld's CST Excel-serial format, and typical pandas reductions for fleet profiles, capacity factors, and regional totals. This is Step 4 of the flagship trail; to plot the results see [visualize-renewable-output](visualize-renewable-output.md).

## Connections

- **Up:** [Home](../index.md) · time step simulation
- **Across:** flagship step 4 — prev: [pww-data](../concepts/pww-data.md) · next: [visualize-renewable-output](visualize-renewable-output.md) · start: [esapp-overview](esapp-overview.md) · [timestep-simulation-setup](timestep-simulation-setup.md)

## Content

**Step 4 (final) of the flagship trail.** ← prev: [pww-data](../concepts/pww-data.md) · start over:
[esapp-overview](esapp-overview.md). Owning project: time step simulation.

You've written the simulation ([timestep-simulation-setup](timestep-simulation-setup.md)) and produced the output
CSVs — this page is how those CSVs are structured and how to write code that reads
and reduces them. The analysis target here is the **solar/wind generation files**,
not a network/contingency report.

## What the simulation produces
Each run writes **two CSVs**: one solar, one wind. Naming:

| Run type | Solar file | Wind file |
|---|---|---|
| Historical (a full year of quarter files) | `Historical_2025_solar.csv` | `Historical_2025_wind.csv` |
| Forecast (a single `.pww`) | `Forecast_..._solar.csv` | `Forecast_..._wind.csv` |

## File layout (8 metadata rows, then hourly data)
`process_results(gen, df)` in `function.py` builds each CSV. The first column is
`DateTimeUTCExcelFormat`; every other column is one renewable generator. The file
opens with **8 metadata header rows**, then the hourly time series. The header rows,
in order, come from these generator fields:

| Header row | Source field |
|---|---|
| `ISO` | `CustomString:2` (assigned by the PFW_Insertion step) |
| `PV / Wind` | `GenFuelType` (`SUN` / `WND`) |
| `PV / Wind Types` | `TSPFWModelString` (the PFW model on the unit) |
| `Gen Max MW` | `GenMWMax` |
| `State` | `ZoneName` |
| `Utility` | `AreaName` |
| `Latitude` | `Latitude` |
| `Longitude` | `Longitude` |

Below the header rows, each data row is one UTC hour and each cell is that
generator's MW for that hour.

## How the values get there
- **Timestamps:** PowerWorld exports Excel-serial timestamps in CST.
  `time_utils.convert_to_utc` shifts CST→UTC, subtracts an hour during US DST
  (second Sunday in March → first Sunday in November), rounds to the nearest hour,
  and writes ISO-8601 UTC strings. (`time_utils.py` is verified against real runs —
  don't change it without a reason.)
- **Solar vs wind split:** columns are matched to generators whose `GenFuelType`
  contains `SUN` (solar file) or `WND` (wind file), keyed by `'BusNum' 'GenID'`.

> **Note on forecast pre-processing:** `interpolate_to_hourly` exists in
> `time_utils.py` for forecast pre-processing but is NOT invoked by the current run
> path (`function.py` / `process_results` / `main.py`).

## Reading / analyzing the CSVs
Because the first 8 rows are metadata, load with pandas accordingly, e.g.:

```python
import pandas as pd
raw = pd.read_csv("Historical_2025_solar.csv")
meta = raw.iloc[:8]            # the 8 description rows (ISO, type, max MW, lat/lon...)
data = raw.iloc[8:].copy()     # hourly time series
data["DateTimeUTCExcelFormat"] = pd.to_datetime(data["DateTimeUTCExcelFormat"])
data.iloc[:, 1:] = data.iloc[:, 1:].astype(float)
```

Typical reductions once loaded: sum across generator columns for a fleet
solar/wind profile; group columns by the `ISO` / `State` / `Utility` metadata rows
for regional totals; divide by `Gen Max MW` for capacity factors; find peak/trough
hours for extreme-scenario screening.

To write matplotlib code that plots these reductions → [visualize-renewable-output](visualize-renewable-output.md).

## File the answer back
A good analysis is a wiki asset, not chat exhaust. Per [CLAUDE](../AGENTS.md), save notable
comparisons or charts as a new `concept`/`method` page, link it from
time step simulation and [index](../index.md), and append to log.

## Next

Plot the results → [visualize-renewable-output](visualize-renewable-output.md)

## Trail complete
[esapp-overview](esapp-overview.md) → [timestep-simulation-setup](timestep-simulation-setup.md) → [pww-data](../concepts/pww-data.md) →
**how-to-analyze-results** → [visualize-renewable-output](visualize-renewable-output.md) ✅
