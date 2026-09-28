# Schema-librarian (Plan 1 of 4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the kit's first agent — a read-only "reference desk" that answers "which PowerWorld object, field or command, and how sure?" — plus the two stale-page fixes the later agents build on.

**Architecture:** A pure-Python lookup engine over the Simulator 25 field export (`openpyxl`, gzip-JSON cache, no PowerWorld needed), a provenance reader over the curated hub page, and a CLI. A skill (`skills/schema-lookup/SKILL.md`) carries the procedure so every harness can use it; a thin Claude Code agent (`agents/schema-librarian.md`) runs that skill in a fresh context on a cheap model.

**Tech Stack:** Python 3.11+, openpyxl, pytest. No esapp, no PowerWorld.

**Spec:** `docs/superpowers/specs/2026-09-28-power-system-agents-design.md` (§3 team, §7 schema-librarian, §10 librarian test row, §11 build order steps 0–1, §13 plugin-agent discovery question).

**Plans 2–4** (case-auditor, study-runner, fix-reviewer) are written after this plan ships; each is independently testable.

## Global Constraints

- Everything ships inside the kit and is self-contained: no imports from any private research repository.
- Worked examples and tests use public data only; the field export is PowerWorld schema, not case data.
- The librarian never opens or writes a case, and never states a field name absent from the export.
- Answer confidence is one of: `verified` / `documented` / `schema-only` / `unverified` / `not-in-export`.
- Every role is a skill plus an engine first; the agent file is a thin wrapper that runs the skill.
- Commit messages carry no AI attribution lines.
- Never `cd` inside a compound shell command; run everything from the repository root.

## Review Focus

