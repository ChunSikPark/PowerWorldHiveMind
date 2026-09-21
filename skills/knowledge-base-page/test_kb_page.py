#!/usr/bin/env python3
"""One must-catch and one must-pass case per rule, plus scope.

    python test_kb_page.py        ->  N/N correct, exit 0

A rule with only a must-catch case is a rule that might refuse everything; a
rule with only a must-pass case is a rule that might refuse nothing. The
coverage assertion at the bottom fails the run if any rule id in RULES is
missing either polarity, so a new rule cannot ship half-tested.
"""

import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kb_page as kb  # noqa: E402

NL = chr(10)
results = []


def record(ok, name, want, rule):
    results.append((bool(ok), name, want, rule))


# --------------------------------------------------------------- fixture
REPO = Path(tempfile.mkdtemp(prefix="kb-page-test-"))
(REPO / "plugin.json").write_text('{"name": "test"}', encoding="utf-8")
(REPO / "README.md").write_text("# Readme" + NL, encoding="utf-8")
(REPO / "concepts").mkdir()
(REPO / "methods").mkdir()
(REPO / "skills" / "thing").mkdir(parents=True)


def write(rel, text):
    p = REPO / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(text.encode("utf-8"))
    return p


def page(body=None, **over):
    fm = {"type": "concept", "domain": "tooling",
          "aliases": "[a-page, the-page]", "tags": "[demo, testing]"}
    fm.update(over)
    head = NL.join("%s: %s" % kv for kv in fm.items() if kv[1] is not None)
    body = body if body is not None else "Some prose about the thing."
    return NL.join([
        "---", head, "---", "",
        "# A Page", "",
        "## Abstract", "One paragraph.", "",
        "## Connections",
        "- **Up:** [Home](../index.md)",
        "- **Across:** [Readme](../README.md)", "",
        "## Content", body, ""])


def refused(rel):
    return [f for f in kb.check_page(REPO / rel, root=REPO)
            if f.level == kb.REFUSE]


def fired(rel, rule):
    return any(f.rule == rule for f in kb.check_page(REPO / rel, root=REPO))


# index.md must name every page that should pass the index-row rule.
write("index.md", NL.join([
    "# Index", "",
    "- [valid](concepts/valid.md)",
    "- [enum-bad](concepts/enum-bad.md)",
    "- [list-bad](concepts/list-bad.md)",
    "- [sections-bad](concepts/sections-bad.md)",
    "- [nofm](concepts/nofm.md)",
    "- [dangling](concepts/dangling.md)",
    "- [orphan](concepts/orphan.md)",
    "- [onelink](concepts/onelink.md)",
    "- [big](concepts/big.md)",
    "- [bom](concepts/bom.md)", ""]))

# ------------------------------------------------------------- the cases
write("concepts/valid.md", page())
record(not refused("concepts/valid.md"),
       "a fully conforming page", False, "frontmatter")

write("concepts/nofm.md", "# No Frontmatter" + NL + "nothing else" + NL)
record(fired("concepts/nofm.md", "frontmatter"),
       "a page with no frontmatter", True, "frontmatter")

write("concepts/missing-key.md", page(tags=None))
record(fired("concepts/missing-key.md", "frontmatter"),
       "frontmatter missing `tags:`", True, "frontmatter")

write("concepts/enum-bad.md", page(type="musing"))
record(fired("concepts/enum-bad.md", "enum"),
       "a type: outside the measured set", True, "enum")
record(not fired("concepts/valid.md", "enum"),
       "a type:/domain: pair the repo actually uses", False, "enum")

write("concepts/list-bad.md", page(tags="demo, testing"))
record(fired("concepts/list-bad.md", "listshape"),
       "tags: that is not a [bracketed, list]", True, "listshape")
write("concepts/wrapped.md", page(
    aliases="[a-page," + NL + "  the-page, a-third]"))
record(not fired("concepts/wrapped.md", "listshape"),
       "...and a list that WRAPS across lines still passes", False, "listshape")

write("concepts/sections-bad.md", NL.join([
    "---", "type: concept", "domain: tooling",
    "aliases: [x]", "tags: [y]", "---", "",
    "# Out Of Order", "",
    "## Content", "[Home](../index.md) [Readme](../README.md)", "",
    "## Abstract", "backwards", ""]))
record(fired("concepts/sections-bad.md", "sections"),
       "Content before Abstract", True, "sections")
record(not fired("concepts/valid.md", "sections"),
       "Abstract then Connections then Content", False, "sections")

