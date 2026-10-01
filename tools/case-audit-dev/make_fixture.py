"""Turn a snapshot from snapshot.py into a fixture fit for a public repo, optionally seeded.

    python tools/case-audit-dev/make_fixture.py <in.json.gz> <out.json.gz> [seeds]

Keeps only the case file's name (no local folders). Seeds, each a defect written into the copy:
  --strip-pfw N          blank the PFW model of the first N renewables that have one
  --unsolved             record the AC solve as failed, with PowerWorld's observed error text
  --skeleton             every closed line gets R = 1e-7 and B = 0 (a DC-only skeleton)
  --overshoot MW         the slack bus's first unit runs MW above its rating
  --placeholder-shunt    add a 0 Mvar switched shunt with no regulated bus
  --no-cost              every unit loses its cost data: GenCostModel = None, no curve points, GenMCost 0
                         (as measured on a synthetic case that carries none)
Run it only on snapshots of public synthetic cases. A seeded fixture is replayed with replay.py,
whose output says it was replayed.
"""
import argparse
import sys
from pathlib import Path, PureWindowsPath

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "case-audit" / "engine"))

from casedata import CaseData  # noqa: E402
from rules_ts import renewables  # noqa: E402

FAILED = "RunScriptCommand: Error in script action execution: NR PowerFlow - Exceeded maximum number of iterations"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--strip-pfw", type=int, default=0)
    ap.add_argument("--unsolved", action="store_true")
    ap.add_argument("--skeleton", action="store_true")
    ap.add_argument("--overshoot", type=float, default=0.0)
    ap.add_argument("--placeholder-shunt", action="store_true")
    ap.add_argument("--no-cost", action="store_true")
    a = ap.parse_args(argv)
    cd = CaseData.from_json(a.src)
    cd.scalars["case_path"] = PureWindowsPath(cd.scalars["case_path"]).name
    cd.scalars.pop("read_seconds", None)
    f = cd.frames
    if a.strip_pfw:
        r = renewables(cd)
        f["Gen"].loc[r.index[r.has_pfw][:a.strip_pfw], "TSPFWModelString"] = ""
    if a.unsolved:
        cd.solve.raised, cd.solve.max_mismatch_mva = FAILED, 205.2
    if a.skeleton:
        lines = (f["Branch"].LineStatus == "Closed") & (f["Branch"].LineXfmr == "NO")
        f["Branch"].loc[lines, ["LineR", "LineC"]] = [1e-7, 0.0]
    if a.overshoot:
        slack = f["Bus"].BusNum[f["Bus"].BusCat == "Slack"].iloc[0]
        i = f["Gen"].index[f["Gen"].BusNum == slack][0]
        f["Gen"].loc[i, "GenMW"] = f["Gen"].loc[i, "GenMWMax"] + a.overshoot
    if a.placeholder_shunt:
        row = {**f["Shunt"].iloc[0].to_dict(), "ShuntID": "P1", "SSCMode": "Discrete", "AutoControl": "YES",
               "SSStatus": "Closed", "SSRegNum": 0.0, "SSAMVR": 0.0, "SSNMVR": 0.0, "SSMaxMVR": 0.0, "SSMinMVR": 0.0}
        f["Shunt"].loc[len(f["Shunt"])] = row
    if a.no_cost:
        f["Gen"]["GenCostModel"] = "None"
        f["Gen"][["GenCostCurvePoints", "GenMCost"]] = 0.0
    cd.to_json(a.dst)
    print(f"{a.dst}: case {cd.scalars['case_path']}, {len(cd.get('Bus'))} buses")


if __name__ == "__main__":
    main()
