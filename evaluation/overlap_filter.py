"""Drop pool items that appear in a candidate's fine-tuning corpus (PROTOCOL.md section 4).

Reads C:\\t2\\data\\pools.parquet, writes C:\\t2\\data\\pools_clean.parquet and evaluation/results/overlap.csv
(counts only, no text).
"""

import pandas as pd

from common import DATA, RAW, RESULTS, overlap_hashes

POOLS = ["en_reviews", "en_service", "ar_reviews", "ar_posts"]
CLAP = RAW / "clapAI__MultiLingualSentiment" / "data"


def split_files(folder, config):
    return sorted((RAW / folder / config).glob("*/*.parquet"))


def texts(files, column, languages=None):
    for path in files:
        columns = [column] + (["language"] if languages else [])
        frame = pd.read_parquet(path, columns=columns)
        if languages:
            frame = frame[frame["language"].isin(languages)]
        yield from frame[column].dropna().astype(str)


# (candidate, corpus label, text iterator factory)
CORPORA = [
    ("M0", "cardiffnlp/tweet_eval sentiment",
     lambda: texts(split_files("cardiffnlp__tweet_eval", "sentiment"), "text")),
    ("M1", "cardiffnlp/tweet_sentiment_multilingual arabic+english",
     lambda: texts(split_files("cardiffnlp__tweet_sentiment_multilingual", "arabic")
                   + split_files("cardiffnlp__tweet_sentiment_multilingual", "english"), "text")),
    ("M2", "tyqiangz/multilingual-sentiments arabic+english",
     lambda: texts(split_files("tyqiangz__multilingual-sentiments", "arabic")
                   + split_files("tyqiangz__multilingual-sentiments", "english"), "text")),
    ("M4", "clapAI/MultiLingualSentiment ar+en",
     lambda: texts(sorted(CLAP.glob("*.parquet")), "text", {"ar", "en"})),
    ("M5", "arbml/ASTD",
     lambda: texts(split_files("arbml__ASTD", "default"), "tweet")),
    ("M5", "arbml/ArSAS",
     lambda: texts(split_files("arbml__ArSAS", "default"), "Tweet_text")),
    ("M5", "cardiffnlp/tweet_sentiment_multilingual arabic (SemEval-2017)",
     lambda: texts(split_files("cardiffnlp__tweet_sentiment_multilingual", "arabic"), "text")),
]
# Sensitivity only, not applied: clapAI rows whose language value is "multilingual".
SENSITIVITY = ("M4", "clapAI/MultiLingualSentiment multilingual (not applied)",
               lambda: texts(sorted(CLAP.glob("*.parquet")), "text", {"multilingual"}))


def hash_set(factory):
    found = set()
    rows = 0
    for text in factory():
        rows += 1
        found |= overlap_hashes(text)
    return found, rows


def main():
    pools = pd.read_parquet(DATA / "pools.parquet")
    item_hashes = pools["text"].map(overlap_hashes)
    dropped = pd.Series(False, index=pools.index)
    records = []
    for candidate, label, factory in CORPORA + [SENSITIVITY]:
        corpus, n_rows = hash_set(factory)
        hit = item_hashes.map(lambda hashes: not hashes.isdisjoint(corpus))
        applied = not label.endswith("(not applied)")
        if applied:
            dropped |= hit
        counts = pools[hit].groupby("pool").size().reindex(POOLS, fill_value=0)
        records.append({"candidate": candidate, "corpus": label, "corpus_rows": n_rows, "applied": applied,
                        **counts.to_dict(), "total": int(counts.sum())})
        print(f"{candidate} {label}: {n_rows} rows; matches {counts.to_dict()}")

    per_pool = pd.DataFrame({
        "after_filters": pools.groupby("pool").size(),
        "dropped": pools[dropped].groupby("pool").size(),
    }).reindex(POOLS).fillna(0).astype(int)
    per_pool["kept"] = per_pool["after_filters"] - per_pool["dropped"]
    print()
    print(per_pool.to_string())

    RESULTS.mkdir(parents=True, exist_ok=True)
    table = pd.DataFrame(records)
    totals = {"candidate": "all", "corpus": "dropped (union of applied corpora)", "corpus_rows": "",
              "applied": True, **per_pool["dropped"].to_dict(), "total": int(per_pool["dropped"].sum())}
    table = pd.concat([table, pd.DataFrame([totals])], ignore_index=True)
    table.to_csv(RESULTS / "overlap.csv", index=False, lineterminator="\n")
    pools[~dropped].to_parquet(DATA / "pools_clean.parquet", index=False)
    print()
    print(pools[~dropped].groupby(["pool", "split", "label"]).size().to_string())


if __name__ == "__main__":
    main()
