"""Whole-grid islanding screen at substation scale. Offline.

    python islanding_screen.py <config.json>        -> islanding_rows.json

A BRIDGE is an in-service inter-substation branch whose loss splits the substation graph. Parallel
circuits are separate edges, so a double circuit is never a bridge. The meshed CORE is the largest
2-edge-connected piece. Every bridge hangs a POCKET (the substations on the far side from the core);
nested bridges along one radial tree are grouped under the tree's ATTACHMENT bridge -- the one that
leaves the core.

Why a screen and not the N-1 result: an outage that islands load often SOLVES with zero violations,
because the stranded buses are dropped rather than flagged. The violation count cannot see it.
Transformer-only islanding inside one substation (a generator step-up) is out of scope here.
"""
import collections
import json

import vmap

cfg, OUT = vmap.load_config()
SCES = vmap.scenario_keys(cfg)
T = json.load(open(OUT / "full_topo.json"))
S = {s["id"]: s for s in T["subs"]}
B = vmap.place_star_buses(T)
INJ = {sc: {int(k): v for k, v in json.load(open(OUT / f"full_inj_{sc}.json")).items()} for sc in SCES}
kvc = vmap.kv_class

# ---- substation multigraph
edges = []
adj = collections.defaultdict(list)
for i, br in enumerate(T["branches"]):
    if not br["on"]:
        continue
    a, c = B[br["f"]]["sub"], B[br["t"]]["sub"]
    if a is None or c is None or a == c:
        continue
    k = len(edges); edges.append((a, c, i)); adj[a].append((c, k)); adj[c].append((a, k))

# ---- bridges (iterative Tarjan over edge ids, so a parallel circuit is its own edge)
disc, low, bridges, t = {}, {}, set(), 0
for root in list(adj):
    if root in disc:
        continue
    disc[root] = low[root] = t; t += 1
    stack = [(root, -1, iter(adj[root]))]
    while stack:
        u, pe, it = stack[-1]
        nxt = next(it, None)
        if nxt is None:
            stack.pop()
            if stack:
                p = stack[-1][0]; low[p] = min(low[p], low[u])
                if low[u] > disc[p]:
                    bridges.add(pe)
            continue
        v, k = nxt
        if k == pe:
            continue
        if v in disc:
            low[u] = min(low[u], disc[v])
        else:
            disc[v] = low[v] = t; t += 1; stack.append((v, k, iter(adj[v])))

# ---- 2-edge-connected pieces; the core is the largest
comp, cid = {}, 0
for s in adj:
    if s in comp:
        continue
    q = [s]; comp[s] = cid
    while q:
        u = q.pop()
        for v, k in adj[u]:
            if k not in bridges and v not in comp:
                comp[v] = cid; q.append(v)
    cid += 1
size = collections.Counter(comp.values()); CORE = size.most_common(1)[0][0]
core_subs = {s for s, c in comp.items() if c == CORE}

# ---- bridge tree rooted at the core: for each bridge, the pocket on the far side
btree = collections.defaultdict(list)
for k in bridges:
    a, c, _ = edges[k]; btree[comp[a]].append((comp[c], k)); btree[comp[c]].append((comp[a], k))
members = collections.defaultdict(list)
for s, c in comp.items():
    members[c].append(s)
parent_bridge, parent_comp, order = {}, {CORE: None}, [CORE]
q = [CORE]
while q:
    u = q.pop()
    for v, k in btree[u]:
        if v not in parent_comp:
            parent_comp[v] = u; parent_bridge[v] = k; order.append(v); q.append(v)
sub_of = {}                      # component -> every substation below it, inclusive
for c in reversed(order):
    acc = list(members[c])
    for v, k in btree[c]:
        if parent_comp.get(v) == c:
            acc += sub_of[v]
    sub_of[c] = acc
attach = {}                      # component -> its tree's attachment bridge
for c in order[1:]:
    x = c
    while parent_comp[x] != CORE:
        x = parent_comp[x]
    attach[c] = parent_bridge[x]
bus_by_sub = collections.defaultdict(list)
for b in T["buses"]:
    bus_by_sub[b["sub"]].append(b["num"])


def mw(subs):
    buses = [n for s in subs for n in bus_by_sub[s]]
    return ([round(sum(INJ[sc].get(n, [0, 0])[0] for n in buses), 1) for sc in SCES],
            [round(sum(INJ[sc].get(n, [0, 0])[1] for n in buses), 1) for sc in SCES])


rows = []
for c in order[1:]:
    k = parent_bridge[c]; a, b_, i = edges[k]; br = T["branches"][i]
    near = a if comp[a] == parent_comp[c] else b_
    L, G = mw(sub_of[c])
    rows.append(dict(bridge=k, kv=kvc(br["kv"]), f=br["f"], t=br["t"], ckt=br["ckt"], xf=br["xf"], mi=br["mi"],
                     near=near, pocket=sorted(sub_of[c]), load=L, gen=G, attach=attach[c], top=parent_comp[c] == CORE))
print(f"{len(S)} subs | {len(edges)} inter-substation branches | {len(bridges)} bridges | core {len(core_subs)} subs | "
      f"{sum(1 for r in rows if r['top'])} radial trees hang off the core")
by = collections.defaultdict(lambda: [0, 0, 0, 0.0, 0.0])
for r in rows:
    x = by[r["kv"]]; x[0] += 1; x[1] += r["top"]; x[2] += len(r["pocket"]) if r["top"] else 0
    if r["top"]:
        x[3] += max(r["load"]); x[4] += max(r["gen"])
print("per voltage level of the bridge: bridges | trees | subs in trees | worst-dispatch load MW | gen MW")
for kv in (765, 345, 138, 69):
    x = by[kv]; print(f"  {kv:>4} kV: {x[0]:5d} | {x[1]:4d} | {x[2]:5d} | {x[3]:9.0f} | {x[4]:9.0f}")
vmap.dump(OUT / "islanding_rows.json", dict(rows=rows, core=sorted(core_subs)))
