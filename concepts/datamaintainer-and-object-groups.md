---
type: concept
domain: tooling
aliases: [datamaintainer, object-group, data-maintainer-inheritance, supplemental-data]
tags: [powerworld, data-model, filters, ownership, silent-failure]
---

# PowerWorld: DataMaintainer and ObjectGroup

## Abstract

`DataMaintainer` records who owns a slice of case data and lets that slice be filtered or
exported on its own; `ObjectGroup` is a lightweight named tag usable as a device filter.
Both let code slice a case along lines that aren't Area/Zone/Owner, and both have an
inheritance or auto-creation behavior that can change what a read or write touches without
any visible change to the script that issued it.

## Connections

**Up:** [pw-data-model](pw-data-model.md) · **Across:** [filter-expression-language](filter-expression-language.md) · [data-check-objects](data-check-objects.md) · **Deeper:** [esapp](esapp.md)

## Content

### DataMaintainer: what it is

`DataMaintainer` (added in v19) records a responsible contact for a slice of case data and
lets that slice be exported or written to an aux file on its own. Each object belongs to
at most one DataMaintainer.

### Assign vs. Inherit, and the fields that carry each

Every object type has two independent yes/no capabilities: whether a DataMaintainer can be
**assigned** to it directly, and whether it can **inherit** one from a related object.
Four fields matter for code that reads or sets this:

- `DataMaintainerAssign` — the direct-set field; writing a blank value clears it.
- `DataMaintainer` — read-only, and gives the *effective* value, which may have been
  inherited rather than assigned.
- `DataMaintainerInherit` — a YES/NO toggle, enterable only on the object types that
  support both assign and inherit: Bus, Gen, Load, Shunt, LineShunt, Branch, 3WXFormer,
  DFACTS, DCTransmissionLine, MTDCRecord, VSCDCLine.
- `DataMaintainerInheritBlock` — Bus and Substation only; setting it YES stops objects
  attached beyond that point from inheriting further up the chain.

### Inheritance order matters for automation

Each object type that inherits does so along a fixed precedence chain, and the chain isn't
symmetric. A Gen inherits from its Bus first, then that Bus's Substation. A Branch inherits
from its **NonMetered** bus first, then that bus's Substation, then the **Metered** bus,
then its Substation. On a tie line, which end is marked "metered" therefore silently
decides which DataMaintainer the branch ends up inheriting — a fact worth checking before
relying on a branch's effective `DataMaintainer` value.

### Objects that can never carry one

Solution/environment option objects, software-maintained objects (Island, ZoneTieLine,
AreaTieLine, SuperBus), and calculation results (ViolationCTG) are NO/NO on both
capabilities. Attempting to set `DataMaintainerAssign` on one of these hits a field that
is not enterable rather than raising an error — check whether the field is settable for
that type before writing to it, the same discipline described for any field in
[esapp](esapp.md).

### DataMaintainer filtering can silently shrink a read

Options → "Use Data Maintainers Filtering on Case Information Displays" ANDs DataMaintainer
filtering onto whatever Area/Zone/Owner filter is already active. Turning this option on,
with no change to any filter definition, can shrink the row count of a case-information
read that used to return everything. If a read count changes unexpectedly, this option is
one of the first things to check.

### ObjectGroup: a lightweight scriptable tag

`ObjectGroup` (added in v24) is a named tag usable as a device filter anywhere a
case-information display or aux script command accepts one, written as
`<DEVICE> ObjectGroup 'GroupName'` (see [filter-expression-language](filter-expression-language.md)
for device-filter syntax generally).

Membership in a group comes in two forms:

- **Assigned** — explicit membership, set through the `ObjectGroup\Assign Names` or
  `ObjectGroup\Append Names` fields. These are comma-delimited, and an object can belong to
  multiple groups.
- **Contained** — inherited membership. Assigning Areas to a group makes every generator
  inside those areas "contained" in the group, even though no generator was individually
  assigned.

### The silent-creation trap

Writing a group name into `ObjectGroup\Append Names` for a group that doesn't exist yet
**creates that group on the spot** — there is no separate create step and no error. Code
that generates an aux file with a typo'd or dynamically-built group name will create a new,
unintended group rather than failing to find the one it meant.

### Relationship to SupplementalData

`ObjectGroup` is functionally the same mechanism as `SupplementalData`/
`SupplementalClassification` configured with `Inherit=YES, Multiple=YES`, documented in the
manual as a topology-tools feature. `ObjectGroup` is the simpler path to the same behavior
when scripting, since it needs no separate classification-definition step.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*
