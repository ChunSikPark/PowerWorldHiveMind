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
