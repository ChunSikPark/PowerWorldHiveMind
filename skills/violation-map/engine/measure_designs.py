"""Measure candidate fixes for one area of the voltage page, in memory. Nothing is saved.

    python measure_designs.py <config.json>            -> design_meas_<scenario>.json for every scenario
    python measure_designs.py <config.json> <scenario>

Reads config["designs"]: the area it serves, the watched buses (the problem the fix is for), the
outages to test, and the candidates. Each candidate, and the as-built case first, is measured on a
FRESH open of the base state's case: a switched shunt or an LTC tap does not move back when a
candidate is taken out again, so an undo cannot be trusted. Per candidate: build, solve, read the
area at N-0, then open each listed outage in turn, solve, read, close it.

Candidate kinds:
    {"name": ..., "kind": "line",  "from_bus": 1, "to_bus": 2, "template": [f, t, "ckt"], "miles": 30}
    {"name": ..., "kind": "shunt", "bus": 1, "mvar": -50}          # negative = reactor
    {"name": ..., "kind": "edit",  "object": "Gen", "rows": [{"BusNum": 1, "GenID": "1", "GenVoltSet": 1.02}]}
"miles" is optional: it defaults to the straight-line distance between the two substations.
An "edit" row must carry the object's full key fields, or the write is a silent no-op.
"""
import json
import time
import warnings

import pandas as pd

import devices
import vmap

warnings.filterwarnings("ignore", message=r".*Read-only field.*")
cfg, OUT = vmap.load_config()
A = vmap.args()
DZ = cfg.get("designs")
if not DZ:
    raise SystemExit("config has no \"designs\" block -- nothing to measure")
T = json.load(open(OUT / "topo.json"))
AREA = T["areas"][DZ["area"]]
H = T["max_hops"]
NB = vmap.net_bus(cfg)
area_subs = {int(s) for s, h in AREA["hop"].items() if h <= H}
AREA_BUS = [b for b in T["buses"] if b["sub"] in area_subs]
NET = [b["num"] for b in AREA_BUS if NB(b)]
NAME = {b["num"]: b["name"] for b in T["buses"]}
WATCH = [int(x) for x in DZ.get("watch_buses", AREA["seeds"])]
OUTS = DZ.get("outages", [])
BAND = cfg["band"]
CANDS = [dict(name="As built", kind="none")] + DZ["candidates"]


def read(E, post):
    b = E.GetParametersMultipleElement("Bus", ["BusNum", "BusPUVolt", "BusStatus"])
    on = b.BusStatus.astype(str).str.strip() == "Connected"
    v = dict(zip(vmap.num(b.BusNum).astype(int), vmap.num(b.BusPUVolt).where(on)))
    val = lambda n: None if v.get(n) is None or v.get(n) != v.get(n) else round(float(v[n]), 4)
    hi = BAND["post_hi"] if post else BAND["hi"]
    lo = BAND["post_lo"] if post else BAND["lo"]
    net = [val(n) for n in NET]
    live = [x for x in net if x is not None]
    watch = [val(n) for n in WATCH]
    return dict(solved=True, v={str(b["num"]): val(b["num"]) for b in AREA_BUS},
                islanded=sorted(NAME[n] for n, x in zip(NET, net) if x is None),
                watch=max((x for x in watch if x is not None), default=None),
                watch_min=min((x for x in watch if x is not None), default=None),
                vmax=max(live, default=None), vmin=min(live, default=None),
                n_out=sum(1 for x in live if x > hi or x < lo))


def new_line_flow(E, c):
    d = E.GetParametersMultipleElement("Branch", ["BusNum", "BusNum:1", "LineCircuit", "LineMW", "LineMVR", "LineMVR:1", "LinePercent"])
    d["BusNum"], d["BusNum:1"] = vmap.num(d.BusNum), vmap.num(d["BusNum:1"])
    r = d[(d.BusNum == c["from_bus"]) & (d["BusNum:1"] == c["to_bus"]) & (d.LineCircuit.astype(str).str.strip() == "1")]
    if len(r) != 1:
        return None
    r = r.iloc[0]
    return dict(mw=round(float(r.LineMW), 1), qf=round(float(r.LineMVR), 1), qt=round(float(r["LineMVR:1"]), 1),
                pct=round(float(r.LinePercent), 1))


