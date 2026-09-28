"""Which PowerWorld object, field or command — from the field export and the study-options hub.

    python lookup.py object Shunt
    python lookup.py field CTG_Options Include
    python lookup.py search "island violations" --object CTG_Options --limit 5
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import schema  # noqa: E402
from hub import hub_passages, hub_rows  # noqa: E402

WRITABLE = ("yes", "aux-only", "edit-mode", "depends", "read-only", "unknown")


def _role(f: schema.Field) -> str:
    if f.key_index:
        return f"key {f.key_index}"
    if f.is_required:
        return "required to create"
    return "-"


def show_object(name: str, fields: dict) -> str:
    obj = schema.resolve_object(name, fields)
    fs = fields[obj]
    count = Counter(f.writable for f in fs)
    return "\n".join([
        f"## {obj}  ({len(fs)} fields)",
        f"keys (in order): {', '.join(f.variable for f in schema.keys(obj, fields)) or 'none (single-record object)'}",
        f"required to create: {', '.join(f.variable for f in schema.required(obj, fields)) or 'none'}",
        "writable: " + "   ".join(f"{w} {count[w]}" for w in WRITABLE if count[w]),
    ])


def show_field(obj: str, name: str, fields: dict) -> tuple[int, str]:
    obj = schema.resolve_object(obj, fields)
    f = schema.find_field(obj, name, fields)
    if f is None:
        near = schema.close_field_names(obj, name, fields)
        lines = [
            f"{obj} has no field {name!r} in the field export.",
            f"spelling neighbours (not substitutes): {', '.join(near) or 'none'}",
        ]
        passages = hub_passages(schema.split_words(schema.normalize_field_name(name)))
        if passages:
            lines.append("the study-options hub on these words:")
            lines += [f"  > {p}" for p in passages]
        return 1, "\n".join(lines)
    concise = f"  (concise: {f.concise})" if f.concise and f.concise != f.variable else ""
    lines = [
        f"{obj}.{f.variable}{concise}",
        f"type: {f.type}   writable: {f.writable} ({f.enterable or 'blank'})   "
        f"role: {_role(f)}   marker: {f.marker or '-'}",
        f"dialog: {f.dialog_path}",
        f"description: {f.description}",
    ]
    rows = hub_rows(obj, f.variable, fields)
    if rows:
        lines.append("hub rows (verbatim; 'name' rows may concern another object):")
        lines += [f"  [{r.match}] {r.section} :: {r.text} :: tag {r.tag}" for r in rows]
    else:
        lines.append("hub: not mentioned - field export only, behaviour not tested here")
    return 0, "\n".join(lines)


def show_search(query: str, obj: str | None, limit: int, fields: dict) -> str:
    hits = schema.search(query, obj=obj, limit=limit, fields=fields)
    if not hits:
        return f"no field matches {query!r}"
    lines = []
    for f in hits:
        concise = f" ({f.concise})" if f.concise and f.concise != f.variable else ""
        lines.append(f"- {f.object}.{f.variable}{concise} [{f.writable}] - {f.dialog_path}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--xlsx", default=str(schema.DEFAULT_XLSX), help="field export to read")
    sub = ap.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("object")
    o.add_argument("name")
    fl = sub.add_parser("field")
    fl.add_argument("object")
    fl.add_argument("name")
    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--object")
    s.add_argument("--limit", type=int, default=20)
    a = ap.parse_args(argv)
    try:
        fields = schema.load_fields(a.xlsx)
        if a.cmd == "object":
            print(show_object(a.name, fields))
            return 0
        if a.cmd == "field":
            code, text = show_field(a.object, a.name, fields)
            print(text)
            return code
        print(show_search(a.query, a.object, a.limit, fields))
        return 0
    except schema.SchemaError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
