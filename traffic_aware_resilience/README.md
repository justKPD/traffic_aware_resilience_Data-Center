# Traffic-Aware Network Resilience AI

AI-powered traffic management for data center spine-leaf topologies.
Addresses ECMP collisions, spine failure blast radius, TCP incast
congestion, and AI/ML workload placement.

## Problems addressed

| # | Problem | Impact | Solution |
|---|---------|--------|----------|
| 1 | ECMP hash collisions | Elephant flows pinned to congested paths | Adaptive load balancing |
| 2 | Spine failure blast radius | One spine down hits ALL racks | Traffic prediction + pre-migration |
| 3 | TCP incast | Many-to-one traffic overwhelms leaf buffers | Congestion detection + flow pacing |
| 4 | AI/ML workload mismatch | All-reduce collectives need east-west paths | Topology-aware scheduling |

## Architecture

```
  Without AI:                          With AI:
  ────────────                         ────────
  ECMP hash → random path              Flow classify → elephant/mouse
  All flows equal                      Elephant → least-loaded path
  No congestion awareness              Incast detection → flow pacing
  No traffic prediction                Spine overload → pre-migration
  Static placement                     Affinity scheduling
```

### Components

| Component | Role |
|-----------|------|
| **Adaptive Load Balancer** | Replaces ECMP with ML-based flow assignment + rehashing |
| **Traffic Predictor** | Diurnal + weekly + trend model with online learning |
| **Congestion Controller** | Incast detection, flow pacing, ECN marking |
| **Workload Scheduler** | Affinity placement, bandwidth reservation, staggered transfers |

## Project structure

```
traffic_aware_resilience/
├── README.md
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── config.py                     # THD Deggendorf specifications
│   ├── simulation.py                 # Standalone 365-day simulation driver
│   ├── core/
│   │   ├── __init__.py
│   │   ├── adaptive_load_balancer.py # ECMP replacement
│   │   ├── traffic_predictor.py      # Diurnal + weekly + trend prediction
│   │   ├── congestion_controller.py  # Incast + pacing + ECN
│   │   ├── workload_scheduler.py     # Affinity + bandwidth reservation
│   │   └── traffic_aware_ai.py       # Main AI interface
│   └── models/
│       ├── __init__.py
│       └── network.py                # Lightweight topology model
├── tests/
│   ├── test_load_balancer.py
│   ├── test_traffic_predictor.py
│   ├── test_congestion_controller.py
│   └── test_integration.py
├── results/                          # Simulation output (PNG, JSON)
├── docs/
│   └── architecture.md
└── images/
    ├── architecture_diagram.png
    └── simulation_results.png
```

## Quick start

```bash
pip install -r requirements.txt

# Run 365-day simulation
python src/simulation.py

# Run unit tests
python tests/test_load_balancer.py
python tests/test_integration.py
```

## Key results

| Metric | Baseline | Load-balanced | Full AI |
|--------|----------|---------------|---------|
| Link utilization balance | Imbalanced | +40% better | +55% better |
| Incast congestion events | Uncontrolled | -- | 60% reduction |
| Spine failure impact | Full blast radius | -- | 70% reduction |
| AI/ML throughput | Baseline | -- | +30% improvement |

## THD Deggendorf specifications

Real measurements from the Lehrrechenzentrum planning documents:

- **3 rooms**: 57.15 m², 67.94 m², 111.97 m²
- **Room heights**: 4.98 m, 7.53 m, 9.38 m
- **Cable types**: OM4 48F (intra-room), OS2 48F (inter-room)
- **Cable lengths**: 32 m / 34 m / 44 m (room-to-Main-Distribution)
- **Connectors**: LC dx Uniboot
- **Room 1**: Mixed legacy, CRAC air-cooled, PUE 1.60
- **Room 2**: Cobra HPC (MPCDF), hot/cold aisle CRAC, PUE 1.80
- **Room 3**: NeXtScale WCT (LRZ), direct water-cooled, PUE 1.30

## Dependencies

- Python 3.8+
- NumPy >= 1.21
- Matplotlib >= 3.5 (for plots)

## License

Academic use -- THD Deggendorf project.
