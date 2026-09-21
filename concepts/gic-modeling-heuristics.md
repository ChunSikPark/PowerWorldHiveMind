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
