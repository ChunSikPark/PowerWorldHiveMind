import os
import re
import shutil

import pytest

import schema


# ---- Task 2: loader and cache

def test_export_loads_all_objects(fields):
    assert len(fields) > 1000
    assert "Shunt" in fields and "CTG_Options" in fields


def test_field_record_shape(fields):
    by_var = {f.variable: f for f in fields["Sim_Solution_Options"]}
    f = by_var["DCPFMode"]
    assert f.concise == "DCApprox"
    assert f.writable == "yes"
    assert f.dialog_path.startswith("DC Approximation")


def test_key_and_required_markers(fields):
    by_var = {f.variable: f for f in fields["Shunt"]}
    assert by_var["BusNum"].key_index == 1
    assert by_var["ShuntID"].key_index == 2
    assert by_var["ShuntID"].marker.startswith("*2")
    assert by_var["SSCMode"].is_required
    assert by_var["BusName_NomVolt"].key_index is None


def test_writable_categories(fields):
    seen = {f.writable for fs in fields.values() for f in fs}
    assert {"yes", "aux-only", "depends", "read-only"} <= seen
    by_var = {f.variable: f for f in fields["Contingency"]}
    assert by_var["CTGSolutionOptions"].writable == "aux-only"


def test_missing_export_names_the_path(tmp_path):
    with pytest.raises(schema.SchemaError, match="nope.xlsx"):
        schema.load_fields(tmp_path / "nope.xlsx")


def test_missing_openpyxl_is_a_schema_error(tmp_path, monkeypatch):
    import builtins
    real_import = builtins.__import__

    def no_openpyxl(name, *a, **k):
        if name == "openpyxl":
            raise ImportError("no openpyxl")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", no_openpyxl)
    with pytest.raises(schema.SchemaError, match="pip install openpyxl"):
        schema._read_xlsx(tmp_path / "any.xlsx")


def test_cache_rebuilt_when_export_changes(tmp_path, monkeypatch):
    src = tmp_path / "fields.xlsx"
    shutil.copy(schema.DEFAULT_XLSX, src)
    monkeypatch.setattr(schema, "CACHE_DIR", tmp_path / "cache")
    schema._MEMO.clear()

    first = schema.load_fields(src)
    assert list((tmp_path / "cache").glob("v*.json.gz")), "cache file not written"

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


def test_corrupt_cache_falls_back_to_export(tmp_path, monkeypatch):
    src = tmp_path / "fields.xlsx"
    src.write_bytes(b"placeholder")
    monkeypatch.setattr(schema, "CACHE_DIR", tmp_path / "cache")
    schema._MEMO.clear()
    cache = schema._cache_path(src, src.stat())
    cache.parent.mkdir()
    cache.write_bytes(b"not gzip")
    monkeypatch.setattr(schema, "_read_xlsx", lambda p: {"Y": []})
    assert schema.load_fields(src) == {"Y": []}


def test_unwritable_cache_dir_still_answers(tmp_path, monkeypatch):
    src = tmp_path / "fields.xlsx"
    src.write_bytes(b"placeholder")
    blocker = tmp_path / "cache"
    blocker.write_text("a file where the cache directory should be")
    monkeypatch.setattr(schema, "CACHE_DIR", blocker)
    schema._MEMO.clear()
    monkeypatch.setattr(schema, "_read_xlsx", lambda p: {"Z": []})
    assert schema.load_fields(src) == {"Z": []}
