"""What a rule returns. Severity and triage are separate labels, each from a closed set."""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

STOPS, WORTH, FYI = "Stops the study", "Worth a look", "FYI"
BROKEN, ON_PURPOSE, YOUR_CALL = "Broken", "Probably on purpose", "Your call"
SEVERITIES = (STOPS, WORTH, FYI)
TRIAGES = (BROKEN, ON_PURPOSE, YOUR_CALL)
PROFILES = ("base", "n1", "timestep", "opf", "scopf")  # n1 = the monitoring verdict reported with base
AC_STUDIES = PROFILES                                 # every study here solves AC
NEEDS_HANDOFF = {"ts.pfw_missing", "opf.3"}           # data the kit does not carry: say where it comes from


@dataclass
class Finding:
    rule: str                  # e.g. "base.dc_skeleton"
    severity: str              # one of SEVERITIES
    triage: str                # one of TRIAGES
    what: str                  # what's wrong, one plain line
    why: str                   # why it matters, one plain line
    page: str = ""             # the kit page that explains it
    stops: tuple = ()          # profiles whose verdict this finding turns NOT READY
    scope: str = ""            # e.g. "N-1 and SCOPF only" - shown after the severity label
    where: list = field(default_factory=list)    # one dict of key fields (and numbers) per object
    details: dict = field(default_factory=dict)  # the numbers the agent quotes
    handoff: str = ""          # who supplies what the fix needs, when the kit cannot

    def __post_init__(self):
        assert self.severity in SEVERITIES, self.severity
        assert self.triage in TRIAGES, self.triage
        assert set(self.stops) <= set(PROFILES), self.stops
        assert bool(self.stops) == (self.severity == STOPS), (self.rule, self.stops)
        assert self.handoff or self.rule not in NEEDS_HANDOFF or self.triage == ON_PURPOSE, self.rule

    @property
    def label(self) -> str:
        return f"{self.severity} — {self.scope}" if self.scope else self.severity

    def to_dict(self) -> dict:
        d = asdict(self)
        d["stops"], d["label"], d["count"] = list(self.stops), self.label, len(self.where)
        return clean(d)


def clean(o):
    """NaN/inf -> None and numpy scalars -> Python, recursively, so json.dump never writes NaN."""
    if hasattr(o, "item") and not isinstance(o, (list, dict, str)):
        o = o.item()
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    return o


def bus(n) -> int:
    return int(n)


def branch_keys(r) -> dict:
    """A branch's three key fields. LineCircuit is text: '1', 'W2', ' 1 ' all stay strings."""
    return {"BusNum": bus(r["BusNum"]), "BusNum:1": bus(r["BusNum:1"]), "LineCircuit": str(r["LineCircuit"])}
