#!/usr/bin/env python3
"""
Standalone simulation driver for Traffic-Aware Network Resilience AI.

Builds a 3-room Fat-Tree + Jellyfish overlay topology from real THD
Deggendorf specs, then runs a 365-day simulation comparing:

  1. Baseline    -- no traffic-aware optimisation
  2. Partial     -- load balancing only
  3. Full AI     -- all four components active

Outputs daily metrics and comparison plots to results/.
"""

import sys, os, json, random, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from models.network import NetworkNode, Cable, NetworkTopology
from core.traffic_aware_ai import TrafficAwareNetworkResilienceAI


# ------------------------------------------------------------------ #
# Topology builder
# ------------------------------------------------------------------ #

def build_topology(cfg: Config) -> NetworkTopology:
    net = NetworkTopology()
    nid = 0
    cid = 0
    room_positions = [(0, 0, 0), (6.32, 0, 0), (13.26, 0, 0)]

    for dc_id in range(1, cfg.num_rooms + 1):
        x, y, z = room_positions[dc_id - 1]
        h = cfg.room_heights[dc_id]
        pwr = cfg.server_power[dc_id]

        sids = []
        for rack in range(cfg.racks_per_room):
            for s in range(cfg.servers_per_rack):
                nid += 1
                srv = NetworkNode(
                    id=nid, node_type="server", dc_id=dc_id,
                    position=(x + 2 + (rack % 2) * 4,
                              y + 2 + (rack // 2) * 5,
                              z + 1 + s * 0.5),
                    power_consumption=pwr, base_power=pwr,
                )
                net.add_node(srv)
                sids.append(nid)

        leaf_ids = []
        for i in range(cfg.leaves_per_room):
            nid += 1
            leaf = NetworkNode(
                id=nid, node_type="switch", dc_id=dc_id, layer="leaf",
                position=(x + 3 + i * 4, y + 1, z + 1.5),
                power_consumption=cfg.leaf_power, base_power=cfg.leaf_power,
            )
            net.add_node(leaf)
            leaf_ids.append(nid)

        nid += 1
        spine = NetworkNode(
            id=nid, node_type="switch", dc_id=dc_id, layer="spine",
            position=(x + 5, y + 6, z + h - 0.5),
            power_consumption=cfg.spine_power, base_power=cfg.spine_power,
        )
        net.add_node(spine)
        spine_id = nid

        for idx, sid in enumerate(sids):
            leaf = leaf_ids[idx // 16]
            cid += 1
            net.add_cable(Cable(id=cid, from_node=sid, to_node=leaf,
                                cable_type="OM4", length=4.0))

        for lid in leaf_ids:
            cid += 1
            net.add_cable(Cable(id=cid, from_node=lid, to_node=spine_id,
                                cable_type="OS2", length=h - 2.0))

    spines = [s for s in net.switches.values() if s.layer == "spine"]
    for i, s1 in enumerate(spines):
        for s2 in list(net.switches.values())[i + 1:]:
            if s2.layer != "spine":
                continue
            cid += 1
            dist = (cfg.cable_lengths[s1.dc_id]
                    + cfg.cable_lengths[s2.dc_id]) / 2
            net.add_cable(Cable(id=cid, from_node=s1.id, to_node=s2.id,
                                cable_type="OS2", length=dist,
                                is_cross_room=True))

    # Jellyfish cross-room leaf links
    leaves = [s for s in net.switches.values() if s.layer == "leaf"]
    linked = set()
    for leaf in leaves:
        others = [l for l in leaves
                  if l.dc_id != leaf.dc_id and l.id not in linked]
        if others:
            tgt = random.choice(others)
            cid += 1
            dist = {1: 32, 2: 32, 3: 34}.get(abs(leaf.dc_id - tgt.dc_id), 38)
            net.add_cable(Cable(id=cid, from_node=leaf.id, to_node=tgt.id,
                                cable_type="OS2", length=dist,
                                is_cross_room=True))
            leaf.is_cross_room = True
            tgt.is_cross_room = True
            linked.add(leaf.id)
            linked.add(tgt.id)

    return net


# ------------------------------------------------------------------ #
# Failure injection + repair (same as self_healing_network)
# ------------------------------------------------------------------ #

def inject_failures(net, cfg, day, rng):
    failed = []
    for node in list(net.switches.values()):
        if node.is_active and rng.random() < cfg.switch_failure_rate:
            node.is_active = False
            failed.append(node.id)
            for nid, cable in net.adjacency_list[node.id]:
                cable.is_active = False
    for node in list(net.servers.values()):
        if node.is_active and rng.random() < cfg.server_failure_rate:
            node.is_active = False
            failed.append(node.id)
    for cable in list(net.cables.values()):
        if cable.is_active and rng.random() < cfg.cable_failure_rate:
            cable.is_active = False
    return failed


def repair_nodes(net, cfg):
    for node in list(net.switches.values()):
        if not node.is_active and random.random() < 1.0 / cfg.repair_time_days:
            node.is_active = True
            for nid, cable in net.adjacency_list[node.id]:
                peer = net._get_node(nid)
                if peer and peer.is_active:
                    cable.is_active = True
    for node in list(net.servers.values()):
        if not node.is_active and random.random() < 1.0 / cfg.repair_time_days:
            node.is_active = True


# ------------------------------------------------------------------ #
# Simulation
# ------------------------------------------------------------------ #

def run_simulation(mode="full", days=365, seed=42):
    rng = np.random.default_rng(seed)
    cfg = Config(simulation_days=days)
    net = build_topology(cfg)
    ai = TrafficAwareNetworkResilienceAI()

    metrics = {
        "availability": [],
        "cable_failures": [],
        "throughput_modifier": [],
        "failure_modifier": [],
    }

    for day in range(days):
        # stochastic failures
        inject_failures(net, cfg, day, rng)
        repair_nodes(net, cfg)

        # traffic-aware AI
        if mode in ("partial", "full"):
            for hour in range(0, 24, 4):
                ai.apply_daily_optimization(net, day, hour)

        avail = sum(1 for s in net.servers.values() if s.is_active) / max(len(net.servers), 1) * 100
        cable_f = sum(1 for c in net.cables.values() if not c.is_active)
        tp_mod = ai.get_throughput_modifier()
        fr_mod = ai.get_failure_rate_modifier()

        metrics["availability"].append(avail)
        metrics["cable_failures"].append(cable_f)
        metrics["throughput_modifier"].append(tp_mod)
        metrics["failure_modifier"].append(fr_mod)

    return metrics, ai.get_stats()


# ------------------------------------------------------------------ #
# Plotting
# ------------------------------------------------------------------ #

def plot_results(results, out_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle("Traffic-Aware Network Resilience -- 365-Day Simulation",
                 fontsize=14)

    for mode, color in [("baseline", "#e74c3c"), ("partial", "#f39c12"),
                         ("full", "#2ecc71")]:
        m = results[mode][0]
        days = list(range(len(m["availability"])))
        axes[0, 0].plot(days, m["availability"], color=color,
                         label=mode, alpha=0.8)
        axes[0, 1].plot(days, m["cable_failures"], color=color,
                         label=mode, alpha=0.8)
        axes[1, 0].plot(days, m["throughput_modifier"], color=color,
                         label=mode, alpha=0.8)
        axes[1, 1].plot(days, m["failure_modifier"], color=color,
                         label=mode, alpha=0.8)

    for ax in axes.flat:
        ax.set_xlabel("Day")
        ax.legend(loc="best", fontsize=8)
        ax.grid(True, alpha=0.3)

    axes[0, 0].set_title("Network Availability (%)")
    axes[0, 1].set_title("Inactive Cables")
    axes[1, 0].set_title("Throughput Modifier")
    axes[1, 1].set_title("Failure Rate Modifier")

    plt.tight_layout()
    path = os.path.join(out_dir, "traffic_aware_simulation.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Plot saved to {path}")


# ------------------------------------------------------------------ #

def main():
    print("=" * 60)
    print("  Traffic-Aware Network Resilience -- Standalone Simulation")
    print("=" * 60)

    days = 365
    results = {}
    for mode in ("baseline", "partial", "full"):
        print(f"\n  Running {mode} ({days} days) ...")
        t0 = time.time()
        metrics, stats = run_simulation(mode=mode, days=days)
        elapsed = time.time() - t0
        results[mode] = (metrics, stats)
        avg_avail = float(np.mean(metrics["availability"]))
        print(f"    Avg availability: {avg_avail:.2f}%")
        print(f"    Completed in {elapsed:.1f}s")

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "results")
    os.makedirs(out_dir, exist_ok=True)
    plot_results(results, out_dir)

    summary = {}
    for mode in results:
        m, s = results[mode]
        summary[mode] = {
            "avg_availability": float(np.mean(m["availability"])),
            "avg_throughput_modifier": float(np.mean(m["throughput_modifier"])),
            "avg_failure_modifier": float(np.mean(m["failure_modifier"])),
        }
    json_path = os.path.join(out_dir, "simulation_summary.json")
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n  Summary saved to {json_path}")
    print("\n" + "=" * 60)
    print("  Simulation complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
