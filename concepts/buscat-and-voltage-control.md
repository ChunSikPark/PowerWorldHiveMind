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
