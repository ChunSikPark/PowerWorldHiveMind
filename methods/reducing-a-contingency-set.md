---
type: method
domain: cross-cutting
aliases: [ctgskip, ctg-skip, reducing-the-ctg-set, contingency-subset, skip-column]
tags: [powerworld, contingency, ctg, esapp, simauto, n-1]
---

# Method: Reducing or partitioning a contingency set

## Abstract

`CTGSkip` and `Delete(Contingency, <filter>)` do two different jobs and are
routinely confused. **`CTGSkip` partitions a set without shrinking it** — every
contingency stays in the case and the skipped ones are simply not solved this
pass, which is how the parallel solver gives each worker a slice. **`Delete` with
a violation filter is the only thing that actually reduces the set**, and it is
destructive, so it needs a backup first. This page collects the mechanism, the
three places it is used, and the three silent failures around it; before this,
`CTGSkip` was mentioned on five pages and owned by none.

## Connections

- **Up:** [Home](../index.md) · contingency remediation
- **Across:** [parallel-contingency-solve](../concepts/parallel-contingency-solve.md) — the chunking use ·
  [new-device-contingency-aux](new-device-contingency-aux.md) — writing a subset to `.aux` ·
  [reading-violationctg](reading-violationctg.md) — where the violation columns the filter uses come from
- **Deeper:** reactive power planning backend · esa pp llm backend

## Content

### The two mechanisms, and which one you want

| you want | use | destructive? |
|---|---|---|
| solve part of the set now, keep all of it | `CTGSkip` = `YES` / `NO` | no |
| permanently drop contingencies that did nothing | `Delete(Contingency, "<filter>")` | **yes** |

**"Are you reducing the ctg set by setting SKIP to YES?"** — no. Setting
`CTGSkip="YES"` excludes a contingency from *this* `CTGSolveAll` and leaves it in
the case. The set is the same size afterwards. That is the right tool for
partitioning and the wrong tool for reduction.

### `CTGSkip` — partitioning

`CTGSkip` is a field on the `Contingency` object, per contingency. Write it with
`change_parameters_multiple_element_df`, and **keep the `Contingency` key field
in the DataFrame** or the write silently no-ops.

Three recorded uses:

1. **Parallel chunking** ([parallel-contingency-solve](../concepts/parallel-contingency-solve.md)). Split the existing
   `CTGLabel` set with `np.array_split`; each OS process sets `CTGSkip=NO` for
   only its own chunk's labels and `YES` for everything else, then runs a plain
   serial `CTGSolveAll`. The full set is intact in every worker's case; each just
   solves its slice.
2. **Reactivating everything** (reactive power planning backend). Read the
   `Contingency` key plus `CTGSkip`, set `CTGSkip="NO"` across the frame, write
   it back. This is the reset before a full sweep.
3. **Persisting a subset** ([new-device-contingency-aux](new-device-contingency-aux.md)). `CTGSkip` travels in
   the `.aux` alongside `CTGLabel`, so a saved subset remembers what was skipped.

### `Delete` — the actual reduction

To shrink the set to what actually violated, filter on the violation counts that
the previous solve wrote:

```
Delete(Contingency, "CTGNVoltViol = 0")    # drop those with no voltage violation
Delete(Contingency, "CTGNBranchViol = 0")  # drop those with no overload
Delete(Contingency, "CTGViol = 0")         # drop those with neither
EnterMode(RUN);
```

**One condition only. `AND` is not supported in this filter.** If you need both,
delete twice or use `CTGViol`.

**Back up first, because this is destructive:**

```
CTGWriteAuxUsingOptions("<path>", NO);   # save the full set
Delete(Contingency);                      # ... work ...
LoadAux("<path>");                        # restore
```

### Multi-round: full sweep, then violations only

The pattern of *"first round full CTG, later rounds only the ones that violated"*
is assembled from the two mechanisms above and is **not** a single built feature:

1. Solve the full set (partition with `CTGSkip` across processes if it is large).
2. Back up with `CTGWriteAuxUsingOptions`.
3. `Delete(Contingency, "CTGViol = 0")` — the survivors are the reduced set.
4. Re-solve the survivors each later round.
5. `LoadAux` the backup when a round needs the full set again.

Step 3 reads violation counts populated by step 1, so the ordering is not
optional. [parallel-contingency-solve](../concepts/parallel-contingency-solve.md) explicitly scopes *out* per-contingency
remediation walks that mutate state between rounds, so do not expect its parallel
helper to carry this loop for you.

### Three silent failures

- **An unquoted action string in a hand-written `.aux`.** Written bare as
  `BRANCH 1001 1064 1 OPEN` instead of quoted, a 691-contingency file loads as
  **one** contingency — and the load **reports success**. Always quote the action.
- **`SaveContingencies` is not a script command** ("Unknown script command"). Use
  `SaveData(<path>,AUX,Contingency,[CTGLabel,CTGSkip],[CTGElement],"",[],[],YES);`
  — the filter argument is a bare string and the sort lists must be bracketed.
- **A missing key field on the write-back.** `change_parameters_multiple_element_df`
  needs the object's key field present or the `CTGSkip` change does nothing and
  says nothing.

### Where the filter's columns come from

`CTGNVoltViol`, `CTGNBranchViol` and `CTGViol` are populated by the solve.
[reading-violationctg](reading-violationctg.md) covers reading per-contingency violations back;
`CTGSolved` and `CTGViol` are among the fields the contingency object exposes.

## Provenance

Every fact here was already recorded and is consolidated rather than derived:
the chunking scheme from [parallel-contingency-solve](../concepts/parallel-contingency-solve.md), the `.aux` shape and its
quoting trap from [new-device-contingency-aux](new-device-contingency-aux.md), the `Delete` filters, the
single-condition limit and the backup/restore pair from
reactive power planning backend, and the contingency field list from
esa pp llm backend.

Written 2026-09-07 because the A/B measurement found `CTGSkip` mentioned on five
pages and owned by none: asked *"are you reducing the ctg set as well by setting
the SKIP column to YES?"*, three independent agents each picked a **different**
wrong page. See 2026 09 07 librarian card fails its ab.
