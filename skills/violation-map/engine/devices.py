"""Create a new line between two buses, cloned from a same-kV template line and rescaled to length.

IMPEDANCE SCALES WITH LENGTH, RATING DOES NOT. R, X, C and G are per-distance quantities, so they
are multiplied by miles / template_miles; the thermal rating belongs to the conductor and towers,
so the template's whole LineAMVA set is copied unchanged. Scaling the rating as well would invent a
conductor that does not exist. Pick a template at the same nominal kV and of similar length so the
scale factor stays near 1.

Every create is read back. PowerWorld accepts a malformed create, reports success and builds
nothing, so the branch count, the new line's X, its status and its device type are all checked.
Kit page: methods/adding-devices-esapp.md (key fields, and the read-only false alarm).
"""
import warnings
from typing import NamedTuple

import pandas as pd
from esapp.components import Branch

# Everything a create must carry. A create missing any key field (both bus-name keys and the whole
# LineAMVA set included) matches nothing and silently does nothing.
WRITE_FIELDS = ["BusName_NomVolt", "BusName_NomVolt:1", "LineR", "LineX", "LineC", "LineG",
                "LineAMVA", "LineAMVA:1", "LineAMVA:2"]
VERIFY_FIELDS = WRITE_FIELDS + ["LineStatus", "BranchDeviceType"]
KEYS = ["BusNum", "BusNum:1", "LineCircuit"]


class Result(NamedTuple):
    ok: bool
    detail: str


def _branches(pw):
    d = pw[Branch, VERIFY_FIELDS]
    for c in ("BusNum", "BusNum:1"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["LineCircuit"] = d["LineCircuit"].astype(str).str.strip()
    return d


def add_line(pw, from_bus, to_bus, template, miles, template_miles, names, ckt="1"):
    """template = (from_bus, to_bus, ckt) of an existing line; names = {bus number: BusName_NomVolt}."""
    full = _branches(pw)
    tf, tt, tc = template
    tmpl = full[(full["BusNum"] == tf) & (full["BusNum:1"] == tt) & (full["LineCircuit"] == str(tc))]
    if len(tmpl) != 1:
        return Result(False, f"template {tf}-{tt} ckt {tc} matched {len(tmpl)} rows")
    if (((full["BusNum"] == from_bus) & (full["BusNum:1"] == to_bus))
            | ((full["BusNum"] == to_bus) & (full["BusNum:1"] == from_bus))).any():
        return Result(False, "a branch already exists between these buses")
    if template_miles <= 0.05 or miles <= 0.05:
        return Result(False, f"degenerate length: new {miles} mi, template {template_miles} mi")

    scale = float(miles) / float(template_miles)
    row = tmpl[[c for c in tmpl.columns if c in set(WRITE_FIELDS) | set(KEYS)]].copy()
    row["BusNum"], row["BusNum:1"], row["LineCircuit"] = float(from_bus), float(to_bus), str(ckt)
    row["BusName_NomVolt"] = names.get(float(from_bus), "")
    row["BusName_NomVolt:1"] = names.get(float(to_bus), "")
    for f in ("LineR", "LineX", "LineC", "LineG"):
        v = pd.to_numeric(row[f], errors="coerce").iloc[0]
        row[f] = 0.0 if pd.isna(v) else float(v) * scale
    row["LineStatus"] = "Closed"      # esapp calls it read-only; PowerWorld takes it on create, and an Open tie carries nothing
    n_before = len(full)
    pw.edit_mode()
    try:
        with warnings.catch_warnings():               # suppress the false alarm for the named list only
            warnings.filterwarnings("ignore", message=r".*Read-only field.*", category=UserWarning)
            pw[Branch] = row
    finally:
        pw.run_mode()

    after = _branches(pw)
    if len(after) - n_before != 1:
        return Result(False, f"branch count moved by {len(after) - n_before}, expected +1")
    made = after[(after["BusNum"] == from_bus) & (after["BusNum:1"] == to_bus) & (after["LineCircuit"] == str(ckt))]
    if len(made) != 1:
        return Result(False, "branch count rose but the new line is not locatable by key")
    n = made.iloc[0]
    want_x = float(pd.to_numeric(tmpl["LineX"], errors="coerce").iloc[0]) * scale
    got_x = float(pd.to_numeric(n["LineX"], errors="coerce"))
    if abs(got_x - want_x) > max(1e-9, abs(want_x) * 1e-4):
        return Result(False, f"LineX did not take: asked {want_x:.6g}, got {got_x:.6g}")
    if str(n["LineStatus"]).strip().upper() != "CLOSED":
        return Result(False, f"created line is {n['LineStatus']}")
    if str(n["BranchDeviceType"]).strip().lower() != "line":
        return Result(False, f"created object is a {n['BranchDeviceType']}, not a Line")
    return Result(True, f"new {miles:.1f} mi line from template {tf}-{tt} ckt {tc} (x{scale:.3f}), "
                        f"rating {float(pd.to_numeric(n['LineAMVA'], errors='coerce')):.0f} MVA")


def add_shunt(pw, bus, mvar, name, area, zone, shunt_id="VM"):
    """A fixed shunt: negative MVAr is a reactor. Sized through the block, never through SSMinMVR/SSMaxMVR,
    which are derived and silently discard a write. Kit page: methods/adding-devices-esapp.md."""
    from esapp.components import Shunt
    n0 = len(pw.esa.GetParametersMultipleElement("Shunt", ["BusNum", "ShuntID"]))
    df = pd.DataFrame([{"BusNum": bus, "ShuntID": shunt_id, "BusName_NomVolt": name, "SSStatus": "Closed",
                        "SSCMode": "Fixed", "SSBlockMVarPerStep": float(mvar), "SSBlockNumSteps": 1,
                        "SSNMVR": float(mvar), "AreaNum": area, "ZoneNum": zone}])
    pw.edit_mode()
    try:
        pw[Shunt] = df
    finally:
        pw.run_mode()
    got = pw.esa.GetParametersMultipleElement("Shunt", ["BusNum", "ShuntID", "SSNMVR", "SSStatus"])
    if len(got) - n0 != 1:
        return Result(False, f"shunt count moved by {len(got) - n0}, expected +1")
    me = got[(pd.to_numeric(got.BusNum, errors="coerce") == bus) & (got.ShuntID.astype(str).str.strip() == shunt_id)]
    if (len(me) != 1 or me.SSStatus.astype(str).str.strip().iloc[0] != "Closed"
            or abs(float(pd.to_numeric(me.SSNMVR, errors="coerce").iloc[0]) - float(mvar)) > 0.5):
        return Result(False, f"shunt created but not as asked: {me.to_dict('records')}")
    return Result(True, f"{mvar:+.0f} MVAr fixed shunt at bus {bus}")
