import pandas as pd

from auditcase import case
from findings import FYI, ON_PURPOSE, STOPS, WORTH, YOUR_CALL
from rules_opf import area_table, opf_conditions


def test_all_three_conditions_hold(frames):
    assert opf_conditions(case(frames)) == []


def test_no_opf_area_or_super_area(frames):
    frames["Area"].loc[0, "BGAGC"] = "Off AGC"
    [f] = opf_conditions(case(frames))
    assert f.rule == "opf.1" and f.severity == STOPS and f.triage == YOUR_CALL and f.stops == ("opf",)


def test_a_super_area_on_opf_counts_and_its_areas_are_checked(frames):
    # measured 2026-09-30: an OPF solved with only the super area on OPF, every area Off AGC
    frames["Area"].loc[0, ["BGAGC", "SAName"]] = ["Off AGC", "Texas"]
    frames["SuperArea"] = pd.DataFrame({"SAName": ["Texas"], "BGAGC": ["OPF"]})
    assert opf_conditions(case(frames)) == []
    frames["Gen"].GenCostCurvePoints = 0
    assert [f.rule for f in opf_conditions(case(frames))] == ["opf.3"]


def _super_area_with_a_load_only_member(frames):
    frames["Area"].loc[0, ["BGAGC", "SAName"]] = ["Off AGC", "S"]
    frames["Area"].loc[1] = {**frames["Area"].iloc[0].to_dict(), "AreaNum": 2}       # no units at all
    frames["SuperArea"] = pd.DataFrame({"SAName": ["S"], "BGAGC": ["OPF"]})


def test_a_load_only_member_of_an_opf_super_area_is_fyi_not_a_stop(frames):
    _super_area_with_a_load_only_member(frames)
    [f] = opf_conditions(case(frames))
    assert (f.rule, f.severity, f.triage) == ("opf.2", FYI, ON_PURPOSE)
    assert f.where == [{"AreaNum": 2, "SAName": "S", "movable_units": 0, "priced_units": 0}]


def test_an_unpriced_super_area_stops_as_one_group(frames):
    _super_area_with_a_load_only_member(frames)
    frames["Gen"].GenCostCurvePoints = 0
    [f] = opf_conditions(case(frames))
    assert (f.rule, f.severity) == ("opf.3", STOPS) and f.where == [{"SAName": "S", "areas": [1, 2], "movable_units": 3}]
    assert "super area S" in f.what


def test_an_area_on_opf_inside_a_super_area_off_agc_counts(frames):
    # measured 2026-09-30: the OPF solved with the area on OPF and its super area Off AGC
    frames["Area"].loc[0, "SAName"] = "FullCase"
    frames["SuperArea"] = pd.DataFrame({"SAName": ["FullCase"], "BGAGC": ["Off AGC"]})
    assert opf_conditions(case(frames)) == []


def test_opf_area_with_no_agc_unit(frames):
    frames["Gen"].GenAGCAble = "NO"
    [f] = opf_conditions(case(frames))
    assert f.rule == "opf.2" and f.details["agc_off_everywhere"] and "dispatch" in f.why


def test_one_unpriced_area_stops_even_when_another_is_priced(frames):
    frames["Area"].loc[1] = {**frames["Area"].iloc[0].to_dict(), "AreaNum": 2}
    frames["Gen"].loc[0, ["AreaNum", "GenCostCurvePoints"]] = [2, 0]      # area 2's only unit: no curve
    [f] = opf_conditions(case(frames))
    assert f.rule == "opf.3" and f.severity == STOPS and f.where == [{"AreaNum": 2, "movable_units": 1}]
    assert "cost-data source" in f.handoff


def test_cost_model_none_is_no_data(frames):
    frames["Gen"].GenCostModel = "None"
    assert opf_conditions(case(frames))[0].severity == STOPS


def test_an_unpriced_unit_beside_priced_ones_is_worth_a_look(frames):
    frames["Gen"].loc[0, "GenCostCurvePoints"] = 0
    [f] = opf_conditions(case(frames))
    assert (f.rule, f.severity, f.triage) == ("opf.3", WORTH, YOUR_CALL) and [w["GenID"] for w in f.where] == ["1"]


def test_zero_cost_renewables_are_priced(frames):
    frames["Gen"].loc[[1, 2], "GenMCost"] = 0.0                  # wind and solar: curve points, price 0
    assert opf_conditions(case(frames)) == []


def test_a_thermal_unit_at_zero_cost_is_probably_on_purpose(frames):
    frames["Gen"].loc[0, "GenMCost"] = 0.0
    [f] = opf_conditions(case(frames))
    assert (f.rule, f.severity, f.triage) == ("opf.3", WORTH, ON_PURPOSE) and f.handoff == ""


def test_area_table(frames):
    [a] = area_table(case(frames))
    assert a == {"AreaNum": 1, "BGAGC": "OPF", "SAName": "", "opf": True, "via_super_area": False,
                 "agc_units": 3, "with_curve": 3, "cost_above_zero": 3, "cost_models": {"Cubic": 3}}
