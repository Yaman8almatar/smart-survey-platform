"""Agreement on the 60 audit items (PROTOCOL.md section 5).

Reads C:\\t2\\audit\\audit_{yaman,hasan,yousef}.csv once the members have filled the label column (negative,
neutral or positive; neg, neu, pos also accepted) and writes evaluation/results/audit.md: Fleiss' kappa of the
three members and each member's agreement with the source labels. Exits cleanly, writing nothing, while the
files are still blank.
"""

import sys

import pandas as pd

from common import AUDIT, EVAL, LABELS, RESULTS

MEMBERS = ["yaman", "hasan", "yousef"]
SHORT = {"neg": "negative", "neu": "neutral", "pos": "positive"}


def read(member):
    frame = pd.read_csv(AUDIT / f"audit_{member}.csv", encoding="utf-8-sig", dtype=str, keep_default_na=False)
    labels = frame["label"].str.strip().str.lower().map(lambda v: SHORT.get(v, v))
    return frame["id"].tolist(), labels.tolist()


def fleiss_kappa(ratings):
    """ratings: one list of labels per item, one label per rater."""
    n_raters = len(ratings[0])
    counts = [[item.count(c) for c in LABELS] for item in ratings]
    p_items = [(sum(c * c for c in row) - n_raters) / (n_raters * (n_raters - 1)) for row in counts]
    p_bar = sum(p_items) / len(p_items)
    shares = [sum(row[j] for row in counts) / (len(counts) * n_raters) for j in range(len(LABELS))]
    p_e = sum(s * s for s in shares)
    return (p_bar - p_e) / (1 - p_e) if p_e < 1 else 1.0


def main():
    expected = pd.read_csv(EVAL / "audit_ids.csv")["id"].tolist()
    data = {}
    for member in MEMBERS:
        ids, labels = read(member)
        if ids != expected:
            sys.exit(f"audit_{member}.csv: ids or order differ from evaluation/audit_ids.csv.")
        data[member] = labels

    filled = {m: sum(1 for v in labels if v) for m, labels in data.items()}
    if not any(filled.values()):
        print("The audit files are still blank: nothing to compute. Fill the label column and run again.")
        return
    bad = {m: [v for v in labels if v not in LABELS] for m, labels in data.items()}
    if any(bad.values()):
        sys.exit(f"Not every row has a valid label yet (filled: {filled}; invalid or blank per member: "
                 f"{ {m: len(v) for m, v in bad.items()} }).")

    gold = pd.read_csv(EVAL / "gold_v1_ids.csv").set_index("id").loc[expected]
    kappa = fleiss_kappa([[data[m][i] for m in MEMBERS] for i in range(len(expected))])
    lines = ["# T-2 audit — agreement on the 60 audit items\n",
             f"Fleiss' kappa (3 members, 3 classes): **{kappa:.3f}**\n",
             "| Member | Agreement with source label | Arabic | English |", "|---|---|---|---|"]
    for m in MEMBERS:
        same = pd.Series(data[m], index=expected) == gold["label"]
        by_lang = same.groupby(gold["language"]).mean()
        lines.append(f"| {m} | {same.mean():.3f} | {by_lang.get('ar', float('nan')):.3f} | "
                     f"{by_lang.get('en', float('nan')):.3f} |")
    majority = []
    for i in range(len(expected)):
        votes = [data[m][i] for m in MEMBERS]
        top = max(LABELS, key=votes.count)
        majority.append(top if votes.count(top) >= 2 else None)
    agree = [mj == g for mj, g in zip(majority, gold["label"]) if mj is not None]
    lines.append(f"\nMajority label (2 of 3) agrees with the source label on {sum(agree)} of {len(agree)} items "
                 f"with a majority ({len(expected) - len(agree)} items have no majority).\n")
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "audit.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
