"""Bridges and the radial pockets they hang, on the bus multigraph. Iterative, so a 100k-bus
case does not hit Python's recursion limit. Mirrors the bridge search of the violation-map
engine's islanding screen (same conventions), at bus level and as a library.

Parallel circuits are separate edges, so a double circuit is never a bridge. The meshed core
is the largest 2-edge-connected piece; each bridge's far side is the part away from the core.
Only far-side sizes are computed for every bridge; the far side itself is built on demand, for
the few bridges a rule asks about, and capped.
"""
from __future__ import annotations

from collections import Counter, defaultdict


def bridges(nodes, edges) -> set[int]:
    """Indices of the edges whose loss splits their component. edges: list of (u, v)."""
    adj = adjacency(edges)
    disc, low, out, t = {}, {}, set(), 0
    for root in nodes:
        if root in disc:
            continue
        disc[root] = low[root] = t
        t += 1
        stack = [(root, -1, iter(adj[root]))]
        while stack:
            u, pe, it = stack[-1]
            nxt = next(it, None)
            if nxt is None:
                stack.pop()
                if stack:
                    p = stack[-1][0]
                    low[p] = min(low[p], low[u])
                    if low[u] > disc[p]:
                        out.add(pe)
                continue
            v, k = nxt
            if k == pe:
                continue
            if v in disc:
                low[u] = min(low[u], disc[v])
            else:
                disc[v] = low[v] = t
                t += 1
                stack.append((v, k, iter(adj[v])))
    return out


def adjacency(edges) -> dict:
    adj = defaultdict(list)
    for k, (u, v) in enumerate(edges):
        adj[u].append((v, k))
        adj[v].append((u, k))
    return adj


def pockets(nodes, edges) -> dict[int, dict]:
    """For every bridge reachable from the core: {edge: {"near": core-side node, "far": far-side
    terminal, "size": far-side bus count, "parent": the next bridge towards the core or None}}.
    Sizes come from a post-order walk over integers; no per-bridge node sets are built, so memory
    stays linear in the case size however deep the radial chains run."""
    br = bridges(nodes, edges)
    adj = adjacency(edges)
    comp = {}
    for s in nodes:
        if s in comp:
            continue
        comp[s], q = s, [s]
        while q:
            u = q.pop()
            for v, k in adj[u]:
                if k not in br and v not in comp:
                    comp[v] = s
                    q.append(v)
    if not comp:
        return {}
    pieces = Counter(comp.values())
    core = pieces.most_common(1)[0][0]
    members = defaultdict(list)
    for n, c in comp.items():
        members[c].append(n)
    info, order, child_of, seen = {}, [], {}, {core}
    stack = [(core, None)]
    while stack:                                   # walk the bridge tree outward from the core
        c, parent_edge = stack.pop()
        order.append(c)
        for n in members[c]:
            for v, k in adj[n]:
                if k in br and comp[v] not in seen:
                    seen.add(comp[v])
                    info[k] = {"near": n, "far": v, "parent": parent_edge}
                    child_of[comp[v]] = k
                    stack.append((comp[v], k))
    size = {c: pieces[c] for c in seen}
    for c in reversed(order):                      # leaves first: add each subtree to its parent
        k = child_of.get(c)
        if k is not None:
            size[comp[info[k]["near"]]] += size[c]
            info[k]["size"] = size[c]
    return info


def far_side(adj, k, far, limit):
    """The buses beyond bridge k: a search from its far terminal that never crosses k. None as
    soon as it passes `limit` buses, so a big radial region costs `limit` steps, not its size."""
    side, q = {far}, [far]
    while q:
        u = q.pop()
        for v, e in adj[u]:
            if e != k and v not in side:
                side.add(v)
                if len(side) > limit:
                    return None
                q.append(v)
    return side
