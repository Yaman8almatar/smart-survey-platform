"""Metrics, intervals and the NFR-07 decision rule (PROTOCOL.md sections 7 and 8).

Reads evaluation/gold_v1_ids.csv, evaluation/dev_v1_ids.csv and evaluation/results/{predictions_*,models,overlap}.csv;
writes evaluation/results/results.csv and evaluation/results/results.md. Needs no dataset text.
"""

import numpy as np
import pandas as pd

from common import EVAL, LABELS, RESULTS, SEED

ROUNDS = 2000
ORDER = ["M0", "M1", "M2", "M3", "M4", "M5", "R1"]
ELIGIBLE = ["M1", "M2", "M4", "R1"]
BOTH = ["M1", "M2", "M3", "M4", "R1"]
COVERS = {"M0": ["en"], "M5": ["ar"]}
STATUS = {"M0": "baseline, English only; cannot win", "M1": "eligible", "M2": "eligible",
          "M3": "reference (training data not public); cannot win", "M4": "eligible",
          "M5": "Arabic only; cannot win", "R1": "eligible"}
HUB = {"M0": "cardiffnlp/twitter-roberta-base-sentiment-latest", "M1": "cardiffnlp/twitter-xlm-roberta-base-sentiment",
       "M2": "lxyuan/distilbert-base-multilingual-cased-sentiments-student",
       "M3": "tabularisai/multilingual-sentiment-analysis", "M4": "clapAI/roberta-base-multilingual-sentiment",
       "M5": "CAMeL-Lab/bert-base-arabic-camelbert-msa-sentiment", "R1": "router"}
# Licence declared on the model card (LEAKAGE.md); None = no licence declared.
LICENCE = {"M0": "cc-by-4.0", "M1": None, "M2": "apache-2.0", "M3": "cc-by-nc-4.0", "M4": "apache-2.0",
           "M5": "apache-2.0"}
CODE = {label: i for i, label in enumerate(LABELS)}


def encode(values):
    return np.array([CODE[v] for v in values])


def f1_parts(y, p):
    """Per-class precision, recall, F1 along the last axis (y, p: int arrays, same shape)."""
    out = []
    for c in range(3):
        tp = ((y == c) & (p == c)).sum(-1)
        pred = (p == c).sum(-1)
        true = (y == c).sum(-1)
        precision = np.divide(tp, pred, out=np.zeros(tp.shape), where=pred > 0)
        recall = np.divide(tp, true, out=np.zeros(tp.shape), where=true > 0)
        f1 = np.divide(2 * precision * recall, precision + recall, out=np.zeros(tp.shape),
                       where=(precision + recall) > 0)
        out.append((precision, recall, f1))
    return out


def macro_f1(gold, predicted):
    y, p = encode(gold), encode(predicted)
    return float(np.mean([f1 for _, _, f1 in f1_parts(y, p)]))


def boot_macro(y, p, idx):
    return np.mean([f1 for _, _, f1 in f1_parts(y[idx], p[idx])], axis=0)


def interval(values):
    return float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))


def licence_ok(model_id, arms):
    if model_id == "R1":
        return all(licence_ok(m, arms) for m in set(arms.values()))
    licence = LICENCE[model_id]
    return licence is not None and "nc" not in licence.split("-")


def load():
    gold = pd.read_csv(EVAL / "gold_v1_ids.csv")
    dev = pd.read_csv(EVAL / "dev_v1_ids.csv")
    preds = {m: pd.read_csv(RESULTS / f"predictions_{m}.csv") for m in ORDER}
    models = pd.read_csv(RESULTS / "models.csv").set_index("id")
    return gold, dev, preds, models


def aligned(gold, pred, split, language):
    g = gold[gold["language"] == language].sort_values("id")
    p = pred[pred["split"] == split].set_index("id")
    missing = [i for i in g["id"] if i not in p.index]
    p = p.reindex(g["id"])
    return g, p, missing