1. **Windows console encoding.** Descriptions contain non-ASCII (e.g. `≥` in `Substation.NERCCIP14AggWeight`); a default cp1252 console crashes on print. Expect clean UTF-8 output. → Task 6 test `test_cli_survives_cp1252_console`.
2. **Case-insensitive and misspelled object names** (`ctg_options`, `Shunts`). Expect resolution or a "did you mean" list, never a stack trace. → Task 3 tests `test_resolve_object_case_insensitive`, `test_unknown_object_suggests`.
3. **Colon fields in three spellings** (`MaxItr:1`, Python's `MaxItr__1`, concise `MaxItrVoltLoop`). Expect all three to find the same field. → Task 3 test `test_find_field_colon_python_and_concise_forms`.
4. **Export missing or renamed** (user deleted it, or a v26 export lands under another name). Expect a message naming the path, exit code 2. → Task 2 test `test_missing_export_names_the_path`, Task 6 test `test_cli_missing_export_exit_2`.
5. **Stale cache after the export is replaced** with a newer Simulator build. Expect the cache to be rebuilt, not the old fields served. → Task 2 test `test_cache_rebuilt_when_export_changes`.

---

## File Structure

| file | responsibility |
|---|---|
| `concepts/parallel-contingency-solve.md` (modify) | gain the rule to `.exit()` instances you own |
| `methods/reading-violationctg.md` (modify) | replace "islanding is undetectable" with the three-check picture |
| `skills/schema-lookup/engine/schema.py` | load the export (with cache); resolve objects; keys, required, find field, search |
| `skills/schema-lookup/engine/provenance.py` | read confidence tags for a field from the hub page |
| `skills/schema-lookup/engine/lookup.py` | CLI: `object`, `field`, `search` subcommands |
| `skills/schema-lookup/tests/conftest.py` | put `engine/` on `sys.path`; session-scoped loaded fields |
| `skills/schema-lookup/tests/test_schema.py` | loader, cache, lookups, search |
| `skills/schema-lookup/tests/test_provenance.py` | confidence tags against the real hub page |
| `skills/schema-lookup/tests/test_lookup_cli.py` | CLI end to end via subprocess |
| `skills/schema-lookup/SKILL.md` | the procedure any harness follows |
| `agents/schema-librarian.md` | Claude Code agent: runs the skill, haiku, read-only tools |
| `.gitignore` (modify) | ignore `skills/*/engine/.cache/` |
| `README.md` (modify) | list the new skill and agent on the plugin route |
| `AGENTS.md` (modify) | routing row for "which object / field / command" |

---

### Task 1: Sync the two stale kit pages

**Files:**
- Modify: `concepts/parallel-contingency-solve.md` (paragraph ending "so that's a non-issue.", ~line 72)
- Modify: `methods/reading-violationctg.md` (paragraph "**So the correct pairing is …**", ~line 262)

**Interfaces:**
- Consumes: nothing.
- Produces: page text that Plan 3 (study-runner) cites for worker cleanup and island detection.

- [ ] **Step 1: Confirm both stale statements are present**

Run: `grep -n "so that's a non-issue" concepts/parallel-contingency-solve.md; grep -n "So the correct pairing is" methods/reading-violationctg.md`
Expected: one hit in each file.

- [ ] **Step 2: Add the owned-instance rule to `concepts/parallel-contingency-solve.md`**

Insert this paragraph immediately after the paragraph that ends `process lifetime, so that's a non-issue.`:

```markdown
**The rule cuts the other way for an instance you own and reopen in a loop.** A worker that opens a
fresh case per candidate — the pattern a measurement harness uses so no tap or shunt state carries
between candidates — must call `.exit()` on **its own** instance before the next open. Dropping the
Python reference (`del pw`) does not release the COM server: measured 2026-09-28, each open left one
`pwrworld.exe` of ~1 GB running, and a run of four workers reached sixteen stray servers in a few
minutes, starving the other sweep on the machine. So: never `.exit()` a shared instance; always
`.exit()` one you opened and are done with. Killing the Python process eventually frees them too, but
only once COM notices the client is gone.
```

Also, in `## Connections` (~line 34), replace the line

```markdown
  instances concurrently, the real rule is just "never call `.exit()`")
```

with

```markdown
  instances concurrently; the rule is never `.exit()` a shared instance, always `.exit()` one you own)
```

- [ ] **Step 3: Replace the islanding conclusion in `methods/reading-violationctg.md`**

Replace the two lines

```markdown
**So the correct pairing is: `CTGSolveAll` for the violations, the LODF denominator for the
islanding list.** Neither one covers the other.
```

with:

```markdown
**Correction (2026-09-24, completed 2026-09-28): islanding *is* visible after `CTGSolveAll` —
through three checks that each catch a different set, and no single one catches all.**

- **`Contingency.LoadMW` / `GenMW`** hold the load and generation cut off by each outage and are
  non-zero only on islanding outages — these are islands PowerWorld **drops**. Checked against a
  direct `CTGApply` plus re-solve of every outage on a public 40-bus synthetic case (93 of 93
  agreed). A generation-only pocket reads `LoadMW = 0`; catch it through `GenMW`.
- **`CTG_Options.Include`** (concise `IslandViolations`) = YES, with `BGLoadMW` and
  `IslandTotalBus` as minimum-size filters and `Sim_Solution_Options.EvalSolutionIsland` = YES as
  its prerequisite, reports *Island Solved* rows for self-sustaining pockets PowerWorld keeps
  **energized** — exactly the ones where `LoadMW` / `GenMW` read 0.
- **`DetermineBranchesThatCreateIslands`** (script) is the structural check: it finds both kinds
  plus 0-MW pockets whose generation is offline.

Measured 2026-09-28 on a regional synthetic planning model. Gate an island check on MW only when
the stranded pocket carries MW. The LODF denominator above remains the solve-free screen.
`ViolationCTG` alone still ranks every one of these outages harmless — read the island checks
alongside it.
```

- [ ] **Step 4: Verify the stale text is gone and links still resolve**

Run: `grep -c "So the correct pairing is" methods/reading-violationctg.md`
Expected: `0`

Run: `python -c "import pathlib,re;R=pathlib.Path('.');print([f'{p}: {t}' for d in ('concepts','methods','demos','references') for p in (R/d).glob('*.md') for t in set(re.findall(r'\]\(([^)#]+\.md)',p.read_text(encoding='utf-8-sig'))) if not (p.parent/t).exists()] or 'no dangling links')"`
Expected: `no dangling links`

- [ ] **Step 5: Rebuild dist and commit**

```bash
python build_dist.py
git add concepts/parallel-contingency-solve.md methods/reading-violationctg.md dist/
git commit -m "Sync two stale pages: exit owned instances, islanding is detectable"
```

---

### Task 2: Field loader with cache

**Files:**
- Create: `skills/schema-lookup/engine/schema.py`
- Create: `skills/schema-lookup/tests/conftest.py`
- Create: `skills/schema-lookup/tests/test_schema.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `references/powerworld-object-fields-v25.xlsx` (sheet `ObjectFields`; columns 0 Object Type, 2 Key/Required, 3 Variable Name, 4 Concise, 5 Type, 6 Description, 7 Available Field List, 8 Enterable).
- Produces: `Field` dataclass (`object, variable, concise, type, description, dialog_path, enterable, marker`; properties `key_index: int | None`, `is_alternate_key: bool`, `is_required: bool`); `SchemaError`; `load_fields(xlsx=DEFAULT_XLSX) -> dict[str, list[Field]]`; module constants `KIT_ROOT`, `DEFAULT_XLSX`, `CACHE_DIR`, `_MEMO`.

- [ ] **Step 1: Write conftest and the failing loader tests**

`skills/schema-lookup/tests/conftest.py`:

```python
import sys
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parents[1] / "engine"
sys.path.insert(0, str(ENGINE))


@pytest.fixture(scope="session")
def fields():
    import schema
    return schema.load_fields()
```

`skills/schema-lookup/tests/test_schema.py`:

```python
import os
import shutil

import pytest

import schema


def test_export_loads_all_objects(fields):
    assert len(fields) > 1000
    assert "Shunt" in fields and "CTG_Options" in fields


def test_field_record_shape(fields):
    by_var = {f.variable: f for f in fields["Sim_Solution_Options"]}
    f = by_var["DCPFMode"]
    assert f.concise == "DCApprox"
    assert f.enterable == "Yes"
    assert f.dialog_path.startswith("DC Approximation")


def test_key_and_required_markers(fields):
    by_var = {f.variable: f for f in fields["Shunt"]}
    assert by_var["BusNum"].key_index == 1
    assert by_var["ShuntID"].key_index == 2
    assert by_var["SSCMode"].is_required
    assert by_var["BusName_NomVolt"].is_alternate_key
    assert by_var["AreaNum:1"].enterable == "read-only"


def test_missing_export_names_the_path(tmp_path):
    missing = tmp_path / "nope.xlsx"
    with pytest.raises(schema.SchemaError, match="nope.xlsx"):
        schema.load_fields(missing)


def test_cache_rebuilt_when_export_changes(tmp_path, monkeypatch):
    src = tmp_path / "fields.xlsx"
    shutil.copy(schema.DEFAULT_XLSX, src)
    monkeypatch.setattr(schema, "CACHE_DIR", tmp_path / "cache")
    schema._MEMO.clear()

    first = schema.load_fields(src)
    assert list((tmp_path / "cache").glob("*.json.gz")), "cache file not written"

    schema._MEMO.clear()
    monkeypatch.setattr(schema, "_read_xlsx", lambda p: pytest.fail("cache not used"))
    assert schema.load_fields(src).keys() == first.keys()

    st = src.stat()
    os.utime(src, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))
    schema._MEMO.clear()
    calls = []
    monkeypatch.setattr(schema, "_read_xlsx", lambda p: calls.append(p) or {"X": []})
    assert schema.load_fields(src) == {"X": []}
    assert calls, "changed export was served from the stale cache"
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest skills/schema-lookup/tests/test_schema.py -v`
Expected: collection error `ModuleNotFoundError: No module named 'schema'`.

- [ ] **Step 3: Implement the loader**

`skills/schema-lookup/engine/schema.py`:

```python
"""Field lookup over PowerWorld's case-object field export (no PowerWorld needed)."""
from __future__ import annotations

