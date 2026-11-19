# T-2 results — sentiment model evaluation (NFR-07)

Protocol: `evaluation/PROTOCOL.md` v1.1 (v1 frozen before the test set was built, v1.1 before any model run). Test set gold_v1: 150 Arabic and 150 English items. Intervals: 95% percentile bootstrap, 2,000 resamples, seed 20261118.

## Winner

**M4** (clapAI/roberta-base-multilingual-sentiment) — decided by rule step **4b higher mean neutral recall**. Leader by headline: M4; tied with the leader: R1.

Step 6 (deployment, FR-05): M4 declares a licence with no non-commercial clause; FR-05 ships it.

## Headline (mean of Arabic and English macro-F1)

| Model | Status | Headline [95% CI] | Arabic macro-F1 [95% CI] | English macro-F1 [95% CI] | Mean neutral recall | p50 ms | p95 ms | Peak MB | Weights MB | Licence |
|---|---|---|---|---|---|---|---|---|---|---|
| M0 | baseline, English only; cannot win | — | — | 0.718 [0.643, 0.789] | 0.500 | 44.1 | 62.1 | 718 | 478 | cc-by-4.0 |
| M1 | eligible | 0.620 [0.564, 0.674] | 0.571 [0.489, 0.649] | 0.669 [0.594, 0.742] | 0.430 | 50.0 | 87.5 | 1032 | 1061 | none declared |
| M2 | eligible | 0.387 [0.347, 0.429] | 0.330 [0.272, 0.384] | 0.445 [0.380, 0.510] | 0.030 | 26.0 | 46.7 | 1096 | 516 | apache-2.0 |
| M3 | reference (training data not public); cannot win | 0.601 [0.544, 0.653] | 0.558 [0.474, 0.637] | 0.645 [0.571, 0.714] | 0.530 | 26.2 | 47.4 | 1101 | 516 | cc-by-nc-4.0 |
| M4 | eligible | 0.733 [0.681, 0.781] | 0.703 [0.622, 0.773] | 0.764 [0.692, 0.830] | 0.750 | 263.4 | 611.1 | 1402 | 530 | apache-2.0 |
| M5 | Arabic only; cannot win | — | 0.647 [0.567, 0.719] | — | 0.440 | 46.4 | 79.1 | 799 | 416 | apache-2.0 |
| R1 | eligible | 0.705 [0.649, 0.755] | 0.647 [0.567, 0.719] | 0.764 [0.692, 0.830] | 0.540 | 87.8 | 409.1 | 2201 | 947 | apache-2.0 + apache-2.0 |

R1 arms (chosen on the dev set only): Arabic M5, English M4. R1 peak memory and weights are the sums of its two arms.
Missing test predictions: M0 0, M1 0, M2 0, M3 0, M4 0, M5 0, R1 0.

## Decision rule

1. Eligible (all test items predicted): M1, M2, M4, R1. M0, M3, M5 cannot win.
2. Leader by headline: **M4** (0.733).
3. Paired bootstrap of headline(rival) − headline(leader):

| Rival | Difference | 95% CI | Tied |
|---|---|---|---|
| M1 | -0.113 | [-0.175, -0.050] | no |
| M2 | -0.346 | [-0.408, -0.282] | no |
| R1 | -0.028 | [-0.073, +0.017] | yes |

4. Tie-breaks among M4, R1:

   - 4a licence without a non-commercial clause — M4: pass, R1: pass → remaining M4, R1
   - 4b higher mean neutral recall — M4: 0.750, R1: 0.540 → remaining M4

Decided by: **4b higher mean neutral recall**. Mean neutral recall: M1 0.430, M2 0.030, M4 0.750, R1 0.540.

## Per language (test)

### Arabic (MSA)

| Model | n | Macro-F1 [95% CI] | Accuracy | Neg P / R / F1 | Neu P / R / F1 | Pos P / R / F1 |
|---|---|---|---|---|---|---|
| M1 | 150 | 0.571 [0.489, 0.649] | 0.587 | 0.58 / 0.58 / 0.58 | 0.64 / 0.36 / 0.46 | 0.57 / 0.82 / 0.67 |
| M2 | 150 | 0.330 [0.272, 0.384] | 0.407 | 0.37 / 0.74 / 0.49 | 0.00 / 0.00 / 0.00 | 0.52 / 0.48 / 0.50 |
| M3 | 150 | 0.558 [0.474, 0.637] | 0.560 | 0.54 / 0.66 / 0.59 | 0.52 / 0.46 / 0.49 | 0.62 / 0.56 / 0.59 |
| M4 | 150 | 0.703 [0.622, 0.773] | 0.700 | 0.80 / 0.64 / 0.71 | 0.57 / 0.86 / 0.68 | 0.88 / 0.60 / 0.71 |
| M5 | 150 | 0.647 [0.567, 0.719] | 0.653 | 0.56 / 0.78 / 0.65 | 0.73 / 0.44 / 0.55 | 0.74 / 0.74 / 0.74 |
| R1 | 150 | 0.647 [0.567, 0.719] | 0.653 | 0.56 / 0.78 / 0.65 | 0.73 / 0.44 / 0.55 | 0.74 / 0.74 / 0.74 |

