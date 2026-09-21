---
type: concept
domain: tooling
aliases: [distributed-computing-add-on, distributed-computer-list, verify-computers-available, ds-server]
tags: [powerworld, distributed-computing, contingency, atc, transient-stability, pv-qv, silent-failure]
---

# Simulator's built-in Distributed Computing add-on

## Abstract

[Parallel N-1 contingency solve](parallel-contingency-solve.md) exists because
Simulator's own Distributed Computing add-on silently fell back to single-process
serial on this machine. This page is the checklist that workaround never needed to
follow through on: what the built-in feature actually requires before it will run
anything on a remote or even a local core, and the specific settings that make it
degrade quietly rather than error. It is a paid add-on, separate from SimAuto,
configured once as global Simulator options rather than per-case.

## Connections

**Up:** [Home](../index.md) · **Across:** [parallel-contingency-solve](parallel-contingency-solve.md) · [lodf](lodf.md) ·
[post-contingency-aux-state-carryover](post-contingency-aux-state-carryover.md) (a different
Contingency Analysis batch-run hazard — that page's per-contingency aux hooks leak state
across a serial run, this page's worker chunking is what makes the run parallel in the
first place) · **Deeper:** [esapp](esapp.md)

## Content

### One shared computer list, several consumers

Distributed Computing is configured once, in Simulator Options, as a single
**Distributed Computer List** — not per-tool and not per-case. Contingency
Analysis, ATC, Transient Stability, and QV Curves (added in version 24) all read
the same list. Power flow itself does not participate. Using local CPU cores
instead of a remote machine is not a different mode — it means adding a computer
to the list named `localhost`.

### Authentication is the first silent trap

Every non-local entry needs domain/username/password credentials, which Simulator
stores encrypted and unlocks at runtime with a user-set **Master Password**. The
trap: adding authentication for the *local* machine causes Windows to return an
"Access is denied" error instead of running locally. If a local-only distributed
run fails outright rather than degrading, stray local credentials are the first
thing to check.

### Verify before trusting the run

A **Verify Computers Available** action populates `Enabled`, `Available`, and
`Cores` per machine. Nothing else in the dialog confirms a machine will actually
pick up work — skipping this step and assuming the list is live is a plausible
reason a run stays serial with no error raised.

### Errors silently retire a worker for the rest of the run

Each computer entry carries a **Max # Errors** setting that defaults to **1**.
Once a machine hits that many failures, Simulator stops sending it work for the
remainder of the run and does not retry — a single transient network blip can
permanently drop a worker mid-sweep, with the run finishing on whatever machines
are left and no indication that capacity was lost partway through. **Processes**
(worker processes to start on that machine) can also be set above the core count,
which is a separate knob from `Cores` reported by Verify Computers Available.

### Chunking is configured per tool, not globally

The unit of work handed to each machine differs by tool:

- **Contingency Analysis** — `Number of Contingencies per Process`: contingencies
  are grouped into batches of this size and doled out as machines finish.
- **ATC** — `Number of Directions per Process`, which only applies to
  multiple-direction ATC runs, not multiple-scenario ones.
- **QV Curves (v24+)** — scenarios are bus x contingency combinations; Simulator
  picks whether to chunk by bus count or contingency count based on `ChunkSize`
  versus whichever count is larger, as an explicit fallback rule.
- **Transient Stability** — a plain on/off toggle with no chunk-size control at
  all; TS distributes whole contingencies with no tunable batch size.

An aux script driving any of these should set the matching per-tool field, not
assume one setting covers all four.

### Nothing here is a case object

None of this — the computer list, credentials, Max # Errors, per-tool chunk
sizes — is exposed as a Python object in [esapp](esapp.md) or serialized into the
`.pwb`. It lives entirely in Simulator's global options and per-dialog fields, so
it cannot be scripted through case data the way most of this kit's other settings
are; it has to be set up once in the Simulator UI (or via SCRIPT actions against
those same global options) before any distributed run will do anything at all.

### Relationship to this kit's own workaround

[parallel-contingency-solve](parallel-contingency-solve.md) exists precisely
because this feature was never configured to the point of Verify Computers
Available reporting live workers — it documents an OS-process-level substitute,
not a diagnosis of why the built-in feature failed. If the built-in feature is
ever revisited instead of the workaround, the checklist is: computer list entries
(including `localhost` if wanted) -> correct authentication (never on the local
entry) -> Verify Computers Available actually showing available cores -> Max #
Errors raised from its default of 1 if the network is at all lossy. For a
different way to avoid a large-N-1 solve entirely rather than parallelizing it,
see [lodf](lodf.md).

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*
