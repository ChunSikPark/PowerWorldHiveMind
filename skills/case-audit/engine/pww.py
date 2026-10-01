"""Read a .pww weather file's header and station list (concepts/pww-data.md). Header only:
the data array after the stations is never read, so a year-long file costs what a day does."""
from __future__ import annotations

import struct
from datetime import datetime, timedelta
from pathlib import Path

OLE_EPOCH = datetime(1899, 12, 30)
CHUNK = 1 << 20


class PwwError(Exception):
    """Not a PowerWorld weather file, or its header is cut short."""


class _Header:
    def __init__(self, f, name):
        self.f, self.name, self.buf, self.pos, self.base = f, name, b"", 0, 0

    @property
    def offset(self) -> int:
        return self.base + self.pos

    def _need(self, n):
        while len(self.buf) - self.pos < n:
            more = self.f.read(CHUNK)
            if not more:
                raise PwwError(f"{self.name}: header ends early")
            self.base += self.pos
            self.buf = self.buf[self.pos:] + more
            self.pos = 0

    def take(self, fmt):
        size = struct.calcsize("<" + fmt)
        self._need(size)
        v = struct.unpack_from("<" + fmt, self.buf, self.pos)
        self.pos += size
        return v if len(v) > 1 else v[0]

    def cstr(self):
        while (end := self.buf.find(b"\0", self.pos)) < 0:
            self._need(len(self.buf) - self.pos + 1)
        s = self.buf[self.pos:end].decode("latin-1")
        self.pos = end + 1
        return s


def read_header(path: str | Path) -> dict:
    path = Path(path)
    with path.open("rb") as f:
        h = _Header(f, path.name)
        key1, key2, _version = h.take("hhh")
        if key1 != 2001 or key2 not in (8065, 8066):
            raise PwwError(f"{path.name} is not a PowerWorld weather file (keys {key1}, {key2})")
        date_min, date_max = h.take("dd")
        lat_min, lat_max, lon_min, lon_max = h.take("dddd")
        for _ in range(h.take("h")):
            h.cstr()                                # description strings
        count, sample, loc = h.take("iii")
        h.take("h")                                 # LOC_FC
        varcount = h.take("h")
        for _ in range(varcount):
            h.take("h")                             # variable codes
        h.take("h")                                 # BYTECOUNT
        if key2 == 8066:
            for _ in range(varcount):
                h.take("i")                         # VERSION 2 valid counts
        stations = []
        for _ in range(loc):
            lat, lon = h.take("dd")
            h.take("h")                             # elevation
            h.cstr(), h.cstr(), h.cstr()            # who, country, region
            stations.append((lat, lon))
        header_bytes = h.offset
    return {"version": 2 if key2 == 8066 else 1, "steps": count, "sample_seconds": sample,
            "header_bytes": header_bytes,
            "start": (OLE_EPOCH + timedelta(days=date_min)).isoformat(timespec="minutes"),
            "end": (OLE_EPOCH + timedelta(days=date_max)).isoformat(timespec="minutes"),
            "bounds": {"lat": [lat_min, lat_max], "lon": [lon_min, lon_max]}, "stations": stations}
