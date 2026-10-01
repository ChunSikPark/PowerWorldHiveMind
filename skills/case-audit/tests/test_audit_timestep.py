import struct

import pytest

from auditcase import case
from findings import BROKEN, FYI, WORTH, YOUR_CALL
from pww import PwwError, read_header
from rules_ts import coverage, latlon_missing, pfw_missing, pww_footprint


def write_pww(path, stations, version=2):
    """A minimal .pww per concepts/pww-data.md: header, stations, and a data array."""
    codes = [102, 106]
    b = struct.pack("<hhh", 2001, 8066 if version == 2 else 8065, version)
    b += struct.pack("<dd", 45910.0, 45911.0)
    lats, lons = [s[0] for s in stations], [s[1] for s in stations]
    b += struct.pack("<dddd", min(lats), max(lats), min(lons), max(lons))
    b += struct.pack("<h", 1) + b"PowerWorld Timestep Simulation Weather\0"
    b += struct.pack("<iii", 24, 3600, len(stations)) + struct.pack("<hh", 0, len(codes))
    b += struct.pack(f"<{len(codes)}h", *codes) + struct.pack("<h", len(codes))
    if version == 2:
        b += struct.pack(f"<{len(codes)}i", *[24 * len(stations)] * len(codes))
    for lat, lon in stations:
        b += struct.pack("<ddh", lat, lon, 0) + b"+st/\0\0\0"
    b += bytes(24 * len(codes) * len(stations))
    path.write_bytes(b)
    return path


def test_header_v2_and_v1(tmp_path):
    for v in (1, 2):
        h = read_header(write_pww(tmp_path / f"w{v}.pww", [(30.0, -97.0), (30.25, -97.0)], version=v))
        assert h["version"] == v and h["steps"] == 24 and h["sample_seconds"] == 3600
        assert h["stations"] == [(30.0, -97.0), (30.25, -97.0)] and h["start"] == "2025-09-10T00:00"


def test_the_public_hawaii_weather_file_header(hawaii):
    """The header and station list of the public Hawaii40 3-day weather file, cut where its data begins."""
    p = hawaii.parent / "hawaii_konaday_header.pww"
    h = read_header(p)
    assert (h["version"], h["steps"], h["sample_seconds"], len(h["stations"])) == (1, 72, 3600, 609)
    assert h["header_bytes"] == p.stat().st_size and h["stations"][0] == (18.0, -161.0)


def test_not_a_weather_file(tmp_path):
    p = tmp_path / "x.pww"
    p.write_bytes(b"\0" * 64)
    with pytest.raises(PwwError, match="not a PowerWorld weather file"):
        read_header(p)


def test_every_renewable_follows_the_weather(frames):
    cd = case(frames)
    assert pfw_missing(cd) == [] and latlon_missing(cd) == []
    assert coverage(cd) == {"renewables": 2, "with_pfw": 2, "installed_mw": 150.0, "following_mw": 150.0}


def test_missing_pfw_says_what_the_run_will_do(frames):
    frames["Gen"].loc[1, "TSPFWModelString"] = ""
    frames["Gen"].loc[1, "GenUnitType"] = "W2 (Wind Turbine, Type 2)"
    [f] = pfw_missing(case(frames))
    assert f.severity == WORTH and f.triage == BROKEN and f.stops == ()
    assert f.what.startswith("time step will run: 1 of 2 renewables follow the weather; 1 read 0 MW")
    assert "(100 of 150 MW installed, 66.7%)" in f.what
    assert f.where == [{"BusNum": 2, "GenID": "W1", "GenFuelType": "WND (Wind)", "GenMWMax": 100.0}]
    assert f.details["missing_wind_with_class"] == 1
    assert "Auto_PFW" in f.handoff and "1 of the 1 missing wind units" in f.handoff


def test_none_string_is_not_a_model(frames):
    frames["Gen"].loc[2, "TSPFWModelString"] = "None"
    assert pfw_missing(case(frames))[0].details["missing"] == 1


def test_substation_location_counts_when_the_bus_has_none(frames):
    frames["Gen"]["Latitude"] = float("nan")
    frames["Gen"]["Longitude"] = float("nan")
    frames["Gen"].loc[1, ["Latitude:1", "Longitude:1"]] = [30.0, -97.0]
    cd = case(frames)
    assert cd.get("Gen").loc[1, "Latitude"] != cd.get("Gen").loc[1, "Latitude"]
    assert latlon_missing(cd) == []


def test_zero_zero_is_no_location(frames):
    frames["Gen"].loc[1, ["Latitude:1", "Longitude:1"]] = [0.0, 0.0]
    [f] = latlon_missing(case(frames))
    assert f.where == [{"BusNum": 2, "GenID": "W1", "GenMWMax": 100.0}]


def test_no_weather_file_is_one_fyi(frames):
    [f] = pww_footprint(case(frames), None)
    assert f.severity == FYI and f.triage == YOUR_CALL
    assert f.what == "weather file not given, so I didn't check it covers these units"


def test_units_outside_the_footprint(frames, tmp_path):
    p = write_pww(tmp_path / "w.pww", [(30.0, -97.0), (30.25, -97.0)])
    [f] = pww_footprint(case(frames), str(p))
    assert f.severity == WORTH and [w["GenID"] for w in f.where] == ["S1"]
    assert f.where[0]["nearest_station_miles"] > 25


def test_file_covering_every_unit(frames, tmp_path):
    p = write_pww(tmp_path / "w.pww", [(30.0, -97.0), (30.5, -97.5)])
    [f] = pww_footprint(case(frames), str(p))
    assert f.severity == FYI and f.details["stations"] == 2


def test_unreadable_weather_file_is_fyi(frames, tmp_path):
    [f] = pww_footprint(case(frames), str(tmp_path / "missing.pww"))
    assert f.severity == FYI and "couldn't read" in f.what
