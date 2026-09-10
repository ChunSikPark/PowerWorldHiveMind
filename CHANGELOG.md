# Changelog

## Unreleased

- **The plugin's skill could not find its own pages.** `skills/powerworld/SKILL.md` sent the
  agent to `concepts/`, `methods/`, `demos/` and `references/` as bare relative paths, so an
  installed plugin — which lives under `~/.claude/plugins/cache/…` — had the agent searching
  the user's working directory instead. All 44 pages shipped correctly; nothing could find
  them. The skill now resolves `${CLAUDE_PLUGIN_ROOT}` first and anchors every path to it,
  with a fallback for agents that do not set that variable. Verified by installing the
  plugin and reading back its component inventory and cached page count.
- **New `/powerworld-setup` command** (`commands/powerworld-setup.md`): finds Python,
  installs `esapp`, `TeamOverbyeWeather` and `pywin32`, runs preflight checks 1–4, reports
  the Simulator build date, and reads the failure back in plain language — including that
  the SimAuto add-on is licensed separately and no code change fixes it.
- **`GETTING-STARTED.md` rebuilt around the plugin install.** Six steps to five: the ZIP
  download and the folder-picker are gone from the main path, replaced by two `/plugin`
  lines and `/powerworld-setup`. Both survive as a manual route for agents without a plugin
  system. `README.md`'s install section leads with the same route.
- **Codex plugin support**: adds a portable `plugin.json` at the repo root and
  `.agents/plugins/marketplace.json`, per the agent-plugins.org 1.0.0 schema, which Codex
  discovers via `codex plugin marketplace add`. Manifests validate against the published
  schema but are **untested against a released Codex build**; both docs say so.

## 0.1.5 — 2026-09-09

**Example cases are now referred to by neutral names** — `Synth2k`, `Synth40`, `Synth8k`,
`Synth9k` — instead of by the specific model each measurement was taken on. Roughly a
hundred references across seventeen pages. Every figure is unchanged: the bus counts, the
row counts, the timings and the violation numbers are the same measurements they always
were. What is gone is which model produced them, which was never something a reader could
use.

The export now refuses to publish a page containing a name from a maintained list, so this
cannot drift back in one page at a time. It is the third check on the same boundary as the
existing private-path and personal-name checks, and it caught five references the manual
pass had missed, including two hidden in page metadata.

## 0.1.4 — 2026-09-09

- **The Claude Skill (`skills/powerworld/SKILL.md`) is rewritten** to match `AGENTS.md`:
  search the four content directories first and read the page you find in full, rather
  than starting at `index.md`. It also gains a defect-reporting section — how to hand the
  user a pre-filled issue link when a page is wrong or missing, and why the text must be
  shown first, since a traceback can carry case filenames and substation names into a
  public tracker.
- **Three dangling `[[wikilinks]]` removed** from code comments in
  `concepts/powerworld-simauto.md`, `methods/save-powerworld-case.md` and
  `methods/new-device-contingency-aux.md`. They pointed at pages that exist only in the
  private source vault. The export now fails on this shape instead of shipping it.
- `dist/` bundles rebuilt.

## 0.1.3 — 2026-09-09

The instruction layer. Nothing about PowerWorld changed; what changed is whether your
agent ever sees the rules that govern the 41 pages.

### The bug: instructions detached from the knowledge

`AGENTS.md` holds everything that makes this kit work — search before you reason, read
the right page in full, cite the page or say there is not one. Codex, Cursor, Copilot and
Windsurf load that file natively. Claude Code does not: it reads `CLAUDE.md` and nothing
else. Ours said "Instructions for agents live in AGENTS.md. Read that file" — a markdown
link, which loads nothing. So every Claude Code user got the knowledge base with the
rules detached from it, and the symptom looked like an agent ignoring instructions it had
in fact never been shown.

Fixed with the documented `@AGENTS.md` import. That fix was luck: nobody had ever written
down which tool reads which file, so nothing could have caught it.

