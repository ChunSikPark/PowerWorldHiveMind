---
type: concept
domain: tooling
aliases: [raw-roundtrip, epc-roundtrip, psse-raw-traps, pslf-epc-traps, raw-epc-silent-loss]
tags: [powerworld, raw, epc, pti, pslf, roundtrip, data-loss, gic]
---

# RAW/EPC round-trip traps

## Abstract

Reading or writing a PTI RAW or GE EPC file through PowerWorld is not a lossless transcription —
Simulator reinterprets, discards, or silently converts fields on both the read and the write side,
and none of it raises an error or a warning. A model saved to RAW or EPC and reloaded is not
guaranteed to match the model you started with, even without touching it in between. This matters
most for anyone scripting a save/reload cycle, or comparing a case before and after a round-trip and
trusting the diff to be empty when it isn't.

## Connections

**Up:** [pw-manual-map](pw-manual-map.md) · **Across:** [save-powerworld-case](../methods/save-powerworld-case.md) · [case-to-case-device-transplant](case-to-case-device-transplant.md) · [case-impedance-completeness](case-impedance-completeness.md) ·
[fixednumbus-and-raw-v34](fixednumbus-and-raw-v34.md) (full-topology RAW v34+ layers its own
`FixedNumBus`/`SubNodeNum` numbering scheme on top of the round-trip behavior documented here) ·
[difference-case-tool](difference-case-tool.md) (its tolerance-aware diff is the practical
way to check whether a round-trip actually changed anything, rather than trusting a naive diff)

## Content

### Why this is different from the PWB `SaveCase` trap

[save-powerworld-case](../methods/save-powerworld-case.md) documents a PWB save that reports success
and writes nothing. RAW/EPC is a different failure shape entirely: the file **is** written, and it
**does** reload — but the model it describes has changed underneath you, because RAW and EPC cannot
represent everything Simulator's internal model can. There is no missing-file check that catches
this; the only defense is knowing what each format silently reinterprets.

### On RAW read — values Simulator overwrites or reclassifies, not what the file says

- **Radial-bus voltages are overwritten.** A bus with no shunt/conductance, no online device, and
  reached by exactly one non-transformer branch has its voltage silently replaced by the far-end
  bus's voltage — a convergence aid, not the source value. Never trust a post-load voltage on such a
  bus as data you supplied.
- **Generator participation factors come from PMax MW, not MVA base.** If your source data assumed
  participation tracked MVA capacity, the loaded value won't match.
- **Switched shunt modes 4 and 5 have no Simulator equivalent** and downgrade to a constant-Mvar
  fixed shunt; mode 3 becomes "controlling Mvar output of generation." Both are lossy conversions
  with no warning.
- **Any non-transformer branch with R=0, B=0, and X<0 is auto-flagged as a series capacitor** — this
  matters directly for GIC work, since a series cap blocks DC GIC flow. A branch that only
  *coincidentally* matches those three parameters gets reclassified regardless of intent.
- **Three-winding transformer star-bus voltage/angle can be silently overridden** by Simulator's own
  estimate, if that estimate produces smaller terminal-bus mismatches than the value in the file. A
  re-read of a file you just wrote is not guaranteed bit-identical even without any edits of your own.
- **Bus rating sets are reassigned on read**: Normal ratings land in set A, Contingency ratings in
  set B, regardless of how the source file tagged them.
- **An unexpected trailing field on a Bus/Gen/Load/Line/Transformer record is opportunistically read
  as a memo or label** rather than raising a parse error — malformed-looking data is silently
  absorbed instead of rejected.

### On RAW read — one field that is lost outright

Inline comments on a data line load into the `Memo` field on read, but **that Memo is never written
back out on a RAW save** — a one-way loss. If you depend on preserving those comments across a
round-trip, capture them separately before the first read.

### On RAW write — what gets synthesized or converted away

- **A switched shunt with no defined blocks does not round-trip as-is.** RAW write always emits at
  least one block; if none exists, a single 1-step block sized to the present output is synthesized.
- **Line-drop and reactive-current-compensation control on a generator has no RAW representation.**
  On write, such a generator is silently rewritten to instead regulate its own terminal bus at that
  bus's present voltage — a real control-behavior change for anything that later reads the file.
- **Labels are lost on write unless you opt in.** They can optionally be embedded as
  `/* [label] */` comments; without that, labels do not survive the trip to RAW at all.

### On EPC read — flags and fields with no direct PowerWorld equivalent

- **PSLF's "Baseload Flag" maps into two different Simulator concepts from one source flag**: the
  `Governor Response Limits` field (Normal / Down Only / Fixed) and, depending on an interpretation
  option, Post-Contingency-Prevent-AGC as well.
- **AVR on/off is inferred, not read directly** — PSLF has no explicit AVR flag, so Simulator derives
  it from `Qmax − Qmin` against a default 2.0 Mvar deadband. A unit with a narrow reactive range can
  come in as AVR=NO even if the source model intended AVR on.
- **`aloss` (loss allocation) is rounded onto whichever bus is "From End Metered"** — an
  approximation of PSLF's semantics, not a preserved value.

### On EPC write — modes and units that don't survive

- **Switched shunts on Generator-Mvar or Wind-Mvar control are written as fixed (locked) control.**
  EPC has no representation for those control modes, so exporting freezes them silently.
- **If `GE Ohmic Data Flag`=1, R/X are written in ohms and B in microMhos instead of per-unit** — a
  units trap for any downstream code that assumes per-unit throughout.

### Common to both formats

- **Appending to an existing case overwrites by key**, not merges: a record sharing the same bus
  number completely replaces the existing one. A branch is only appended if **both** its terminal
  buses already exist in the target case — a branch pointing at a not-yet-created bus is silently
  dropped, not deferred until that bus appears.
- **Newly appended buses/branches are flagged "just added"** so the power-flow pre-processing step
  auto-estimates their voltage/angle — appended data does not need to arrive pre-solved to converge.

### Formats that are one-way or lossy by design

- **Areva HDBExport (`.csv`) can only be read, never saved** by Simulator — it's a full-topology
  import for the Integrated Topology Processing add-on, not a general exchange format.
- **UCTE (`.uct`) and IEEE Common Format are input-oriented and lossy.** IEEE CF in particular does
  not support multiple loads or generators at a single bus.

### How to catch the loss instead of discovering it later

There is no single flag that surfaces these. The practical defenses:
1. **Never treat a reloaded RAW/EPC file as identical to what you saved** — diff key fields (voltage,
   participation factors, shunt mode, control mode) explicitly rather than assuming equality.
2. **Snapshot anything format-specific before the round-trip** — memos, labels, line-drop/RCC control
   settings, shunt control modes — and reapply if these matter downstream.
3. **Check series-capacitor reclassification explicitly** before a GIC study on any case that passed
   through RAW: `R=0, B=0, X<0` branches may not be capacitors you intended.
4. For a lossless in-Simulator round-trip, prefer PowerWorld's own AUX export
   ([case-to-case-device-transplant](case-to-case-device-transplant.md)) over RAW/EPC — AUX carries
   Simulator's full field set, not a third-party format's subset.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*
