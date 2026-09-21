---
type: method
domain: tooling
aliases: [aux-file-mode, aux-mode, no-python-mode, driving-powerworld-without-python,
  no-simauto-licence, agent-operating-mode]
tags: [powerworld, aux, script-transfer, no-licence, agent, operating-mode, template]
---

# Aux-file mode: driving PowerWorld with no Python and no licence

## Abstract

A working mode for when the Python path is closed — no SimAuto licence, nothing installable
on the caller's side, or a machine you do not control. The agent writes `.aux` only, delivers
it by copying a file into a watched folder, and reads results back out of CSVs. It costs you
return values, branching, headless operation and the ability to test your own work. This page
is the setup handshake, the rules, and a working template to copy.

## Connections

- **Up:** [Home](../index.md)
- **The channel:** [powerworld-script-transfer](../concepts/powerworld-script-transfer.md) —
  how the drop folder works
- **The language:** [aux-only-powerworld](../concepts/aux-only-powerworld.md) — what a `.aux`
  can do unaided, and the syntax traps
- **The alternative:** [esapp](../concepts/esapp.md) — the Python mode this one replaces
- **Command names:** [aux-script-commands](../references/aux-script-commands.md)
- **Build floor:** [version-requirements](../concepts/version-requirements.md)

## Content

### When to use it

Use aux-file mode when the work has to run somewhere the Python stack will not be: a machine
with no SimAuto licence, a colleague's desk, a hand-off where the recipient should not have to
install anything. That portability is the whole point of the mode.

Use [esapp](../concepts/esapp.md) otherwise. It is faster, it returns real values, and it can
be tested without a human in the loop.

**Pick one and stay in it.** Mixing them produces work that cannot be rerun in the environment
it was asked for — an aux deliverable that was secretly debugged in Python still fails on the
machine that has no Python.

### Step 1 — the setup handshake

Four things have to happen in the GUI, and **an agent cannot do any of them.** If you are an
agent entering this mode, your first output is these four steps with the real folder path
filled in, before you write a single line of aux:

1. Open Simulator.
2. **Load the case by hand.** Do not script this — see the `OpenCase` warning below.
3. Tools → Script. Set *ScriptTransferFileDirectory* by browsing to your transfer folder,
   e.g. `C:\PowerWorldTransfer`.
4. Tick **Enabled External Script Control**, and leave that dialog open.

After that, any file copied into the folder as `SimulatorScriptInput.aux` runs automatically,
one poll interval later.

Two things about this cost real time when you do not know them:

- **The settings persist in the registry, the dialog does not.** `ScriptTransferFileEnabled`,
  `ScriptTransferFileDirectory` and `ScriptInputOutputPollSec` survive a restart, so the
  browsing step is once per machine. The dialog still has to be open every session.
- **Closing the dialog stops the poller while the flag still reads enabled.** The dropped file
  just sits there — which looks exactly like a crash, a failed run, and a run still in
  progress. If a drop is not picked up, check the dialog before you debug the aux.

### Step 2 — deliver by copy, never by authoring in place

Write the aux somewhere else, then copy it in as `SimulatorScriptInput.aux`. The poller cannot
tell a finished file from one still being written, and **a truncated aux is still a valid aux
up to the truncation point** — so authoring in place races the poll interval and can feed
Simulator half a script that runs and reports success.

Simulator deletes the input file once it has read it. That deletion **is** the acknowledgement,
and it means the script destroys itself — archive a copy before you drop it or you will end up
with results and no record of what produced them.

### The rules

**Never:**

- **`OpenCase`.** It raises an access violation, aborts the file, and the poller then re-runs
  it every interval *forever*. Measured 2026-09-21 with a file containing nothing but
  `OpenCase` and three log markers, on a freshly started Simulator with no case loaded — so
  this is not a case-swap problem. Load the case by hand. `CaseSummaryGet` on a named `.pwb`
  works fine, so you can still *read* a case file, just not load one.
- **`LogClear`.** Anywhere in a dropped file it suppresses `SimulatorScriptOutput.txt`
  entirely — the script runs and the channel returns nothing at all.
- **A `("", STOP)` failure slot**, unless you mean it. A file that stops early is never
  consumed, so it loops.
- **Writing a derived field to cause a state.** A status field that *reports* a condition
  cannot set it. `BusStatus` is the classic: PowerWorld's field export leaves its `Enterable`
  column empty, so writing it is a no-op that still reports success. Open the branches and call
  `UpdateIslandsAndBusStatus`; the status follows.

**Always:**

- **Read back.** The channel returns a log transcript, not a return value. If the answer
  matters, `SaveData` it to CSV and read the CSV. `Simulation: Successful Power Flow Solution`
  is worth grepping for, but its absence is not a diagnosis.
