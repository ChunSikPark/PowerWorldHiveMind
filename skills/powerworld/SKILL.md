---
name: powerworld
description: "Use when working with PowerWorld Simulator, .pwb case files, SimAuto, or the esapp Python package - opening or modifying cases, solving power flow, adding buses/lines/generators, applying a dispatch, contingency analysis and violation reports, saving cases, and PowerWorld SCRIPT/aux actions. Also covers PowerWorld's built-in weather features: PWW weather files, TimeStep simulation for hourly renewable generator output, and fetching the .pww files those need via the TeamOverbyeWeather client. Also fires on power-system study work phrased without any tool name: overloaded or heavily loaded branches, N-1 violations and what caused them, comparing two planning cases or vintages, what a transmission plan builds, testing whether a new line or reinforcement helps, hourly wind and solar output from weather, and applying a dispatch."
---

# PowerWorld expert

A knowledge base of PowerWorld Simulator automation. Most PowerWorld mistakes are silent;
this records them.

## Where these pages live

Every path on this page — `concepts/`, `methods/`, `demos/`, `references/`, `index.md`,
`AGENTS.md` — is relative to the **kit root**, never to the user's working directory.

Installed as a Claude Code plugin, the kit root is `${CLAUDE_PLUGIN_ROOT}`. Resolve it once
at the start of the session and prefix every path below with it —
`${CLAUDE_PLUGIN_ROOT}/methods/preflight-powerworld.md` — and scope every search to it.

Anywhere else (Codex, Cursor, or the kit copied into a project), the kit root is whichever
directory holds `AGENTS.md` alongside the four content directories. That is usually the
project root or a `PowerWorldHiveMind/` subdirectory of it. Find it once, then use it the
same way.

**Searching the working directory instead of the kit root is the one failure this skill
cannot survive** — it fires, sends you to a page, and the page is not there. If a path
below does not resolve, you have the wrong root. Find the root; do not conclude the page
is missing.

## Consult it before you reason

**Do not work PowerWorld problems out from first principles or from general API
intuition.** PowerWorld fails silently — it accepts a wrong call, reports success, and
returns a wrong answer. Nothing will prompt you to look something up.

- Open the relevant page **before** writing code, and say which page you followed.
- Code failed? Re-read the page before inventing a fix. The page usually already warned you.
- No page covers it? **Say so explicitly** and mark the answer as unsourced. Do not present
  a guess with the confidence of sourced work.
- Believe a page is wrong? Say so with evidence. Never silently override it.

## Before anything else

**Run the preflight** in `methods/preflight-powerworld.md` (under the kit root). Five
seconds, and it tells you whether this machine can drive PowerWorld at all. Record the
Simulator build date it prints — behaviour shifts silently between versions
(`concepts/version-requirements.md`).

A preflight failure is a fact about the machine, not a bug in your code. Report which check
failed and stop. In particular the **SimAuto add-on is licensed separately from Simulator**,
so a healthy-looking installation can still run no automation at all.

## Finding the right page

**Search the four content directories first** — `concepts/`, `methods/`, `demos/`,
`references/`, all under the kit root resolved above. Search page text, not the catalog.
Put several terms in one pass and include both the plain-English phrasing and the
identifier it maps to ("save the case" *and*
`SaveCase`), then rank a page by how many terms land on it. Measured over 48 agents on 16
questions: search found the right page 10 times out of 16, the routing table 8, starting from
`index.md` 7.

Once you have the right page, **read its `## Content` in full.** The limit is on **breadth,
not depth** — opening eight pages while hunting means your search terms were wrong, not that
you should read less of the page you found.

`AGENTS.md` at the kit root carries the full 22-row task-routing table and the rest of the
ladder. Use it and `index.md` as disambiguators when search comes back thin, never as the
first move — both name topics, and a topic is coarser than a page.

**Never conclude "not in the knowledge base" from a routing-table miss alone.** Report an
absence only after searching all four directories on both phrasings.

## Run studies, not queries

