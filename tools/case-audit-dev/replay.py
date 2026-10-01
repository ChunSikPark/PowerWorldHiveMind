"""Audit a stored snapshot with no PowerWorld. The output says so, everywhere.

    python tools/case-audit-dev/replay.py <snapshot.json.gz> --out <dir> [--profiles base,timestep,opf] [--pww <file>]

findings.json carries "source": "snapshot" and read_only.unchanged = null; findings.md opens
with "Replayed from a stored snapshot; no case was opened". Used for seeded test and eval cases.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "case-audit" / "engine"))

import report  # noqa: E402
from casedata import CaseData  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("snapshot")
    ap.add_argument("--out", required=True)
    ap.add_argument("--profiles", default="base")
    ap.add_argument("--pww")
    a = ap.parse_args()
    r = report.build(CaseData.from_json(a.snapshot), a.profiles.split(","), a.pww, source="snapshot")
    report.write(r, Path(a.out))
    print(f"replayed {r['case']}: " + "; ".join(f"{p} {v['verdict']}" for p, v in r["verdicts"].items()))
