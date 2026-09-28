"""Field lookup over PowerWorld's case-object field export (no PowerWorld needed)."""
from __future__ import annotations

import difflib
import gzip
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_XLSX = KIT_ROOT / "references" / "powerworld-object-fields-v25.xlsx"
CACHE_DIR = Path(__file__).resolve().parent / ".cache"
_CACHE_VERSION = 1
_MEMO: dict[tuple, dict] = {}


class SchemaError(Exception):
    """The export is missing or unreadable, or a lookup cannot be answered."""


@dataclass(frozen=True)
class Field:
    object: str
    variable: str
    concise: str
    type: str
    description: str
    dialog_path: str
    enterable: str  # the export's raw Enterable cell; "" means read-only
    marker: str     # the export's raw Key/Required cell; "" if none

    @property
    def key_index(self) -> int | None:
        m = re.match(r"\*(\d)", self.marker)
        return int(m.group(1)) if m else None

    @property
    def is_required(self) -> bool:
        return "**" in self.marker

    @property
    def writable(self) -> str:
        """yes | aux-only | edit-mode | depends | read-only | unknown."""
        e = self.enterable
        if e in ("Yes", "Yes/Always"):
            return "yes"
        if e == "AUX/Paste":
            return "aux-only"
        if e == "Edit Mode Only":
            return "edit-mode"
        if e.startswith("Depends"):
            return "depends"
        if e == "":
            return "read-only"
        return "unknown"


def _s(v) -> str:
    if v is None:
        return ""
    return re.sub(r"\s+", " ", str(v)).strip().replace("�", "...")


def _read_xlsx(path: Path) -> dict[str, list[Field]]:
    try:
        import openpyxl
    except ImportError as e:
        raise SchemaError(
            "openpyxl is needed to read the field export: python -m pip install openpyxl"
        ) from e
    wb = openpyxl.load_workbook(path, read_only=True)
    objs: dict[str, list[Field]] = {}
    cur = None
    for row in wb.worksheets[0].iter_rows(min_row=2, values_only=True):
        r = tuple(row) + (None,) * (9 - len(row))
        if r[0]:
            cur = _s(r[0])
            objs[cur] = []
        elif r[3] and cur:
            objs[cur].append(Field(
                object=cur, variable=_s(r[3]), concise=_s(r[4]), type=_s(r[5]),
                description=_s(r[6]), dialog_path=_s(r[7]), enterable=_s(r[8]), marker=_s(r[2]),
            ))
    wb.close()
    return objs


def _cache_path(xlsx: Path, st: os.stat_result) -> Path:
    return CACHE_DIR / f"v{_CACHE_VERSION}-{xlsx.stem}-{st.st_size}-{st.st_mtime_ns}.json.gz"


def _read_cache(cache: Path) -> dict[str, list[Field]] | None:
    try:
        raw = json.loads(gzip.decompress(cache.read_bytes()))
        return {o: [Field(**f) for f in fs] for o, fs in raw.items()}
    except (OSError, ValueError, EOFError, TypeError, AttributeError):
        return None


def _write_cache(cache: Path, objs: dict[str, list[Field]]) -> None:
    """Best effort: a read-only install simply runs without a cache."""
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache.with_name(f"{cache.name}.{os.getpid()}.tmp")
        payload = {o: [asdict(f) for f in fs] for o, fs in objs.items()}
        tmp.write_bytes(gzip.compress(json.dumps(payload).encode("utf-8")))
        os.replace(tmp, cache)
    except OSError:
        pass


def load_fields(xlsx: Path | str = DEFAULT_XLSX) -> dict[str, list[Field]]:
    """All objects and their fields, cached on disk by the export's size and mtime."""
    xlsx = Path(xlsx)
    if not xlsx.is_file():
        raise SchemaError(
            f"Field export not found: {xlsx}. The kit ships it as "
            f"references/powerworld-object-fields-v25.xlsx; pass --xlsx to use another export."
        )
    st = xlsx.stat()
    key = (str(xlsx.resolve()), st.st_size, st.st_mtime_ns)
    if key in _MEMO:
        return _MEMO[key]
    cache = _cache_path(xlsx, st)
    objs = _read_cache(cache) if cache.is_file() else None
    if objs is None:
        objs = _read_xlsx(xlsx)
        _write_cache(cache, objs)
    _MEMO[key] = objs
    return objs
