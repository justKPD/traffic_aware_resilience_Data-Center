"""Unit tests for TrafficPredictor."""

import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.core.traffic_predictor import TrafficPredictor


def test_peak_hour():
    tp = TrafficPredictor()
    pred = tp.predict_traffic(14, 2, 100)
    assert pred["is_peak"] is True or pred["predicted_load"] > 0.5


def test_off_peak():
    tp = TrafficPredictor()
    pred = tp.predict_traffic(3, 2, 100)
    assert pred["predicted_load"] < 0.7


def test_weekend_reduction():
    tp = TrafficPredictor()
    weekday = tp.predict_traffic(14, 2, 100)["predicted_load"]
    weekend = tp.predict_traffic(14, 6, 100)["predicted_load"]
    assert weekend < weekday


def test_online_learning():
    tp = TrafficPredictor()
    for h in range(24):
        pred = tp.predict_traffic(h, 2, 0)
        actual = pred["predicted_load"] + 0.05
        tp.record_actual(actual, h)
    assert len(tp.mae_history) == 24
    assert tp.get_stats()["mean_absolute_error"] > 0


def test_spine_overload():
    tp = TrafficPredictor()
    result = tp.predict_spine_overload(1, 1, 14, 2, 100, 0.9, 1.0)
    assert "recommendation" in result
    assert isinstance(result["overload_risk"], (bool, np.bool_))


if __name__ == "__main__":
    test_peak_hour()
    test_off_peak()
    test_weekend_reduction()
    test_online_learning()
    test_spine_overload()
    print("All TrafficPredictor tests passed.")
