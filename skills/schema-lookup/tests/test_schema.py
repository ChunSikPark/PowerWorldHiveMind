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


# ---- Task 3: lookups

def test_shunt_keys_required_and_area_fields(fields):
    assert [f.variable for f in schema.keys("Shunt", fields)] == ["BusNum", "ShuntID"]
    req = {f.variable for f in schema.required("Shunt", fields)}
    assert {"SSCMode", "SSNMVR", "SSStatus"} <= req
    own = schema.find_field("Shunt", "AreaNum", fields)
    bus = schema.find_field("Shunt", "AreaNum:1", fields)
    assert own.writable == "yes" and "of Shunt" in own.dialog_path
    assert bus.writable == "read-only" and "of Bus" in bus.dialog_path


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


def test_absent_field_returns_none(fields):
    assert schema.find_field("OPF_Options", "SCOPFMaxInnerLoopItr", fields) is None


def test_split_words():
    assert schema.split_words("SCOPFMaxInnerLoopItr") == ["scopf", "max", "inner", "loop", "itr"]
