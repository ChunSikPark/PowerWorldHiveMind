#!/usr/bin/env python3
"""Refuse a knowledge-base page that does not conform to this repo's schema.

    python kb_page.py check <page.md>
    python kb_page.py audit [--root <repo>]
    python kb_page.py rules
    python kb_page.py --api-version

Every REFUSE rule below was derived by measuring the 57 content pages this repo
ships, not by taste. The discipline is one line:

    A rule ships as REFUSE only if every page already in the repo passes it.

Anything even one shipped page fails is a WARN. That is why `linkfloor` and
`index-row` are WARNs -- two pages fall short of each, and a checker that
refuses the repo's own pages is wrong about the repo, not about the page.

Measured on the repo at the time of writing:
    frontmatter  57/57 carry type, domain, aliases, tags
    enum         type in {concept, method, reference, tool, dataset};
                 domain in {tooling, cross-cutting, weather}
    listshape    aliases/tags are bracketed lists, 0 deviations
    sections      Abstract -> Connections -> Content, 57/57
    links        360 distinct link targets over 521 instances, 0 dangling
                 (a WARN even so -- see the note on the RULES entry)
    linkfloor    55/57 carry 2 or more (hence WARN)
    index-row    55/57 appear in index.md (hence WARN)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CONTRACT_API = 1

REFUSE = "REFUSE"
WARN = "WARN"

# Folders that hold machinery or build output, not pages.
# `commands` and `skills` hold plugin machinery -- a SKILL.md is not a page.
SKIP_DIRS = {".git", ".github", "dist", "assets", "node_modules",
             "__pycache__", "raw", ".obsidian", "scripts",
             "commands", "skills"}

# Root-level .md files are meta -- README, AGENTS, index, CHANGELOG and friends.
# A content page lives in a folder. This is deliberately a *shape* rule and not
# a list of filenames: a list is a second source of truth that drifts, and the
# repo has zero root-level content pages to make one necessary.
#
# It is applied in BOTH `check_page` and `audit_pages`. Applying it in only one
# place is a real defect with a real bite -- a gate that calls check_page
# directly will otherwise block every edit to files the audit has never had an
# opinion about.
def is_meta_page(rel: Path) -> bool:
    return len(rel.parts) == 1


TYPES = {"concept", "method", "reference", "tool", "dataset"}
DOMAINS = {"tooling", "cross-cutting", "weather"}
REQUIRED_KEYS = ("type", "domain", "aliases", "tags")
SECTIONS = ("Abstract", "Connections", "Content")

LINKFLOOR_SIGNAL = 2
SIZE_LINES, SIZE_CHARS = 500, 40000

MDLINK = re.compile(r"\[[^\]]+\]\(([^)#]+\.md)(?:#[^)]*)?\)")
HEADING = re.compile(r"^## (.+?)\s*$", re.M)

RULES = [
    ("encoding", REFUSE, "the file cannot be read as UTF-8, or carries an "
                         "embedded U+FEFF"),
    ("frontmatter", REFUSE, "missing YAML frontmatter, or missing one of "
                            "type/domain/aliases/tags"),
    ("enum", REFUSE, "a type: or domain: value outside the measured set"),
    ("listshape", REFUSE, "aliases: or tags: is not a [bracketed, list]"),
    ("sections", REFUSE, "## Abstract, ## Connections, ## Content missing or "
                         "out of order"),
    # WARN, not REFUSE: a page written before the pages it links to has
    # dangling links through no fault of its own, and two new pages that
    # link to each other could never both be written. The audit catches
    # dangling links across the finished corpus, which is the right place
    # for a check a batch can only satisfy once it is complete.
    ("links", WARN, "a relative .md link that does not resolve on disk"),
    ("orphan", REFUSE, "no outbound links at all -- the page is unreachable"),
    ("linkfloor", WARN, "fewer than %d outbound links" % LINKFLOOR_SIGNAL),
    ("index-row", WARN, "the page has no row in index.md"),
    ("size", WARN, "past the length signal; consider splitting"),
]


class Finding:
    def __init__(self, rule, message, evidence=None):
        self.rule = rule
        self.message = message
        self.evidence = evidence
        self.level = dict((r, lv) for r, lv, _ in RULES).get(rule, REFUSE)

    def __str__(self):
        tail = "  <<%s>>" % self.evidence if self.evidence else ""
        return "  %-6s %-12s %s%s" % (self.level, self.rule, self.message, tail)


class PageReadError(Exception):
    pass


def find_repo_root(start):
    """The repo root: the directory carrying both plugin.json and index.md."""
    p = Path(start).resolve()
    for cand in [p] + list(p.parents):
        if (cand / "plugin.json").exists() and (cand / "index.md").exists():
            return cand
    return None


def _at(text, idx):
    """"line L, column C" plus the offending line with a caret under it.

    An offset alone is useless for a U+FEFF: it is invisible in every
    editor, so "character 281" means opening a hex view or writing a
    script -- the work the checker exists to save. Point at a line.
    """
    line_no = text.count("\n", 0, idx) + 1
    line_start = text.rfind("\n", 0, idx) + 1
    col = idx - line_start + 1
    line_end = text.find("\n", idx)
    line = text[line_start:line_end if line_end != -1 else len(text)]
    # Render invisibles as <U+XXXX>. Echoing a U+FEFF verbatim defeats the
    # purpose -- and on a cp1252 console, the Windows default, printing it
    # raises UnicodeEncodeError, so the message would crash rather than
    # explain.
    shown, caret_col = "", col
    for i, ch in enumerate(line):
        if ch.isprintable() and ch != "\ufeff":
            shown += ch
            continue
        token = "<U+%04X>" % ord(ch)
        if i < col - 1:
            caret_col += len(token) - 1
        shown += token
    width = len("<U+%04X>" % ord(text[idx])) if idx < len(text) else 1
    caret = " " * (caret_col - 1) + "^" * width
    return "line %d, column %d%s%s%s%s" % (line_no, col, chr(10), shown,
                                           chr(10), caret)


def read_page(path):
    try:
        raw = Path(path).read_bytes()
    except OSError as exc:
        raise PageReadError(str(exc))
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        # exc.start is a BYTE offset and the text will not decode, so
        # locate it in a lossy decode rather than reporting a number in
        # different units from the one the U+FEFF branch uses.
        lossy = raw.decode("utf-8", errors="replace")
        idx = len(raw[:exc.start].decode("utf-8", errors="replace"))
        raise PageReadError("not valid UTF-8 at %s" % _at(lossy, idx))
    stripped = text.replace("\r\n", "\n")
    idx = stripped.find("\ufeff")
    if idx != -1:
        raise PageReadError(
            "embedded U+FEFF (invisible) at %s" % _at(stripped, idx))
    return stripped


def split_frontmatter(text):
    """(dict, body, error). A missing/unterminated block is an error."""
    if not text.startswith("---\n"):
        return None, text, "page does not open with YAML frontmatter"
    end = text.find("\n---", 3)
    if end == -1:
        return None, text, "frontmatter block is never closed"
    # A YAML list may wrap: an indented continuation line belongs to the
    # key above it, so `aliases: [a, b,` + `  c]` is one value, not a
    # bracket that never closes.
    fm, key = {}, None
    for line in text[4:end].split("\n"):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith((" ", "\t")) and key is not None:
            fm[key] = fm[key] + " " + line.strip()
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            key = k.strip()
            fm[key] = v.strip()
        else:
            key = None
    return fm, text[end + 4:], None


def outbound_links(body):
    return sorted(set(MDLINK.findall(body)))


def index_mentions(root, rel):
    """True when index.md references this page by path or by stem."""
    try:
        index = read_page(Path(root) / "index.md")
    except (PageReadError, OSError):
        return True  # cannot prove absence; do not invent a finding
    return rel.as_posix() in index or Path(rel).stem in index


def check_page(path, root=None):
    """Every rule against one page. Returns a list of Findings."""
    path = Path(path)
    if root is None:
        root = find_repo_root(path)
    try:
        text = read_page(path)
    except PageReadError as exc:
        return [Finding("encoding", str(exc))]

    try:
        rel = path.resolve().relative_to(Path(root).resolve())
    except (ValueError, TypeError, OSError):
        rel = Path(path.name)

    # Meta pages and machinery folders are not content pages. Same test the
    # audit uses -- see the note on is_meta_page.
    if is_meta_page(rel) or (set(q.lower() for q in rel.parts[:-1]) & SKIP_DIRS):
        return []

    findings = []
    fm, body, fm_error = split_frontmatter(text)

    if fm_error:
        findings.append(Finding("frontmatter", fm_error))
    else:
        missing = [k for k in REQUIRED_KEYS if k not in fm]
        if missing:
            findings.append(Finding(
                "frontmatter", "frontmatter is missing %s"
                % ", ".join("`%s:`" % m for m in missing)))

        if "type" in fm and fm["type"] not in TYPES:
            findings.append(Finding(
                "enum", "type: %r is not one of %s"
                % (fm["type"], ", ".join(sorted(TYPES))), fm["type"]))
        if "domain" in fm and fm["domain"] not in DOMAINS:
            findings.append(Finding(
                "enum", "domain: %r is not one of %s"
                % (fm["domain"], ", ".join(sorted(DOMAINS))), fm["domain"]))

        for key in ("aliases", "tags"):
            val = fm.get(key)
            if val is not None and not (val.startswith("[") and val.endswith("]")):
                findings.append(Finding(
                    "listshape", "%s: must be a [bracketed, list]" % key, val[:60]))
            elif val is not None and val.strip() == "[]":
                findings.append(Finding(
                    "listshape", "%s: is an empty list" % key, val))

    heads = [h for h in HEADING.findall(body) if h in SECTIONS]
    if tuple(heads[:3]) != SECTIONS:
        findings.append(Finding(
            "sections", "missing or out of order: want %s"
            % " then ".join("## " + s for s in SECTIONS),
            " / ".join("## " + h for h in heads[:4]) or "(none present)"))

    links = outbound_links(body)
    for t in links:
        tried = (path.parent / t).resolve()
        if tried.exists():
            continue
        # Quote the path actually tried: a `../` depth mistake and a
        # misspelt filename produce the same link text and need
        # different fixes.
        try:
            shown = tried.relative_to(Path(root).resolve()).as_posix()
        except (ValueError, TypeError, OSError):
            shown = str(tried)
        findings.append(Finding(
            "links", "link target does not exist; resolved to %s" % shown,
            t))

    if not links:
        findings.append(Finding(
            "orphan", "no outbound [text](../page.md) links; every page must "
                      "be reachable from at least one other"))
    elif len(links) < LINKFLOOR_SIGNAL:
        findings.append(Finding(
            "linkfloor", "%d outbound link; the signal is %d"
            % (len(links), LINKFLOOR_SIGNAL), links[0]))

    if root is not None and not index_mentions(root, rel):
        findings.append(Finding(
            "index-row", "no row in index.md; a new page adds exactly one"))

    lines, chars = body.count("\n") + 1, len(body)
    if lines > SIZE_LINES or chars > SIZE_CHARS:
        findings.append(Finding(
            "size", "page is %d lines / %d chars (signal at %d / %d)"
            % (lines, chars, SIZE_LINES, SIZE_CHARS)))

    return findings


def audit_pages(root):
    """The pages `audit` scans: content pages only."""
    out = []
    for path in sorted(Path(root).rglob("*.md")):
        rel = path.relative_to(root)
        if set(q.lower() for q in rel.parts[:-1]) & SKIP_DIRS:
            continue
        if is_meta_page(rel):
            continue
        out.append(path)
    return out


def cmd_check(args):
    root = find_repo_root(args.page)
    findings = check_page(args.page, root=root)
    refuses = [f for f in findings if f.level == REFUSE]
    if findings:
        print("%s %s" % ("REFUSED" if refuses else "ok, with warnings",
                         args.page))
        for f in findings:
            print(f)
    else:
        print("ok %s" % args.page)
    return 1 if refuses else 0


def cmd_audit(args):
    root = Path(args.root).resolve() if args.root else find_repo_root(Path.cwd())
    if root is None:
        print("no repo root found (need plugin.json + index.md)")
        return 1
    pages = audit_pages(root)
    counts = dict((r, 0) for r, _, _ in RULES)
    refused = 0
    for page in pages:
        findings = check_page(page, root=root)
        if not findings:
            continue
        for f in findings:
            counts[f.rule] = counts.get(f.rule, 0) + 1
        if any(f.level == REFUSE for f in findings):
            refused += 1
            print("\n%s" % page.relative_to(root).as_posix())
            for f in findings:
                print(f)
    print("\nscanned %d pages; %d would be refused" % (len(pages), refused))
    print("\nper-rule fire counts:")
    for rid, level, _ in RULES:
        print("  %-6s %-12s %4d" % (level, rid, counts.get(rid, 0)))
    return 0


def cmd_rules(_args):
    print("CONTRACT_API %d\n" % CONTRACT_API)
    for rid, level, why in RULES:
        print("  %-6s %-12s %s" % (level, rid, why))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="kb_page.py", description=__doc__.split("\n")[0])
    p.add_argument("--api-version", action="store_true",
                   help="print CONTRACT_API and the rule ids, then exit")
    sub = p.add_subparsers(dest="cmd")

    c = sub.add_parser("check", help="check one page")
    c.add_argument("page")
    c.set_defaults(func=cmd_check)

    a = sub.add_parser("audit", help="check every page in the repo")
    a.add_argument("--root")
    a.set_defaults(func=cmd_audit)

    r = sub.add_parser("rules", help="print the rule table")
    r.set_defaults(func=cmd_rules)

    args = p.parse_args(argv)
    if args.api_version:
        print("CONTRACT_API %d" % CONTRACT_API)
        for rid, _, _ in sorted(RULES):
            print(rid)
        return 0
    if not getattr(args, "func", None):
        p.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
