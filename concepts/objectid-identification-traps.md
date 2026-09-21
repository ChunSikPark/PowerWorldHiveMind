---
type: concept
domain: tooling
aliases: [objectid-traps, multi-section-line-identifier, three-winding-objectid, star-bus-identification]
tags: [powerworld, objectid, aux, multi-section-line, three-winding-transformer, identification]
---

# ObjectID identification traps: multi-section lines and 3-winding transformers

## Abstract

Two branch shapes need extra identifiers that a normal 3-field `ObjectID` doesn't carry, and
getting the field count wrong doesn't error — the parser accepts both the 3-field and
4-field shapes contextually, so a missing or extra identifier resolves to **the wrong
section or the wrong winding, silently**, with a plausible-looking row coming back. This
page exists to make that failure concrete and give the check to run before trusting an
ObjectID match.

## Connections

**Up:** [powerworld-script-transfer](powerworld-script-transfer.md) (ObjectID compact single-field syntax) ·
[aux-only-powerworld](aux-only-powerworld.md) (field-name provenance rule) ·
**Across:** [simauto-output-shapes-and-discovery](simauto-output-shapes-and-discovery.md) (raw field discovery) ·
[topology-consolidation-and-derived-status](topology-consolidation-and-derived-status.md)
(a different way an object's identity silently shifts — there it's `BusNum` moving under ITP
consolidation, here it's the wrong section/winding resolving from a malformed ObjectID) ·
[required-fields-for-object-creation](required-fields-for-object-creation.md) (a sibling
silent-failure gate on the write path — that one skips creating an object outright, this one
matches the wrong existing one) ·
**Deeper:** Simulator's *Auxiliary Files and Script Commands* manual chapter (Help menu)

## Content

### Resolution order, and what it can't do

`ObjectID` resolves against a fixed precedence: ObjectID string itself → Label → Primary
Keys → Secondary Keys. Loading by ObjectID or Label can never create a new object, only
match an existing one — relevant if `SetElseCreateData` or any `CreateIfNotFound`-driven
write is keyed off ObjectID/Label rather than raw primary keys, since that path will never
create the row it can't find.

### Multi-section lines need a 4th identifier

A normal branch has 3 identifiers — from bus, to bus, circuit ID:

```
BRANCH 23 29 'AB'
```

A branch that is part of a **multi-section line** needs a 4th identifier, the section
number, appended at the end:

```
BRANCH 23 29 'AB' 4
```

**The trap:** using 3 identifiers when the branch needs 4 (or the reverse) does not error —
the parser accepts both shapes contextually and resolves to the wrong section rather than
refusing the match. A `LineShunt` attached to a branch inside a multi-section line follows
the same pattern one level up: 6 identifiers instead of the normal 5 (from bus, to bus,
terminal bus, circuit ID, shunt ID, + section ID appended last), e.g.
`LineShunt 40489 40687 40489 2 A 6`. The terminal-bus field (3rd) must be the bus on the same
side as the shunt.

### Three-winding transformer windings: two identification schemes

A winding of a three-winding transformer can be named two ways:

- **Legacy star-bus form** — `BRANCH 10001 10004 'AB'` — where `10001`/`10004` are the
  internal star-bus number and one terminal bus. **Not portable**: PSS/E RAW files don't
  persist star-bus numbers across a load, and PowerWorld can renumber star buses on every
  RAW read according to its NEAR/MAX/VALUE setting for star-bus numbering.
- **4-identifier terminal-bus form** — `BRANCH 10001 10002 10003 'AB'` — all three terminal
  buses plus circuit ID. The branch is interpreted as the winding at the *first* listed
  terminal bus; the order of the 2nd and 3rd bus numbers doesn't matter.

Prefer the 4-identifier form for anything that must survive a PTI RAW round-trip, since the
star-bus numbers the legacy form depends on aren't stable across reads.

### FixedNumBus (Version 24+) changes what the integers mean

If a bus carries a FixedNumBus designation, an ObjectID's bus-number fields may be given as
FixedNumBus integers instead of live bus numbers — but if you do this, **every** integer in
that ObjectID string must be a FixedNumBus integer, not a mix of the two numbering schemes.
When writing an AUX file, FixedNumBus integers used to specify an object are also what gets
written back out, so a file already written this way stays self-consistent — but reading a
mixed-numbering ObjectID string is another way to silently resolve to the wrong object.

### Before trusting a match

Given the silent-wrong-match failure mode above, verify identity rather than assume it:
read the resolved row back and check its own key fields (from/to bus, circuit ID, and
section or star-bus number as applicable) against what you intended, rather than trusting
that a returned row belongs to the object you asked for.

---

*Distilled from the PowerWorld Simulator help corpus (pinned commit `e13a8aa`). Paraphrased; reproduces no manual text.*
