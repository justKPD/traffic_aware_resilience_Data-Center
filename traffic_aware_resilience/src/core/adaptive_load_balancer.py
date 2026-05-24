"""
Adaptive Load Balancer
========================

Replaces static ECMP hashing with ML-based adaptive load balancing.

Problem with ECMP:
  - Uses 5-tuple hash to assign flows to equal-cost paths
  - Elephant flows (large, long-lived) get pinned to one path
  - Multiple elephants hashing to the same path = congestion
  - No awareness of current link utilization

Solution:
  - Monitor per-link utilization via EWMA
  - Classify flows as elephant or mouse by packet/byte count
  - Route elephant flows to least-loaded path
  - Mouse flows: weighted random (lighter paths preferred)
  - Re-hash elephants when path exceeds threshold
"""

import numpy as np
from collections import defaultdict
from typing import Dict, List, Optional, Tuple


class AdaptiveLoadBalancer:

    def __init__(self, rehash_threshold=0.7,
                 elephant_threshold_packets=100):
        self.rehash_threshold = rehash_threshold
        self.elephant_threshold = elephant_threshold_packets

        self.link_utilization = defaultdict(float)
        self.link_ewma = defaultdict(float)
        self.ewma_alpha = 0.2

        self.flow_table = {}       # flow_id -> {path, packets, bytes, is_elephant}
        self.elephant_flows = set()
        self.mouse_flows = set()

        self.rehash_events = 0
        self.rehash_successes = 0
        self.ecmp_collisions_avoided = 0

    # ------------------------------------------------------------------

    def classify_flow(self, flow_id: str, packet_count: int,
                      byte_count: int) -> str:
        """Classify as 'elephant' or 'mouse'."""
        if flow_id not in self.flow_table:
            self.flow_table[flow_id] = {
                "packets": 0, "bytes": 0,
                "is_elephant": False, "path": None,
            }

        entry = self.flow_table[flow_id]
        entry["packets"] += packet_count
        entry["bytes"] += byte_count

        is_elephant = (entry["packets"] > self.elephant_threshold
                       or entry["bytes"] > 1_000_000)

        if is_elephant and not entry["is_elephant"]:
            entry["is_elephant"] = True
            self.elephant_flows.add(flow_id)
            self.mouse_flows.discard(flow_id)
            self.ecmp_collisions_avoided += 1
        elif not is_elephant:
            self.mouse_flows.add(flow_id)

        return "elephant" if is_elephant else "mouse"

    def assign_path(self, flow_id: str, available_paths: List[List[int]],
                    current_loads: Dict[int, float] = None) -> List[int]:
        """Assign a path.  Elephants get least-loaded; mice get weighted random."""
        if not available_paths:
            return []

        is_elephant = (flow_id in self.flow_table
                       and self.flow_table[flow_id]["is_elephant"])

        if is_elephant:
            path_loads = []
            for path in available_paths:
                max_load = 0.0
                for i in range(len(path) - 1):
                    key = (min(path[i], path[i + 1]),
                           max(path[i], path[i + 1]))
                    max_load = max(max_load,
                                   self.link_utilization.get(key, 0.0))
                path_loads.append(max_load)
            chosen = available_paths[int(np.argmin(path_loads))]
        else:
            if current_loads:
                weights = [1.0 / (1.0 + current_loads.get(i, 0))
                           for i in range(len(available_paths))]
                total = sum(weights)
                probs = [w / total for w in weights]
                idx = np.random.choice(len(available_paths), p=probs)
                chosen = available_paths[idx]
            else:
                chosen = list(available_paths[
                    np.random.randint(len(available_paths))])

        if flow_id in self.flow_table:
            self.flow_table[flow_id]["path"] = chosen

        return chosen

    # ------------------------------------------------------------------

    def update_link_utilization(self, from_node: int, to_node: int,
                                 utilization: float):
        key = (min(from_node, to_node), max(from_node, to_node))
        old = self.link_ewma[key]
        self.link_ewma[key] = self.ewma_alpha * utilization + (1 - self.ewma_alpha) * old
        self.link_utilization[key] = utilization

    def check_rehash_needed(self) -> List[str]:
        """Return elephant flow IDs whose current path is overloaded."""
        candidates = []
        for fid in self.elephant_flows:
            entry = self.flow_table.get(fid)
            if not entry or not entry["path"]:
                continue
            path = entry["path"]
            max_load = 0.0
            for i in range(len(path) - 1):
                key = (min(path[i], path[i + 1]),
                       max(path[i], path[i + 1]))
                max_load = max(max_load, self.link_ewma.get(key, 0))
            if max_load > self.rehash_threshold:
                candidates.append(fid)
        return candidates

    def perform_rehash(self, flow_id: str,
                       available_paths: List[List[int]]) -> Optional[List[int]]:
        old_path = self.flow_table.get(flow_id, {}).get("path")
        new_path = self.assign_path(flow_id, available_paths)

        if new_path and new_path != old_path:
            self.rehash_events += 1
            if old_path:
                old_load = self._path_max_load(old_path)
                new_load = self._path_max_load(new_path)
                if new_load < old_load:
                    self.rehash_successes += 1
                    self.flow_table[flow_id]["path"] = new_path
                    return new_path
        return old_path

    def _path_max_load(self, path: List[int]) -> float:
        if len(path) < 2:
            return 1.0
        return max(
            self.link_ewma.get((min(path[i], path[i + 1]),
                                max(path[i], path[i + 1])), 0)
            for i in range(len(path) - 1))

    # ------------------------------------------------------------------

    def get_imbalance_score(self) -> float:
        """0 = perfectly balanced, 1 = maximally imbalanced (coeff. of var.)."""
        vals = list(self.link_ewma.values())
        if len(vals) < 2:
            return 0.0
        mean = np.mean(vals)
        if mean == 0:
            return 0.0
        return min(float(np.std(vals) / mean), 1.0)

    def get_stats(self) -> Dict:
        ewma_vals = list(self.link_ewma.values())
        return {
            "total_flows": len(self.flow_table),
            "elephant_flows": len(self.elephant_flows),
            "mouse_flows": len(self.mouse_flows),
            "ecmp_collisions_avoided": self.ecmp_collisions_avoided,
            "rehash_events": self.rehash_events,
            "rehash_successes": self.rehash_successes,
            "imbalance_score": self.get_imbalance_score(),
            "avg_link_utilization": float(np.mean(ewma_vals)) if ewma_vals else 0,
            "max_link_utilization": float(max(ewma_vals)) if ewma_vals else 0,
        }
