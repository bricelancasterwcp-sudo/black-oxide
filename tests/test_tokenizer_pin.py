"""The committed tokenizer file must match every recorded source hash.

Hermetic: reads only committed files, never the network. The one-time
three-way live assertion happened at fetch time and is recorded in
provenance.json; this test keeps it true forever.
"""
import hashlib
import json

from eval.tokenizer_pin import PROVENANCE_FILE, TOKENIZER_FILE, QWEN_REPOS, committed_pin


def test_tokenizer_identity_pin():
    file_hash = hashlib.sha256(TOKENIZER_FILE.read_bytes()).hexdigest()
    prov = json.loads(PROVENANCE_FILE.read_text(encoding="utf-8"))
    entries = prov["repos"]
    assert len(entries) == 3
    assert {e["repo"] for e in entries} == set(QWEN_REPOS)
    for e in entries:
        assert e["sha256"] == file_hash, e["repo"]
        assert e["revision"]  # resolved commit, never a branch name
    assert committed_pin() == file_hash
