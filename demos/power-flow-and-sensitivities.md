---
type: method
domain: tooling
aliases: [demo-power-flow, dcpf-demo, ptdf-demo, lodf-demo, sensitivities-demo]
tags: [demo, powerflow, dcpf, ptdf, lodf, esapp, worked-example]
---

# Demo: Power flow, DC mode, LODF and PTDF

## Abstract

Solving a case and asking the three standard sensitivity questions, on a real 37-bus
system. Includes the `1e8` sentinel that makes LODF results look insane, and a PTDF
failure whose obvious recovery **also fails** — both encountered in an actual run, both
recovered without asking the user.

## Connections

- **Up:** [Home](../index.md) · demos index
- **Across:** [esapp-overview](../methods/esapp-overview.md) · [lodf](../concepts/lodf.md) · [handling-errors](../methods/handling-errors.md) · [esapp-environment](../concepts/esapp-environment.md)

## Content

### The user's prompts

> *"Open my case and tell me which branches are most heavily loaded."*
> *"Run it as a DC power flow instead."*
> *"If the most loaded line trips, where does the flow go?"*

### AC power flow

```python
from esapp import PowerWorld
from esapp.components import Bus, Branch, Gen, Load

pw = PowerWorld(r"C:\path\to\Synth40.pwb")
pw.pflow()

v = pw[Bus, "BusPUVolt"]["BusPUVolt"]
print(f"V {v.min():.4f} - {v.max():.4f} pu, overloads {len(pw.overloads())}")
```

```
V 0.9749-1.0034 pu, overloads 0
```

`overloads()`, `violations()`, `mismatch()`, `flows()`, `ptdf()`, `lodf()`, `ybus()` are
**all methods** — call them. Referencing one without parentheses hands you a bound method
that fails confusingly further down.

Ranking by loading:

```python
br = pw[Branch, ["LineMVA", "LineLimMVA", "LinePercent"]]
top = br.sort_values("LinePercent", ascending=False).head(5)
```

```
  27 ->  29 ckt 1     54.65 /   67.50 MVA =  80.96%
  19 ->  23 ckt 2     78.14 /  100.30 MVA =  77.90%
  19 ->  23 ckt 3     78.14 /  100.30 MVA =  77.90%
  19 ->  23 ckt 1     78.14 /  100.30 MVA =  77.90%
  19 ->  23 ckt 4     78.14 /  100.30 MVA =  77.90%
```

Four identical rows for 19→23 are four **parallel circuits**, not duplicates. Check the
circuit id before reporting a repeated bus pair as a data error.

### DC power flow — an option, not a method

```python
pw.dc_mode = True      # NOT pw.dc_mode(True)
pw.pflow()
print(f"max loading {pw[Branch, 'LinePercent']['LinePercent'].max():.2f}%")
pw.dc_mode = False     # put it back
pw.pflow()
```

```
max loading 80.96%  |  branches >90%: 0
```

`pw.dc_mode(True)` raises `TypeError: 'bool' object is not callable`. It is an assignable
solver option. Same for the other solver flags: `flat_start`, `max_iterations`,
`enforce_gen_mw_limits`.

**A DC solve always reports zero mismatch.** It cannot tell you generation is short — the
slack bus absorbs the shortfall silently. Check the schedule against load directly, and
say plainly when a result is DC.

### LODF — and the sentinel that ruins it

```python
L = pw.lodf((27, 29, "1"))       # (from_bus, to_bus, circuit)
```

Ranked naively, the answer is nonsense:

```
    1 ->   2  +100000000.0000
    1 ->   2  +100000000.0000
    1 ->   5  +100000000.0000
```

`1e8` is PowerWorld's **"undefined"** marker, not a distribution factor. Nothing receives
a hundred million times the flow. Filter it:

```python
real = L[L["LineLODF"].abs() < 1e7]
top = real.reindex(real["LineLODF"].abs().sort_values(ascending=False).index).head(5)
```

```
rows total 89, sentinel rows 88, real 1
    27 ->  29 ckt 1  LODF -100.0000
```

Only the outaged branch itself has a defined factor: it loses 100% of its own flow. On
this small system that outage does not redistribute onto anything with a defined LODF,
which is a finding about the topology — report it as such, not as "the calculation
failed."

**A result that looks absurd is your bug until proven otherwise.** Never report a
100,000,000 anything.

### PTDF — a failure, and a recovery that also fails

The obvious first attempt:

```python
areas = pw[Area]
P = pw.ptdf(seller=int(areas["AreaNum"].iloc[0]), buyer=int(areas["AreaNum"].iloc[-1]))
```

```
PowerWorldError: Error in script action execution:
Seller and Buyer can not be the same in script action CalculatePTDF
```

The case has exactly **one** area, so first and last are the same. Recovery: use buses.

```python
g = pw[Gen, "GenMW"].groupby("BusNum")["GenMW"].sum().sort_values(ascending=False)
l = pw[Load, "LoadSMW"].groupby("BusNum")["LoadSMW"].sum().sort_values(ascending=False)
P = pw.ptdf(seller=int(g.index[0]), buyer=int(l.index[0]))
```

```
biggest gen bus 23, biggest load bus 23
PowerWorldError: Seller and Buyer can not be the same
```

**The recovery failed the same way.** On this case the largest generator and the largest
load are the same bus. Force them apart:

```python
src = int(g.index[0])
snk = int(next(b for b in l.index if int(b) != src))
P = pw.ptdf(seller=src, buyer=snk)
```

```
seller bus 23 (460.8 MW gen), buyer bus 26 (75.3 MW load)
OK  89 branches, 89 with real PTDF
    2 ->  26 ckt 2   PTDF +27.2714
    2 ->  26 ckt 1   PTDF +27.2714
   24 ->  33 ckt 1   PTDF -21.3910
   25 ->  26 ckt 1   PTDF +12.0331
   25 ->  26 ckt 2   PTDF +12.0331
```

Two lessons. First, **an error's obvious fix can reproduce the same error** — check that
the recovery actually satisfies the constraint. Second, do not ask the user about any of
this. They wanted sensitivities, not a report on area counts.

Signatures, verified:

```python
pw.ptdf(seller: int, buyer: int, method: str = "DC") -> DataFrame
pw.lodf(branch: tuple, method: str = "DC")           -> DataFrame
pw.ybus(dense: bool = False)                          # csr_matrix (37, 37)
```

### What to report back

> Case solved: 37 buses, voltage 0.975–1.003 pu, no base-case overloads. The most loaded
> branch is 27→29 at **80.96%** of its 67.5 MVA rating; the four parallel 19→23 circuits
> each sit at 77.9%.
>
> Outaging 27→29 produces no defined LODF onto other branches — on this system that
> outage does not redistribute measurably.
>
> The case has one area, so I computed PTDFs for a bus-to-bus transfer, bus 23 → bus 26.
> Most sensitive: 2→26 at +27.3.
>
> Pages used: `methods/esapp-overview.md`, `concepts/lodf.md`, `methods/handling-errors.md`.
