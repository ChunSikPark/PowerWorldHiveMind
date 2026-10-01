"""Regulator rules: what each LTC and switched shunt holds (methods/ltc-regulation-checks.md)."""
from __future__ import annotations

import pandas as pd

from casedata import CaseData
from findings import BROKEN, ON_PURPOSE, WORTH, YOUR_CALL, Finding, branch_keys, bus
from thresholds import BAND_TOL_PU, FALLBACK_BAND, KV_SAME_REL, LTC_BAND_CAN_ACT_PU

PAGE = "methods/ltc-regulation-checks.md"
REGULATING_MODES = {"Discrete", "Continuous", "SVC"}
THREE_WINDING = "three-winding transformers are not checked in this version"
ZERO_MVAR_EPS = 1e-6             # Mvar: a shunt range this small reads as 0 (placeholder, not a real range)
TAP_LIMIT_STEP_FRACTION = 0.5    # a tap within half a step of its limit counts as at the limit


def active_ltcs(cd: CaseData) -> pd.DataFrame:
    """Closed LTCs on automatic control, two-winding only (a leg touching a star bus is skipped)."""
    br, b = cd.get("Branch"), cd.get("Bus")
    star = set(b.BusNum[b.BusIsStarBus == "YES"])
    m = ((br.LineXfmr == "YES") & (br.LineXFType == "LTC") & (br.XFAuto == "YES")
         & (br.LineStatus == "Closed") & ~br.BusNum.isin(star) & ~br["BusNum:1"].isin(star))
    return br[m]


def taps_move(cd: CaseData) -> bool:
    return str(cd.scalars.get("ChkTaps", "YES")).strip().upper() == "YES"


def _target(reg, status: dict) -> str | None:
    """Why a regulated-bus number is no target: 'zero', 'missing', 'disconnected', or None if fine."""
    if pd.isna(reg) or reg == 0:
        return "zero"
    if reg not in status:
        return "missing"
    return "disconnected" if status[reg] == "Disconnected" else None


def regulates_nothing(cd: CaseData) -> list[Finding]:
    b = cd.get("Bus")
    status = dict(zip(b.BusNum, b.BusStatus))
    broken, placeholders = [], []
    sh = cd.get("Shunt")
    sh = sh[(sh.SSStatus == "Closed") & sh.SSCMode.isin(REGULATING_MODES) & (sh.AutoControl == "YES")]
    for r in sh.itertuples():
        if status.get(r.BusNum) == "Disconnected":
            continue                                   # a de-energised regulator is not this defect
        why = _target(r.SSRegNum, status)
        if why:
            row = {"device": "switched shunt", "BusNum": bus(r.BusNum), "ShuntID": r.ShuntID,
                   "SSRegNum": None if pd.isna(r.SSRegNum) else bus(r.SSRegNum), "reason": why}
            empty = abs(r.SSMaxMVR) < ZERO_MVAR_EPS and abs(r.SSMinMVR) < ZERO_MVAR_EPS
            (placeholders if empty else broken).append(row)
    for _, r in active_ltcs(cd).iterrows():
        if "Disconnected" in (status.get(r["BusNum"]), status.get(r["BusNum:1"])):
            continue
        why = _target(r["XFRegBus"], status)
        if why:
            broken.append({"device": "LTC", **branch_keys(r),
                           "XFRegBus": None if pd.isna(r["XFRegBus"]) else bus(r["XFRegBus"]), "reason": why})
    out = []
    if broken:
        out.append(Finding(
            "base.regulates_nothing", WORTH, BROKEN,
            what=f"{len(broken)} regulator(s) point at a bus that does not exist or is out of service",
            why="the case still solves, but these devices hold nothing the modeller intended",
            page=PAGE, where=broken, details={"three_winding": THREE_WINDING}))
    if placeholders:
        out.append(Finding(
            "base.regulates_nothing", WORTH, ON_PURPOSE,
            what=f"{len(placeholders)} switched shunt(s) with a 0 Mvar range and no regulated bus",
            why="a 0 Mvar shunt with no target is usually a placeholder, not a defect",
            page=PAGE, where=placeholders))
    return out


def ltc_middle_target(cd: CaseData) -> list[Finding]:
    ltc = active_ltcs(cd)
    ltc = ltc[(ltc.XFRegTargetType == "Middle") & ((ltc.XFRegMax - ltc.XFRegMin) <= LTC_BAND_CAN_ACT_PU)]
    if ltc.empty:
        return []
    bands = ltc.groupby(["XFRegMin", "XFRegMax"]).size().sort_values(ascending=False)
    (lo, hi), n_band = bands.index[0], int(bands.iloc[0])
    where = [{**branch_keys(r), "XFRegBus": None if pd.isna(r["XFRegBus"]) else bus(r["XFRegBus"]),
              "XFRegMin": r["XFRegMin"], "XFRegMax": r["XFRegMax"],
              "midpoint": (r["XFRegMin"] + r["XFRegMax"]) / 2} for _, r in ltc.iterrows()]
    frozen = "" if taps_move(cd) else " (taps are frozen in this case: Sim_Solution_Options.ChkTaps is not YES)"
    return [Finding(
        "base.ltc_middle_target", WORTH, BROKEN,
        what=(f"{len(ltc)} active LTC(s) drive to the middle of their band, not into it; most common band "
              f"{lo:.3f}-{hi:.3f} pu ({n_band} units), midpoint {(lo + hi) / 2:.4f}{frozen}"),
        why="out of band, a Middle target pulls the bus to the midpoint, so a band tuned to the limit overshoots",
        page=PAGE, where=where,
        details={"count": len(ltc), "most_common_band": [lo, hi], "units_on_that_band": n_band,
                 "midpoint": (lo + hi) / 2, "taps_move": taps_move(cd), "three_winding": THREE_WINDING})]


