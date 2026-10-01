import pytest

from auditcase import case
from findings import BROKEN, FYI, ON_PURPOSE, STOPS
from rules_mon import (bus_limit_overrides, monitored_footprint, no_contingencies, nothing_monitored,
                       rate_set_empty, rate_sets_populated)


def test_monitored_case_is_quiet(frames):
    cd = case(frames)
    assert nothing_monitored(cd) == [] and rate_set_empty(cd) == [] and bus_limit_overrides(cd) == []


def test_every_area_and_zone_off_stops_n1_only(frames):
    frames["Area"].BGReportLimits = "NO"
    frames["Zone"].BGReportLimits = "NO"
    [f] = nothing_monitored(case(frames))
    assert f.severity == STOPS and f.stops == ("n1",) and f.label == "Stops the study — N-1 and SCOPF only"


def test_no_element_will_monitor(frames):
    frames["Branch"]["LineMonEle:1"] = "NO"
    frames["Bus"]["BusMonEle:1"] = "NO"
    assert nothing_monitored(case(frames))[0].rule == "mon.nothing_monitored"


def test_no_contingency_records_stops_scopf_only(frames):
    assert no_contingencies(case(frames)) == []
    frames["Contingency"] = None
    [f] = no_contingencies(case(frames))
    assert f.stops == ("scopf",) and f.label == "Stops the study — SCOPF only"


def test_footprint_is_always_reported(frames):
    [f] = monitored_footprint(case(frames, LMS_IgnoreRadial="NO"))
    assert f.severity == FYI and f.details["areas"] == [{"AreaNum": 1, "min_kv": 0.0, "max_kv": 9999.0}]
    assert f.details["branches_will_monitor"] == 6 and f.details["ignore_radial"] == "NO"


def test_contingency_rate_set_with_no_ratings(frames):
    frames["LimitSet"].loc[0, "LSLineRateSet:1"] = "D"
    [f] = rate_set_empty(case(frames))
    assert f.where == [{"LSName": "Default", "rate_set": "contingency", "letter": "D"}]


def test_disabled_limit_set_is_not_checked(frames):
    frames["LimitSet"].loc[0, ["LSLineRateSet", "LSDisabled"]] = ["D", "YES"]
    assert rate_set_empty(case(frames)) == []


def test_populated_letters(frames):
    [f] = rate_sets_populated(case(frames))
    assert f.details["branches_per_letter"] == {"A": 6, "B": 6, "C": 6}
    assert f.details["amp_or_mva"] == {"Default": "MVA"}


def test_bus_with_its_own_limits(frames):
    b = frames["Bus"]
    b.loc[b.BusNum == 2, ["BusVoltLim", "BusVoltLimLow", "BusVoltLimHigh"]] = ["YES", 0.95, 1.04]
    [f] = bus_limit_overrides(case(frames))
    assert f.where == [{"BusNum": 2, "low": 0.95, "high": 1.04}]


def test_own_limits_equal_to_the_group_band_are_not_reported(frames):
    b = frames["Bus"]
    b.loc[b.BusNum == 2, ["BusVoltLim", "BusVoltLimLow", "BusVoltLimHigh"]] = ["YES", 0.89999998, 1.10000002]
    assert bus_limit_overrides(case(frames)) == []


def test_nothing_monitored_severity_triage(frames):
    """mon.nothing_monitored must have severity=STOPS, triage=BROKEN, stops=n1 only."""
    frames["Area"].BGReportLimits = "NO"
    frames["Zone"].BGReportLimits = "NO"
    [f] = nothing_monitored(case(frames))
    assert f.severity == STOPS and f.triage == BROKEN and f.stops == ("n1",)
    assert "N-1 and SCOPF only" in f.label


def test_rate_set_empty_severity_triage(frames):
    """mon.rate_set_empty must have severity=STOPS, triage=BROKEN, stops=n1 only."""
    frames["LimitSet"].loc[0, "LSLineRateSet:1"] = "D"
    [f] = rate_set_empty(case(frames))
    assert f.severity == STOPS and f.triage == BROKEN and f.stops == ("n1",)
    assert "N-1 and SCOPF only" in f.label


def test_monitored_footprint_severity_triage(frames):
    """mon.footprint must have severity=FYI, triage=ON_PURPOSE."""
    [f] = monitored_footprint(case(frames, LMS_IgnoreRadial="NO"))
    assert f.severity == FYI and f.triage == ON_PURPOSE and f.stops == ()


def test_rate_sets_populated_severity_triage(frames):
    """mon.rate_sets_populated must have severity=FYI, triage=ON_PURPOSE."""
    [f] = rate_sets_populated(case(frames))
    assert f.severity == FYI and f.triage == ON_PURPOSE and f.stops == ()


def test_bus_limit_overrides_severity_triage(frames):
    """mon.bus_limit_overrides must have severity=FYI, triage=ON_PURPOSE."""
    b = frames["Bus"]
    b.loc[b.BusNum == 2, ["BusVoltLim", "BusVoltLimLow", "BusVoltLimHigh"]] = ["YES", 0.95, 1.04]
    [f] = bus_limit_overrides(case(frames))
    assert f.severity == FYI and f.triage == ON_PURPOSE and f.stops == ()


def test_no_contingencies_severity_triage(frames):
    """mon.no_contingencies must have severity=STOPS, triage=BROKEN, stops=scopf only."""
    frames["Contingency"] = None
    [f] = no_contingencies(case(frames))
    assert f.severity == STOPS and f.triage == BROKEN and f.stops == ("scopf",)
    assert "SCOPF only" in f.label
