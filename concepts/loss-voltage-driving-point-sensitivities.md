---
type: concept
domain: cross-cutting
aliases: [loss-sensitivity, flow-voltage-sensitivity, driving-point-impedance, self-sensitivity, penalty-factor]
tags: [loss-sensitivity, voltage-sensitivity, driving-point-impedance, sensitivities, powerworld, cross-cutting]
---

# Loss, flow/voltage, and driving-point sensitivities — reference frames that trap unwary reads

## Abstract

Three sensitivity families that share nothing with PTDF/LODF except the word
"sensitivity": loss sensitivities, whose absolute value is meaningless outside a
differenced pair; flow/voltage sensitivities, which read zero at every PV bus unless AVR
is temporarily disabled; and driving-point impedance, whose answer depends entirely on
which of three Ybus models it's built from. Each has a silent-failure mode that produces
a plausible-looking wrong number rather than an error. For transaction-based sensitivities
(PTDF/shift factor/OTDF), see [ptdf-shift-factor-otdf](ptdf-shift-factor-otdf.md); for
fast N-1 flow redistribution, see [lodf](lodf.md).

## Connections

**Up:** [Home](../index.md) · **Across:** [ptdf-shift-factor-otdf](ptdf-shift-factor-otdf.md) ·
[lodf](lodf.md) · **Deeper:** [pw-power-flow](pw-power-flow.md)

## Content

### Loss sensitivities: only differences are meaningful

Every loss sensitivity is computed the same way underneath — model a 1 MW/1 Mvar
injection at bus `i` and see how it's absorbed at the island slack — regardless of which
"Loss Function Type" you picked for reporting (Each Island / Each Area / Each
Area-or-Super-Area / a user-specified list). The Loss Function Type only chooses which
aggregate loss total the number is expressed against; the underlying calculation is
always slack-referenced. That means reporting a single sensitivity value as an absolute
fact — "bus A's loss sensitivity is -0.04 MW/MW" — is wrong on its face. Only a
*difference* between two buses' sensitivities, used through superposition for a specific
transfer (`Σ(MW_i × sens_i)` across the transfer's participants), means anything.

**"User-Specified" freezes stale values.** Selecting that Loss Function Type does not
trigger a recalculation — it locks in whatever sensitivities were last computed under a
*different* type. Before trusting a read, confirm which type is currently active and
whether a calculate action has actually run since the last topology or dispatch change.

### Flow/voltage sensitivities: PV buses read zero by construction, not by insensitivity

In the base Single-Meter/Multiple-Transfers and Self-Sensitivity calculations, a PV bus's
voltage is pinned by AVR control in the Jacobian, so a change in real or reactive
injection there produces no voltage change — that's the model, not evidence the bus is
insensitive. Getting a real voltage sensitivity at a generator bus requires temporarily
converting participating PV buses to PQ (fixed Mvar, AVR off): the "Set generators off
AVR... to fixed" option on Single-Transfer/Multiple-Meters does this by turning off AVR,
re-solving, computing the sensitivity, then restoring AVR and re-solving again. A script
driving this should expect **two power-flow solves per call**, and that the case's
dispatch afterward is not guaranteed identical to before (re-convergence, not exact
restoration).

Five tabs cover different (source, target) shapes:

- **Single Meter/Multiple Transfers** — one flow, injection tested at every bus.
- **Single Transfer/Multiple Meters** — one seller/buyer transfer, voltage read at every
  bus.
- **Self Sensitivity** — a bus's own `dV/dP`, `dV/dQ`; fast, restricted to displayed
  buses.
- **Multiple Meters/Single Control Change** — one control device (generator setpoint,
  transformer tap, phase shifter angle, switched shunt Mvar, or branch series reactance
  `Xinj`) against every bus/branch/interface. The `Xinj` control type is the scriptable
  way to ask "what if I added series compensation here" without editing the branch.
- **Multiple Meters/Multiple Control Change** — a full control × meter matrix, exposed
  via SimAuto as `MULTMETERMULTCONTROLSENS`.

### Driving-point impedance: the answer depends on which Ybus you point it at

Three model choices produce three different numbers for the same bus:

1. **Power Flow Ybus** — built from power-flow data only, no generator/motor internal
   impedance, referenced to the power-flow slack.
2. **Transient Stability, including bus local shunts** — the TS Ybus with shunts and
   generator/motor internal impedance left in.
3. **Transient Stability, without bus local shunts** — the same TS Ybus but with the
   local bus's own shunt/generator/motor impedance subtracted out before inverting. This
   is the two-bus-equivalent / SMIB convention.

Both TS-based options require transient stability data to already be loaded — calling
them without it is a precondition failure, not an automatic fallback to power-flow data.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*
