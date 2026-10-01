"""Read a case the way the engine does and store what was read, for tests and fixtures.

    python tools/case-audit-dev/snapshot.py <case.pwb> <out.json.gz>

A snapshot holds every field the engine reads for every bus, branch and unit. Take one only of
a public synthetic case, and never commit one without running make_fixture.py on it first.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "case-audit" / "engine"))

from reader import read_case  # noqa: E402

if __name__ == "__main__":
    cd = read_case(sys.argv[1])
    cd.to_json(sys.argv[2])
    print(f"{sys.argv[2]}: {len(cd.get('Bus'))} buses, solve {'converged' if cd.solve.converged else 'FAILED'}, "
          f"case file unchanged: {cd.scalars['sha256_before'] == cd.scalars['sha256_after']}")
