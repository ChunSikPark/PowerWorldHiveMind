"""Live probe for the case-auditor: what the fields the rules depend on actually read.

    python tools/case-audit-dev/probe.py <case.pwb> [<case.pwb> ...]

Developer tool, kept outside skills/ so no agent runs it: it edits cases in memory. Opens each
case, prints one line per question, and closes it with esa.exit(). One OPF is solved as the case
opened. Five questions need an in-memory edit (area and super-area OPF control switched off; a
value written to one shunt, one transformer and one bus; load scaled until the AC solve fails).
Nothing is ever saved: the case file's sha256 is printed before and after, and the run fails
if they differ.
"""
import hashlib
import os
import sys
import time

import pandas as pd

num = lambda s: pd.to_numeric(s, errors="coerce")


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def get(E, obj, fields):
    d = E.GetParametersMultipleElement(obj, fields)
    if d is None:
        return None
    for c in d.columns:
        d[c] = d[c].astype(str).str.strip()
    return d


def counts(s, n=6):
    return dict(s.value_counts().head(n))


def row(item, value):
    print(f"| {item} | {value} |")


def opf(E):
    """Run an OPF and say whether it started: the refusal is a status string, not an exception."""
    try:
        E.InitializePrimalLP()
        E.SolvePrimalLP()
        raised = "no raise"
    except Exception as e:
        raised = f"RAISED {type(e).__name__}: {str(e)[:90]}"
    s = get(E, "OPFSolutionSummary", ["LPOPFSolutionStatus", "LPOPFCostFunction:1"])
    return f"{raised}; {None if s is None else s.iloc[0].to_dict()}"