- **Carry the key fields** in every table you write or intend to write back — `BusNum`+`GenID`,
  `BusNum`+`BusNum:1`+`LineCircuit`, `BusNum`+`ShuntID`. Drop one and PowerWorld cannot tell
  which row you mean; the write no-ops and reports success.
- **Get field names from PowerWorld's own field export**, never from the manual and never from
  memory. The *Auxiliary File Format* manual has no per-object field catalog. The vocabularies
  also differ between the Python and aux sides — a Python class name is not always the aux
  object type, and using one for the other is a hard validation error.

**Cannot, and say so rather than fake it:**

- Return a value, or branch on a result. There is no query-then-act, so a choice that depends
  on the case is made by a human reading an exported CSV between two runs. Asked to "pick one
  at random", say the language has no RNG and no variables, and expose the choice as an edit
  point — do not hardcode a pick and call it random.
- Run headless, batched or in parallel. A visible dialog is required.
- **Test your own work.** Verifying an aux means asking a human to drop it. Reaching for the
  Python channel "just to check" has left the mode.

### Knowing whether it worked

A completed run writes `SimulatorScriptOutput.txt`, framed like this:

```
Automatic loading of file ...\SimulatorScriptInput.Aux started at 2026-09-21T14:43:01.314Z
Starting load of auxiliary file: ...\SimulatorScriptInput.Aux
  ... your LogAdd markers and PowerWorld's own lines ...
Finished load of auxiliary file: ...\SimulatorScriptInput.Aux
Automatic loading of file finished successfully in 0.083 seconds
```

**That trailing line is the completion signal** and it is parseable. Typical round trips are
0.08–0.5 s for a small case.

The failure shape is the input file still sitting there with no output file written. That
happens on an abort — and, measured 2026-09-21, it also happens on a **fully successful** run
that called `OpenCase`: all stages ran, both solves converged, every output file was correct,
zero errors logged, and the poller still re-ran the whole thing five times. Any harness must
pull its own input file on a timeout rather than wait for a signal that is not coming.

### A trap worth knowing before you trust a summary

`CaseSummaryGet` with a blank first argument describes **the `.pwb` file behind the current
case, not the case as you have edited it.** The spec says "the pwb file for the current case"
and means it literally. Unsaved in-memory changes are invisible to it, so diffing two summaries
across an unsaved edit shows no difference at all — which reads exactly like a change that
never happened. Read the CSVs.

### Template

A complete working file. It identifies the loaded case, surveys the folder for other cases,
baselines, opens a bus by opening the branches that touch it, solves, and restores. Change the
two marked lines and it runs on PowerWorld's own shipped `B7flat` sample.