- **`GEMINI.md` is new.** Gemini CLI reads `GEMINI.md` by default and reaches `AGENTS.md`
  only if you set `context.fileName` in your own settings — which a kit cannot do for you.
  It had the same detached instructions, and the AGENTS.md standard's own supporter list
  says Gemini CLI is supported, which is how it stayed invisible. The file is generated
  from `AGENTS.md` at export; edit `AGENTS.md`.
- **The README now says which file your agent actually reads**, per vendor, verified
  against each vendor's own documentation on 2026-09-09.
- **The export now fails** if a listed vendor has no shim, if an import shim has no real
  import, if a generated copy has been hand-edited, or if `AGENTS.md` grows past the
  32 KiB Codex truncates at without saying so.

## 0.1.2 — 2026-09-08

One troubleshooting entry, from watching the same install go wrong twice. Both people
downloaded the Claude installer, never ran it, and reported that Claude was missing.

- **Step 3 says to run the installer**, not only to download it, and says that Claude
  creates no desktop icon — an empty desktop is not evidence the install failed. The fix
  is Start, type `Claude`, right-click, **Pin to taskbar**.
- **"I downloaded Claude but I cannot find it"** is now a troubleshooting entry, with both
  causes, because from the outside they look the same.

## 0.1.1 — 2026-09-08

Setup and navigation. Nothing about PowerWorld changed; what changed is how you install
this and how an agent finds the right page inside it.

### Getting started, rewritten

Feedback from someone installing the kit with no Python and no GitHub background: they got
as far as "start your assistant in the folder you unzipped" and stopped. The old page never
said what to actually start, and it listed the Claude desktop app as a coding agent without
saying what to do with it.

- **The desktop app is now the documented route.** Click `Code`, click the folder button,
  choose `Open folder...`. Three screenshots at the three places people got stuck. No
  terminal, no launch command, no folder path to type.
- **The terminal instructions moved to an appendix** for people using a command-line agent,
  and now link Anthropic's terminal guide rather than re-explaining it.
- **Two prerequisites that were missing entirely:** Claude Code needs a paid plan, and on
  Windows it needs Git installed. Both used to fail late and look like bugs.
- **Your agent now installs the Python packages** as part of the first question, instead of
  a separate `pip` step.
- **One word for one thing.** The page used "AI assistant", "AI coding assistant" and
  "agent" interchangeably, which was the literal question the tester asked. It is "agent"
  throughout now.
- **If you have no paid plan**, the `dist/` bundles and what you lose by using them are
  documented rather than implied.

### Navigation, measured and rewritten

`AGENTS.md` used to send an agent to `index.md` first, then to a task-routing table. Both
lost a measurement: 48 agents, 16 questions with human-written answers, scored against
ground truth. Searching the page text found the right page 10 times out of 16, the routing
table 8, `index.md` 7.

- **Search all four content directories first**, with both the plain-English phrasing and
  the identifier, ranked by how many terms land. Concrete forms given for Claude Code,
  ripgrep, Cursor and PowerShell.
- **`index.md` and the routing table are now disambiguators, not routers.** Both name
  topics, and a topic is coarser than a page.
- **A false-absent rule.** "Not in the knowledge base" is not a conclusion you may reach
  from a routing-table miss. In the same measurement the table produced two confident
  "not here" answers on pages it does route.
- **The read budget is about breadth, not depth.** The old wording capped pages opened,
  which agents read as permission to stop halfway through the right page. Once a page is
  the right page, read all of it.

### Removed

- **`install.ps1` and `install.sh` are gone.** A PowerShell script that strangers are asked
  to run makes a repository look hostile regardless of what it does. Install by unzipping
  the folder, or through your agent's own plugin mechanism.

### Pages updated

- `concepts/esapp.md`
- `concepts/powerworld-simauto.md`

## 0.1.0 — 2026-08-27

First release.

A markdown knowledge base that makes a coding agent competent at PowerWorld Simulator
automation. 41 linked pages, no software to run.

### What it covers

- **Driving PowerWorld from Python** with `esapp` — opening cases, reading and writing
  data, solving power flow, saving
- **Modifying cases** — adding buses, branches, loads and generators; applying a
  dispatch; reclassifying branches as transformers
- **Contingency analysis** — building sets, reading violations, ranking devices by
  severity, generating filter and contingency `.aux` files
