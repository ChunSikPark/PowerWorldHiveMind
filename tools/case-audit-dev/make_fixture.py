"""Turn a snapshot from snapshot.py into a fixture fit for a public repo.

    python tools/case-audit-dev/make_fixture.py <in.json.gz> <out.json.gz>

Keeps only the case file's name (no local folders). Run it only on snapshots of public
synthetic cases. (Task 16 adds the seeding options.)
"""
import argparse
import sys
from pathlib import Path, PureWindowsPath

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "case-audit" / "engine"))

from casedata import CaseData  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    a = ap.parse_args(argv)
    cd = CaseData.from_json(a.src)
    cd.scalars["case_path"] = PureWindowsPath(cd.scalars["case_path"]).name
    cd.scalars.pop("read_seconds", None)
    cd.to_json(a.dst)
    print(f"{a.dst}: case {cd.scalars['case_path']}, {len(cd.get('Bus'))} buses")


if __name__ == "__main__":
    main()
