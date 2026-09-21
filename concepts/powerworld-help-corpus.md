---
type: dataset
domain: tooling
aliases: [powerworld-webhelp, webhelp, simulator-help, PowerWorld-Help, help-corpus]
tags: [powerworld, documentation, retrieval, agent-workflow, knowledge-base, simauto]
---

# PowerWorld help corpus

## Abstract

**The PowerWorld Simulator WebHelp, captured as 80 offline Markdown chapter files holding 1,670 topics —
and the reason you cannot navigate it by its own table of contents.** The manual is organised the
way the *program* is organised (ribbon tabs, dialogs, add-ons), so every research subject is split
across chapters that the contents page never puts side by side. Three splits bite repeatedly:
time-step work, switched-shunt/reactive work, and anything that has both a dialog and a script
command. A topic-level index that re-cuts the corpus by research domain lives outside the wiki;
this page is the *why*, the retrieval gotchas, and the one provenance rule the help system itself
states.

Read this before searching the help for anything. It costs less than one wrong grep.

## Connections

**Up:** [Home](../index.md) ·
**Across:** [aux-only-powerworld](aux-only-powerworld.md) (the field-name provenance rule this page confirms from a second
source), [aux-script-catalog](../references/aux-script-commands.md) (the SCRIPT action catalog, condensed from the *other* manual),
[esapp](esapp.md), [powerworld-simauto](powerworld-simauto.md) ·
**Distilled from this corpus:** [solver-mechanics-and-failure-modes](solver-mechanics-and-failure-modes.md),
[filter-expression-language](filter-expression-language.md), [simauto-output-shapes-and-discovery](simauto-output-shapes-and-discovery.md),
[raw-epc-roundtrip-traps](raw-epc-roundtrip-traps.md) — a sample of the content pages now carrying manual
material directly; each subject routing page below names its own full set ·
**Deeper:** [timestep-simulation](timestep-simulation.md), [gic](gic.md)

## Content

### What it is

An offline Markdown capture of `powerworld.com/WebHelp`, the Simulator manual. As captured
2026-09-18: **1,670 topics in 80 chapter files (~6.6 MB) and 3 PDFs.** Internal links are in good
order — measured on the pinned commit, **zero broken anchors**.

