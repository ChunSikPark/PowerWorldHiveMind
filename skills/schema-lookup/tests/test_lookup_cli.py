import os
import subprocess
import sys
from pathlib import Path

LOOKUP = Path(__file__).resolve().parents[1] / "engine" / "lookup.py"


def run(*args, env_extra=None, cwd=None):
    env = {**os.environ, **(env_extra or {})}
    p = subprocess.run([sys.executable, str(LOOKUP), *args], capture_output=True, env=env, cwd=cwd)
    return p.returncode, p.stdout.decode("utf-8"), p.stderr.decode("utf-8", "replace")


def test_object_lists_keys_required_and_writability():
    code, out, _ = run("object", "Shunt")
    assert code == 0
    assert "keys (in order): BusNum, ShuntID" in out
    assert "SSCMode" in out and "SSNMVR" in out and "SSStatus" in out
    assert "read-only" in out


def test_field_prints_concise_marker_and_hub_rows():
    code, out, _ = run("field", "CTG_Options", "IslandViolations")
    assert code == 0
    assert "CTG_Options.Include  (concise: IslandViolations)" in out
    assert "[exact]" in out and "tag D, fires live" in out


def test_field_shows_decoy_verbatim():
    code, out, _ = run("field", "CTG_Options", "CTG_ReportMonitoredAreas")
    assert code == 0 and "decoy" in out


def test_field_not_on_hub_says_so():
    code, out, _ = run("field", "Substation", "NERCCIP14AggWeight")
    assert code == 0 and "field export only" in out


def test_absent_field_exit_1_points_at_the_real_answer():
    code, out, _ = run("field", "OPF_Options", "SCOPFMaxInnerLoopItr")
    assert code == 1
    assert "not substitutes" in out
    assert "OPF_MaxLPIterations" in out


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


def test_cli_runs_from_outside_the_kit(tmp_path):
    code, out, _ = run("object", "Shunt", cwd=tmp_path)
    assert code == 0 and "BusNum" in out


def test_cli_corrupt_export_exit_2(tmp_path):
    bad = tmp_path / "bad.xlsx"
    bad.write_bytes(b"not a zip file")
    code, _, err = run("--xlsx", str(bad), "object", "Shunt")
    assert code == 2 and "not a readable xlsx" in err
    assert "Traceback" not in err


def test_field_named_in_hub_prose_is_not_called_untested():
    code, out, _ = run("field", "Contingency", "LoadMW")
    assert code == 0
    assert "field export only" not in out
    assert "2026-09-28" in out
