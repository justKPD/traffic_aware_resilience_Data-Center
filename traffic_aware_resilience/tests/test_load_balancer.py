"""Unit tests for AdaptiveLoadBalancer."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.core.adaptive_load_balancer import AdaptiveLoadBalancer


def test_classify_mouse():
    lb = AdaptiveLoadBalancer()
    ftype = lb.classify_flow("f1", 10, 5000)
    assert ftype == "mouse"
    assert "f1" in lb.mouse_flows


def test_classify_elephant():
    lb = AdaptiveLoadBalancer(elephant_threshold_packets=50)
    lb.classify_flow("f2", 60, 2000000)
    assert "f2" in lb.elephant_flows


def test_assign_path_elephant():
    lb = AdaptiveLoadBalancer()
    lb.classify_flow("e1", 200, 5000000)
    paths = [[1, 2, 3], [4, 5, 6]]
    chosen = lb.assign_path("e1", paths)
    assert chosen in paths


def test_update_utilization():
    lb = AdaptiveLoadBalancer()
    lb.update_link_utilization(10, 20, 0.5)
    key = (10, 20)
    assert key in lb.link_ewma
    assert abs(lb.link_ewma[key] - 0.5 * 0.2) < 0.01


def test_imbalance_score():
    lb = AdaptiveLoadBalancer()
    lb.update_link_utilization(1, 2, 0.5)
    lb.update_link_utilization(3, 4, 0.5)
    score = lb.get_imbalance_score()
    assert 0 <= score <= 1


if __name__ == "__main__":
    test_classify_mouse()
    test_classify_elephant()
    test_assign_path_elephant()
    test_update_utilization()
    test_imbalance_score()
    print("All AdaptiveLoadBalancer tests passed.")
