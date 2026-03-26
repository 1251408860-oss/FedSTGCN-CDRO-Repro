# Per-Attack-Family Breakdown

This breakdown is pooled over the four protocol splits. That choice is deliberate: `weak_attack_strategy_ood` is a mimic-holdout protocol, so a protocol-only family table would collapse `slowburn` and `burst` to zero-count rows.

## main

| Family | Method | F1 | Recall | FPR |
|---|---|---:|---:|---:|
| slowburn | Noisy-CE | 0.874 +- 0.034 | 0.892 +- 0.079 | 0.144 +- 0.077 |
| slowburn | CDRO-Fixed | 0.866 +- 0.051 | 0.885 +- 0.086 | 0.147 +- 0.064 |
| slowburn | CDRO-UG(sw0) | 0.869 +- 0.038 | 0.887 +- 0.082 | 0.144 +- 0.099 |
| burst | Noisy-CE | 0.468 +- 0.091 | 0.516 +- 0.134 | 0.144 +- 0.077 |
| burst | CDRO-Fixed | 0.444 +- 0.074 | 0.488 +- 0.100 | 0.147 +- 0.064 |
| burst | CDRO-UG(sw0) | 0.433 +- 0.086 | 0.464 +- 0.109 | 0.144 +- 0.099 |
| mimic | Noisy-CE | 0.773 +- 0.088 | 0.991 +- 0.012 | 0.182 +- 0.098 |
| mimic | CDRO-Fixed | 0.757 +- 0.103 | 0.988 +- 0.013 | 0.208 +- 0.131 |
| mimic | CDRO-UG(sw0) | 0.775 +- 0.097 | 0.993 +- 0.009 | 0.183 +- 0.111 |

- Main-batch readout: `burst` is the hardest family, while `slowburn` and `mimic` remain substantially easier.

## external_j

| Family | Method | F1 | Recall | FPR |
|---|---|---:|---:|---:|
| slowburn | Noisy-CE | 0.848 +- 0.036 | 0.950 +- 0.020 | 0.294 +- 0.077 |
| slowburn | CDRO-Fixed | 0.858 +- 0.033 | 0.943 +- 0.034 | 0.257 +- 0.069 |
| slowburn | CDRO-UG(sw0) | 0.860 +- 0.035 | 0.935 +- 0.023 | 0.236 +- 0.057 |
| burst | Noisy-CE | 0.507 +- 0.088 | 0.995 +- 0.014 | 0.294 +- 0.077 |
| burst | CDRO-Fixed | 0.478 +- 0.105 | 0.849 +- 0.152 | 0.257 +- 0.069 |
| burst | CDRO-UG(sw0) | 0.455 +- 0.060 | 0.768 +- 0.141 | 0.236 +- 0.057 |
| mimic | Noisy-CE | 0.603 +- 0.194 | 1.000 +- 0.000 | 0.270 +- 0.080 |
| mimic | CDRO-Fixed | 0.629 +- 0.187 | 0.995 +- 0.009 | 0.237 +- 0.073 |
| mimic | CDRO-UG(sw0) | 0.642 +- 0.175 | 0.998 +- 0.005 | 0.226 +- 0.052 |

- External-J readout: CDRO-UG has the lowest pooled FPR for `slowburn` and `mimic`, while `burst` remains the hardest family across all methods.

Artifacts: `table19_attack_family_breakdown.csv`, `attack_family_summary.json`.