---
type: reference
domain: tooling
aliases: [aux-cookbook, two-window-workflow, script-transfer-walkthrough, first-drop,
  getting-started-aux, external-script-control-setup]
tags: [demo, aux, script-transfer, walkthrough, getting-started, two-window]
---

# Cookbook: Claude in one window, Simulator in the other

## Abstract

A start-to-finish walkthrough of the file-based workflow, written for someone sitting in
front of two windows. Four recipes, in order: turn the channel on, prove it is alive with a
four-line script, let the agent scan the case for its devices, then change something and
measure it. Every number here came from a real run on a small sample case, failures included.

## Connections

- **Up:** [Home](../index.md)
- **The reference:** [aux-file-mode](../methods/aux-file-mode.md) — the rules and the full
  template this page walks you through
- **The channel:** [powerworld-script-transfer](../concepts/powerworld-script-transfer.md)
- **The language:** [aux-only-powerworld](../concepts/aux-only-powerworld.md)
- **Other demos:** [start-here](start-here.md)

## Content

### How this works

Two windows, side by side. **Simulator on the right, with your case open.** **Claude on the
left.** They never talk to each other directly — they pass files through one folder you
nominate.

Claude writes a script. You copy it into the folder. Simulator notices it, runs it, deletes
it, and writes back a log plus whatever CSVs the script asked for. Claude reads those. That
is the entire loop, and you are the part that moves the file.

Pick the folder now. Anything empty will do:

```
C:\PowerWorldTransfer
```

---

### Recipe 1 — Turn the channel on

Do this in Simulator. Claude cannot do any of it, and will ask you to.

1. **Open PowerWorld Simulator.**
2. **Open your case.** Any `.pwb` will do. The numbers shown further down came from a
   small 7-bus sample, so yours will differ — it is the *shape* of each step that matters,
   not the values.
3. **Switch to Run Mode**, then **Tools → Script** to open the Script Command Execution
   Dialog. The source deck specifies Run Mode at this point; do not skip it on the
   assumption that a script can switch modes for you later.
4. In that dialog, set **ScriptTransferFileDirectory** by browsing to `C:\PowerWorldTransfer`.
5. Tick **Enabled External Script Control**.
6. **Leave the dialog open.** This is the step people skip. The source deck is explicit that
   the functionality is available only while the dialog is *visible*, so closing it stops
   Simulator watching the folder. The settings live in the registry and keep reading as
   enabled either way — so everything still looks configured while nothing happens.
7. **Open Simulator's message log and keep it where you can see it.** Every script writes
   its progress there as it runs.

**Watch that log.** The output file is only written once a run finishes, so while something
is wrong the file tells you nothing — the log is the only place you can see what is actually
happening. It is how you catch the two failures that otherwise look like waiting:

- **A run that is looping** shows the same block of lines appearing again and again, every
  poll interval. Nothing in the folder tells you that; the log makes it obvious in seconds.
- **A run that failed** prints its error there, in full, even in the cases where no output
  file is ever written.

Keeping it visible turns "nothing is happening" into a readable answer, and it is the
difference between fixing a script in one attempt and guessing at it.

Then tell Claude, in these words or your own:

> *"Aux-file mode. My transfer folder is `C:\PowerWorldTransfer` and I have my case loaded."*

**You only do steps 4 and 5 once per machine** — they are stored in the registry and survive
a restart. Steps 1, 2, 6 and 7 are every session, and 6 and 7 are the two that get forgotten.

---

### Recipe 2 — Prove it is alive before you trust it

Do not debug a real script against an unproven channel. Ask for the smallest possible one:

> *"Give me a four-line aux that just writes a marker to the log, so I can check the channel
> works."*

You get something like this. Save it anywhere **except** the transfer folder:

```
SCRIPT
{
  LogAdd("HELLO -- the channel works");
  LogAddDateTime;
}
```

Now **copy** it into `C:\PowerWorldTransfer` and rename it to exactly
`SimulatorScriptInput.aux`.

