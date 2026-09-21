# knowledge-base-page

The skill that writes pages into this knowledge base, plus the checker that
refuses the ones that do not conform.

## Files

| File | What it is |
|---|---|
| `SKILL.md` | the skill — filing tree, page shape, links, bookkeeping, what must not go in a page |
| `kb_page.py` | the checker; refuses, does not advise |
| `test_kb_page.py` | one must-catch and one must-pass case per rule |

## Commands

```bash
python skills/knowledge-base-page/kb_page.py check <page.md>
python skills/knowledge-base-page/kb_page.py audit [--root <repo>]
python skills/knowledge-base-page/kb_page.py rules
python skills/knowledge-base-page/test_kb_page.py
```

`check` exits 1 when a REFUSE fires, 0 otherwise. Warnings never fail it.

## The rules, and why each is the level it is

Every REFUSE was derived by measuring the pages this repo ships. The discipline
is one line:

> **A rule ships as REFUSE only if every page already in the repo passes it.**

`links` is the exception that proves the rule needs a second clause. All 57
shipped pages have zero dangling links, so by the letter of the discipline it
qualified as a REFUSE — but that measured a *finished* corpus and then gated
the *transition*. A page written before the pages it links to dangles through
no fault of its own, and two new pages linking to each other could never both
be written. So: **a rule is a REFUSE only if a page can satisfy it at the
moment it is written**, not merely once everything around it exists.

A rule that even one shipped page fails is a WARN. A checker that refuses the
repo's own pages is wrong about the repo, not about the page.

| Rule | Level | Measured basis |
|---|---|---|
| `encoding` | REFUSE | decode failure or an embedded U+FEFF |
| `frontmatter` | REFUSE | 57/57 carry `type`, `domain`, `aliases`, `tags` |
| `enum` | REFUSE | `type` ∈ 5 values, `domain` ∈ 3 — 57/57 |
| `listshape` | REFUSE | `aliases`/`tags` are bracketed lists — 57/57 |
| `sections` | REFUSE | Abstract → Connections → Content — 57/57 |
| `links` | WARN | 360 distinct link targets over 521 instances, 0 dangling |
| `orphan` | REFUSE | every page carries ≥1 outbound link — 57/57 |
| `linkfloor` | WARN | ≥2 links holds for only 55/57 |
| `index-row` | WARN | an `index.md` row holds for only 55/57 |
| `size` | WARN | a length signal, not a limit |

**`encoding` short-circuits.** When a page fails to decode, `check_page`
returns that finding alone and runs no other rule. A page with a BOM *and*
four other faults reports one fault, and fixing the BOM reveals the rest.
A clean result straight after an encoding fix is not yet a clean page —
run the check again.

Re-measure after any schema change:

```bash
python skills/knowledge-base-page/kb_page.py audit
```

Zero refusals is the invariant. If a change to the rules refuses a shipped
page, either the rule is wrong or the page is — decide which, and say so.

## Scope: what is a page

- **Content pages** live in a folder: `concepts/`, `methods/`, `references/`,
  `demos/`.
- **Root-level `.md` files are meta** — `README.md`, `AGENTS.md`, `index.md`,
  `CHANGELOG.md` and the rest. They are skipped.
- These hold machinery or build output, not pages, and are skipped wherever
  they appear: `commands/`, `skills/`, `dist/`, `assets/`, `scripts/`,
  `raw/`, `node_modules/`, `__pycache__/`, `.git/`, `.github/`, `.obsidian/`.
  The list is `SKIP_DIRS` in `kb_page.py`.

The meta test is a *shape* rule (`len(rel.parts) == 1`), not a list of
filenames, because a list is a second source of truth that drifts.

It is applied in **both** `check_page` and `audit_pages`, so a caller that
checks one page sees the same scope the audit does. `test_kb_page.py` has a
case pinning both layers.

## Changing the schema

Adding a `type:` or `domain:` value means editing `TYPES`/`DOMAINS` in
`kb_page.py`, adding a test case for it, and re-running the audit. Do not bend
a page to fit a list that should have grown; do not grow the list to excuse a
page that is simply wrong.
