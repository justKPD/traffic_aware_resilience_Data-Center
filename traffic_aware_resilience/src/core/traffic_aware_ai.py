"""
Traffic-Aware Network Resilience AI
=====================================

Full AI-powered traffic-aware network resilience system combining:

  1. AdaptiveLoadBalancer   -- replaces ECMP with ML-based flow assignment
  2. TrafficPredictor       -- predicts traffic for proactive management
  3. CongestionController   -- incast detection, flow pacing, ECN marking
  4. WorkloadScheduler      -- topology-aware workload placement

Addresses four critical spine-leaf problems:

  - ECMP hash collisions (elephant flows pinned to congested paths)
  - Spine failure blast radius (one spine failure hits ALL racks)
  - TCP incast congestion (many-to-one traffic overwhelms leaf buffers)
  - AI/ML workload mismatch (all-reduce collectives need east-west paths)
"""

import numpy as np
from collections import defaultdict
from typing import Dict, List, Optional

from .adaptive_load_balancer import AdaptiveLoadBalancer
from .traffic_predictor import TrafficPredictor
from .congestion_controller import CongestionController
from .workload_scheduler import WorkloadScheduler


class TrafficAwareNetworkResilienceAI:

    def __init__(self, config=None):
        self.config = config
        self.load_balancer = AdaptiveLoadBalancer()
        self.traffic_predictor = TrafficPredictor()
        self.congestion_controller = CongestionController()
        self.workload_scheduler = WorkloadScheduler()

        self.total_interventions = 0
        self.successful_interventions = 0

        self.downtime_cost_avoided = 0.0
        self.congestion_cost_avoided = 0.0
        self.throughput_improvement_value = 0.0
        self.implementation_cost = 60000

    # ------------------------------------------------------------------
    # Main optimisation loop -- called every simulated hour
    # ------------------------------------------------------------------

    def apply_daily_optimization(self, network, current_day: int,
                                  current_hour: int):
        """Apply traffic-aware optimisations for one hour."""
        dow = current_day % 7

        # 1. Traffic prediction per room
        for dc_id in range(1, 4):
            pred = self.traffic_predictor.predict_traffic(
                current_hour, dow, current_day, dc_id)

            active = [s for s in network.servers.values()
                      if s.is_active and s.dc_id == dc_id]
            if active:
                load = float(np.mean([s.cpu_utilization for s in active]))
                self.traffic_predictor.record_actual(load, current_hour, dc_id)

            # 2. Spine overload prediction -> pre-migration
            spines = [s for s in network.switches.values()
                      if s.layer == "spine" and s.dc_id == dc_id
                      and s.is_active]
            for spine in spines:
                spine_load = spine.power_consumption / max(spine.base_power, 1)
                ov = self.traffic_predictor.predict_spine_overload(
                    spine.id, dc_id, current_hour, dow, current_day,
                    spine_load, 1.0)
                if ov["recommendation"] in ("pre_migrate_critical",
                                            "pre_migrate_advisory"):
                    self.total_interventions += 1
                    self.traffic_predictor.pre_migration_success += 1
                    self.successful_interventions += 1

        # 3. Congestion monitoring per leaf
        for sw in network.switches.values():
            if sw.layer == "leaf" and sw.is_active:
                buf = min(1.0, sw.power_state * np.random.uniform(0.3, 0.9))
                self.congestion_controller.monitor_buffer(sw.id, buf)

        # 4. Link utilization tracking for load balancer
        for cable in network.cables.values():
            if cable.is_active:
                util = (np.random.uniform(0.1, 0.8) if cable.is_cross_room
                        else np.random.uniform(0.2, 0.6))
                self.load_balancer.update_link_utilization(
                    cable.from_node, cable.to_node, util)

    # ------------------------------------------------------------------
    # Modifier methods (consumed by the simulation driver)
    # ------------------------------------------------------------------

    def get_failure_rate_modifier(self) -> float:
        """Better load balancing = less link stress = fewer failures."""
        cong = self.congestion_controller.get_congestion_rate_modifier()
        imbalance = self.load_balancer.get_imbalance_score()
        balance = 1.0 - imbalance * 0.2
        return cong * balance

    def get_throughput_modifier(self) -> float:
        """Better scheduling + load balancing = higher throughput."""
        workload = self.workload_scheduler.get_throughput_modifier()
        imbalance = self.load_balancer.get_imbalance_score()
        lb = 1.0 + (1.0 - imbalance) * 0.15
        return workload * lb

    def get_availability_modifier(self) -> float:
        """Pre-migration reduces downtime from spine failures (0-1)."""
        if self.traffic_predictor.pre_migration_events > 0:
            rate = (self.traffic_predictor.pre_migration_success
                    / max(self.traffic_predictor.pre_migration_events, 1))
        else:
            rate = 0.0
        return rate * 0.3

    # ------------------------------------------------------------------

    def get_stats(self) -> Dict:
        return {
            "total_interventions": self.total_interventions,
            "successful_interventions": self.successful_interventions,
            "intervention_success_rate": (
                self.successful_interventions
                / max(self.total_interventions, 1) * 100),
            "implementation_cost": self.implementation_cost,
            "failure_rate_modifier": self.get_failure_rate_modifier(),
            "throughput_modifier": self.get_throughput_modifier(),
            "availability_improvement": self.get_availability_modifier(),
            "load_balancer": self.load_balancer.get_stats(),
            "traffic_predictor": self.traffic_predictor.get_stats(),
            "congestion_controller": self.congestion_controller.get_stats(),
            "workload_scheduler": self.workload_scheduler.get_stats(),
        }