> Copy it in finished. Do not save directly into the folder from an editor — Simulator cannot
> tell a finished file from one you are still writing, and a half-written script is still a
> valid script up to the point it was cut off. It will run the fragment.

**Within a second, two things happen:**

| | |
|---|---|
| `SimulatorScriptInput.aux` **disappears** | Simulator consumed it. The deletion *is* the acknowledgement |
| `SimulatorScriptOutput.Txt` **appears** | The log from that run |

Open it. The last line is what you are looking for:

```
Automatic loading of file ...\SimulatorScriptInput.Aux started at 2026-09-21T14:43:01.314Z
Starting load of auxiliary file: ...\SimulatorScriptInput.Aux
HELLO -- the channel works
September 21, 2026 09:43:01.342
Finished load of auxiliary file: ...\SimulatorScriptInput.Aux
Automatic loading of file finished successfully in 0.083 seconds
```

**`finished successfully in N seconds` is the completion signal.** On a small case a run
takes 0.08–0.5 s; a large one takes longer, but the line is the same. If you see it, the
channel works, and every later problem is in your script rather than your setup.

**If the file does not disappear**, the channel is not running. In order of likelihood: the
Script dialog got closed, the checkbox is not ticked, or the folder in the dialog is not the
folder you copied into. Delete `SimulatorScriptInput.aux` before you retry, or it will run
the moment you fix the setting.

---

### Recipe 3 — Let it scan the case first

**Once you confirm the setup, the agent should not wait to be asked — it should offer this:**

> *"Channel is live. I cannot see your case from here. Do you want me to scan it first and
> list what devices are in it? It is read-only — it writes CSVs and changes nothing."*

Say yes. It is one drop and it saves you the whole guessing phase, because until it runs the
agent knows nothing about your case: not the bus numbers, not whether there are transformers,
not whether a contingency set already exists. Everything it suggests before this is a guess.

The script it hands you writes one CSV per device class — buses, branches, substations,
generators, loads, shunts, contingencies, areas, zones — plus the case summary. The pattern
repeats, and the comments above each block are the part that matters:

```
//--- STAGE A: where the CSVs go -------------------------------------------
SCRIPT
{
  SetCurrentDirectory("C:\PowerWorldTransfer\scan", YES);   // YES = create it
  CaseSummaryGet("", "SCAN_00_case_identity.txt", 3);
}

//--- STAGE B: the network -------------------------------------------------
SCRIPT
{
  // KEY: BusNum
  SaveData("SCAN_bus.csv", CSV, Bus,
           [BusNum,BusName_NomVolt,BusNomVolt,SubNum,SubName,AreaNum,ZoneNum,
            BusStatus,BusSlack,BusPUVolt,BusAngle,BusGenMW,BusLoadMW],
           [], "", [], NO, NO);

  // KEY: BusNum, BusNum:1, LineCircuit
  // BranchDeviceType is what separates a Line from a Transformer.
  SaveData("SCAN_branch.csv", CSV, Branch,
           [BusNum,BusNum:1,LineCircuit,BranchDeviceType,LineStatus,
            LineR,LineX,LineAMVA,LineMW,LinePercent],
           [], "", [], NO, NO);
}

//--- STAGE C: the injections ----------------------------------------------
SCRIPT
{
  // KEY: BusNum, GenID
  // GenMVRMax/Min is capability, not dispatch. A unit idling at 0 MVAr with
  // 200 MVAr of range is reactive support; GenMVR alone would call it nothing.
  SaveData("SCAN_gen.csv", CSV, Gen,
           [BusNum,GenID,GenStatus,GenMW,GenMVR,GenMVRMax,GenMVRMin],
           [], "", [], NO, NO);

  LogAdd("SCAN COMPLETE");
}
```

