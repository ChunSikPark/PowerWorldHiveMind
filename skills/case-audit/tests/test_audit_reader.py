"""The reader against the stand-in esapp (tests/fake_esapp): no PowerWorld needed."""
import pytest

import reader


def _case(tmp_path, name="c.pwb"):
    p = tmp_path / name
    p.write_bytes(b"case")
    return p


def test_reads_every_object_and_exits(fake_esapp, monkeypatch, tmp_path):
    monkeypatch.setenv("PWHM_FAKE_EMPTY", "Gen")                 # Gen reads None, as zero rows do
    cd = reader.read_case(_case(tmp_path))
    assert fake_esapp.CALLS[-1] == ("exit",) and cd.solve.converged
    assert cd.get("Gen").empty and len(cd.get("Bus")) == 37
    assert cd.scalars["sha256_before"] == cd.scalars["sha256_after"] and cd.scalars["SBase"] == "100"
    assert [c for c in fake_esapp.CALLS if c[0] == "SolvePowerFlow"] == [("SolvePowerFlow", ())]


def test_a_solve_that_raises_is_recorded_not_retried(fake_esapp, monkeypatch, tmp_path):
    monkeypatch.setenv("PWHM_FAKE_SOLVE_ERROR", "RunScriptCommand: NR PowerFlow - Power flow unable to converge.\nmore")
    cd = reader.read_case(_case(tmp_path))
    assert fake_esapp.CALLS[-1] == ("exit",) and not cd.solve.converged
    assert cd.solve.raised == "RunScriptCommand: NR PowerFlow - Power flow unable to converge."
    assert sum(c[0] == "SolvePowerFlow" for c in fake_esapp.CALLS) == 1


def test_a_solve_crash_that_is_not_a_powerworld_error_propagates(fake_esapp, monkeypatch, tmp_path):
    monkeypatch.setenv("PWHM_FAKE_SOLVE_CRASH", "COM gone")
    with pytest.raises(RuntimeError, match="COM gone"):
        reader.read_case(_case(tmp_path))
    assert fake_esapp.CALLS[-1] == ("exit",)


def test_exit_runs_even_when_a_read_fails(fake_esapp, monkeypatch, tmp_path):
    monkeypatch.setenv("PWHM_FAKE_READ_ERROR", "COM gone")
    with pytest.raises(RuntimeError):
        reader.read_case(_case(tmp_path))
    assert fake_esapp.CALLS[-1] == ("exit",)


def test_a_failed_open_stops_only_the_server_it_started(fake_esapp, monkeypatch, tmp_path):
    monkeypatch.setenv("PWHM_FAKE_OPEN_ERROR", "SimAuto not registered")
    seen = iter([{101, 102}, {101, 102, 555}])
    killed = []
    monkeypatch.setattr(reader, "_tasklist", lambda: next(seen))
    monkeypatch.setattr(reader, "_taskkill", killed.append)
    with pytest.raises(reader.ReadError, match="could not open"):
        reader.read_case(_case(tmp_path))
    assert killed == [555]


def test_a_failed_listing_stops_nothing(fake_esapp, monkeypatch, tmp_path):
    monkeypatch.setenv("PWHM_FAKE_OPEN_ERROR", "SimAuto not registered")
    seen = iter([None, {1, 2}])                                  # the listing before the open failed
    killed = []
    monkeypatch.setattr(reader, "_tasklist", lambda: next(seen))
    monkeypatch.setattr(reader, "_taskkill", killed.append)
    with pytest.raises(reader.ReadError, match="could not be listed, so none was stopped"):
        reader.read_case(_case(tmp_path))
    assert killed == []
    assert reader.kill_new_servers({1}, lister=lambda: None, killer=killed.append) is None and killed == []


def test_kill_new_servers_leaves_older_ones_alone():
    killed = []
    assert reader.kill_new_servers({1, 2}, lister=lambda: {1, 2, 3, 9}, killer=killed.append) == [3, 9]
    assert killed == [3, 9]


def test_missing_case_is_a_read_error(tmp_path):
    with pytest.raises(reader.ReadError, match="case not found"):
        reader.read_case(tmp_path / "nope.pwb")


def test_variants_are_found_by_name_not_by_listing(tmp_path):
    for n in ("grid.pwb", "grid_PFW.pwb", "grid_old.pwb", "gridlock.pwb"):
        (tmp_path / n).write_bytes(b"x")
    assert reader.variants_beside(tmp_path / "grid.pwb") == ["grid_PFW.pwb"]
    assert reader.variants_beside(tmp_path / "grid_PFW.pwb") == ["grid.pwb"]
    assert reader.variants_beside(tmp_path / "gridlock.pwb") == []
