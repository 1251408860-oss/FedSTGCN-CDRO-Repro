# Runtime Cost Summary

## Methodology
- CPU-only benchmark with `torch.set_num_threads(1)`.
- Inference latency is measured as full-graph forward time over saved models, averaged over 20 timed repeats after 5 warmup passes.
- `wall` is the outer process time recorded by the suite runner; `train` is the model-only runtime reported inside `results.json`.

## main

### One-time preprocessing
- Weak-label generation: 3.27s.
- Protocol graph preparation: 1.63 +/- 0.03s per protocol (4 protocols, 6.52s total).
- Fixed suite setup total: 9.79s.

### Per-run training
- Noisy-CE: wall=2.52 +/- 0.23s, train=0.71 +/- 0.15s, delta vs Noisy-CE wall=+0.00s.
- Posterior-CE: wall=2.40 +/- 0.27s, train=0.64 +/- 0.17s, delta vs Noisy-CE wall=-0.12s.
- CDRO-Fixed: wall=2.59 +/- 0.20s, train=0.78 +/- 0.14s, delta vs Noisy-CE wall=+0.07s.
- CDRO-UG (sw0): wall=2.27 +/- 0.24s, train=0.59 +/- 0.16s, delta vs Noisy-CE wall=-0.26s.
- CDRO-UG + PriorCorr: wall=2.35 +/- 0.28s, train=0.62 +/- 0.15s, delta vs Noisy-CE wall=-0.17s.

### Per-run inference
- Noisy-CE: forward=72.30 +/- 4.96ms, 82993.7 nodes/s, 2555.4 windows/s, ~0.39ms per temporal window, delta vs Noisy-CE forward=+0.00ms.
- Posterior-CE: forward=68.97 +/- 4.61ms, 86993.7 nodes/s, 2678.5 windows/s, ~0.37ms per temporal window, delta vs Noisy-CE forward=-3.32ms.
- CDRO-Fixed: forward=68.31 +/- 5.03ms, 87897.8 nodes/s, 2706.4 windows/s, ~0.37ms per temporal window, delta vs Noisy-CE forward=-3.99ms.
- CDRO-UG (sw0): forward=72.58 +/- 8.34ms, 83232.6 nodes/s, 2562.7 windows/s, ~0.39ms per temporal window, delta vs Noisy-CE forward=+0.28ms.
- CDRO-UG + PriorCorr: forward=71.21 +/- 5.45ms, 84337.2 nodes/s, 2596.7 windows/s, ~0.39ms per temporal window, delta vs Noisy-CE forward=-1.09ms.

### Reading
- CDRO-UG changes wall time by -0.26s relative to Noisy-CE and changes full-graph forward latency by +0.28ms.
- Under the current CPU-only setting, the rewritten UG does not introduce a meaningful deployment-time penalty; the extra method complexity mainly remains within the same runtime scale as the baseline family.

## batch2

### One-time preprocessing
- Weak-label generation: 1.87s.
- Protocol graph preparation: 1.75 +/- 0.05s per protocol (4 protocols, 6.99s total).
- Fixed suite setup total: 8.86s.

### Per-run training
- Noisy-CE: wall=2.27 +/- 0.20s, train=0.58 +/- 0.14s, delta vs Noisy-CE wall=+0.00s.
- Posterior-CE: wall=2.29 +/- 0.22s, train=0.57 +/- 0.13s, delta vs Noisy-CE wall=+0.02s.
- CDRO-Fixed: wall=2.19 +/- 0.17s, train=0.54 +/- 0.14s, delta vs Noisy-CE wall=-0.08s.
- CDRO-UG (sw0): wall=2.19 +/- 0.15s, train=0.56 +/- 0.14s, delta vs Noisy-CE wall=-0.08s.
- CDRO-UG + PriorCorr: wall=2.34 +/- 0.32s, train=0.62 +/- 0.18s, delta vs Noisy-CE wall=+0.06s.

### Per-run inference
- Noisy-CE: forward=51.58 +/- 2.10ms, 91212.2 nodes/s, 2970.5 windows/s, ~0.34ms per temporal window, delta vs Noisy-CE forward=+0.00ms.
- Posterior-CE: forward=54.31 +/- 3.60ms, 86846.3 nodes/s, 2828.3 windows/s, ~0.35ms per temporal window, delta vs Noisy-CE forward=+2.73ms.
- CDRO-Fixed: forward=58.19 +/- 4.91ms, 81263.8 nodes/s, 2646.5 windows/s, ~0.38ms per temporal window, delta vs Noisy-CE forward=+6.61ms.
- CDRO-UG (sw0): forward=53.17 +/- 2.31ms, 88504.9 nodes/s, 2882.3 windows/s, ~0.35ms per temporal window, delta vs Noisy-CE forward=+1.60ms.
- CDRO-UG + PriorCorr: forward=55.70 +/- 4.31ms, 84798.3 nodes/s, 2761.6 windows/s, ~0.36ms per temporal window, delta vs Noisy-CE forward=+4.12ms.

### Reading
- CDRO-UG changes wall time by -0.08s relative to Noisy-CE and changes full-graph forward latency by +1.60ms.
- Under the current CPU-only setting, the rewritten UG does not introduce a meaningful deployment-time penalty; the extra method complexity mainly remains within the same runtime scale as the baseline family.