write("concepts/dangling.md", page().replace(
    "[Readme](../README.md)", "[Gone](../nowhere/missing.md)"))
record(fired("concepts/dangling.md", "links"),
       "a relative link that does not resolve", True, "links")
record(not fired("concepts/valid.md", "links"),
       "links that all resolve on disk", False, "links")

write("concepts/orphan.md", NL.join([
    "---", "type: concept", "domain: tooling",
    "aliases: [x]", "tags: [y]", "---", "",
    "# Orphan", "", "## Abstract", "a", "", "## Connections", "none at all",
    "", "## Content", "no links anywhere", ""]))
record(fired("concepts/orphan.md", "orphan"),
       "a page with no outbound links at all", True, "orphan")
record(not fired("concepts/valid.md", "orphan"),
       "...and a linked page is not an orphan", False, "orphan")

write("concepts/onelink.md", page().replace(
    "- **Across:** [Readme](../README.md)" + NL, ""))
record(fired("concepts/onelink.md", "linkfloor"),
       "exactly one outbound link", True, "linkfloor")
record(not fired("concepts/valid.md", "linkfloor"),
       "two or more outbound links", False, "linkfloor")
record(all(f.level == kb.WARN
           for f in kb.check_page(REPO / "concepts/onelink.md", root=REPO)
           if f.rule == "linkfloor"),
       "...and linkfloor WARNs rather than refusing", False, "linkfloor")

write("concepts/unlisted.md", page())
record(fired("concepts/unlisted.md", "index-row"),
       "a page with no row in index.md", True, "index-row")
record(not fired("concepts/valid.md", "index-row"),
       "a page index.md names", False, "index-row")

write("concepts/big.md", page(body=("a long line of prose." + NL) * 600))
record(fired("concepts/big.md", "size"),
       "a page past the length signal", True, "size")
record(not fired("concepts/valid.md", "size"),
       "a page inside the length signal", False, "size")

write("concepts/bom.md", page(body="text with a " + chr(0xFEFF) + " inside"))
record(fired("concepts/bom.md", "encoding"),
       "an embedded U+FEFF", True, "encoding")
record(not fired("concepts/valid.md", "encoding"),
       "a cleanly decodable page", False, "encoding")

# ------------------------------------------------------------------ scope
# The lesson that motivated this build: the meta-page test must hold in BOTH
# check_page and audit_pages, or a gate calling check_page directly blocks
# every edit to files the audit never had an opinion about.
write("CHANGELOG.md", "# Changelog" + NL + "no frontmatter, no sections." + NL)
record(not refused("CHANGELOG.md"),
       "check_page: a root meta page is exempt", False, "scope")
record("CHANGELOG.md" not in {p.name for p in kb.audit_pages(REPO)},
       "audit_pages: the same root meta page is skipped", True, "scope")

write("skills/thing/SKILL.md", "---" + NL + "name: thing" + NL + "---" + NL)
record(not refused("skills/thing/SKILL.md"),
       "check_page: a SKILL.md is machinery, not a page", False, "scope")
record("SKILL.md" not in {p.name for p in kb.audit_pages(REPO)},
       "audit_pages: skills/ is skipped too", True, "scope")
record(any(p.name == "valid.md" for p in kb.audit_pages(REPO)),
       "...and ordinary content pages are still audited", False, "scope")

record(kb.find_repo_root(REPO / "concepts" / "valid.md") == REPO,
       "find_repo_root walks up to plugin.json + index.md", False, "scope")

# ------------------------------------------------------------- API surface
record(kb.CONTRACT_API >= 1, "CONTRACT_API is set", False, "meta")
record(bool(kb.RULES), "a non-empty rule table", True, "meta")

_covered = {}
for ok, name, want, rule in results:
    _covered.setdefault(rule, set()).add(want)
_gaps = [rid for rid, _, _ in kb.RULES
         if _covered.get(rid, set()) != {True, False}]
record(not _gaps,
       "every rule has a must-catch AND a must-pass case%s"
       % (" (missing: %s)" % ", ".join(_gaps) if _gaps else ""), True, "meta")

# ------------------------------------------------------------------ report
width = max(len(n) for _, n, _, _ in results)
missed = sum(not ok for ok, _, _, _ in results)
for ok, name, want, rule in results:
    print("%s  %s  %s" % ("ok  " if ok else "MISS", name.ljust(width),
                          "must be caught" if want else "must pass"))
print(NL + "%d/%d correct" % (len(results) - missed, len(results)))
raise SystemExit(1 if missed else 0)
