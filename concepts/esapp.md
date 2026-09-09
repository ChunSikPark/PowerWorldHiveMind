---
type: tool
domain: tooling
aliases: [ESA++, esa_pp, esapp-api]
tags: [esapp, powerworld, simauto, python, tool]
---

# ESA++ (esapp) — tool reference

## Abstract

`esapp` (ESA++) is a Python toolkit that gives a Pythonic, pandas-flavored interface to PowerWorld Simulator's Automation Server (SimAuto) over COM. It is Windows-only and requires PowerWorld locally. This page is the full API map: top-level imports, architecture (mixin-built `SAW`, `PowerWorld` workbench, embedded modules), the bracket read/write interface, all `pw.*` methods, transient-stability helpers, and the GObject schema accessors. For how to drive it in practice, start at [esapp-overview](../methods/esapp-overview.md).

## Connections

- **Up:** [Home](../index.md) · esapp package
- **Across:** [powerworld-simauto](powerworld-simauto.md) · [esapp-overview](../methods/esapp-overview.md) · esa pp llm · time step simulation · dynamic line rating · reactive power planning · real power planning · synthetic creation · [gic](gic.md)
- **Field schema + commands:** [esapp-schema-reference](../references/esapp-schema-reference.md) — exact object key/identifier fields + SimAuto command catalog for writing esapp code
- **SCRIPT action catalog:** aux script catalog — full raw PowerWorld SCRIPT-command name index (344 actions), for anything not yet wrapped by a named SAW method
- **House rule for calling them:** esapp script command wrappers — call `pw.esa.TimeStepDoRun()`, never `RunScriptCommand("TimeStepDoRun;")`; also the 0.2.1 change that made a bad write warn instead of raise

## Content

`esapp` (ESA++) is a Python toolkit that gives a Pythonic, pandas-flavored
interface to **PowerWorld Simulator's Automation Server (SimAuto)** over COM
(see [powerworld-simauto](powerworld-simauto.md)). It is **Windows-only** (depends on `pywin32` for
COM interop) and requires PowerWorld Simulator installed locally. This page is
*what it is* — the API map. For *how to drive it*, start at [esapp-overview](../methods/esapp-overview.md).
The project that maintains/extends the package is esapp package.

> Source of truth: `C:\path\to\esapp`. Every symbol below was
> read out of that tree. Validate against `esapp` source (or the `esapp` skill)
> before shipping any `methods/` page that calls the API.

## Top-level imports

```python
from esapp import PowerWorld          # main entry point
from esapp import SAW                 # low-level SimAuto wrapper (usually via pw.esa)
from esapp import TS, TSField         # transient-stability field constants
from esapp.components import Bus, Gen, Load, Branch, Shunt, Area, Zone  # GObject types
from esapp.utils import TSWatch, ContingencyBuilder, SimAction, BranchType  # helpers
```

`esapp/__init__.py` exports `PowerWorld`, `SAW`, `TS`, `TSField`, and the
exception hierarchy (`PowerWorldError`, `COMError`, `SimAutoFeatureError`,
`PowerWorldPrerequisiteError`, `PowerWorldAddonError`). `CommandNotRespectedError` was
**removed in 0.2.0** — do not reference it.
Note: `TSWatch` / `ContingencyBuilder` are **not** top-level — import them from
`esapp.utils`.

## Architecture (real)

- **`PowerWorld`** — `esapp/workbench.py`. The user-facing class; subclass of
  `Indexable`. Holds the live SimAuto connection on `pw.esa` and three embedded
  application modules: `pw.network`, `pw.gic`, `pw.buscat`.
- **`Indexable`** — `esapp/indexable.py`. Implements the bracket read/write
  interface (`__getitem__` / `__setitem__`) and `open()`.
- **`SAW` (SimAuto Wrapper)** — `esapp/saw/saw.py`. Built by the **mixin
  pattern** from `SAWBase` (`saw/base.py`) plus ~20 focused mixins:
  `DataMixin`, `PowerflowMixin`, `MatrixMixin`, `ContingencyMixin`,
  `TransientMixin`, `SensitivityMixin`, `GICMixin`, `OPFMixin`, `PVMixin`,
  `QVMixin`, `ATCMixin`, `FaultMixin`, `TopologyMixin`, `RegionsMixin`,
  `ModifyMixin`, `GeneralMixin`, `CaseActionsMixin`, `ScheduledActionsMixin`,
  `TimeStepMixin`, `WeatherMixin`. This is the raw COM layer — reach it via
  `pw.esa`.
