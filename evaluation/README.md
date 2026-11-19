# T-2 — Sentiment model evaluation (NFR-07)

Evaluation only: published models are used as they are, nothing is trained (D-004). The protocol, including the
decision rule, is `PROTOCOL.md`; it was committed before the test set was built and before any model ran.
Fine-tuning data per candidate and the overlap counts are in `LEAKAGE.md`; the results are in `results/results.md`.

Dataset texts are not in the repository. It holds the scripts, the item ids with SHA-256 hashes of their texts
(`gold_v1_ids.csv`, `dev_v1_ids.csv`, `audit_ids.csv`), predictions (labels and timings) and results. Data, models
and audit files live in `C:\t2\` and are never added to git.

## Reproduce

Run from the repository root (Windows), with the evaluation environment, never the backend's `.venv`:

1. Environment: `C:\t2\.venv` (Python 3.11) with the pinned versions:
   `C:\t2\.venv\Scripts\python.exe -m pip install --timeout 120 --retries 10 -r evaluation\requirements.txt`
2. Models: the six folders `C:\t2\models\m0` … `m5` (`hf download <hub id> --local-dir C:\t2\models\mN`; the hub ids
   are in `PROTOCOL.md` section 2). clapAI/MultiLingualSentiment (main revision, five parquet files) goes in
   `C:\t2\data\raw\clapAI__MultiLingualSentiment\data\`.
3. `C:\t2\.venv\Scripts\python.exe evaluation\fetch_data.py` — the other datasets, parquet export.
4. `C:\t2\.venv\Scripts\python.exe evaluation\build_pools.py` — sources, label maps, filters
   (`C:\t2\data\pools.parquet`).
5. `C:\t2\.venv\Scripts\python.exe evaluation\overlap_filter.py` — drops items found in any fine-tuning corpus
   (`C:\t2\data\pools_clean.parquet`, `results\overlap.csv`). The clapAI hashing takes a while (more than 10 minutes).
6. `C:\t2\.venv\Scripts\python.exe evaluation\sample.py` — `C:\t2\data\gold_v1.csv` and `dev_v1.csv` (with text),
   `gold_v1_ids.csv`, `dev_v1_ids.csv`, `audit_ids.csv`, and the blank audit files in `C:\t2\audit\`.
   Check: `certutil -hashfile evaluation\gold_v1_ids.csv SHA256` must equal the hash in the commit that froze gold_v1;
   every `text_sha256` must equal the SHA-256 of the UTF-8 text of the rebuilt item.
7. One foreground command per model, each well under 10 minutes on the laptop:
   `C:\t2\.venv\Scripts\python.exe evaluation\run_models.py --model M0` (then M1 … M5), then
   `C:\t2\.venv\Scripts\python.exe evaluation\run_models.py --r1` (R1's arms chosen on dev) —
   `results\predictions_<id>.csv` and `results\models.csv`. Timings depend on the machine.
   `C:\t2\.venv\Scripts\python.exe evaluation\hash_weights.py M0` (one command per model) records each weights
   file's SHA-256 and its Hub etag in `results\models.csv`.
8. `C:\t2\.venv\Scripts\python.exe evaluation\metrics.py` — `results\results.csv`, `results\results.md`, winner.
9. After the three members have filled `C:\t2\audit\audit_<name>.csv` alone (label column: negative, neutral or
   positive): `C:\t2\.venv\Scripts\python.exe evaluation\audit_agreement.py` — `results\audit.md` (Fleiss' kappa and
   each member's agreement with the source labels). While the files are blank it says so and exits.

`.gitattributes` keeps the CSV files byte-identical on every checkout so that their hashes stay checkable.
