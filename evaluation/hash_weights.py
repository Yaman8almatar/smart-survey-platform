"""Record the SHA-256 of one model's weights file in evaluation/results/models.csv (D-177).

Usage: python hash_weights.py M0   (one model per command: M0 ... M5)
The value can be compared with the Hub's etag of the file (for LFS files the etag is the file's SHA-256).
"""

import hashlib
import sys

from run_models import CANDIDATES, upsert_model, weights_file


def main():
    model_id = sys.argv[1] if len(sys.argv) == 2 else None
    if model_id not in CANDIDATES:
        raise SystemExit(__doc__)
    path = weights_file(model_id)
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(2**20), b""):
            digest.update(block)
    upsert_model({"id": model_id, "weights_file": path.name, "weights_sha256": digest.hexdigest(),
                  "hub_etag": hub_etag(path)})
    print(model_id, path.name, digest.hexdigest(), "etag", hub_etag(path))


def hub_etag(path):
    """The etag that `hf download --local-dir` stored for the file (second line of its .metadata)."""
    metadata = path.parent / ".cache" / "huggingface" / "download" / f"{path.name}.metadata"
    return metadata.read_text(encoding="utf-8").splitlines()[1].strip() if metadata.exists() else ""


if __name__ == "__main__":
    main()
