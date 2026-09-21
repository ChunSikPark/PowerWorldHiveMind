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