The user rarely wants a number; they want the work it is for. Diagnose before proposing, and
test before recommending. Group symptoms into causes, then test candidate fixes on a fresh
case each and measure — reinforcing a network can make it worse, and reasoning will not tell
you which. Track count and severity separately; they disagree. Say what you rejected and what
you did not save. See `demos/violation-remediation.md`, where 2 of 5 plausible reinforcements
degraded N-1.

## Rules that fail silently

Apply these to every line of PowerWorld code you write. None raises an exception; each just
produces a wrong answer.

1. **Keep key fields** (`BusNum`, `GenID`, circuit id) in any DataFrame written back, or the
   write is a no-op that reports success.
2. **`pw[Obj, field] = values` is positional over the whole table.** Assigning to a filtered
   subset writes nothing.
3. **Call the named esapp method, not a hand-written script string.**
   `pw.esa.TimeStepDoRun()`, never `pw.esa.RunScriptCommand("TimeStepDoRun;")` — esapp 0.2.1
   wraps 310 SCRIPT commands. You get a typed signature and correct argument building, but
   the real reason is that a hand-written string is a call site nobody can patch when
   PowerWorld changes that command's syntax. Reach for `RunScriptCommand` only where no
   wrapper exists (~41 actions, mostly oneline/GUI and dialogs). Check esapp's own method
   list before concluding a wrapper is missing, and leave a comment saying why.
4. **`SaveCase` is the exception.** It is a COM method, not one of the 310, and
   `pw.esa.SaveCase(...)` is a silent no-op — returns success, writes nothing. Use the script
   form and assert the file exists:
   `pw.esa.RunScriptCommand(f'SaveCase("{out}", PWB);')` (exactly two parameters).
5. **A DC solve always reports zero mismatch.** Check the generation schedule against load
   directly; the slack bus hides a shortfall.
6. **Clear contingency results before solving.** They persist stale inside the `.pwb`.
7. **Absolute paths only.** Relative paths resolve against PowerWorld's working directory,
   not yours.
8. **Write `esapp`, not the standalone `esa`.** Same SimAuto underneath, better documented;
   do not mix the two in one script.

**Assert the effect, never the absence of an error.** PowerWorld accepts malformed requests,
reports success, and does nothing — count objects before and after.
`demos/adding-a-device.md` is a real run where three attempts silently created nothing.

When something does fail, `methods/handling-errors.md`. Fix missing packages and wrong access
paths yourself without narrating. Stop and ask only for a missing SimAuto licence, a
destructive action, or a real modelling decision.

## When this base is wrong or missing, report it

Two cases are worth a bug report, and both are rare enough to be signal:

- **No page covers it** — but only after you have searched all four content directories on
  both the plain-English and the identifier phrasing. A routing-table miss is not enough.
- **A page is wrong** — you followed it, the code failed or returned a wrong answer, and
  re-reading did not resolve it. Name the page and say what PowerWorld actually did.

**Offer the user a report; never file one silently.** Compose a pre-filled link and hand it
over — they click, review on GitHub, and submit:

```
https://github.com/ChunSikPark/PowerWorldHiveMind/issues/new?title=TITLE&body=BODY&labels=LABEL
```

URL-encode both fields. Title as `Page wrong: methods/<page>.md` or `No page: <topic>`;
label `page-defect` or `missing-page`. In the body put the page you followed, what you ran,
what PowerWorld did instead, the Simulator build date from preflight, and the esapp version.
Keep it short — an over-long URL will not open.

Where `gh` is installed and authenticated, `gh issue create --repo
ChunSikPark/PowerWorldHiveMind --title "..." --body "..."` files it directly. Still show the
user the exact text first.

**Show the text before anything is submitted.** A traceback can carry case filenames, bus
numbers, and substation or utility names, the tracker is public, and the cases this kit
drives are often CEII or otherwise restricted. State that it will be public, and let the
user edit it or decline.

## Scope

Covers PowerWorld automation, including its PWW/TimeStep weather features. Does **not** cover
contingency analysis fundamentals, OPF formulation, PV/QV curve theory, transient stability
theory, or weather science such as dynamic line ratings and IEEE 738 — say so rather than
improvising.

Cite which pages you used, so a wrong answer is traceable to a page that needs fixing.
