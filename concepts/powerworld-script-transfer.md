---
type: concept
domain: tooling
aliases: [script-transfer, drop-file-aux, SimulatorScriptInput, SimulatorScriptOutput, external-script-control, sced]
tags: [powerworld, aux, script, external-program, llm, simulator-25, undocumented]
---

# Drop-file script transfer: driving Simulator without SimAuto

## Abstract

Simulator 25 beta can watch a directory and execute any `.aux` dropped into it, writing
back the message-log slice produced by that load. Write a file, read a file — **no COM, no
SimAuto call, and therefore no SimAuto licence.** This is the cheapest channel an external
program (an LLM among them) has ever had into PowerWorld, and it is the first one that
needs nothing installed on the caller's side.

**It is not in the *Auxiliary File Format* manual.** Searched 2026-09-12 against the
September 1, 2026 edition: zero hits for `ScriptTransfer`, `SimulatorScriptInput`,
`SimulatorScriptOutput`, `ScriptInputOutputPollSec` and "drop file". The only source is
Overbye's September 2026 slide deck *Recent Modifications to PowerWorld Simulator to Allow
for More Interaction with External Programs*, which describes the functionality as new and
"probably evolving". Everything below is from that deck; nothing here is measured yet.

## Connections

- **Up:** [powerworld-simauto](powerworld-simauto.md) · [Home](../index.md)
- **Across:** [aux-only-powerworld](aux-only-powerworld.md) (what to write *inside* the dropped file — every trap
  and the read-back rule apply unchanged) · [aux-script-commands](../references/aux-script-commands.md) ·
  [esapp-script-command-wrappers](esapp-script-command-wrappers.md) (the Python-side channel this one bypasses)
- **Deeper:** [esapp-schema-reference](../references/esapp-schema-reference.md) (field-name provenance — still mandatory here)

## Content

### What it does

With the feature enabled, every `ScriptInputOutputPollSec` Simulator checks the configured
directory for a file named exactly **`SimulatorScriptInput.aux`**. If it is there:

1. the aux file is **loaded** (i.e. executed — unnamed `SCRIPT{}` blocks auto-run, see
   [aux-only-powerworld](aux-only-powerworld.md)),
2. the input file is **deleted**,
3. **`SimulatorScriptOutput.txt`** is written into the same directory, containing the new
   message-log entries associated with that load.

That is the whole protocol. Request is a file appearing; response is a file appearing; the
deletion of the request is the acknowledgement.

### Turning it on

Two preconditions the deck states explicitly, and both are real constraints rather than
setup steps: **a case must already be loaded**, and **the Script Command Execution Dialog
(SCED) must be visible**. Tools → Script opens it.

In the SCED:

| Field | Registry name (PowerWorld section) |
|---|---|
| Enabled External Script Control | `ScriptTransferFileEnabled` |
| ScriptTransferFileDirectory | `ScriptTransferFileDirectory` |
| Script File Poll Interval | `ScriptInputOutputPollSec` |

Settings persist in the registry, so this is configurable ahead of a session rather than
only through the dialog.

### The shape of a request

From the deck's worked example, on PowerWorld's own shipped `B7Flat` case:

```
// First change the generator status
DATA (Gen [ObjectID, STATUS])
{
"Gen 1 '1'" "Open"
}
// Then solve the power flow
SCRIPT{SolvePowerFlow;}
```

Two things to copy from this rather than invent:

- **`DATA` + `ObjectID` is a compact one-field key.** `"Gen 1 '1'"` identifies the unit
  without a separate `BusNum`/`GenID` pair. The manual documents `ObjectID` as an
  identifier form on several commands, so this is not deck-only syntax.
- **A single dropped file mixes `DATA` and `SCRIPT` blocks and they run in file order.**
  The edit lands, then the solve runs against it.

The corresponding `SimulatorScriptOutput.txt` is the raw log slice — `1 records read from
file.`, the AGC adjustments, the mismatch iterations, `Simulation: Successful Power Flow
Solution`, bracketed by `Starting load of auxiliary file:` and `Finished load of auxiliary
file:` lines.

### Write it elsewhere, then copy it in

The deck says to create `SimulatorScriptInput.aux` and "store it somewhere other than in
this directory", then copy it into the watched directory. Treat that as mandatory. The
poller has no way to tell a finished file from one still being written, so authoring in
place races the poll interval and can feed Simulator half an aux — which, given that a
truncated script is still a *valid* script up to the truncation point, is the silent
failure this whole vault exists to prevent.

An atomic move within the same volume is the safer version of the same idea.

### What it does not give you

The output is a **log transcript, not a return value.** `SolvePowerFlow` succeeding or
failing shows up as English in a text file, not as a status your caller can branch on
without parsing. So:

- **The read-back discipline from [aux-only-powerworld](aux-only-powerworld.md) applies unchanged.** If the
  answer matters, `SaveData` it to a CSV and read the CSV. Do not infer success from the
  output file merely existing.
- `Simulation: Successful Power Flow Solution` is the string worth grepping for, but its
  absence is not the same as a specific diagnosis.
- This is **not headless**. A visible GUI dialog is required, so it does not replace
  [esapp](esapp.md) for batch or parallel work — see [parallel-contingency-solve](parallel-contingency-solve.md).

### Open questions to settle by experiment

None of these are answered by the deck, and each one changes how a caller must be written:

- Is `SimulatorScriptOutput.txt` **overwritten or appended** on each cycle?
- Is there any signal that the output file is **complete**, or must the caller poll for
  size stability?
- What happens when the aux **fails to parse** — is an output file written at all, and does
  the input file still get deleted?
- Does `StopAuxFile` or `ExitProgram` inside a dropped file behave sanely here?
- What is the **minimum usable poll interval**, and does a short one cost anything?
- Does a second `SimulatorScriptInput.aux` dropped mid-execution get picked up, queued, or
  lost?

### Version floor

**Simulator 25 beta, build date on or after September 12, 2026.** Earlier builds do not
have it, including every Simulator 24 build regardless of patch date. See
[version-requirements](version-requirements.md).
