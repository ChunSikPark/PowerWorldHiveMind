"""opf rules: the three conditions PowerWorld needs before an OPF will run
(concepts/opf-preconditions.md). Checked separately, per OPF group: an area on OPF itself is its own
group; areas on OPF only through their super area are pooled into one group for that super area,
because the OPF moves units across it. The pooling is inferred from how the OPF dispatches, not
measured on a case with an empty member area."""
from __future__ import annotations

import pandas as pd

from casedata import CaseData
from findings import FYI, ON_PURPOSE, STOPS, WORTH, YOUR_CALL, Finding, bus
from summary import is_renewable, opf_areas, opf_super_areas

PAGE = "concepts/opf-preconditions.md"
OPF = ("opf",)
COST_HANDOFF = "your own cost-data source; no script supplies cost curves, and a default one makes the dispatch meaningless"


def _units(cd: CaseData) -> pd.DataFrame:
    g = cd.get("Gen")
    g = g[g.GenStatus == "Closed"].copy()
    g["agc"] = g.GenAGCAble == "YES"
    g["renewable"] = is_renewable(g.GenFuelType)
    # priced = a cost model and a fitted curve. GenMCost is the curve at today's output, so a
    # zero there is a price of zero (wind, solar), not missing data.
    g["priced"] = (g.GenCostModel.str.upper() != "NONE") & (g.GenCostModel != "") & (g.GenCostCurvePoints > 0)
    return g


def area_table(cd: CaseData) -> list[dict]:
    """Per area: may the OPF redispatch it, and what its units carry. The agent shows this table."""
    g, on_opf, sa_on = _units(cd), opf_areas(cd), set(opf_super_areas(cd))
    rows = []
    for _, a in cd.get("Area").iterrows():
        u = g[(g.AreaNum == a.AreaNum) & g.agc]
        rows.append({"AreaNum": bus(a.AreaNum), "BGAGC": a.BGAGC, "SAName": a.SAName,
                     "opf": a.AreaNum in on_opf, "via_super_area": a.BGAGC.upper() != "OPF" and a.SAName in sa_on,
                     "agc_units": int(len(u)), "with_curve": int(u.priced.sum()),
                     "cost_above_zero": int((u.GenMCost > 0).sum()),
                     "cost_models": {str(k): int(v) for k, v in u.GenCostModel.value_counts().items()}})
    return rows


def _units_where(df) -> list[dict]:
    return [{"BusNum": bus(u.BusNum), "GenID": u.GenID, "AreaNum": bus(u.AreaNum), "GenCostModel": u.GenCostModel,
             "GenCostCurvePoints": u.GenCostCurvePoints, "GenMCost": u.GenMCost} for u in df.itertuples()]


def _groups(cd: CaseData) -> dict:
    """OPF group -> its areas. ("super area", name) pools every OPF area inside a super area that is on
    OPF, whether the area is on OPF itself or only through it; ("area", n) is an OPF area outside one."""
    a, on, sa_on = cd.get("Area"), opf_areas(cd), set(opf_super_areas(cd))
    groups = {}
    for _, r in a[a.AreaNum.isin(on)].iterrows():
        key = ("super area", r.SAName) if r.SAName in sa_on else ("area", bus(r.AreaNum))
        groups.setdefault(key, []).append(r.AreaNum)
    return groups


def _where(key, areas) -> dict:
    return {"AreaNum": key[1]} if key[0] == "area" else {"SAName": key[1], "areas": sorted(bus(x) for x in areas)}


def _name(key) -> str:
    return f"area {key[1]}" if key[0] == "area" else f"super area {key[1]}"


