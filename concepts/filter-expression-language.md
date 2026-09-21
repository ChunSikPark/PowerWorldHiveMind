---
type: concept
domain: tooling
aliases: [advanced-filter, device-filter, model-expression, string-expression, filter-syntax]
tags: [powerworld, filters, expressions, data-model, silent-failure]
---

# PowerWorld: the filter and expression language

## Abstract

One grammar underlies Advanced Filters, Model Expressions, String Expressions, and
`DataCheck` conditions in PowerWorld — the same operators and functions, reused across
every place a case-information display, aux script, or `GetParametersMultipleElement`
call needs to select or compute over rows. Read this page before writing a `FilterName`
string, a device filter, or an inline comparison expression: the syntax has several traps
where a malformed filter does not error, it just silently matches nothing.

## Connections

**Up:** [pw-data-model](pw-data-model.md) · **Across:** [data-check-objects](data-check-objects.md) · [datamaintainer-and-object-groups](datamaintainer-and-object-groups.md) · **Deeper:** [esapp](esapp.md)

## Content

### Naming a filter that belongs to another object type

A filter is defined against one object type. Referencing it from a script command or aux
block that targets a *different* type requires prefixing the filter name with the target
type in angle brackets, no space: `<BUS>MyFilter` used where a Gen-scoped filter is
expected. Omit the prefix and PowerWorld looks for a same-named filter on the wrong type —
it will not find one, and the filter that "runs" simply returns nothing.

### Device filters — using one object type to filter another

A **device filter** selects rows of one object type based on membership in a *different*
object (an Injection Group, a `DataCheck`, an `ObjectGroup`; see
[datamaintainer-and-object-groups](datamaintainer-and-object-groups.md)). The form is:

```
<DEVICE> objecttype 'key1' 'key2' 'key3'
```

Its semantics are relational, not literal. An Injection Group used to filter Branches
does not return the group's member objects — it returns the branches connected to any
member's terminal bus. Reading a device filter as "give me the members" instead of "give
me what's related to the members" is the most common misreading.

### Combining conditions: one operator per filter, nest for the rest

A single Advanced Filter combines its conditions with exactly one logical operator: AND,
OR, XOR, NOT AND, NOT OR, One TRUE, or Num TRUE (the last two added in v19/v21
respectively). There is no mixed-operator form inside one filter — `A AND (B OR C)` does
not have a single-filter syntax. Build it by nesting: define one filter for the inner
group (`AF1 = B OR C`), then reference it from the outer filter as a condition
(`AF2 = A AND (meets filter AF1)`).

### The "Pre-Filter using Area/Zone/Owner Filters" checkbox

Every Advanced Filter carries a checkbox, off by default in the sense that its state is
whatever was last set, that pre-restricts the filter's candidate rows to whatever the
live Area/Zone/Owner/DataMaintainer filter currently shows. With it on, the filter's
result depends on UI-level filter state that isn't part of the filter definition itself —
running the identical named filter in two sessions (or two points in a batch run) can
return different rows with no change to the filter. Leave it off for anything that needs
to be reproducible from the filter definition alone.

### Field-to-field comparisons

"Enable Field to Field Comparisons" switches a condition's right-hand side from a
hardcoded constant to another field on the same device, or to a named Model Expression.
This is what makes a filter like "MW output > MW rated capacity" possible without
encoding a plant's capacity as a magic number in the filter itself.

### Range-of-numbers fields

Anywhere a filter, scaling dialog, or "within integer range list" comparison accepts a
list of bus/area/zone numbers, it accepts the same compact format: comma-separated
singles mixed with dashed ranges, no spaces required — `1-5,21,23-25`. This format is
shared across every field of this kind, not per-dialog.

### The shared expression grammar

Expressions, String Expressions, and Model Expressions all evaluate with one
function/operator set:

- Trig functions operate in radians.
- Comparison and bitwise operators: `==`, `<>`, `bitor`, `bitand`, `bitxor`, `shl`, `shr`,
  `MOD`, `!` (factorial), `^` (power).
- String-relevant functions: `Str(x, minlen, decimals)` (a negative `decimals` truncates
  trailing zeros instead of rounding), `Find`/`Search` (case-sensitive exact substring vs.
  wildcard, case-insensitive substring), and `IsTrue`, which normalizes any of
  T/TRUE/CONNECTED/CLOSED/YES/Y/1 to `1` and everything else to `0` — useful because
  status fields spell "on" differently across object types.

**Booleans are C-style, not 0/1.** A `true` result is "not exactly zero" — often literally
the numeric difference the expression computed — and `false` is exactly `0`. Code that
reads back an expression's numeric result and tests `== 1` for truth will be wrong for any
expression whose true branch doesn't happen to evaluate to exactly 1.

### Date/time functions and PowerWorld's date encoding

`TEXT`, `DATETIMEVALUE`, `DATEVALUE`, and `TIMEVALUE` convert between formatted date
strings and PowerWorld's internal date representation: days since 1899-12-30, with the
fractional part encoding time-of-day at roughly 1 ms precision as a double. Any aux file
or weather/TimeStep pipeline that embeds a formatted date string and needs it to round-trip
through PowerWorld goes through these functions.

### Interpolating a Model Expression into text — and its staleness trap

A saved Model Expression can be embedded directly in a case-information display or aux
file using the literal token `&ExprName:digits:decimals`, e.g. `&NetGeneration:5:2`. The
link is a snapshot taken at the point the token was typed, not a live reference — editing
the Model Expression afterward does not update text that already embeds `&ExprName`. Each
embedded reference has to be re-entered, or the file reloaded, for the new definition to
take effect. Generated aux files that embed expression references are exposed to this: a
regeneration step that doesn't force re-entry will keep emitting stale values.

### Verifying a filter matched what you meant

Because none of the failure modes above raise an error — a bad angle-bracket prefix, a
device filter with reversed relational logic, an unintentionally-enabled pre-filter
checkbox — the only reliable check is to count rows. Run the filter, read the resulting
row count (or the objects themselves) back through `esapp`, and compare against an
independent expectation before trusting a downstream call that consumes the filtered set.
A filter that matches zero objects looks, to every caller downstream, exactly like a
successful call over an empty set.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*
