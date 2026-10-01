import numpy as np

from auditcase import case
from findings import BROKEN, ON_PURPOSE, YOUR_CALL
from rules_reg import ltc_middle_target, ltc_regulates_lv_side, regulates_nothing

XF = 3                                                     # row of the 345/138 LTC in toy()


def test_healthy_regulators_are_quiet(frames):
    cd = case(frames)
    assert regulates_nothing(cd) == [] and ltc_middle_target(cd) == [] and ltc_regulates_lv_side(cd) == []


def test_shunt_pointing_at_a_missing_bus(frames):
    frames["Shunt"].loc[0, "SSRegNum"] = 99
    [f] = regulates_nothing(case(frames))
    assert f.triage == BROKEN and f.where == [{"device": "switched shunt", "BusNum": 4, "ShuntID": "1",
                                               "SSRegNum": 99, "reason": "missing"}]


def test_ltc_pointing_at_a_disconnected_bus(frames):
    frames["Bus"].loc[frames["Bus"].BusNum == 5, "BusStatus"] = "Disconnected"
    frames["Branch"].loc[XF, "XFRegBus"] = 5
    [f] = regulates_nothing(case(frames))
    assert f.where[0]["device"] == "LTC" and f.where[0]["reason"] == "disconnected"
    assert f.where[0]["LineCircuit"] == "1"


def test_zero_regulated_bus_is_a_defect(frames):
    # PowerWorld refuses to store 0 through SimAuto (probe 2026-09-30), so a 0 read back came in with the file
    frames["Branch"].loc[XF, "XFRegBus"] = 0
    [f] = regulates_nothing(case(frames))
    assert f.where[0]["reason"] == "zero"


def test_zero_mvar_shunt_with_no_target_is_a_placeholder(frames):
    frames["Shunt"].loc[0, ["SSRegNum", "SSMaxMVR", "SSMinMVR"]] = [0, 0.0, 0.0]
    [f] = regulates_nothing(case(frames))
    assert f.triage == ON_PURPOSE


def test_fixed_and_manual_devices_do_not_regulate(frames):
    frames["Shunt"].loc[0, ["SSRegNum", "SSCMode"]] = [99, "Fixed"]
    frames["Branch"].loc[XF, ["XFRegBus", "XFAuto"]] = [99, "NO"]
    assert regulates_nothing(case(frames)) == []


def test_star_bus_legs_are_skipped(frames):
    frames["Bus"].loc[frames["Bus"].BusNum == 4, "BusIsStarBus"] = "YES"
    frames["Branch"].loc[XF, "XFRegBus"] = 99
    assert regulates_nothing(case(frames)) == []


def test_middle_target_is_one_aggregated_finding(frames):
    extra = frames["Branch"].loc[XF].copy()
    extra["LineCircuit"] = "2"
    frames["Branch"].loc[len(frames["Branch"])] = extra
    frames["Branch"].loc[frames["Branch"].LineXfmr == "YES", "XFRegTargetType"] = "Middle"
    [f] = ltc_middle_target(case(frames))
    assert len(f.where) == 2 and f.details["most_common_band"] == [0.98, 1.02]
    assert f.details["midpoint"] == 1.0 and "three-winding" in f.details["three_winding"]


def test_band_copied_from_tap_range_is_not_middle_finding(frames):
    frames["Branch"].loc[XF, ["XFRegTargetType", "XFRegMin", "XFRegMax"]] = ["Middle", 0.51, 1.5]
    assert ltc_middle_target(case(frames)) == []


def test_frozen_taps_are_said(frames):
    frames["Branch"].loc[XF, "XFRegTargetType"] = "Middle"
    [f] = ltc_middle_target(case(frames, ChkTaps="NO"))
    assert "taps are frozen" in f.what and f.details["taps_move"] is False


def _hv_high(frames):
    frames["Bus"].loc[frames["Bus"].BusNum == 3, "BusPUVolt"] = 1.13
    frames["Branch"].loc[XF, ["LineTap", "XFRegError"]] = [1.1, 0.003]


def test_ltc_holding_lv_while_hv_out_of_band(frames):
    _hv_high(frames)
    [f] = ltc_regulates_lv_side(case(frames))
    w = f.where[0]
    assert f.triage == YOUR_CALL and w["hv_bus"] == 3 and w["hv_pu"] == 1.13 and w["hv_band"] == [0.9, 1.1]
    assert w["at_tap_limit"] and w["pushing_hv_away"] and f.details["pushing"] == 1


