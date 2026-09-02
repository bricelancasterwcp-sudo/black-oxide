"""The committed sha256 ledger for the fine-tune adapters.

The adapters every v0.4 dynamic number rests on live outside the repo and
outside version control. This ledger is the only in-repo record of what
they are, so its shape has to stay machine-checkable: `sha256sum -c` must
accept the non-comment lines verbatim, which means exactly the format
sha256sum writes and nothing else.
"""

import re
from pathlib import Path

LEDGER = Path(__file__).resolve().parents[1] / "eval" / "results" / "ADAPTER-SHAS.txt"

# sha256sum's own text format: 64 lowercase hex, TWO spaces, then the path.
# One space is not the same file -- `sha256sum -c` rejects it -- so the
# separator is pinned as tightly as the hash.
HASH_LINE = re.compile(r"^([0-9a-f]{64})  (\S.*)$")

V5_ADAPTERS = (
    "adapters-v5/tune-ox-7-v5/adapter_model.safetensors",
    "adapters-v5/tune-rs-7-v5/adapter_model.safetensors",
    "adapters-v5/tune-ox-14-v5/adapter_model.safetensors",
    "adapters-v5/tune-rs-14-v5/adapter_model.safetensors",
)

# Quoted in the ledger's header as the hash a truncated transfer failed
# against. If the line moves, the header's account of that stops being true.
TUNE_RS_14_V5 = "57b322601a4c296224742855a3ab90c7ca9081114fd8f043a5057f60f1e72d29"


def _entries() -> dict[str, str]:
    """path -> hash, over every line that is not a comment.

    Blank lines are NOT skipped: they are not comments, they fail the
    pattern, and `sha256sum -c` would reject them too.
    """
    entries: dict[str, str] = {}
    for line in LEDGER.read_text(encoding="utf-8").split("\n")[:-1]:
        if line.startswith("#"):
            continue
        match = HASH_LINE.match(line)
        assert match is not None, f"not a sha256sum line: {line!r}"
        entries[match.group(2)] = match.group(1)
    return entries


def test_every_non_comment_line_is_a_sha256sum_entry():
    entries = _entries()
    assert len(entries) == 17  # 9 pod-built GGUFs + 8 preserved adapters


def test_the_four_v5_adapters_are_present_for_both_arms_at_7b_and_14b():
    """These four are the ones wave 8 Phase B and the 14B screen served,
    and the ones wave 9 reuses. Losing a line here loses the ability to
    tell a good transfer from a truncated one."""
    entries = _entries()
    for path in V5_ADAPTERS:
        assert path in entries, f"missing v5 adapter line: {path}"
    assert entries["adapters-v5/tune-rs-14-v5/adapter_model.safetensors"] == (
        TUNE_RS_14_V5
    )


def test_the_v5_adapter_hashes_are_all_distinct():
    """Two arms sharing a hash would mean a merge did not apply -- the
    exact failure the wave-8 provenance checks GGUFs for, one stage
    earlier."""
    entries = _entries()
    hashes = [entries[p] for p in V5_ADAPTERS]
    assert len(set(hashes)) == len(V5_ADAPTERS)


def test_the_header_says_the_adapters_are_preserved_and_the_ggufs_are_not():
    """The distinction is the file's whole point: one kind of line names
    something recoverable, the other names something that is gone if the
    local copy is gone."""
    header = "\n".join(
        line
        for line in LEDGER.read_text(encoding="utf-8").split("\n")
        if line.startswith("#")
    )
    assert "NOT preserved" in header
    assert "ARE preserved locally" in header
    assert "oxide-runpod-artifacts/wave4/adapters-v5/" in header
    assert "NEVER BY FILE COUNT" in header
