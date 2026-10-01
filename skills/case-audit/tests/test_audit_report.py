import json

from auditcase import case
from casedata import CaseData, Solve
import report

ALL = ["base", "timestep", "opf"]


def rules(r):
    return sorted({(f["rule"], f["severity"]) for f in r["findings"]})


def test_clean_hawaii40_is_ready_for_every_profile(hawaii):
    r = report.build(CaseData.from_json(hawaii), ALL)
    assert {p: v["verdict"] for p, v in r["verdicts"].items()} == {
        "base": "READY", "n1": "READY", "timestep": "READY", "opf": "READY", "scopf": "READY"}
    assert r["verdicts"]["timestep"]["reason"] == "9 of 9 renewables will follow the weather"
    assert rules(r) == [("base.stale_ctg_results", "FYI"), ("mon.footprint", "FYI"),
                        ("mon.rate_sets_populated", "FYI"), ("ts.pww_footprint", "FYI")]


def test_seeded_defects_are_reported_and_nothing_new(hawaii):
    clean = report.build(CaseData.from_json(hawaii), ALL)
    cd = CaseData.from_json(hawaii)
    g, sh = cd.frames["Gen"], cd.frames["Shunt"]
    ren = g.index[g.GenFuelType.str.contains("WND|SUN")][:3]
    g.loc[ren, "TSPFWModelString"] = ""                       # strip PFW from 3 units
    sh.loc[0, "SSRegNum"] = 0                                 # zero the one switched shunt's regulated bus
    g.loc[g.GenAGCAble == "YES", "GenCostModel"] = "None"     # no cost model on any movable unit
    r = report.build(cd, ALL)
    new = set(rules(r)) - set(rules(clean))
    assert new == {("ts.pfw_missing", "Worth a look"), ("base.regulates_nothing", "Worth a look"),
                   ("opf.3", "Stops the study")}
    pfw = next(f for f in r["findings"] if f["rule"] == "ts.pfw_missing")
    assert pfw["count"] == 3 and r["verdicts"]["timestep"]["verdict"] == "READY"
    assert r["verdicts"]["opf"]["verdict"] == "NOT READY" and r["verdicts"]["base"]["verdict"] == "READY"
    assert r["verdicts"]["scopf"]["verdict"] == "NOT READY"


def test_unsolved_case_is_not_ready_and_says_what_was_not_checked(frames):
    r = report.build(case(frames, converged=False), ALL)
    assert all(v["verdict"] == "NOT READY" for v in r["verdicts"].values())
    assert {s["rule"] for s in r["rules_skipped"]} == {
        "base.gen_over_nameplate", "base.ltc_regulates_lv_side", "base.floating_stub"}
    assert r["case_summary"]["from_unsolved_case"] and "did not solve" in report.render_md(r)


def test_floating_stub_is_skipped_not_run_without_a_solve(frames):
    r = report.build(case(frames, converged=False), ["base"])
    assert not [f for f in r["findings"] if f["rule"] == "base.floating_stub"]
    assert "base.floating_stub" not in r["rules_run"]
    skip = next(s for s in r["rules_skipped"] if s["rule"] == "base.floating_stub")
    assert "did not solve" in skip["reason"]
    assert "- base.floating_stub:" in report.render_md(r)


def test_an_unread_tolerance_is_decided_on_the_raise_and_recorded(frames):
    cd = CaseData(frames, {"SBase": "100", "ChkTaps": "YES"}, Solve(True, None, 0.01, None))
    r = report.build(cd, ["base"])
    assert r["verdicts"]["base"]["verdict"] == "READY" and r["solve"]["tolerance_unread"]


def test_base_always_runs_and_n1_is_always_reported(frames):
    r = report.build(case(frames), ["timestep"])
    assert r["profiles"] == ["base", "timestep"] and list(r["verdicts"]) == ["base", "n1", "timestep"]
    assert r["opf_areas"] is None


def test_scopf_needs_a_contingency_list(frames):
    frames["Contingency"] = None
    r = report.build(case(frames), ["opf"])
    assert r["verdicts"]["opf"]["verdict"] == "READY" and r["verdicts"]["scopf"]["verdict"] == "NOT READY"
    assert r["verdicts"]["scopf"]["stopped_by"] == ["mon.no_contingencies"]


def test_no_opf_area_stops_opf_on_opf1_only_and_shows_the_preview(frames):
    frames["Area"]["BGAGC"] = "Participation"          # no area on OPF
    r = report.build(case(frames), ["opf"])
    ids = {f["rule"] for f in r["findings"]}
    assert {"opf.1", "opf.preview"} <= ids
    prev = next(f for f in r["findings"] if f["rule"] == "opf.preview")
    assert prev["stops"] == [] and prev["severity"] == "Worth a look"
    assert r["verdicts"]["opf"]["verdict"] == "NOT READY"
    assert r["verdicts"]["opf"]["stopped_by"] == ["opf.1"]
    assert "opf.preview" not in {x for v in r["verdicts"].values() for x in v["stopped_by"]}
    assert "opf.preview" in report.render_md(r)


def test_a_replay_says_it_opened_no_case(frames):
    r = report.build(case(frames), ["base"], source="snapshot")
    assert r["source"] == "snapshot" and r["read_only"] == {"sha256_before": None, "sha256_after": None,
                                                            "unchanged": None}
    assert report.render_md(r).splitlines()[0] == "Replayed from a stored snapshot; no case was opened."


def test_handoffs_become_what_you_need_to_get(frames):
    frames["Gen"].loc[1, "TSPFWModelString"] = ""
    md = report.render_md(report.build(case(frames), ["timestep"]))
    assert "## What you need to get" in md and "1. time step will run" in md and "Auto_PFW" in md


def test_files_are_utf8_whatever_the_names(frames, tmp_path):
    frames["Bus"].loc[2, "BusName"] = "Kāneʻohe 345"
    frames["Bus"].loc[frames["Bus"].BusNum == 3, "BusPUVolt"] = 1.13
    frames["Branch"].loc[3, ["LineTap", "XFRegError"]] = [1.1, 0.003]
    j, m = report.write(report.build(case(frames), ALL), tmp_path)
    text = m.read_text(encoding="utf-8")
    assert "Kāneʻohe 345" in text and "## Verdict" in text and "## What's in the case" in text
    assert "N-1 will check: areas 1 (of 1), all kV" in text and "## Can the OPF run?" in text
    assert json.loads(j.read_text(encoding="utf-8"))["findings"]


def test_json_never_carries_nan(frames, tmp_path):
    # a NaN that reaches the output: the solve's tolerance is written straight into the JSON
    cd = CaseData(frames, {"SBase": "100", "ChkTaps": "YES"}, Solve(True, None, 0.0, float("nan")))
    j, _ = report.write(report.build(cd, ["base"]), tmp_path)
    text = j.read_text(encoding="utf-8")

    def refuse(token):
        raise AssertionError(f"non-standard JSON token {token}")

    data = json.loads(text, parse_constant=refuse)          # strict: NaN / Infinity raise
    assert "NaN" not in text and "Infinity" not in text
    assert data["solve"]["tolerance_mva"] is None