def test_lv_side_with_hv_in_band_is_quiet(frames):
    frames["Bus"].loc[frames["Bus"].BusNum == 3, "BusPUVolt"] = 1.09
    assert ltc_regulates_lv_side(case(frames)) == []


def test_generator_step_up_is_skipped_and_counted(frames):
    _hv_high(frames)
    b, br, g = frames["Bus"], frames["Branch"], frames["Gen"]
    b.loc[len(b)] = {**b.iloc[3].to_dict(), "BusNum": 7, "BusName": "BUS7", "BusNomVolt": 22.0}
    br.loc[len(br)] = {**br.loc[XF].to_dict(), "BusNum": 3, "BusNum:1": 7, "BusNomVolt:1": 22.0, "XFRegBus": 7.0}
    g.loc[len(g)] = {**g.iloc[0].to_dict(), "BusNum": 7, "GenID": "G7", "GenStatus": "Open"}   # offline still a GSU
    [f] = ltc_regulates_lv_side(case(frames))
    assert [w["BusNum:1"] for w in f.where] == [4] and f.details["generator_step_ups_skipped"] == 1


def test_a_small_unit_on_a_load_bus_is_not_a_step_up(frames):
    _hv_high(frames)
    frames["Gen"].loc[len(frames["Gen"])] = {**frames["Gen"].iloc[0].to_dict(), "BusNum": 4, "GenID": "G4"}
    [f] = ltc_regulates_lv_side(case(frames))
    assert f.details["generator_step_ups_skipped"] == 0


def test_blank_bus_limits_fall_back_to_the_study_band(frames):
    frames["Bus"].loc[frames["Bus"].BusNum == 3, ["BusPUVolt", "BusVoltLimLow", "BusVoltLimHigh"]] = [1.07, 0, 0]
    [f] = ltc_regulates_lv_side(case(frames))
    assert f.where[0]["hv_band"] == [0.94, 1.05]


def test_unread_step_makes_no_tap_limit_claim(frames):
    _hv_high(frames)
    frames["Branch"].loc[XF, "XFStep"] = np.nan
    [f] = ltc_regulates_lv_side(case(frames))
    w = f.where[0]
    assert w["hv_bus"] == 3 and w["at_tap_limit"] is False and w["pushing_hv_away"] is False
    assert f.details["pushing"] == 0


def test_zero_mvar_shunt_on_a_disconnected_target_is_still_a_placeholder(frames):
    frames["Bus"].loc[frames["Bus"].BusNum == 5, "BusStatus"] = "Disconnected"
    frames["Shunt"].loc[0, ["SSRegNum", "SSMaxMVR", "SSMinMVR"]] = [5, 0.0, 0.0]
    out = regulates_nothing(case(frames))
    assert [f.triage for f in out] == [ON_PURPOSE] and out[0].where[0]["reason"] == "disconnected"


def _gsu_bus_7(frames):
    b, g = frames["Bus"], frames["Gen"]
    b.loc[len(b)] = {**b.iloc[3].to_dict(), "BusNum": 7, "BusName": "BUS7", "BusNomVolt": 22.0}
    g.loc[len(g)] = {**g.iloc[0].to_dict(), "BusNum": 7, "GenID": "G7"}


def _xf_to_7(frames, ckt):
    br = frames["Branch"]
    br.loc[len(br)] = {**br.loc[XF].to_dict(), "BusNum": 3, "BusNum:1": 7, "BusNomVolt:1": 22.0,
                       "XFRegBus": 7.0, "LineCircuit": ckt}


def test_unit_bus_with_a_closed_line_is_not_a_step_up(frames):
    _hv_high(frames)
    _gsu_bus_7(frames)
    _xf_to_7(frames, "1")
    br = frames["Branch"]
    br.loc[len(br)] = {**br.iloc[0].to_dict(), "BusNum": 7, "BusNum:1": 6, "BusNomVolt": 22.0}   # a line at bus 7
    [f] = ltc_regulates_lv_side(case(frames))
    assert sorted(w["BusNum:1"] for w in f.where) == [4, 7] and f.details["generator_step_ups_skipped"] == 0


def test_parallel_step_ups_are_both_skipped(frames):
    _hv_high(frames)
    _gsu_bus_7(frames)
    _xf_to_7(frames, "1")
    _xf_to_7(frames, "2")
    [f] = ltc_regulates_lv_side(case(frames))
    assert [w["BusNum:1"] for w in f.where] == [4] and f.details["generator_step_ups_skipped"] == 2
