# Low-Cost External Extension Plan

## Recommended strengthening path

The cheapest useful external strengthening is not another deployment table. It is the appendix-facing scenario-wise tuned-threshold consistency readout captured in `table20_external_direction_consistency.csv` and `external_direction_consistency.md`.

Safe manuscript reading:

- `CDRO-UG (sw0)` lowers tuned-threshold `FPR` in `3/4` external scenarios (`J/K/L`).
- The strongest support remains `External-J`.
- `External-K` provides smaller paired support on tuned-threshold `FPR`.
- `External-L` is directional only.
- `External-I` reverses.
- Pooled external remains non-significant, so this is partial consistency rather than a universal transfer claim.

## Why not add external-K deployment transfer as a headline

A real low-cost deployment rerun was already executed on `batch2_k_baselineplus_s3_v1` with:

`wsl -d Ubuntu2 bash -lc 'export PYTHONPATH=/home/user/FedSTGCN; /home/user/miniconda3/envs/DL/bin/python /home/user/FedSTGCN/make_deployment_artifacts.py --main-summary /home/user/FedSTGCN/cdro_suite/main_baselineplus_s3_v1/cdro_summary.json --external-summary /home/user/FedSTGCN/cdro_suite/batch2_k_baselineplus_s3_v1/cdro_summary.json --output-dir /home/user/FedSTGCN/cdro_suite/deployment_checks_k_s3_v1 --paper-dir /home/user/FedSTGCN/cdro_suite/deployment_checks_k_s3_v1'`

Output directory:

- `/home/user/FedSTGCN/cdro_suite/deployment_checks_k_s3_v1`

Observed frozen-threshold result against `Noisy-CE`:

- `FPR`: `0.1090 -> 0.1507`, `delta = +0.04169`, `p = 0.98536`
- `F1`: `0.8635 -> 0.8356`, `delta = -0.02786`, `p = 0.05297`

Therefore the external-K deployment transfer does not strengthen the BlockSys-facing headline. If mentioned at all, it should remain an internal boundary note rather than a manuscript table.
