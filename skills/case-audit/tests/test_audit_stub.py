import time
import tracemalloc

from auditcase import case
from findings import YOUR_CALL
from rules_stub import floating_stub
from topology import adjacency, bridges, far_side, pockets


def test_double_circuit_is_never_a_bridge():
    assert bridges([1, 2, 3], [(1, 2), (1, 2), (2, 3)]) == {2}


def test_pockets_carry_sizes_and_the_chain_above():
    edges = [(1, 2), (2, 3), (3, 1), (3, 5), (5, 6)]
    p = pockets([1, 2, 3, 5, 6], edges)
    assert p[3] == {"near": 3, "far": 5, "parent": None, "size": 2}
    assert p[4] == {"near": 5, "far": 6, "parent": 3, "size": 1}


def test_far_side_never_crosses_its_bridge_and_stops_at_the_limit():
    edges = [(1, 2), (2, 3), (3, 1), (3, 5), (5, 6), (6, 7)]
    adj = adjacency(edges)
    assert far_side(adj, 3, 5, 10) == {5, 6, 7}
    assert far_side(adj, 3, 5, 2) is None


def test_long_chain_is_linear_in_time_and_memory():
    n = 20000
    edges = [(1, 2), (2, 3), (3, 1)] + [(i, i + 1) for i in range(3, n)]
    tracemalloc.start()
    t = time.perf_counter()
    p = pockets(list(range(1, n + 1)), edges)
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    assert len(p) == n - 3 and time.perf_counter() - t < 10 and peak < 200e6


def _unloaded(frames, stub_pu=(1.05, 1.07)):
    b = frames["Bus"]
    b.loc[b.BusNum.isin([5, 6]), "BusPUVolt"] = list(stub_pu)
    frames["Branch"].loc[4, ["LineMW", "LineMaxPercent"]] = [0.5, 1.0]     # the 3-5 attachment line


def test_unloaded_ehv_stub_fires_once_at_its_attachment(frames):
    _unloaded(frames)
    frames["Branch"].loc[5, "LineMaxPercent"] = 1.0                         # 5-6 passes too; 3-5 is reported
    [f] = floating_stub(case(frames))
    w = f.where[0]
    assert f.triage == YOUR_CALL and len(f.where) == 1 and (w["BusNum"], w["BusNum:1"]) == (3, 5)
    assert w["far_bus"] == 6 and w["far_pu"] == 1.07 and w["far_side_buses"] == 2
    assert w["charging_mvar_at_1pu"] == 4.0 and w["absorbing_room_mvar"] == 0
    assert w["zero_range_units"] == [{"BusNum": 6, "GenID": "S1"}]


def test_a_loaded_attachment_with_an_unloaded_sub_stub_reports_the_sub_stub(frames):
    b = frames["Bus"]
    b.loc[b.BusNum.isin([5, 6]), "BusPUVolt"] = [1.02, 1.07]
    frames["Branch"].loc[5, ["LineMW", "LineMaxPercent"]] = [0.3, 1.0]     # 5-6 unloaded; 3-5 stays at 40 %
    [f] = floating_stub(case(frames))
    assert [(w["BusNum"], w["BusNum:1"]) for w in f.where] == [(5, 6)]


def test_loaded_stub_is_quiet(frames):
    _unloaded(frames)
    frames["Branch"].loc[4, "LineMaxPercent"] = 40.0
    assert floating_stub(case(frames)) == []


def test_no_rise_is_quiet(frames):
    _unloaded(frames, stub_pu=(1.0, 1.0))
    assert floating_stub(case(frames)) == []


def test_no_charging_means_no_stub(frames):
    _unloaded(frames)
    frames["Branch"].LineC = 0.0
    assert floating_stub(case(frames)) == []


def test_below_ehv_is_not_a_stub(frames):
    _unloaded(frames)
    frames["Bus"].loc[frames["Bus"].BusNum.isin([3, 5, 6]), "BusNomVolt"] = 230.0
    assert floating_stub(case(frames)) == []
