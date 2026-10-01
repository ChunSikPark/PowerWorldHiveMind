"""Monitoring rules, reported with base; an N-1 or SCOPF depends on them (the n1 verdict)."""
from __future__ import annotations

import string

from casedata import RATINGS, CaseData
from findings import BROKEN, FYI, ON_PURPOSE, STOPS, Finding, bus
from thresholds import BAND_TOL_PU

N1 = ("n1",)
N1_SCOPE = "N-1 and SCOPF only"
LETTERS = string.ascii_uppercase[:len(RATINGS)]          # A..O
RATING_OF = dict(zip(LETTERS, RATINGS))                  # "A" -> "LineAMVA", "B" -> "LineAMVA:1", ...


def footprint(cd: CaseData) -> dict:
    """The monitored footprint as the case holds it - reported so nobody reads a clean N-1 as system-wide."""
    a, z, br, b = cd.get("Area"), cd.get("Zone"), cd.get("Branch"), cd.get("Bus")

    def windows(df, key):
        on = df[df.BGReportLimits == "YES"]
        return [{key: bus(r[key]), "min_kv": r["BGReportLimMinKV"], "max_kv": r["BGReportLimMaxKV"]}
                for _, r in on.iterrows()]

    return {"areas": windows(a, "AreaNum"), "areas_total": int(len(a)),
            "zones": windows(z, "ZoneNum"), "zones_total": int(len(z)),
            "branches_will_monitor": int((br["LineMonEle:1"] == "YES").sum()),
            "buses_will_monitor": int((b["BusMonEle:1"] == "YES").sum()),
            "ignore_radial": cd.scalars.get("LMS_IgnoreRadial")}


def nothing_monitored(cd: CaseData) -> list[Finding]:
    a, z, fp = cd.get("Area"), cd.get("Zone"), footprint(cd)
    groups = list(a.BGReportLimits) + list(z.BGReportLimits)
    all_off = bool(groups) and all(v == "NO" for v in groups)
    nothing = fp["branches_will_monitor"] == 0 and fp["buses_will_monitor"] == 0
    if not (all_off or nothing):
        return []
    return [Finding(
        "mon.nothing_monitored", STOPS, BROKEN,
        what="nothing in the case is monitored" + (" (every area and zone has limit reporting off)" if all_off else ""),
        why="an N-1 on this case reports no violations whatever happens",
        page="methods/reading-violationctg.md", stops=N1, scope=N1_SCOPE, details=fp)]


def no_contingencies(cd: CaseData) -> list[Finding]:
    if len(cd.get("Contingency")):
        return []
    return [Finding(
        "mon.no_contingencies", STOPS, BROKEN,
        what="the case holds no contingency records",
        why="a SCOPF secures the dispatch against its contingency list; with none, it is a plain OPF",
        page="methods/new-device-contingency-aux.md", stops=("scopf",), scope="SCOPF only")]


def monitored_footprint(cd: CaseData) -> list[Finding]:
    fp = footprint(cd)
    return [Finding(
        "mon.footprint", FYI, ON_PURPOSE,
        what=(f"an N-1 will check {len(fp['areas'])} of {fp['areas_total']} areas, "
              f"{fp['branches_will_monitor']} branches and {fp['buses_will_monitor']} buses"),
        why="a clean N-1 result covers only this footprint, not the whole system",
        page="", details=fp)]


def _in_use(cd: CaseData) -> list[tuple[str, str, str]]:
    """(limit set, which, letter) for the normal and contingency rate set of each enabled limit set."""
    ls = cd.get("LimitSet")
    ls = ls[ls.LSDisabled != "YES"]
    return [(r["LSName"], which, str(r[f]).strip().upper())
            for _, r in ls.iterrows() for which, f in (("normal", "LSLineRateSet"), ("contingency", "LSLineRateSet:1"))]


def rate_set_empty(cd: CaseData) -> list[Finding]:
    br = cd.get("Branch")
    closed = br[br.LineStatus == "Closed"]
    empty = []
    for name, which, letter in _in_use(cd):
        col = RATING_OF.get(letter)
        if col is None or not (closed[col].fillna(0) > 0).any():
            empty.append({"LSName": name, "rate_set": which, "letter": letter})
    if not empty:
        return []
    return [Finding(
        "mon.rate_set_empty", STOPS, BROKEN,
        what="a rate set the limit monitoring uses carries no ratings: "
             + ", ".join(f"{e['LSName']} {e['rate_set']} = {e['letter']}" for e in empty),
        why="with no ratings on that set, no branch can overload in the N-1",
        page="methods/powerworld-limitset-setdata.md", stops=N1, scope=N1_SCOPE, where=empty)]


def rate_sets_populated(cd: CaseData) -> list[Finding]:
    br = cd.get("Branch")
    closed = br[br.LineStatus == "Closed"]
    carried = {letter: int((closed[col].fillna(0) > 0).sum()) for letter, col in RATING_OF.items()}
    carried = {k: v for k, v in carried.items() if v}
    ls = cd.get("LimitSet")
    return [Finding(
        "mon.rate_sets_populated", FYI, ON_PURPOSE,
        what="rate sets with values: " + (", ".join(f"{k} ({v} branches)" for k, v in carried.items()) or "none"),
        why="shows which rating letters a limit set could point at",
        page="methods/reading-violationctg.md",
        details={"branches_per_letter": carried, "closed_branches": int(len(closed)),
                 "in_use": [{"LSName": n, "rate_set": w, "letter": l} for n, w, l in _in_use(cd)],
                 "amp_or_mva": dict(zip(ls.LSName, ls.LSAmpMVA))})]


def bus_limit_overrides(cd: CaseData) -> list[Finding]:
    b = cd.get("Bus")
    own, group = b[b.BusVoltLim == "YES"], b[b.BusVoltLim != "YES"]
    if own.empty:
        return []
    if group.empty:
        diff = own
    else:
        lo, hi = group.groupby(["BusVoltLimLow", "BusVoltLimHigh"]).size().idxmax()
        rel = lambda s, ref: ((s - ref).abs() / abs(ref)) > BAND_TOL_PU
        diff = own[rel(own.BusVoltLimLow, lo) | rel(own.BusVoltLimHigh, hi)]
    if diff.empty:
        return []
    return [Finding(
        "mon.bus_limit_overrides", FYI, ON_PURPOSE,
        what=f"{len(diff)} bus(es) carry their own voltage limits, different from their limit group",
        why="their violations are judged against their own band, not the case's",
        page="methods/ranking-new-devices-by-severity.md",
        where=[{"BusNum": bus(r.BusNum), "low": r.BusVoltLimLow, "high": r.BusVoltLimHigh}
               for r in diff.itertuples()])]
