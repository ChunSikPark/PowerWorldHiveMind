---
type: concept
domain: tooling
aliases: [scheduled-actions, schedule-add-on, apply-scheduled-actions-at, gantt-outages]
tags: [powerworld, scheduling, scripting, topology, outages]
---

# Scheduled Actions scripting

## Abstract

Scheduled Actions is Simulator's paid Gantt-chart add-on for planned-outage topology
changes, and it has four SCRIPT commands that drive it headlessly. The trap: a
Scheduled Action Group can sit in the case, inside its time window, looking ready to
fire — and never apply, because a separate `Status` flag on the group is Inactive. Code
that walks the action list and assumes "in window" means "will run" gets silently wrong
topology. This page covers the apply/revert state mechanic those four commands drive
and the breaker-identification taxonomy they produce, none of which is explained beyond
a one-line name in the existing script references.

## Connections

**Up:** [pw-manual-map](pw-manual-map.md#scheduled-actions) · **Across:**
[aux-script-commands](../references/aux-script-commands.md) ·
[the named-wrapper-over-RunScriptCommand rule](../AGENTS.md) ·
[island-and-breaker-grouping](island-and-breaker-grouping.md) (that page's Breaker Isolated
Groups taxonomy is the per-bus analogue of this page's per-action `Origin` tagging) ·
**Deeper:**
[powerworld-limitset-setdata](../methods/powerworld-limitset-setdata.md) (a different
per-object SetData gotcha, same "silent success" family)

## Content

### What a Scheduled Action is

A Scheduled Action targets one Branch, Shunt, Load, or Generator with an action type —
Open, Close, Open with Breakers, Close with Breakers, or (generators only) Set To /
Changed By a field value. Individual actions belong to a **Scheduled Action Group**,
which owns the Start/End time window shown on the Gantt chart.

### The activation gate: Status is separate from the time window

A group also carries a `Status` (itself a reusable object, Active or Inactive).
**Only Active groups are ever applied** — an Inactive group still renders on the Gantt
chart inside its window but has zero effect on the case. Don't infer "will fire" from
the time window alone; check the group's Status.

### The four script commands and the reference-state cycle

The GUI's "Apply Actions" checkbox snapshots system state the instant it's checked and
restores that exact snapshot the instant it's unchecked. The four SCRIPT actions map
onto that same mechanic:

- `ScheduledActionsSetReference` — captures the state that will be restored before
  applying a given timestamp.
- `ApplyScheduledActionsAt` — applies whatever actions are Active within a filtered time
  window.
- `RevertScheduledActionsAt` — applies the *opposite* of those same actions.
- `IdentifyBreakersForScheduledActions` — expands an Open/Close-Breakers action into
  individual breaker actions (see below).

Driving a sweep of scheduled outages by script means calling these in the right order —
set reference, apply at T, do work, revert at T (or re-set reference before the next T)
— otherwise state accumulates across steps instead of giving a clean per-timestep
snapshot.

Two options change what "within the window" and "reverted" mean:

- **Apply All Within Resolution**: given a Resolution (time-slider step) and the current
  View Time, every action inside `[View Time, View Time + Resolution)` counts as active
  for that step — a coarse resolution can pull in actions nominally scheduled somewhat
  later than the view time.
- **Use Normal Status**: on revert, restores each device's *Normal Status* field instead
  of whatever state the previous action left it in — matters when action groups overlap
  or sit adjacent in the sweep.

### Breaker identification produces a taxonomy, not a boolean

Running "Identify Breakers" on an Open/Close-Breakers action converts it into individual
breaker Open/Close actions, each tagged with an `Origin`:

- `User` — hand-authored.
- `Added` — synthesized to actually achieve the requested topology.
- `Extra` — a device incidentally isolated or connected as a side effect.

**`Extra` actions default to `Allow Active = No`** — they exist for audit visibility and
will not be applied even though they appear in the action list. Code that walks the
action list and applies everything present must check `Allow Active`, not just
presence, or it silently over-applies.

A related gap: Breaker actions typically don't carry their associated Disconnect
switches along. The "Switch Disconnects to Normal Status in Open and Close Breakers
Actions" option exists to patch this — without it, and without the case's disconnects
already at normal status, the resulting topology after a breaker action can be wrong
even though the action reports success.

### Conflicts are opt-in, not automatic

`Check Conflicts` populates a `Conflicts` field when two different Scheduled Actions
target the same device with different actions. This must be run explicitly —
conflicting actions are not rejected at authoring time.

### CROW CSV import is a labeling precondition, not a plug-in path

CROW (Control Room Operations Window) outage schedules can be imported as CSV, but
resolving CROW's device identifiers against PowerWorld objects requires case-specific
labeling conventions set up in advance — not an out-of-the-box import.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*
