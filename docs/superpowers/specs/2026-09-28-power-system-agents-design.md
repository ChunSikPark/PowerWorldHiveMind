# Power-system agents for PowerWorldHiveMind — design

Date: 2026-09-28. Status: design approved in conversation, awaiting review of this written spec.

## 1. Goal

Give anyone who installs PowerWorldHiveMind a small team of agents that audit a case, run
steady-state studies with the user's own preferences, verify fixes, and answer "which object and
field?" questions — so an open-ended request ("the bus is at 1.06, what fixes it?") is worked on
real numbers instead of guesses.

**Audience:** every user of the kit, including its author. Everything ships inside the kit and is
self-contained: no imports from any private research repository, worked examples and tests on
public synthetic grids only.

**Scope:** steady state only. Transient stability and GIC are out.

## 2. Design principles

1. **Methods are knowledge; agents are roles.** A study method (AC power flow, DC, N-1, OPF,
   SCOPF, time step) is a kit page plus an engine script. Adding a method never adds an agent.
2. **An agent exists only when a skill cannot do the job:** it needs a **fresh context** (output too
   noisy for the main session), **different permissions** (must never write the case), or
   **independence** (must not grade its own work).
3. **Deterministic checks live in code, not in prompts.** An agent reads findings and judges them;
   it does not re-derive a rule on each run.
4. **Judgment happens once, up front, where the user can see it.** Execution is mechanical and
   recorded, so the same request always reproduces the same numbers.
5. **Every PowerWorld write is read back.** PowerWorld reports success on writes that change
   nothing; a write that did not stick fails the run.

## 3. The team

| role | kind | one-line job |
|---|---|---|
| engineer | the user + the main session with the `powerworld` skill | frames the problem, forms hypotheses, chooses candidates, decides |
| case-auditor | subagent, read-only | "is this case sane, and can it run study X?" |
| study-runner | subagent | turns preferences into settings, runs studies exactly, summarises |
| network-visualizer | subagent | maps the network around a site, measures the engineer's design and its own challengers on identical settings, and compares them side by side |
| schema-librarian | subagent, cheap model, read-only | "which object, field, command — and how sure?" |

There is no separate planner agent: power-system judgment belongs in the context the user is
talking to.

**Portability:** subagents are a Claude Code feature. Every role is therefore a **skill plus an
engine** first; the skill carries the commands, and the agent file carries the **role contract**
(responsible / not responsible, protocol, failure modes, examples, checklist — revised 2026-09-28,
see `docs/agents/`). Codex and Gemini users of the kit get the skills and engines and lose only the
context isolation.

## 4. case-auditor

**Triggers:** "review this case", "scan the case", "can I run time step / OPF / N-1 on this",
"is this case ready for X".

**Engine** (`skills/case-audit/engine/`, esapp):
- `audit.py --case <pwb> --profiles base,timestep --out <dir>` → `findings.json` + `findings.md`.
- A **rule** is one small function: id, profile, severity (`BLOCKER` / `WARN` / `INFO`), fields
  read, the check, a one-line why, the kit page that explains it, and a fix pointer — either a kit
  page or an external handoff.
- Findings carry the object's key fields so each points at exact objects.
- **Read-only, enforced by a test:** the engine may solve N-0 in memory but never calls
  `SaveCase` or writes a case. An AST test fails the build otherwise.

**v1 profiles** (only rules already backed by kit pages):

| profile | checks |
|---|---|
| base | N-0 converges; switched shunt or LTC regulating nothing or an out-of-service bus; LTC `XFRegTargetType = Middle`; lightly loaded EHV radial stubs |
| timestep | renewables have `GenFuelType` WND/SUN, a PFW model string, valid Lat/Lon, the ISO field |
| opf | an area on `BGAGC = "OPF"`; AGC-able gens; `GenCostModel` ≠ None with `GenCostCurvePoints > 0` and `GenMCost > 0` |

Deferred: `n1` profile (with the runner's coverage guard), `transient` (out of scope).

**Handoffs for data the kit does not own.** The auditor detects; it never fabricates. Missing PFW
models link to the Grid-Workshop repository's `Auto_PFW` scripts (EIA-860 data the kit does not
carry), and the user re-audits the returned case — which catches units the insertion silently
skipped. Missing cost curves are reported as data to be sourced, never set to a default.

