---
name: knowledge-base-page
description: Write something up as a page in this knowledge base, or edit a page already here. Use when the user wants to record, save, document, write up or keep what they just worked out - a PowerWorld behaviour, a procedure that worked, a failure mode, a gotcha - so it is not lost when the session ends. Also use when asked to add a page, fix a page, or check whether the pages still hang together (missing index rows, links pointing nowhere).
---

# Writing a page into this knowledge base

This repo is a knowledge base you are expected to **grow**, not just read. A
session that worked something out and left it in the chat has thrown it away.

The schema below is not taste. It was derived by measuring the pages this
repo already ships — every one of them follows it, with no exceptions. **The
pages are authoritative.** If this file and the pages ever disagree, read a
few pages and follow those; then fix this file.

## Before you write: does a page already cover it?

`grep` the four content folders on both the plain-English phrasing and the
likely identifier, several terms at once:

```bash
grep -rn -i "shunt\|Shunt\|GenMVRMax" concepts/ methods/ references/ demos/
```

Read a candidate's `## Abstract` first — it is written to tell you whether the
page is the right one. If it covers the ground, **edit that page instead of
adding a second one.** Two pages on one topic is the failure this base exists
to avoid.

## Where the page goes

| The thing you are recording | Folder | `type:` |
|---|---|---|
| What a thing *is* — a model, a concept, a failure mode | `concepts/` | `concept` |
| How to *do* a thing — a procedure that worked | `methods/` | `method` |
| A code/API surface reconstructed in detail | `references/` | `reference` |
| A worked run with real output, failures left in | `demos/` | `reference` |
| A package or tool's interface | `concepts/` | `tool` |
| A dataset's shape and quirks | `concepts/` | `dataset` |

## The page shape

Copy this. Every field is required.

```markdown
---
type: concept
domain: tooling
aliases: [the-slug, a-synonym, what-someone-would-search]
tags: [esapp, powerworld, contingency]
---

# Title In Sentence Case

## Abstract
One paragraph, written so a reader can decide from it alone whether to open the
rest. State the answer here, not a promise of the answer.

## Connections
- **Up:** [Home](../index.md)
- **Used in:** [some-method](../methods/some-method.md)
- **Across:** [a-concept](../concepts/a-concept.md)

## Content

### The actual material
```

**`type:`** is one of `concept`, `method`, `reference`, `tool`, `dataset`.
**`domain:`** is one of `tooling`, `cross-cutting`, `weather`.
Both lists are closed: every page in the repo uses one of these and nothing
else. If your page genuinely needs a new value, **say so explicitly** rather
than bending the page to fit or quietly inventing one — adding a value is a
decision about the whole base, not about your page.

**`aliases:`** and **`tags:`** are `[bracketed, lists]`. They may wrap across
lines. These are what `grep` finds later, so write the phrasings a future
reader would actually type, not a restatement of the title.

## Links are the point

A page with no outbound links is **refused** — it is unreachable and will never
be found again. Links are relative markdown, not wikilinks:

```markdown
[copper-plate](../concepts/copper-plate.md)     <- correct
[[copper-plate]]                                 <- not used in this repo
```

Every link target must exist on disk; a typo or a renamed page is a refusal.
Two or more links is the signal — one gets a warning.

## Bookkeeping: add the index.md row

`index.md` is the catalog. A new page adds **exactly one** row, in the table
for its folder, in the existing style:

```markdown
| [your-page](concepts/your-page.md) | One line on what it covers and when to open it. |
```

A page with no row warns rather than refusing, because two pages already ship
without one. Add it anyway — a page nobody can find is a page nobody reads.

## Check the corpus when you have finished

There is no checker to run. Writing the page correctly is the job, and the
shape above is the whole schema. Two questions are worth asking across all
the pages at once, though, because no amount of care on one page answers
them. Run these from the repo root when you have added or renamed pages:

```bash
# pages with no row in index.md
python -c "import pathlib;R=pathlib.Path('.');i=(R/'index.md').read_text(encoding='utf-8-sig');print([f'{d}/{p.name}' for d in ('concepts','methods','demos','references') for p in (R/d).glob('*.md') if f'{d}/{p.name}' not in i and p.stem not in i] or 'all pages indexed')"

# links that point at a file that does not exist
python -c "import pathlib,re;R=pathlib.Path('.');print([f'{p}: {t}' for d in ('concepts','methods','demos','references') for p in (R/d).glob('*.md') for t in set(re.findall(r'\]\(([^)#]+\.md)',p.read_text(encoding='utf-8-sig'))) if not (p.parent/t).exists()] or 'no dangling links')"
```

Paste what they print. If either returns a list, fix it before you say you
are done — a page nobody can reach and a link that goes nowhere are the two
failures that make a knowledge base stop compounding.
