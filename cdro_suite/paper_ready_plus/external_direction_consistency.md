# External Scenario-Wise Direction Consistency

This appendix note isolates the cheapest useful external-validation strengthening path: a tuned-threshold, scenario-wise comparison of `CDRO-UG (sw0)` against `Noisy-CE` across external scenarios `I/J/K/L`.

## What the table shows

- `table20_external_direction_consistency.csv` records the paired pooled `F1` and `FPR` comparisons for each external scenario plus the pooled external row.
- This is a tuned-threshold reading. It should not be conflated with the frozen-threshold deployment transfer table, which is kept separate because it answers a different systems question.

## Safe reading

- `CDRO-UG (sw0)` lowers tuned-threshold `FPR` in `3/4` external scenarios: `External-J`, `External-K`, and `External-L`.
- The strongest supported case is still `External-J`, where `FPR` drops from `0.2695` to `0.2259` with `delta = -0.043630` and `p = 0.00513`.
- `External-K` also lowers `FPR` from `0.1745` to `0.1503` with `delta = -0.024203` and `p = 0.04467`, but the `F1` change is slightly negative and non-significant.
- `External-L` is only directional: `FPR` falls from `0.2893` to `0.2839`, but the paired support is weak (`p = 0.83061`).
- `External-I` reverses the pattern: `FPR` rises from `0.0749` to `0.0924`, even though `F1` is slightly higher.
- The pooled external row therefore remains the governing summary for broad generalization: `delta_F1 = +0.000353` (`p = 0.94150`) and `delta_FPR = -0.013916` (`p = 0.20834`).

## Why this belongs in the appendix

- The table strengthens the paper honestly by showing partial scenario-wise external consistency, not universal transfer.
- It supports a restrained sentence such as: "Under tuned thresholds, the external-J false-positive reduction is not isolated; FPR direction aligns in three of four external scenarios, although pooled external remains non-significant and one scenario reverses."
- This is the lowest-cost external strengthening already supported by existing artifacts. It improves reviewer confidence without changing the main headline hierarchy.
