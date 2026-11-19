"""Run M0-M5 on dev and test, then build R1 from the dev results (PROTOCOL.md sections 2.1 and 6).

Each model runs in its own foreground command (its own Python process). Writes
evaluation/results/predictions_<id>.csv (id, split, predicted, ms) and its row of evaluation/results/models.csv.
Usage: python run_models.py --model M2   (one model: M0, M1, M2, M3, M4 or M5)
       python run_models.py --r1         (after all six: choose R1's arms on dev and write its predictions)
"""

import sys
import time

import pandas as pd

from common import DATA, MODELS, RESULTS, routes_to_arabic
from metrics import macro_f1

CANDIDATES = {
    # id: (folder, languages, card preprocessing)
    "M0": ("m0", {"en"}, True),
    "M1": ("m1", {"ar", "en"}, True),
    "M2": ("m2", {"ar", "en"}, False),
    "M3": ("m3", {"ar", "en"}, False),
    "M4": ("m4", {"ar", "en"}, False),
    "M5": ("m5", {"ar"}, False),
}
LABEL_MAP = {
    "negative": "negative", "neutral": "neutral", "positive": "positive",
    "very negative": "negative", "very positive": "positive",  # M3's five labels
}
WEIGHT_FILES = ("pytorch_model.bin", "model.safetensors")
R1_ARABIC_POOL = ["M1", "M2", "M4", "M5"]
R1_ENGLISH_POOL = ["M0", "M1", "M2", "M4"]
MODELS_CSV = RESULTS / "models.csv"


def items():
    dev = pd.read_csv(DATA / "dev_v1.csv", encoding="utf-8").assign(split="dev")
    test = pd.read_csv(DATA / "gold_v1.csv", encoding="utf-8").assign(split="test")
    return pd.concat([dev, test], ignore_index=True)


def card_preprocess(text):
    """The M0/M1 model cards' preprocessing."""
    words = []
    for word in text.split(" "):
        word = "@user" if word.startswith("@") and len(word) > 1 else word
        word = "http" if word.startswith("http") else word
        words.append(word)
    return " ".join(words)


def peak_mb(process):
    info = process.memory_info()
    return getattr(info, "peak_wset", info.rss) / 2**20


def run_one(model_id):
    import psutil
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    folder, languages, preprocess = CANDIDATES[model_id]
    path = MODELS / folder
    process = psutil.Process()

    start = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(path)
    model = AutoModelForSequenceClassification.from_pretrained(path).eval()
    load_s = time.perf_counter() - start

    id2label = {int(k): v.lower() for k, v in model.config.id2label.items()}
    unknown = [v for v in id2label.values() if v not in LABEL_MAP]
    if unknown:
        raise SystemExit(f"{model_id}: unknown labels {unknown}; run stopped.")

    rows = []
    peak = peak_mb(process)
    selected = items()
    selected = selected[selected["language"].isin(languages)]
    with torch.no_grad():
        for item in selected.itertuples():
            text = card_preprocess(item.text) if preprocess else item.text
            t0 = time.perf_counter()
            encoded = tokenizer(text, truncation=True, max_length=512, return_tensors="pt")
            logits = model(**encoded).logits
            ms = (time.perf_counter() - t0) * 1000
            rows.append({"id": item.id, "split": item.split,
                         "predicted": LABEL_MAP[id2label[int(logits.argmax(-1).item())]], "ms": round(ms, 3)})
            peak = max(peak, peak_mb(process))

    pd.DataFrame(rows).to_csv(RESULTS / f"predictions_{model_id}.csv", index=False, lineterminator="\n")
    return {"id": model_id, "load_s": round(load_s, 2), "peak_mb": round(peak, 1),
            "weights_mb": round(weights_file(model_id).stat().st_size / 2**20, 1),
            "torch_threads": torch.get_num_threads()}


def weights_file(model_id):
    path = MODELS / CANDIDATES[model_id][0]
    return next(path / name for name in WEIGHT_FILES if (path / name).exists())


def upsert_model(row):
    """Insert or update one model's row in results/models.csv, keeping other columns (e.g. weights_sha256)."""
    frame = pd.read_csv(MODELS_CSV, dtype={"arms": str}) if MODELS_CSV.exists() else pd.DataFrame({"id": []})
    frame = frame.set_index("id")
    for key, value in row.items():
        if key != "id":
            if key not in frame.columns:
                frame[key] = pd.Series(dtype=object)
            frame.loc[row["id"], key] = value
    order = [m for m in [*CANDIDATES, "R1"] if m in frame.index]
    frame.loc[order].reset_index().to_csv(MODELS_CSV, index=False, lineterminator="\n")


def dev_scores(model_id, language, gold):
    preds = pd.read_csv(RESULTS / f"predictions_{model_id}.csv")
    dev = preds[preds["split"] == "dev"].merge(gold[gold["language"] == language], on="id")
    return macro_f1(dev["label"], dev["predicted"]), dev["ms"].quantile(0.95)


def choose_arm(pool, language, gold):
    scored = [(*dev_scores(m, language, gold), m) for m in pool]
    # highest dev macro-F1, then lower dev p95, then lower candidate id
    best = sorted(scored, key=lambda s: (-s[0], s[1], s[2]))[0]
    return best[2], scored


def build_r1(models):
    data = items()
    gold = data[["id", "language", "label"]]
    arabic, arabic_scores = choose_arm(R1_ARABIC_POOL, "ar", gold)
    english, english_scores = choose_arm(R1_ENGLISH_POOL, "en", gold)
    arms = {m: pd.read_csv(RESULTS / f"predictions_{m}.csv").set_index(["id", "split"]) for m in {arabic, english}}
    rows = []
    for item in data.itertuples():
        arm = arabic if routes_to_arabic(item.text) else english
        key = (item.id, item.split)
        if key not in arms[arm].index:
            raise SystemExit(f"R1: {arm} has no prediction for {key}; run stopped.")
        row = arms[arm].loc[key]
        rows.append({"id": item.id, "split": item.split, "predicted": row["predicted"], "ms": row["ms"]})
    pd.DataFrame(rows).to_csv(RESULTS / "predictions_R1.csv", index=False, lineterminator="\n")
    a, e = models[arabic], models[english]
    same = arabic == english
    models["R1"] = {"id": "R1", "load_s": a["load_s"] if same else round(a["load_s"] + e["load_s"], 2),
                    "peak_mb": a["peak_mb"] if same else round(a["peak_mb"] + e["peak_mb"], 1),
                    "weights_mb": a["weights_mb"] if same else round(a["weights_mb"] + e["weights_mb"], 1),
                    "torch_threads": a["torch_threads"], "arms": f"ar={arabic};en={english}"}
    print("R1 Arabic arm (dev macro-F1, dev p95 ms):", {m: (round(f, 4), round(p, 1)) for f, p, m in arabic_scores},
          "->", arabic)
    print("R1 English arm (dev macro-F1, dev p95 ms):", {m: (round(f, 4), round(p, 1)) for f, p, m in english_scores},
          "->", english)


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    if len(sys.argv) == 3 and sys.argv[1] == "--model":
        row = run_one(sys.argv[2])
        upsert_model(row)
        print(row)
    elif sys.argv[1:] == ["--r1"]:
        models = pd.read_csv(MODELS_CSV).set_index("id").to_dict("index")
        missing = [m for m in CANDIDATES if m not in models]
        if missing:
            raise SystemExit(f"Run these models first: {missing}")
        for m in models:
            models[m]["id"] = m
        build_r1(models)
        upsert_model(models["R1"])
        print(pd.read_csv(MODELS_CSV).to_string(index=False))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