def step_up_buses(cd: CaseData) -> set:
    """A generator step-up's LV bus: it has a unit (any status), no closed load, and every closed
    branch at it is a transformer - parallel step-ups included."""
    g, ld, br = cd.get("Gen"), cd.get("Load"), cd.get("Branch")
    closed = br[br.LineStatus == "Closed"]
    ends = pd.concat([closed[["BusNum", "LineXfmr"]],
                      closed[["BusNum:1", "LineXfmr"]].rename(columns={"BusNum:1": "BusNum"})])
    only_xf = ends.groupby("BusNum").LineXfmr.agg(lambda s: bool((s == "YES").all()))
    candidates = set(g.BusNum) - set(ld.BusNum[ld.LoadStatus == "Closed"])
    return {b for b in candidates if only_xf.get(b, False)}


def _band(r) -> tuple[float, float]:
    lo, hi = r["BusVoltLimLow"], r["BusVoltLimHigh"]
    if pd.isna(lo) or pd.isna(hi) or lo <= 0 or hi <= 0:
        return FALLBACK_BAND
    return float(lo), float(hi)


def ltc_regulates_lv_side(cd: CaseData) -> list[Finding]:
    b = cd.get("Bus").set_index("BusNum")
    gsu_buses = step_up_buses(cd)
    where, gsu = [], 0
    for _, r in active_ltcs(cd).iterrows():
        kf, kt = r["BusNomVolt"], r["BusNomVolt:1"]
        if pd.isna(kf) or pd.isna(kt) or abs(kf - kt) <= KV_SAME_REL * max(kf, kt):
            continue
        hv, lv = (r["BusNum"], r["BusNum:1"]) if kf > kt else (r["BusNum:1"], r["BusNum"])
        lv_kv, reg = min(kf, kt), r["XFRegBus"]
        lv_side = reg == lv or (reg not in (hv, lv) and reg in b.index
                                and b.at[reg, "BusNomVolt"] <= lv_kv * (1 + KV_SAME_REL))
        if not lv_side or hv not in b.index:
            continue
        lo, hi = _band(b.loc[hv])
        v = b.at[hv, "BusPUVolt"]
        if lo - BAND_TOL_PU <= v <= hi + BAND_TOL_PU:
            continue
        if lv in gsu_buses:
            gsu += 1
            continue
        if pd.notna(r["XFStep"]):
            half = r["XFStep"] * TAP_LIMIT_STEP_FRACTION
            at_limit = abs(r["LineTap"] - r["XFTapMax"]) < half or abs(r["LineTap"] - r["XFTapMin"]) < half
        else:
            at_limit = False                           # step unread: tap position unknown, claim nothing
        pushing = bool(at_limit and pd.notna(r["XFRegError"]) and r["XFRegError"] != 0)
        where.append({**branch_keys(r), "XFRegBus": bus(reg), "hv_bus": bus(hv),
                      "hv_bus_name": b.at[hv, "BusName"], "hv_pu": v, "hv_band": [lo, hi],
                      "lv_pu": b.at[lv, "BusPUVolt"] if lv in b.index else None,
                      "LineTap": r["LineTap"], "XFTapMin": r["XFTapMin"], "XFTapMax": r["XFTapMax"],
                      "XFRegError": r["XFRegError"], "LineMVA": r["LineMVA"],
                      "at_tap_limit": bool(at_limit), "pushing_hv_away": pushing})
    if not where:
        return []
    pushing = sum(w["pushing_hv_away"] for w in where)
    return [Finding(
        "base.ltc_regulates_lv_side", WORTH, YOUR_CALL,
        what=(f"{len(where)} LTC(s) hold their low-voltage side while the high-voltage side is out of band"
              + (f"; {pushing} sit at a tap limit, actively pushing the high side away" if pushing else "")),
        why="a tap moves Mvar from one side to the other: holding the LV bus can cause the HV violation "
            "(right for a distribution tap, wrong for a bulk transformer)",
        page=PAGE, where=where,
        details={"count": len(where), "pushing": pushing, "generator_step_ups_skipped": gsu,
                 "taps_move": taps_move(cd), "three_winding": THREE_WINDING})]
