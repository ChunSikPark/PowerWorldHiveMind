---
description: Write a new page into this knowledge base, or check and audit the pages already here
---

# Knowledge base page

Grow this knowledge base, or check that it still conforms. What the user asked
for decides which of the three below you do. Do not do all three.

## If they want to record something — write a page

Invoke the `knowledge-base-page` skill and follow it. It carries the filing
tree, the page shape, the link rules, the `index.md` bookkeeping, and the rule
about what must never go into a public page.

Two things that are easy to skip and are the whole point:

1. **Search first.** `grep -rn -i "<term>" concepts/ methods/ references/ demos/`
   on both the plain-English phrasing and the identifier. If a page covers it,
   edit that page. A second page on one topic is the failure this base exists
   to avoid.
2. **Add the `index.md` row.** One row, in the table for the page's folder.

## If they want one page checked

```bash
python skills/knowledge-base-page/kb_page.py check <path/to/page.md>
```

Exit 1 means a REFUSE fired. **Paste the output.** Fix what it names — do not
argue with it and do not edit the rule to make the page pass. If you believe
the rule is wrong, say so and stop; changing a rule is a schema decision, not a
page fix.

## If they want the whole repo audited

```bash
python skills/knowledge-base-page/kb_page.py audit
```

The invariant is **zero refusals**. Report the count and the per-rule fire
counts as printed. Warnings are a to-do list, not a failure — say how many and
of what kind, and offer to fix them, but do not silently start.

## If a write was already refused

The refusal text names the rule and quotes the offending line. Fix the page and
write it again. `python skills/knowledge-base-page/kb_page.py rules` prints the
full table with what each rule means.

## Before you claim any of this is done

Run the command and show its output. "It looks right" is not evidence, and this
is a checker — there is no reason to guess when you can run it.