**But the figures are missing.** The chapters carry 1,120 `images/*.gif` references and the
repository contains no `images/` directory, so every figure reference is broken in a clone. The
corpus's own README describes 1,097 figures at 273 MB; they were never committed. Where a topic
explains itself with a block diagram — most of the dynamic-model catalog — the offline copy does
not carry the explanation. It ships a `manifest.json` (chapter list, sizes,
cross-reference graph) and a `toc.json` (the help system's own contents tree).

It is **the program's documentation, not a textbook.** It describes dialogs, fields and options.
Where it states theory it is brief and worth reading — the power-flow solution chapter is the
main place it does ([pw-power-flow](pw-power-flow.md) lists what) — but the bulk is reference material for a UI.

### Why its own categories cut the wrong way

The corpus groups its chapters into the manual's parts: *Getting Started*, *Viewing Case Data*,
*Contingency Analysis*, *Add-Ons*, *Transient Models*, and so on. Those are the program's
divisions. A research question crosses them:

- **Running a time-step study** spans four chapters — tool, script commands, programmatic entry
  point and batch engine ([pw-timestep-sim](pw-timestep-sim.md) names them).
- **Reactive support** — switched-shunt material is spread over the power-flow chapter, *both*
  object-property chapters (edit mode and run mode have separate pages for the same object), the
  contingency-options chapter (post-contingency shunt behaviour), the time-step chapter (shunt
  control time-step options) and the SVC control-mode topics, which sit in the appendix described
  below.
- **Anything with both a dialog and a command** — the dialog is documented in its feature chapter,
  the command that does the same thing is in the scripting chapter, and neither page is obliged
  to mention the other.

The practical consequence: **finding the feature chapter is not finding the answer.** Expect a
subject to live in three or four files and plan the read accordingly.

### The appendix that is not in the table of contents

Roughly 4% of topics — 67 in this capture — are reachable **only by cross-link**, never by the
contents tree. In the capture they are swept into a trailing "additional linked topics" chapter,
which is consequently a grab bag spanning half a dozen unrelated subjects under no useful
heading — each subject page flags its own stranded topics. This is real content, not scraps:
several of those pages are the only description of their mechanism anywhere in the manual.

**So a table-of-contents-shaped search misses them.** Grep the whole corpus, not the contents.

### The legacy-duplicate trap

The help ships current API pages *and* the version-9 pages for the same functions, with nearly
identical titles. A grep for a SimAuto function name returns both, and the old page will look
plausible. **Check the title for a version marker before trusting an automation page** — and
prefer the current chapter, which documents the typed and flat-output variants the legacy pages
predate.

### The field-name provenance rule, confirmed twice

[aux-only-powerworld](aux-only-powerworld.md) established that the Auxiliary File Format manual contains **no per-object
field catalog**. The WebHelp says the same thing about itself, explicitly: it names field variables
as the basis of every automation call, gives `GenMW` and `BusNum` as examples, and then states that
rather than list them, Simulator will **generate the list on demand from its Help menu**.

So there are two manuals and neither one holds the field names. The rule stands and now has two
sources: **verify a field name against the live schema — `esapp`'s field metadata, or
`GetFieldList` — never against prose in a manual.** A page that names a field is illustrating a
concept, not publishing a catalog.

### Roughly a tenth of the topics say nothing

**164 of the 1,670 topics (9.8%) carry no usable body.** 76 hold the capture's own marker
*"This topic has no body text in the source help file"* — the vendor's table of contents lists a
topic the vendor never wrote. The other 88 are under 150 characters, usually nothing but an
auto-correction block reading *"To be documented."*

They are concentrated in the dynamic-model chapters and **interleaved with fully-documented
models in the same file**, so nothing about a topic's position or title tells you which kind it
is. Every one costs a read to discover it is empty. A model name appearing in the manual is
therefore **not** evidence that the model is documented.

### Six copies of the release notes are 6% of the corpus

The manual's *"What's New"* topic appears **six times** in the capture and together those six
hold about **92k tokens — 6.2% of all body text in the corpus**, making them the largest topics
in it by a wide margin. They are version history, not reference material.

This generalises past this one corpus: **in a converted vendor manual, the largest topics are
usually the least useful ones.** Release notes, licence text and "what's new" pages are long,
highly duplicated, and answer no question anyone asks. Check a topic's size before opening it and
treat the big ones with suspicion rather than deference.

### What its AI-readiness scores actually measure

Scored with the `ai-readiness-audit` rubric (measured 2026-09-20, all chapter files), the corpus
lands around 60/100 overall, and **most of that gap is genre, not defect**. The heuristics flagged
*"instructions read as descriptive, not actionable"* on **every** file and *"no gotchas section"* on
every file; median imperative ratio across the corpus is **0.00**. That is what a reference manual
is. Its "undefined terminology" signal is also largely artefact — the detector counts `AND`, `NOT`,
`YES`, `ACOS` and model parameter names among hundreds of "undefined acronyms", of which only a
couple of dozen are real domain terms.

The lesson is about the measurement, not the manual, and it generalises to any scored corpus:
**a readiness rubric built for instruction docs will mark a reference corpus down for being a
reference corpus.** Three findings survive that correction and are real — oversized sections
(282 across the chapter files, the worst a single ~19.7k-token section), heavy duplication, and
the stub topics above. Those are worth acting on; the actionability score is not.
writing-ai-ready-claude-md already states the principle as a house rule — *"actionability is
genre-capped… respect the genre"* and *"don't score-game"* — and this is what it looks like at
corpus scale.

### Why this corpus is cheap to search

what-drives-hop-count measured that hop count tracks the **number of candidate pages** a search
works through, not total bytes — so splitting a long page in two can make retrieval *more*
expensive. This capture was built the same way round: chapters are cut at roughly 150 KB, each
sized to fit in one context window, and a chapter is split only when it exceeds that. 1,670 topics
compressed into 80 files is the shape that measurement predicts will retrieve cheaply, which is
consistent with the hop counts the kit posted in that benchmark.

The corollary for anyone tempted to "improve" it: **do not explode it into one file per topic.**
That is 1,670 candidates for the same bytes.

### What an index over it buys

Chapter-level categories already ship in the corpus manifest, so the value of re-indexing is
entirely at **topic level**: tagging each of the 1,670 topics with the research domain it serves,
plus cross-cutting tags that ignore chapter boundaries, so a domain question resolves to the two
or three files that actually hold it. That artifact is a repo index, not wiki content — the wiki
carries the reasoning, the repo carries the 1,670 rows.

---

*Ported from the research vault. Describes and routes over the PowerWorld Simulator help corpus; reproduces no manual text.*
