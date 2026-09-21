#!/usr/bin/env python3
"""PreToolUse hook: refuse a knowledge-base page write that breaks the schema.

Reads a Claude Code PreToolUse payload on stdin. If the write targets a `.md`
page inside this repo, it runs kb_page.py against the content the write *would
produce* and exits 2 with the refusal text when a REFUSE fires. Anything else:
exit 0.

Exit status, per the PreToolUse contract:
    0  allow the write (in scope and clean, out of scope, or the hook broke)
    2  block the write; stderr is fed back to the agent

2 is not merely "non-zero" here -- it is the only non-zero status that blocks.
Any other non-zero is shown to the user and the write proceeds anyway, so a
hook that exits 1 on a refusal looks like it is enforcing and is not.

IT IS NOT WIRED BY DEFAULT. Installing it edits your global Claude Code config
and affects every session on your machine, including sessions that have nothing
to do with this repo. That is your call, not something a package gets to do to
you. README.md in this folder has the block to paste and how to back it out.

--- Why import kb_page rather than subprocess it ---

"Which paths are pages" is already decided by kb_page's SKIP_DIRS and
is_meta_page. Subprocessing would mean hand-copying that logic here, which is a
second source of truth for the rule that decides whether the gate fires at all.
Importing means the hook's scope test *is* the checker's scope test. It also
means the refusal text the agent reads is Finding.__str__ -- the same string the
CLI prints, not a paraphrase.

The cost is that a crash in kb_page crashes the hook. That is handled: every
failure path below exits 0. A checker bug must not become a wall between a user
and their own notes.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent  # skills/knowledge-base-page -> skills -> repo root


def _payload():
    try:
        data = json.loads(sys.stdin.read())
    except (ValueError, OSError):
        return None
    return data if isinstance(data, dict) else None


def _target(tool_name, tool_input):
    """The new text this write would put on disk, or (None, None) to stay out.

    The hook runs *before* the write, so the file on disk is still the old
    content. Checking that would report on text nobody is writing, so the
    post-write content is reconstructed here.
    """
    path = tool_input.get("file_path")
    if not isinstance(path, str) or not path:
        return None, None

    if tool_name == "Write":
        content = tool_input.get("content")
        return (path, content) if isinstance(content, str) else (None, None)

    if tool_name in ("Edit", "MultiEdit"):
        edits = [tool_input] if tool_name == "Edit" else tool_input.get("edits")
        if not isinstance(edits, list):
            return None, None
        try:
            text = Path(path).read_bytes().decode("utf-8-sig")
        except (OSError, UnicodeDecodeError):
            return None, None
        for edit in edits:
            if not isinstance(edit, dict):
                return None, None
            old, new = edit.get("old_string"), edit.get("new_string")
            if not isinstance(old, str) or not isinstance(new, str):
                return None, None
            if old not in text:
                return None, None  # the write will fail on its own
            text = (text.replace(old, new) if edit.get("replace_all")
                    else text.replace(old, new, 1))
        return path, text

    return None, None


def _in_scope(path, kb_page):
    """The page's parts relative to the repo root, or None."""
    p = Path(path)
    if p.suffix.lower() != ".md":
        return None
    try:
        rel = p.resolve().relative_to(REPO.resolve())
    except (ValueError, OSError, TypeError):
        return None
    if kb_page.is_meta_page(rel):
        return None
    if set(q.lower() for q in rel.parts[:-1]) & kb_page.SKIP_DIRS:
        return None
    return rel.parts


def _check(parts, new_text, kb_page):
    """Run the checker over the would-be content. Returns REFUSE findings.

    The content is staged into a throwaway tree that mirrors the page's
    position in the repo -- tmp/<folder>/<same basename>. The checker derives
    the page's folder and name from its path relative to the root, and those
    drive the meta-page test and the link-resolution rule. A flat temp file
    would get both wrong.

    Link resolution is the reason the *real* repo is also needed: a staged copy
    has no siblings, so every relative link would dangle. The staged tree is
    used for shape, and the real path for resolution -- so the check runs
    against the real page location with the new bytes written there and then
    removed. Nothing outside the temp tree is touched.
    """
    tmp = Path(tempfile.mkdtemp(prefix="kb-page-hook-"))
    try:
        staged = tmp.joinpath(*parts)
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_text(new_text, encoding="utf-8")
        findings = kb_page.check_page(staged, root=tmp)
        # The link and index-row rules need the real repo to resolve against;
        # re-run only those against the real location.
        real = REPO.joinpath(*parts)
        body = kb_page.split_frontmatter(new_text)[1]
        keep = []
        for f in findings:
            if f.rule in ("links", "index-row"):
                continue
            keep.append(f)
        for target in kb_page.outbound_links(body):
            if not (real.parent / target).resolve().exists():
                keep.append(kb_page.Finding(
                    "links", "link target does not exist", target))
        return [f for f in keep if f.level == kb_page.REFUSE]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    data = _payload()
    if data is None:
        return 0
    tool_input = data.get("tool_input")
    if not isinstance(tool_input, dict):
        return 0

    if not ((REPO / "plugin.json").exists() and (REPO / "index.md").exists()):
        return 0  # not a recognisable repo root; stay out of it

    sys.path.insert(0, str(HERE))
    try:
        import kb_page  # noqa: E402  -- deliberately late; see module docstring
    except Exception:
        return 0

    try:
        path, new_text = _target(data.get("tool_name"), tool_input)
        if new_text is None:
            return 0
        parts = _in_scope(path, kb_page)
        if parts is None:
            return 0
        refusals = _check(parts, new_text, kb_page)
    except Exception:
        return 0  # a checker bug must not wall the user out of their own notes

    if not refusals:
        return 0

    print("kb-page: REFUSED %s" % path, file=sys.stderr)
    for f in refusals:
        print(f, file=sys.stderr)
    print("\nFix the page and write it again. `python %s rules` prints the "
          "rule table." % (HERE / "kb_page.py"), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