```
//=============================================================================
// Identify the case -> baseline -> open a bus -> solve -> restore.
// Read-only on disk: edits memory, never calls SaveCase.
//
// BEFORE DROPPING:
//   1. Load the case by hand. Stage E names its bus numbers.
//   2. Tools -> Script open, "Enabled External Script Control" ticked.
//   3. Copy in as SimulatorScriptInput.aux. Never author in place.
//
// FOUR RULES (each a silent failure if ignored):
//   - No OpenCase. Access violation, then the poller re-runs the file forever.
//   - No LogClear. It suppresses SimulatorScriptOutput.txt entirely.
//   - CaseSummaryGet reads the .pwb FILE, not your edited case.
//   - BusStatus is derived, not settable. Open the branches, not the bus.
//=============================================================================


//--- A: output folder --------------------------------------------------------
SCRIPT
{
  // <<< EDIT: where the CSVs go. YES = create it if absent.
  SetCurrentDirectory("C:\PowerWorldTransfer\out", YES);
  LogAdd("A1 output dir set");
  LogAddDateTime;
}


//--- B: what case is loaded? -------------------------------------------------
SCRIPT
{
  // Blank name = the file behind the current case. Detail 3 = the most fields.
  CaseSummaryGet("", "01_case_identity.txt", 3);

  // "# of Breakers" decides how you open a bus:
  //   0  -> bus-branch. Open the incident branches (stage E).
  //   >0 -> node-breaker. Use OpenWithBreakers instead.
  LogAdd("B1 01_case_identity.txt -- check '# of Buses' and '# of Breakers'");
}


//--- C: survey the folder ----------------------------------------------------
SCRIPT
{
  // Reads .pwb files WITHOUT opening them -- identify a case with no OpenCase.
  CaseDirectorySummaryGet("C:\PowerWorldTransfer", NO,
                          "00_directory_survey.txt", 1);   // NO = skip subfolders
  LogAdd("C1 00_directory_survey.txt");
}


//--- D: baseline -------------------------------------------------------------
SCRIPT
{
  EnterMode(RUN);
  SolvePowerFlow(RECTNEWT);     // no ("",STOP) slot: a bad solve is a result
  LogAdd("D1 base solve -- grep above for 'Successful Power Flow Solution'");

  SaveData("base_bus.csv", CSV, Bus,
           [BusNum,BusName_NomVolt,BusStatus,BusSlack,BusPUVolt,BusAngle,BusGenMW,BusLoadMW],
           [], "", [], NO, NO);

  // Read this file to choose the bus for stage E. Aux has no RNG.
  SaveData("base_branch.csv", CSV, Branch,
           [BusNum,BusNum:1,LineCircuit,LineStatus,LineMW,LineMVA,LinePercent],
           [], "", [], NO, NO);
  LogAdd("D2 base_bus.csv + base_branch.csv");
}


//--- E: open the bus ---------------------------------------------------------
// <<< EDIT: one line per branch touching your chosen bus, from base_branch.csv.
// KEY = BusNum + BusNum:1 + LineCircuit. All three, or the write no-ops and
// still reports success.
// On B7flat, bus 4 has gen and load and is not the slack, so it still solves.
DATA (Branch, [BusNum,BusNum:1,LineCircuit,LineStatus])
{
2 4 "1" "Open"
3 4 "1" "Open"
4 5 "1" "Open"
}

SCRIPT
{
  UpdateIslandsAndBusStatus;    // without this the bus stays "Connected"
  LogAdd("E1 branches opened, islands updated");

  // Proof the flip is topological: the bus is already dead here, no solve yet.
  SaveData("pre_solve_bus.csv", CSV, Bus,
           [BusNum,BusName_NomVolt,BusStatus,BusPUVolt,BusGenMW,BusLoadMW],
           [], "", [], NO, NO);
  LogAdd("E2 pre_solve_bus.csv -- bus Disconnected BEFORE any solve");
}


//--- F: solve and read back --------------------------------------------------
SCRIPT
{
  SolvePowerFlow(RECTNEWT);
  LogAdd("F1 post-outage solve");

  SaveData("post_bus.csv", CSV, Bus,
           [BusNum,BusName_NomVolt,BusStatus,BusSlack,BusPUVolt,BusAngle,BusGenMW,BusLoadMW],
           [], "", [], NO, NO);
  SaveData("post_branch.csv", CSV, Branch,
           [BusNum,BusNum:1,LineCircuit,LineStatus,LineMW,LineMVA,LinePercent],
           [], "", [], NO, NO);

  // Wrong on purpose: shows the as-saved totals, not the outaged ones.
  CaseSummaryGet("", "03_summary_AFTER_outage.txt", 3);

  LogAdd("F2 post_bus.csv + post_branch.csv written");
  LogAdd("F3 ANSWER = diff base_bus.csv vs post_bus.csv");
}


//--- G: restore --------------------------------------------------------------
DATA (Branch, [BusNum,BusNum:1,LineCircuit,LineStatus])
{
2 4 "1" "Closed"
3 4 "1" "Closed"
4 5 "1" "Closed"
}

SCRIPT
{
  UpdateIslandsAndBusStatus;
  SolvePowerFlow(RECTNEWT);
  SaveData("restored_bus.csv", CSV, Bus,
           [BusNum,BusName_NomVolt,BusStatus,BusSlack,BusPUVolt,BusAngle,BusGenMW,BusLoadMW],
           [], "", [], NO, NO);

  // Matches base_bus.csv on status and voltage. Angles differ in the 5th
  // decimal -- solver tolerance from a different start point, not a failure.
  LogAdd("G1 restored, re-solved, restored_bus.csv");
  LogAddDateTime;
  LogSave("run.log.txt", NO);
}
```

### What that template produces

On `B7flat`, opening bus 4 takes out 93.71 MW of generation and 80 MW of load. The result is
visible in one diff:

| | base | post-outage |
|---|---|---|
| bus 4 status | `Connected` | `Disconnected` |
| bus 4 voltage | 1.000000 pu | 0.000000 |
| bus 3 voltage | 0.992669 pu | 0.961330 |
| slack output | 200.63 MW | 215.83 MW |
| worst branch loading | 68.7 % | 91.9 % |

Only one surviving bus moves, because it was the one leaning on the outaged bus's local
generation. The five voltage-controlled buses hold their setpoints exactly.

The restore returns every bus to `Connected` with voltage magnitudes identical to six decimals.
Angles differ in the fifth decimal and the slack by about a kilowatt — Newton–Raphson
converging from the outaged solution rather than the loaded state. **That is solver tolerance,
not a failed restore**, and expecting an exact match will make a correct run look broken.