def probe(path):
    from esapp import PowerWorld
    before = sha(path)
    print(f"\n## {os.path.basename(path)}\n\n| question | observed |\n|---|---|")
    t = time.perf_counter()
    pw = PowerWorld(path)
    try:
        E = pw.esa
        row("open, seconds", f"{time.perf_counter() - t:.1f}")
        opts = get(E, "Sim_Solution_Options", ["SBase", "ChkTaps", "ConvergenceTol:2"])
        row("Sim_Solution_Options SBase / ChkTaps / ConvergenceTol:2 (MVA)", opts.iloc[0].to_dict())
        info = get(E, "PWCaseInformation", ["BusNum", "BranchNum", "GenNum", "BranchNum:2", "BGNIslands"])
        row("PWCaseInformation counts (before solve)", None if info is None else info.iloc[0].to_dict())
        ctg = E.GetParametersMultipleElement("ViolationCTG", ["CTGLabel", "LimViolID:1"])
        row("ViolationCTG rows held in the case as opened", 0 if ctg is None else len(ctg))
        row("zero-row object: GetParametersMultipleElement('3WXFormer', key)",
            repr(E.GetParametersMultipleElement("3WXFormer", ["BusIdentifier"])))
        t = time.perf_counter()
        try:
            E.SolvePowerFlow()
            row("AC SolvePowerFlow as opened", f"no raise, {time.perf_counter() - t:.1f} s")
        except Exception as e:
            row("AC SolvePowerFlow as opened", f"RAISED {type(e).__name__}: {str(e)[:120]}")
        bus = get(E, "Bus", ["BusNum", "BusCat", "BusStatus", "BusIsStarBus", "BusNomVolt", "BusPUVolt",
                             "BusVoltLim", "BusVoltLimLow", "BusVoltLimHigh", "BusMismatchP", "BusMismatchQ"])
        row("max |BusMismatchP| / |BusMismatchQ| after solve",
            f"{num(bus.BusMismatchP).abs().max():.4g} / {num(bus.BusMismatchQ).abs().max():.4g}")
        row("Bus.BusStatus values", counts(bus.BusStatus))
        row("Bus.BusCat values", counts(bus.BusCat))
        row("Bus.BusIsStarBus values", counts(bus.BusIsStarBus))
        row("Bus.BusVoltLim values", counts(bus.BusVoltLim))
        row("Bus (BusVoltLimLow, BusVoltLimHigh) most common",
            dict(bus.groupby(["BusVoltLimLow", "BusVoltLimHigh"]).size().sort_values(ascending=False).head(4)))
        br = get(E, "Branch", ["BusNum", "BusNum:1", "LineCircuit", "LineStatus", "LineXfmr",
                               "BranchDeviceType", "LineXFType", "XFAuto", "XFRegBus", "XFRegBus:1",
                               "XFRegTargetType", "XFRegMin", "XFRegMax", "XFTapMin", "XFTapMax",
                               "XFRegBusOnWhichSide", "LineLength"])
        row("Branch.LineLength = 0 share", f"{(num(br.LineLength) == 0).mean():.3f}")
        row("Branch.BranchDeviceType values", counts(br.BranchDeviceType))
        row("Branch.LineCircuit values with a space or non-digit", sorted(set(c for c in br.LineCircuit if not c.isdigit()))[:8])
        star = set(bus.BusNum[bus.BusIsStarBus == "YES"])
        row("Branch rows touching a star bus", int((br.BusNum.isin(star) | br["BusNum:1"].isin(star)).sum()))
        xf = br[br.LineXfmr == "YES"]
        row("transformer LineXFType values", counts(xf.LineXFType))
        row("transformer XFAuto values", counts(xf.XFAuto))
        row("transformer XFRegTargetType values", counts(xf.XFRegTargetType))
        ltc = xf[(xf.LineXFType == "LTC") & (xf.XFAuto == "YES") & (xf.LineStatus == "Closed")]
        own = (ltc.XFRegBus == ltc.BusNum) | (ltc.XFRegBus == ltc["BusNum:1"])
        row("active LTCs: XFRegBus = own terminal / = 0 / elsewhere",
            f"{int(own.sum())} / {int((ltc.XFRegBus == '0').sum())} / {int((~own & (ltc.XFRegBus != '0')).sum())}")
        row("active LTCs: (XFRegMin, XFRegMax) most common",
            dict(ltc.groupby(["XFRegMin", "XFRegMax"]).size().sort_values(ascending=False).head(3)))
        row("active LTCs: XFRegBusOnWhichSide values", counts(ltc.XFRegBusOnWhichSide))
        w3 = E.GetParametersMultipleElement("3WXFormer", ["BusIdentifier", "BusIdentifier:1", "BusIdentifier:2", "LineCircuit"])
        row("3WXFormer rows", 0 if w3 is None else len(w3))
        sh = get(E, "Shunt", ["BusNum", "ShuntID", "SSStatus", "SSCMode", "AutoControl", "SSRegNum",
                              "SSRegNum:1", "SSMaxMVR", "SSMinMVR"])
        if sh is None:
            row("Shunt rows", "None")
        else:
            row("Shunt.SSCMode values", counts(sh.SSCMode))
            row("Shunt.AutoControl values", counts(sh.AutoControl))
            reg = sh[sh.SSCMode.isin(["Discrete", "Continuous", "SVC"])]
            row("regulating shunts: SSRegNum = own bus / = 0 / elsewhere",
                f"{int((reg.SSRegNum == reg.BusNum).sum())} / {int((reg.SSRegNum == '0').sum())} / "
                f"{int(((reg.SSRegNum != reg.BusNum) & (reg.SSRegNum != '0')).sum())}")
            row("regulating shunts with SSRegNum = 0: SSRegNum:1 values", counts(reg[reg.SSRegNum == "0"]["SSRegNum:1"]))
        gen = get(E, "Gen", ["BusNum", "GenID", "GenStatus", "GenMW", "GenMWMax", "GenFuelType",
                             "TSPFWModelString", "Latitude", "Longitude", "Latitude:1", "Longitude:1",
                             "CustomInteger:1", "GenUnitType", "GenAGCAble", "GenCostModel"])
        ren = gen[gen.GenFuelType.str.contains("WND|SUN")]
        row("renewables: Gen.Latitude (bus) blank / Gen.Latitude:1 (substation) blank",
            f"{int(num(ren.Latitude).isna().sum())} / {int(num(ren['Latitude:1']).isna().sum())} of {len(ren)}")
        row("Gen.CustomInteger:1 values", counts(gen["CustomInteger:1"]))
        over = num(gen.GenMW) - num(gen.GenMWMax)
        on = gen.GenStatus == "Closed"
        row("online units over GenMWMax by > 0.1 MW (MW over, largest 5)",
            sorted(over[on & (over > 0.1)].round(2).tolist(), reverse=True)[:5])
        row("Gen.GenFuelType values", counts(gen.GenFuelType, 10))
        row("Gen.TSPFWModelString length > 2", int((gen.TSPFWModelString.str.len() > 2).sum()))
        row("Gen.GenCostModel values", counts(gen.GenCostModel))
        area = get(E, "Area", ["AreaNum", "BGAGC", "BGReportLimits"])
        row("Area.BGAGC values", counts(area.BGAGC))
        sa = get(E, "SuperArea", ["SAName", "BGAGC"])
        row("SuperArea.BGAGC values", "None" if sa is None else counts(sa.BGAGC))
        ls = get(E, "LimitSet", ["LSName", "LSDisabled", "LSLineRateSet", "LSLineRateSet:1", "LSAmpMVA"])
        row("LimitSet rows (LSName, LSDisabled, LSLineRateSet, :1, LSAmpMVA)", ls.values.tolist())
        mon = get(E, "Limit_Monitoring_Options", ["LMS_IgnoreRadial"])
        row("Limit_Monitoring_Options.LMS_IgnoreRadial", None if mon is None else mon.iloc[0, 0])
        member = get(E, "Area", ["AreaNum", "SAName", "BGAGC"])
        row("Area (AreaNum, SAName, BGAGC)", member.values.tolist()[:4])
        row("OPF as opened: InitializePrimalLP + SolvePrimalLP", opf(E))

        # --- in-memory edits below; the case on disk is never written
        for _, r in member.iterrows():
            E.ChangeParametersSingleElement("Area", ["AreaNum", "BGAGC"], [r.AreaNum, "Off AGC"])
        if sa is not None:
            for _, r in sa.iterrows():
                E.ChangeParametersSingleElement("SuperArea", ["SAName", "BGAGC"], [r.SAName, "Off AGC"])
        row("OPF with every area and super area Off AGC (in memory)", opf(E))
        if sh is not None and len(reg):
            s = reg.head(1)
            k = [s.BusNum.iloc[0], s.ShuntID.iloc[0]]
            other = next(b for b in bus.BusNum if b != k[0])
            f = ["BusNum", "ShuntID", "SSRegNum", "SSRegNum:1"]
            for v in (other, "0"):
                E.ChangeParametersSingleElement("Shunt", f[:3], k + [v])
                got = E.GetParametersSingleElement("Shunt", f, k + ["", ""]).astype(str).str.strip()
                row(f"regulating shunt at bus {k[0]}: write SSRegNum = {v}, read back SSRegNum / SSRegNum:1",
                    f"{got['SSRegNum']} / {got['SSRegNum:1']}")
        b = ltc.head(1) if len(ltc) else xf[xf.LineStatus == "Closed"].head(1)
        if len(b):
            k = [b.BusNum.iloc[0], b["BusNum:1"].iloc[0], b.LineCircuit.iloc[0]]
            kf = ["BusNum", "BusNum:1", "LineCircuit"]
            if not len(ltc):   # no live LTC in this case: make one in memory
                E.ChangeParametersSingleElement("Branch", kf + ["LineXFType", "XFAuto"], k + ["LTC", "YES"])
            f = kf + ["XFRegBus", "XFRegBus:1", "LineXFType", "XFAuto"]
            for v in (k[1], "0"):
                E.ChangeParametersSingleElement("Branch", kf + ["XFRegBus"], k + [v])
                got = E.GetParametersSingleElement("Branch", f, k + ["", "", "", ""]).astype(str).str.strip()
                row(f"LTC {k[0]}-{k[1]} ({got['LineXFType']}, XFAuto {got['XFAuto']}): write XFRegBus = {v}, "
                    f"read back XFRegBus / XFRegBus:1", f"{got['XFRegBus']} / {got['XFRegBus:1']}")
        k = [bus.BusNum.iloc[0]]
        f = ["BusNum", "BusVoltLim", "BusVoltLimLow", "BusVoltLimHigh"]
        E.ChangeParametersSingleElement("Bus", f, k + ["YES", "0.95", "1.04"])
        got = E.GetParametersSingleElement("Bus", f, k + ["", "", ""]).astype(str).str.strip()
        row(f"bus {k[0]}: write BusVoltLim = YES, 0.95 / 1.04, read back BusVoltLimLow / High",
            f"{got['BusVoltLimLow']} / {got['BusVoltLimHigh']}")
        before_mw = num(get(E, "Load", ["BusNum", "LoadID", "LoadMW"]).LoadMW).sum()
        E.Scale("LOAD", "FACTOR", [4.0], "SYSTEM")
        mw = num(get(E, "Load", ["BusNum", "LoadID", "LoadMW"]).LoadMW).sum()
        row("esapp Scale(LOAD, FACTOR, [4], SYSTEM): system load MW before -> after", f"{before_mw:.1f} -> {mw:.1f}")
        load = get(E, "Load", ["BusNum", "LoadID", "LoadMW", "LoadMVR"])
        for factor in (4, 8, 12, 20, 40):
            scaled = load.copy()
            scaled["LoadMW"] = num(load.LoadMW) * factor
            scaled["LoadMVR"] = num(load.LoadMVR) * factor
            E.ChangeParametersMultipleElement("Load", list(scaled.columns), scaled.values.tolist())
            try:
                E.SolvePowerFlow()
                outcome = "no raise"
            except Exception as e:
                outcome = f"RAISED {type(e).__name__}: {str(e)[:90]}"
            b2 = get(E, "Bus", ["BusNum", "BusMismatchP", "BusPUVolt"])
            row(f"AC solve, load x{factor} (in memory)",
                f"{outcome}; max mismatch {num(b2.BusMismatchP).abs().max():.4g} MW; min V {num(b2.BusPUVolt).min():.3f}")
            if outcome != "no raise":
                break
    finally:
        pw.esa.exit()
    after = sha(path)
    row("case file sha256 unchanged", before == after)
    if before != after:
        sys.exit("the case file changed on disk")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        probe(os.path.abspath(p))
