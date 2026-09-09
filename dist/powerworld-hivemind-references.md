# PowerWorldHiveMind - REFERENCES

# ==== aux-script-commands.md ====

---
type: reference
domain: tooling
aliases: [aux-script-commands, script-commands, aux-actions, script-action-index, powerworld-script-actions]
tags: [powerworld, aux, script, commands, reference, simauto]
---

# Reference: PowerWorld SCRIPT actions — working subset

## Abstract

A task-organized index of the PowerWorld SCRIPT actions this kit's workflows actually
use, plus their close neighbours — 198 of the ~370 that Simulator defines. Look
here to find *which* command does a job; look in Simulator's own *Auxiliary File Format*
manual for argument lists and exact syntax, which this page deliberately does not
reproduce. Every command runs the same way: `pw.esa.RunScriptCommand("ActionName(args)")`,
or inside a `SCRIPT { }` block in an `.aux` file. Start at [esapp-overview](../methods/esapp-overview.md) for the
Python side.

## Connections

- **Up:** [Home](../index.md)
- **Across:** [esapp](../concepts/esapp.md) · [powerworld-simauto](../concepts/powerworld-simauto.md) · [esapp-schema-reference](esapp-schema-reference.md)
- **Deeper:** [esapp-package-backend](esapp-package-backend.md)

## Content

> **Descriptions here are written for this kit, not copied from PowerWorld's
> documentation.** They say what a command is *for* in the context of these workflows.
> For argument order, optional parameters, and filter syntax, consult Simulator's
> *Auxiliary File Format* manual — it ships with the program under Help, and it is the
> authority. Where this page and the manual disagree, the manual is right.

### How a script action is invoked

```python
pw.esa.RunScriptCommand('SolvePowerFlow(RECTNEWT)')
pw.esa.RunScriptCommand('SaveCase("C:\\out\\case.pwb", PWB, YES)')
```

Two rules that cause most first-attempt failures, both documented at
[save-powerworld-case](../methods/save-powerworld-case.md) and [new-device-contingency-aux](../methods/new-device-contingency-aux.md):

- File paths must be **absolute**. A relative path resolves against Simulator's current
  working directory, which is not your script's.
- `LoadAux` **merges** into the open case rather than replacing it. Loading the same aux
  twice duplicates its objects.

---

### Opening, saving, and case lifecycle

| Action | What it is for |
|---|---|
| `OpenCase` | Open a `.pwb` from disk, replacing whatever is loaded |
| `NewCase` | Start from an empty case |
| `AppendCase` | Merge a second case into the open one |
| `SaveCase` | Write the case to disk. **Use this, not the COM `SaveCase`** — see [save-powerworld-case](../methods/save-powerworld-case.md) |
| `EnterMode` | Switch between `RUN` and `EDIT`. Many data writes are rejected outside `EDIT` |
| `Scale` | Scale load, generation, or injection by a factor or to a target total |
| `Equivalence` | Reduce the case to an equivalent of the retained subsystem |
| `DeleteExternalSystem` | Drop everything outside the retained area/zone selection |
| `SaveExternalSystem` | Write the external subsystem out separately |
| `LoadEMS` | Read an EMS-format snapshot |
| `RenumberBuses` | Renumber buses en masse — changes key fields, so re-read any DataFrame you held |
| `RenumberAreas`, `RenumberZones`, `RenumberSubs` | Same, for those container types |
| `RenumberCase` | Apply a renumbering scheme across the whole case |
| `Renumber3WXFormerStarBuses` | Renumber the hidden star buses inside three-winding transformers |
| `CaseDescriptionSet`, `CaseDescriptionClear` | Set or clear the case's description text |

### Reading and writing data

| Action | What it is for |
|---|---|
| `SetData` | Write field values on existing objects. **Requires the entire key-field row** or it errors — see [powerworld-limitset-setdata](../methods/powerworld-limitset-setdata.md) |
| `CreateData` | Create new objects (buses, branches, loads, generators) — see [adding-devices-esapp](../methods/adding-devices-esapp.md) |
| `Delete` | Delete objects of a type matching a filter |
| `DeleteDevice` | Delete one specific device |
| `DeleteIncludingContents` | Delete a container and everything inside it |
| `LoadAux` | Read an `.aux` file into the case. Absolute path; **merges** |
| `LoadAuxDirectory` | Load every aux in a directory |
| `LoadCSV`, `LoadData`, `ImportData` | Bulk-import records from CSV or another data source |
| `LoadScript` | Run a named `SCRIPT` block from an aux file |
| `SaveData` | Export a table of objects and chosen fields to file |
| `SaveDataWithExtra` | Same, with additional computed columns |
| `SaveDataUsingBuiltInAUXFormat` | Export as aux using Simulator's own field layout |
| `SaveDataUsingExportFormat` | Export using a named custom format |
| `SaveDataEPC` | Export in EPC format |
| `SaveObjectFields` | Write out which fields exist for an object type |
| `SelectAll`, `UnSelectAll` | Set or clear the `Selected` flag, which many other actions filter on |
| `SendtoExcel` | Push a table to Excel. Note the lowercase `t` — the obvious spelling fails |
| `WriteLimitMonitoringSettings` | Dump the current limit-monitoring configuration |

### Solving power flow

| Action | What it is for |
|---|---|
| `SolvePowerFlow` | Solve. Takes the method: `RECTNEWT`, `POLARNEWT`, `GAUSSSEIDEL`, `FASTDEC`, `DC` |
| `ResetToFlatStart` | Reset voltages to 1.0 pu / 0 degrees before a hard solve |
| `EstimateVoltages` | Seed a starting voltage profile when flat start will not converge |
| `ZeroOutMismatches` | Force mismatches to zero — diagnostic, not a fix |
| `UpdateIslandsAndBusStatus` | Recompute island membership and energization after topology edits |
| `VoltageConditioning`, `ConditionVoltagePockets` | Repair local voltage anomalies that block convergence |
| `InitializeGenMvarLimits` | Reset generator reactive limits to their defined values |
| `GenForceLDC_RCC` | Force line-drop / reactive-current compensation behaviour |
| `SaveJacobian` | Write the Jacobian matrix to file |
| `SaveYbusInMatlabFormat` | Write Ybus in MATLAB format |
| `StoreState`, `RestoreState`, `DeleteState` | Snapshot and roll back a solved state. Cheaper than reloading the case between scenarios |
| `ClearPowerFlowSolutionAidValues` | Clear stored solution aids |

**A DC solve always reports zero mismatch.** It cannot tell you that your generation
schedule is short — the slack bus absorbs it silently. Check the schedule against total
load directly. See [applying-a-dispatch-to-a-case](../methods/applying-a-dispatch-to-a-case.md).

### Contingency analysis

| Action | What it is for |
|---|---|
| `CTGSolveAll` | Solve every active contingency. The workhorse |
| `CTGSolve` | Solve one named contingency |
| `CTGApply` | Apply a contingency's actions to the case without solving |
| `CTGAutoInsert` | Generate a contingency set automatically from the case topology |
| `CTGPrimaryAutoInsert` | Auto-insert primary contingencies only |
| `CTGRestoreReference` | Return the case to its pre-contingency reference state |
| `CTGSetAsReference` | Mark the current state as the reference base |
| `CTGClearAllResults` | Clear stored results. **Do this first** — results persist stale inside the `.pwb`, see [reading-violationctg](../methods/reading-violationctg.md) |
| `CTGProduceReport` | Write a formatted violation report |
| `CTGSaveViolationMatrices` | Export the violation matrices |
| `CTGWriteResultsAndOptions` | Write results plus the option set that produced them |
| `CTGWriteAuxUsingOptions` | Emit the contingency definitions as an aux file |
| `CTGSort` | Sort the contingency list |
| `CTGCloneOne`, `CTGCloneMany` | Duplicate contingency definitions |
| `CTGDeleteWithIdenticalActions`, `CTGSkipWithIdenticalActions` | Remove or skip duplicates by action set |
| `CTGConvertAllToDeviceCTG`, `CTGConvertToPrimaryCTG` | Convert between contingency representations |
| `CTGCreateStuckBreakerCTGs`, `CTGCreateExpandedBreakerCTGs` | Build breaker-failure contingencies |
| `CTGCreateContingentInterfaces` | Create interfaces defined by contingency outcomes |
| `CTGRelinkUnlinkedElements` | Re-bind contingency elements whose keys stopped resolving |
| `CTGJoinActiveCTGs` | Combine active contingencies into one |
| `CTGComboSolveAll`, `CTGComboDeleteAllResults` | Solve or clear combination contingencies |
| `CTGCalculateOTDF` | Outage transfer distribution factors |
| `CTGCompareTwoListsofContingencyResults` | Diff two result sets |
| `CTGProcessRemedialActionsAndDependencies` | Evaluate remedial action schemes |
| `CTGVerifyIteratedLinearActions` | Validate iterated linear contingency actions |
| `CTGReadFilePTI`, `CTGReadFilePSLF`, `CTGWriteFilePTI` | Exchange contingency sets with PSS/E and PSLF |
| `CTGWriteAllOptions` | Dump every contingency analysis option |
| `DoCTGAction` | Execute a single contingency action directly |

Building a contingency set for a chosen device list is its own procedure with several
silent failure modes (`ElementType=GEN` is ignored; the action string must be quoted;
labels get whitespace-trimmed on load) — see [new-device-contingency-aux](../methods/new-device-contingency-aux.md).

### Time step simulation and weather

| Action | What it is for |
|---|---|
| `TimeStepLoadPWW` | Load a `.pww` weather file for the simulation |
| `TimeStepLoadPWWRange` | Load a time range from a PWW |
| `TimeStepLoadPWWRangeLatLon` | Load a time range cropped to a lat/lon box — the usual entry point |
| `TimeStepAppendPWW`, `TimeStepAppendPWWRange`, `TimeStepAppendPWWRangeLatLon` | Append further weather to what is already loaded |
| `TimeStepLoadTSB`, `TimeStepLoadB3D` | Load time-series data in TSB or B3D format |
| `TimeStepDoRun` | Run the full time-step simulation |
| `TimeStepDoSinglePoint` | Solve one time point only — use this to debug setup before a long run |
| `TimeStepClearResults`, `TimeStepDeleteAll` | Clear results, or clear the whole time-step definition |
| `WeatherPWWSetDirectory` | Point Simulator at the directory holding PWW files |
| `WeatherPWWLoadForDateTimeUTC` | Load weather for a specific UTC timestamp |
| `WeatherPWWFileCombine2` | Merge two PWW files |
| `WeatherPWWFileGeoReduce` | Crop a PWW geographically — do this before loading, not after |
| `WeatherPWWFileAllMeasValid` | Check that all measurements in a PWW are valid |
| `TemperatureLimitsBranchUpdate` | Update branch thermal limits from temperature — the dynamic line rating hook |
| `WeatherLimitsGenUpdate` | Update generator limits from weather |
| `WeatherPFWModelsSetInputs` | Set inputs on PFW renewable models |
| `WeatherPFWModelsSetInputsAndApply` | Set and apply them in one step |
| `WeatherPFWModelsRestoreDesignValues` | Restore PFW models to design values |

`PWW` (PowerWorld Weather data) and `PFW` (the renewable output model) are different
things with confusingly similar names. See [pww-data](../concepts/pww-data.md).

### Modifying case objects

