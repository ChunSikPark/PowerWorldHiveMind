"""base.floating_stub: a lightly loaded EHV dead end rising on its own line charging
(concepts/unloaded-ehv-stub-overvoltage.md)."""
from __future__ import annotations

import pandas as pd

from casedata import CaseData
from findings import WORTH, YOUR_CALL, Finding, branch_keys, bus
from thresholds import (EHV_KV, FALLBACK_BAND, STUB_LIGHT_MW, STUB_LIGHT_PERCENT, STUB_MAX_BUSES,
                        STUB_RISE_PU)
from topology import adjacency, far_side, pockets

PAGE = "concepts/unloaded-ehv-stub-overvoltage.md"


def floating_stub(cd: CaseData) -> list[Finding]:
    b = cd.get("Bus")
    b = b[b.BusStatus == "Connected"].set_index("BusNum")
    br = cd.get("Branch")
    br = br[(br.LineStatus == "Closed") & br.BusNum.isin(b.index) & br["BusNum:1"].isin(b.index)]
    br = br.reset_index(drop=True)
    ehv = set(b.index[b.BusNomVolt >= EHV_KV])
    edges = list(zip(br.BusNum, br["BusNum:1"]))
    info, adj = pockets(list(b.index), edges), adjacency(edges)
    g, sh = cd.get("Gen"), cd.get("Shunt")
    g, sh = g[g.GenStatus == "Closed"], sh[sh.SSStatus == "Closed"]
    sbase = float(cd.scalars.get("SBase") or 100.0)
    passing = {}
    for k, v in info.items():
        if not (br.at[k, "LineXfmr"] == "NO" and v["near"] in ehv and v["far"] in ehv
                and v["size"] <= STUB_MAX_BUSES):
            continue
        side = far_side(adj, k, v["far"], STUB_MAX_BUSES)
        if side is None:
            continue
        r, near = br.loc[k], v["near"]
        light = r.LineMaxPercent < STUB_LIGHT_PERCENT if r.LineAMVA > 0 else abs(r.LineMW) < STUB_LIGHT_MW
        far = max((n for n in side if n in ehv), key=lambda n: b.at[n, "BusPUVolt"])
        rise = b.at[far, "BusPUVolt"] - b.at[near, "BusPUVolt"]
        inside = br.BusNum.isin(side) & br["BusNum:1"].isin(side)
        charging = float(br.loc[inside & (br.LineXfmr == "NO"), "LineC"].sum() + r.LineC)
        if not (light and rise >= STUB_RISE_PU and charging > 0):
            continue
        gs, ss = g[g.BusNum.isin(side)], sh[sh.BusNum.isin(side)]
        high = b.at[far, "BusVoltLimHigh"]
        high = FALLBACK_BAND[1] if pd.isna(high) or high <= 0 else float(high)
        zero_range = gs[(gs.GenMVRMax == 0) & (gs.GenMVRMin == 0)]
        passing[k] = {**branch_keys(r), "near_bus": bus(near), "near_pu": b.at[near, "BusPUVolt"],
                      "far_bus": bus(far), "far_bus_name": b.at[far, "BusName"],
                      "far_pu": b.at[far, "BusPUVolt"], "far_above_limit": bool(b.at[far, "BusPUVolt"] > high),
                      "LineMW": r.LineMW, "LineMaxPercent": r.LineMaxPercent, "far_side_buses": len(side),
                      "charging_mvar_at_1pu": charging * sbase,
                      "absorbing_room_mvar": float((gs.GenMVR - gs.GenMVRMin).sum() + (ss.SSNMVR - ss.SSMinMVR).sum()),
                      "zero_range_units": [{"BusNum": bus(u.BusNum), "GenID": u.GenID}
                                           for u in zero_range.itertuples()]}
    where = [row for k, row in passing.items() if not _passing_above(k, info, passing)]
    if not where:
        return []
    return [Finding(
        "base.floating_stub", WORTH, YOUR_CALL,
        what=f"{len(where)} lightly loaded EHV dead end(s) whose far end rises on its own line charging",
        why="the rise depends on the dispatch: with the far-end plant off it runs higher, and the one "
            "link that feeds it islands it on a single outage",
        page=PAGE, where=where, details={"count": len(where), "system_mva_base": sbase})]


def _passing_above(k, info, passing) -> bool:
    """Along one radial chain, report only the bridge nearest the core that itself passes."""
    p = info[k]["parent"]
    while p is not None:
        if p in passing:
            return True
        p = info[p]["parent"]
    return False