### English

| Model | n | Macro-F1 [95% CI] | Accuracy | Neg P / R / F1 | Neu P / R / F1 | Pos P / R / F1 |
|---|---|---|---|---|---|---|
| M0 | 150 | 0.718 [0.643, 0.789] | 0.727 | 0.68 / 0.86 / 0.76 | 0.71 / 0.50 / 0.59 | 0.79 / 0.82 / 0.80 |
| M1 | 150 | 0.669 [0.594, 0.742] | 0.673 | 0.64 / 0.74 / 0.69 | 0.61 / 0.50 / 0.55 | 0.76 / 0.78 / 0.77 |
| M2 | 150 | 0.445 [0.380, 0.510] | 0.513 | 0.51 / 0.74 / 0.61 | 0.30 / 0.06 / 0.10 | 0.54 / 0.74 / 0.63 |
| M3 | 150 | 0.645 [0.571, 0.714] | 0.640 | 0.59 / 0.64 / 0.62 | 0.55 / 0.60 / 0.57 | 0.83 / 0.68 / 0.75 |
| M4 | 150 | 0.764 [0.692, 0.830] | 0.767 | 0.74 / 0.78 / 0.76 | 0.76 / 0.64 / 0.70 | 0.80 / 0.88 / 0.84 |
| R1 | 150 | 0.764 [0.692, 0.830] | 0.767 | 0.74 / 0.78 / 0.76 | 0.76 / 0.64 / 0.70 | 0.80 / 0.88 / 0.84 |

## Confusion matrices (test; rows gold, columns predicted: neg, neu, pos)

- M0 en: neg 43 6 1; neu 15 25 10; pos 5 4 41
- M1 ar: neg 29 5 16; neu 17 18 15; pos 4 5 41
- M1 en: neg 37 12 1; neu 14 25 11; pos 7 4 39
- M2 ar: neg 37 3 10; neu 38 0 12; pos 26 0 24
- M2 en: neg 37 5 8; neu 24 3 23; pos 11 2 37
- M3 ar: neg 33 10 7; neu 17 23 10; pos 11 11 28
- M3 en: neg 32 17 1; neu 14 30 6; pos 8 8 34
- M4 ar: neg 32 15 3; neu 6 43 1; pos 2 18 30
- M4 en: neg 39 8 3; neu 10 32 8; pos 4 2 44
- M5 ar: neg 39 5 6; neu 21 22 7; pos 10 3 37
- R1 ar: neg 39 5 6; neu 21 22 7; pos 10 3 37
- R1 en: neg 39 8 3; neu 10 32 8; pos 4 2 44

## Development set (macro-F1; used only to choose R1's arms)

| Model | Arabic | English |
|---|---|---|
| M0 | — | 0.634 |
| M1 | 0.602 | 0.566 |
| M2 | 0.321 | 0.400 |
| M3 | 0.397 | 0.600 |
| M4 | 0.526 | 0.692 |
| M5 | 0.622 | — |

## Runs

| Model | Load s | Peak MB | Weights MB | torch threads | Weights file SHA-256 | = Hub etag |
|---|---|---|---|---|---|---|
| M0 | 3.4 | 718 | 478 | 10 | `pytorch_model.bin` `4d24a3e32a88ed1c4e5b789fc6644e2e767500554e954b27dccf52a8e762cbae` | yes |
| M1 | 4.4 | 1032 | 1061 | 10 | `pytorch_model.bin` `93316a86051c359748c5d5453e7660c69a21a57cfb477892f95f539e3e171196` | yes |
| M2 | 4.0 | 1096 | 516 | 10 | `model.safetensors` `0ab095b69033944004bb7a6ffcbfc2d77a240dd0f71c27820aa73efa71f664fe` | yes |
| M3 | 3.8 | 1101 | 516 | 10 | `model.safetensors` `3ab3cecb8605da0a240e5b4e18d969704d44e27c6ea48533ef6693d31dbb926a` | yes |
| M4 | 6.0 | 1402 | 530 | 10 | `model.safetensors` `01234f0e63a987c7bd768b5eb4a047343844de0414b14fa4f6625f88698c7771` | yes |
| M5 | 6.0 | 799 | 416 | 10 | `pytorch_model.bin` `543da83a6ae351ad8088f1649ada775981cf83567d970a6b1b2f13b70e21d7d4` | yes |
| R1 | 12.0 | 2201 | 947 | 10 | arms M5 + M4 | — |

CPU only, one item at a time, `torch.no_grad()`, truncation at 512 tokens. Overlap counts: `results/overlap.csv` and `LEAKAGE.md`.