| Action | What it is for |
|---|---|
| `ChangeSystemMVABase` | Change the system base. Re-derives per-unit quantities — see [per-unit-basis-discipline](../concepts/per-unit-basis-discipline.md) |
| `CalculateRXBGFromLengthConfigCondType` | Derive branch R/X/B/G from length, configuration, and conductor type |
| `CreateLineDeriveExisting` | Create a line by deriving parameters from an existing one |
| `TapTransmissionLine` | Tap a line to insert a new bus |
| `SplitBus`, `MergeBuses` | Split one bus into two, or merge two into one |
| `MergeLineTerminals`, `MergeMSLineSections` | Merge line terminals or multi-section line segments |
| `ClearSmallIslands` | Remove islands below a size threshold |
| `RotateBusAnglesInIsland` | Rotate all angles in an island to a new reference |
| `SetScheduledVoltageForABus` | Set a bus's scheduled voltage setpoint |
| `SetParticipationFactors` | Set generator participation factors for AGC-style dispatch |
| `SetGenPMaxFromReactiveCapabilityCurve` | Derive generator MW max from its capability curve |
| `BranchMVALimitReorder` | Reorder branch MVA limit sets |
| `InjectionGroupCreate`, `InjectionGroupsAutoInsert` | Create injection groups by hand or automatically |
| `InjectionGroupRemoveDuplicates`, `RenameInjectionGroup` | Maintain injection groups |
| `InterfaceCreate`, `InterfacesAutoInsert` | Create interfaces by hand or automatically |
| `InterfaceAddElementsFromContingency` | Build an interface from a contingency's elements |
| `InterfaceFlatten`, `InterfaceFlattenFilter` | Flatten nested interface definitions |
| `InterfaceRemoveDuplicates`, `InterfaceModifyIsolatedElements` | Maintain interfaces |
| `SetInterfaceLimitToMonitoredElementLimitSum` | Set an interface limit from the sum of its elements' limits |
| `DirectionsAutoInsert`, `DirectionsAutoInsertReference` | Auto-create transfer directions |
| `AutoInsertTieLineTransactions` | Auto-create tie-line transactions |
| `SuperAreaAddAreas`, `SuperAreaRemoveAreas` | Manage super-area membership |
| `Remove3WXformerContainer` | Remove a three-winding transformer container |
| `ReassignIDs` | Reassign object IDs |
| `Move` | Move an object to a different container |

Reclassifying a line as a transformer is not done here — `BranchDeviceType` is derived,
so you set `LineXFMR` instead. See [converting-lines-to-transformers](../methods/converting-lines-to-transformers.md).

### Sensitivities

| Action | What it is for |
|---|---|
| `CalculatePTDF` | Power transfer distribution factors for one direction — see [lodf](../concepts/lodf.md) |
| `CalculatePTDFMultipleDirections` | PTDFs for several directions at once |
| `CalculateLODF` | Line outage distribution factors for one outage |
| `CalculateLODFMatrix` | The full LODF matrix |
| `CalculateLODFAdvanced` | LODFs with extended options |
| `CalculateLODFScreening` | LODF-based screening pass — the cheap first cut in critical branch screening |
| `CalculateShiftFactors` | Shift factors for a transfer |
| `CalculateShiftFactorsMultipleElement` | Shift factors across several elements |
| `CalculateFlowSense` | Sensitivity of a flow to injections |
| `CalculateVoltSense`, `CalculateVoltSelfSense` | Sensitivity of voltage to injections |
| `CalculateVoltToTransferSense` | Sensitivity of voltage to a transfer |
| `CalculateLossSense` | Sensitivity of losses to injections |
| `CalculateTapSense` | Sensitivity to transformer tap position |
| `SetSensitivitiesAtOutOfServiceToClosest` | Fill sensitivities at out-of-service elements from the nearest in-service one |
| `LineLoadingReplicatorCalculate`, `LineLoadingReplicatorImplement` | Compute then apply a loading pattern that reproduces target flows |

### Optimal power flow

| Action | What it is for |
|---|---|
| `SolvePrimalLP` | Solve the LP OPF |
| `InitializePrimalLP` | Initialize before solving |
| `SolveSinglePrimalLPOuterLoop` | Run one outer-loop iteration — useful for diagnosing non-convergence |
| `SolveFullSCOPF` | Solve the security-constrained OPF |
| `OPFWriteResultsAndOptions` | Write OPF results and the options used |

### PV and QV analysis

| Action | What it is for |
|---|---|
| `PVSetSourceAndSink` | Define the transfer's source and sink before running |
| `PVRun` | Run the PV (nose curve) study |
| `PVStartOver`, `PVClear`, `PVDestroy` | Restart or tear down a PV study |
| `PVWriteResultsAndOptions`, `PVDataWriteOptionsAndResults` | Write PV results |
| `PVWriteInadequateVoltages` | Report buses whose voltage is inadequate along the curve |
| `PVQVTrackSingleBusPerSuperBus` | Track one representative bus per super bus |
| `QVRun` | Run the QV study |
| `QVSelectSingleBusPerSuperBus` | Select one bus per super bus for QV |
| `QVWriteCurves` | Write the QV curves |
| `QVWriteResultsAndOptions`, `QVDataWriteOptionsAndResults` | Write QV results |
| `QVDeleteAllResults` | Clear QV results |
| `RefineModel` | Refine the model between study passes |

### Transient stability

| Action | What it is for |
|---|---|
| `TSInitialize` | Initialize dynamics from the solved power flow |
| `TSSolve` | Run one transient stability contingency |
| `TSSolveAll` | Run all of them |
| `TSRunUntilSpecifiedTime` | Advance the run to a given time, then stop — manual stepping |
| `TSGetResults` | Retrieve results into memory |
| `TSGetVCurveData` | Retrieve V-curve data |
| `TSCalculateCriticalClearTime` | Compute critical clearing time |
| `TSCalculateSMIBEigenValues` | Single-machine-infinite-bus eigenvalues |
| `TSValidate`, `TSAutoCorrect` | Validate dynamic models, and auto-correct what can be fixed |
| `TSClearAllModels`, `TSClearModelsforObjects` | Remove dynamic models |
| `TSClearResultsFromRAM` | Free result memory between runs |
| `TSResultStorageSetAll` | Choose which quantities are stored |
| `TSLoadPTI`, `TSLoadGE`, `TSLoadBPA`, `TSLoadRDB` | Import dynamic models from other formats |
| `TSSavePTI`, `TSSaveGE`, `TSSaveBPA` | Export dynamic models |
| `TSSaveDynamicModels`, `TSWriteModels` | Write the model set out |
| `TSSaveTwoBusEquivalent` | Save a two-bus equivalent |
| `TSTransferStateToPowerFlow` | Push the dynamic state back into the power flow case |
| `TSAutoInsertDistRelay`, `TSAutoInsertZPOTT` | Auto-insert distance and POTT relay models |
| `TSAutoSavePlots`, `TSPlotSeriesAdd` | Manage transient plots |
| `TSRunResultAnalyzer` | Run the result analyzer |
| `TSJoinActiveCTGs` | Join active contingencies for TS |
| `TSDisableMachineModelNonZeroDerivative` | Disable machine models with non-zero initial derivatives |
| `TSSetSelectedForTransientReferences` | Set the selected flag for transient reference objects |
| `TSWriteOptions` | Dump TS options |

### Geomagnetically induced current

| Action | What it is for |
|---|---|
| `GICCalculate` | Run the GIC calculation for a uniform field — see [gic](../concepts/gic.md) |
| `GICClear` | Clear GIC results |
| `GICLoad3DEfield` | Load a 3-D electric field |
| `GICTimeVaryingCalculate` | Run GIC over a time-varying field |
| `GICTimeVaryingEFieldCalculate` | Compute the time-varying E-field itself |
| `GICSetupTimeVaryingSeries` | Set up the time series |
| `GICTimeVaryingAddTime` | Add a time point |
| `GICTimeVaryingDeleteAllTimes`, `GICTimeVaryingElectricFieldsDeleteAllTimes` | Clear time points or fields |
| `GICShiftOrStretchInputPoints` | Shift or stretch the input series in time |
| `GICSaveGMatrix` | Save the G matrix |
| `GICReadFilePTI`, `GICReadFilePSLF`, `GICWriteFilePTI`, `GICWriteFilePSLF` | Exchange GIC data with PSS/E and PSLF |
| `GICWriteOptions` | Dump GIC options |

### Case comparison

| Action | What it is for |
|---|---|
| `DiffCaseSetAsBase` | Mark the open case as the comparison base |
| `DiffCaseMode` | Turn difference mode on or off |
| `DiffCaseKeyType` | Choose how objects are matched between cases |
| `DiffCaseRefresh` | Recompute the comparison |
| `DiffCaseShowPresentAndBase` | Show present and base values side by side |
| `DiffCaseClearBase` | Clear the base case |
| `DiffCaseWriteCompleteModel` | Write the full differenced model |
| `DiffCaseWriteNewEPC`, `DiffCaseWriteRemovedEPC`, `DiffCaseWriteBothEPC` | Write added, removed, or both as EPC |

### Program and file housekeeping

| Action | What it is for |
|---|---|
| `SetCurrentDirectory` | Set Simulator's working directory. Prefer absolute paths over relying on this |
| `CopyFile`, `DeleteFile` | Copy or delete a file from inside a script |
| `WriteTextToFile` | Write arbitrary text to a file |
| `LogAdd`, `LogAddDateTime`, `LogClear`, `LogSave`, `LogShow` | Message-log control — `LogSave` is the cheapest way to capture what a long script did |
| `StopAuxFile` | Treat the rest of the aux file as a comment |
| `ExitProgram` | Exit Simulator immediately, without prompting |

### What this page leaves out

Simulator defines roughly 370 SCRIPT actions. Omitted here as outside this kit's scope:
oneline and user-interface actions, fault analysis, ATC, integrated topology processing,
regions, scheduled actions, distributed computing, the trainer, and customer-specific
actions. If you need one of those, the *Auxiliary File Format* manual lists them by the
same category names used above.


---

# ==== esapp-package-backend.md ====

---
type: reference
domain: tooling
aliases: [esapp-backend, esapp-internals]
tags: [esapp, powerworld, simauto, internals, backend, reference]
---

# ESA++ (esapp) — Package Backend / Internals Reference

## Abstract

Internals reference for the esapp package project, covering bracket-interface mechanics (`Indexable.__getitem__`/`__setitem__`), SAW mixin composition, the component-generation pipeline, GObject schema model, embedded utility apps (`Network`, `GIC`, `BusCat`), descriptors, and the exception hierarchy. This is the heavy/deep layer — read it in full only when writing or regenerating code for esapp package; for the gist, use the project page.

## Connections

- **Up:** esapp package (the project) + [Home](../index.md)
- **Across:** [esapp](../concepts/esapp.md) (API-usage map for callers), [powerworld-simauto](../concepts/powerworld-simauto.md), aux script catalog (raw SCRIPT-command name index)

## Content

**Scope:** how `esapp` works *inside* and how to *extend* it — bracket-interface
mechanics, the SAW mixin assembly, the component-generation pipeline, the GObject
schema model, embedded utility apps, descriptors, and the exception hierarchy. This
is the INTERNALS companion to the API-usage map in [esapp](../concepts/esapp.md); it does not re-document
user-facing call recipes. Project status/tracker lives at esapp package; hub is
[Home](../index.md).

All file:line citations are against the real source under `C:\path\to\esapp`.

---

## 1. Object graph (who owns whom)

```
PowerWorld(Indexable)            workbench.py:22   — user entry point
 ├── .esa : SAW                  set in Indexable.open() indexable.py:50
 │    └── SAW(SAWBase, *mixins)  saw/saw.py:28      — ~20 mixins composed
 ├── .network : Network(self)    workbench.py:36    — utils/network.py
 ├── .gic     : GIC(self)        workbench.py:37    — utils/gic.py
 └── .buscat  : BusCat(self)     workbench.py:38    — utils/buscat.py
```

