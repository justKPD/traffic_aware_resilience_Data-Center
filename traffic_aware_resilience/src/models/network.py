"""
Lightweight network model for standalone simulation.
Same interface as the self_healing_network version.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class NetworkNode:
    id: int
    node_type: str
    dc_id: int
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    is_active: bool = True
    is_cross_room: bool = False
    layer: str = ""
    power_consumption: float = 0.0
    base_power: float = 0.0
    cpu_utilization: float = 0.5
    power_state: float = 1.0


@dataclass
class Cable:
    id: int
    from_node: int
    to_node: int
    cable_type: str
    length: float
    fiber_count: int = 48
    is_active: bool = True
    is_cross_room: bool = False


class NetworkTopology:

    def __init__(self):
        self.servers: Dict[int, NetworkNode] = {}
        self.switches: Dict[int, NetworkNode] = {}
        self.cables: Dict[int, Cable] = {}
        self.adjacency_list: Dict[int, List[Tuple[int, Cable]]] = defaultdict(list)

    def add_node(self, node: NetworkNode):
        if node.node_type == "server":
            self.servers[node.id] = node
        else:
            self.switches[node.id] = node

    def add_cable(self, cable: Cable):
        self.cables[cable.id] = cable
        self.adjacency_list[cable.from_node].append((cable.to_node, cable))
        self.adjacency_list[cable.to_node].append((cable.from_node, cable))

    def _get_node(self, node_id: int) -> Optional[NetworkNode]:
        if node_id in self.servers:
            return self.servers[node_id]
        return self.switches.get(node_id)

    def stats(self) -> Dict:
        return {
            "servers": len(self.servers),
            "switches": len(self.switches),
            "cables": len(self.cables),
            "active_servers": sum(1 for s in self.servers.values() if s.is_active),
            "active_switches": sum(1 for s in self.switches.values() if s.is_active),
            "active_cables": sum(1 for c in self.cables.values() if c.is_active),
        }
