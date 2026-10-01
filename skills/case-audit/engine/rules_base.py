"""base rules: does the AC solve, is the network real, is any unit past its rating, stale results."""
from __future__ import annotations

import numpy as np

from casedata import CaseData
from findings import AC_STUDIES, BROKEN, FYI, ON_PURPOSE, STOPS, WORTH, Finding, branch_keys, bus
from thresholds import (DC_SKELETON_MEDIAN_XR, DC_SKELETON_PARTIAL_SHARE, DC_SKELETON_SHARE, GEN_OVER_MIN_MW,
                        GEN_OVER_STOP_MW, GEN_OVER_STOP_SHARE, TINY_R)


def ac_converges(cd: CaseData) -> list[Finding]:
    s = cd.solve
    if s.converged:
        return []
    if s.raised:
        how = f"PowerWorld stopped the AC solve: {s.raised}"
    else:
        how = f"the largest bus mismatch is {s.max_mismatch_mva} MVA against a tolerance of {s.tolerance_mva} MVA"
    return [Finding(
        "base.ac_converges", STOPS, BROKEN,
        what="the AC power flow does not solve on the case as it opened",
        why=f"{how}; nothing read after an unsolved power flow can be trusted",
        page="methods/handling-errors.md", stops=AC_STUDIES,
        details={"raised": s.raised, "max_mismatch_mva": s.max_mismatch_mva,
                 "tolerance_mva": s.tolerance_mva})]


def dc_skeleton(cd: CaseData) -> list[Finding]:
    br = cd.get("Branch")
    lines = br[(br.LineStatus == "Closed") & (br.LineXfmr == "NO")]
    if lines.empty:
        return []
    ratio = (lines.LineX / lines.LineR.replace(0, np.nan)).dropna()
    xr = float(ratio.median()) if len(ratio) else float("nan")
    no_r_no_c = (lines.LineR <= TINY_R) & (lines.LineC == 0)
    share = float(no_r_no_c.mean())
    xr_text = "undefined (R = 0 on every line)" if np.isnan(xr) else f"{xr:,.0f}"
    details = {"median_xr": xr, "share_no_r_no_c": share, "closed_lines": int(len(lines)),
               "lines_with_no_r_no_c": int(no_r_no_c.sum()), "lines_with_zero_charging": int((lines.LineC == 0).sum())}
    if np.isnan(xr) or xr > DC_SKELETON_MEDIAN_XR or share >= DC_SKELETON_SHARE:
        return [Finding(
            "base.dc_skeleton", STOPS, BROKEN,
            what=f"a DC-only skeleton: median X/R {xr_text}, and {share:.0%} of closed lines have no resistance and no charging",
            why="the lines carry no real resistance or charging, so AC flows, losses and voltages are artifacts",
            page="concepts/case-impedance-completeness.md", stops=AC_STUDIES,
            scope="every AC study; a DC-only study can still run", details=details)]
    if share >= DC_SKELETON_PARTIAL_SHARE:
        return [Finding(
            "base.dc_skeleton", WORTH, BROKEN,
            what=f"part of the network is a DC skeleton: {int(no_r_no_c.sum())} of {len(lines)} closed lines ({share:.0%}) have no resistance and no charging",
            why="flows and voltages on those lines are artifacts; the rest of the case is real",
            page="concepts/case-impedance-completeness.md", details=details,
            where=[branch_keys(r) for _, r in lines[no_r_no_c].iterrows()])]
    return []


def gen_over_nameplate(cd: CaseData) -> list[Finding]:
    g = cd.get("Gen")
    on = g[g.GenStatus == "Closed"].copy()
    on["over"] = on.GenMW - on.GenMWMax
    on = on[on.over > GEN_OVER_MIN_MW]
    if on.empty:
        return []
    slack = set(cd.get("Bus").query("BusCat == 'Slack'").BusNum)
    size = np.maximum(GEN_OVER_STOP_SHARE * on.GenMWMax, GEN_OVER_STOP_MW)
    out = []
    for stop, part in ((True, on[on.over > size]), (False, on[on.over <= size])):
        if part.empty:
            continue
        where = [{"BusNum": bus(r.BusNum), "GenID": r.GenID, "GenMW": r.GenMW, "GenMWMax": r.GenMWMax,
                  "over_mw": round(r.over, 3), "slack": r.BusNum in slack} for r in part.itertuples()]
        total = float(part.over.sum())
        out.append(Finding(
            "base.gen_over_nameplate", STOPS if stop else WORTH, BROKEN,
            what=f"{len(part)} online unit(s) above their rating after the solve, {total:,.1f} MW over in all",
            why=("an overshoot this large means the dispatch does not match the ratings (at the slack, it is "
                 "a shortfall the slack absorbed), so the flows are artifacts" if stop else
                 "the case runs; the overshoot is small enough not to move a finding"),
            page="methods/applying-a-dispatch-to-a-case.md", stops=AC_STUDIES if stop else (),
            where=where, details={"over_mw": total}))
    return out


def stale_ctg_results(cd: CaseData) -> list[Finding]:
    n = len(cd.get("ViolationCTG"))
    if not n:
        return []
    return [Finding(
        "base.stale_ctg_results", FYI, ON_PURPOSE,
        what=f"the case already holds {n} contingency violation rows from an earlier run",
        why="they describe whatever the case was when that run happened, not this audit - do not read them",
        page="methods/reading-violationctg.md", details={"rows": n})]
