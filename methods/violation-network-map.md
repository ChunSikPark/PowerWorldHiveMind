---
type: method
domain: tooling
aliases: [violation-network-map, violation-map, voltage-map, reactive-balance-map, radial-ties-map,
  islanding-screen, map-the-violations, visualize-the-violations, network-map, bridge-screen]
tags: [esapp, powerworld, voltage, overvoltage, islanding, radial, bridges, visualization, html,
  remediation, n-1, reactive-power]
---

# Mapping Violations on the Network: the Voltage Page and the Radial-Ties Page

## Abstract

Two single-file HTML pages that put a violation **on the map** instead of in a table, built by the
`violation-map` skill's engine (`skills/violation-map/engine/`). The **voltage page** shows the
substations around a set of out-of-band buses, every line in its own kV colour, a click-to-zoom
problem list, a one-line of any substation, the **reactive balance** inside the radius (line
charging against generators absorbing and reactors, with the *room* each has left), and —
optionally — measured candidate fixes with a Before/After switch and a scenario × outage
pass/fail grid. The **radial-ties page** screens the whole grid for **bridges** (lines whose
single outage splits the network), groups them into radial trees, suggests a tie per tree and
shows its AC-measured verdict.

Four facts decide whether the pages tell the truth, and each fails silently: an outage that
**islands load solves with zero violations**, so islanding needs its own screen; a measured
candidate needs a **fresh case**, because LTC taps and switched shunts do not move back when you
undo; a tie's **rating does not scale with its length**; and a PowerWorld process you do not
`esa.exit()` stays resident.

## Connections

- **Up:** [Home](../index.md)
- **Uses:** [adding-devices-esapp](adding-devices-esapp.md) · [esapp-overview](esapp-overview.md) · [reading-violationctg](reading-violationctg.md)
- **Across:** [violation-remediation](../demos/violation-remediation.md) · [ranking-new-devices-by-severity](ranking-new-devices-by-severity.md) · [handling-errors](handling-errors.md)

## Content

### When to reach for it

When the question is *where* — where the high buses sit, what feeds them, what one outage cuts
off, what a new line would close. A table of 40 overvoltage rows is four problems in four
places; the map makes that grouping visible before any fix is proposed. It is the diagnose step
of [violation-remediation](../demos/violation-remediation.md), drawn.

It is **not** a replacement for the N-1 run. The voltage page tests only the outages you list;
the radial page tests only bridge outages. Neither is a full contingency analysis — the pages
say so on every measured result, and so should you.

### Ask before extracting anything

Four decisions belong to the user, and each changes what gets extracted:

| Ask | Default to offer |
|---|---|
| Which cases, and which **states** (as delivered, after a fix) | the delivered set only |
| Which violations: intact voltage, N-1 voltage, islanding | intact voltage |
| Area and depth: seeded from which buses, how many substation-hops | seeds = the out-of-band buses, 5 hops |
| Look only, or also **measure candidate fixes** | look only |

Very meshed areas explode past a few hops — open those at 2–3 and say so. Step-up, star-point
and tertiary buses are out of the count by default (`exclude_bus_prefixes`); list them
separately if the user wants them.

### The pipeline

Everything is driven by one `config.json` (see `skills/violation-map/config.example.json`):
scenarios, states with one case path per scenario, the voltage band, the seeded areas, and
optionally a `designs` block. Every output lands in the config's `out_dir`; nothing is written
to a case.

```bash
E=<kit root>/skills/violation-map/engine
# voltage page
python $E/extract.py         config.json topo      # area topology + hop rings
python $E/extract.py         config.json state     # solved values, every state x scenario
python $E/measure_designs.py config.json           # optional: candidate fixes, in memory
python $E/build.py           config.json           # -> voltage_map.html
# radial-ties page
python $E/extract_full.py    config.json topo
python $E/extract_full.py    config.json inj
python $E/islanding_screen.py config.json          # bridges, core, radial trees
python $E/designs_all.py     config.json           # suggested tie per tree
python $E/measure_trees.py   config.json <scenario>   # per scenario; AC, in memory
python $E/build_radial.py    config.json           # -> radial_ties.html
```

