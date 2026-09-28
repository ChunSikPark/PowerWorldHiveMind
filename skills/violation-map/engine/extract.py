"""Extract the neighbourhood of each seeded area for the voltage page. Read-only: nothing is saved.

    python extract.py <config.json> topo              -> topo.json   (subs, buses, branches, gens, shunts; hop rings per area)
    python extract.py <config.json> state             -> state_<state>_<scenario>.json for every state x scenario
    python extract.py <config.json> state <st> <sc>   -> just that one

Areas are seeded by bus numbers in the config (usually the buses outside the band). Each area
keeps every substation within `hops` substation-hops of a seed, plus one ring for geometry.
Topology is read from the base state's first scenario; the state files carry only solved values.
"""
import json

import vmap

cfg, OUT = vmap.load_config()
A = vmap.args()
HOPS = int(cfg["hops"])
frame = vmap.frame


def topo():
    sc = vmap.scenario_keys(cfg)[0]
    pw = vmap.open_case(vmap.case_path(cfg, sc))
    try:
        E = pw.esa
        sub = frame(E, "Substation", ["SubNum", "SubName", "Latitude", "Longitude"], ["SubNum", "Latitude", "Longitude"])
        bus = frame(E, "Bus", ["BusNum", "BusName", "SubNum", "BusNomVolt"], ["BusNum", "SubNum", "BusNomVolt"])
        br = frame(E, "Branch", ["BusNum", "BusNum:1", "LineCircuit", "LineStatus", "LineXfmr", "BranchDeviceType",
                                 "LineR", "LineX", "LineC", "LineAMVA"],
                   ["BusNum", "BusNum:1", "LineR", "LineX", "LineC", "LineAMVA"])
        gn = frame(E, "Gen", ["BusNum", "GenID", "GenMWMax", "GenMVRMin", "GenMVRMax", "GenRegNum", "GenFuelType"],
                   ["BusNum", "GenMWMax", "GenMVRMin", "GenMVRMax", "GenRegNum"])
        sh = frame(E, "Shunt", ["BusNum", "ShuntID", "SSCMode", "SSMinMVR", "SSMaxMVR", "SSRegNum"],
                   ["BusNum", "SSMinMVR", "SSMaxMVR", "SSRegNum"])
    finally:
        vmap.close_case(pw)

    b2s = dict(zip(bus.BusNum, bus.SubNum))
    br["sf"], br["st"] = br.BusNum.map(b2s), br["BusNum:1"].map(b2s)
    inter = br[(br.sf != br.st) & (br.LineStatus == "Closed") & br.sf.notna() & br.st.notna()]
    adj = {}
    for a, b in zip(inter.sf, inter.st):
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    hops = {}
    for key, a in cfg["areas"].items():
        unknown = [x for x in a["seeds"] if x not in b2s or b2s[x] != b2s[x]]
        if unknown:
            raise SystemExit(f"area {key!r}: seed bus(es) {unknown} not in the case or not in a substation")
        h = {b2s[x]: 0 for x in a["seeds"]}
        frontier = list(h)
        for d in range(1, HOPS + 2):                      # one ring past HOPS, for geometry
            nxt = []
            for s in frontier:
                for n in adj.get(s, ()):
                    if n not in h:
                        h[n] = d
                        nxt.append(n)
            frontier = nxt
        hops[key] = {int(k): v for k, v in h.items()}
    keep = set().union(*[set(h) for h in hops.values()])
    kv = dict(zip(bus.BusNum, bus.BusNomVolt))
    keepb = set(bus[bus.SubNum.isin(keep)].BusNum)
    lat, lon = dict(zip(sub.SubNum, sub.Latitude)), dict(zip(sub.SubNum, sub.Longitude))
    mi = lambda a, b: round(vmap.miles(lat[a], lon[a], lat[b], lon[b]), 1) if a != b else 0.0

    out = dict(max_hops=HOPS,
               areas={k: dict(title=a.get("title", k), seeds=a["seeds"], roots=sorted({int(b2s[x]) for x in a["seeds"]}),
                              hop=hops[k]) for k, a in cfg["areas"].items()},
               subs=[dict(id=int(r.SubNum), name=r.SubName, lat=float(r.Latitude), lon=float(r.Longitude))
                     for r in sub[sub.SubNum.isin(keep)].itertuples()],
               buses=[dict(num=int(r.BusNum), name=r.BusName, sub=int(r.SubNum), kv=float(r.BusNomVolt))
                      for r in bus[bus.BusNum.isin(keepb)].itertuples()],
               branches=[dict(f=int(r.BusNum), t=int(r._2), ckt=r.LineCircuit, sf=int(r.sf), st=int(r.st),
                              kv=float(max(kv[r.BusNum], kv[r._2])), kv_lo=float(min(kv[r.BusNum], kv[r._2])),
                              xf=r.LineXfmr == "YES", w=r.BranchDeviceType == "TransformerWinding",
                              r=float(r.LineR), x=float(r.LineX), b=float(r.LineC), rate=float(r.LineAMVA), mi=mi(r.sf, r.st))
                         for r in br[br.sf.isin(keep) & br.st.isin(keep)].itertuples()],
               gens=[dict(bus=int(r.BusNum), id=r.GenID, mwmax=float(r.GenMWMax), qmin=float(r.GenMVRMin),
                          qmax=float(r.GenMVRMax), reg=int(r.GenRegNum) if r.GenRegNum == r.GenRegNum else 0,
                          fuel=r.GenFuelType.split(" (")[0])
                     for r in gn[gn.BusNum.isin(keepb)].itertuples()],
               shunts=[dict(bus=int(r.BusNum), id=r.ShuntID, mode=r.SSCMode, qmin=float(r.SSMinMVR),
                            qmax=float(r.SSMaxMVR), reg=int(r.SSRegNum) if r.SSRegNum == r.SSRegNum else 0)
                       for r in sh[sh.BusNum.isin(keepb)].itertuples()])
    vmap.dump(OUT / "topo.json", out)
    for k, h in hops.items():
        print(k, "substations per hop:", {d: sum(1 for v in h.values() if v == d) for d in range(HOPS + 2)})
    print(f"{len(out['subs'])} subs, {len(out['buses'])} buses, {len(out['branches'])} branches, "
          f"{len(out['gens'])} gens, {len(out['shunts'])} shunts")


