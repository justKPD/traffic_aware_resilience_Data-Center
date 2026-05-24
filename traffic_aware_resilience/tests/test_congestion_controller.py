"""Unit tests for CongestionController."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.core.congestion_controller import CongestionController


def test_monitor_buffer():
    cc = CongestionController()
    cc.monitor_buffer(1, 0.85)
    assert cc.switch_buffers[1] == 0.85
    assert cc.congestion_events == 1


def test_incast_detection():
    cc = CongestionController()
    cc.monitor_buffer(1, 0.9)
    flows = [(i, 100) for i in range(8)]
    result = cc.detect_incast(1, flows)
    assert result is not None
    assert result["incast_detected"] is True


def test_no_incast():
    cc = CongestionController()
    flows = [(1, 10), (2, 20)]
    result = cc.detect_incast(1, flows)
    assert result is None


def test_flow_pacing():
    cc = CongestionController()
    r = cc.apply_flow_pacing("f1", 500)
    assert r["paced"] is True
    assert "f1" in cc.paced_flows


def test_ecn_marking():
    cc = CongestionController()
    cc.monitor_buffer(1, 0.9)
    marked = cc.apply_ecn_marking(1, 1000)
    assert marked > 0


def test_handle_congestion():
    cc = CongestionController()
    cc.monitor_buffer(1, 0.85)
    flows = [(i, 100) for i in range(6)]
    result = cc.handle_congestion(1, flows)
    assert "actions_taken" in result
    assert len(result["actions_taken"]) > 0


if __name__ == "__main__":
    test_monitor_buffer()
    test_incast_detection()
    test_no_incast()
    test_flow_pacing()
    test_ecn_marking()
    test_handle_congestion()
    print("All CongestionController tests passed.")