- **PowerWorld's weather features** — the PWW format, TimeStep simulation for hourly
  renewable output, and fetching `.pww` files with the TeamOverbyeWeather client
- **198 SCRIPT actions**, organized by task rather than by manual chapter

### Demos

Five worked runs on a real 37-bus case. Every number is from an actual execution, and
the failures were left in deliberately:

- `demos/comparing-planning-cases.md` — diffing two vintages of one system (2016 vs 2024
  summer peak): 691 new branches, 199 new generators, guarded against renumbering and
  endpoint-swap artifacts, then a contingency set for only the new devices. The naive
  solve reports 240 violations; only 32 belong to the plan
- `demos/violation-remediation.md` — the full study: 12 N-1 violations diagnosed down to
  a single corridor, five candidate reinforcements tested independently and ranked. Two
  of the five made the system worse, including the one an engineer would reach for first
- `demos/adding-a-device.md` — three `CreateData` attempts that raised no exception and
  created nothing, then the documented fix, then the N-1 comparison it enables
- `demos/power-flow-and-sensitivities.md` — AC, DC, LODF, PTDF, including the `1e8`
  sentinel and an error whose obvious recovery fails the same way
- `demos/contingency-and-aux.md` — N-1 from scratch, then generating and loading an aux
- `demos/timestep-and-pfw.md` — the PFW-model check that decides whether a case can run
  a weather study at all
- `demos/start-here.md` — one-line prompts, so you never need to know which page covers
  what

### Version awareness

Preflight now reports the Simulator build date on every run, so the version is on record
before any analysis is written. `concepts/version-requirements.md` covers three ways to
detect your version, what this kit was verified against, and the behaviours that shift
silently between releases.

Verified against **Simulator 24, build 24.2026.7.22**: 13 of 14 feature areas confirmed
working (the fourteenth was a prerequisite error on an empty case, which is correct
behaviour, not a failure).

### Error handling

`methods/handling-errors.md` sorts failures into three tiers: fix silently (missing
packages, wrong access paths), fix and mention (a recovery that changes the answer's
meaning), or stop and ask (SimAuto licence, destructive actions, real modelling
decisions).

It also covers what no exception handler catches: PowerWorld frequently accepts a
malformed request, reports success, and does nothing. Seven verified silent failures are
tabulated with a guard for each. The rule is to assert the *effect*, never the absence of
an error.

### Install

```bash
git clone https://github.com/ChunSikPark/PowerWorldHiveMind.git
```

- **Claude Code:** `/plugin marketplace add ChunSikPark/PowerWorldHiveMind`
- **Any other project:** copy the cloned folder in as a subdirectory — it is plain
  markdown, with nothing to build or run
- **ChatGPT / claude.ai:** upload from `dist/` — a Claude Skill zip, a single-file
  bundle, or split files for Custom GPT knowledge

### Verification at release

- 119 Python code blocks checked against the installed `esapp` 0.1.3 — 0 invalid API
  references
- 0 dead internal links, 0 private paths, 0 personal names
- Five build gates: code integrity, link resolution, index completeness, private paths,
  personal names
- The preflight script was extracted from the published markdown of a fresh public clone
  and run end to end: 5/5 checks passed against a real case

### Known limitations

- **Cold-agent navigation: validation in progress.** The traversal protocol is designed
  so a fresh assistant reads three to five pages before writing code, and the acceptance
  criterion is fewer than 8 of 41. That has not been measured yet. The test is defined in
  `demos/start-here.md` and runs against the public clone; results will land in a
  subsequent release. Until then, treat the page-count claim as a design target rather
  than a measured result.
- **Scope is PowerWorld automation.** Contingency analysis fundamentals, OPF
  formulation, PV/QV theory, transient stability theory, and weather science such as
  dynamic line ratings are deliberately out.
- **Some claims are marked UNVERIFIED** in the reference pages, inherited from the source
  material. They are labelled rather than removed, so unverified content stays
  distinguishable from verified content.
- **PowerWorld automation requires a separately licensed SimAuto add-on.** Fetching and
  inspecting weather data is the only part that works without it.
