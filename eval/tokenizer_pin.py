"""One tokenizer, pinned by content hash, attested from three checkpoints.

The spec requires all three Qwen2.5-Coder sizes to share a tokenizer.
`fetch()` downloads tokenizer.json from each repo at its resolved
revision, asserts the three files are byte-identical, and commits ONE
copy plus a provenance record. Everything afterwards (tests, the
builder CLI) trusts only the committed pair via `committed_pin()`.
"""
from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path

QWEN_REPOS = (
    "Qwen/Qwen2.5-Coder-1.5B",
    "Qwen/Qwen2.5-Coder-7B",
    "Qwen/Qwen2.5-Coder-14B",
)
TOKENIZER_DIR = Path("eval/train/tokenizer")
TOKENIZER_FILE = TOKENIZER_DIR / "tokenizer.json"
PROVENANCE_FILE = TOKENIZER_DIR / "provenance.json"
_API = "https://huggingface.co/api/models/{repo}"
_RESOLVE = "https://huggingface.co/{repo}/resolve/{rev}/tokenizer.json"


class PinError(RuntimeError):
    """The tokenizer pin does not hold; nothing downstream may run."""


def _get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as resp:
        return resp.read()


def fetch(repos: tuple[str, ...] = QWEN_REPOS, dest: Path = TOKENIZER_DIR) -> dict:
    """Download, three-way assert, and write the committed pin files."""
    entries = []
    blobs = []
    for repo in repos:
        info = json.loads(_get(_API.format(repo=repo)))
        rev = info["sha"]
        blob = _get(_RESOLVE.format(repo=repo, rev=rev))
        entries.append(
            {"repo": repo, "revision": rev,
             "sha256": hashlib.sha256(blob).hexdigest()}
        )
        blobs.append(blob)
    hashes = {e["sha256"] for e in entries}
    if len(hashes) != 1:
        raise PinError(f"tokenizers differ across checkpoints: {entries}")
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "tokenizer.json").write_bytes(blobs[0])
    provenance = {"file": "tokenizer.json", "repos": entries}
    (dest / "provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return provenance


def committed_pin() -> str:
    """The pinned sha256, after re-asserting file-vs-provenance agreement."""
    file_hash = hashlib.sha256(TOKENIZER_FILE.read_bytes()).hexdigest()
    prov = json.loads(PROVENANCE_FILE.read_text(encoding="utf-8"))
    for e in prov["repos"]:
        if e["sha256"] != file_hash:
            raise PinError(
                f"committed tokenizer.json does not match {e['repo']} "
                f"({e['sha256']} != {file_hash})"
            )
    return file_hash


if __name__ == "__main__":
    print(json.dumps(fetch(), indent=2, sort_keys=True))
