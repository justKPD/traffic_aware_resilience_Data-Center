"""
Workload Scheduler
====================

AI traffic-aware scheduler for data center workloads.

Problem: Standard spine-leaf is optimised for north-south (client-server)
traffic, but AI/ML and HPC workloads need:
  - East-west traffic (all-reduce collectives)
  - Large, synchronised bursts (parameter server updates)
  - Low-latency between specific server pairs

Solutions:
  - Affinity scheduling: place communicating tasks in the same room
  - Time-based scheduling: stagger large transfers to off-peak hours
  - Bandwidth reservation: reserve paths for elephant flows
  - Topology-aware placement: leverage cross-room shortcuts
"""

import random
from collections import defaultdict
from typing import Dict, List, Optional


class WorkloadScheduler:

    WORKLOAD_TYPES = {
        "hpc_training":  {"pattern": "all_reduce",  "bw": "high", "lat": "low"},
        "web_service":   {"pattern": "client_server", "bw": "medium", "lat": "low"},
        "batch_job":     {"pattern": "map_reduce",  "bw": "high", "lat": "medium"},
        "storage":       {"pattern": "sequential",  "bw": "high", "lat": "high"},
    }

    def __init__(self):
        self.server_affinity = defaultdict(lambda: defaultdict(float))
        self.server_workload_type = defaultdict(str)

        self.reservations = []
        self.reservation_count = 0

        self.affinity_placements = 0
        self.staggered_transfers = 0
        self.bandwidth_reservations = 0

    # ------------------------------------------------------------------

    def learn_affinity(self, src_server: int, dst_server: int,
                       traffic_bytes: float):
        """Learn communication affinity between two servers."""
        self.server_affinity[src_server][dst_server] += traffic_bytes
        if len(self.server_affinity[src_server]) > 20:
            top = sorted(self.server_affinity[src_server].items(),
                         key=lambda x: -x[1])[:10]
            self.server_affinity[src_server] = dict(top)

    def suggest_placement(self, workload_type: str, num_servers: int,
                          available_rooms: List[int],
                          room_capacities: Dict[int, int]) -> Dict:
        """Suggest optimal server placement for a workload."""
        if workload_type in ("hpc_training", "all_reduce"):
            best = max(available_rooms,
                       key=lambda r: room_capacities.get(r, 0))
            placement = {best: min(num_servers,
                                   room_capacities.get(best, 0))}
            return {
                "workload_type": workload_type,
                "placement": placement,
                "strategy": "single_room_affinity",
                "cross_room_traffic_reduction": 0.9,
                "expected_latency_improvement": 0.4,
            }

        if workload_type == "web_service":
            per = num_servers // len(available_rooms)
            rem = num_servers % len(available_rooms)
            placement = {}
            for i, room in enumerate(available_rooms):
                placement[room] = per + (1 if i < rem else 0)
            return {
                "workload_type": workload_type,
                "placement": placement,
                "strategy": "distributed_redundancy",
                "cross_room_traffic_reduction": 0.0,
                "expected_latency_improvement": 0.0,
            }

        best = max(available_rooms,
                   key=lambda r: room_capacities.get(r, 0))
        placement = {best: min(num_servers, room_capacities.get(best, 0))}
        return {
            "workload_type": workload_type,
            "placement": placement,
            "strategy": "capacity_optimized",
            "cross_room_traffic_reduction": 0.5,
            "expected_latency_improvement": 0.2,
        }

    def schedule_transfer(self, flow_size_bytes: int, priority: str,
                          available_paths: List[List[int]],
                          current_time: float) -> Dict:
        if priority == "high" and available_paths:
            path = min(available_paths, key=len)
            reservation = {
                "path": path,
                "bandwidth_mbps": 10000,
                "start_time": current_time,
                "end_time": current_time + flow_size_bytes / 1.25e9,
                "priority": priority,
            }
            self.reservations.append(reservation)
            self.reservation_count += 1
            self.bandwidth_reservations += 1
            return {
                "scheduled": True,
                "path": path,
                "start_time": current_time,
                "method": "bandwidth_reservation",
            }

        delay = 4 * 3600
        self.staggered_transfers += 1
        return {
            "scheduled": True,
            "path": random.choice(available_paths) if available_paths else None,
            "start_time": current_time + delay,
            "method": "staggered_off_peak",
        }

    # ------------------------------------------------------------------

    def get_throughput_modifier(self) -> float:
        affinity_imp = 1.0 + 0.1 * min(self.affinity_placements / 10, 1.0)
        stagger_imp = 1.0 + 0.05 * min(self.staggered_transfers / 20, 1.0)
        return affinity_imp * stagger_imp

    def get_stats(self) -> Dict:
        return {
            "affinity_placements": self.affinity_placements,
            "staggered_transfers": self.staggered_transfers,
            "bandwidth_reservations": self.bandwidth_reservations,
            "total_reservations": self.reservation_count,
            "throughput_modifier": self.get_throughput_modifier(),
        }
