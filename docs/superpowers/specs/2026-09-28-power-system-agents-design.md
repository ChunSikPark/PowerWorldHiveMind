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
| fix-reviewer | subagent, read-only on the original | independently re-measures a claimed fix: PASS / REJECT |
| schema-librarian | subagent, cheap model, read-only | "which object, field, command — and how sure?" |

There is no separate planner agent: power-system judgment belongs in the context the user is
talking to.

**Portability:** subagents are a Claude Code feature. Every role is therefore a **skill plus an
engine** first; the agent file is a thin wrapper that runs the skill in a fresh context. Codex and
Gemini users of the kit get the skills and engines and lose only the context isolation.

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

**v1 methods:** AC power flow, DC power flow, N-1 contingency. OPF and SCOPF follow once the
auditor's opf profile exists; SCOPF has no dated end-to-end verification yet.

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

## 6. fix-reviewer

1. Start from a clean copy of the original case and apply only the claimed fix.
2. Run the **full** N-1 through the runner with the same manifest settings as the baseline.
3. Check: the target violation is gone; no new violations elsewhere; no new islands or unsolved
   contingencies; known traps (e.g. a switched shunt shipped as `Continuous` that re-breaks the fix).
4. Return **PASS / REJECT** with before/after counts and anything new.

It never proposes a fix, edits the case, or passes something it did not measure.

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
5. Engineer picks one; the existing `violation-map` skill can draw before/after.
6. fix-reviewer re-measures it on the full N-1 and returns PASS or REJECT.

## 9. Kit layout

```
agents/case-auditor.md  study-runner.md  fix-reviewer.md  schema-librarian.md
skills/case-audit/SKILL.md      engine/  tests/
skills/study-runner/SKILL.md    engine/  tests/
skills/fix-review/SKILL.md
skills/schema-lookup/SKILL.md
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
| reviewer | a candidate that fixes the target but creates a new violation is REJECTed |
| librarian | known lookups (shunt keys, island reporting, SCOPF outer loops, no SCOPF inner loop) answered correctly with the right confidence tag |

## 11. Build order

0. Prerequisites: sync the kit's `concepts/parallel-contingency-solve.md` (missing the rule to
   `.exit()` instances you own) and `methods/reading-violationctg.md` (still says islanding is
   undetectable).
1. schema-librarian — smallest, reads pages that already exist, and the runner depends on it.
2. case-auditor — base, timestep, opf profiles.
3. study-runner — ACPF, DCPF, N-1.
4. fix-reviewer.

## 12. Out of scope for v1

Transient stability, GIC, OPF/SCOPF execution (next release), an n1 audit profile, a
visualisation adapter from runner output to `violation-map`.

## 13. Open questions

- Which public synthetic cases serve as fixtures: one without PFW models or cost data, one with
  PFW models (the time-step demo's case), one with cost data if any public case carries it.
- Whether the kit may redistribute PowerWorld's field export and a digest of the aux-file-format
  document; this decides whether the librarian's sources ship or are fetched by the user.
- Plugin agent discovery: confirm that agent files placed in the kit are picked up when the kit is
  installed as a plugin, before building on it.
