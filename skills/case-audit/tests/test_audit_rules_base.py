import pandas as pd

from auditcase import case
from casedata import CaseData, Solve
from findings import FYI, STOPS, WORTH
from rules_base import ac_converges, dc_skeleton, gen_over_nameplate, stale_ctg_results


def test_converged_case_has_no_convergence_finding(frames):
    assert ac_converges(case(frames)) == []


def test_raised_solve_stops_every_study(frames):
    cd = CaseData(frames, {}, Solve(True, "NR PowerFlow - Exceeded maximum number of iterations", 2e-5, 1e-5))
    [f] = ac_converges(cd)
    assert f.severity == STOPS and set(f.stops) == {"base", "n1", "timestep", "opf", "scopf"}
    assert "Exceeded maximum number" in f.why


def test_mismatch_over_tolerance_without_a_raise_still_fails(frames):
    [f] = ac_converges(CaseData(frames, {}, Solve(True, None, 3.0, 0.1)))
    assert "3.0 MVA" in f.why


def test_real_network_is_not_a_skeleton(frames):
    assert dc_skeleton(case(frames)) == []


def test_placeholder_resistance_is_a_skeleton(frames):
    lines = frames["Branch"].LineXfmr == "NO"
    frames["Branch"].loc[lines, "LineR"] = 1e-7
    frames["Branch"].loc[lines, "LineC"] = 0.0
    [f] = dc_skeleton(case(frames))
    assert f.severity == STOPS and f.details["median_xr"] > 1000 and f.details["share_no_r_no_c"] == 1.0
    assert f.scope == "every AC study; a DC-only study can still run"


def test_part_skeleton_is_worth_a_look(frames):
    frames["Branch"].loc[0, ["LineR", "LineC"]] = [1e-7, 0.0]             # 1 of 5 closed lines
    [f] = dc_skeleton(case(frames))
    assert f.severity == WORTH and f.where == [{"BusNum": 1, "BusNum:1": 2, "LineCircuit": "1"}]


def test_zero_resistance_everywhere_says_undefined_not_nan(frames):
    frames["Branch"].loc[frames["Branch"].LineXfmr == "NO", ["LineR", "LineC"]] = [0.0, 0.0]
    [f] = dc_skeleton(case(frames))
    assert f.severity == STOPS and "undefined (R = 0 on every line)" in f.what and "nan" not in f.what


def test_small_overshoot_is_worth_a_look_with_its_mw(frames):
    frames["Gen"].loc[0, "GenMW"] = 403.0                   # 3 MW over a 400 MW unit: under max(4, 5)
    [f] = gen_over_nameplate(case(frames))
    assert f.severity == WORTH and f.where[0]["over_mw"] == 3.0 and f.where[0]["slack"]


def test_large_overshoot_stops_the_study(frames):
    frames["Gen"].loc[0, "GenMW"] = 460.0
    [f] = gen_over_nameplate(case(frames))
    assert f.severity == STOPS and f.where[0] == {"BusNum": 1, "GenID": "1", "GenMW": 460.0,
                                                  "GenMWMax": 400.0, "over_mw": 60.0, "slack": True}


def test_offline_unit_over_its_max_is_ignored(frames):
    frames["Gen"].loc[0, ["GenMW", "GenStatus"]] = [460.0, "Open"]
    assert gen_over_nameplate(case(frames)) == []


def test_stale_ctg_rows_are_fyi(frames):
    frames["ViolationCTG"] = pd.DataFrame({"CTGLabel": ["a", "a", "b"]})
    [f] = stale_ctg_results(case(frames))
    assert f.severity == FYI and f.details["rows"] == 3
    frames["ViolationCTG"] = None
    assert stale_ctg_results(case(frames)) == []