- **Components** — `esapp/components/`. `grid.py` (auto-generated, large) holds
  a `GObject` subclass per PowerWorld object type; `ts_fields.py` holds the
  `TS` / `TSField` constants; `gobject.py` is the base class;
  `generate_components.py` regenerates both from the `PWRaw` TSV schema. **Do
  not hand-edit `grid.py` / `ts_fields.py` — regenerate them.**
- **Utils** — `esapp/utils/`: `network.py` (`Network`), `gic.py` (`GIC`),
  `dynamics.py` (`TSWatch`, TS result processing), `contingency.py`
  (`ContingencyBuilder`, `SimAction`), `b3d.py` (`B3D` field-file I/O),
  `buscat.py` (`BusCat`).
- **Enums / descriptors / exceptions** — `saw/_enums.py` (`SolverMethod`,
  `JacobianForm`, `LinearMethod`, `PowerWorldMode`, filter keywords, …),
  `_descriptors.py` (`SolverOption`, `GICOption` descriptors), and
  `saw/_exceptions.py` (`PowerWorldError` hierarchy).

## Bracket data interface (the core idiom)

```python
pw[Bus]                              # primary-key columns only
pw[Bus, "BusPUVolt"]                 # keys + one field
pw[Gen, ["GenMW", "GenMVR", "GenStatus"]]   # keys + several
pw[Bus, :]                           # keys + EVERY defined field
```

Reads go through `esa.GetParamsRectTyped` and return a typed `DataFrame`.
Writes use the same brackets:

```python
pw[Gen, "GenMW"] = 100.0             # broadcast scalar to existing gens
pw[Gen, "GenMW"] = [100, 150, 200]   # per-element list
pw[Bus] = df                         # bulk update from a DataFrame (must carry primary keys)
```

`pw[Type] = df` can also **create** objects when the case is in EDIT mode and
the SAW was opened with `CreateIfNotFound=True`.

> ⚠️ **Changed in 0.2.1.** Unknown and read-only columns used to raise
> `ValueError: Cannot set read-only field(s)` (`indexable.py:228`/`:280` in 0.1.x). They
> now emit a `warnings.warn` and the write is **still attempted** — PowerWorld is treated
> as the authority so a lagging generated schema can't block a newer Simulator's fields.
> The cost: a field-name typo no longer raises. Run write-heavy code under
> `python -W error::UserWarning`. See esapp script command wrappers.

> ⚠️ **Key fields are mandatory for writes.** PowerWorld matches each row back to an
> object by its **key field(s)** (e.g. `BusNum`+`GenID` for a Gen). The bracket read
> includes the keys automatically, so a read-modify-write round-trip keeps them — but if
> you build a DataFrame by hand, or drop columns, it **must still carry the key columns**
> or the write silently does nothing (no error, no change applied). On the raw `esa`/SAW
> path you must prepend them yourself: `pw.esa.get_key_field_list('gen') + [<fields>]`. Rule
> of thumb: never strip key columns from a DataFrame you intend to push back.

## PowerWorld API surface (`pw.*`, from workbench.py)

- **State / case** — `pw.open()`, `pw.save(filename=None)`, `pw.close()`,
  `pw.edit_mode()`, `pw.run_mode()`, `pw.flatstart()`, `pw.snapshot()`
  (context manager: `SaveState` on enter, `LoadState` on exit),
  `pw.log(msg)`, `pw.print_log(...)`.
- **Solve** — `pw.pflow(getvolts=True, method=SolverMethod.POLARNEWT)` returns a
  complex voltage Series; `pw.ts_solve(ctgs, fields)` runs transient stability
  and returns `(metadata, timeseries)` DataFrames.
- **Voltages / power** — `pw.voltage(complex=True, pu=True)`,
  `pw.set_voltages(V)`, `pw.mismatch(asComplex=False)`, `pw.netinj(...)`,
  `pw.violations(v_min=0.9, v_max=1.1)`.
