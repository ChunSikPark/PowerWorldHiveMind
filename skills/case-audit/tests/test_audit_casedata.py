import math

import pandas as pd
import pytest

from auditcase import case
from casedata import READS, CaseData, Solve
from findings import BROKEN, STOPS, WORTH, Finding, branch_keys, clean


def test_none_frame_becomes_empty_frame_with_columns():
    cd = CaseData({"Shunt": None}, {}, Solve())
    sh = cd.get("Shunt")
    assert sh.empty and list(sh.columns) == READS["Shunt"]
    assert sh[sh.SSStatus == "Closed"].SSMaxMVR.sum() == 0


def test_numbers_parsed_and_text_stripped():
    cd = CaseData({"Gen": pd.DataFrame({"BusNum": ["    23"], "GenID": [" 1 "], "GenMW": [" 69.27"],
                                        "Latitude": ["None"]})}, {}, Solve())
    g = cd.get("Gen")
    assert g.BusNum.iloc[0] == 23 and g.GenID.iloc[0] == "1" and g.GenMW.iloc[0] == pytest.approx(69.27)
    assert math.isnan(g.Latitude.iloc[0])
    assert g.GenFuelType.iloc[0] == ""                     # missing column added, empty


def test_line_circuit_stays_text():
    cd = CaseData({"Branch": pd.DataFrame({"BusNum": [1, 2], "BusNum:1": [2, 3], "LineCircuit": [" 01 ", "W2"]})},
                  {}, Solve())
    keys = [branch_keys(r) for _, r in cd.get("Branch").iterrows()]
    assert [k["LineCircuit"] for k in keys] == ["01", "W2"]


def test_converged_needs_no_raise_and_mismatch_under_tolerance():
    assert Solve(True, None, 0.02, 0.1).converged
    assert not Solve(True, "NR PowerFlow - Exceeded maximum number", 2e-5, 1e-5).converged
    assert not Solve(True, None, 0.5, 0.1).converged
    assert not Solve(False).converged


def test_an_unreadable_tolerance_does_not_fail_the_case():
    s = Solve(True, None, 0.02, None)
    assert s.converged and s.tolerance_unread
    assert not Solve(True, "NR PowerFlow - Power flow unable to converge", None, None).converged


def test_snapshot_round_trip(tmp_path):
    cd = case()
    p = tmp_path / "snap.json.gz"
    cd.to_json(p)
    back = CaseData.from_json(p)
    pd.testing.assert_frame_equal(back.get("Branch"), cd.get("Branch"))
    assert back.solve.converged and back.scalars["SBase"] == "100"


def test_finding_labels_are_closed_sets():
    with pytest.raises(AssertionError):
        Finding("x", "Blocker", BROKEN, "w", "y")
    with pytest.raises(AssertionError):
        Finding("x", STOPS, BROKEN, "w", "y")               # stops the study but names no study
    f = Finding("x", STOPS, BROKEN, "w", "y", stops=("n1",), scope="N-1 and SCOPF only")
    assert f.label == "Stops the study — N-1 and SCOPF only"
    assert Finding("x", WORTH, BROKEN, "w", "y").to_dict()["count"] == 0


def test_data_the_kit_lacks_must_name_its_source():
    with pytest.raises(AssertionError):
        Finding("ts.pfw_missing", WORTH, BROKEN, "w", "y")
    assert Finding("ts.pfw_missing", WORTH, BROKEN, "w", "y", handoff="Auto_PFW").to_dict()["handoff"] == "Auto_PFW"


def test_clean_removes_nan_and_numpy():
    import numpy as np
    assert clean({"a": float("nan"), "b": np.int64(3), "c": [np.float64(1.5)]}) == {"a": None, "b": 3, "c": [1.5]}
