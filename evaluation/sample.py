"""Sample the test set gold_v1, the dev set dev_v1 and the audit files (PROTOCOL.md section 5).

Reads C:\\t2\\data\\pools_clean.parquet. Writes, outside the repository, C:\\t2\\data\\gold_v1.csv,
C:\\t2\\data\\dev_v1.csv (with text) and the three blank audit files in C:\\t2\\audit\\; in the repository,
evaluation/gold_v1_ids.csv, evaluation/dev_v1_ids.csv and evaluation/audit_ids.csv (no text).
"""

import random

import pandas as pd

from common import AUDIT, DATA, EVAL, SEED, sha256

# (pool, class, test size, dev size), in protocol order
CELLS = [
    ("en_reviews", "negative", 25, 5), ("en_reviews", "neutral", 25, 5), ("en_reviews", "positive", 25, 5),
    ("en_service", "negative", 25, 5), ("en_service", "neutral", 25, 5), ("en_service", "positive", 25, 5),
    ("ar_reviews", "negative", 25, 5), ("ar_reviews", "positive", 25, 5),
    ("ar_posts", "negative", 25, 5), ("ar_posts", "neutral", 50, 10), ("ar_posts", "positive", 25, 5),
]
TRAIN_FALLBACK = {"ar_reviews", "ar_posts"}
ID_COLUMNS = ["id", "language", "domain", "source", "source_id", "label", "text_sha256"]
MEMBERS = ["yaman", "hasan", "yousef"]
AUDIT_PER_CLASS = 10


def candidates(pools, pool, label, split):
    cell = pools[(pools["pool"] == pool) & (pools["label"] == label) & (pools["split"] == split)]
    order = sorted(cell.index, key=lambda i: int(cell.at[i, "source_id"].split(":")[1]))
    return order


def main():
    pools = pd.read_parquet(DATA / "pools_clean.parquet")
    rng = random.Random(SEED)
    test, dev, report = [], [], []
    for pool, label, n_test, n_dev in CELLS:
        first_split = "train" if pool == "en_service" else "test"
        order = candidates(pools, pool, label, first_split)
        rng.shuffle(order)
        used_train = False
        if pool in TRAIN_FALLBACK and len(order) < n_test + n_dev:
            extra = candidates(pools, pool, label, "train")
            rng.shuffle(extra)
            order += extra
            used_train = True
        cell_test, cell_dev = order[:n_test], order[n_test:n_test + n_dev]
        test += cell_test
        dev += cell_dev
        report.append({"pool": pool, "label": label, "test": len(cell_test), "test_target": n_test,
                       "dev": len(cell_dev), "dev_target": n_dev, "train_split_used": used_train})

    rng.shuffle(test)
    rng.shuffle(dev)
    gold = frame(pools, test, "g1")
    devset = frame(pools, dev, "d1")

    gold.to_csv(DATA / "gold_v1.csv", index=False, encoding="utf-8", lineterminator="\n")
    devset.to_csv(DATA / "dev_v1.csv", index=False, encoding="utf-8", lineterminator="\n")
    gold[ID_COLUMNS].to_csv(EVAL / "gold_v1_ids.csv", index=False, lineterminator="\n")
    devset[ID_COLUMNS].to_csv(EVAL / "dev_v1_ids.csv", index=False, lineterminator="\n")

    taken = {}
    audit_rows = []
    for row in gold.itertuples():
        key = (row.language, row.label)
        if taken.get(key, 0) < AUDIT_PER_CLASS:
            taken[key] = taken.get(key, 0) + 1
            audit_rows.append(row.Index)
    audit = gold.loc[audit_rows]
    audit[["id"]].to_csv(EVAL / "audit_ids.csv", index=False, lineterminator="\n")
    AUDIT.mkdir(parents=True, exist_ok=True)
    blank = pd.DataFrame({"id": audit["id"], "text": audit["text"], "label": ""})
    for member in MEMBERS:
        # utf-8-sig so that Excel shows the Arabic text correctly.
        blank.to_csv(AUDIT / f"audit_{member}.csv", index=False, encoding="utf-8-sig", lineterminator="\n")

    print(pd.DataFrame(report).to_string(index=False))
    print()
    print("test:", gold.groupby(["language", "domain", "label"]).size().to_dict())
    print("dev:", devset.groupby(["language", "domain", "label"]).size().to_dict())
    print("audit:", audit.groupby(["language", "label"]).size().to_dict())


def frame(pools, indices, prefix):
    rows = pools.loc[indices, ["language", "domain", "source", "source_id", "label", "text"]].reset_index(drop=True)
    rows.insert(0, "id", [f"{prefix}-{n:04d}" for n in range(1, len(rows) + 1)])
    rows["text_sha256"] = rows["text"].map(sha256)
    return rows


if __name__ == "__main__":
    main()