Run the script by its full path rather than changing directory first: each script imports its
sibling `vmap.py`, and Python finds it because the script's own folder is on the path.

### The page contract

- **Every line in its own kV colour, everywhere** (765 green, 345 red, 138 dark, ≤69 olive).
  Emphasis is by width only. Recolouring a line by the group it belongs to reads as a different
  voltage and confuses the reader.
- **Problem list with click-to-zoom**, plus Prev/Next on the map bar.
- **Voltage-layer filter** (All / 765 / 345 / 138 / ≤69) that hides the other classes' lines and
  substations.
- **Substation one-line** on click: bus bars by kV with pu, transformers with X and flow,
  generators and shunts with MVAr and pinned flags, outgoing lines fanned with far-end names —
  and **Isolate neighbourhood** at 1–3 hops.
- A **scenario switch**, a **state switch** (as delivered / after a fix), and for measured
  designs a **Before/After** switch and a scenario × condition grid of pass/fail cells.
- **Reactive balance** inside the radius. Capability is not room: a generator at its absorbing
  limit has capability and no room, which is exactly the unit that cannot help.
- **Choose / Accept** writes the pick to the page's own store when the page is published where
  one exists (a Claude artifact with the `db` capability); the agent reads it back instead of
  asking the user to retype it. Without a store the button is replaced by "tell your agent".
- **PNG/SVG export** with a title band and colours baked in, and a **CSV** of the problems or the
  candidate table.

Open the built HTML in a browser, or publish it. Take one screenshot before handing it over —
a page that renders blank from a data error looks identical to one still loading.

### Traps, each of which cost a run

**`esa.exit()` every case you open.** `del pw` leaves one `pwrworld.exe` resident per open —
roughly a gigabyte each on a 10,000-bus model — and a measurement loop that opens a case per
candidate will starve every other process on the machine. The engine closes in a `finally`.

**A fresh open per candidate; never trust an undo.** Taking a new line back out does not move
LTC taps or switched shunts back to where they were, so the next candidate is measured on a
different case. `measure_designs.py` reopens per candidate. `measure_trees.py` reuses one case
per scenario for speed, and **fingerprints** it after every design — closed-branch count plus a
fixed 40-bus voltage sample — and reopens the moment either drifts. An undo that did not restore
the case once went unnoticed until the fingerprint caught it.

**Islanding solves with zero violations.** When an outage strands buses, PowerWorld drops them
from the solution rather than flagging them, so the violation count stays clean. The radial page
exists because of this; the voltage page marks a substation ISLANDED when every one of its
network buses loses its voltage. Read [reading-violationctg](reading-violationctg.md) for the
N-1 side of the same trap.

**Adding several devices before one solve: freeze the controls.** Live taps and shunts drift
between writes, and the saved case then disagrees with what you measured. Set `ChkTaps`,
`ChkShunts` and `ChkPhaseShifters` to `NO`, add everything, restore them, and take one solve.
The engine adds one device per candidate, so it does not need this — a multi-device candidate
does.

**A tie starts where the MW is, then where it closes the most bridges.** For a chain of substations,
the far end usually removes the most bridges; for a plant tree, start at the plant only when the
plant's own exit is weaker than the plant. `designs_all.py` ranks sources by MW first because
the other order once routed a plant's whole output through a lower-voltage line inside the
pocket when its exit opened.

**Rating does not scale with length; impedance does.** A new line cloned from a template gets R,
X, C and G scaled by the length ratio and the template's whole `LineAMVA` set unchanged. Choose
the template by **rating first** (it must clear the stranded MW) and length second — a template
chosen by length alone once put a line at 250% into a delivered case. The create is read back:
branch count +1, X as asked, status Closed, device type Line. See
[adding-devices-esapp](adding-devices-esapp.md) for why every create must be read back.

### What it does not do yet

**No thermal view.** Both pages were built for voltage and islanding. A thermal page would extend
the voltage template — lines coloured by percent of Rate A, overloaded branches as the problem
list, the driving outage per branch from `ViolationCTG` — rather than start a new one. Say so
when asked for it; do not present the voltage page as covering thermal.
