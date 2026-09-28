"""What the curated study-options page says about a field — verbatim, never summarised.

The hub's tags rate a row's claim (a recipe, a trap, a decoy), not a field, so this module
returns the rows themselves and leaves the reading to whoever asked.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from schema import KIT_ROOT, find_field

HUB = KIT_ROOT / "references" / "powerworld-study-options.md"


@dataclass(frozen=True)
class HubRow:
    section: str  # nearest heading above the row
    text: str     # the row's cells joined with " | ", tag excluded
    tag: str      # the row's tag cell verbatim, "" when its table has no tag column
    match: str    # "exact": the row names Object.Field; "name": only the bare field name


def _tokens(text: str) -> list[str]:
    """Backticked names, reduced to their first word before any '='."""
    out = []
    for t in re.findall(r"`([^`]+)`", text):
        words = t.split()
        if words:
            out.append(words[0].split("=")[0])
    return out


def _cells(line: str) -> list[str]:
    return [c.strip() for c in re.split(r"(?<!\\)\|", line)[1:-1]]


def _table_rows(hub: Path):
    """(section, body cells, tag) per data row. Only a table whose header ends in 'tag' has tags."""
    section, header, prev_table = "", None, False
    for line in hub.read_text(encoding="utf-8").splitlines():
        is_table = line.startswith("|")
        if line.startswith("#"):
            section = line.lstrip("#").strip()
        elif is_table and not prev_table:
            header = _cells(line)
        elif is_table and not re.match(r"^\|[\s|:-]+\|$", line):
            cells = _cells(line)
            if header and header[-1].lower() == "tag":
                yield section, cells[:-1], cells[-1]
            else:
                yield section, cells, ""
        prev_table = is_table


def hub_rows(obj: str, field_name: str, fields: dict | None = None, hub: Path = HUB) -> list[HubRow]:
    """Hub table rows that name this field: exact Object.Field matches first."""
    f = find_field(obj, field_name, fields)
    if f is None:
        return []
    names = {n for n in (f.variable, f.concise) if n}
    found = []
    for section, cells, tag in _table_rows(hub):
        body = " | ".join(cells)
        match = ""
        for tok in _tokens(body):
            if "." in tok:
                o, fld = tok.split(".", 1)
                if o.lower() == f.object.lower() and fld in names:
                    match = "exact"
                    break
            elif tok in names:
                match = "name"
        if match:
            found.append(HubRow(section, body, tag, match))
    return sorted(found, key=lambda r: r.match != "exact")


def hub_passages(words: list[str], hub: Path = HUB, limit: int = 3) -> list[str]:
    """Paragraphs and table rows mentioning at least two of `words`, most matches first."""
    words = [w.lower() for w in words if len(w) >= 3]
    blocks, para = [], []
    for line in hub.read_text(encoding="utf-8").splitlines():
        if line.startswith("|"):
            blocks.append(line)
        elif line.strip() and not line.startswith("#"):
            para.append(line.strip())
            continue
        if para:
            blocks.append(" ".join(para))
            para = []
    if para:
        blocks.append(" ".join(para))
    scored = [(sum(w in b.lower() for w in set(words)), i, b) for i, b in enumerate(blocks)]
    scored = [s for s in scored if s[0] >= 2]
    scored.sort(key=lambda s: (-s[0], s[1]))
    return [s[2] for s in scored[:limit]]