`PowerWorld` **subclasses** `Indexable` (so `pw[...]` works directly), and **holds**
a `SAW` instance as `self.esa`. The embedded apps each keep a back-reference to the
`PowerWorld` instance (`self._pw`) and delegate all data access through it — they
never open their own COM connection.

`PowerWorld.__init__` (workbench.py:26–45) instantiates the three apps *first*, then
either opens the case (`self.open()`, inherited from `Indexable`) or leaves
`self.esa = None`. `Indexable.open()` (indexable.py:25–50) absolutizes/validates the
path and constructs `SAW(self.fname, CreateIfNotFound=True, early_bind=True)` — note
**`CreateIfNotFound=True` is hard-wired here**, which is what makes the bracket-write
create path possible (see §3).

---

## 2. `Indexable` — bracket read/write mechanics

File: `esapp/indexable.py`. `Indexable` is a mixin-style base with two declared
attributes (`esa: SAW`, `fname: str`) and the bracket protocol. Both `PowerWorld`
and `SAW` are described as implementing indexable access, but the read/write logic
lives here and is backed by SAW data methods.

### 2.1 `__getitem__` (read) — indexable.py:52–113

Index forms and how they resolve:

| Index | `requested_fields` | Fields fetched |
|---|---|---|
| `pw[Bus]` | `None` | `set(gtype.keys())` only |
| `pw[Bus, :]` | `slice(None)` | keys ∪ `gtype.fields()` (all) |
| `pw[Bus, "BusPUVolt"]` | str | keys ∪ {field} |
| `pw[Bus, ["a","b"]]` | list | keys ∪ {a,b} |
| `pw[Bus, Bus.PUVolt]` | a `GObject` member | uses `field.value[1]` (the PW field string) |

Mechanics (verbatim flow):
1. Unpack `index` into `(gtype, requested_fields)` (tuple) or `(gtype, None)`.
2. `fields_to_get = set(gtype.keys())` — **always starts from primary keys.**
3. A bare `GObject` member in the field list is resolved via `field.value[1]`
   (the field-name string carried in the enum value tuple — see §5).
4. A `slice` other than `[:]` raises `ValueError("Only the full slice [:] is
   supported...")`.
5. Returns `self.esa.GetParamsRectTyped(gtype.TYPE(), sorted(list(fields_to_get)))`.

So **every read is backed by `SAW.GetParamsRectTyped`** (data.py:324–362), which
calls COM `GetParamsRectTyped` with `pythoncom.VT_VARIANT` to preserve native typing,
and returns a `DataFrame(output, columns=ParamList)` or `None`. Fields are passed
**sorted**, so column order in the returned DataFrame is alphabetical, not request
order.

### 2.2 `__setitem__` (write) — indexable.py:115–173

Two dispatch cases:

- **Case 1 — bulk** `pw[GObject] = DataFrame`: `args` is a `type` subclassing
  `GObject` → `_bulk_update_from_df(args, value)`.
- **Case 2 — broadcast** `pw[GObject, field(s)] = value`: `args` is a 2-tuple →
  normalizes `fields` to a list and calls `_broadcast_update_to_fields(gtype, fields, value)`.
- Anything else → `TypeError`.

### 2.3 `_bulk_update_from_df` — indexable.py:175–253 (the create path)

This is the load-bearing method. Flow:

1. Reject non-DataFrame `value` with `TypeError`.
2. **Settable gate:** `non_settable = [c for c in df.columns if not gtype.is_settable(c)]`.
   If any column is read-only → `ValueError("Cannot set read-only field(s)...")`.
   `is_settable` = key ∪ secondary ∪ editable (see §5).
3. Fast path: `self.esa.ChangeParametersMultipleElementRect(gtype.TYPE(),
   df.columns.tolist(), df)` — one COM round-trip (data.py:88–121).
4. **Create fallback keyed off the exception type:** wrapped in
   `except PowerWorldPrerequisiteError as e:` and `if "not found" in str(e).lower():`
   - Compute `missing_keys = set(gtype.keys()) - set(df.columns)`. If any primary key
     is missing → `ValueError` (can't create/identify objects without full keys;
     secondary keys are *not* required).
   - Else fall back to `ChangeParametersMultipleElement(type, cols, values)` (the
     row-by-row variant, data.py:54–86), which **creates** objects when
     `CreateIfNotFound=True` **and** PowerWorld is in **EDIT mode**. A second
     `"not found"` `PowerWorldPrerequisiteError` from this call is **swallowed**
     (expected for freshly created rows); any other message re-raises.
   - Any non-`"not found"` `PowerWorldPrerequisiteError` re-raises immediately.

This is the concrete answer to "where bracket-write keys off `PowerWorldPrerequisiteError`":
indexable.py:233–253. The classification "not found" → `PowerWorldPrerequisiteError`
is decided in `PowerWorldError.from_message` (see §6); the bracket layer then string-matches
`"not found"` again to distinguish the create case from other prerequisite failures.

> Prerequisites for the create path to actually create: `SAW(..., CreateIfNotFound=True)`
> (already forced by `Indexable.open()`, indexable.py:50) **and** `pw.edit_mode()`
> (`esa.EnterMode('EDIT')`, workbench.py:427–429) before assignment.

### 2.4 `_broadcast_update_to_fields` — indexable.py:255–316

For `pw[GObject, fields] = value`. Same settable gate first. Then two sub-paths:

- **Keyless object** (`not gtype.keys()`, e.g. `Sim_Solution_Options`): builds the
  change DataFrame directly from `value` without reading PowerWorld. Single field →
  `{field: [value]}`; multiple fields require `value` to be a list/tuple of equal
  length (else `ValueError`).
- **Keyed object:** reads existing primary keys via `self[gtype, keys]` (a recursive
  `__getitem__`), returns early if empty (nothing to update — **never creates** on
  this path), then assigns `change_df[field] = value` (pandas broadcasts a scalar or
  aligns a list/array). Single field uses the bare name to avoid pandas multi-column
  treatment.

Always finishes with `ChangeParametersMultipleElementRect`. So broadcast writes are
update-only; only the Case-1 DataFrame path can create.

`fexcept` (indexable.py:11) is a small lambda turning `'Three…'` type names into
`'3…'` (e.g. `ThreeWindingTransformer` → `3WindingTransformer`) — Python-identifier
vs PowerWorld-string reconciliation, mirrored in the generator (§4).

---

## 3. SAW mixin composition — `esapp/saw/saw.py`

`SAW` is an **empty class body** (`pass`) whose entire behavior comes from its MRO.
saw.py:28–55:

```python
class SAW(
    SAWBase,           # core COM: __init__, _com_call, RunScriptCommand, exec_aux...
    CaseActionsMixin, DataMixin, ContingencyMixin, GeneralMixin, MatrixMixin,
    ModifyMixin, PowerflowMixin, RegionsMixin, SensitivityMixin, ScheduledActionsMixin,
    TopologyMixin, TransientMixin, FaultMixin, ATCMixin, GICMixin, OPFMixin,
    PVMixin, QVMixin, TimeStepMixin, WeatherMixin,
):
    pass
```

21 bases total (`SAWBase` + 20 functional mixins). Each mixin lives in its own
`esapp/saw/<area>.py` and is imported at the top of saw.py:5–25.

### How a mixin works (the shared contract)

Mixins do **not** declare `__init__` or hold state — they rely on `SAWBase`
providing:
- `self._com_call(func, *args)` — the single COM gateway (base.py:331–401). Wraps
  every SimAuto call, unwraps the `(Error, Result)` tuple, maps RPC failures to
  `COMError`, and raises `PowerWorldError.from_message(...)` when SimAuto returns an
  error string. Returns `output[1]` (single result) or `output[1:]`.
- `self._run_script(command, *args)` — builds a script statement `"Cmd(a, b);"`
  (strips trailing `None`s, stringifies args) and routes through `RunScriptCommand`
  (base.py:202–238). This is how every *script-command* mixin method works.
- `self.log`, `self.decimal_delimiter`, `self._object_fields` (field-list cache),
  `self.pw_order`, etc.

Two concrete patterns to copy when extending:

- **Script-command method** (most analysis verbs) — `PowerflowMixin.SolvePowerFlow`
  (powerflow.py:10–40): normalize an enum/str arg, then
  `return self._run_script("SolvePowerFlow", method)`.
  `TimeStepMixin` (timestep.py) is the cleanest example: nearly every method is a
  one-line `self._run_script("TimeStep…", …)` with filename/time args quoted.
- **Data method** (typed COM data calls) — `DataMixin` (data.py): convert lists/DFs
  to COM variants (`convert_list_to_variant`, `convert_df_to_variant`) and call
  `self._com_call("GetParamsRectTyped", …)`.

### How to add a mixin (extension recipe)

1. Create `esapp/saw/<feature>.py` with `class FeatureMixin:` and methods that use
   `self._run_script(...)` (for script commands) or `self._com_call(...)` (for direct
   SimAuto functions). No `__init__`, no state of your own.
2. Import it in `saw/saw.py` (top, alongside the others) and add it to the `SAW(...)`
   base list. **MRO order matters** only if two mixins define the same method name —
   keep `SAWBase` first and avoid name collisions.
3. If the feature needs new type-safe constants, add them to `saw/_enums.py` and
   export via `saw/__init__.py`'s `__all__`.

No registry/metaclass — composition is purely the explicit base-class tuple, so the
only "wiring" is the import + the line in the tuple.

---

## 4. Component generation pipeline — `esapp/components/`

`grid.py` (~13 MB) and `ts_fields.py` are **auto-generated** from the `PWRaw` TSV
schema export. Do **not** hand-edit them (the file banner says so, and the project
conventions in esapp package reiterate it). Regenerate with:

```bash
cd esapp/components && python generate_components.py   # reads ./PWRaw
```

`generate_components.py:490–507` (the `__main__`): builds a `ComponentGenerator('PWRaw')`,
calls `.parse()`, then `.generate_components('grid.py')` and `.generate_ts_fields('ts_fields.py')`.

### Pipeline stages (`ComponentGenerator`)

1. **Row iteration** — `_iter_raw_rows` (337–341) skips the header and joins wrapped
   quoted continuation lines via `_join_continuation_lines` (343–362). A line is a
   field row if it starts with a tab (`_is_field_row`, 369–370); an object header is
   detected by `_is_object_header` (372–380) using the subdata/maintainer columns.
2. **Parse** — `_parse_components` (150–171) walks rows, creating an
   `ObjectTypeDefinition` per header (skipping `EXCLUDE_OBJECTS`, 79–92) and appending
   `FieldDefinition`s (skipping `EXCLUDE_FIELDS` and any var name containing `/`).
   `_parse_field_definition` (382–397) reads columns: var name (col 3), key symbol
   (col 2), concise name (4), data type (5), description (6), enterable (8).
3. **Key-symbol → role** — `_parse_key_symbol` (446–459) maps PWRaw symbols to
   `FieldRole` flags: `*`→PRIMARY_KEY, `*1*/*2*/*3*`→COMPOSITE_KEY_n, `*2B*`→SECONDARY_ID,
   `*4B*`→CIRCUIT_ID, `*A*`→ALTERNATE_KEY, `**`→BASE_VALUE, `<`→STANDARD_FIELD.
   `FieldDefinition.is_primary` (39–45) treats PRIMARY/COMPOSITE_n/SECONDARY_ID/CIRCUIT_ID
   as primary; `is_secondary` (47–51) = ALTERNATE_KEY|BASE_VALUE.