- **Matrices / topology** — `pw.ybus(dense=False)`,
  `pw.jacobian(dense=False, form=JacobianForm.RECTANGULAR, ids=False)`,
  `pw.busmap()`, `pw.buscoords(astuple=True)` (returns a `(Longitude,
  Latitude)` tuple by default — **not** a DataFrame).
- **Convenience tables** — `pw.gens()`, `pw.loads()`, `pw.shunts()`,
  `pw.lines()`, `pw.transformers()`, `pw.areas()`, `pw.zones()`,
  `pw.flows()`, `pw.overloads(threshold=100.0)`.
- **Sensitivities** — `pw.ptdf(seller, buyer, method=LinearMethod.DC)`,
  `pw.lodf(branch, method=LinearMethod.DC)`.
- **Quick props** — `pw.n_bus`, `pw.n_branch`, `pw.n_gen`, `pw.sbase`,
  `pw.summary()` (dict of counts + totals + v_min/v_max).
- **Solver options as descriptors** — set them like attributes:
  `pw.flat_start = True`, `pw.max_iterations = 30`, `pw.convergence_tol = 1e-4`,
  `pw.dc_mode = True`, … (each is a `SolverOption` mapping to a PowerWorld
  Sim_Solution_Options field).

## Embedded modules

- **`pw.network`** (`utils/network.py`) — `incidence()`, `laplacian(weights,
  ...)`, `lengths()`, `zmag()`, `ybranch()`, `yshunt()`, `gamma()`, `delay()`,
  `busmap()`, `buscoords()`; `BranchType.{LENGTH, RES_DIST, DELAY}` weighting.
- **`pw.gic`** (`utils/gic.py`) — `configure()`, `storm(maxfield, direction,
  solvepf=True)`, `model()`, `gmatrix(sparse=True)`, `settings()`,
  `cleargic()`, `loadb3d()`, `timevary_csv()`; result matrices on properties
  `A, G, H, zeta, Px, eff`; options via descriptors `pf_include`, `efield_mag`,
  `efield_angle`, `calc_mode`, … See [gic](gic.md).
- **`pw.buscat`** (`utils/buscat.py`) — bus classification.

## Transient stability (TS)

> ⚠️ **"TS" disambiguation — do not conflate.** Here `TS` = **Transient Stability**: a
> dynamics study of faults, generator trips, rotor angles, and frequency over
> milliseconds-to-seconds (`pw.ts_solve`, `TSWatch`, `ContingencyBuilder`, `TS.*` field
> constants). This is **completely unrelated** to the `time-step-simulation` project
> (PowerWorld's **TimeStep** weather feature: `.pww` weather → hourly solar/wind MW),
> which uses the low-level `esa` `TimeStep*` script commands, NOT this `ts_solve` API.
> (Intentionally NOT wikilinked — there is no relationship to graph.) The shared letters
> are a coincidence; the
> `TSPFWModelString` field's "TS" likewise means *TimeStep*, not Transient Stability.
> These two never reference each other.

```python
from esapp.utils import TSWatch, ContingencyBuilder
tsw = TSWatch().watch(Gen, [TS.Gen.P, TS.Gen.W])
fields = tsw.prepare(pw)
ctg = ContingencyBuilder("GenTrip", runtime=5.0).at(1.0).fault_bus("101").at(1.1).clear_fault("101")
meta, data = pw.ts_solve("GenTrip", fields)
```

`TSWatch` registers result fields; `ContingencyBuilder` fluently builds transient-stability
event sequences (`SimAction` enum). For dynamics studies only — see [powerworld-simauto](powerworld-simauto.md)
for the underlying `TransientMixin`.

## GObject schema access

Every component class exposes `@classmethod` schema accessors (call with `()`):
`Bus.TYPE()`, `Bus.keys()`, `Bus.fields()`, `Bus.secondary()`,
`Bus.editable()`, `Bus.identifiers()`, `Bus.settable()`.

## Used across

esapp package · esa pp llm · time step simulation ·
reactive power planning · real power planning · synthetic creation ·
dynamic line rating — most PowerWorld work in this wiki routes through it.

## Related

- How-to entry: [esapp-overview](../methods/esapp-overview.md) · underlying COM server: [powerworld-simauto](powerworld-simauto.md)
- Writing devices + DC OPF + N-1 (write-side mechanics): [adding-devices-esapp](../methods/adding-devices-esapp.md)
- Feeds the esa pp llm agent's knowledge base.
