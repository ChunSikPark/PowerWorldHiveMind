---
type: method
domain: tooling
aliases: [comparing-planning-cases, case-diff, case-comparison, planning-delta, what-changed, new-devices]
tags: [demo, planning, case-diff, contingency, aux, esapp, worked-example]
---

# Demo: Comparing two planning cases, and testing what the plan builds

## Abstract

Two vintages of the same system — a 2016 summer peak and a 2024 summer peak — diffed to
find what the plan actually builds, then a contingency set generated for **only the new
devices** and solved. Real numbers throughout: 691 new branches, 199 new generators, and
a scoping trap that would have made the headline answer **87% wrong**.

## Connections

- **Up:** [Home](../index.md) · demos index
- **Across:** [new-device-contingency-aux](../methods/new-device-contingency-aux.md) · [ranking-new-devices-by-severity](../methods/ranking-new-devices-by-severity.md) · [contingency-and-aux](contingency-and-aux.md) · [reading-violationctg](../methods/reading-violationctg.md) · [adding-devices-esapp](../methods/adding-devices-esapp.md)

## Content

### The user's prompt

> *"Compare my 2016 and 2024 cases, work out what the plan builds, and tell me whether
> the new devices cause problems."*

### Step 1 — the two cases

```python
from esapp import PowerWorld
from esapp.components import Bus, Branch, Gen

a = PowerWorld(r"C:\cases\Synth2k_case1.pwb")
b = PowerWorld(r"C:\cases\Synth2k_case.PWB")
for name, s in (("2016", a.summary()), ("2024", b.summary())):
    print(f"{name}: {s['n_bus']} buses / {s['n_branch']} branches / "
          f"{s['n_gen']} gens / load {s['total_load_mw']:.0f} MW")
```

```
2016 summerpeak: 2000 buses / 3220 branches / 544 gens / load 67109 MW
2024 summerpeak: 2000 buses / 3911 branches / 743 gens / load 87578 MW
```

Load grows 67.1 GW → 87.6 GW, **+30.5%** over eight years. That framing matters: the
build is a response to that growth, and it is the first thing to report.

### Step 2 — diff, but guard against false construction

**A naive diff is wrong in the direction that looks right.** A renumbered bus, a
relabelled circuit, or a swapped from/to each produce a RETIRED row *and* a matching NEW
row. An unguarded comparison reports construction that never happened, and the output
looks entirely plausible.

So run the naive diff and the guarded one, and compare them:

```python
# --- buses: naive by number, then paired by (name, kV) ---
ba, bb = a[Bus, ["BusName", "BusNomVolt"]], b[Bus, ["BusName", "BusNomVolt"]]
na, nb = set(ba["BusNum"].astype(int)), set(bb["BusNum"].astype(int))

key = lambda d: set(zip(d["BusName"].astype(str).str.strip(), d["BusNomVolt"].round(2)))
ka, kb = key(ba), key(bb)

renumbered = (len(na - nb) + len(nb - na)) - (len(ka - kb) + len(kb - ka))
```

```
BUSES  naive by BusNum  : retired-looking 0, new-looking 0
       paired by (name,kV): only-2016 0, only-2024 0
       => 0 bus rows differ by NUMBERING only
```

Same for branches, normalising the endpoint order:

```python
bf = lambda pw: set(zip(pw[Branch]["BusNum"].astype(int),
                        pw[Branch]["BusNum:1"].astype(int),
                        pw[Branch]["LineCircuit"].astype(str).str.strip()))
norm = lambda s: {(min(x, y), max(x, y), c) for x, y, c in s}
```

```
BRANCHES naive             : retired-looking 0, new-looking 691
         from/to normalised: retired 0, NEW 691
         => 0 were FROM/TO SWAPS, not construction

GENERATORS: retired 0, NEW 199
```

**This pair is clean** — no renumbering, no swaps, nothing retired. Pure expansion: 691
branches and 199 generators added.

That is a finding, not a formality. Run the guarded diff *anyway*, every time. When the
two counts agree you have earned the right to trust the number; when they disagree, the
naive answer was fiction and you would never have known.

Devices present in both but with changed parameters are a third category — **UPGRADED**
— found by comparing ratings and impedances on the common keys, not by set difference.

### Step 3 — a contingency set for only the new devices

```python
kv = {int(r["BusNum"]): float(r["BusNomVolt"]) for _, r in b[Bus, ["BusNomVolt"]].iterrows()}
new = sorted(bf(b) - bf(a))
hv = [t for t in new if max(kv.get(t[0], 0), kv.get(t[1], 0)) >= 345]
```

```
new branches: 691
of which >=345 kV: 31
```

Scope before you solve. 691 contingencies on a 2000-bus case is a long wait; the 31
highest-voltage additions answer the question that matters first.