import gzip
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_XLSX = KIT_ROOT / "references" / "powerworld-object-fields-v25.xlsx"
CACHE_DIR = Path(__file__).resolve().parent / ".cache"
_MEMO: dict[tuple, dict] = {}


class SchemaError(Exception):
    """The export is missing or a lookup cannot be answered."""


@dataclass(frozen=True)
class Field:
    object: str
    variable: str
    concise: str
    type: str
    description: str
    dialog_path: str
    enterable: str  # "Yes" | "AUX/Paste" | "read-only"
    marker: str     # raw Key/Required cell, "" if none

    @property
    def key_index(self) -> int | None:
        m = re.search(r"\*(\d)", self.marker)
        return int(m.group(1)) if m else None

    @property
    def is_alternate_key(self) -> bool:
        return "*A*" in self.marker

    @property
    def is_required(self) -> bool:
        return "**" in self.marker


def _s(v) -> str:
    if v is None:
        return ""
    return re.sub(r"\s+", " ", str(v)).strip().replace("�", "...")


def _read_xlsx(path: Path) -> dict[str, list[Field]]:
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True)
    objs: dict[str, list[Field]] = {}
    cur = None
    for row in wb.worksheets[0].iter_rows(min_row=2, values_only=True):
        r = tuple(row) + (None,) * (9 - len(row))
        if r[0]:
            cur = _s(r[0])
            objs[cur] = []
        elif r[3] and cur:
            objs[cur].append(Field(
                object=cur, variable=_s(r[3]), concise=_s(r[4]), type=_s(r[5]),
                description=_s(r[6]), dialog_path=_s(r[7]),
                enterable=_s(r[8]) or "read-only", marker=_s(r[2]),
            ))
    wb.close()
    return objs


def load_fields(xlsx: Path | str = DEFAULT_XLSX) -> dict[str, list[Field]]:
    """All objects and their fields. Cached on disk, keyed by the export's size and mtime."""
    xlsx = Path(xlsx)
    if not xlsx.is_file():
        raise SchemaError(
            f"Field export not found: {xlsx}. The kit ships it as "
            f"references/powerworld-object-fields-v25.xlsx; pass --xlsx to use another export."
        )
    st = xlsx.stat()
    key = (str(xlsx.resolve()), st.st_size, st.st_mtime_ns)
    if key in _MEMO:
        return _MEMO[key]
    cache = CACHE_DIR / f"{xlsx.stem}-{st.st_size}-{st.st_mtime_ns}.json.gz"
    if cache.is_file():
        raw = json.loads(gzip.decompress(cache.read_bytes()))
        objs = {o: [Field(**f) for f in fs] for o, fs in raw.items()}
    else:
        objs = _read_xlsx(xlsx)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        payload = {o: [asdict(f) for f in fs] for o, fs in objs.items()}
        cache.write_bytes(gzip.compress(json.dumps(payload).encode("utf-8")))
    _MEMO[key] = objs
    return objs
