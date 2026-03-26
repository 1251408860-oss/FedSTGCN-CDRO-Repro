# Graph Schema

Required graph fields for the weak-supervision/CDRO experiments:

- `x`
- `y`
- `edge_index`
- `edge_type`
- `train_mask`
- `val_mask`
- `test_mask`
- `temporal_test_mask`
- `window_idx`
- `ip_idx`
- `source_ips`
- `weak_label`
- `weak_posterior`
- `weak_agreement`
- `weak_uncertainty`
- `rho_proxy`

Representative shape: `x=(5976, 7)`, `edge_index=(2, 8142)`.

Feature index:

- `ln(N+1)` -> `0`
- `ln(T+1)` -> `1`
- `entropy` -> `2`
- `D_observed` -> `3`
- `pkt_rate` -> `4`
- `avg_pkt_size` -> `5`
- `port_diversity` -> `6`