**Agent:** maps the question to profiles, runs the engine, triages each finding as *defect /
likely deliberate / needs you*, and returns **READY / NOT READY for <study>**, the blocker table
and the handoffs. The raw findings stay in the file.

## 5. study-runner

**Phase 1 — configure (agentic).** The user's request in plain words becomes an **option delta**
using the schema-librarian and `references/powerworld-study-options.md`, shown before anything
runs:

```
Sim_Solution_Options.MaxItr               100 → 200
CTG_Options.Include                       NO  → YES
Sim_Solution_Options.EvalSolutionIsland   NO  → YES   (required for island reporting)
```

A preference with no matching field is reported as such, with the nearest real field — never
improvised.

**Phase 2 — execute (deterministic).**
- The delta, case hash, commands and PowerWorld build go into `manifest.json`.
- **Every worker replays the manifest itself.** Each parallel worker opens its own PowerWorld
  instance; an option set in the parent does not exist in the workers.
- Each option: read, write, read back, record before and after. A mismatch fails the run.
- The original case is never saved; variants run on fresh copies with their aux delta loaded and
  the case **solved after `LoadAux`** before anything is read.

**v1 methods:** AC power flow, DC power flow, N-1 contingency, OPF, SCOPF.

- **OPF and SCOPF need real cost data** (the auditor's opf condition 3) for the generators the
  study moves; otherwise the runner refuses. Area/super-area OPF control and `GenAGCAble` are
  switches the runner sets only for the areas and units the engineer approved. It never sets a
  cost model.
- OPF: `InitializePrimalLP` then `SolvePrimalLP`, fail handler always given; results from
  `OPFSolutionSummary` (final cost is `LPOPFCostFunction:1`) and `Branch.LineLPUnenforceableMVA`.
- SCOPF: `SolveFullSCOPF(POWERFLOW|OPF)`; `SCOPFMaxOuterLoopItr` and the other `SCOPF*` options
  set through the configure phase like any other option. There is no inner-loop setting; a request
  for one is answered with `OPF_MaxLPIterations` as the nearest real field.
- **SCOPF has no dated end-to-end verification.** The first SCOPF run on a public case is its
  verification spike, and its result is written back to `references/powerworld-study-options.md`.
- **DC OPF / DC SCOPF** use `SolvePowerFlow(DC)` to enter DC mode (never the `DCPFMode` flag alone)
  and `CTG_CalculationMethod = DC`; the AC re-solve guard applies afterwards.

**N-1 engine:** OS-process parallelism as described in `concepts/parallel-contingency-solve.md`,
re-implemented self-contained in the kit — contingency set split into chunks, one PowerWorld
instance per worker, `CTGSkip` partitioning, pure-Python merge. Serial or parallel is chosen by case
size (the fixed per-worker open cost dominates on small cases); worker count from CPU and RAM
headroom, not core count; every instance the runner opens is `.exit()`-ed.

**Guards:**
- contingency coverage counted before a sweep (records vs lines plus two-winding transformers);
  `CTGAutoInsert` is not trusted without the count
- DC only via `SolvePowerFlow(DC)`, followed by an AC re-solve before any AC result is read
- islands reported with all three checks — dropped (`LoadMW`/`GenMW`), energized
  (`CTG_Options.Include`), structural (`DetermineBranchesThatCreateIslands`) — gated on MW only
  when the pocket carries MW

**Post-processing:**
- violations from `ViolationCTG` with an explicit field list: thermal, voltage, unsolved, islands
- rankings both ways: worst outages, and most-hit elements (the kit's severity method)
- a reduced set (contingencies that produced a violation, plus an LODF near-miss screen) saved as
  aux for fast repeat runs — **never used for a verdict**. The near-miss loading threshold is a
  runner parameter, recorded in the manifest; its default is set in the implementation plan.

**Output:** `results/<run>/manifest.json`, `scoreboard.csv`, `violations.csv`, `islands.csv`,
`rankings.csv`, `reduced_set.aux`, `REPORT.md`, and one status line to the engineer.

**Heartbeat (for run supervision, §8a).** While a run is live the engine rewrites
`results/<run>/heartbeat.json` at least once a minute: `state` (`running` / `finished` / `failed`),
contingencies done and total, ETA, failed chunks, unsolved so far, the count of `pwrworld.exe`
processes the run owns, and the time of the last completed solve. Written atomically (temp file,
then replace) so a reader never sees half a file. Watching a run means reading this file, never the
raw results.

## 6. network-visualizer

*Replaced the fix-reviewer on 2026-09-28.* A standalone reviewer grading AI-proposed fixes was the
awkward role; the useful one is the planner's question: *"here is my design — show me the network,
try it, try yours, and tell me which is better and why."*

**Triggers:** "visualize the network around …", "I want to connect this load / plant to that
substation — what happens?", "will it overload?", "compare my design with yours", "map the
violations".

1. **Map** the network N substation-hops around the site (default 5) with the existing
   `violation-map` engine — wrapped, not replaced.
2. **Measure the engineer's design(s)** exactly as given: N-0, then the **full** N-1 through the
   study-runner engine with one settings manifest, and all three island checks.
3. **Propose challengers** only when asked, 1–3, cheapest first from the kit's action menu
   (setpoints and controls before new devices), each labelled as the agent's proposal.
4. **Compare** every design on the same manifest in one scoreboard, and render a map with a
   Before / Engineer / Challenger switch.

**Guards (they carry what the reviewer existed for):**
- every design — the engineer's and the agent's — is measured on identical settings and the full
  contingency set; a design measured on fewer outages is never compared with one measured on all;
- the comparison is engine numbers only; the agent states **where the engineer's design wins**, and
  never declares a winner without the table;
- the agent never edits the engineer's design, and never saves over the original case.

**Engine work this needs** (none of it exists yet): a *large-load* candidate kind (today: shunt,
line, setpoint edit); the **thermal view** `violation-map` lists as not built; and full-N-1
measurement of candidates through the study-runner engine (today the voltage page measures listed
outages and the radial page bridge outages only).

## 7. schema-librarian

Answers "which object, field, command?" in a few lines, with a confidence tag.

- **Sources, in order:** `references/powerworld-study-options.md` (curated, provenance-tagged) →
  `references/powerworld-option-objects-v25.md` and `powerworld-object-fields-v25.xlsx` (exact
  fields, keys, required fields, writability) → `references/powerworld-study-commands.md` (syntax).
- **Answer shape:** object, key fields, required fields, the field(s), a write snippet, and one of
  *verified on a live case / documented / schema-only*.
- **Used by** the user directly and by the runner's configure phase.
- Never touches a case; never states a field name absent from the export.

## 8. Walkthrough: "a bus sits at 1.06 pu, what fixes it?"

1. Engineer forms hypotheses from the kit's pages (line charging on a stub, an LTC holding the
   wrong side, a capacitor left on, a generator setpoint).
2. case-auditor (base profile) returns the neighbourhood diagnosis. Nothing changes.
3. Engineer turns it into candidates, cheapest first (zero-device setpoint and control fixes before
   new devices).
4. study-runner measures each candidate on a copy — N-0, then N-1 on survivors — and returns a
   scoreboard.
5. network-visualizer maps the neighbourhood and puts the engineer's pick beside its own
   challenger on the full N-1, same settings, with a Before / Engineer / Challenger switch.
6. Engineer decides from the side-by-side scoreboard.

## 8a. Run supervision — a mode, not an agent

Long runs — a full N-1 on a large case, a TimeStep year — take hours. Today the engineer starts one,
trusts it, and finds out the next day whether it finished. Run supervision lets the engineer
follow a run from anywhere and make each round's decision from a phone.

It is a **mode of the main session** (a skill, `run-supervisor`), not a subagent: a subagent lives
only while its parent task runs, so it cannot wait hours for a reply or reach a phone. The main
session can — it runs the study in the background, wakes on events rather than polling, sends push
notifications, and can be opened from the Claude mobile or web app through Remote Control.

1. **Launch** the study-runner engine in the background with an approved manifest.
2. **Watch** `heartbeat.json`, waking on events, not on a timer.
3. **Alarm** (push notification) on: no progress for N minutes (default 15), any failed chunk,
   an unsolved count above the manifest's threshold, more `pwrworld.exe` processes than workers
   (a leak), the run failing, and the run finishing.
4. **Round digest** when a round finishes: the scoreboard's headline, the worst offenders, islands,
   and two to four concrete next moves — e.g. "measure the three cheapest candidates on the worst
   corridor", "map the islanded pocket with the network-visualizer", "stop here".
5. **The engineer decides** from the phone. The answer is a choice among the offered moves or free
   text; nothing proceeds without it — no auto-approval, same as every other gate in this design.
6. The chosen move launches the next round (study-runner or network-visualizer) and supervision
   continues.

Portability: the engine and the heartbeat file are plain files any harness can read. Push
notifications, background watching and Remote Control are Claude Code features; other harnesses get
the heartbeat and the digest, not the phone.

## 9. Kit layout

```
agents/case-auditor.md  study-runner.md  network-visualizer.md  schema-librarian.md
skills/case-audit/SKILL.md      engine/  tests/
skills/study-runner/SKILL.md    engine/  tests/
skills/violation-map/SKILL.md   engine/  (exists; extended in Plan 4)
skills/schema-lookup/SKILL.md
skills/run-supervisor/SKILL.md  (a main-session mode; no agent file)
```

Engines are Python on esapp, matching `skills/violation-map/engine/`.

## 10. Testing

All on public synthetic cases.

| test | passes when |
|---|---|
| auditor, clean case | READY for each profile the case supports |
| auditor, seeded defects (strip PFW from 3 units, zero a regulated bus, set a cost model to None) | reports exactly those, nothing new |
| auditor read-only | AST test finds no `SaveCase` / case write in the engine |
| runner, serial vs parallel | identical violations and islands |
| runner, manifest replay | two runs of one manifest give identical results |
| runner, read-back | a write that does not stick fails the run loudly |
| runner, coverage | a deliberately incomplete contingency set fails the guard |
| runner, OPF gate | on a case with no cost data, OPF and SCOPF are refused, not run |
| runner, OPF | on a case with cost data, OPF returns a solved status and a final cost, and binding lines match `LineLPUnenforceableMVA` |
| runner, SCOPF | converges within `SCOPFMaxOuterLoopItr`; changing that option changes the recorded loop count; result recorded as the dated verification |
| visualizer, parity | two designs measured in one comparison share one manifest hash and one contingency count |
| visualizer, side effects | a design that clears the target but creates a new overload shows the new overload in the scoreboard |
| runner, heartbeat | during a run the heartbeat advances; a killed worker shows up as a failed chunk within one heartbeat interval |
| supervisor, stall | a run whose heartbeat stops advancing raises the stall alarm after the configured interval |
| supervisor, gate | the next round never launches without an engineer's answer |
| visualizer, large load | adding a load candidate changes N-0 flows and appears on the map's Before/Engineer switch |
| librarian | known lookups (shunt keys, island reporting, SCOPF outer loops, no SCOPF inner loop) answered correctly with the right confidence tag |

## 11. Build order

0. Prerequisites: sync the kit's `concepts/parallel-contingency-solve.md` (missing the rule to
   `.exit()` instances you own) and `methods/reading-violationctg.md` (still says islanding is
   undetectable).
1. schema-librarian — smallest, reads pages that already exist, and the runner depends on it.
2. case-auditor — base, timestep, opf profiles.
3. study-runner — ACPF, DCPF, N-1, then OPF and SCOPF (behind the auditor's opf gate).
4. network-visualizer — large-load candidate, thermal view, full-N-1 comparison through the study-runner engine.
5. run supervision — the `run-supervisor` mode over the runner's heartbeat; after Plan 3, because it
   supervises the runner's runs.

## 12. Out of scope for v1

Transient stability, GIC, unit commitment, an n1 audit profile.

## 13. Open questions

- Which public synthetic cases serve as fixtures: one without PFW models or cost data, one with
  PFW models (the time-step demo's case), one with cost data if any public case carries it.
- Whether the kit may redistribute PowerWorld's field export and a digest of the aux-file-format
  document; this decides whether the librarian's sources ship or are fetched by the user.
- Does PowerWorld/SimAuto keep running with the PC locked, or the user logged out? Run supervision
  assumes the machine stays up for hours; test this before building Plan 5.
- ~~Plugin agent discovery~~ — answered 2026-09-28: `agents/` in the kit is loaded
  (`claude --plugin-dir <kit> plugin details powerworld-hivemind`, Claude Code 2.1.284).