4. **Name sanitizing** — `_sanitize_for_python` (420–426): `:`→`__`, space→`___`,
   leading digit handling (`3…`→`Three…`, else prefix `_`). `_fix_pw_string` (428–436)
   is the inverse used to recover the PowerWorld field string. (This is the same
   `Three…`↔`3…` rule as `fexcept` in indexable.py.)
5. **Emit GObject classes** — `generate_components` (233–262): writes the preamble
   `from .gobject import *`, then per object a `class <Name>(GObject):` with members
   `PyName = ("PWFieldString", <dtype>, <FieldPriority flags>)` plus a docstring, and
   finally `ObjectString = '<full obj name>'`. Fields are sorted by `_get_sort_key`
   (468–477: composite/primary keys first, then alternate, secondary, base value,
   then standard). Priority flags built by `_build_field_priority_flags` (479–487):
   PRIMARY → `FieldPriority.PRIMARY`, secondary → `FieldPriority.SECONDARY`, else
   `FieldPriority.OPTIONAL`; `+ REQUIRED` if base value; `+ EDITABLE` if enterable.

Real generated output (`grid.py:6036–6048`):
```python
class Bus(GObject):
	BusNum = ("BusNum", int, FieldPriority.PRIMARY)
	"""Number"""
	BusName_NomVolt = ("BusName_NomVolt", str, FieldPriority.SECONDARY)
	"""Name_Nominal kV"""
	AreaNum = ("AreaNum", int, FieldPriority.SECONDARY | FieldPriority.REQUIRED | FieldPriority.EDITABLE)
	...
```

6. **TS fields** — `_extract_ts_fields` (173–231) matches var-name prefixes from
   `TS_OBJECT_MAPPING` (128–138: `TSBus`→`Bus`, `TSGen`→`Gen`, `TSACLine`→`Branch`,
   …), strips `:N` index suffixes, dedups per object type, and emits a frozen
   `TSField` dataclass per attribute under nested `class <ObjType>:` inside one `TS`
   class (generate_ts_fields, 264–333). `TSField.__getitem__` (300–302) lets you write
   `TS.Bus.Input[1]` → `TSField("TSBusInput:1")`.

`MANUAL_FIELDS` (101–124) injects fields PWRaw defines poorly (e.g. `Dbd:3` on
`PlantController_REPCA1`), merged in by `_fields_with_manual_fields` (399–411) without
clobbering existing names.

### `components/__init__.py`
Re-exports: `GObject` from `gobject`, `from .grid import *` (all object classes), and
`TS, TSField` from `ts_fields`.

---

## 5. `GObject` schema model — `esapp/components/gobject.py`

`GObject(Enum)` builds a class-level schema at *definition time* via a custom
`__new__` (gobject.py:59–106). Each subclass member is either:
- the **type tag** — a single-arg member (`ObjectString = 'Bus'`) → sets `cls._TYPE`
  and stores an int `_value_`; or
- a **field** — a `(name, dtype, priority)` triple → `_value_` becomes the 4-tuple
  `(int, field_name_str, dtype, priority)`, and the field name is appended to the
  per-class lists `_FIELDS`, plus `_KEYS`/`_SECONDARY`/`_EDITABLE` depending on its
  `FieldPriority` flags (95–104).

This is why `__getitem__` can read `field.value[1]` for a member (indexable.py:102) —
index 1 of the tuple is the PowerWorld field-name string.

`FieldPriority(Flag)` (gobject.py:16–27): `PRIMARY`, `SECONDARY`, `REQUIRED`,
`OPTIONAL`, `EDITABLE` — combinable.

### Classmethod schema accessors (the public extension surface)

| Classmethod | Returns | Source |
|---|---|---|
| `TYPE()` | PW object-type string (e.g. `"Bus"`), or `'NO_OBJECT_NAME'` | 149–151 |
| `keys()` | primary-key field names (`_KEYS`) | 122–124 |
| `fields()` | all field names (`_FIELDS`) | 126–128 |
| `secondary()` | secondary-key field names (`_SECONDARY`) | 130–133 |
| `editable()` | editable field names (`_EDITABLE`) | 135–137 |
| `identifiers()` | `set(keys) ∪ set(secondary)` | 139–142 |
| `settable()` | `identifiers() ∪ set(editable)` | 144–147 |
| `is_editable(f)` | bool — in `_EDITABLE` | 153–156 |
| `is_settable(f)` | bool — in `settable()` | 158–161 |

`is_settable` is the exact gate used by both bracket-write paths (§2.3, §2.4). `keys()`
drives the always-included primary keys in reads and the "missing keys → ValueError"
create check.

`__str__` returns the PW field string for field members (so a member stringifies to
its PowerWorld name); `__repr__` shows the type or field for debugging (108–120).

---

## 6. Exception hierarchy — `esapp/saw/_exceptions.py`

```
Exception
└── Error                         (base for everything esapp; _exceptions.py:8)
    ├── PowerWorldError           (SimAuto returned an error string; 19)
    │   ├── SimAutoFeatureError           ("cannot be retrieved through simauto"; 77)
    │   ├── PowerWorldPrerequisiteError   (setup/data missing — KEY for writes; 92)
    │   ├── PowerWorldAddonError          ("not registered"; 108)
    │   └── CommandNotRespectedError      (silent no-op; 135)
    ├── COMError                  (COM/RPC layer failure; 121)
    ├── GridObjDNE                (165)
    ├── FieldDataException / AuxParseException / ContainerDeletedException
    ├── PowerFlowException        (180)
    │   ├── BifurcationException / DivergenceException / GeneratorLimitException
    └── GICException              (204)
```

### The classification factory — `PowerWorldError.from_message` (50–74)

`SAWBase._com_call` raises `PowerWorldError.from_message(output[0])` when SimAuto
returns a non-empty, non-"No data" error string (base.py:386–387). The factory
lower-cases the message and returns a **subclass**:
- `"cannot be retrieved through simauto"` → `SimAutoFeatureError`.
- Any of `"no active"`, **`"not found"`**, `"could not be found"`, `"requires setup"`,
  `"is not online"`, `"at least one"`, `"no directions set"`, `"out-of-range"`,
  `"no available participation points"` → `PowerWorldPrerequisiteError`.
- `"not registered"` → `PowerWorldAddonError`.
- else → base `PowerWorldError`.

This is the linchpin for bracket-write: a SimAuto "object not found" comes back as
`PowerWorldPrerequisiteError`, which `_bulk_update_from_df` catches and re-string-matches
on `"not found"` to trigger the create fallback (§2.3). So the create path depends on
**both** the factory's substring list *and* the bracket layer's own `"not found"` check.

`COMError` is different in kind — it wraps a thrown COM exception (RPC server crash /
invalid function), raised in `_com_call`'s `except` (base.py:368–376), not via the
factory.

`__init__` (38–48) splits the message on the first `:` into `source` / `message`,
keeping `raw_message`.

The exception classes consolidated from the old `utils/exceptions.py` (`GridObjDNE`,
`PowerFlowException` & subtypes, `GICException`, etc.) now live in this same file and
are re-exported through `saw/__init__.py` and the top-level `esapp/__init__.py`.

---

## 7. Descriptors — `esapp/_descriptors.py`

Two descriptor classes give Pythonic option access without boilerplate, both built on
the bracket interface:

- **`SolverOption(key, is_bool=True)`** (_descriptors.py:12–34): maps a `PowerWorld`
  attribute to a `Sim_Solution_Options` field. `__get__` does
  `obj[Sim_Solution_Options, key][key].iloc[0]` and coerces to bool via `== YesNo.YES`;
  `__set__` does `obj[Sim_Solution_Options, key] = YesNo.from_bool(value)` (or raw
  value if `is_bool=False`). The ~25 `pw.flat_start`, `pw.max_iterations`, etc. in
  workbench.py:50–93 are instances of this — they read/write through `__setitem__`'s
  keyless broadcast path (§2.4).
- **`GICOption(key, is_bool=True)`** (_descriptors.py:37–68): maps a `GIC` attribute to
  a `GIC_Options_Value` row. `__get__` reads `obj._pw[GIC_Options_Value, "ValueField"]`
  and filters by `VariableName == key`; `__set__` wraps the write in
  `EnterMode("EDIT")` … `SetData('GIC_Options_Value', ['VariableName','ValueField'],
  [key, value])` … `EnterMode("RUN")`. The `pf_include`, `calc_mode`, `efield_mag`, …
  attributes in gic.py:69–96 are instances.

To add a new solver/GIC flag: just declare one more class attribute
`my_opt = SolverOption('PWFieldName')` on `PowerWorld` (or `GICOption(...)` on `GIC`) —
no method needed.

---

## 8. Embedded utility apps — `esapp/utils/`

All three follow the same pattern: `__init__(self, pw=None)` stores `self._pw`, and
every method reaches data via `self._pw[GObject, fields]` or `self._pw.esa.<saw method>`.
They are stateless wrappers over the live case (plus some cached matrices).

- **`Network`** (network.py:62) — topology matrices. `busmap()` (Series BusNum→index),
  `incidence()` (signed branch×bus sparse, HVDC appended, cached in `self._A`),
  `laplacian(weights)` = `A.T @ diags(W) @ A`, plus electrical helpers `lengths`,
  `zmag`, `ybranch`, `yshunt`, `gamma`, `delay`. Pulls `Branch`/`Bus`/`Substation`/
  `DCTransmissionLine` via the bracket interface; `delay()` also calls
  `self._pw.esa.get_ybus()` directly (MatrixMixin). `PowerWorld.busmap/buscoords`
  delegate here (workbench.py:245–275).
- **`GIC`** (gic.py:34) — GIC engine integration. `configure()` sets the `GICOption`
  descriptors; `gmatrix()` forces `pf_include=True` then `self._pw.esa.get_gmatrix()`;
  `storm()` → `esa.GICCalculate(...)`; `model()` (gic.py:250–373) builds the full
  sparse incidence `A`, conductance Laplacian `G`, H-matrix and per-unit `zeta`
  entirely from `GICXFormer`/`Substation`/`Bus`/`Branch`/`Gen` bracket reads. Results
  exposed as read-only properties (`A`, `G`, `H`, `zeta`, `Px`, `eff`).
- **`BusCat`** (buscat.py) — parses the `BusCat` string field into typed bus
  classes/roles using `BusType`/`BusCtrl`/`Role` enums from `saw/_enums.py`; reads
  `Bus` via `self._pw`.

To add another embedded app: write `class Foo: def __init__(self, pw=None): self._pw = pw`
in `utils/`, then add `self.foo = Foo(self)` in `PowerWorld.__init__` (workbench.py:36–38).

---

## 9. Quick "where do I touch X" index

| Want to change… | Edit | Notes |
|---|---|---|
| How `pw[...]` reads/writes | `indexable.py` | backed by `GetParamsRectTyped` / `ChangeParametersMultipleElement[Rect]` |
| Add a new SAW capability | new `saw/<x>.py` mixin + line in `saw/saw.py` | use `_run_script` / `_com_call` |
| Object/field schema | regenerate via `generate_components.py` from `PWRaw` | **never** hand-edit `grid.py`/`ts_fields.py` |
| Key/editable classification | `gobject.py` flags + `_parse_key_symbol` in generator | drives `is_settable` gate |
| New error type | `saw/_exceptions.py` + `from_message` substring list | export in `saw/__init__.py` |
| New solver/GIC flag | one `SolverOption`/`GICOption` attr | `_descriptors.py` |
| New analysis app on `pw` | `utils/<x>.py` + `self.x = X(self)` in `__init__` | delegate via `self._pw` |

