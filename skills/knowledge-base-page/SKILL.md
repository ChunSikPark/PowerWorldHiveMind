---
name: knowledge-base-page
description: Write a new page into this knowledge base, or fix one that does not conform. Use when the user wants to record something they learned - a PowerWorld behaviour, a method that worked, a failure mode, a decision - as a page in concepts/, methods/, references/ or demos/. Also use when a page write was refused and needs fixing, or when asked to check, audit or lint pages.
---

# Writing a page into this knowledge base

This repo is a knowledge base you are expected to **grow**, not just read. A
session that worked something out and left it in the chat has thrown it away.

The schema below is not taste. It was derived by measuring the 57 pages this
repo ships, and `kb_page.py` enforces it. **The checker is authoritative** — if
this file and the checker ever disagree, the checker is right and this file is
stale.

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
Both lists are closed — the checker refuses anything else. If you genuinely
need a new value, add it to `TYPES`/`DOMAINS` in `kb_page.py` **and** say so,
rather than bending the page.

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

## Check before you claim it is done

```bash
python skills/knowledge-base-page/kb_page.py check concepts/your-page.md
python skills/knowledge-base-page/kb_page.py audit      # the whole repo
python skills/knowledge-base-page/kb_page.py rules      # the rule table
```

`check` exits 1 on a REFUSE and prints the rule id and the offending text.
Warnings do not fail it. **Run it and paste the output** — "it looks right" is
not evidence.
