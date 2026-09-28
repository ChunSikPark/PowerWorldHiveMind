"""Assemble the radial-ties page from full_topo.json, tree_designs.json and tree_meas_<scenario>.json. Offline.

    python build_radial.py <config.json>        -> <out_dir>/radial_ties.html

Scope: trees whose bridge is at or above radial.min_kv. Measurements are optional -- a tree with
none shows as "topology only".
"""
import json
from pathlib import Path

import vmap

cfg, OUT = vmap.load_config()
HERE = Path(__file__).parent
SCES = vmap.scenario_keys(cfg)
MIN_KV = cfg["radial"]["min_kv"]
BAND = cfg["band"]
T = json.load(open(OUT / "full_topo.json"))
B = vmap.place_star_buses(T)
S = {s["id"]: s for s in T["subs"]}
TD = [t for t in json.load(open(OUT / "tree_designs.json")) if t["kv"] >= MIN_KV]
meas = {}
for sc in SCES:
    p = OUT / f"tree_meas_{sc}.json"
    if p.exists():
        for tr in json.load(open(p))["trees"]:
            meas.setdefault(tr["attach"], {})[sc] = tr["res"]
line_by_key = {(b["f"], b["t"], b["ckt"]): b for b in T["branches"]}
trees = []
for t in TD:
    ds = []
    for i, d in enumerate(t["designs"]):
        tm = line_by_key.get(tuple(d["tmpl"]))
        got = meas.get(t["attach"], {})
        # match by the tie's own buses, never by position: re-running designs_all.py can reorder the designs
        m = {sc: next((x for x in got.get(sc, []) if (x.get("fb"), x.get("tb")) == (d["fb"], d["tb"])), None) for sc in SCES}
        ds.append(dict(frm=d["frm"], to=d["to"], fb=d["fb"], tb=d["tb"], mi=d["mi"], long=d["long"], covers=d["covers"], of=d["of"],
                       tmpl_name=f"{S[B[tm['f']]['sub']]['name']} – {S[B[tm['t']]['sub']]['name']}" if tm else "?", tmpl_mi=d["tmpl_mi"],
                       tmpl_rate=d["tmpl_rate"], rate_clears=d["rate_clears"], meas=m if any(m.values()) else None))
    trees.append(dict(id=t["attach"], kv=t["kv"], subs=t["tree"], near=t["near"], stake=t["stake_mw"], max_load=t["max_load"],
                      max_gen=t["max_gen"], why=t.get("why", ""), designs=ds,
                      bridges=[dict(sa=B[b["f"]]["sub"], sc=B[b["t"]]["sub"], mi=b["mi"], pocket=b["pocket"], load=b["load"], gen=b["gen"],
                                    kv=max(B[b["f"]]["kv"], B[b["t"]]["kv"])) for b in t["bridges"]]))
used = {s for t in trees for s in t["subs"] + [t["near"]] + [x for d in t["designs"] for x in (d["frm"], d["to"])]}
pairs = {}
for br in T["branches"]:
    a, c = B[br["f"]]["sub"], B[br["t"]]["sub"]
    if br["on"] and a is not None and c is not None and a != c and br["kv"] >= 100:
        k = (min(a, c), max(a, c)); pairs[k] = max(pairs.get(k, 0), br["kv"]); used.update(k)


def verdict(ms):
    """ms: {scenario: measurement}. Pass = solved, nothing islanded, pocket within the post band, every pocket branch <= 100%."""
    n = m = 0
    worst = 0.0
    for sc in SCES:
        x = ms.get(sc) if ms else None
        if not x or "error" in x:
            continue
        m += 1
        good = True
        for o in x["outs"]:
            worst = max(worst, o.get("worst_pct") or 0)
            if (not o.get("solved") or o.get("islanded") or (o.get("worst_pct") or 0) > 100
                    or (o.get("vmin") is not None and (o["vmin"] < BAND["post_lo"] or o["vmax"] > BAND["post_hi"]))):
                good = False
        n += good
    return dict(n=n, m=m, worst=round(worst, 1))


lines = []
for t in trees:                               # one tie per tree: the best measured design
    if not t["designs"]:
        continue
    best = max(t["designs"], key=lambda d: (verdict(d["meas"])["n"], -d["mi"]))
    lines.append(dict(kind="core", trees=[t["id"]], frm=best["frm"], to=best["to"], mi=best["mi"], kv=t["kv"], closes_mw=t["stake"],
                      **verdict(best["meas"])))
levels = sorted({t["kv"] for t in trees}, reverse=True)
data = dict(title=cfg.get("radial_title", cfg["title"] + " · radial ties"), scenarios=cfg["scenarios"], band=BAND, levels=levels,
            subs=[dict(id=s, name=S[s]["name"], lat=round(S[s]["lat"], 4), lon=round(S[s]["lon"], 4)) for s in sorted(used)],
            pairs=[[a, c, kv] for (a, c), kv in pairs.items()], trees=trees,
            portfolios=[dict(key="per_tree", name="One tie per tree", note="the best measured design for each tree on its own",
                             lines=lines, left=0)])
size = vmap.inject(HERE / "radial_template.html", data, OUT / "radial_ties.html")
print(f"{len(trees)} trees (>= {MIN_KV} kV), {sum(1 for t in trees if any(d['meas'] for d in t['designs']))} with measurements, "
      f"{len(data['subs'])} subs, {len(data['pairs'])} context pairs; {size / 1e6:.1f} MB -> {OUT / 'radial_ties.html'}")
