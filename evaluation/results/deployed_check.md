# FR-05 deployment check: the worker's adapter against T-2 (M4)

A deployment check (D-178 (3)), not a new evaluation: the T-2 result in `results.md` is unchanged. The 300 gold_v1 test items (150 Arabic, 150 English) ran one at a time through `backend/infrastructure/local_analyzer.py`, the adapter the analysis worker uses. No dataset text is in this file.

## Run

| Item | Value |
|---|---|
| Model | clapAI/roberta-base-multilingual-sentiment |
| torch | 2.15.0+cpu |
| transformers | 5.23.0 |
| dtype | float32 (T-2 ran the stored float16) |
| torch threads | 10 |
| Load s (SHA-256 check and load) | 7.78 |
| Weights | weights SHA-256 verified (`model.safetensors` `01234f0e63a987c7bd768b5eb4a047343844de0414b14fa4f6625f88698c7771`) |
| Item text SHA-256 = gold_v1_ids.csv | 300 of 300 |
| Peak memory MB | 1783 |

## Labels against predictions_M4.csv

Differing labels: **0** of 300 (stop rule: more than 3).

## Macro-F1 (test)

| | Deployed (float32) | T-2 |
|---|---|---|
| Arabic | 0.703 | 0.703 |
| English | 0.764 | 0.764 |
| Headline (mean) | 0.733 | 0.733 |

## Latency per item (ms, warm, one at a time, CPU)

| | Deployed (float32) | T-2 |
|---|---|---|
| p50 | 52 | 263 |
| p95 | 89 | 611 |

Command: `.venv\Scripts\python.exe evaluation\check_deployed.py` from the repository root.
