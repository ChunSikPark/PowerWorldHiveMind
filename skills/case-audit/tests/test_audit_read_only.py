"""The engine never writes a case. Enforced on the source, in three layers:

1. only reader.py imports esapp;
2. in reader.py every name bound to an esapp object (the imported `PowerWorld`, `pw = PowerWorld(...)`,
   `E = pw.esa`) is bound only by a plain `name = ...` statement - never through `with`, a tuple,
   an attribute, a return value or a conditional expression - and may be used only through an allowlist - `.esa`, `.SolvePowerFlow()` with no
   arguments, `.GetParametersMultipleElement`, `.exit` - never subscripted, assigned to, passed
   to a function, or re-bound;
3. no name, attribute or string anywhere in engine/*.py names a write (the substring scan).
"""
import ast
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1] / "engine"
FORBIDDEN = ("SaveCase", "LoadAux", "ChangeParameters", "SetData", "WriteAuxFile", "Delete", "CreateData",
             "ProcessAuxFile", "exec_aux", "ResetToFlatStart", "Scale", "EnterMode", "SaveState",
             "RunScriptCommand", "edit_mode", "flat_start", "pflow", "save",
             "__import__", "import_module", "importlib")   # not "esapp": reader.py's error text names it
ALLOWED_ATTRS = {"esa", "SolvePowerFlow", "GetParametersMultipleElement", "exit"}
CALLED_ATTRS = ALLOWED_ATTRS - {"esa"}        # these must be called on the spot, never stored


def imports_esapp(tree) -> bool:
    for n in ast.walk(tree):
        if isinstance(n, ast.Import) and any(a.name.split(".")[0] == "esapp" for a in n.names):
            return True
        if isinstance(n, ast.ImportFrom) and (n.module or "").split(".")[0] == "esapp":
            return True
    return False


def _parents(tree):
    for n in ast.walk(tree):
        for c in ast.iter_child_nodes(n):
            c.parent = n


def _root(node):
    """The Name at the bottom of an attribute chain such as pw.esa.exit, or None."""
    while isinstance(node, ast.Attribute):
        node = node.value
    return node if isinstance(node, ast.Name) else None


def _holds_esapp(value, bound) -> bool:
    """`PowerWorld(...)` (a call of a bound name), `pw.esa`, or a bound name itself."""
    if isinstance(value, ast.Call):
        return isinstance(value.func, ast.Name) and value.func.id in bound
    if isinstance(value, ast.Attribute):
        return value.attr == "esa" and _root(value) is not None and _root(value).id in bound
    return isinstance(value, ast.Name) and value.id in bound


def bound_names(tree) -> set[str]:
    """Names that hold an esapp object: imports from esapp, and anything assigned from one.
    A method's return value (a DataFrame from GetParametersMultipleElement) is data, not bound."""
    bound = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and (n.module or "").split(".")[0] == "esapp":
            bound |= {a.asname or a.name for a in n.names}
        if isinstance(n, ast.Import):
            bound |= {a.asname or a.name for a in n.names if a.name.split(".")[0] == "esapp"}
    grew = True
    while grew:
        grew = False
        for n in ast.walk(tree):
            if isinstance(n, (ast.Assign, ast.AnnAssign, ast.NamedExpr)) and _holds_esapp(n.value, bound):
                targets = n.targets if isinstance(n, ast.Assign) else [n.target]
                for t in targets:
                    if isinstance(t, ast.Name) and t.id not in bound:
                        bound.add(t.id)
                        grew = True
    return bound


def _plain_bind(node) -> bool:
    """`name = <value>`: one target, and that target a bare name."""
    return isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)


