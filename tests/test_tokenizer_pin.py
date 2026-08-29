"""The committed tokenizer file must match every recorded source hash.

Hermetic: reads only committed files, never the network. The one-time
three-way live assertion happened at fetch time and is recorded in
provenance.json; this test keeps it true forever.
"""
import hashlib
import json

import pytest

from eval.tokenizer_pin import (
    INSTRUCT_REPOS,
    PROVENANCE_FILE,
    TOKENIZER_FILE,
    QWEN_REPOS,
    committed_pin,
)


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


def test_instruct_attestation_pinned():
    file_hash = hashlib.sha256(TOKENIZER_FILE.read_bytes()).hexdigest()
    prov = json.loads(PROVENANCE_FILE.read_text(encoding="utf-8"))
    entries = prov["instruct_repos"]
    assert len(entries) == 3
    assert {e["repo"] for e in entries} == set(INSTRUCT_REPOS)
    for e in entries:
        assert e["sha256"] == file_hash, e["repo"]
        assert e["revision"]


def test_fetch_instruct_raises_on_mismatch(monkeypatch, tmp_path):
    import eval.tokenizer_pin as tp
    (tmp_path / "tokenizer.json").write_bytes(b"pinned-bytes")
    (tmp_path / "provenance.json").write_text(json.dumps({
        "file": "tokenizer.json",
        "repos": [{"repo": r, "revision": "x",
                   "sha256": hashlib.sha256(b"pinned-bytes").hexdigest()}
                  for r in tp.QWEN_REPOS]}), encoding="utf-8")
    monkeypatch.setattr(tp, "TOKENIZER_FILE", tmp_path / "tokenizer.json")
    monkeypatch.setattr(tp, "PROVENANCE_FILE", tmp_path / "provenance.json")
    monkeypatch.setattr(tp, "_get", lambda url: b'{"sha": "r"}'
                        if "api" in url else b"DIFFERENT-bytes")
    with pytest.raises(tp.PinError):
        tp.fetch_instruct(dest=tmp_path)
