"""A stand-in for esapp that serves a stored snapshot, so the real reader and CLI run with no
PowerWorld. Put this folder first on sys.path (or PYTHONPATH) and set:

  PWHM_FAKE_SNAPSHOT     the snapshot to serve (required)
  PWHM_FAKE_SOLVE_ERROR  SolvePowerFlow raises PowerWorldError with this text
  PWHM_FAKE_SOLVE_CRASH  SolvePowerFlow raises a RuntimeError (not a PowerWorldError) with this text
  PWHM_FAKE_OPEN_ERROR   PowerWorld(path) raises with this text
  PWHM_FAKE_READ_ERROR   every GetParametersMultipleElement raises with this text
  PWHM_FAKE_EMPTY        comma list of objects that read as None (PowerWorld's zero-row answer)

CALLS records every call, for the tests that count them.
"""
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "engine"))
from casedata import CaseData  # noqa: E402

CALLS = []


class PowerWorldError(Exception):
    """Named and shaped like esapp.saw._exceptions.PowerWorldError (a plain Exception subclass)."""


class _SAW:
    def __init__(self):
        cd = CaseData.from_json(os.environ["PWHM_FAKE_SNAPSHOT"])
        self.frames, self.scalars = cd.frames, cd.scalars
        self.empty = set(filter(None, os.environ.get("PWHM_FAKE_EMPTY", "").split(",")))

    def SolvePowerFlow(self, *args):
        CALLS.append(("SolvePowerFlow", args))
        if os.environ.get("PWHM_FAKE_SOLVE_ERROR"):
            raise PowerWorldError(os.environ["PWHM_FAKE_SOLVE_ERROR"])
        if os.environ.get("PWHM_FAKE_SOLVE_CRASH"):
            raise RuntimeError(os.environ["PWHM_FAKE_SOLVE_CRASH"])

    def GetParametersMultipleElement(self, obj, fields):
        CALLS.append(("Get", obj))
        if os.environ.get("PWHM_FAKE_READ_ERROR"):
            raise RuntimeError(os.environ["PWHM_FAKE_READ_ERROR"])
        if obj in ("Sim_Solution_Options", "Limit_Monitoring_Options"):
            return pd.DataFrame([[self.scalars.get(f, "") for f in fields]], columns=fields)
        d = self.frames.get(obj)
        if obj in self.empty or d is None or d.empty:
            return None
        return d[fields].astype(str)

    def exit(self):
        CALLS.append(("exit",))


class PowerWorld:
    def __init__(self, path):
        CALLS.append(("open", path))
        if os.environ.get("PWHM_FAKE_OPEN_ERROR"):
            raise RuntimeError(os.environ["PWHM_FAKE_OPEN_ERROR"])
        self.esa = _SAW()
