"""
Traffic Predictor
==================

Predicts data center traffic patterns for proactive network management.

Models:
  - Diurnal cycle (sinusoidal + Fourier harmonics)
  - Weekly cycle (weekday vs weekend)
  - Long-term trend (gradual load increase)
  - Per-room adjustments (HPC rooms peak differently)

Key use case: predict spine overload and trigger pre-migration of
traffic before congestion hits.
"""

import numpy as np
from collections import defaultdict
from typing import Dict


class TrafficPredictor:

    def __init__(self):
        self.diurnal_amplitude = 0.3
        self.diurnal_phase = 14.0       # peak at 14:00
        self.diurnal_baseline = 0.5

        self.weekend_factor = 0.6
        self.trend_rate = 0.0001

        self.predictions = []
        self.actuals = []
        self.mae_history = []

        self.room_models = defaultdict(
            lambda: {"amplitude": 0.3, "phase": 14.0, "baseline": 0.5})

        self.spine_capacity = defaultdict(float)
        self.spine_predicted_load = defaultdict(float)
        self.pre_migration_events = 0
        self.pre_migration_success = 0

    # ------------------------------------------------------------------

    def predict_traffic(self, hour: int, day_of_week: int, day: int,
                        room_id: int = 0) -> Dict[str, float]:
        """Predict traffic load for the given time parameters."""
        # diurnal (fundamental + 2nd harmonic)
        diurnal = self.diurnal_baseline + self.diurnal_amplitude * np.cos(
            2 * np.pi * (hour - self.diurnal_phase) / 24)
        diurnal += 0.05 * np.cos(
            4 * np.pi * (hour - self.diurnal_phase) / 24)

        weekly = self.weekend_factor if day_of_week >= 5 else 1.0
        trend = self.trend_rate * day

        room_adj = (self.room_models[room_id]["baseline"]
                    - self.diurnal_baseline) * 0.3

        predicted = (diurnal + trend + room_adj) * weekly
        predicted = max(0.05, min(predicted, 1.0))

        confidence = max(0.6, 1.0 - 0.02 * abs(hour - 12))
        margin = 0.1 / confidence

        return {
            "predicted_load": predicted,
            "confidence": confidence,
            "lower_bound": max(0, predicted - margin),
            "upper_bound": min(1, predicted + margin),
            "is_peak": predicted > 0.7,
            "is_off_peak": predicted < 0.3,
        }

    def predict_spine_overload(self, spine_id: int, room_id: int,
                                hour: int, day_of_week: int,
                                day: int, current_spine_load: float,
                                spine_capacity: float) -> Dict:
        """Predict whether a spine will be overloaded."""
        tp = self.predict_traffic(hour, day_of_week, day, room_id)
        predicted_load = current_spine_load + (
            tp["predicted_load"] - 0.5) * spine_capacity

        overload = predicted_load > spine_capacity * 0.85
        critical = predicted_load > spine_capacity * 0.95

        rec = "normal"
        if critical:
            rec = "pre_migrate_critical"
            self.pre_migration_events += 1
        elif overload:
            rec = "pre_migrate_advisory"
            self.pre_migration_events += 1

        self.spine_predicted_load[spine_id] = predicted_load
        self.spine_capacity[spine_id] = spine_capacity

        return {
            "spine_id": spine_id,
            "predicted_load": predicted_load,
            "spine_capacity": spine_capacity,
            "utilization_predicted": predicted_load / max(spine_capacity, 0.1),
            "overload_risk": overload,
            "critical_risk": critical,
            "recommendation": rec,
            "traffic_prediction": tp,
        }

    # ------------------------------------------------------------------

    def record_actual(self, actual_load: float, hour: int,
                      room_id: int = 0):
        """Record actual load for online learning."""
        self.actuals.append(actual_load)

        predicted = self.diurnal_baseline + self.diurnal_amplitude * np.cos(
            2 * np.pi * (hour - self.diurnal_phase) / 24)

        error = actual_load - predicted
        lr = 0.01

        self.diurnal_baseline += lr * error
        self.diurnal_amplitude += lr * error * np.cos(
            2 * np.pi * (hour - self.diurnal_phase) / 24)
        self.diurnal_amplitude = max(0.1, min(self.diurnal_amplitude, 0.5))
        self.diurnal_baseline = max(0.3, min(self.diurnal_baseline, 0.7))

        self.mae_history.append(abs(error))

    def get_stats(self) -> Dict:
        mae = float(np.mean(self.mae_history)) if self.mae_history else 0
        return {
            "mean_absolute_error": mae,
            "prediction_count": len(self.actuals),
            "pre_migration_events": self.pre_migration_events,
            "pre_migration_success": self.pre_migration_success,
            "diurnal_baseline": self.diurnal_baseline,
            "diurnal_amplitude": self.diurnal_amplitude,
        }
