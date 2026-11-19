"""Deployment check for FR-05 (TASK-39, D-178 (3)): does the worker's adapter give T-2's M4 labels?

Runs the 300 gold_v1 test items one at a time through backend/infrastructure/local_analyzer.py
(M4 in float32) and compares the labels with T-2's evaluation/results/predictions_M4.csv.
Writes evaluation/results/deployed_check.md with no dataset text. The T-2 result is not changed.
The model files are checked against the committed manifest in backend/infrastructure/model_manifests/.
Standard library plus the model runtime. From the repository root:
    .venv\\Scripts\\python.exe evaluation\\check_deployed.py [--model-path PATH]
Exit code 2 when more than MAX_DIFFERENT labels differ (the stop rule).
"""

import argparse
import csv
import hashlib
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from infrastructure.local_analyzer import (  # noqa: E402
    LocalTransformersAnalyzer,
    manifest_path,
    read_manifest,
)

# The same values as backend/.env.example.
DEFAULT_MODEL_PATH = r"C:\t2\models\m4"
MODEL_ID = "clapAI/roberta-base-multilingual-sentiment"
GOLD_TEXT = Path(r"C:\t2\data\gold_v1.csv")
GOLD_IDS = ROOT / "evaluation" / "gold_v1_ids.csv"
T2_PREDICTIONS = ROOT / "evaluation" / "results" / "predictions_M4.csv"
OUTPUT = ROOT / "evaluation" / "results" / "deployed_check.md"
LABELS = ("negative", "neutral", "positive")
T2 = {"ar": 0.703, "en": 0.764, "headline": 0.733, "p50": 263, "p95": 611}  # results/results.md, M4
MAX_DIFFERENT = 3


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def macro_f1(gold, predicted):
    """Mean per-class F1 over the three labels; a class with no support or prediction scores 0."""
    scores = []
    for label in LABELS:
        tp = sum(1 for g, p in zip(gold, predicted) if g == label and p == label)
        pred = sum(1 for p in predicted if p == label)
        true = sum(1 for g in gold if g == label)
        precision = tp / pred if pred else 0.0
        recall = tp / true if true else 0.0
        scores.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
    return sum(scores) / len(scores)