def build(pw, c):
    E = pw.esa
    if c["kind"] == "none":
        return devices.Result(True, "as built")
    if c["kind"] == "line":
        bus = E.GetParametersMultipleElement("Bus", ["BusNum", "BusName_NomVolt", "SubNum"])
        names = dict(zip(vmap.num(bus.BusNum).astype(float), bus.BusName_NomVolt.astype(str)))
        b2s = dict(zip(vmap.num(bus.BusNum).astype(int), vmap.num(bus.SubNum)))
        sub = E.GetParametersMultipleElement("Substation", ["SubNum", "Latitude", "Longitude"])
        ll = {int(s): (float(a), float(o)) for s, a, o in zip(vmap.num(sub.SubNum), vmap.num(sub.Latitude), vmap.num(sub.Longitude))}
        dist = lambda x, y: vmap.miles(*ll[int(b2s[x])], *ll[int(b2s[y])])
        tf, tt, tc = c["template"]
        return devices.add_line(pw, float(c["from_bus"]), float(c["to_bus"]), (float(tf), float(tt), str(tc)),
                                c.get("miles") or dist(c["from_bus"], c["to_bus"]), dist(tf, tt), names)
    if c["kind"] == "shunt":
        b = E.GetParametersSingleElement("Bus", ["BusNum", "BusName_NomVolt", "AreaNum", "ZoneNum"], [c["bus"], "", "", ""])
        return devices.add_shunt(pw, c["bus"], c["mvar"], b["BusName_NomVolt"], int(b["AreaNum"]), int(b["ZoneNum"]))
    if c["kind"] == "edit":
        from esapp import components
        obj = getattr(components, c["object"])
        pw.edit_mode()
        try:
            pw[obj] = pd.DataFrame(c["rows"])
        finally:
            pw.run_mode()
        for row in c["rows"]:                     # assert the effect: a row missing a key field writes nothing
            got = E.GetParametersMultipleElement(c["object"], list(row))
            hit = pd.Series(True, index=got.index)
            for k, v in row.items():
                if isinstance(v, (int, float)):
                    hit &= (vmap.num(got[k]) - float(v)).abs() < 1e-6
                else:
                    hit &= got[k].astype(str).str.strip() == str(v)
            if not hit.any():
                return devices.Result(False, f"{c['object']} write did not take for {row} -- are all key fields present?")
        return devices.Result(True, f"edited {len(c['rows'])} {c['object']} row(s)")
    return devices.Result(False, f"unknown kind {c['kind']!r}")


def measure(sce):
    res, t0 = [], time.time()
    for c in CANDS:
        pw = vmap.open_case(vmap.case_path(cfg, sce))           # fresh open per candidate, never an undo
        try:
            E = pw.esa
            r = build(pw, c)
            if not r.ok:
                res.append(dict(name=c["name"], error=r.detail))
                print(f"  [{sce}] {c['name']}: build failed -- {r.detail}")
                continue
            m = dict(name=c["name"], note=r.detail)
            ok = vmap.solve(E)
            m["n0"] = read(E, False) if ok else dict(solved=False)
            if ok and c["kind"] == "line":
                m["new_line"] = new_line_flow(E, c)
            stuck = None
            for o in OUTS:
                if stuck:
                    m[o["key"]] = dict(solved=False, error=f"not measured: could not re-close {stuck}")
                    continue
                if not ok or not vmap.set_branch(E, o["f"], o["t"], o.get("ckt", "1"), "Open"):
                    m[o["key"]] = dict(solved=False, error="could not open the branch" if ok else "N-0 did not solve")
                    continue
                m[o["key"]] = read(E, True) if vmap.solve(E) else dict(solved=False)
                if not vmap.set_branch(E, o["f"], o["t"], o.get("ckt", "1"), "Closed"):
                    stuck = o["label"]            # never measure the next outage on top of this one
                vmap.solve(E)
            res.append(m)
            n0 = m["n0"]
            print(f"  [{sce}] {c['name']}: N-0 watched max {n0.get('watch')}, {n0.get('n_out')} bus(es) out of band")
        finally:
            vmap.close_case(pw)
    vmap.dump(OUT / f"design_meas_{sce}.json", dict(scenario=sce, results=res))
    print(f"[{sce}] {len(res)} candidates in {(time.time() - t0) / 60:.1f} min")


for sc in (A[:1] or vmap.scenario_keys(cfg)):
    measure(sc)