def state(which, sce):
    T = json.load(open(OUT / "topo.json"))
    keepb = {b["num"] for b in T["buses"]}
    pw = vmap.open_case(vmap.case_path(cfg, sce, which))
    try:
        E = pw.esa
        bus = frame(E, "Bus", ["BusNum", "BusPUVolt"], ["BusNum", "BusPUVolt"])
        br = frame(E, "Branch", ["BusNum", "BusNum:1", "LineCircuit", "LineStatus", "LineMW", "LineMVR", "LineMVR:1", "LinePercent"],
                   ["BusNum", "BusNum:1", "LineMW", "LineMVR", "LineMVR:1", "LinePercent"])
        gn = frame(E, "Gen", ["BusNum", "GenID", "GenStatus", "GenMW", "GenMVR", "GenVoltSet"], ["BusNum", "GenMW", "GenMVR", "GenVoltSet"])
        sh = frame(E, "Shunt", ["BusNum", "ShuntID", "SSStatus", "SSNMVR", "SSVLow", "SSVHigh"], ["BusNum", "SSNMVR", "SSVLow", "SSVHigh"])
        ld = frame(E, "Load", ["BusNum", "LoadStatus", "LoadMW", "LoadMVR"], ["BusNum", "LoadMW", "LoadMVR"])
    finally:
        vmap.close_case(pw)
    bus = bus[bus.BusNum.isin(keepb)]
    br = br[br.BusNum.isin(keepb) & br["BusNum:1"].isin(keepb)]
    gn = gn[gn.BusNum.isin(keepb)]
    sh = sh[sh.BusNum.isin(keepb)]
    ld = ld[ld.BusNum.isin(keepb) & (ld.LoadStatus == "Closed")].groupby("BusNum")[["LoadMW", "LoadMVR"]].sum()
    r1 = lambda x: None if x != x else round(float(x), 1)
    out = dict(scenario=sce, set=which,
               v={int(b): round(float(v), 4) for b, v in zip(bus.BusNum, bus.BusPUVolt) if v == v},
               br={f"{int(r.BusNum)}-{int(r._2)}-{r.LineCircuit}": [r.LineStatus == "Closed", r1(r.LineMW), r1(r.LineMVR),
                                                                    r1(r._7), r1(r.LinePercent)] for r in br.itertuples()},
               gen={f"{int(r.BusNum)}-{r.GenID}": [r.GenStatus == "Closed", r1(r.GenMW), r1(r.GenMVR),
                                                   round(float(r.GenVoltSet), 4)] for r in gn.itertuples()},
               sh={f"{int(r.BusNum)}-{r.ShuntID}": [r.SSStatus == "Closed", r1(r.SSNMVR),
                                                   round(float(r.SSVLow), 4), round(float(r.SSVHigh), 4)] for r in sh.itertuples()},
               load={int(b): [round(float(r.LoadMW), 1), round(float(r.LoadMVR), 1)] for b, r in ld.iterrows()})
    vmap.dump(OUT / f"state_{which}_{sce}.json", out)
    print(f"{which} {sce}: {len(out['v'])} buses, {len(out['br'])} branches")


if not A or A[0] not in ("topo", "state"):
    raise SystemExit(__doc__)
if A[0] == "topo":
    topo()
elif len(A) >= 3:
    state(A[1], A[2])
else:
    for st in cfg["states"]:
        for sc in vmap.scenario_keys(cfg):
            state(st["key"], sc)
