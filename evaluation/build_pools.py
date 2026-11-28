"""Build the four test pools: sources, label maps and item filters (PROTOCOL.md section 3).

Writes C:\\t2\\data\\pools.parquet (with text, outside the repository) and prints the counts per filter step.
"""

import pandas as pd

from common import ARABIC_RANGES, DATA, LATIN_RANGES, RAW, normalise_a, script_share

SST5 = {0: "negative", 1: "negative", 2: "neutral", 3: "positive", 4: "positive"}
LABR = {0: "negative", 4: "positive"}
ARSARCASM = {"POS": "positive", "NEG": "negative", "NEU": "neutral"}
AIRLINE = {"negative": "negative", "neutral": "neutral", "positive": "positive"}


def read(folder, config, split, columns):
    frame = pd.read_parquet(RAW / folder / config / split / "0000.parquet")
    missing = [c for c in columns if c not in frame.columns]
    if missing:
        raise SystemExit(f"{folder}/{config}/{split}: missing columns {missing}; stop and ask.")
    return frame


def rows(frame, pool, language, domain, source, split, text_col, labels):
    out = pd.DataFrame({
        "pool": pool,
        "language": language,
        "domain": domain,
        "source": source,
        "split": split,
        "row": frame.index,
        "label": labels,
        "text": frame[text_col].astype(str),
    })
    return out


def en_reviews():
    frame = read("SetFit__sst5", "default", "test", ["text", "label"])
    return [rows(frame, "en_reviews", "en", "reviews", "SetFit/sst5", "test", "text", frame["label"].map(SST5))]


def en_service():
    frame = read("osanseviero__twitter-airline-sentiment", "default", "train",
                 ["text", "airline_sentiment", "airline_sentiment_confidence"])
    frame = frame[frame["airline_sentiment_confidence"] == 1.0]
    labels = frame["airline_sentiment"].map(AIRLINE)
    if labels.isna().any():
        raise SystemExit("airline: unknown airline_sentiment value; stop and ask.")
    return [rows(frame, "en_service", "en", "service", "osanseviero/twitter-airline-sentiment", "train",
                 "text", labels)]


def ar_reviews():
    parts = []
    for split in ("test", "train"):
        frame = read("mohamedadaly__labr", "plain_text", split, ["text", "label"])
        frame = frame[frame["label"].isin(LABR)]
        parts.append(rows(frame, "ar_reviews", "ar", "reviews", "mohamedadaly/labr", split, "text",
                          frame["label"].map(LABR)))
    return parts


def ar_posts():
    parts = []
    for split in ("test", "train"):
        frame = read("arbml__ArSarcasm_v2", "default", split, ["tweet", "sentiment", "dialect", "label"])
        frame = frame[(frame["dialect"] == "msa") & (frame["label"] == 0)]
        labels = frame["sentiment"].map(ARSARCASM)
        if labels.isna().any():
            raise SystemExit("ArSarcasm_v2: unknown sentiment value; stop and ask.")
        parts.append(rows(frame, "ar_posts", "ar", "posts", "arbml/ArSarcasm_v2", split, "tweet", labels))
    return parts


def keep(frame, mask, step, counts):
    frame = frame[mask]
    counts[step] = frame.groupby("pool").size()
    return frame


def main():
    pools = pd.concat(en_reviews() + en_service() + ar_reviews() + ar_posts(), ignore_index=True)
    pools["source_id"] = pools["split"] + ":" + pools["row"].astype(str)
    counts = {"source rows": pools.groupby("pool").size()}

    words = pools["text"].str.split().str.len()
    pools = keep(pools, words.between(5, 60), "5-60 words", counts)
    lower = pools["text"].str.lower()
    pools = keep(pools, ~(lower.str.contains("http", regex=False) | lower.str.contains("www.", regex=False)),
                 "no URL", counts)
    share = [
        script_share(text, ARABIC_RANGES if language == "ar" else LATIN_RANGES)
        for text, language in zip(pools["text"], pools["language"])
    ]
    pools = keep(pools, pd.Series(share, index=pools.index) >= 0.9, "script >= 90%", counts)
    # Rows are already in the protocol order: pools in table order, test before train, file order.
    pools["norm_a"] = pools["text"].map(normalise_a)
    pools = keep(pools, ~pools.duplicated(subset=["language", "norm_a"], keep="first"), "deduplicated", counts)

    table = pd.DataFrame(counts).fillna(0).astype(int)
    print(table.loc[["en_reviews", "en_service", "ar_reviews", "ar_posts"]].to_string())
    print()
    print(pools.groupby(["pool", "split", "label"]).size().to_string())
    pools.drop(columns=["norm_a", "row"]).to_parquet(DATA / "pools.parquet", index=False)


if __name__ == "__main__":
    main()
