# knowledge-base-page

The skill that writes pages into this knowledge base, plus the checker that
refuses the ones that do not conform.

## Files

| File | What it is |
|---|---|
| `SKILL.md` | the skill — filing tree, page shape, links, bookkeeping, what must not go in a page |
| `kb_page.py` | the checker; refuses, does not advise |
| `test_kb_page.py` | one must-catch and one must-pass case per rule |
| `hook_check.py` | an optional PreToolUse hook — **not wired by default** |

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

A rule that even one shipped page fails is a WARN. A checker that refuses the
repo's own pages is wrong about the repo, not about the page.

| Rule | Level | Measured basis |
|---|---|---|
| `encoding` | REFUSE | decode failure or an embedded U+FEFF |
| `frontmatter` | REFUSE | 57/57 carry `type`, `domain`, `aliases`, `tags` |
| `enum` | REFUSE | `type` ∈ 5 values, `domain` ∈ 3 — 57/57 |
| `listshape` | REFUSE | `aliases`/`tags` are bracketed lists — 57/57 |
| `sections` | REFUSE | Abstract → Connections → Content — 57/57 |
| `links` | REFUSE | 360 relative-link instances, 0 dangling |
| `orphan` | REFUSE | every page carries ≥1 outbound link — 57/57 |
| `linkfloor` | WARN | ≥2 links holds for only 55/57 |
| `index-row` | WARN | an `index.md` row holds for only 55/57 |
| `size` | WARN | a length signal, not a limit |

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
- `commands/`, `skills/`, `dist/`, `assets/` hold machinery, not pages.

The meta test is a *shape* rule (`len(rel.parts) == 1`), not a list of
filenames, because a list is a second source of truth that drifts.

It is applied in **both** `check_page` and `audit_pages`. That matters more
than it looks: if the skip lives only in the audit walker, a gate that calls
`check_page` directly — like the hook — blocks every edit to files the audit
has never had an opinion about. `test_kb_page.py` has a case pinning both
layers.

## Changing the schema

Adding a `type:` or `domain:` value means editing `TYPES`/`DOMAINS` in
`kb_page.py`, adding a test case for it, and re-running the audit. Do not bend
a page to fit a list that should have grown; do not grow the list to excuse a
page that is simply wrong.

## The optional PreToolUse hook

`kb_page.py` refuses a bad page **when it is run**. The chain still ends in
someone choosing to run it, and a rule that depends on remembering is a
remembered rule.

`hook_check.py` closes that. As a `PreToolUse` hook it sees every
`Write`/`Edit` before it lands, reconstructs the content the write *would*
produce, runs the same check, and exits **2** with the refusal text — which
blocks the tool call and hands the reason back to the agent. Out-of-scope
paths, and any failure inside the hook itself, exit 0 and let the write
through.

### It is not wired, and that is deliberate

Wiring it edits **your global Claude Code config** and changes **every session
on your machine**, including sessions that have nothing to do with this repo.
That is your call, not something a package gets to do to you.

Add to `~/.claude/settings.json` (Windows: `C:\Users\<you>\.claude\settings.json`),
merging into any `hooks` key already there, with the absolute path to your copy
of this repo:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "python \"/absolute/path/to/PowerWorldHiveMind/skills/knowledge-base-page/hook_check.py\""
          }
        ]
      }
    ]
  }
}
```

If `python` is not on PATH for your harness, use the interpreter's absolute
path in place of `python`.

**What it costs.** It runs on *every* `Write`/`Edit` in every session. It exits
early on anything that is not a `.md` inside this repo, but it is still a
process spawn per write.

**What it will not catch.** It gates writes made through the harness's file
tools. A page written by hand, by an editor, or by a script goes straight to
disk and the hook never sees it. For those, `audit` is the only check.

**A new hook may need a restart.** Claude Code picks up `settings.json` at
session start, so a hook added mid-session may not fire until you restart or
open `/hooks`.

To back it out: delete the block. There is no uninstall step and nothing else
on disk changes.