def main():
    gold, dev, preds, models = load()
    arms = dict(part.split("=") for part in str(models.at["R1", "arms"]).split(";"))
    rng = np.random.default_rng(SEED)
    n = {lang: int((gold["language"] == lang).sum()) for lang in ("ar", "en")}
    idx = {lang: rng.integers(0, n[lang], size=(ROUNDS, n[lang])) for lang in ("ar", "en")}

    rows, boots, missing_by_model, confusion, latency = [], {}, {}, {}, {}
    for m in ORDER:
        langs = COVERS.get(m, ["ar", "en"])
        missing_by_model[m] = 0
        ms = []
        for lang in langs:
            g, p, missing = aligned(gold, preds[m], "test", lang)
            missing_by_model[m] += len(missing)
            if missing:
                continue
            y, q = encode(g["label"]), encode(p["predicted"])
            parts = f1_parts(y, q)
            boots[(m, lang)] = boot_macro(y, q, idx[lang])
            lo, hi = interval(boots[(m, lang)])
            row = {"model": m, "language": lang, "n": len(y),
                   "macro_f1": float(np.mean([f for _, _, f in parts])), "ci_low": lo, "ci_high": hi,
                   "accuracy": float((y == q).mean()), "neutral_recall": float(parts[1][1])}
            for label, (pr, rc, f1) in zip(LABELS, parts):
                row |= {f"{label}_precision": float(pr), f"{label}_recall": float(rc), f"{label}_f1": float(f1)}
            rows.append(row)
            matrix = np.zeros((3, 3), dtype=int)
            np.add.at(matrix, (y, q), 1)
            confusion[(m, lang)] = matrix
            ms += list(p["ms"])
        latency[m] = (float(np.percentile(ms, 50)), float(np.percentile(ms, 95))) if ms else (np.nan, np.nan)
    table = pd.DataFrame(rows)
    table.to_csv(RESULTS / "results.csv", index=False, lineterminator="\n", float_format="%.4f")

    def score(m, lang, col="macro_f1"):
        hit = table[(table["model"] == m) & (table["language"] == lang)]
        return float(hit[col].iloc[0]) if len(hit) else np.nan

    headline = {}
    for m in BOTH:
        if (m, "ar") in boots and (m, "en") in boots:
            point = (score(m, "ar") + score(m, "en")) / 2
            headline[m] = (point, *interval((boots[(m, "ar")] + boots[(m, "en")]) / 2))

    # Decision rule
    eligible = [m for m in ELIGIBLE if missing_by_model[m] == 0 and m in headline]
    leader = max(eligible, key=lambda m: headline[m][0])
    lead_boot = (boots[(leader, "ar")] + boots[(leader, "en")]) / 2
    paired = {}
    for m in eligible:
        if m == leader:
            continue
        diff = (boots[(m, "ar")] + boots[(m, "en")]) / 2 - lead_boot
        lo, hi = interval(diff)
        paired[m] = (headline[m][0] - headline[leader][0], lo, hi, lo <= 0 <= hi)
    tied = [leader] + [m for m, v in paired.items() if v[3]]
    neutral = {m: (score(m, "ar", "neutral_recall") + score(m, "en", "neutral_recall")) / 2 for m in eligible}
    criteria = [
        ("4a licence without a non-commercial clause", lambda m: 0 if licence_ok(m, arms) else 1),
        ("4b higher mean neutral recall", lambda m: -neutral[m]),
        ("4c lower p95 latency", lambda m: latency[m][1]),
        ("4d smaller weights", lambda m: float(models.at[m, "weights_mb"])),
    ]
    remaining, log = list(tied), []
    decided_by = "2 highest headline (no rival tied)" if len(tied) == 1 else None
    for name, key in criteria:
        if len(remaining) == 1:
            break
        values = {m: key(m) for m in remaining}
        best = min(values.values())
        remaining = [m for m in remaining if values[m] == best]
        log.append((name, {m: values[m] for m in values}, list(remaining)))
        if len(remaining) == 1:
            decided_by = name
    winner = remaining[0] if len(remaining) == 1 else None

    # Step 6 (protocol v1.1): deployment licence rule; it does not change the winner.
    licensed = [m for m in sorted(eligible, key=lambda m: -headline[m][0]) if licence_ok(m, arms)]
    deploy = winner if winner and licence_ok(winner, arms) else (licensed[0] if licensed else None)

    write_md(table, headline, latency, models, confusion, paired, leader, tied, log, winner, decided_by,
             neutral, arms, gold, dev, preds, missing_by_model, deploy)
    print(f"leader {leader}; tied {tied}; winner {winner}; decided by {decided_by}; FR-05 ships {deploy}")


