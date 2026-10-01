"""Make a live audit's findings fit for a public repo: every absolute path becomes its file name.

    python tools/case-audit-dev/scrub_findings.py <folder with findings.json>

Rewrites findings.json and re-renders findings.md from it, so the two always agree.
"""
import json
import re
import sys
from pathlib import Path, PureWindowsPath

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "case-audit" / "engine"))

import report  # noqa: E402

ABSOLUTE = re.compile(r"^(?:[A-Za-z]:[/\\]|/)")


def scrub(o):
    if isinstance(o, str):
        return PureWindowsPath(o).name if ABSOLUTE.match(o) else o
    if isinstance(o, dict):
        return {k: scrub(v) for k, v in o.items()}
    if isinstance(o, list):
        return [scrub(v) for v in o]
    return o


if __name__ == "__main__":
    d = Path(sys.argv[1])
    r = scrub(json.loads((d / "findings.json").read_text(encoding="utf-8")))
    report.write(r, d)
    print(f"{d}: case {r['case']}")
