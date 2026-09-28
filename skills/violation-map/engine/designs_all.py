"""Suggested ties for every radial tree from islanding_screen.py. Offline.

    python designs_all.py <config.json>        -> tree_designs.json

Per tree:
  SOURCE   the tree substation (with a network bus at the tree's kV) that carries the most MW, then
           the one whose tie removes the most bridges on its way to the core. The tie starts where
           the MW is: picking the substation that closes the most bridges once put a plant's whole
           output through a lower-voltage line inside the pocket when the plant's exit opened.
  LANDINGS core substations with a network bus at the same kV, >= 2 distinct core neighbours, not
           the tree's own attachment substation (a tie back to the same substation fails the
           single-substation test), and whose name contains none of radial.exclude_landing_name_parts
           (large-load taps and the like). Nearest two within radial.reach_mi, else within
           radial.reach_max_mi, flagged long.
  TEMPLATE a same-kV in-service line whose rating clears the tree's worst stranded MW (x1.1), nearest
           in length. A template picked by length alone once put a line at 250% into a delivered case.
Straight-line miles throughout.
"""
import collections
import json

import vmap

cfg, OUT = vmap.load_config()
RC = cfg["radial"]
T = json.load(open(OUT / "full_topo.json"))
IR = json.load(open(OUT / "islanding_rows.json"))
S = {s["id"]: s for s in T["subs"]}
B = vmap.place_star_buses(T)
CORE = set(IR["core"])
kvc = vmap.kv_class
NB = vmap.net_bus(cfg)
AVOID = tuple(RC["exclude_landing_name_parts"])
mi = lambda a, b: vmap.miles(S[a]["lat"], S[a]["lon"], S[b]["lat"], S[b]["lon"])

bus_at = collections.defaultdict(dict)       # sub -> kv class -> a network bus there
for b in T["buses"]:
    if b["sub"] is not None and NB(b):
        bus_at[b["sub"]].setdefault(kvc(b["kv"]), b["num"])
core_nb = collections.defaultdict(set)
for br in T["branches"]:
    a, c = B[br["f"]]["sub"], B[br["t"]]["sub"]
    if br["on"] and a is not None and c is not None and a != c and a in CORE and c in CORE:
        core_nb[a].add(c); core_nb[c].add(a)
lines = [br for br in T["branches"] if br["on"] and not br["xf"] and not br["w"] and br["mi"] > 3]

INJ = [{int(k): v for k, v in json.load(open(OUT / f"full_inj_{sc}.json")).items()} for sc in vmap.scenario_keys(cfg)]
sub_mw = collections.Counter()
for b in T["buses"]:
    if b["sub"] is not None:
        sub_mw[b["sub"]] = max(sub_mw[b["sub"]], max(sum(inj.get(b["num"], [0, 0])) for inj in INJ))
trees = collections.defaultdict(list)
for r in IR["rows"]:
    trees[r["attach"]].append(r)
out = []
for k, rs in trees.items():
    top = next(r for r in rs if r["top"])
    kv = top["kv"]
    tree_subs = set(top["pocket"])
    stake = max(max(r["load"]) + max(r["gen"]) for r in rs if r["top"])
    best = None
    for s in tree_subs:
        if kv not in bus_at[s]:
            continue
        cov = [r for r in rs if s in r["pocket"]]
        key = (round(sub_mw.get(s, 0), 1), len(cov), sum(max(r["load"]) + max(r["gen"]) for r in cov))
        if best is None or key > best[0]:
            best = (key, s, cov)
    base = dict(attach=k, kv=kv, tree=sorted(tree_subs), bridges=[dict(f=r["f"], t=r["t"], ckt=r["ckt"], mi=r["mi"], xf=r["xf"],
                pocket=r["pocket"], load=r["load"], gen=r["gen"]) for r in rs], near=top["near"], stake_mw=round(stake, 1),
                max_load=max(max(r["load"]) for r in rs), max_gen=max(max(r["gen"]) for r in rs))
    if best is None:
        out.append(dict(base, designs=[], why=f"no substation in the tree has a {kv} kV network bus"))
        continue
    _, src, cov = best
    cands = sorted(((mi(src, c), c) for c in CORE if kv in bus_at[c] and len(core_nb[c]) >= 2 and c != top["near"]
                    and not any(p in S[c]["name"] for p in AVOID)), key=lambda x: x[0])
    near = [x for x in cands if x[0] <= RC["reach_mi"]][:2] or [x for x in cands if x[0] <= RC["reach_max_mi"]][:2]
    need = stake * 1.1
    des = []
    for d, c in near:
        pool = [l for l in lines if kvc(l["kv"]) == kv and abs(l["kv"] - l["kv_lo"]) < 1 and l["rate"] >= need] or \
               [l for l in lines if kvc(l["kv"]) == kv and abs(l["kv"] - l["kv_lo"]) < 1]
        if not pool:
            continue
        tm = min(pool, key=lambda l: abs(l["mi"] - d))
        des.append(dict(frm=src, fb=bus_at[src][kv], to=c, tb=bus_at[c][kv], mi=round(d, 1), long=d > RC["reach_mi"],
                        covers=len(cov), of=len(rs), tmpl=[tm["f"], tm["t"], tm["ckt"]], tmpl_mi=tm["mi"],
                        tmpl_rate=tm["rate"], rate_clears=tm["rate"] >= need))
    out.append(dict(base, designs=des, why="" if des else f"no core landing within {RC['reach_max_mi']} mi"))
out.sort(key=lambda x: (-x["kv"], -x["stake_mw"]))
vmap.dump(OUT / "tree_designs.json", out)
n = collections.Counter((x["kv"], bool(x["designs"]), x["stake_mw"] > 0) for x in out)
print("trees by (kV, has design, MW at stake):", dict(sorted(n.items(), reverse=True)))
print("designs:", sum(len(x["designs"]) for x in out), f"| long (>{RC['reach_mi']} mi):", sum(d["long"] for x in out for d in x["designs"]))
