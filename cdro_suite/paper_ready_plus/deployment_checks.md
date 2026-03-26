# Deployment-Oriented Checks

Scope: external-J (`batch2_baselineplus_s3_v1`) with thresholds frozen from the matched main-batch run (`same protocol + method + seed`).

Latency and throughput remain reported in `runtime_costs.md`; this note adds the missing deployment-side checks: frozen-threshold transfer, first-alert delay, and analyst-facing benign alert burden.

| Method | Tuned F1 / FPR | Tuned detect-rate / delay | Frozen F1 / FPR | Frozen detect-rate / delay | Frozen benign alerts | Frozen benign IP burden |
|---|---:|---:|---:|---:|---:|---:|
| Noisy-CE | 0.888 +- 0.029 / 0.270 +- 0.080 | 1.000 +- 0.000 / 0.06 +- 0.08 windows | 0.874 +- 0.030 / 0.168 +- 0.089 | 0.990 +- 0.017 / 0.58 +- 0.73 windows | 63.4 +- 27.3 FP / 1676 +- 886 per 10k benign | 0.904 +- 0.270 flagged benign IP rate |
| CDRO-Fixed | 0.888 +- 0.030 / 0.237 +- 0.073 | 1.000 +- 0.000 / 0.10 +- 0.10 windows | 0.827 +- 0.087 / 0.239 +- 0.274 | 0.987 +- 0.025 / 0.64 +- 1.22 windows | 120.4 +- 204.3 FP / 2386 +- 2738 per 10k benign | 0.806 +- 0.356 flagged benign IP rate |
| CDRO-UG(sw0) | 0.885 +- 0.026 / 0.226 +- 0.052 | 1.000 +- 0.000 / 0.10 +- 0.10 windows | 0.860 +- 0.053 / 0.096 +- 0.069 | 0.978 +- 0.027 / 0.88 +- 1.08 windows | 36.1 +- 25.3 FP / 958 +- 689 per 10k benign | 0.715 +- 0.437 flagged benign IP rate |

## Reading

- Frozen-threshold `CDRO-UG(sw0)` vs `Noisy-CE`: delta F1 `-0.014`, p=`0.227728`; delta FPR `-0.072`, p=`0.00219673`; delta benign FP count `-27.3`, p=`0.00170857`; delta benign alerts / 10k `-718`, p=`0.00219673`; delta benign-IP flagged rate `-0.189`, p=`0.0627288`.
- Frozen-threshold `CDRO-UG(sw0)` vs `CDRO-Fixed`: delta F1 `+0.033`, p=`0.146693`; delta FPR `-0.143`, p=`0.0441787`; delta benign FP count `-84.3`, p=`0.0344154`; delta benign alerts / 10k `-1428`, p=`0.0441787`; delta benign-IP flagged rate `-0.091`, p=`0.500122`.
- With tuned thresholds, all three methods detect essentially all attack IPs and median first-alert delay is 0 windows.
- With thresholds frozen from the main batch, CDRO-UG keeps the lowest external-J FPR and also yields the lowest benign alert burden by absolute FP count and FP-per-10k-benign. This makes the deployment gain easier to interpret in analyst-facing terms.
- That benign-side reduction is not free: CDRO-UG still trades some frozen-threshold F1 and attack-IP detection coverage/delay for the lower alert burden. This is the correct deployment tradeoff to report rather than hide.

Artifacts: `table18_deployment_checks.csv`, `deployment_summary.json`, `frozen_externalJ_significance.json`.