---

## See also
- API-usage map (how to *call* esapp): [esapp](../concepts/esapp.md)
- Project status/tracker: esapp package
- Underlying COM server: [powerworld-simauto](../concepts/powerworld-simauto.md)
- Hub: [Home](../index.md)


---

# ==== esapp-schema-reference.md ====

---
type: reference
domain: tooling
aliases: [esapp-schema, object-fields, simauto-commands, grid-py-reference]
tags: [esapp, schema, fields, simauto, commands, reference]
---

# Reference: esapp object-field schema + SimAuto command catalog

## Abstract

This is the field-schema + SimAuto-command lookup for **writing esapp code**: read
it when you need an object type's exact **key fields** (so a read-modify-write
round-trips) or the **command/method** for an operation. **Part A** documents the
`GObject` category model (keys / secondary / editable / identifiers / settable) plus
its runtime `@classmethod` accessors and the real per-type key/identifier table pulled
from `grid.py`. **Part B** catalogs the `SAW` mixins and the named SAW methods; the
full raw SCRIPT-command index lives in aux script catalog. Every field name and method below was read
out of `C:\path\to\esapp` source — cited `file:line`.

## Connections

- **Up:** esapp package · [Home](../index.md)
- **Across:** [esapp](../concepts/esapp.md) · [esapp-overview](../methods/esapp-overview.md) · [powerworld-simauto](../concepts/powerworld-simauto.md) · [esapp-package-backend](esapp-package-backend.md) · aux script catalog

## Content

> Source of truth: `C:\path\to\esapp`. Field names + flags were read
> from `components/gobject.py` and `components/grid.py`; methods from `saw/*.py`.
> `grid.py` is auto-generated (~197k lines, 1001 `GObject` classes) — regenerate via
> `components/generate_components.py`, never hand-edit.

---

## Part A — Object field schema

### A.1 The category model (`components/gobject.py`)

Each component is a `GObject` subclass (an `Enum`). Every field is declared as
`Member = ("PWFieldName", dtype, FieldPriority...)`. The `FieldPriority` `Flag`
(`gobject.py:16-27`) drives which category a field lands in:

| Flag | Meaning (`gobject.py:23-27`) |
|---|---|
| `PRIMARY` | Field is part of the **primary key** for the object |
| `SECONDARY` | Field is part of a **secondary key** (a secondary identifier) |
| `REQUIRED` | Required for data retrieval/update |
| `OPTIONAL` | Optional |
| `EDITABLE` | User-modifiable |

At class-construction time `GObject.__new__` (`gobject.py:59-106`) sorts every field
into class-level lists: `_FIELDS` (all), `_KEYS` (has `PRIMARY`), `_SECONDARY`
(has `SECONDARY`), `_EDITABLE` (has `EDITABLE`). Flags combine with `|`
(e.g. `SECONDARY | REQUIRED | EDITABLE`).

### A.2 Runtime accessors (call with `()` — they are `@classmethod`s)

From `gobject.py:122-161`. **They are methods, not properties — `Bus.keys()` not
`Bus.keys`.**

| Accessor | Returns | Source |
|---|---|---|
| `Type.TYPE()` | PowerWorld object-type string (e.g. `"Bus"`) | `gobject.py:149-151` |
| `Type.fields()` | `list` — every defined field name | `gobject.py:126-128` |
| `Type.keys()` | `list` — **primary** key fields only | `gobject.py:122-124` |
| `Type.secondary()` | `list` — secondary identifier fields | `gobject.py:130-133` |
| `Type.editable()` | `list` — editable (user-modifiable) fields | `gobject.py:135-137` |
| `Type.identifiers()` | `set` — **primary ∪ secondary** keys | `gobject.py:139-142` |
| `Type.settable()` | `set` — **identifiers ∪ editable** (everything writable) | `gobject.py:144-147` |
| `Type.is_editable(name)` | `bool` — is this field editable | `gobject.py:153-156` |
| `Type.is_settable(name)` | `bool` — is this field a key or editable | `gobject.py:158-161` |

```python
from esapp.components import Bus, Gen
Bus.TYPE()          # 'Bus'
Bus.keys()          # ['BusNum']
Gen.keys()          # ['BusNum', 'GenID']
Gen.identifiers()   # primary + secondary, e.g. {'BusNum','GenID','GenStatus','GenMWSetPoint', ...}
Gen.is_settable('GenMW')   # True  -> safe to push back
```

### A.3 The KEY-FIELD WRITE-BACK RULE (do not skip)

PowerWorld matches each DataFrame row back to a live object by its **primary key
field(s)**. If a row you write lacks those keys, PowerWorld cannot identify the object
and the change is a **silent no-op** (no error, no change).

- **Bracket path (preferred):** `pw[Gen, "GenMW"]` *automatically* includes the keys
  on read (`indexable.py:84-89` — reads always start with `gtype.keys()`), so a
  read-modify-write keeps them. A bulk write `pw[Gen] = df` **validates that all
  primary keys are present** and raises `ValueError` if any are missing
  (`indexable.py:235-241`). Every column must also pass `gtype.is_settable(...)`
  (`indexable.py:224-225`).
- **Raw `esa`/SAW path:** you must prepend the keys yourself — there is no auto-key on
  `GetParametersMultipleElement` / `ChangeParametersMultipleElementRect`. Build the
  field list as `list(Gen.keys()) + [<your fields>]` and keep the key columns in the
  DataFrame end-to-end.

**Rule of thumb: never strip key columns from a DataFrame you intend to push back.**

### A.4 Per-type key / identifier table (read from `grid.py`)

Keys/secondary verbatim from the `FieldPriority.PRIMARY` / `.SECONDARY` flags in
`grid.py`. `secondary` here lists the most useful identifiers (full list via
`Type.secondary()`); `#flds`/`#edit` are total field and editable-field counts.

| Object type | `TYPE()` | `keys()` (primary) | key secondary / identifiers | #flds | #edit | grid.py line | Description |
|---|---|---|---|---|---|---|---|
| **Bus** | `Bus` | `BusNum` | `BusName`, `BusNomVolt`, `AreaNum`, `ZoneNum`, `BusName_NomVolt` | 588 | 111 | `6036` | **UNVERIFIED:** (no prose definition found; key field is `BusNum` since a bus is uniquely identified by its number). |
| **Gen** | `Gen` | `BusNum`, `GenID` | `GenStatus`, `GenMWSetPoint`, `GenMVRMax/Min`, `GenMWMax/Min`, `GenVoltSet` | 607 | 222 | `61768` | **UNVERIFIED:** (BidCurve subdata = piecewise-linear cost curve; ReactiveCapability subdata = MW vs. Min/Max MVAR limits). |
| **Load** | `Load` | `BusNum`, `LoadID` | `LoadStatus`, `LoadSMW`, `LoadSMVR` | 287 | 118 | `97444` | **UNVERIFIED:** (BidCurve subdata = piecewise-linear benefit curve; costs must be increasing for loads). |
| **Branch** (line) | `Branch` | `BusNum`, `BusNum:1`, `LineCircuit` *(+`BusName_NomVolt:1`)* | `LineR`, `LineX`, `LineAMVA` (rating), `BusName_NomVolt` | 811 | 188 | `4298` | A network element (e.g. transmission line) connecting a from-bus and to-bus with a circuit ID; MW flow direction runs from-bus → to-bus. |
| **Transformer** | `Transformer` | `BusNum`, `BusNum:1`, `LineCircuit` *(+`BusName_NomVolt:1`)* | `LineXFType`, `XFTapMax/Min`, `XFStep`, `XFAuto`, `XFRegMax/Min` | 814 | 193 | `176297` | The `3WXFormer` type — a three-winding transformer modeled internally as a container of two-winding transformer branches joined at a common star bus. |
| **Shunt** (switched) | `Shunt` | `BusNum`, `ShuntID` | `SSStatus`, `SSNMVR`, `SSCMode` | 302 | 154 | `156986` | A switched shunt device (e.g. capacitor bank or reactor) at a bus that injects/absorbs Mvar in discrete steps. |
| **DCTransmissionLine** | `DCTransmissionLine` | `BusNum`, `BusNum:1`, `DCLID` *(+`BusName_NomVolt:1`)* | `DCLMode`, `DCLSetVolt`, `DCLR`, `DCLAlpha`, `DCLGamma` | 324 | 184 | `21018` | **UNVERIFIED:** (no prose found for the plain 2-terminal type; grouped with VSCDCLine/MSLine/3WXFormer/MTDC* as Edit-Mode-only topology objects). |
| **MultiSectionLine** | `MultiSectionLine` | `BusNum`, `BusNum:1`, `LineCircuit` *(+`BusName_NomVolt:1`)* | `BusInt`, `BusInt:1…` (section buses) | 149 | 48 | `127339` | A transmission line (MSLine) modeled as segments joined by intermediate dummy buses, running in order from the From Bus to the To Bus. |
| **Area** | `Area` | `AreaNum` | `AreaName` | 446 | 95 | `1693` | **UNVERIFIED:** (no prose definition found beyond an unrelated SelectByCriteriaSet reference). |
| **Zone** | `Zone` | `ZoneNum` | `ZoneName` | 390 | 57 | `192861` | **UNVERIFIED:** (no prose definition found beyond an unrelated SelectByCriteriaSet reference). |
| **Substation** | `Substation` | `SubNum` | `SubName` | 512 | 90 | `168780` | Groups the equipment/buses at a physical site to support full node-breaker topology modeling (vs. simpler bus-branch representation). |
| **SuperArea** | `SuperArea` | `SAName` | *(none flagged secondary)* | 198 | 32 | `169809` | A named grouping of Areas, each assigned an optional participation factor. |
| **Owner** | `Owner` | `OwnerNum` | `OwnerName` | 126 | 37 | `130894` | An entity holding ownership of buses, loads, generators, and branches; generator ownership is recorded as a percentage fraction. |
| **InjectionGroup** | `InjectionGroup` | `InjGrpName` | *(none flagged secondary)* | 174 | 65 | `87889` | A named collection of participation points (gens, loads, switched shunts, buses, or other injection groups), each with a participation factor, for an aggregate/distributed injection. |
| **Interface** | `Interface` | `FGName` | `IntNum`, `IntMonDir` | 149 | 43 | `88373` | A monitored aggregate power-flow quantity, summing (directional) flow/injection across branches, DC lines, MSLines, gens, loads, injection groups, areas, zones, or other interfaces. |
| **Nomogram** | `Nomogram` | `FGName` | *(none flagged secondary)* | 45 | 25 | `127898` | A safe-operating limit curve relating simultaneous flows on two interfaces, bounded by vertex breakpoints (NomogramBreakPoint). |
| **Contingency** | `Contingency` | `CTGLabel` | *(none flagged secondary)* | 166 | 40 | `10980` | **UNVERIFIED:** (no standalone prose found; only its CTGElement subdata format — an ordered list of actions with optional criteria/status/timing — is documented). |

Notes / gotchas read from source:
- **Branch / Transformer / DCLine / MSLine** are all two-terminal: the `:1` suffix is
  the **to-bus** (`BusNum` = from, `BusNum:1` = to), plus a circuit id
  (`LineCircuit`, or `DCLID` for DC). The generator also flags `BusName_NomVolt:1` as
  `PRIMARY` — it is a composite "BusName_NomVolt" identifier for the to-bus; the
  numeric `BusNum`/`BusNum:1`/`LineCircuit` triple is the one you normally supply.