def bound_use_violations(source: str, name: str = "<src>") -> list[str]:
    tree = ast.parse(source)
    _parents(tree)
    bound, out = bound_names(tree), []
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and (n.module or "").split(".")[0] == "esapp"                 and any(a.name == "*" for a in n.names):
            out.append(f"{name}:{n.lineno} star import from esapp hides what is bound")
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Name) and n.id in bound):
            continue
        where = f"{name}:{n.lineno} {n.id}"
        p = n.parent
        if isinstance(n.ctx, ast.Store):
            ok = (isinstance(p, ast.Assign) and len(p.targets) == 1
                  and not isinstance(p.value, ast.Name) and _holds_esapp(p.value, bound))
            if not ok:
                out.append(f"{where} re-bound")
            continue
        node = n
        while isinstance(node.parent, ast.Attribute):
            node = node.parent
            if node.attr not in ALLOWED_ATTRS:
                out.append(f"{where}.{node.attr} is not on the read-only allowlist")
            if isinstance(node.ctx, ast.Store):
                out.append(f"{where}.{node.attr} assigned")
        top = node.parent
        if node is not n and node.attr in CALLED_ATTRS and not (isinstance(top, ast.Call) and top.func is node):
            out.append(f"{where}.{node.attr} referenced without being called on the spot")
        if node is not n and node.attr == "esa" and not isinstance(top, ast.Attribute) and not _plain_bind(top):
            out.append(f"{where}.esa bound other than by a plain `name = ...`")
        if node is n:
            if isinstance(top, ast.Call) and top.func is n and n.id[:1].isupper():
                if not _plain_bind(top.parent):
                    out.append(f"{where}(...) bound other than by a plain `name = ...` "
                               f"({type(top.parent).__name__})")
                continue                                     # PowerWorld(path): opens, writes nothing
            out.append(f"{where} used directly ({type(top).__name__})")
        elif isinstance(top, ast.Subscript):
            out.append(f"{where} subscripted")
        elif isinstance(top, ast.Call) and top.func is node and node.attr == "SolvePowerFlow" and (top.args or top.keywords):
            out.append(f"{where}.SolvePowerFlow with a method (DC or a fallback)")
        elif isinstance(top, ast.Call) and top.func is not node:
            out.append(f"{where} passed to a function")
    return out


def substring_violations(source: str, name: str = "<src>") -> list[str]:
    out = []
    for node in ast.walk(ast.parse(source)):
        words = [node.attr] if isinstance(node, ast.Attribute) else [node.id] if isinstance(node, ast.Name) \
            else [node.value] if isinstance(node, ast.Constant) and isinstance(node.value, str) else []
        for w in words:
            out += [f"{name}:{node.lineno} {bad}" for bad in FORBIDDEN if bad in w]
    return out


def violations(source: str, name: str = "<src>") -> list[str]:
    return bound_use_violations(source, name) + substring_violations(source, name)


def test_only_reader_imports_esapp():
    importers = [p.name for p in ENGINE.glob("*.py") if imports_esapp(ast.parse(p.read_text(encoding="utf-8")))]
    assert importers == ["reader.py"]


def test_engine_never_writes_a_case():
    found = [v for p in sorted(ENGINE.glob("*.py")) for v in violations(p.read_text(encoding="utf-8"), p.name)]
    assert found == []


OPEN = "from esapp import PowerWorld\npw = PowerWorld(p)\nE = pw.esa\n"


def test_the_check_catches_writes():
    for bad in ['pw.esa.SaveCase("x.pwb")', "pw.save()", 'pw[Gen, "GenMW"] = df', 'pw.pflow(method="DC")',
                "pw.flat_start = True", "pw.edit_mode()", 'E.SolvePowerFlow("DC")', 'getattr(E, "x")',
                "helper(E)", "E2 = E", 'E.ChangeParametersSingleElement("Bus", f, v)', "x = pw[Bus]"]:
        assert violations(OPEN + bad), bad
    imp = "from esapp import PowerWorld\n"
    for bad in ["with PowerWorld(p) as pw:\n    pw.save()\n",
                "pw, n = PowerWorld(p), 1\npw.save()\n",
                "def opener(p):\n    return PowerWorld(p)\npw = opener(p)\npw.save()\n",
                "self.pw = PowerWorld(p)\nself.pw.save()\n",
                "pw = PowerWorld(p) if p else None\npw.save()\n"]:
        assert bound_use_violations(imp + bad), bad   # caught by the binding rule alone, not the scan
    assert violations('E.RunScriptCommand("SaveCase(x);")')
    assert violations('getattr(E, "LoadAux")')
    # three bypasses the review found
    assert violations("from esapp import *\npw = PowerWorld(p)\npw[Gen, 'GenMW'] = df\n")      # star import
    assert violations("import importlib\nm = importlib.import_module('esapp')\n")                # dynamic import
    assert violations("m = __import__('esapp')\n")
    assert violations(OPEN + "g = E.exit\ns = g.__self__\ns.SolvePowerFlow('DC')\n")           # stored method
    assert violations(OPEN + "g = E.SolvePowerFlow\n")
    assert violations(OPEN + "g = E.GetParametersMultipleElement\n")



def test_the_readers_own_calls_pass():
    ok = OPEN + "E.SolvePowerFlow()\nd = E.GetParametersMultipleElement('Bus', ['BusNum'])\npw.esa.exit()\n"
    assert violations(ok) == []