```python
sel = hv[:25]
lines  = ["CONTINGENCY (Name, Skip)", "{"]
lines += [f'"NEW_{f}_{t}_{c}" "NO"' for f, t, c in sel] + ["}", ""]
lines += ["CONTINGENCYELEMENT (Contingency, Object, Action, Status)", "{"]
lines += [f'"NEW_{f}_{t}_{c}" "BRANCH {f} {t} {c}" "OPEN" "CHECK"' for f, t, c in sel] + ["}"]

aux = os.path.abspath(r"C:\out\tx_new_devices.aux")
open(aux, "w", encoding="utf-8").write("\n".join(lines))

b.esa.RunScriptCommand("CTGClearAllResults")
n0 = len(b[Contingency])
b.esa.RunScriptCommand(f'LoadAux("{aux}", YES)')
n1 = len(b[Contingency])
assert n1 - n0 == len(sel)
```

```
wrote aux: 2216 bytes, 25 contingencies
contingencies in case before LoadAux: 3875
after LoadAux: 3900  (added 25)
```

**Note that first number.** The 2024 case already carried **3,875 contingencies** of its
own. Which sets up the trap.

### Step 4 — the trap that makes the answer 87% wrong

```python
b.esa.RunScriptCommand("CTGSolveAll")
v = b[ViolationCTG, ["CTGLabel", "LimViolValue", "LimViolLimit"]]
print("total violation rows:", len(v))
```

```
total violation rows: 240
```

Report that and you have said the plan's new 345 kV devices cause 240 violations. Now
filter by the labels you actually created:

```python
labs = v["CTGLabel"].astype(str).str.strip()
mine = labs.str.startswith("NEW_")
print("from MY new-device contingencies :", int(mine.sum()))
print("from contingencies already in the case:", int((~mine).sum()))
```

```
from MY new-device contingencies : 32
from OTHER contingencies already in the case: 208
```

**`LoadAux` adds contingencies. It does not scope the solve.** `CTGSolveAll` solved all
3,900, and 208 of the 240 violations belong to contingencies that were already in the
case and have nothing to do with the plan. The honest number is **32**, not 240 — the
naive answer overstates by 87%.

Two ways to get this right, and you should do both:

1. **Filter results by your label prefix**, as above. Cheap, and it also documents intent.
2. **Restrict what solves.** Set `Skip` to `YES` on the pre-existing contingencies, or
   build a case that carries only your set. This is the autoinsert-then-restrict pattern
   in [new-device-contingency-aux](../methods/new-device-contingency-aux.md).

Filtering alone still *solves* 3,900 contingencies, so on a large case do the restriction
too — for the runtime, not just the arithmetic.

And remember PowerWorld **trims whitespace from `CTGLabel` on load**, so strip before
matching on a prefix. A label that fails to match looks exactly like a contingency with
no violations.

### Step 5 — rank the new devices

With the correct 32 rows, group by contingency and rank:

```python
v = v[mine].copy()
v["pct"] = v["LimViolValue"] / v["LimViolLimit"] * 100
agg = (v.groupby(labs[mine])
        .agg(rows=("pct", "size"), worst=("pct", "max"))
        .sort_values(["rows", "worst"], ascending=False))
```

Rank on **rows and worst severity together**. A device causing one 130% violation is a
different problem from one causing eight at 101%, and which is worse is a planning call.
Full scoring method, including why voltage must not rank on `LimViolPct`, is in
[ranking-new-devices-by-severity](../methods/ranking-new-devices-by-severity.md).

### What to report back

> **The plan.** Between 2016 and 2024 summer peak, load grows 67.1 → 87.6 GW (+30.5%).
> The build adds **691 branches and 199 generators**, retires nothing, and renumbers
> nothing — I checked, by pairing buses on (name, kV) and normalising branch endpoint
> order, so none of those additions are diff artifacts.
>
> **Testing.** I built a contingency set for the 25 highest-voltage new branches
> (31 are ≥345 kV) and solved.
>
> **Result: 32 violations attributable to the new devices.** The raw solve reported 240,
> but 208 belong to the 3,875 contingencies already in the case and are not part of this
> plan.
>
> Nothing was saved. The aux is on disk for reuse.
>
> Pages used: `methods/new-device-contingency-aux.md`,
> `methods/reading-violationctg.md`, `demos/contingency-and-aux.md`.

### The two lessons

**Guard the diff.** Numbering, labelling and endpoint order all manufacture fake
construction. Run both the naive and guarded comparisons and report when they disagree.

**Scope the solve, or scope the results.** Adding contingencies does not remove the ones
already there. Attribute every violation to the contingency that produced it before
attributing anything to the plan.
