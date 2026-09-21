---
type: concept
domain: tooling
aliases: [simauto-raw-output, flat-output-shape, getspecificfieldlist, field-family-discovery]
tags: [powerworld, simauto, esapp, com, discovery, field-metadata]
---

# SimAuto raw output shapes and field discovery

## Abstract

Below esapp's DataFrame conversion, every `pw.esa.*` SimAuto call returns the same envelope,
and a handful of raw functions never made it into esapp's wrapper set at all. This page
covers that envelope, the "flat" array layout used by three of those functions, and two
field-discovery calls that answer questions `GetFieldList` cannot: how many indexed slots a
repeatable field family has, and how to look up specific fields by name instead of pulling
the whole list. Useful when a raw COM call is unavoidable, or when `is_settable()` and
friends aren't enough to know what a field family actually contains.

## Connections

**Up:** [powerworld-simauto](powerworld-simauto.md) · [esapp-schema-reference](../references/esapp-schema-reference.md) ·
**Across:** [aux-only-powerworld](aux-only-powerworld.md) (field-name provenance rule) ·
[esapp-script-command-wrappers](esapp-script-command-wrappers.md) (the `SaveCase` COM exception this page's FileType table supports) ·
[objectid-identification-traps](objectid-identification-traps.md) (that page's silent-wrong-match
failure mode is exactly the kind of thing worth double-checking with this page's raw field
discovery calls) ·
**Deeper:** Simulator's *SimAuto Functions* manual chapter (Help menu)

## Content

### Every function's Output starts the same way

Whatever a SimAuto call returns, slot 0 of the `Output` variant array is always the error
string, empty on success. This is the shape under every raw `pw.esa.*` call, wrapped by
esapp or not — worth knowing when debugging a raw call by inspecting `Output` directly
rather than through an esapp exception.

### Three ways to discover field metadata — not interchangeable

`GetFieldList(ObjectType)` is esapp's existing authority for `is_settable()`, returning
every field's key designator, legacy `variablename:location` form, data type, description,
and an enterable flag, in a fixed six-column layout. Two more functions answer different
questions:

- `GetSpecificFieldList(ObjectType, FieldList)` looks up only the fields you name, and adds
  the GUI column header alongside the variable name — pass `"ALL"` for every field, or
  `"variablename:ALL"` to expand one repeatable field family (e.g. `CustomInteger:ALL`,
  `PTDFMult:ALL`) into all of its indexed instances.
- `GetSpecificFieldMaxNum(ObjectType, "variablename")` returns the highest location index a
  given field name uses for that object type — the way to learn in code how many
  `CustomInteger`/`CustomString`/`PTDFMult`-style slots exist before iterating them, instead
  of guessing a cutoff.

Neither appears in esapp's mixin table today; only `GetFieldList` does.

### ListOfDevices vs ListOfDevicesAsVariantStrings

`ListOfDevices` is the one SimAuto function that returns strongly-typed values — bus numbers
as Long Integers, IDs as strings — instead of variant-of-string like everything else, a
long-standing quirk PowerWorld can no longer change without breaking existing callers.
`ListOfDevicesAsVariantStrings` is the corrected twin, returning variant-of-string
consistently. This only matters if code inspects `pw.esa.ListOfDevices` output types
directly rather than going through esapp's DataFrame conversion.

### The flat output/input layout

`GetParametersMultipleElementFlatOutput`, `ListOfDevicesFlatOutput`, and the input-side
`ChangeParametersMultipleElementFlatInput` exist for callers without good multi-dimensional
array support. All three share one layout:

```
[errorString, NumberOfObjectsReturned, NumberOfFieldsPerObject,
 Obj1Field1, Obj1Field2, ..., ObjNFieldM]
```

fields for object 1 first, then object 2, and so on. `ChangeParametersMultipleElementFlatInput`
aborts the whole call — loudly, not silently — if `NoOfObjects × len(ParamList) !=
len(ValueList)`, so a ragged flat array fails fast rather than misaligning fields silently.

### Typed column retrieval and its failure mode

`GetParamsRectTyped`/`GetParamsTypedCols` let you request a COM VARENUM type
(`VT_I2`/`VT_I4`/`VT_R4`/`VT_R8`/`VT_BSTR`/`VT_VARIANT`) per column instead of getting
everything back as a string. Requesting a non-scalar-convertible field — a string ID field
as `VT_R8`, say — is a hard error naming the offending field, not a silent NaN or garbage
value. `VT_VARIANT` is the safe fallback: it returns natively-typed values with no
conversion contract to violate.

### SaveCase FileType values

`SaveCase(FileName, FileType, Overwrite)` accepts: `"PTI23"`–`"PTI35"` (raw), `"GE14"`–`"GE23"`
(epc), `"IEEE"`, `"UCTE"`, `"PWB5"`–`"PWB24"` or `"PWB"` (most recent). For aux output
specifically, `"AUXNETWORK"` (network data only) is PowerWorld's recommended type;
`"AUX"`/`"AUXSECOND"`/`"AUXLABEL"` (whole-case, keyed on primary/secondary/label keys
respectively) are kept for backward compatibility. Since the kit already documents COM
`SaveCase` as a silent no-op and routes callers to the script-command `SaveCase(...)`
instead (see [esapp-script-command-wrappers](esapp-script-command-wrappers.md)), this table
is the reference for choosing a non-PWB FileType with that script command.

### RunScriptCommand2's extra signal

`RunScriptCommand2(Statements, out StatusMessage)` returns a Boolean success flag plus an
out-parameter message string that carries informational text even on success — unlike plain
`RunScriptCommand`, whose return value only ever carries an error string. Useful when a
script action's own success message carries information (e.g. a row count) worth capturing
without a separate `LogSave`.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*