**Every table leads with its key fields, and that is not decorative.** A bus row is keyed by
`BusNum`, a generator by `BusNum` + `GenID`, a branch by `BusNum` + `BusNum:1` +
`LineCircuit`. Drop the key and the CSV is a picture rather than data — you cannot join it to
anything, and if you ever write it back PowerWorld cannot tell which device you meant, so the
change silently does nothing and still reports success.

Three things to know when you read the results:

- **A zero-byte CSV means the case has none of that class**, not that the scan failed. No
  header row is written for an empty type. An empty `SCAN_shunt.csv` is a real answer.
- **The summary header and the CSVs can disagree, on purpose.** `SCAN_00_case_identity.txt`
  describes the `.pwb` on disk; the CSVs describe what is loaded right now. If you changed
  something without saving, the CSVs are the truthful half.
- **Search the log for `Warning:`.** This is where it bites hardest, because a scan asks for
  many field names at once and a wrong one is only a warning:

  ```
  Warning: unknown fields will not be written to the file
  Warning: Variable name 'AREALOADMW' is not defined for Area objects.
  ```

  That run wrote a 75-byte `SCAN_area.csv` — the key column and nothing else — and reported
  success. Nothing else tells you the numbers you asked for are missing.

With those CSVs in hand the agent can answer follow-ups without another drop: *what is the
voltage range*, *how many transformers*, *which branches are most loaded*, *is there a
contingency set already*. One drop, then conversation.

### Recipe 4 — Change something and measure it

> *"Take bus 4 out of service and tell me what it does to the system."*

What comes back is one script that baselines the case, opens the three branches touching bus
4, re-solves, writes everything to CSV, and then closes those branches again so your case is
where you left it. Copy in, rename, watch it go. It takes about 0.4 s.

Bus 4 was carrying 93.71 MW of generation and 80 MW of load. Diffing the before and after
CSVs:

| | before | after |
|---|---|---|
| bus 4 status | `Connected` | `Disconnected` |
| bus 4 voltage | 1.000000 pu | 0.000000 |
| bus 3 voltage | 0.992669 pu | 0.961330 |
| slack output | 200.63 MW | 215.83 MW |
| worst branch loading | 68.7 % | 91.9 % |

Only bus 3 moves, because it was the one leaning on bus 4's local generation. Line 1–3 goes
from comfortable to nearly loaded. That is the answer, and it came out of CSVs — the log
never contained it.

**Why the script opens branches instead of the bus.** You cannot switch a bus off by setting
its status: that field *reports* whether the bus is energised, it does not control it.
Writing to it does nothing and still reports success. So the script opens the branches and
lets the status follow — then reads it back to prove it worked.

---

### When it goes wrong

Three failure shapes, all of which look similar from your side of the folder.

**The file sits there and nothing happens.** Setup. Dialog closed, checkbox unticked, or
wrong folder. Delete the file, fix the setting, drop again.

**The file sits there but files keep being written.** The script failed partway and Simulator
is re-running it every poll interval, forever — a failed script is never cleaned up. You will
see output timestamps advancing while the input file stays put. **Delete
`SimulatorScriptInput.aux` yourself.** Nothing else stops it.

**Everything completed, but a column is missing from a CSV.** A bad field name is a
`Warning:`, not an error. The column is silently dropped and the run still reports success.
Search the log for `Warning:` — it is worth doing every time:

```
Warning: unknown fields will not be written to the file
Warning: Variable name 'AREALOADMW' is not defined for Area objects.
```

That run produced a 75-byte CSV with the key column and nothing else, and reported success.

### What this mode costs you

Worth knowing before you build a habit on it.

- **You are the transport.** Every run needs you to copy a file. There is no unattended
  operation.
- **It is not headless.** A dialog has to stay open, so nothing batches or runs in parallel.
- **Claude cannot test its own work.** It can check a script's object types and field names
  before handing it over, but it cannot run it. The first execution is always yours.

What you get in exchange: every script is reviewable before it touches your case, every
artifact is a file you can read and keep, and the deliverable is a script you own rather
than a session that happened once. For work that edits a case, being in the loop is the
feature.