- **Transformer is a separate `GObject` class** from `Branch` (`grid.py:176297`), but
  in PowerWorld a transformer is still a Branch with `LineXFType` set — the two schemas
  overlap heavily (both expose `LineR`/`LineX`, ratings, `Branch*` fields).
- **`ThreeWXFormer`** (`grid.py:9`) is the 3-winding transformer with a different key
  shape (`BusIdentifier`, `BusIdentifier:1`, `BusIdentifier:2`, `LineCircuit`) — use it
  for 3-winders, not `Transformer`.
- **Substation**: `grid.py` declares `SubNum`/`SubName` **twice** in the class body
  (duplicate enum members). Under Python ≥3.13's stricter `Enum` this raises on import
  (the package targets 3.11, where the dup is treated as an alias). Effective key is
  `SubNum`, secondary `SubName`.
- **` contingencies / interfaces / injection groups / nomograms`** are **string-keyed**
  (`CTGLabel`, `FGName`, `InjGrpName`) — no numeric key.
- Keyless objects exist too (e.g. `Sim_Solution_Options`): `Type.keys()` is empty and
  the bracket setter takes a positional value list instead (`indexable.py:282-296`).

---

## Part B — SAW SimAuto command catalog

`SAW` (`saw/saw.py:28-55`) is assembled by the **mixin pattern**: `SAWBase` plus 19
mixins. Reach it via `pw.esa`. Two call styles inside:
`_com_call(...)` wraps a direct SimAuto COM function; `_run_script("Cmd", *args)`
(`base.py:202`) builds a PowerWorld **script command** string and routes it through
`RunScriptCommand`. So a mixin method named `EnterMode` *is* the script command
`EnterMode(...)` — the Python method name = the PowerWorld aux/script command name.

### B.1 Mixins (what each covers) — `saw/`

| Mixin | File | Covers |
|---|---|---|
| `SAWBase` | `base.py` | COM core: connect/`exit`, `RunScriptCommand`/`RunScriptCommand2`, `ProcessAuxFile`, `exec_aux`, `_run_script`/`_com_call` plumbing, properties (`CreateIfNotFound`, `ProcessID`) |
| `DataMixin` | `data.py` | **The data layer** — Get/Change Parameters (single/multiple/rect/typed), `GetFieldList`, `ListOfDevices` |
| `PowerflowMixin` | `powerflow.py` | `SolvePowerFlow`, flat start, mismatch/tolerance, **`SaveState`/`LoadState`**, diff-case |
| `GeneralMixin` | `general.py` | `EnterMode`, `StoreState`/`RestoreState`/`DeleteState`, aux/CSV load (`LoadAux`, `LoadCSV`, `ImportData`), `SaveData`, `SetData`/`CreateData`, `GetSubData`/`SetSubData`, `Delete`, `SelectAll` |
| `CaseActionsMixin` | `case_actions.py` | `OpenCase`/`OpenCaseType`, `SaveCase`, `CloseCase`, `NewCase`, renumbering, `Scale` |
| `ModifyMixin` | `modify.py` | Topology/model edits: `Move`, `SplitBus`/`MergeBuses`, `TapTransmissionLine`, injection-group/interface create, participation factors |
| `ContingencyMixin` | `contingency.py` | `CTGSolve`/`CTGSolveAll`, `CTGAutoInsert`, `CTGApply`, OTDF, read/write CTG files |
| `TransientMixin` | `transient.py` | Transient stability: `TSSolve`/`TSSolveAll`, `TSInitialize`, `TSGetResults`, result storage, model load/save |
| `SensitivityMixin` | `sensitivity.py` | `CalculatePTDF`, `CalculateLODF`(+matrix/screening), `CalculateShiftFactors`, loss/volt sense |
| `MatrixMixin` | `matrices.py` | `get_ybus`, `get_jacobian`(+ids), `get_gmatrix`, `SaveJacobian` |
| `TopologyMixin` | `topology.py` | Path/island analysis, `CloseWithBreakers`/`OpenWithBreakers`, `ExpandBusTopology`, `SaveConsolidatedCase` |
| `RegionsMixin` | `regions.py` | Area/zone/region operations |
| `ScheduledActionsMixin` | `scheduled.py` | Scheduled-action automation |
| `TimeStepMixin` | `timestep.py` | **TimeStep weather feature** — `TimeStepDoRun`, `TimeStepLoadPWW*`, B3D/TSB load-save, `TimeStepSaveFieldsSet` |
| `WeatherMixin` | `weather.py` | Weather data helpers |
| `GICMixin` | `gic.py` | Geomagnetically-induced-current commands |
| `OPFMixin` / `PVMixin` / `QVMixin` / `ATCMixin` / `FaultMixin` | `opf.py` … `fault.py` | OPF, PV/QV curves, ATC, fault analysis |

### B.2 Most-used methods (the ones agents actually call)

**Reading data** (`saw/data.py`):
- `GetParametersMultipleElement(ObjectType, ParamList, FilterName="")` → `DataFrame`
  (string output, `data.py:284`). The classic ESA read.
- `GetParamsRectTyped(ObjectType, ParamList, FilterName="")` → typed `DataFrame`
  (preserves native variant types; `data.py:324`). **This is what the bracket read
  uses.**
- `GetParametersSingleElement(ObjectType, ParamList, Values)` → `Series` (`data.py:246`).
- `GetFieldList(ObjectType)` → all available fields for a type (`data.py:187`);
  `ListOfDevices(ObjType, FilterName="")` → device keys (`data.py:478`).

**Writing data** (`saw/data.py`):
- `ChangeParametersMultipleElementRect(ObjectType, ParamList, df)` — push a whole
  DataFrame back (`data.py:88`). **Used by the bracket setter.** `ParamList` **must
  lead with the key fields.**
- `ChangeParametersMultipleElement(ObjectType, ParamList, ValueList)` (`data.py:54`).
- `ChangeParametersSingleElement(ObjectType, ParamList, Values)` (`data.py:21`).

**Mode / state / solve**:
- `EnterMode("EDIT" | "RUN")` (`general.py:200`) — must be in EDIT to create/delete
  objects; RUN to solve. Accepts `PowerWorldMode.EDIT/RUN`.
- `SolvePowerFlow(SolMethod=SolverMethod.RECTNEWT)` (`powerflow.py:10`) — also accepts
  `"POLARNEWT"`, `"GAUSS"`, `"DC"`, etc.
- `SaveState()` / `LoadState()` (`powerflow.py:382`/`390`) — the **single** PowerWorld
  power-flow state stack (`pw.snapshot()` context manager wraps these).
- `StoreState(name)` / `RestoreState(name, state_type="USER")` / `DeleteState(name)`
  (`general.py:225`/`246`/`267`) — **named** states (different from Save/LoadState).

**Case actions** (`saw/case_actions.py`): `OpenCase(FileName)` (`33`),
`SaveCase(FileName=None, FileType="PWB", Overwrite=True)` (`127`), `CloseCase()` (`113`),
`NewCase()` (`254`), `Scale(...)` (`458`).

**Aux / script** (`saw/base.py` + `general.py`):
- `RunScriptCommand(Statements)` (`base.py:240`) — run a raw PowerWorld script string.
- `RunScriptCommand2(Statements, StatusMessage)` (`base.py:260`).
- `ProcessAuxFile(FileName)` (`base.py:179`) / `exec_aux(aux, ...)` (`base.py:422`) —
  run an aux file / inline aux text.
- `LoadAux(filename, create_if_not_found=False)` (`general.py:288`),
  `LoadCSV` (`337`), `ImportData` (`311`).

**TimeStep (weather)** (`saw/timestep.py`): `TimeStepDoRun(start, end)` (`10`),
`TimeStepDoSinglePoint(time_point)` (`28`), `TimeStepLoadPWW(filename, solution_type)`
(`146`), `TimeStepLoadPWWRange(...)` (`164`), `TimeStepSaveFieldsSet(object_type,
field_list, filter_name)` (`268`), `TimeStepLoadB3D` (`135`), `TimeStepLoadTSB`/`SaveTSB`
(`307`/`318`). *(This is PowerWorld's TimeStep feature — NOT transient stability; see the
TS disambiguation on [esapp](../concepts/esapp.md).)*

**Contingency** (`saw/contingency.py`): `CTGSolve(ctg_name)` (`11`),
`CTGSolveAll(distributed=False, clear_results=True)` (`33`), `CTGAutoInsert()` (`61`),
`CTGApply(name)` (`136`), `CTGWriteResultsAndOptions(...)` (`79`).

**Transient stability** (`saw/transient.py`): `TSSolve(...)` (`58`), `TSSolveAll()`
(`96`), `TSInitialize()` (`28`), `TSGetResults(...)` (`326`),
`TSResultStorageSetAll(object="ALL", value=True)` (`41`).

**Matrices / sensitivities**: `get_ybus(full=False)` (`matrices.py:15`),
`get_jacobian(full=False, form=JacobianForm.RECTANGULAR)` (`matrices.py:178`),
`CalculatePTDF(seller, buyer, method=LinearMethod.DC)` (`sensitivity.py:36`),
`CalculateLODF(branch, method=LinearMethod.DC)` (`sensitivity.py:65`),
`CalculateShiftFactors(...)` (`sensitivity.py:197`).

### B.3 Common `RunScriptCommand(...)` script commands

Full SCRIPT-command index (all 26 categories, 344 actions) → aux script catalog.
The named methods above (§B.2) remain the preferred Python entry points; the catalog
is the raw script-command reference for anything unwrapped.

> Preference (per wiki house rules): for **data**, use the bracket interface
> (`pw[Gen, fields]`, `pw[Gen] = df`) over raw `GetParametersMultipleElement` /
> `ChangeParametersMultipleElementRect`; for **script commands**, use the named SAW
> methods (`pw.esa.SolvePowerFlow()`) or `pw.esa.RunScriptCommand("...")` for anything
> not yet wrapped. See [esapp-overview](../methods/esapp-overview.md) for end-to-end recipes and [powerworld-simauto](../concepts/powerworld-simauto.md)
> for the underlying COM server.


---

# ==== time-step-simulation-backend.md ====

---
type: reference
domain: cross-cutting
aliases: [timestep-backend, time-step-simulation-backend]
tags: [timestep, powerworld, esapp, simauto, backend, reference]
---

# Reference: time-step-simulation backend

> ⚠️ **TimeStep ≠ Transient Stability.** This is PowerWorld's **TimeStep** weather
> feature (quasi-static `.pww` weather → hourly MW), driven by the low-level `esapp`
> `TimeStep*` script commands. It is **NOT** a transient-stability/dynamics study and
> does **NOT** use esapp's `pw.ts_solve` / `TSWatch` / `ContingencyBuilder` API (see the
> "TS" warning on [esapp](../concepts/esapp.md)). The "TS" in the `TSPFWModelString` field means *TimeStep*,
> not Transient Stability. Do not import or call any transient-stability function here.

## Abstract

Code-reconstruction reference for the time step simulation project — the `_simulation_worker` PowerWorld call sequence (weather load → generator selection → field-save wrapper → run → export), `_GEN_PARAM` field list, `process_results` CSV post-processing with 8 header rows skipped, and both series and parallel `main.py` orchestration variants. Covers every SimAuto command, required wrapper (`TIMESTEPSaveSelectedModifyStart`/`Finish`), and gotcha in enough detail to regenerate working simulation code from scratch. Read this in full only when writing or regenerating code for time step simulation; for the gist, use the project page.

## Connections

- **Up:** time step simulation (the project) + [Home](../index.md)
- **Across:** [pww-data](../concepts/pww-data.md), pfw copperplate, [timestep-simulation](../concepts/timestep-simulation.md), [timestep-simulation-setup](../methods/timestep-simulation-setup.md)

