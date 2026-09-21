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
four-line script, inventory a case, then change something and measure it. Every number here
came from a real run on PowerWorld's own shipped `B7flat` sample, failures included.

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
2. **Open a case.** For this cookbook use `B7flat.pwb`, which ships with Simulator — every
   number below is from that case, so you can check your output against it.
3. **Tools → Script** to open the Script Command Execution Dialog.
4. In that dialog, set **ScriptTransferFileDirectory** by browsing to `C:\PowerWorldTransfer`.
5. Tick **Enabled External Script Control**.
6. **Leave the dialog open.** This is the step people skip. Closing it stops Simulator
   watching the folder, while the setting still reads as enabled — so everything looks
   configured and nothing happens.

Then tell Claude, in these words or your own:

> *"Aux-file mode. My transfer folder is `C:\PowerWorldTransfer` and I have B7flat loaded."*

**You only do steps 4 and 5 once per machine** — they are stored in the registry and survive a
restart. Steps 1, 2 and 6 are every session.

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

**`finished successfully in N seconds` is the completion signal.** A real run on this case
takes 0.08–0.5 s. If you see that line, the channel is working and every later problem is in
your script, not your setup.

**If the file does not disappear**, the channel is not running. In order of likelihood: the
Script dialog got closed, the checkbox is not ticked, or the folder in the dialog is not the
folder you copied into. Delete `SimulatorScriptInput.aux` before you retry, or it will run
the moment you fix the setting.

---

### Recipe 3 — Ask what is in the case

Now something useful. Say:

> *"Write me an aux that tells me what is in this case."*

Same cycle: copy in, rename, watch it vanish. You get `01_case_identity.txt`:

```
Information for: ...\B7flat.pwb
EXE Build Date: 25 beta September 12, 2026
CASE SUMMARY BEGIN
  # of Buses = 7
  Gen MW = 768.07
  Load MW = 760.00
  # of Gens = 5
  # of Areas = 3
  # of Breakers = 0
  Slack Buses = Bus 7 (7) in Area Right (3);
CASE SUMMARY END
```

plus CSVs — one row per bus, per branch, per generator — which Claude reads to answer
follow-up questions.

**`# of Breakers = 0` matters more than it looks.** It says this is a bus-branch model, so
to take a bus out you open the branches that touch it. A case with breakers would be
switched a different way. Claude checks this line before proposing an outage.

> **One trap to know now rather than later.** That summary describes the `.pwb` **file on
> disk**, not the case as you have edited it in memory. Change something without saving and
> the summary will not show it. The CSVs always tell the truth; the summary does not. Ask for
> CSVs whenever the answer matters.

---

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
