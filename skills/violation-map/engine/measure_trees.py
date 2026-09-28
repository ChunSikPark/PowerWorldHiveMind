"""AC-measure the suggested tie(s) for every radial tree with MW at stake, in one dispatch. In memory only.

    python measure_trees.py <config.json> <scenario> [N]      -> tree_meas_<scenario>.json   (N = first N trees only)

Per design: build the tie (devices.add_line), solve, read N-0; then open each bridge of the tree in
turn, re-solve, read islanded buses, pocket voltages, the worst pocket branch and the new line's
loading, and close it again. Then take the tie out (status Open) and FINGERPRINT the case against
its opening state -- closed-branch count and a fixed voltage sample. A drifted case is reopened,
never trusted: an undo that did not restore the case once went unnoticed until a fingerprint
caught it, because LTC taps and switched shunts do not move back on their own.

Scope is trees whose bridge is at or above radial.min_kv.
"""
import json
import random
import time
import warnings

import devices
import vmap

warnings.filterwarnings("ignore", message=r".*Read-only field.*")
cfg, OUT = vmap.load_config()
A = vmap.args()
if not A:
    raise SystemExit(__doc__)
SCE = A[0]
CASE = vmap.case_path(cfg, SCE)
T = json.load(open(OUT / "full_topo.json"))
B = vmap.place_star_buses(T)
NB = vmap.net_bus(cfg)
TREES = [t for t in json.load(open(OUT / "tree_designs.json"))
         if t["designs"] and t["stake_mw"] > 0 and t["kv"] >= cfg["radial"]["min_kv"]]
if len(A) > 1:
    TREES = TREES[: int(A[1])]
num = vmap.num


class Case:
    def __init__(self):
        self.open()

    def open(self):
        self.pw = vmap.open_case(CASE)
        self.E = self.pw.esa
        self.made = set()                         # ties this open case created, the only ones build() may re-close
        nmv = self.E.GetParametersMultipleElement("Bus", ["BusNum", "BusName_NomVolt"])
        self.names = dict(zip(num(nmv.BusNum).astype(float), nmv.BusName_NomVolt.astype(str)))
        self.fp = self.fingerprint()

    def close(self):
        vmap.close_case(self.pw)

    def buses(self):
        b = self.E.GetParametersMultipleElement("Bus", ["BusNum", "BusPUVolt", "BusStatus"])
        on = b.BusStatus.astype(str).str.strip() == "Connected"
        return dict(zip(num(b.BusNum).astype(int), num(b.BusPUVolt).where(on)))

    def branches(self):
        d = self.E.GetParametersMultipleElement("Branch", ["BusNum", "BusNum:1", "LineCircuit", "LineStatus", "LinePercent", "LineMW"])
        d["BusNum"], d["BusNum:1"] = num(d.BusNum).astype(int), num(d["BusNum:1"]).astype(int)
        d["LineCircuit"] = d.LineCircuit.astype(str).str.strip()
        return d

    def fingerprint(self):
        br, v = self.branches(), self.buses()
        pool = sorted(n for n, x in v.items() if x == x)
        sample = random.Random(7).sample(pool, min(40, len(pool)))
        return dict(closed=int((br.LineStatus.astype(str).str.strip() == "Closed").sum()), v={n: v[n] for n in sample})

    def drifted(self):
        br, v = self.branches(), self.buses()
        closed = int((br.LineStatus.astype(str).str.strip() == "Closed").sum())
        dv = max((abs(v[n] - x) if v.get(n) is not None and v[n] == v[n] else 1.0)   # a sampled bus gone dead is drift
                 for n, x in self.fp["v"].items())
        return closed != self.fp["closed"] or dv > 0.003


def build(C, d):
    """Add the tie, or switch it back in when an earlier design on this open case already created it."""
    r = devices.add_line(C.pw, float(d["fb"]), float(d["tb"]), tuple(d["tmpl"]), d["mi"], d["tmpl_mi"], C.names)
    key = (d["fb"], d["tb"])
    if r.ok:
        C.made.add(key)
        return True, r.detail
    if "already exists" in r.detail and key in C.made and vmap.set_branch(C.E, d["fb"], d["tb"], "1", "Closed"):
        return True, "re-closed the line an earlier design created"
    return False, r.detail


def read(C, tree_subs, new):
    v, br = C.buses(), C.branches()
    allb = {b["num"] for b in T["buses"] if b["sub"] in tree_subs}
    live = [x for x in (v.get(n) for n in allb if NB(B[n])) if x is not None and x == x]
    isl = sorted(B[n]["name"] for n in allb if v.get(n) is None or v.get(n) != v.get(n))
    touch = br[(br.BusNum.isin(allb) | br["BusNum:1"].isin(allb)) & (br.LineStatus.astype(str).str.strip() == "Closed")]
    nl = br[((br.BusNum == new[0]) & (br["BusNum:1"] == new[1])) | ((br.BusNum == new[1]) & (br["BusNum:1"] == new[0]))]
    return dict(vmin=round(min(live), 4) if live else None, vmax=round(max(live), 4) if live else None, islanded=isl,
                worst_pct=round(float(num(touch.LinePercent).max()), 1) if len(touch) else None,
                new_pct=round(float(num(nl.LinePercent).iloc[0]), 1) if len(nl) else None,
                new_mw=round(float(num(nl.LineMW).iloc[0]), 1) if len(nl) else None)


C = Case()
out, t0, reopened = [], time.time(), 0
try:
    for ti, tr in enumerate(TREES):
        subs = set(tr["tree"])
        res = []
        for d in tr["designs"]:
            ok1, why = build(C, d)
            if not ok1:
                res.append(dict(error=why, fb=d["fb"], tb=d["tb"])); continue
            ok = vmap.solve(C.E)
            m = dict(fb=d["fb"], tb=d["tb"], n0=read(C, subs, (d["fb"], d["tb"])) if ok else {}, outs=[])
            m["n0"]["solved"] = ok
            for b in tr["bridges"]:
                if not vmap.set_branch(C.E, b["f"], b["t"], b["ckt"], "Open"):
                    m["outs"].append(dict(solved=False, error="could not open the bridge", bridge=f"{b['f']}-{b['t']}-{b['ckt']}"))
                    continue
                ok2 = vmap.solve(C.E)
                o = read(C, subs, (d["fb"], d["tb"])) if ok2 else {}
                o.update(solved=ok2, bridge=f"{b['f']}-{b['t']}-{b['ckt']}")
                m["outs"].append(o)
                vmap.set_branch(C.E, b["f"], b["t"], b["ckt"], "Closed")
                vmap.solve(C.E)
            vmap.set_branch(C.E, d["fb"], d["tb"], "1", "Open")
            vmap.solve(C.E)
            if C.drifted():
                C.close(); C.open(); reopened += 1
            res.append(m)
        out.append(dict(attach=tr["attach"], res=res))
        if ti % 10 == 0:
            print(f"[{SCE}] {ti + 1}/{len(TREES)} trees, {(time.time() - t0) / 60:.1f} min, reopened {reopened}", flush=True)
finally:
    C.close()
vmap.dump(OUT / f"tree_meas_{SCE}.json", dict(scenario=SCE, trees=out, reopened=reopened))
print(f"[{SCE}] done: {len(out)} trees in {(time.time() - t0) / 60:.1f} min, case reopened {reopened} times", flush=True)
