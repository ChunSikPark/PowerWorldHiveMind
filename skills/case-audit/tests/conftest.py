"""Engine on sys.path, and the fixtures shared by every case-audit test file."""
import importlib
import sys
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parents[1] / "engine"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
FAKE_ESAPP = Path(__file__).resolve().parent / "fake_esapp"
sys.path.insert(0, str(ENGINE))

from auditcase import toy  # noqa: E402


@pytest.fixture
def frames():
    return toy()


@pytest.fixture(scope="session")
def hawaii():
    """What the reader read from the public Hawaii40 case (37 buses) on 2026-09-30, file name only."""
    return FIXTURES / "hawaii40.json.gz"


@pytest.fixture
def fake_esapp(monkeypatch, hawaii):
    """The stand-in esapp, serving Hawaii40, imported fresh; returns the module (see its CALLS)."""
    monkeypatch.setenv("PWHM_FAKE_SNAPSHOT", str(hawaii))
    for var in ("PWHM_FAKE_SOLVE_ERROR", "PWHM_FAKE_OPEN_ERROR", "PWHM_FAKE_READ_ERROR", "PWHM_FAKE_EMPTY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.syspath_prepend(str(FAKE_ESAPP))
    monkeypatch.delitem(sys.modules, "esapp", raising=False)
    module = importlib.import_module("esapp")
    monkeypatch.setattr("reader._tasklist", lambda: set())
    return module
