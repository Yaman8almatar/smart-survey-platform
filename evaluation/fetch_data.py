"""Download the public test sources and fine-tuning corpora (PROTOCOL.md sections 3 and 4).

Files land in C:\\t2\\data\\raw\\<owner>__<name>\\ (outside the repository). clapAI/MultiLingualSentiment is not
downloaded: it is read from the user's local main-revision files. A folder that already holds parquet files for
every requested config is kept as it is.
"""

import os

# Weak network (D-167): set before huggingface_hub is imported.
os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "120"
os.environ["HF_HUB_ETAG_TIMEOUT"] = "60"
os.environ["HF_HUB_DISABLE_XET"] = "1"

from pathlib import Path  # noqa: E402

from huggingface_hub import snapshot_download  # noqa: E402
from huggingface_hub.errors import RevisionNotFoundError  # noqa: E402

RAW = Path(r"C:\t2\data\raw")
PARQUET_REVISION = "refs/convert/parquet"

# repo id -> configs of the parquet export to fetch
DATASETS = {
    # test sources
    "SetFit/sst5": ["default"],
    "osanseviero/twitter-airline-sentiment": ["default"],
    "mohamedadaly/labr": ["plain_text"],
    "arbml/ArSarcasm_v2": ["default"],
    # fine-tuning corpora
    "cardiffnlp/tweet_eval": ["sentiment"],
    "cardiffnlp/tweet_sentiment_multilingual": ["arabic", "english"],
    "tyqiangz/multilingual-sentiments": ["arabic", "english"],
    "arbml/ASTD": ["default"],
    "arbml/ArSAS": ["default"],
}


def local_dir(repo_id):
    return RAW / repo_id.replace("/", "__")


def has_configs(folder, configs):
    return all(any((folder / config).rglob("*.parquet")) for config in configs)


def fetch(repo_id, configs):
    folder = local_dir(repo_id)
    if has_configs(folder, configs):
        return "kept"
    try:
        snapshot_download(
            repo_id=repo_id,
            repo_type="dataset",
            revision=PARQUET_REVISION,
            allow_patterns=[f"{config}/*" for config in configs],
            local_dir=folder,
        )
        if not has_configs(folder, configs):
            raise SystemExit(f"{repo_id}: parquet export has no files for {configs}; stop and ask.")
        return PARQUET_REVISION
    except RevisionNotFoundError:
        # PROTOCOL: fall back to the main revision for this dataset and report it.
        snapshot_download(repo_id=repo_id, repo_type="dataset", revision="main", local_dir=folder)
        return "main (parquet export refused)"


def main():
    for repo_id, configs in DATASETS.items():
        revision = fetch(repo_id, configs)
        files = sorted(
            str(p.relative_to(local_dir(repo_id))) for p in local_dir(repo_id).rglob("*")
            if p.is_file() and ".cache" not in p.parts
        )
        print(f"{repo_id}: {revision}")
        for name in files:
            print(f"    {name}")
    clap = RAW / "clapAI__MultiLingualSentiment" / "data"
    print("clapAI/MultiLingualSentiment: local files")
    for p in sorted(clap.glob("*.parquet")):
        print(f"    {p.name}")


if __name__ == "__main__":
    main()