## Content

> **Library note — prefer `esapp` over `esa`.** This repo imports the standalone `esa` (Easy SimAuto) package. For new or regenerated code, prefer **`esapp` (ESA++)**: it wraps the **same** PowerWorld SimAuto server, so every `RunScriptCommand` / `TimeStep*` script command is identical via `pw.esa.RunScriptCommand(...)`, and esapp is far better documented in-package — an agent reasons about it more reliably. Swap esa's data helpers (`GetParametersMultipleElement`, `change_parameters_multiple_element_df`, `get_key_field_list`) for esapp's bracket interface (`pw[Type, fields]`, `pw[Type] = df`, `Type.keys()`). See [esapp-overview](../methods/esapp-overview.md). (Library choice only — unrelated to the TimeStep-vs-Transient-Stability distinction.)

Code-reconstruction knowledge for time step simulation. Given a plain prompt
("run the renewable sim on the Synth2k case"), an agent reads this page and
writes WORKING code. Everything here is verified against the real source on disk
(`C:\path\to\time-step-simulation`). Hub: [Home](../index.md).

The whole engine is two functions in `function.py`: `_simulation_worker(...)` (drives
PowerWorld) and `process_results(...)` (post-processes the CSV). `main.py` /
`parallel/main.py` are just CLI + grouping + I/O around them. The time math lives in
`time_utils.py`. **`parallel/function.py` is byte-identical to `function.py`** — the
engine is shared; only the `main.py` orchestration differs.

---

## 0. Imports & environment (get these wrong and nothing runs)

- **`from esapp import PowerWorld`** — esapp (ESA++) wraps the same PowerWorld SimAuto
  server as the older standalone `esa` package, and is the one to write. `pw.esa` is
  esapp's own raw SimAuto handle, so every `RunScriptCommand` / `TimeStep*` call below is
  identical; only the data helpers differ (bracket interface instead of esa's
  `GetParametersMultipleElement` / `change_parameters_multiple_element_df`).
- The import is **lazy** — done *inside* `_simulation_worker`, not at module top —
  so importing `function.py` never requires PowerWorld to be installed. Keep it lazy
  if you regenerate this.
- **Windows-only.** esapp drives PowerWorld Simulator through SimAuto (COM). No
  PowerWorld → no run.
- `numpy` is imported at module top with `# noqa: F401` purely "for parity with
  downstream tooling" — it's not used directly in `function.py`. `pandas` is used.
- `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))` is done so
  `from time_utils import convert_to_utc` resolves regardless of CWD.

```python
import os, sys, shutil, tempfile
import numpy as np   # noqa: F401
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from time_utils import convert_to_utc
# ... inside the worker:
from esapp import PowerWorld       # lazy, only when actually simulating
from esapp.components import Gen
```

---

## 1. `_GEN_PARAM` — the generator field list (verbatim)

These extra fields are appended to the case's key fields and pulled from every
generator. Verbatim from `function.py:28-32`:

```python
_GEN_PARAM = [
    'Latitude', 'Longitude', 'GenUnitType', 'GenFuelType',
    'ZoneName', 'AreaName', 'TSPFWModelString', 'GenMWMax',
    'Selected', 'CustomString:1', 'CustomString:2',
]
```

Why each field is pulled:

| Field | Used for |
|---|---|
| `Latitude`, `Longitude` | output header rows (rows 7 & 8); also fed by `PFW_Insertion` to assign ISO region |
| `GenUnitType` | pulled for completeness; not used downstream in `function.py` |
| `GenFuelType` | **the renewable selector** — `.str.contains('WND\|SUN')` picks wind/solar; also splits solar (`SUN`) vs wind (`WND`) |
| `ZoneName` | output header "State" row (label maps `ZoneName` → "State") |
| `AreaName` | output header "Utility" row (label maps `AreaName` → "Utility") |
| `TSPFWModelString` | output header "PV / Wind Types" row — the unit's PFW model string |
| `GenMWMax` | output header "Gen Max MW" row |
| `Selected` | toggled to `'YES'` for renewables, then used to drive `TimeDomainSelected` |
| `CustomString:1` | pulled but not used in `function.py` |
| `CustomString:2` | output header "ISO" row (label maps `CustomString:2` → "ISO"); populated by `PFW_Insertion` spatial join |

Key fields come from `Gen.keys()` (typically `BusNum`, `GenID`)
and are **prepended**, so the resulting `gen` DataFrame has columns
`[<key fields>] + _GEN_PARAM`.

> ⚠️ **This prepend is not optional.** Later the code pushes `gen` back with
> `pw[Gen] = gen` (twice — to set `Selected` and
> `TimeDomainSelected`). PowerWorld matches each row to a generator by its key fields, so
> if `BusNum`/`GenID` weren't in the DataFrame the write would **silently do nothing** and
> no generators would be selected. Always keep the key columns in any DataFrame you write
> back. (Same rule on the esapp bracket path — see [esapp](../concepts/esapp.md).)

---

## 2. `_simulation_worker` — the FULL backend sequence, IN ORDER

Signature: `_simulation_worker(case_path, pww_list, result_csv) -> gen (DataFrame)`.
Returns the generator metadata DataFrame (the caller needs it for `process_results`).
Verbatim mechanics from `function.py:35-83`:

```python
def _simulation_worker(case_path, pww_list, result_csv):
    from esapp import PowerWorld                     # lazy import
    from esapp.components import Gen
    tmp_case = None
    try:
        # (a) temp-copy the case so parallel runs never fight over the .pwb lock
        tmp_fd, tmp_case = tempfile.mkstemp(suffix='.PWB')
        os.close(tmp_fd)
        shutil.copy2(case_path, tmp_case)

        # (b) open the temp case
        pw = PowerWorld(tmp_case)

        # (c) pull generator metadata (key fields + _GEN_PARAM)
        gen_param = list(Gen.keys()) + _GEN_PARAM
        gen = pw[Gen, gen_param]

        # (d) load weather file(s): first = Load, rest = Append
        pw.esa.RunScriptCommand(f'TimeStepLoadPWW("{pww_list[0]}","Weather Only");')
        for pww in pww_list[1:]:
            pw.esa.RunScriptCommand(f'TimeStepAppendPWW("{pww}","Weather Only");')

        # (e) EDIT mode: mark renewables Selected = YES, push back
        pw.esa.RunScriptCommand('EnterMode(EDIT);')
        gen.loc[gen['GenFuelType'].str.contains('WND|SUN', na=False), 'Selected'] = 'YES'
        pw[Gen] = gen
        pw.esa.RunScriptCommand('EnterMode(RUN);')

        # (f) declare which fields to save — MUST be wrapped (see callout below)
        pw.esa.RunScriptCommand("TIMESTEPSaveSelectedModifyStart;")
        gen.loc[gen['Selected'] == 'YES', 'TimeDomainSelected'] = 'YES'
        pw[Gen] = gen
        pw.esa.RunScriptCommand(
            'TimeStepSaveFieldsSet(GEN, [BGGenMWFuelTypeGeneric:10, BGGenMWFuelTypeGeneric:12], SELECTED);'
        )
        pw.esa.RunScriptCommand("TIMESTEPSaveSelectedModifyFinish;")

        # (g) run + export
        pw.esa.RunScriptCommand('TimeStepDoRun();')
        pw.esa.RunScriptCommand(f'TimeStepSaveResultsByTypeCSV(gen,"{result_csv}");')
        pw.esa.CloseCase()
        return gen
    finally:
        # (h) always delete the temp case
        if tmp_case and os.path.exists(tmp_case):
            try:
                os.remove(tmp_case)
            except OSError:
                pass
```

Step-by-step, every SimAuto call / SAW method in execution order:

1. `tempfile.mkstemp(suffix='.PWB')` → `os.close(fd)` → `shutil.copy2(case_path, tmp_case)` — work on a private temp copy, never the original `.pwb`.
2. `pw = PowerWorld(tmp_case)` — open the case.
3. `gen_param = list(Gen.keys()) + _GEN_PARAM`
4. `gen = pw[Gen, gen_param]` — DataFrame of all gens.
5. `pw.esa.RunScriptCommand('TimeStepLoadPWW("<pww0>","Weather Only");')` — load first weather file.
6. for each remaining pww: `pw.esa.RunScriptCommand('TimeStepAppendPWW("<pww>","Weather Only");')` — append.
7. `pw.esa.RunScriptCommand('EnterMode(EDIT);')`
8. set `gen['Selected'] = 'YES'` where `GenFuelType` contains `WND|SUN`.
9. `pw[Gen] = gen` — push selection into the case.
10. `pw.esa.RunScriptCommand('EnterMode(RUN);')`
11. **`pw.esa.RunScriptCommand("TIMESTEPSaveSelectedModifyStart;")`** ← opens the save-field edit transaction.
12. set `gen['TimeDomainSelected'] = 'YES'` where `Selected == 'YES'`.
13. `pw[Gen] = gen` — push `TimeDomainSelected`.
14. `pw.esa.RunScriptCommand('TimeStepSaveFieldsSet(GEN, [BGGenMWFuelTypeGeneric:10, BGGenMWFuelTypeGeneric:12], SELECTED);')` — choose the two MW-by-fuel-type fields to save for selected gens.
15. **`pw.esa.RunScriptCommand("TIMESTEPSaveSelectedModifyFinish;")`** ← closes the transaction.
16. `pw.esa.RunScriptCommand('TimeStepDoRun();')` — run the time-step simulation.
17. `pw.esa.RunScriptCommand(f'TimeStepSaveResultsByTypeCSV(gen,"{result_csv}");')` — export gen results to CSV.
18. `pw.esa.CloseCase()`.
19. `finally:` delete `tmp_case`.

### ⚠️ REQUIRED wrapper — do not drop it

```
TIMESTEPSaveSelectedModifyStart;
   ... set TimeDomainSelected = YES + TimeStepSaveFieldsSet(...) ...
TIMESTEPSaveSelectedModifyFinish;
```

The `TimeStepSaveFieldsSet` + `TimeDomainSelected` changes **MUST** be bracketed by
`TIMESTEPSaveSelectedModifyStart;` … `TIMESTEPSaveSelectedModifyFinish;`. Without this
wrapper the field-save selection **silently fails** — the sim runs, the CSV is
written, but the per-generator MW columns you wanted are missing/empty. There is no
error; you just get a useless file. If you regenerate this code, keep the Start/Finish
pair around steps 11–15 exactly.

### Field codes `BGGenMWFuelTypeGeneric:10` / `:12`

These are the two PowerWorld TimeStep result fields saved per selected generator —
"generator MW by generic fuel type", indices `10` and `12`. Downstream
`process_results` splits output columns by the literal substrings `'solar'` and
`'wind'` in the exported CSV column names, so the two indices correspond to the solar
and wind MW outputs.
> **UNVERIFIED:** needs confirmation -- which of `:10` / `:12` is solar vs wind in the PowerWorld fuel-type
> generic enumeration (code only relies on the column-name token, not the index).

### `pww_list` semantics

`pww_list[0]` → `TimeStepLoadPWW`; every subsequent entry → `TimeStepAppendPWW`. Both
use the `"Weather Only"` mode argument. In practice the callers pass **one PWW per
worker call** (`[pww]`) and concatenate the resulting CSVs in pandas afterward — the
Append branch exists but the production paths feed single-file lists and stitch
quarters at the DataFrame level (see §4).

---

## 3. `process_results(gen, df)` — CSV → (solar_df, wind_df)

