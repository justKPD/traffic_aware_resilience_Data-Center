"""Integration test -- full TrafficAwareNetworkResilienceAI."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.models.network import NetworkNode, Cable, NetworkTopology
from src.core.traffic_aware_ai import TrafficAwareNetworkResilienceAI


def build_small_topology():
    net = NetworkTopology()
    nid, cid = 0, 0
    for dc_id in (1, 2):
        sids = []
        for _ in range(4):
            nid += 1
            s = NetworkNode(id=nid, node_type="server", dc_id=dc_id)
            net.add_node(s)
            sids.append(nid)

        nid += 1
        leaf = NetworkNode(id=nid, node_type="switch", dc_id=dc_id,
                           layer="leaf")
        net.add_node(leaf)
        lid = nid

        nid += 1
        spine = NetworkNode(id=nid, node_type="switch", dc_id=dc_id,
                            layer="spine")
        net.add_node(spine)
        sid = nid

        for srv in sids:
            cid += 1
            net.add_cable(Cable(id=cid, from_node=srv, to_node=lid,
                                cable_type="OM4", length=4.0))

        cid += 1
        net.add_cable(Cable(id=cid, from_node=lid, to_node=sid,
                            cable_type="OS2", length=6.0))

    spines = [s for s in net.switches.values() if s.layer == "spine"]
    cid += 1
    net.add_cable(Cable(id=cid, from_node=spines[0].id,
                        to_node=spines[1].id,
                        cable_type="OS2", length=38, is_cross_room=True))
    return net


def test_full_ai_runs():
    net = build_small_topology()
    ai = TrafficAwareNetworkResilienceAI()

    for day in range(30):
        for hour in range(0, 24, 4):
            ai.apply_daily_optimization(net, day, hour)

    stats = ai.get_stats()
    assert stats["total_interventions"] >= 0
    assert 0 <= stats["failure_rate_modifier"] <= 2
    assert stats["throughput_modifier"] >= 0


if __name__ == "__main__":
    test_full_ai_runs()
    print("Integration test passed.")