def opf_conditions(cd: CaseData) -> list[Finding]:
    groups, g = _groups(cd), _units(cd)
    all_off = not g.agc.any()
    why_off = "AGC is off on every unit; writing GenMW turns it off, so a dispatch step is the likely cause"
    if not groups:
        stop = Finding(
            "opf.1", STOPS, YOUR_CALL,
            what="no area or super area is set to let the OPF redispatch it",
            why="the OPF will not start: which areas it may move is your study choice",
            page=PAGE, stops=OPF)
        # conditions 2 and 3 are checked separately: cost data is the long-lead item, so show it now
        rows = [{"AreaNum": r["AreaNum"], "agc_units": r["agc_units"], "with_curve": r["with_curve"]}
                for r in area_table(cd)]
        none_priced = not (g.agc & g.priced).any()
        preview = Finding(
            "opf.preview", WORTH, YOUR_CALL,
            what="preview for when areas are put on OPF: the units each area could let the OPF move, and how many carry cost data",
            why=why_off if all_off else "an OPF needs AGC-able units with real cost curves in each area it controls",
            page=PAGE, where=rows, handoff=COST_HANDOFF if none_priced else "",
            details={"agc_off_everywhere": all_off, "units_with_cost_data": int((g.agc & g.priced).sum())})
        return [stop, preview]
    out, empty, unpriced, thin, movable_all = [], [], [], [], []
    for key, areas in groups.items():
        movable = g[g.AreaNum.isin(areas) & g.agc]
        movable_all.append(movable)
        if movable.empty:
            empty.append((key, _where(key, areas)))
        elif not movable.priced.any():
            unpriced.append((key, {**_where(key, areas), "movable_units": int(len(movable))}))
        elif key[0] == "super area":
            for a in areas:                     # a member with nothing of its own is covered by the pool
                own = movable[movable.AreaNum == a]
                if own.empty or not own.priced.any():
                    thin.append({"AreaNum": bus(a), "SAName": key[1], "movable_units": int(len(own)),
                                 "priced_units": int(own.priced.sum())})
    if empty:
        out.append(Finding(
            "opf.2", STOPS, YOUR_CALL,
            what="no unit the OPF may move in " + ", ".join(_name(k) for k, _ in empty),
            why=(why_off if all_off else "an OPF group with no AGC-able unit gives the OPF nothing to redispatch"),
            page=PAGE, stops=OPF, where=[w for _, w in empty], details={"agc_off_everywhere": all_off}))
    if unpriced:
        out.append(Finding(
            "opf.3", STOPS, YOUR_CALL,
            what="no cost data on any unit the OPF could move in " + ", ".join(_name(k) for k, _ in unpriced),
            why="an OPF needs real cost curves there; switching a cost model on without them gives a meaningless dispatch",
            page=PAGE, stops=OPF, where=[w for _, w in unpriced], handoff=COST_HANDOFF))
    if thin:
        out.append(Finding(
            "opf.2", FYI, ON_PURPOSE,
            what=f"{len(thin)} member area(s) of an OPF super area have no movable or no priced unit of their own",
            why="the OPF moves units across the whole super area, so the rest of it covers them",
            page=PAGE, where=thin))
    movable = pd.concat(movable_all)
    priced_groups = movable.groupby(movable.AreaNum.map({a: k for k, v in groups.items() for a in v})).priced.transform("any")
    bare = movable[~movable.priced & priced_groups]
    if not bare.empty:
        out.append(Finding(
            "opf.3", WORTH, YOUR_CALL,
            what=f"{len(bare)} of the {len(movable)} units the OPF could move carry no cost curve",
            why="the OPF runs on the priced units; these ones have no price to be dispatched on",
            page=PAGE, where=_units_where(bare), handoff=COST_HANDOFF,
            details={"units": int(len(movable)), "priced": int(movable.priced.sum())}))
    free = movable[movable.priced & (movable.GenMCost <= 0) & ~movable.renewable]
    if not free.empty:
        out.append(Finding(
            "opf.3", WORTH, ON_PURPOSE,
            what=f"{len(free)} thermal unit(s) the OPF could move have a cost curve that reads 0 at today's output",
            why="the OPF will treat their next MW as free; check the curve if that is not intended",
            page=PAGE, where=_units_where(free)))
    return out
