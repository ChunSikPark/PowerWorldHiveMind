"""Write graph.json for the site: every kit page, the links between them, and the date each was added.

Pages are the ones the repo's Obsidian graph shows (see .obsidian/graph.json): everything except
skills/, commands/, dist/, assets/ and the root-level meta files. Dates come from git, so the
checkout needs full history (fetch-depth: 0).

    python site/build_graph.py <out.json>
"""
import json
import posixpath
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = ("skills/", "commands/", "dist/", "assets/", "site/", ".github/", ".obsidian/")
LINK = re.compile(r"\]\(([^)\s#]+\.md)(?:#[^)]*)?\)")
GROUPS = {"concepts", "methods", "references", "demos"}


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True).stdout


def title_of(text, stem):
    body = text.split("\n---", 2)[-1] if text.startswith("---") else text
    m = re.search(r"^# (.+)$", body, re.M)
    return m.group(1).strip() if m else stem.replace("-", " ")


def main(out):
    pages = sorted(p for p in git("ls-files", "*.md").splitlines() if "/" in p and not p.startswith(SKIP))
    known = set(pages)
    nodes, links = [], set()
    for p in pages:
        text = (ROOT / p).read_text(encoding="utf-8")
        added = git("log", "--diff-filter=A", "--follow", "--format=%as", "--", p).split()
        top = p.split("/")[0]
        nodes.append({
            "id": p,
            "title": title_of(text, Path(p).stem),
            "group": top if top in GROUPS else "agents",
            "added": added[-1] if added else date.today().isoformat(),
        })
        for target in LINK.findall(text):
            t = posixpath.normpath(posixpath.join(posixpath.dirname(p), target))
            if t in known and t != p:
                links.add(tuple(sorted((p, t))))
    Path(out).write_text(json.dumps({
        "generated": date.today().isoformat(),
        "nodes": nodes,
        "links": [list(l) for l in sorted(links)],
    }, indent=1), encoding="utf-8")
    print(f"{len(nodes)} pages, {len(links)} links -> {out}")


if __name__ == "__main__":
    main(sys.argv[1])