def fmt(x, d=3):
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{d}f}"


def write_md(table, headline, latency, models, confusion, paired, leader, tied, log, winner, decided_by,
             neutral, arms, gold, dev, preds, missing_by_model, deploy):
    L = []
    L.append("# T-2 results — sentiment model evaluation (NFR-07)\n")
    L.append("Protocol: `evaluation/PROTOCOL.md` v1.1 (v1 frozen before the test set was built, v1.1 before any "
             "model run). Test set gold_v1: "
             f"{(gold['language'] == 'ar').sum()} Arabic and {(gold['language'] == 'en').sum()} English items. "
             "Intervals: 95% percentile bootstrap, 2,000 resamples, seed 20261118.\n")

    L.append("## Winner\n")
    if winner:
        L.append(f"**{winner}** ({HUB[winner]}{', arms ' + arms['ar'] + ' (Arabic) and ' + arms['en'] + ' (English)' if winner == 'R1' else ''}) "
                 f"— decided by rule step **{decided_by}**. Leader by headline: {leader}; tied with the leader: "
                 f"{', '.join(t for t in tied if t != leader) or 'none'}.\n")
    else:
        L.append(f"No single winner after every tie-break; remaining: {tied}. Leader by headline: {leader}.\n")
    if winner and deploy == winner:
        L.append(f"Step 6 (deployment, FR-05): {winner} declares a licence with no non-commercial clause; "
                 "FR-05 ships it.\n")
    else:
        L.append(f"Step 6 (deployment, FR-05): the winner does not declare a licence without a non-commercial "
                 f"clause. The eligible candidate with the highest headline that does is **{deploy or 'none'}**; "
                 "FR-05 ships it unless the winner's authors grant permission. This does not change the winner.\n")

    L.append("## Headline (mean of Arabic and English macro-F1)\n")
    L.append("| Model | Status | Headline [95% CI] | Arabic macro-F1 [95% CI] | English macro-F1 [95% CI] | "
             "Mean neutral recall | p50 ms | p95 ms | Peak MB | Weights MB | Licence |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for m in ORDER:
        def lang_cell(lang):
            hit = table[(table["model"] == m) & (table["language"] == lang)]
            if not len(hit):
                return "—"
            r = hit.iloc[0]
            return f"{r.macro_f1:.3f} [{r.ci_low:.3f}, {r.ci_high:.3f}]"
        h = headline.get(m)
        nr = [table[(table["model"] == m) & (table["language"] == lang)]["neutral_recall"] for lang in ("ar", "en")]
        nr = [float(x.iloc[0]) for x in nr if len(x)]
        licence = (f"{LICENCE.get(arms['ar'])} + {LICENCE.get(arms['en'])}" if m == "R1"
                   else (LICENCE[m] or "none declared"))
        L.append(f"| {m} | {STATUS[m]} | {f'{h[0]:.3f} [{h[1]:.3f}, {h[2]:.3f}]' if h else '—'} | "
                 f"{lang_cell('ar')} | {lang_cell('en')} | {fmt(float(np.mean(nr)) if nr else None)} | "
                 f"{fmt(latency[m][0], 1)} | {fmt(latency[m][1], 1)} | {models.at[m, 'peak_mb']:.0f} | "
                 f"{models.at[m, 'weights_mb']:.0f} | {licence} |")
    L.append(f"\nR1 arms (chosen on the dev set only): Arabic {arms['ar']}, English {arms['en']}. "
             "R1 peak memory and weights are the sums of its two arms.")
    L.append(f"Missing test predictions: {', '.join(f'{m} {v}' for m, v in missing_by_model.items())}.\n")

    L.append("## Decision rule\n")
    L.append(f"1. Eligible (all test items predicted): "
             f"{', '.join(m for m in ELIGIBLE if missing_by_model[m] == 0)}. M0, M3, M5 cannot win.")
    L.append(f"2. Leader by headline: **{leader}** ({headline[leader][0]:.3f}).")
    L.append("3. Paired bootstrap of headline(rival) − headline(leader):\n")
    L.append("| Rival | Difference | 95% CI | Tied |")
    L.append("|---|---|---|---|")
    for m, (d, lo, hi, t) in paired.items():
        L.append(f"| {m} | {d:+.3f} | [{lo:+.3f}, {hi:+.3f}] | {'yes' if t else 'no'} |")
    L.append("")
    if log:
        L.append("4. Tie-breaks among " + ", ".join(tied) + ":\n")
        for name, values, left in log:
            sign = -1 if name.startswith("4b") else 1  # 4b is ranked on the negated recall
            shown = ", ".join(f"{m}: {sign * v:.3f}" if isinstance(v, float)
                              else f"{m}: {'pass' if v == 0 else 'fail'}" for m, v in values.items())
            L.append(f"   - {name} — {shown} → remaining {', '.join(left)}")
    else:
        L.append("4. No tie-break needed.")
    L.append(f"\nDecided by: **{decided_by}**. Mean neutral recall: "
             + ", ".join(f"{m} {v:.3f}" for m, v in neutral.items()) + ".\n")

    L.append("## Per language (test)\n")
    for lang, name in (("ar", "Arabic (MSA)"), ("en", "English")):
        L.append(f"### {name}\n")
        L.append("| Model | n | Macro-F1 [95% CI] | Accuracy | Neg P / R / F1 | Neu P / R / F1 | Pos P / R / F1 |")
        L.append("|---|---|---|---|---|---|---|")
        for r in table[table["language"] == lang].itertuples():
            cells = [" / ".join(f"{getattr(r, f'{c}_{k}'):.2f}" for k in ("precision", "recall", "f1"))
                     for c in LABELS]
            L.append(f"| {r.model} | {r.n} | {r.macro_f1:.3f} [{r.ci_low:.3f}, {r.ci_high:.3f}] | "
                     f"{r.accuracy:.3f} | {' | '.join(cells)} |")
        L.append("")

    L.append("## Confusion matrices (test; rows gold, columns predicted: neg, neu, pos)\n")
    for (m, lang), cm in confusion.items():
        cells = "; ".join(f"{g[:3]} " + " ".join(str(int(v)) for v in cm[i]) for i, g in enumerate(LABELS))
        L.append(f"- {m} {lang}: {cells}")
    L.append("")

    L.append("## Development set (macro-F1; used only to choose R1's arms)\n")
    L.append("| Model | Arabic | English |")
    L.append("|---|---|---|")
    for m in ORDER:
        if m == "R1":
            continue
        vals = []
        for lang in ("ar", "en"):
            g = dev[dev["language"] == lang]
            p = preds[m][preds[m]["split"] == "dev"].merge(g, on="id")
            vals.append(fmt(macro_f1(p["label"], p["predicted"])) if len(p) else "—")
        L.append(f"| {m} | {vals[0]} | {vals[1]} |")
    L.append("")

    L.append("## Runs\n")
    L.append("| Model | Load s | Peak MB | Weights MB | torch threads | Weights file SHA-256 | = Hub etag |")
    L.append("|---|---|---|---|---|---|---|")
    for m in ORDER:
        r = models.loc[m]
        if m == "R1":
            sha, same = f"arms {arms['ar']} + {arms['en']}", "—"
        else:
            sha = f"`{r.weights_file}` `{r.weights_sha256}`"
            same = "yes" if r.weights_sha256 == r.hub_etag else "**no**"
        L.append(f"| {m} | {r.load_s:.1f} | {r.peak_mb:.0f} | {r.weights_mb:.0f} | {int(r.torch_threads)} | "
                 f"{sha} | {same} |")
    L.append("\nCPU only, one item at a time, `torch.no_grad()`, truncation at 512 tokens. Overlap counts: "
             "`results/overlap.csv` and `LEAKAGE.md`.\n")
    (RESULTS / "results.md").write_text("\n".join(L), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