Signature: `process_results(gen, df) -> (solar_df, wind_df)`. `gen` is the DataFrame
returned by the worker; `df` is the raw exported CSV read back via `pd.read_csv`.
Verbatim from `function.py:86-152`.

### 3a. Time conversion first
`result = convert_to_utc(df)` — replaces the first column (Excel-serial CST
timestamps) with ISO-8601 UTC strings (see §6).

### 3b. The 8 metadata header rows
Eight rows are prepended above the time-series. `row_names` are the row labels;
`labels` are the `gen` columns each row pulls its values from (positional zip):

```python
row_names = ['ISO', 'PV / Wind', 'PV / Wind Types', 'Gen Max MW', 'State', 'Utility',
             'Latitude', 'Longitude']
labels    = ['CustomString:2', 'GenFuelType', 'TSPFWModelString',
             'GenMWMax', 'ZoneName', 'AreaName', 'Latitude', 'Longitude']
```

| Header row | Source `gen` column |
|---|---|
| ISO | `CustomString:2` |
| PV / Wind | `GenFuelType` |
| PV / Wind Types | `TSPFWModelString` |
| Gen Max MW | `GenMWMax` |
| State | `ZoneName` |
| Utility | `AreaName` |
| Latitude | `Latitude` |
| Longitude | `Longitude` |

### 3c. `(BusNum, GenID)` meta_lookup
An O(1) dict over only the renewable rows, keyed by `(int(BusNum), str(GenID))`:

```python
ren_mask = gen['GenFuelType'].str.contains('WND|SUN', na=False)
meta_lookup = {
    (int(row['BusNum']), str(row['GenID'])): row
    for _, row in gen[ren_mask].iterrows()
}
```

### 3d. Header build — per-column branch logic
Walk every column of `result` once:

- column == `'DateTimeUTCExcelFormat'` → each header row gets its own label (the row name itself) in this column.
- column contains `'Gen'` → parse `parts = col.split(' ')`; `busnum = int(parts[2].replace("'", ""))`, `genid = parts[3].replace("'", "")`. On `IndexError`/`ValueError` → fill `'N/A'`. Otherwise look up `meta_lookup[(busnum, genid)]` and fill each header row from its mapped label (`'N/A'` if not found).
- any other column → fill `''` (empty) for all header rows.

The column-name shape PowerWorld emits is therefore like `... Gen '<BusNum>' '<GenID>' ...` (quoted bus and id at `parts[2]`/`parts[3]`), with `'solar'`/`'wind'` somewhere in the name. Header rows are assembled into `header_df` and `pd.concat([header_df, result], ignore_index=True)` → `result_1`.

### 3e. Solar / wind split by token matching
```python
PV_gen = gen[gen['GenFuelType'].str.contains('SUN', na=False)]
WT_gen = gen[gen['GenFuelType'].str.contains('WND', na=False)]

solar_tokens = {f"'{int(r['BusNum'])}' '{r['GenID']}'" for _, r in PV_gen.iterrows()}
wind_tokens  = {f"'{int(r['BusNum'])}' '{r['GenID']}'" for _, r in WT_gen.iterrows()}

solar_columns = ['DateTimeUTCExcelFormat'] + [
    c for c in result_1.columns
    if 'solar' in c.lower() and any(tok in c for tok in solar_tokens)]
wind_columns = ['DateTimeUTCExcelFormat'] + [
    c for c in result_1.columns
    if 'wind' in c.lower() and any(tok in c for tok in wind_tokens)]

return result_1[solar_columns], result_1[wind_columns]
```

A column lands in the solar output iff its name contains `'solar'` (case-insensitive)
**AND** contains a `'<BusNum>' '<GenID>'` token of a `SUN` generator; symmetric for
wind/`WND`. The timestamp column `DateTimeUTCExcelFormat` is always kept first in both.
Both returned frames carry the 8 header rows on top.

---

## 4. `main.py` (series) — grouping, run loop, output naming

- CLI args (`parse_args`): `--case` (required), mutually-exclusive **required** group
  `--pww FILE...` xor `--pww-dir DIR`, plus `--year YYYY` (int, filters `--pww-dir`),
  `--output-dir`, `--yes/-y` (skip the `input()` confirm prompt).
- Default output: `Results/` next to `main.py` (`os.path.join(_script_dir, "Results")`).
- **Grouping (`_group_files`)**: for each file, `re.search(r"(\d{4})_Q\d", name)`.
  Matches (quarter files like `NorthAmerica2025_Q1.pww`) are grouped by **year** so all
  4 quarters run as one logical run (`groups[year] = [...]`). Non-matches (e.g. forecast
  files) become individual runs keyed by their filename stem. With `--pww-dir`, only
  `.pww` files are listed and `year_filter=args.year` drops other years.
- **Run loop**: for each `(key, pww_list)`:
  - `is_historical = bool(re.search(r"\d{4}_Q\d", basename(pww_list[0])))`.
  - `out_stem = f"Historical_{key}"` if historical else `key` (forecast stems already
    start with `Forecast_`, so don't double-prefix).
  - Outputs: `{out_stem}_solar.csv`, `{out_stem}_wind.csv` in `output_dir`.
  - **Resume-safe skip**: if BOTH solar and wind CSVs already exist → skip (delete to re-run).
  - Runs each pww **one at a time** via `_simulation_worker(args.case, [pww], q_csv)`
    into `_raw_<qname>.csv`, reads each back with `pd.read_csv`, removes the temp csv,
    `pd.concat(dfs, ignore_index=True)`, then `process_results(gen, df)` → write
    `solar_path` / `wind_path`. `gen` from the last quarter is reused (identical per case).
  - Wrapped in try/except → prints error + `traceback.print_exc()`, continues to next group.

---

## 5. `parallel/main.py` — the parallel variant (differences only)

Engine (`parallel/function.py`) is identical; only orchestration changes.

- **`ProcessPoolExecutor`** (`concurrent.futures`). Each PWW is simulated in its own
  child process driving its **own PowerWorld/SimAuto instance** against its **own
  private temp copy** of the case (the temp-copy in `_simulation_worker` is what makes
  this safe). Workers are **top-level functions** (`_run_one_sim`, `_run_one_group`) so
  they're picklable on Windows; they import `function` *inside* the child so the parent
  never loads PowerWorld.
- **`--workers/-w N`** (default 4): caps concurrent PowerWorld instances. Keep ≤ what
  the PowerWorld license + RAM allow. `effective_workers = min(workers, num_tasks)`.
- **`--year` takes `nargs="+`** here (multiple years), vs a single int in series.
  Omitting `--year` with `--pww-dir` → `_discover_years` runs **every** year found.
- **`_collect_year_quarters`**: for each requested year, collects `Q1..Q4` and reports
  `complete` / `partial` (missing quarters listed) / `none`. **Incomplete years are
  skipped**; only years with all 4 quarters become groups.
- **Two parallel granularities**:
  - **by-file (default)**: flatten groups into one task per PWW; each quarter runs in a
    separate worker concurrently (`_run_one_sim`). Parent then **assembles** each group
    sequentially — reads the per-quarter raw CSVs in sorted (quarter) order, concats,
    `process_results`, writes solar/wind, deletes temps. `gen_by_group` keeps the last
    gen per group; a group with any failed sim skips assembly.
  - **`--by-year`**: one whole year per worker (`_run_one_group`) — the worker runs all
    4 quarters sequentially, concats, splits, and writes the CSVs itself, returning
    `(key, ok, msg)` so big DataFrames never cross the process boundary.
- **Resume-safe**: before launching, groups whose solar+wind CSVs both exist are moved
  to `skipped`; only `pending` is run.
- Output naming (`_out_paths`) is the same `Historical_{year}` vs stem logic as series.

---

## 6. `time_utils.py` — time math ("settled, don't change")

CLAUDE.md flags this module as verified against real runs — **do not change without a
clear reason.** Signatures + behavior:

- `EXCEL_EPOCH = np.datetime64('1899-12-30')`; `CST_OFFSET_DAYS = 6.0/24.0` (CST = UTC-6).
- **`excel_serial_to_datetime(serial_values)`** → `datetime64[ns]` (tz-naive).
  Subtracts the 6h CST offset, splits into integer days + fractional nanoseconds, adds
  to the Excel epoch. Vectorized NumPy.
- **`_find_dst_sunday(year, month, start_day)`** → the first Sunday on/after `start_day`
  in that month, via numpy day-of-week arithmetic (epoch Thursday = 0).
- **`build_dst_mask(times)`** → bool array, True during US DST: **second Sunday in
  March 02:00 → first Sunday in November 02:00**, computed per unique year in the input.
- **`convert_to_utc(df)`** → copy of `df` with column 0 replaced by ISO-8601 UTC
  strings. Pipeline: `pd.to_numeric(col0)` → `excel_serial_to_datetime` →
  subtract 1h where `build_dst_mask` is True (CST→CDT correction) → round to nearest
  hour (`+1800s` then truncate to `datetime64[h]`) → `np.datetime_as_string(..., unit='s', timezone='UTC')`. This is what `process_results` calls.
- **`interpolate_to_hourly(df)`** → fills 3-hour forecast gaps to hourly. Detects gaps
  (`diff > 3601s`); if none, returns `df` unchanged. Otherwise reindexes onto an hourly
  `date_range`, linearly interpolates the generator columns, and rewrites column 0 back
  to Excel-serial. **Note:** present in `time_utils.py` but NOT called by `function.py`
  / `process_results` in the current path — available for forecast pre-processing.

---

## 7. Gotchas checklist (regenerate-safe)

- ✅ `from esapp import PowerWorld` — **esapp, not the standalone `esa`**. Same SimAuto
  underneath; do not mix the two in one script.
- ✅ **Windows + PowerWorld only** (SimAuto/COM).
- ✅ **Temp-copy the case** (`mkstemp('.PWB')` + `shutil.copy2`) and run against the
  copy; delete in `finally`. This is what makes parallel runs lock-safe.
- ✅ **`TIMESTEPSaveSelectedModifyStart;` … `TIMESTEPSaveSelectedModifyFinish;`** must
  wrap the `TimeStepSaveFieldsSet` + `TimeDomainSelected` edits, or saved fields
  silently come back empty.
- ✅ Selection is two-stage: `Selected='YES'` (EDIT mode) for renewables, then
  `TimeDomainSelected='YES'` (inside the Save-Modify wrapper) for those same gens.
- ✅ `EnterMode(EDIT)` before pushing `Selected`; `EnterMode(RUN)` before the
  Save-Modify wrapper and the run.
- ✅ Renewable selector everywhere: `GenFuelType.str.contains('WND|SUN', na=False)`;
  solar = `SUN`, wind = `WND`.
- ✅ **Resume-safe skip**: a run is skipped iff BOTH its solar and wind CSVs exist.
- ✅ **Historical grouping** keys off `re.search(r"(\d{4})_Q\d", name)` — quarter files
  group by year and are named `Historical_{year}_{solar,wind}.csv`; anything else runs
  individually under its stem. Keep `_group_files` and the `is_historical` check in sync.
- ✅ Confirmation prompt via `input()` unless `--yes/-y`; parallel adds `--workers`.
- ✅ Parallel workers must stay **top-level / picklable** and import `function` inside
  the child process (Windows spawn).

---

## Related

- Project: time step simulation · Hub: [Home](../index.md)
- Concept/how-to: [timestep-simulation](../concepts/timestep-simulation.md) · [timestep-simulation-setup](../methods/timestep-simulation-setup.md)
- Inputs: [pww-data](../concepts/pww-data.md) · PFW context: pfw copperplate · ISO prep: `PFW_Insertion/`


---
