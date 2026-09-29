---
name: violation-map
description: "Build an interactive network map of the violations in PowerWorld cases: out-of-band voltages with the reactive balance around them, or the radial trees one outage can island, with candidate fixes measured and a Before/After switch. Use when the user says map the violations, visualize the violations, show me where the high voltages are, show me the network around a bus, which outages island load, where are the radial lines, or asks to see a voltage or islanding problem and what could fix it."
---

# Violation map

A working engine plus a page contract. The engine lives in `engine/` next to this file and is
driven by one config file; the contract and every trap it guards against are in
`methods/violation-network-map.md` under the **kit root** (`${CLAUDE_PLUGIN_ROOT}` when installed
as a plugin, otherwise the directory holding `AGENTS.md`). Read that page in full before running
anything. Reuse the engine; do not rebuild the map from scratch.

## 1. Before anything else

- Run the preflight in `methods/preflight-powerworld.md`. The engine drives PowerWorld through
  esapp; a machine that cannot is a fact about the machine, not a bug to code around.
- Read `methods/violation-network-map.md`, then the page it points at for anything you are about
  to write (`methods/adding-devices-esapp.md` before a candidate that creates a device).

## 2. Ask before extracting (one question, defaults stated)

1. **Which cases and which states.** One case per scenario; a second state (after a fix) is
   optional. If the cases are restricted — CEII or otherwise — say that the built page embeds
   bus names, substation names and coordinates, and must be shared accordingly.
2. **Which violations:** intact voltage (the default band is 0.94–1.05 pu; ask whether theirs
   differs), voltage after listed outages, or islanding (the radial page).
3. **Area and depth:** the seed buses (default: the out-of-band network buses) and the
   substation-hops around them (default 5; offer 2–3 for a very meshed area). **Opening view:** a
   light case (under a bus-count cutoff) opens on the whole case with the site highlighted;
   zooming into a site shows that area only, the rest hidden, with boundary stubs, click to
   re-centre; on a light case a "Back to whole case" control returns to the whole-case view; and
   a "Render further network" button that adds N more hops per press; a heavy case
   (over the cutoff) opens straight on the area. The page says which mode it opened in and why.
   The cutoff is a tunable bus-count default, measured by timing page build and render on public
   synthetic cases; the engine does not apply this rule yet. What is drawn never limits what is
   computed.
4. **Look only, or measure fixes:** reactors, new lines, setpoint edits, measured in memory.

Then write their `config.json` from `config.example.json` next to this file. Keep it and the
`out_dir` outside the kit folder.

## 3. Run

Call each script by its full path with the config as the first argument; the order is on the
method page. Measurement scripts open PowerWorld once per candidate — say roughly how long
before starting a long one, and run it in the background.

## 4. Hand it over

- Screenshot the built HTML once (a headless browser is enough) before saying it is done.
- Say what was measured and what was not: the voltage page tests only the listed outages, the
  radial page only bridge outages. Neither is a full N-1.
- If the page is published somewhere with a store (a Claude artifact with the `db` capability),
  read the user's Choose/Accept back from it rather than asking them to retype the pick.

## Not built yet

A **thermal** view. If asked, extend `engine/template.html` — lines coloured by percent of
Rate A, overloaded branches as the problem list, the driving outage per branch — and say that
you are building it for the first time.
