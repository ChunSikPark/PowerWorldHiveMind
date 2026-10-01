"""The case summary: facts, not findings. The agent presents these numbers; it never recomputes them."""
from __future__ import annotations

import pandas as pd

from casedata import CaseData
from thresholds import GEN_OVER_MIN_MW, RENEWABLE_CODES


def is_renewable(fuel: pd.Series) -> pd.Series:
    """GenFuelType *contains* WND or SUN: the case labels them 'WND (Wind)', 'SUN (Solar)'."""
    return fuel.str.upper().str.contains("|".join(RENEWABLE_CODES), regex=True)


def opf_super_areas(cd: CaseData) -> list[str]:
    sa = cd.get("SuperArea")
    return list(sa.SAName[sa.BGAGC.str.upper() == "OPF"])


def opf_areas(cd: CaseData) -> set:
    """Areas the OPF may redispatch: BGAGC = OPF, or a member (Area.SAName) of a super area on OPF.
    Measured 2026-09-30 on two public synthetic cases: an OPF solved with only the super area on
    OPF (every area Off AGC), and with an area on OPF inside a super area that was Off AGC."""
    a = cd.get("Area")
    return set(a.AreaNum[(a.BGAGC.str.upper() == "OPF") | a.SAName.isin(opf_super_areas(cd))])


def case_summary(cd: CaseData, opf: bool = False) -> dict:
    gen, load, sh, bus, br = (cd.get(o) for o in ("Gen", "Load", "Shunt", "Bus", "Branch"))
    on = gen[gen.GenStatus == "Closed"].copy()
    ld = load[load.LoadStatus == "Closed"]
    on["renewable"] = is_renewable(on.GenFuelType)
    on["headroom"] = (on.GenMWMax - on.GenMW).clip(lower=0)
    gen_mw, load_mw = float(on.GenMW.sum()), float(ld.LoadMW.sum())
    dispatchable = on[~on.renewable]
    fuel = gen.GenFuelType.replace("", "(blank)")
    rows = []
    for label in sorted(fuel.unique()):
        units = gen[fuel == label]
        u_on = on[on.GenFuelType.replace("", "(blank)") == label]
        weather = bool(is_renewable(pd.Series([label])).iloc[0])
        rows.append({
            "fuel": label,
            "units_online": int(len(u_on)), "units_total": int(len(units)),
            "installed_mw": float(units.GenMWMax.sum()), "output_mw": float(u_on.GenMW.sum()),
            "share_of_output": float(u_on.GenMW.sum() / gen_mw) if gen_mw else 0.0,
            "headroom_mw": None if weather else float(u_on.headroom.sum()),
            "weather_limited": weather,
        })
    shin = sh[sh.SSStatus == "Closed"]
    kv = sorted({round(float(v), 1) for v in bus.BusNomVolt.dropna() if v > 0})
    over = (on.GenMW - on.GenMWMax)
    out = {
        "load_mw": load_mw, "load_mvar": float(ld.LoadMVR.sum()),
        "generation_mw": gen_mw, "generation_mvar": float(on.GenMVR.sum()),
        "losses_mw": gen_mw - load_mw,
        "headroom_dispatchable_mw": float(dispatchable.headroom.sum()),
        "generation_includes_overshoot_mw": float(over[over > GEN_OVER_MIN_MW].sum()),
        "mvar_range": [float(on.GenMVRMin.sum()), float(on.GenMVRMax.sum())],
        "fuel": rows,
        "shunts": {"count": int(len(sh)), "in_service": int(len(shin)),
                   "mvar_now": float(shin.SSAMVR.sum()),
                   "capacitive_mvar": float(shin.SSMaxMVR.sum()),
                   "inductive_mvar": float(shin.SSMinMVR.sum())},
        "size": {"buses": int(len(bus)), "branches": int(len(br)),
                 "transformers": int((br.LineXfmr == "YES").sum()),
                 "areas": int(len(cd.get("Area"))), "zones": int(len(cd.get("Zone"))),
                 "kv_levels": kv},
        "contingencies": int(len(cd.get("Contingency"))),
        "from_unsolved_case": not cd.solve.converged,
    }
    if opf:
        areas = opf_areas(cd)
        movable = on[(on.GenAGCAble == "YES") & on.AreaNum.isin(areas) & ~on.renewable]
        out["opf_movable_headroom_mw"] = float(movable.headroom.sum())
    return out
