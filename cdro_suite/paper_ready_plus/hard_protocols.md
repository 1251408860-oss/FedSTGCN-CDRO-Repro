# Hard / Camouflaged Protocol Suite

## Main
### Hard temporal OOD
- Noisy-CE: F1=0.0214, FPR=0.0880, ECE=0.4293
- CDRO-Fixed: F1=0.0272, FPR=0.1179, ECE=0.4757
- CDRO-UG (sw0): F1=0.0166, FPR=0.0829, ECE=0.4221

### Hard topology OOD
- Noisy-CE: F1=0.0183, FPR=0.1371, ECE=0.4398
- CDRO-Fixed: F1=0.0159, FPR=0.1695, ECE=0.4732
- CDRO-UG (sw0): F1=0.0173, FPR=0.1290, ECE=0.4256

### Hard attack-strategy OOD
- Noisy-CE: F1=0.0148, FPR=0.1509, ECE=0.4220
- CDRO-Fixed: F1=0.0146, FPR=0.1711, ECE=0.4070
- CDRO-UG (sw0): F1=0.0148, FPR=0.1557, ECE=0.4137

### Hard congestion OOD
- Noisy-CE: F1=0.1328, FPR=0.2389, ECE=0.4708
- CDRO-Fixed: F1=0.1400, FPR=0.2770, ECE=0.4726
- CDRO-UG (sw0): F1=0.1466, FPR=0.2748, ECE=0.4863

### Pooled hard suite
- Noisy-CE: F1=0.0468, FPR=0.1537, ECE=0.4405
- CDRO-Fixed: F1=0.0494, FPR=0.1839, ECE=0.4571
- CDRO-UG (sw0): F1=0.0488, FPR=0.1606, ECE=0.4369

## Batch2
### Hard temporal OOD
- Noisy-CE: F1=0.0277, FPR=0.2505, ECE=0.5265
- CDRO-Fixed: F1=0.0266, FPR=0.3283, ECE=0.5534
- CDRO-UG (sw0): F1=0.0267, FPR=0.2495, ECE=0.5278

### Hard topology OOD
- Noisy-CE: F1=0.0064, FPR=0.1535, ECE=0.5269
- CDRO-Fixed: F1=0.0065, FPR=0.1253, ECE=0.4619
- CDRO-UG (sw0): F1=0.0063, FPR=0.1798, ECE=0.5191

### Hard attack-strategy OOD
- Noisy-CE: F1=0.0293, FPR=0.1737, ECE=0.4134
- CDRO-Fixed: F1=0.0277, FPR=0.1697, ECE=0.3323
- CDRO-UG (sw0): F1=0.0295, FPR=0.1646, ECE=0.3810

### Hard congestion OOD
- Noisy-CE: F1=0.0678, FPR=0.3277, ECE=0.5049
- CDRO-Fixed: F1=0.0699, FPR=0.2900, ECE=0.4791
- CDRO-UG (sw0): F1=0.0646, FPR=0.2778, ECE=0.4968

### Pooled hard suite
- Noisy-CE: F1=0.0328, FPR=0.2264, ECE=0.4929
- CDRO-Fixed: F1=0.0327, FPR=0.2283, ECE=0.4567
- CDRO-UG (sw0): F1=0.0318, FPR=0.2179, ECE=0.4812

## Reading
- Combined hard-suite pooled comparison against Noisy-CE: delta_F1=+0.000490, p=0.860107; delta_FPR=-0.000772, p=0.936603.
- This suite should be read as a stress-test supplement: after correcting merged pairing, the combined hard-suite pooled delta is near zero, so the safe takeaway is no catastrophic collapse rather than a new advantage claim.
