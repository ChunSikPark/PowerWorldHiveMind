"""Whole-grid extract for the islanding screen. Read-only: nothing is saved.

    python extract_full.py <config.json> topo     -> full_topo.json  (subs, buses, branches, gens, shunts)
    python extract_full.py <config.json> inj      -> full_inj_<scenario>.json for every scenario (bus -> [load MW, gen MW], solved)

Reads the base state's cases (the first entry under "states").
"""
import vmap

cfg, OUT = vmap.load_config()
A = vmap.args()
frame = vmap.frame


def topo():
    pw = vmap.open_case(vmap.case_path(cfg, vmap.scenario_keys(cfg)[0]))
    try:
        E = pw.esa
        sub = frame(E, "Substation", ["SubNum", "SubName", "Latitude", "Longitude"], ["SubNum", "Latitude", "Longitude"])
        bus = frame(E, "Bus", ["BusNum", "BusName", "SubNum", "BusNomVolt"], ["BusNum", "SubNum", "BusNomVolt"])
        br = frame(E, "Branch", ["BusNum", "BusNum:1", "LineCircuit", "LineStatus", "LineXfmr", "BranchDeviceType",
                                 "LineR", "LineX", "LineC", "LineAMVA"], ["BusNum", "BusNum:1", "LineR", "LineX", "LineC", "LineAMVA"])
        gn = frame(E, "Gen", ["BusNum", "GenID", "GenMWMax", "GenMVRMin", "GenMVRMax", "GenFuelType"],
                   ["BusNum", "GenMWMax", "GenMVRMin", "GenMVRMax"])
        sh = frame(E, "Shunt", ["BusNum", "ShuntID", "SSMinMVR", "SSMaxMVR"], ["BusNum", "SSMinMVR", "SSMaxMVR"])
    finally:
        vmap.close_case(pw)
    lat, lon = dict(zip(sub.SubNum, sub.Latitude)), dict(zip(sub.SubNum, sub.Longitude))
    b2s = dict(zip(bus.BusNum, bus.SubNum))

    def mi(a, b):
        if a is None or b is None or a != a or b != b or a == b:
            return 0.0
        return round(vmap.miles(lat[a], lon[a], lat[b], lon[b]), 1)

    kv = dict(zip(bus.BusNum, bus.BusNomVolt))
    out = dict(
        subs=[dict(id=int(r.SubNum), name=r.SubName, lat=float(r.Latitude), lon=float(r.Longitude)) for r in sub.itertuples()],
        buses=[dict(num=int(r.BusNum), name=r.BusName, sub=(int(r.SubNum) if r.SubNum == r.SubNum else None), kv=float(r.BusNomVolt))
               for r in bus.itertuples()],
        branches=[dict(f=int(r.BusNum), t=int(r._2), ckt=r.LineCircuit, on=r.LineStatus == "Closed", xf=r.LineXfmr == "YES",
                       w=r.BranchDeviceType == "TransformerWinding", kv=float(max(kv[r.BusNum], kv[r._2])),
                       kv_lo=float(min(kv[r.BusNum], kv[r._2])), r=float(r.LineR), x=float(r.LineX), b=float(r.LineC),
                       rate=float(r.LineAMVA), mi=mi(b2s.get(r.BusNum), b2s.get(r._2))) for r in br.itertuples()],
        gens=[dict(bus=int(r.BusNum), id=r.GenID, mwmax=float(r.GenMWMax), qmin=float(r.GenMVRMin), qmax=float(r.GenMVRMax),
                   fuel=r.GenFuelType.split(" (")[0]) for r in gn.itertuples()],
        shunts=[dict(bus=int(r.BusNum), id=r.ShuntID, qmin=float(r.SSMinMVR), qmax=float(r.SSMaxMVR)) for r in sh.itertuples()])
    vmap.dump(OUT / "full_topo.json", out)
    print(f"{len(out['subs'])} subs, {len(out['buses'])} buses, {len(out['branches'])} branches")


def inj(sce):
    pw = vmap.open_case(vmap.case_path(cfg, sce))
    try:
        E = pw.esa
        ld = frame(E, "Load", ["BusNum", "LoadStatus", "LoadMW"], ["BusNum", "LoadMW"])
        gn = frame(E, "Gen", ["BusNum", "GenStatus", "GenMW"], ["BusNum", "GenMW"])
    finally:
        vmap.close_case(pw)
    L = ld[ld.LoadStatus == "Closed"].groupby("BusNum").LoadMW.sum()
    G = gn[gn.GenStatus == "Closed"].groupby("BusNum").GenMW.sum()
    out = {int(b): [round(float(L.get(b, 0)), 1), round(float(G.get(b, 0)), 1)] for b in set(L.index) | set(G.index)}
    vmap.dump(OUT / f"full_inj_{sce}.json", out)
    print(f"{sce}: {len(out)} buses with load or generation")


if not A or A[0] not in ("topo", "inj"):
    raise SystemExit(__doc__)
if A[0] == "topo":
    topo()
else:
    for sc in (A[1:2] or vmap.scenario_keys(cfg)):
        inj(sc)
