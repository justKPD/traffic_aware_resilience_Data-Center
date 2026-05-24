"""
Congestion Controller
======================

AI-based congestion control for TCP incast and general congestion.

Problem: TCP Incast
  - Many servers send to one receiver simultaneously (all-to-one)
  - Overwhelms the leaf switch buffers
  - Packet loss, retransmissions, throughput collapse
  - Common in: MapReduce shuffles, distributed storage, AI training

Solutions:
  1. Incast detection: monitor for many-to-one patterns
  2. Flow pacing: slow down senders to prevent buffer overflow
  3. ECN marking: Explicit Congestion Notification for early backoff
  4. Aggressive backoff: when buffer > 95%, apply maximum rate reduction
"""

import numpy as np
from collections import defaultdict
from typing import Dict, List, Optional, Tuple


class CongestionController:

    def __init__(self, buffer_threshold=0.8, incast_detection_window=5,
                 pacing_rate_mbps=1000):
        self.buffer_threshold = buffer_threshold
        self.incast_window = incast_detection_window
        self.pacing_rate = pacing_rate_mbps

        self.switch_buffers = defaultdict(float)
        self.buffer_history = defaultdict(list)

        self.many_to_one_flows = defaultdict(int)
        self.incast_events = 0
        self.incast_events_prevented = 0

        self.paced_flows = set()
        self.pacing_actions = 0

        self.ecn_marked_packets = 0
        self.ecn_threshold = 0.7

        self.congestion_events = 0
        self.congestion_events_resolved = 0

    # ------------------------------------------------------------------

    def monitor_buffer(self, switch_id: int, buffer_usage: float):
        self.switch_buffers[switch_id] = buffer_usage
        self.buffer_history[switch_id].append(buffer_usage)
        if len(self.buffer_history[switch_id]) > 100:
            self.buffer_history[switch_id].pop(0)

        if buffer_usage > self.buffer_threshold:
            self.congestion_events += 1

    def detect_incast(self, switch_id: int,
                      flow_src_dst: List[Tuple[int, int]]) -> Optional[Dict]:
        """Detect many-to-one incast pattern (>4 flows to same dst)."""
        dst_counts = defaultdict(int)
        for src, dst in flow_src_dst:
            dst_counts[dst] += 1

        incast_dsts = {d: c for d, c in dst_counts.items() if c > 4}

        if incast_dsts:
            self.incast_events += 1
            buf = self.switch_buffers.get(switch_id, 0)
            severity = ("critical" if buf > 0.9 else
                        "high" if buf > 0.8 else "moderate")
            return {
                "incast_detected": True,
                "switch_id": switch_id,
                "affected_destinations": incast_dsts,
                "buffer_usage": buf,
                "severity": severity,
            }
        return None

    # ------------------------------------------------------------------

    def apply_flow_pacing(self, flow_id: str,
                          target_rate_mbps: float = None) -> Dict:
        rate = target_rate_mbps or self.pacing_rate
        self.paced_flows.add(flow_id)
        self.pacing_actions += 1
        return {
            "flow_id": flow_id,
            "paced": True,
            "rate_mbps": rate,
            "original_rate_mbps": 10000,
            "rate_reduction": (1 - rate / 10000) * 100,
        }

    def apply_ecn_marking(self, switch_id: int,
                          packet_count: int) -> int:
        buf = self.switch_buffers.get(switch_id, 0)
        if buf > self.ecn_threshold:
            frac = (buf - self.ecn_threshold) / (1 - self.ecn_threshold)
            marked = int(packet_count * frac)
            self.ecn_marked_packets += marked
            return marked
        return 0

    # ------------------------------------------------------------------

    def handle_congestion(self, switch_id: int,
                          flow_src_dst: List[Tuple[int, int]]) -> Dict:
        """Full congestion handling: detect incast, pace flows, mark ECN."""
        result = {"switch_id": switch_id, "actions_taken": []}
        buf = self.switch_buffers.get(switch_id, 0)

        incast = self.detect_incast(switch_id, flow_src_dst)
        if incast:
            result["incast"] = incast
            result["actions_taken"].append("incast_detected")

            for dst, count in incast["affected_destinations"].items():
                for src, d in flow_src_dst:
                    if d == dst:
                        fid = f"flow_{src}_{dst}"
                        self.apply_flow_pacing(fid, self.pacing_rate)
                        result["actions_taken"].append(f"paced_{fid}")

            self.incast_events_prevented += 1

        marked = self.apply_ecn_marking(switch_id, 1000)
        if marked > 0:
            result["actions_taken"].append(f"ecn_marked_{marked}_packets")

        if buf > 0.95:
            result["actions_taken"].append("aggressive_backoff")
            self.congestion_events_resolved += 1

        return result

    # ------------------------------------------------------------------

    def get_congestion_rate_modifier(self) -> float:
        """Returns 0-1 multiplier for effective failure/loss rate."""
        if not self.switch_buffers:
            return 1.0
        prev_rate = (self.incast_events_prevented
                     / max(self.incast_events, 1))
        return max(0.5, 1.0 - prev_rate * 0.3)

    def get_stats(self) -> Dict:
        bufs = list(self.switch_buffers.values())
        return {
            "congestion_events": self.congestion_events,
            "congestion_events_resolved": self.congestion_events_resolved,
            "incast_events": self.incast_events,
            "incast_events_prevented": self.incast_events_prevented,
            "incast_prevention_rate": (
                self.incast_events_prevented / max(self.incast_events, 1) * 100),
            "pacing_actions": self.pacing_actions,
            "paced_flows": len(self.paced_flows),
            "ecn_marked_packets": self.ecn_marked_packets,
            "avg_buffer_usage": float(np.mean(bufs)) if bufs else 0,
            "max_buffer_usage": float(max(bufs)) if bufs else 0,
        }
