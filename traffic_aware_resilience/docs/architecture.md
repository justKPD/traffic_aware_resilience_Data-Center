# Architecture

## Component Overview

```
                 ┌─────────────────────────────────┐
                 │ TrafficAwareNetworkResilienceAI  │
                 │         (main interface)         │
                 └───────────┬─────────────────────┘
                             │
     ┌───────────┬───────────┼───────────┬────────────┐
     │           │           │           │            │
┌────▼────┐ ┌────▼────┐ ┌───▼────┐ ┌────▼─────┐
│ Adaptive│ │ Traffic │ │Congest.│ │ Workload │
│  Load   │ │Predictor│ │ Ctrl   │ │Scheduler │
│Balancer │ │         │ │        │ │          │
└─────────┘ └─────────┘ └────────┘ └──────────┘
```

## Adaptive Load Balancer

Replaces static ECMP hashing.  Flows are classified as **elephant**
(>100 packets or >1 MB) or **mouse** (everything else).  Elephants
are assigned to the least-loaded path; mice use weighted random
selection favouring lighter links.  When a link exceeds the
rehash threshold (default 70% utilization), elephant flows on that
path are rehashed to better alternatives.

Link utilization is tracked via an Exponentially Weighted Moving
Average (EWMA, alpha=0.2) for smoothing.

## Traffic Predictor

Models three traffic components:

| Component | Model | Parameters |
|-----------|-------|------------|
| Diurnal | Cosine + 2nd harmonic | amplitude, phase, baseline |
| Weekly | Weekend factor | 0.6 (60% of weekday load) |
| Trend | Linear | 0.0001/day increase |

Parameters are updated online with gradient descent (lr=0.01) as
actual measurements come in.  Spine overload is predicted when the
estimated load exceeds 85% of capacity, triggering a pre-migration
recommendation.

## Congestion Controller

Four-stage pipeline:

1. **Buffer monitoring**: track per-switch buffer utilization
2. **Incast detection**: flag when >4 simultaneous flows target
   the same destination
3. **Flow pacing**: slow down incast sources from 10 Gbps to
   a configurable rate (default 1 Gbps)
4. **ECN marking**: mark packets proportionally when buffer
   exceeds 70%, giving TCP receivers early congestion signals

## Workload Scheduler

Topology-aware workload placement:

| Workload | Strategy | Cross-room traffic reduction |
|----------|----------|------------------------------|
| HPC training | Single-room affinity | 90% |
| Web service | Distributed redundancy | 0% |
| Batch job | Capacity-optimized | 50% |

Large data transfers are either bandwidth-reserved (high priority)
or staggered to off-peak hours (low priority, 4h delay).

## Data Flow

1. Every 4 simulated hours, `apply_daily_optimization()` runs.
2. Traffic predictor generates per-room load forecasts.
3. Spine overload predictions trigger pre-migration.
4. Leaf buffer levels are monitored for congestion.
5. Link utilization feeds into the load balancer's EWMA tracker.
6. Modifiers (`failure_rate_modifier`, `throughput_modifier`,
   `availability_modifier`) are returned to the simulation driver.