```

Append to `.gitignore`:

```
# schema-lookup engine: rebuilt from the field export on first use
skills/*/engine/.cache/
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest skills/schema-lookup/tests/test_schema.py -v`
Expected: 5 passed. The first run reads the xlsx (tens of seconds); later runs hit the cache.

- [ ] **Step 5: Commit**

```bash
git add skills/schema-lookup/engine/schema.py skills/schema-lookup/tests/conftest.py skills/schema-lookup/tests/test_schema.py .gitignore
git commit -m "Add the schema-lookup field loader with an export-keyed cache"
```

---

### Task 3: Object and field lookups

**Files:**
- Modify: `skills/schema-lookup/engine/schema.py` (append)
- Modify: `skills/schema-lookup/tests/test_schema.py` (append)

**Interfaces:**
- Consumes: `load_fields`, `Field`, `SchemaError` from Task 2.
- Produces: `UnknownObject(SchemaError)` with `.name` and `.suggestions: list[str]`; `resolve_object(name, fields=None) -> str`; `object_fields(name, fields=None) -> list[Field]`; `keys(name, fields=None) -> list[Field]` (ordered by key index); `alternate_keys(name, fields=None) -> list[Field]`; `required(name, fields=None) -> list[Field]`; `normalize_field_name(name) -> str`; `find_field(obj, name, fields=None) -> Field | None`; `close_field_names(obj, name, fields=None) -> list[str]`.

- [ ] **Step 1: Write the failing tests** (append to `test_schema.py`)

```python
def test_shunt_keys_required_and_area_fields(fields):
    assert [f.variable for f in schema.keys("Shunt", fields)] == ["BusNum", "ShuntID"]
    req = {f.variable for f in schema.required("Shunt", fields)}
    assert {"SSCMode", "SSNMVR", "SSStatus"} <= req
    own = schema.find_field("Shunt", "AreaNum", fields)
    bus = schema.find_field("Shunt", "AreaNum:1", fields)
    assert own.enterable == "Yes" and "of Shunt" in own.dialog_path
    assert bus.enterable == "read-only" and "of Bus" in bus.dialog_path


def test_resolve_object_case_insensitive(fields):
    assert schema.resolve_object("ctg_options", fields) == "CTG_Options"


def test_unknown_object_suggests(fields):
    with pytest.raises(schema.UnknownObject) as e:
        schema.resolve_object("Shunts", fields)
    assert "Shunt" in e.value.suggestions
    assert "Shunt" in str(e.value)


def test_find_field_colon_python_and_concise_forms(fields):
    a = schema.find_field("Sim_Solution_Options", "MaxItr:1", fields)
    b = schema.find_field("Sim_Solution_Options", "MaxItr__1", fields)
    c = schema.find_field("Sim_Solution_Options", "MaxItrVoltLoop", fields)
    assert a is not None and a == b == c
    assert a.variable == "MaxItr:1"


def test_concise_name_is_the_same_field(fields):
    assert schema.find_field("Sim_Solution_Options", "DCApprox", fields).variable == "DCPFMode"


def test_absent_field_returns_none_with_close_names(fields):
    assert schema.find_field("OPF_Options", "SCOPFMaxInnerLoopItr", fields) is None
    assert "SCOPFMaxOuterLoopItr" in schema.close_field_names("OPF_Options", "SCOPFMaxInnerLoopItr", fields)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest skills/schema-lookup/tests/test_schema.py -v`
Expected: the six new tests FAIL with `AttributeError: module 'schema' has no attribute 'keys'` (or `resolve_object` / `find_field`).

- [ ] **Step 3: Implement** (append to `schema.py`)

```python
import difflib


class UnknownObject(SchemaError):
    def __init__(self, name: str, suggestions: list[str]):
        self.name = name
        self.suggestions = suggestions
        hint = f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""
        super().__init__(f"No object type {name!r} in the field export.{hint}")


def resolve_object(name: str, fields: dict | None = None) -> str:
    fields = fields if fields is not None else load_fields()
    if name in fields:
        return name
    lower = {o.lower(): o for o in fields}
    if name.lower() in lower:
        return lower[name.lower()]
    near = difflib.get_close_matches(name.lower(), list(lower), n=3, cutoff=0.6)
    raise UnknownObject(name, [lower[n] for n in near])


def object_fields(name: str, fields: dict | None = None) -> list[Field]:
    fields = fields if fields is not None else load_fields()
    return fields[resolve_object(name, fields)]


def keys(name: str, fields: dict | None = None) -> list[Field]:
    return sorted((f for f in object_fields(name, fields) if f.key_index), key=lambda f: f.key_index)


def alternate_keys(name: str, fields: dict | None = None) -> list[Field]:
    return [f for f in object_fields(name, fields) if f.is_alternate_key]


def required(name: str, fields: dict | None = None) -> list[Field]:
    return [f for f in object_fields(name, fields) if f.is_required]


def normalize_field_name(name: str) -> str:
    """Accept the Python attribute spelling: MaxItr__1 -> MaxItr:1."""
    return re.sub(r"__(\d+)$", r":\1", name.strip())


def find_field(obj: str, name: str, fields: dict | None = None) -> Field | None:
    """Match on variable name first, then concise name, case-insensitively."""
    want = normalize_field_name(name).lower()
    fs = object_fields(obj, fields)
    for f in fs:
        if f.variable.lower() == want:
            return f
    for f in fs:
        if f.concise and f.concise.lower() == want:
            return f
    return None


def close_field_names(obj: str, name: str, fields: dict | None = None) -> list[str]:
    names = [f.variable for f in object_fields(obj, fields)]
    return difflib.get_close_matches(normalize_field_name(name), names, n=3, cutoff=0.6)
```

Move `import difflib` up into the import block at the top of the file.

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest skills/schema-lookup/tests/test_schema.py -v`
Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/schema-lookup/engine/schema.py skills/schema-lookup/tests/test_schema.py
git commit -m "Add object and field lookups: keys, required, concise and colon names"
```

---

### Task 4: Search across the export

**Files:**
- Modify: `skills/schema-lookup/engine/schema.py` (append)
- Modify: `skills/schema-lookup/tests/test_schema.py` (append)

**Interfaces:**
- Consumes: `load_fields`, `object_fields`, `Field`.
- Produces: `search(query: str, obj: str | None = None, limit: int = 20, fields=None) -> list[Field]` — ranked by number of query terms matched anywhere (names, dialog path, description), then by terms matched in the names, then object and variable name.

- [ ] **Step 1: Write the failing tests** (append)

```python
def test_search_finds_island_reporting(fields):
    top = [f.variable for f in schema.search("island violations", obj="CTG_Options", fields=fields)[:3]]
    assert "Include" in top


def test_search_across_all_objects_respects_limit(fields):
    hits = schema.search("voltage", limit=7, fields=fields)
    assert len(hits) == 7
    assert len({f.object for f in schema.search("voltage", limit=50, fields=fields)}) > 1


def test_search_empty_query_returns_nothing(fields):
    assert schema.search("  ", fields=fields) == []


def test_there_is_no_scopf_inner_loop_field(fields):
    names = [f.variable for f in schema.object_fields("OPF_Options", fields)]
    assert "SCOPFMaxOuterLoopItr" in names
    assert not [n for n in names if re.search(r"scopf.*inner", n, re.I)]
```

Add `import re` to the imports of `test_schema.py`.

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest skills/schema-lookup/tests/test_schema.py -v`
Expected: three search tests FAIL with `AttributeError: module 'schema' has no attribute 'search'`; `test_there_is_no_scopf_inner_loop_field` passes already (it pins a fact of the export).

- [ ] **Step 3: Implement** (append to `schema.py`)

```python
def search(query: str, obj: str | None = None, limit: int = 20,
           fields: dict | None = None) -> list[Field]:
    terms = [t for t in re.split(r"\W+", query.lower()) if t]
    if not terms:
        return []
    fields = fields if fields is not None else load_fields()
    pool = object_fields(obj, fields) if obj else [f for fs in fields.values() for f in fs]
    scored = []
    for f in pool:
        names = f"{f.variable} {f.concise}".lower()
        text = f"{names} {f.dialog_path} {f.description}".lower()
        hits = sum(t in text for t in terms)
        if hits:
            scored.append((-hits, -sum(t in names for t in terms), f.object, f.variable, f))
    scored.sort(key=lambda s: s[:4])
    return [s[4] for s in scored[:limit]]
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest skills/schema-lookup/tests/test_schema.py -v`
Expected: 15 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/schema-lookup/engine/schema.py skills/schema-lookup/tests/test_schema.py
git commit -m "Add ranked search across the field export"
```

---

### Task 5: Confidence tags from the hub page

**Files:**
- Create: `skills/schema-lookup/engine/provenance.py`
- Create: `skills/schema-lookup/tests/test_provenance.py`

**Interfaces:**
- Consumes: `find_field`, `Field`, `KIT_ROOT` from `schema`; the tables in `references/powerworld-study-options.md`, whose last column is a tag starting `V`, `D`, `S` or `not verified`.
- Produces: `Provenance` dataclass (`level: str`, `tag: str`, `source: str`); `provenance(obj, field_name, fields=None, hub=HUB) -> Provenance`. `level` ∈ `verified | documented | schema-only | unverified | not-in-export`; `source` ∈ `hub | export | ""`.

- [ ] **Step 1: Write the failing tests**

`skills/schema-lookup/tests/test_provenance.py`:

```python
from provenance import _first_field, provenance


def test_verified_from_hub(fields):
    p = provenance("CTG_Options", "CTG_WhatToDoWithBC", fields)
    assert (p.level, p.source) == ("verified", "hub")


def test_documented_dotted_row(fields):
    p = provenance("CTG_Options", "Include", fields)
    assert p.level == "documented"
    assert p.tag.startswith("D")


def test_verified_trap(fields):
    assert provenance("Sim_Solution_Options", "MinVoltSLoad", fields).level == "verified"


def test_schema_only_from_hub(fields):
    assert provenance("Sim_Solution_Options", "MaxItr", fields).level == "schema-only"


def test_object_disambiguates_same_field_name(fields):
    assert provenance("Area", "BGAGC", fields).level == "verified"
    assert provenance("SuperArea", "BGAGC", fields).level == "schema-only"


def test_field_only_in_export(fields):
    p = provenance("PVCurve_Options", _first_field("PVCurve_Options", fields), fields)
    assert (p.level, p.source) == ("schema-only", "export")


def test_not_in_export(fields):
    assert provenance("OPF_Options", "SCOPFMaxInnerLoopItr", fields).level == "not-in-export"
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest skills/schema-lookup/tests/test_provenance.py -v`
Expected: collection error `ModuleNotFoundError: No module named 'provenance'`.

- [ ] **Step 3: Implement**

`skills/schema-lookup/engine/provenance.py`:

```python
"""Confidence for a field: the hub page's curated tag if it has one, else the export's word."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from schema import KIT_ROOT, find_field, object_fields

HUB = KIT_ROOT / "references" / "powerworld-study-options.md"
_TAG = re.compile(r"^(V|D|S|not verified)\b")
_LEVEL = {"V": "verified", "D": "documented", "S": "schema-only", "not verified": "unverified"}


@dataclass(frozen=True)
class Provenance:
    level: str   # verified | documented | schema-only | unverified | not-in-export
    tag: str     # the hub's raw tag cell, "" if none
    source: str  # hub | export | ""


def _rows(hub: Path) -> list[list[str]]:
    rows = []
    for line in hub.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or re.match(r"^\|[\s|:-]+\|$", line):
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line)[1:-1]]
        if len(cells) >= 3 and _TAG.match(cells[-1]):
            rows.append(cells)
    return rows


def _tokens(text: str) -> list[str]:
    """Backticked names, reduced to their first word before any '='."""
    out = []
    for t in re.findall(r"`([^`]+)`", text):
        words = t.split()
        if words:
            out.append(words[0].split("=")[0])
    return out


def _score(cells: list[str], obj: str, names: set[str]) -> int:
    body = " | ".join(cells[:-1])
    best = 0
    for tok in _tokens(body):
        if "." in tok:
            o, fld = tok.split(".", 1)
            if o.lower() == obj.lower() and fld in names:
                best = max(best, 3)
        elif tok in names:
            best = max(best, 2 if obj.lower() in body.lower() else 1)
    return best


def provenance(obj: str, field_name: str, fields: dict | None = None, hub: Path = HUB) -> Provenance:
    f = find_field(obj, field_name, fields)
    if f is None:
        return Provenance("not-in-export", "", "")
    names = {n for n in (f.variable, f.concise) if n}
    scored = [(_score(c, f.object, names), c[-1]) for c in _rows(hub)]
    scored = [s for s in scored if s[0]]
    if not scored:
        return Provenance("schema-only", "", "export")
    tag = max(scored, key=lambda s: s[0])[1]
    return Provenance(_LEVEL[_TAG.match(tag).group(1)], tag, "hub")


def _first_field(obj: str, fields: dict | None = None) -> str:
    """Test helper: a field of `obj` that the hub never mentions."""
    text = HUB.read_text(encoding="utf-8")
    for f in object_fields(obj, fields):
        if f.variable not in text:
            return f.variable
    raise LookupError(obj)
```

Note on `_tokens`: a token such as `` `Area.BGAGC = "OPF"` `` reduces to `Area.BGAGC`; `` `MaxItr:1` `` stays `MaxItr:1`, so `MaxItr` and `MaxItr:1` stay distinct. Only rows whose last cell is a tag (`V…`, `D…`, `S…`, `not verified`) are read, so the "every study at a glance" table, whose last column holds commands, is ignored.

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest skills/schema-lookup/tests/test_provenance.py -v`
Expected: 7 passed.

If `test_object_disambiguates_same_field_name` fails, print `_rows(HUB)` rows containing `BGAGC` and check the `Area` row's token reduces to `Area.BGAGC` — fix `_tokens`, not the test.

- [ ] **Step 5: Commit**

```bash
git add skills/schema-lookup/engine/provenance.py skills/schema-lookup/tests/test_provenance.py
git commit -m "Add confidence tags for fields from the study-options hub"
```

---

### Task 6: The lookup CLI

**Files:**
- Create: `skills/schema-lookup/engine/lookup.py`
- Create: `skills/schema-lookup/tests/test_lookup_cli.py`

**Interfaces:**
- Consumes: everything in `schema` and `provenance`.
- Produces: `python skills/schema-lookup/engine/lookup.py [--xlsx PATH] object <Obj>` | `field <Obj> <Field>` | `search <query> [--object Obj] [--limit N]`. Exit 0 on an answer, 1 when the field is absent from the export, 2 on an unknown object or missing export. `main(argv: list[str] | None = None) -> int`.

- [ ] **Step 1: Write the failing tests**

`skills/schema-lookup/tests/test_lookup_cli.py`:

```python
import os
import subprocess
import sys
from pathlib import Path

LOOKUP = Path(__file__).resolve().parents[1] / "engine" / "lookup.py"


def run(*args, env_extra=None):
    env = {**os.environ, **(env_extra or {})}
    p = subprocess.run([sys.executable, str(LOOKUP), *args], capture_output=True, env=env)
    return p.returncode, p.stdout.decode("utf-8"), p.stderr.decode("utf-8", "replace")


def test_object_lists_keys_and_required():
    code, out, _ = run("object", "Shunt")
    assert code == 0
    assert "keys (in order): BusNum, ShuntID" in out
    assert "SSCMode" in out and "SSNMVR" in out and "SSStatus" in out


def test_field_reports_confidence_and_concise():
    code, out, _ = run("field", "Sim_Solution_Options", "DCApprox")
    assert code == 0
    assert "Sim_Solution_Options.DCPFMode" in out and "DCApprox" in out
    assert "confidence:" in out


def test_field_absent_exit_1_with_suggestions():
    code, out, _ = run("field", "OPF_Options", "SCOPFMaxInnerLoopItr")
    assert code == 1
    assert "SCOPFMaxOuterLoopItr" in out


def test_unknown_object_exit_2():
    code, _, err = run("object", "Shunts")
    assert code == 2 and "Did you mean" in err


def test_search_prints_one_line_per_hit():
    code, out, _ = run("search", "island violations", "--object", "CTG_Options", "--limit", "3")
    assert code == 0
    assert len([l for l in out.splitlines() if l.startswith("- ")]) == 3


def test_cli_missing_export_exit_2(tmp_path):
    code, _, err = run("--xlsx", str(tmp_path / "gone.xlsx"), "object", "Shunt")
    assert code == 2 and "gone.xlsx" in err


def test_cli_survives_cp1252_console():
    code, out, _ = run("field", "Substation", "NERCCIP14AggWeight", env_extra={"PYTHONIOENCODING": "cp1252"})
    assert code == 0
    assert "≥" in out
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest skills/schema-lookup/tests/test_lookup_cli.py -v`
Expected: all 7 FAIL (non-zero exit / `can't open file ... lookup.py`).

- [ ] **Step 3: Implement**

`skills/schema-lookup/engine/lookup.py`:

```python
"""Which PowerWorld object, field or command — from the field export and the study-options hub.

    python lookup.py object Shunt
    python lookup.py field CTG_Options Include
    python lookup.py search "island violations" --object CTG_Options --limit 5
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import schema  # noqa: E402
from provenance import provenance  # noqa: E402


def _role(f: schema.Field) -> str:
    if f.key_index:
        return f"key {f.key_index}"
    if f.is_alternate_key:
        return "alternate key"
    if f.is_required:
        return "required to create"
    return "-"


def show_object(name: str, fields: dict) -> str:
    obj = schema.resolve_object(name, fields)
    fs = fields[obj]
    count = {e: sum(f.enterable == e for f in fs) for e in ("Yes", "AUX/Paste", "read-only")}
    return "\n".join([
        f"## {obj}  ({len(fs)} fields)",
        f"keys (in order): {', '.join(f.variable for f in schema.keys(obj, fields)) or 'none (single-record object)'}",
        f"alternate keys: {', '.join(f.variable for f in schema.alternate_keys(obj, fields)) or 'none'}",
        f"required to create: {', '.join(f.variable for f in schema.required(obj, fields)) or 'none'}",
        f"writable: {count['Yes']}   AUX/Paste only: {count['AUX/Paste']}   read-only: {count['read-only']}",
    ])


def show_field(obj: str, name: str, fields: dict) -> tuple[int, str]:
    obj = schema.resolve_object(obj, fields)
    f = schema.find_field(obj, name, fields)
    if f is None:
        near = schema.close_field_names(obj, name, fields)
        return 1, f"{obj} has no field {name!r} in the export. Closest: {', '.join(near) or 'none'}"
    p = provenance(obj, f.variable, fields)
    where = f"hub: {p.tag}" if p.source == "hub" else "field export only; behaviour not tested"
    concise = f"  (concise: {f.concise})" if f.concise and f.concise != f.variable else ""
    return 0, "\n".join([
        f"{obj}.{f.variable}{concise}",
        f"type: {f.type}   enterable: {f.enterable}   role: {_role(f)}",
        f"dialog: {f.dialog_path}",
        f"description: {f.description}",
        f"confidence: {p.level} ({where})",
    ])


def show_search(query: str, obj: str | None, limit: int, fields: dict) -> str:
    hits = schema.search(query, obj=obj, limit=limit, fields=fields)
    if not hits:
        return f"no field matches {query!r}"
    lines = []
    for f in hits:
        concise = f" ({f.concise})" if f.concise and f.concise != f.variable else ""
        lines.append(f"- {f.object}.{f.variable}{concise} [{f.enterable}] - {f.dialog_path}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--xlsx", default=str(schema.DEFAULT_XLSX), help="field export to read")
    sub = ap.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("object")
    o.add_argument("name")
    fl = sub.add_parser("field")
    fl.add_argument("object")
    fl.add_argument("name")
    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--object")
    s.add_argument("--limit", type=int, default=20)
    a = ap.parse_args(argv)
    try:
        fields = schema.load_fields(a.xlsx)
        if a.cmd == "object":
            print(show_object(a.name, fields))
            return 0
        if a.cmd == "field":
            code, text = show_field(a.object, a.name, fields)
            print(text)
            return code
        print(show_search(a.query, a.object, a.limit, fields))
        return 0
    except schema.SchemaError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the whole suite**

Run: `python -m pytest skills/schema-lookup/tests -v`
Expected: 29 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/schema-lookup/engine/lookup.py skills/schema-lookup/tests/test_lookup_cli.py
git commit -m "Add the schema-lookup CLI: object, field and search"
```

---

### Task 7: The skill, the agent, and registration

**Files:**
- Create: `skills/schema-lookup/SKILL.md`
- Create: `agents/schema-librarian.md`
- Modify: `README.md` (the "On the plugin route" paragraph, ~line 134)
- Modify: `AGENTS.md` (routing table, after the `violation-map` row, ~line 140)

**Interfaces:**
- Consumes: the CLI from Task 6; `references/powerworld-study-options.md`, `references/powerworld-study-commands.md`.
- Produces: skill `schema-lookup` and agent `schema-librarian`, which Plan 3's study-runner calls in its configure phase.

- [ ] **Step 1: Write the skill**

`skills/schema-lookup/SKILL.md`:

````markdown
---
name: schema-lookup
description: "Answer which PowerWorld object, field or SCRIPT command to use, and how sure that is. Use when the user asks which field holds something, what the key or required fields of an object are, how to set an option (iterations, island reporting, SCOPF loops, DC mode), what a field or concise name means, or whether a field exists at all - e.g. 'which parameter do I set for...', 'what fields does a shunt need', 'is there a setting for...'."
---

# Schema lookup

Answer from the kit's own sources, never from memory. PowerWorld has about 1,000 object types
and 100,000 fields; a guessed field name fails silently.

The kit root is `${CLAUDE_PLUGIN_ROOT}` when installed as a plugin, otherwise the directory
holding `AGENTS.md`. Every path below is relative to it.

## 1. Look it up

```
python skills/schema-lookup/engine/lookup.py object <Object>
python skills/schema-lookup/engine/lookup.py field <Object> <Field>
python skills/schema-lookup/engine/lookup.py search "<words>" [--object <Object>] [--limit 10]
```

- Don't know the object? `search` without `--object`, then `object` on the best hit.
- A field may be given by variable name (`DCPFMode`), concise name (`DCApprox`) or Python
  spelling (`MaxItr__1`); all resolve to one field.
- Exit 1 means the field is not in the export. Say so and give the closest real field the tool
  prints. **Never offer a field name the tool did not print.**

## 2. Check the curated pages

- `references/powerworld-study-options.md` — per study, which option and command, and the traps.
  If the field appears there, its trap applies to your answer.
- `references/powerworld-study-commands.md` — exact SCRIPT syntax, parameters and defaults.
  Read the "Surprises" section before recommending any command.

## 3. Answer in this shape

```
<Object>.<Field>  (concise: …)      type · enterable · role (key 1 / required / -)
what it does: <one line, from the description>
how to set it: SetData(<Object>, [<Field>], [<value>]);   — then read it back
confidence: verified | documented | schema-only | unverified | not in export
trap: <one line from the hub page, if any>
```

For "what do I need to create an X": give the keys in order and the required fields.

## Never

- Never open, solve or write a case — this is a lookup.
- Never state a field that the tool did not return.
- Never upgrade confidence: `schema-only` means the field exists and PowerWorld describes it,
  nothing more.
````

- [ ] **Step 2: Write the agent**

`agents/schema-librarian.md`:

```markdown
---
name: schema-librarian
description: "Read-only PowerWorld reference desk. Answers which object, field or SCRIPT command to use and how sure that is, from the kit's field export and study pages. Use for 'which field do I set for…', 'what does a shunt/area/contingency need', 'is there an option for…'. Never opens a case."
tools: Bash, Read, Grep, Glob
model: haiku
---

You are the schema librarian for the PowerWorldHiveMind kit.

Read `skills/schema-lookup/SKILL.md` under the kit root (`${CLAUDE_PLUGIN_ROOT}`, or the
directory holding `AGENTS.md`) and follow it exactly. It is the whole procedure.

Return only the answer block the skill defines — no search logs, no tool output dumps. If the
question names several fields, return one block per field. If nothing in the export matches,
say "not in the export" and give the closest real fields the tool printed.
```

- [ ] **Step 3: Register in README and AGENTS**

In `README.md`, change

```
Code loads `skills/powerworld/SKILL.md`, `skills/knowledge-base-page/SKILL.md` and
`skills/violation-map/SKILL.md`, and
```

to

```
Code loads `skills/powerworld/SKILL.md`, `skills/knowledge-base-page/SKILL.md`,
`skills/violation-map/SKILL.md` and `skills/schema-lookup/SKILL.md`, registers the
`schema-librarian` agent from `agents/`, and
```

In `AGENTS.md`, add after the `violation-map` row:

```
| Which object, field or command to use, and how sure | `python skills/schema-lookup/engine/lookup.py`, see [skills/schema-lookup/SKILL.md](skills/schema-lookup/SKILL.md) |
```

- [ ] **Step 4: Verify the skill's commands work as written**

Run: `python skills/schema-lookup/engine/lookup.py object Shunt`
Expected: `keys (in order): BusNum, ShuntID` and the three required fields.

Run: `python skills/schema-lookup/engine/lookup.py field CTG_Options IslandViolations`
Expected: `CTG_Options.Include  (concise: IslandViolations)` and `confidence: documented (hub: D, fires live)`.

Run: `python -m pytest skills/schema-lookup/tests -v`
Expected: 29 passed.

- [ ] **Step 5: Verify plugin agent discovery (spec §13 open question)**

This needs a human in Claude Code; it cannot be asserted from a test.

1. In a new Claude Code conversation on a machine with the kit installed as a plugin, run `/reload-plugins`.
2. Run `/agents`. Expected: `schema-librarian` listed under the plugin.
3. Ask: "Use the schema-librarian: which field turns on island reporting in contingency analysis?" Expected: an answer block naming `CTG_Options.Include` with confidence `documented`.

Record the result (listed or not, and the Claude Code version) in the commit message. If the agent is **not** discovered, stop and report — Plans 2–4 assume agents in `agents/` load, and the spec's layout must change first.

- [ ] **Step 6: Rebuild dist and commit**

```bash
python build_dist.py
git add skills/schema-lookup/SKILL.md agents/schema-librarian.md README.md AGENTS.md dist/
git commit -m "Add the schema-lookup skill and schema-librarian agent"
```

---

## Self-review record

- **Spec coverage:** §11 step 0 → Task 1; §7 sources/answer shape/confidence → Tasks 5–7; §7 "never states a field absent from the export" → Task 6 exit 1 plus SKILL rule; §10 librarian row (shunt keys, island reporting, SCOPF outer loops, no inner loop) → Tasks 3, 4, 6; §3 portability (skill first, thin agent) → Task 7; §13 plugin discovery → Task 7 Step 5.
- **Placeholders:** none.
- **Names across tasks:** `load_fields`, `resolve_object`, `object_fields`, `keys`, `alternate_keys`, `required`, `find_field`, `close_field_names`, `search`, `provenance`, `Provenance`, `SchemaError`, `UnknownObject` are defined once and used with the same signatures.
- **Review Focus:** all five lines have a named test in the owning task.