def peak_memory_mb():
    """Peak working set of this process (Windows), or peak RSS elsewhere; None when unknown."""
    try:
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes

            class Counters(ctypes.Structure):
                _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                            ("PeakPagefileUsage", ctypes.c_size_t)]

            counters = Counters()
            counters.cb = ctypes.sizeof(Counters)
            psapi = ctypes.WinDLL("psapi")
            kernel32 = ctypes.WinDLL("kernel32")
            kernel32.GetCurrentProcess.restype = wintypes.HANDLE
            psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
            if psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
                return counters.PeakWorkingSetSize / 2**20
            return None
        import resource

        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    except Exception:  # noqa: BLE001 - memory is reported only when it can be read
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model-path", default=DEFAULT_MODEL_PATH)
    args = parser.parse_args()

    texts = {row["id"]: row["text"] for row in read_csv(GOLD_TEXT)}
    gold = {row["id"]: row for row in read_csv(GOLD_IDS)}
    t2 = {row["id"]: row["predicted"] for row in read_csv(T2_PREDICTIONS) if row["split"] == "test"}
    ids = sorted(gold)
    missing = [i for i in ids if i not in texts or i not in t2]
    if missing:
        raise SystemExit(f"Items without text or T-2 prediction: {missing[:10]}; run stopped.")
    text_hash_matches = sum(
        1 for i in ids if hashlib.sha256(texts[i].encode("utf-8")).hexdigest() == gold[i]["text_sha256"]
    )

    import torch
    import transformers

    analyzer = LocalTransformersAnalyzer(args.model_path, MODEL_ID, read_manifest(MODEL_ID))
    start = time.perf_counter()
    analyzer._ensure_loaded()  # the adapter's own first-use step: manifest check, then load
    load_s = time.perf_counter() - start
    # The load raised unless every manifest file matched; the total counts every file in the folder.
    verified = len(analyzer.manifest)
    folder_files = sum(1 for path in Path(args.model_path).iterdir() if path.is_file())
    dtype = str(next(analyzer._model.parameters()).dtype).replace("torch.", "")

    analyzer.analyze_sentiment(texts[ids[0]])  # warm-up, not counted

    predicted, ms = {}, []
    for item_id in ids:
        t0 = time.perf_counter()
        result = analyzer.analyze_sentiment(texts[item_id])
        ms.append((time.perf_counter() - t0) * 1000)
        predicted[item_id] = result["label"].lower()
    peak = peak_memory_mb()

    different = [i for i in ids if predicted[i] != t2[i]]
    f1 = {}
    for language in ("ar", "en"):
        chosen = [i for i in ids if gold[i]["language"] == language]
        f1[language] = macro_f1([gold[i]["label"] for i in chosen], [predicted[i] for i in chosen])
    f1["headline"] = (f1["ar"] + f1["en"]) / 2
    p50 = statistics.median(ms)
    p95 = statistics.quantiles(ms, n=100, method="inclusive")[94]
    counts = {lang: sum(1 for i in ids if gold[i]["language"] == lang) for lang in ("ar", "en")}

    lines = [
        "# FR-05 deployment check: the worker's adapter against T-2 (M4)\n",
        "A deployment check (D-178 (3)), not a new evaluation: the T-2 result in `results.md` is unchanged. "
        f"The 300 gold_v1 test items ({counts['ar']} Arabic, {counts['en']} English) ran one at a time "
        "through `backend/infrastructure/local_analyzer.py`, the adapter the analysis worker uses. "
        "No dataset text is in this file.\n",
        "## Run\n",
        "| Item | Value |",
        "|---|---|",
        f"| Model | {MODEL_ID} |",
        f"| torch | {torch.__version__} |",
        f"| transformers | {transformers.__version__} |",
        f"| dtype | {dtype} (T-2 ran the stored float16) |",
        f"| torch threads | {torch.get_num_threads()} |",
        f"| Load s (manifest check and load) | {load_s:.2f} |",
        f"| Files verified against the manifest | {verified} of {folder_files} "
        f"(`backend/infrastructure/model_manifests/{manifest_path(MODEL_ID).name}`) |",
        f"| Item text SHA-256 = gold_v1_ids.csv | {text_hash_matches} of {len(ids)} |",
        f"| Peak memory MB | {f'{peak:.0f}' if peak is not None else 'not measured'} |",
        "",
        "## Labels against predictions_M4.csv\n",
        f"Differing labels: **{len(different)}** of {len(ids)} (stop rule: more than {MAX_DIFFERENT}).",
    ]
    if different:
        lines.append("\n| id | T-2 | deployed |\n|---|---|---|")
        lines += [f"| {i} | {t2[i]} | {predicted[i]} |" for i in different]
    lines += [
        "",
        "## Macro-F1 (test)\n",
        "| | Deployed (float32) | T-2 |",
        "|---|---|---|",
        f"| Arabic | {f1['ar']:.3f} | {T2['ar']:.3f} |",
        f"| English | {f1['en']:.3f} | {T2['en']:.3f} |",
        f"| Headline (mean) | {f1['headline']:.3f} | {T2['headline']:.3f} |",
        "",
        "## Latency per item (ms, warm, one at a time, CPU)\n",
        "| | Deployed (float32) | T-2 |",
        "|---|---|---|",
        f"| p50 | {p50:.0f} | {T2['p50']} |",
        f"| p95 | {p95:.0f} | {T2['p95']} |",
        "",
        "Command: `.venv\\Scripts\\python.exe evaluation\\check_deployed.py` from the repository root.\n",
    ]
    OUTPUT.write_text("\n".join(lines), encoding="utf-8", newline="\n")

    print(f"differing {len(different)}: {different}")
    print(f"macro-F1 ar {f1['ar']:.3f} en {f1['en']:.3f} headline {f1['headline']:.3f}")
    print(f"p50 {p50:.0f} ms p95 {p95:.0f} ms load {load_s:.2f} s peak {peak if peak is None else round(peak)} MB "
          f"dtype {dtype} threads {torch.get_num_threads()}")
    print(f"files verified against the manifest: {verified} of {folder_files}")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    if len(different) > MAX_DIFFERENT:
        print(f"STOP: more than {MAX_DIFFERENT} labels differ.")
        sys.exit(2)


if __name__ == "__main__":
    main()
