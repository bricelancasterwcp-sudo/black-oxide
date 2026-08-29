# RunPod Fine-Tune Experiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the token-matched Black Oxide vs Rust fine-tune experiment:
6 QLoRA trainings, 12 eval arms on one RunPod environment, pre-registered
endpoints computed once at the end.

**Architecture:** Local instrument tasks first (attestation, card-free
prompt mode, analysis module, campaign driver — all TDD'd against the
existing harness), then pod-side scripts, then three execution tasks
(dry-run cost gate, trainings, campaign) that follow written procedures
with STOP conditions, and a final analysis/report task. The existing
`run_session` 4-attempt loop IS the iterations-to-green instrument; the
existing `probe_campaign` IS the strict-repair instrument — this plan
extends, never rebuilds.

**Tech Stack:** Python 3.14 `.venv` locally (stdlib + pytest); pod side
runpod/pytorch image (torch 2.9.1+cu129, Python 3.12) with transformers
5.5.0 / peft 0.20.0, llama.cpp (CUDA build, pinned commit) for
convert/quantize/serve; RunPod REST API.

**Spec:** `docs/superpowers/specs/2026-08-27-runpod-experiment-design.md`
(and, inherited, `2026-08-27-token-matching-design.md`). The plan argues
from the spec; executors read both.

## Global Constraints

- Branch `finetune-experiment`; commit per task; push at the end of local
  tasks and after each execution task.
- Tests: `.venv/bin/pytest` from repo root. Suite baseline at plan time:
  **1520 passed, 3 deselected**.
- **Mutation discipline:** before EVERY test run in a mutation check
  (mutated AND restored):
  `export PYTHONDONTWRITEBYTECODE=1` and
  `find . -name __pycache__ -type d -prune -exec rm -rf {} +`.
- Protected paths (read-only): `eval/tasks.jsonl`, `eval/solutions/`,
  `eval/train/tasks.jsonl`, `eval/train/pairs/`, `eval/train/matched/`,
  `eval/probes.jsonl`, everything under `eval/results/` except the NEW
  `eval/results/runpod-exp/` this experiment creates.
- Sampler pinned: temperature **0.2**, top_p 0.95, seeds **1–10**,
  `num_ctx 8192`, `num_predict 2048`. Unconstrained: `grammar=None`
  everywhere.
- Budget: **$23** available now; top-up at 16:30 2026-08-28. The tranche
  boundary is an infrastructure pause; **no endpoint is computed before
  all 12 arms have `.DONE`** — the analysis module enforces this.
- RunPod API key: `~/.config/runpod/api_key`. Never print, commit, or
  copy it anywhere; scripts read it at call time.
- Default-parameter behavior of every touched harness function must stay
  byte-identical (existing 1520 tests are the guard; new byte-stability
  tests pin the prompt paths specifically).
- Spec amendments discovered by this plan are made **non-silently**
  (dated footnotes) in the named task, never silently.

---

### Task 1: Instruct-checkpoint tokenizer attestation

**Files:**
- Modify: `eval/tokenizer_pin.py`
- Modify: `tests/test_tokenizer_pin.py`
- Modify (generated, committed): `eval/train/tokenizer/provenance.json`

**Interfaces:**
- Consumes: existing `fetch`, `committed_pin`, `PinError`, `_get`,
  `_API`, `_RESOLVE`, `TOKENIZER_DIR`, `TOKENIZER_FILE`,
  `PROVENANCE_FILE` in `eval/tokenizer_pin.py`.
- Produces: `INSTRUCT_REPOS: tuple[str, str, str]`,
  `fetch_instruct(dest: Path = TOKENIZER_DIR) -> dict` (raises
  `PinError` on any hash mismatch with the committed pin). Task 7's
  procedure treats this task's committed attestation as its gate.

- [ ] **Step 1: Write the failing test** (append to `tests/test_tokenizer_pin.py`)

```python
from eval.tokenizer_pin import INSTRUCT_REPOS


def test_instruct_attestation_pinned():
    file_hash = hashlib.sha256(TOKENIZER_FILE.read_bytes()).hexdigest()
    prov = json.loads(PROVENANCE_FILE.read_text(encoding="utf-8"))
    entries = prov["instruct_repos"]
    assert len(entries) == 3
    assert {e["repo"] for e in entries} == set(INSTRUCT_REPOS)
    for e in entries:
        assert e["sha256"] == file_hash, e["repo"]
        assert e["revision"]
```

(The file already imports `hashlib`, `json`, `TOKENIZER_FILE`,
`PROVENANCE_FILE` — extend the existing import line for
`INSTRUCT_REPOS`.)

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_tokenizer_pin.py -v`
Expected: FAIL — `ImportError: cannot import name 'INSTRUCT_REPOS'`

- [ ] **Step 3: Implement** (append to `eval/tokenizer_pin.py`; replace the `__main__` block)

```python
INSTRUCT_REPOS = (
    "Qwen/Qwen2.5-Coder-1.5B-Instruct",
    "Qwen/Qwen2.5-Coder-7B-Instruct",
    "Qwen/Qwen2.5-Coder-14B-Instruct",
)


def fetch_instruct(dest: Path = TOKENIZER_DIR) -> dict:
    """Attest the -Instruct checkpoints against the committed pin.

    The token matching was computed under the pinned tokenizer; a
    mismatching instruct tokenizer invalidates it, so this raises
    rather than recording the difference.
    """
    committed = committed_pin()
    entries = []
    for repo in INSTRUCT_REPOS:
        info = json.loads(_get(_API.format(repo=repo)))
        rev = info["sha"]
        blob = _get(_RESOLVE.format(repo=repo, rev=rev))
        digest = hashlib.sha256(blob).hexdigest()
        if digest != committed:
            raise PinError(
                f"{repo} tokenizer.json {digest} != committed pin "
                f"{committed}; the token matching is invalid for this "
                f"checkpoint — stop the experiment"
            )
        entries.append({"repo": repo, "revision": rev, "sha256": digest})
    prov = json.loads((dest / "provenance.json").read_text(encoding="utf-8"))
    prov["instruct_repos"] = entries
    (dest / "provenance.json").write_text(
        json.dumps(prov, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return prov


if __name__ == "__main__":
    import sys

    _fn = fetch_instruct if "instruct" in sys.argv[1:] else fetch
    print(json.dumps(_fn(), indent=2, sort_keys=True))
```

- [ ] **Step 4: Run the one-time attestation fetch**

Run: `cd ~/workspace/oxide && .venv/bin/python -m eval.tokenizer_pin instruct`
Expected: JSON whose `instruct_repos` has 3 entries, every `sha256`
equal to the committed pin (`c0382117…`), 3 distinct resolved
`revision` commits. Needs network (~7MB × 3). **If any hash differs,
STOP and report BLOCKED** — this is the spec's fail-closed gate.

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_tokenizer_pin.py -v`
Expected: 2 PASS

- [ ] **Step 6: Mutation-check** (pyc preamble each run)

1. Edit provenance.json: change one hex char of one `instruct_repos`
   sha256 → test must FAIL. Restore by re-running Step 4.
2. In `fetch_instruct`, replace `raise PinError(...)` mismatch branch
   with `pass` — with a clean provenance the test still passes, so ALSO
   hand-set one instruct hash wrong and re-run `fetch_instruct` with a
   stubbed `_get`? No — simpler and honest: this branch's guard is
   live-only; assert it via a unit test instead:

```python
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
```

   Add this test (with `import pytest` in the imports), verify it
   passes, then mutation-check IT: replace the mismatch `raise` with
   `entries.append(...)`-only → the test must FAIL. Restore.

- [ ] **Step 7: Commit**

```bash
git add eval/tokenizer_pin.py tests/test_tokenizer_pin.py eval/train/tokenizer/provenance.json
git commit -m "feat: attest -Instruct tokenizers against the committed pin (fail-closed)"
```

---

### Task 2: Card-free prompt mode across harness, repair, probe, driver

**Files:**
- Modify: `eval/harness.py` (`build_prompt`, ~line 243)
- Modify: `eval/repair.py` (`initial_context`, `build_repair_prompt`)
- Modify: `eval/probe.py` (`build_probe_prompt`, ~line 178; `run_corpus`)
- Modify: `eval/probe_campaign.py` (`run_cell`, `run_campaign`)
- Modify: `eval/driver.py` (`run_session`, ~line 37)
- Modify: `docs/superpowers/specs/2026-08-27-token-matching-design.md`
  (one dated footnote) and
  `docs/superpowers/specs/2026-08-27-runpod-experiment-design.md`
  (two dated footnotes)
- Create: `tests/test_cardfree.py`

**Interfaces:**
- Produces (later tasks rely on these exact signatures):
  - `harness.build_prompt(arm, task_id, shots=0, tasks_path=None, include_lead: bool = True) -> str`
    — `include_lead=False` yields exactly
    `"Task:\n" + task_prompt + "\n\n" + OUTPUT_CONTRACT + "\n"` and
    raises `HarnessError` if `shots > 0`.
  - `repair.initial_context(arm, task_id, shots=0, tasks_path=None, include_lead=True)`
    and `repair.build_repair_prompt(arm, source, verdict, *, task_id, shots=0, tasks_path=None, include_lead=True)` — passthrough.
  - `probe.build_probe_prompt(record, diagnostics=None, *, include_card: bool = True)`
    — `include_card=False` omits the `language_card(arm)` section (the
    prompt then starts with `PROBE_INSTRUCTION`).
  - `probe.run_corpus(..., include_card: bool = True)`,
    `probe_campaign.run_cell(root, arm, seed, client_factory, include_card: bool = True)`,
    `probe_campaign.run_campaign(root, arms, seeds, *, client_factory, provenance=None, include_card: bool = True)` — threaded through to
    `build_probe_prompt`.
  - `driver.run_session(..., include_lead: bool = True)` — threads to
    both `harness.build_prompt` and `build_repair_prompt` calls inside.
- All defaults `True` ⇒ byte-identical legacy behavior.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_cardfree.py
"""Card-free prompt mode: tuned arms see no lead material anywhere.

The experiment spec's tuned arms are card-free in generation, repair
rounds, and seeded-defect probes alike; the default path must stay
byte-identical (the 1520-test suite pins most of it; the first test
pins the equality explicitly).
"""
import pytest

from eval import harness, probe
from eval.repair import build_repair_prompt


def _card(arm: str) -> str:
    return (harness._REPO_ROOT / harness.CARD_FILES[arm]).read_text(
        encoding="utf-8"
    )


def test_default_prompt_byte_identical_to_explicit_true():
    assert harness.build_prompt("oxide", "t01") == harness.build_prompt(
        "oxide", "t01", include_lead=True
    )


def test_cardfree_prompt_is_task_and_contract_only():
    task = harness.load_tasks()["t01"]
    p = harness.build_prompt("oxide", "t01", include_lead=False)
    assert p == (
        "Task:\n" + task["prompt"].rstrip("\n") + "\n\n"
        + harness.OUTPUT_CONTRACT + "\n"
    )
    assert _card("oxide")[:80] not in p


def test_cardfree_rust_prompt_drops_preamble():
    p = harness.build_prompt("rust", "t01", include_lead=False)
    assert harness.RUST_PREAMBLE.strip()[:40] not in p


def test_cardfree_shots_refused():
    with pytest.raises(harness.HarnessError):
        harness.build_prompt("oxide", "t01", shots=3, include_lead=False)


def test_cardfree_repair_prompt_retains_no_card():
    verdict = {"compiled": True, "passed": False, "stdout": "wrong\n"}
    p = build_repair_prompt(
        "oxide", "fn main() { }", verdict, task_id="t01", include_lead=False
    )
    assert _card("oxide")[:80] not in p
    assert "The program below was rejected" in p
    assert "Task:\n" in p  # the task statement itself is retained


def test_cardfree_probe_prompt():
    rec = next(r for r in probe.load_probes() if r["arm"] == "oxide")
    diags = [{"code": "OX0400", "message": "m", "line": 1}]
    with_card = probe.build_probe_prompt(rec, diags)
    without = probe.build_probe_prompt(rec, diags, include_card=False)
    assert probe.language_card("oxide")[:80] in with_card
    assert probe.language_card("oxide")[:80] not in without
    assert without.startswith(probe.PROBE_INSTRUCTION[:20])
```

Note: if `render_diagnostics` rejects the minimal `diags` dict shape,
read `eval/repair.py:37` and adjust the fixture to the real field names
— the assertion targets stay the same.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_cardfree.py -v`
Expected: FAIL — `TypeError: build_prompt() got an unexpected keyword argument 'include_lead'`

- [ ] **Step 3: Implement**

In `harness.build_prompt`: add the parameter; guard shots; make the
lead section conditional. The exact change to the body (everything else
unchanged):

```python
def build_prompt(
    arm: str,
    task_id: str,
    shots: int = 0,
    tasks_path: str | Path | None = None,
    include_lead: bool = True,
) -> str:
    """The complete solver prompt for one task in one arm (section 45).

    ``include_lead=False`` (the fine-tune experiment's tuned arms) drops
    the language card / Rust preamble and forbids shots: the tuned model
    carries the language in its weights, and the rendering must equal
    the training rendering exactly.
    """
    _require_arm(arm)
    if shots < 0:
        raise HarnessError("--shots must be >= 0")
    if shots and not include_lead:
        raise HarnessError(
            "shots require the lead material; card-free prompts are 0-shot"
        )
    task = _get_task(task_id, tasks_path)
    sections: list[str] = []
    if include_lead:
        if arm == "rust":
            lead = RUST_PREAMBLE
        else:
            card_path = _REPO_ROOT / CARD_FILES[arm]
            try:
                lead = card_path.read_text(encoding="utf-8")
            except OSError as exc:
                raise HarnessError(
                    f"cannot read language card '{card_path}': {exc}"
                ) from exc
        sections.append(lead.rstrip("\n"))
    if shots:
        pairs = load_shots(arm)
        if shots > len(pairs):
            raise HarnessError(
                f"arm '{arm}' has only {len(pairs)} shots (requested {shots})"
            )
        for task_text, solution in pairs[:shots]:
            sections.append(
                "Example task:\n"
                + task_text.rstrip("\n")
                + "\n\nExample solution:\n"
                + solution.rstrip("\n")
            )
    sections.append("Task:\n" + task["prompt"].rstrip("\n"))
    sections.append(OUTPUT_CONTRACT)
    return "\n\n".join(sections) + "\n"
```

In `eval/repair.py`: add `include_lead: bool = True` to
`initial_context` and `build_repair_prompt`; each passes it down
(`harness.build_prompt(..., include_lead=include_lead)` /
`initial_context(..., include_lead=include_lead)`). No other change —
the contract-stripping logic is lead-agnostic.

In `eval/probe.py` `build_probe_prompt`: add keyword-only
`include_card: bool = True`; build the return as

```python
    lead = f"{language_card(arm)}\n\n" if include_card else ""
    return (
        f"{lead}"
        f"{PROBE_INSTRUCTION}\n\n"
        ...unchanged tail...
    )
```

In `probe.run_corpus`: add `include_card: bool = True` and pass it to
its `build_probe_prompt` call (read the function; it is the only call
site). In `probe_campaign.run_cell` and `run_campaign`: add
`include_card: bool = True` and thread it through (`run_cell` →
`run_corpus`; `run_campaign` → `run_cell`).

In `eval/driver.py` `run_session`: add `include_lead: bool = True`;
pass to the initial `harness.build_prompt(...)` call and to the
`build_repair_prompt(...)` call in the attempt loop.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_cardfree.py -q && .venv/bin/pytest -q`
Expected: 6 new PASS; full suite green (1520 + 6, 3 deselected) — the
full-suite run is mandatory here: it is the byte-stability guard for
every default path this task touched.

- [ ] **Step 5: Spec amendments (non-silent)**

Append to `docs/superpowers/specs/2026-08-27-runpod-experiment-design.md`,
at the end of the "New components" section:

```markdown
> **Amended 2026-08-27 (implementation):** the K=4 repair loop already
> exists — `harness.Session`/`driver.run_session` implement exactly the
> spec's loop (MAX_ATTEMPTS=4, diagnostics fed back, per-session token
> accounting). The `eval/repair_loop.py` row is withdrawn; the metric
> extraction lands in `eval/experiment_report.py` instead. Also
> amended: the base-rs arms keep `RUST_PREAMBLE` (their measured lead
> condition); the card table's "no" refers to the language card only.
```

Append to `docs/superpowers/specs/2026-08-27-token-matching-design.md`,
at the end of Decision 4:

```markdown
> **Amended 2026-08-27 (experiment plan):** "bare prompt" means bare of
> lead material (card/preamble). The arm-neutral `OUTPUT_CONTRACT` is
> included in the training user turn so the train and eval renderings
> are byte-equal (`harness.build_prompt(..., include_lead=False)` is
> the single rendering function for both). Prompt tokens were never
> matched, only reported, so this changes no budget.
```

- [ ] **Step 6: Mutation-check** (pyc preamble each run)

1. In `build_prompt`, make `include_lead` dead (`include_lead = True`
   first line): cardfree prompt tests must FAIL.
2. Delete the shots guard: `test_cardfree_shots_refused` must FAIL.
3. In `build_probe_prompt`, make `include_card` dead:
   `test_cardfree_probe_prompt` must FAIL.
4. In `run_session`, drop `include_lead` from the
   `build_repair_prompt` call only: no current test fails (repair-round
   leakage is exercised end-to-end in Task 4's fake-client test, which
   asserts on EVERY prompt the client saw) — record this as the known
   gap this round, closed by Task 4 mutation 3. Restore.

- [ ] **Step 7: Commit**

```bash
git add eval/harness.py eval/repair.py eval/probe.py eval/probe_campaign.py eval/driver.py tests/test_cardfree.py docs/superpowers/specs/
git commit -m "feat: card-free prompt mode for tuned arms — generation, repair rounds, probes"
```

---

### Task 3: Analysis module with completion refusal

**Files:**
- Create: `eval/experiment_report.py`
- Create: `tests/test_experiment_report.py`

**Interfaces:**
- Consumes: cells.jsonl rows as `run_session` writes them
  (`first_passed`, `final_passed`, `attempts_to_pass`, `tokens_out`,
  `task`, `arm`, `attempts`); probe cell dirs as `probe_campaign`
  writes them.
- Produces:

```python
ARM_NAMES = (
    "base-ox-1.5", "base-ox-7", "base-ox-14",
    "base-rs-1.5", "base-rs-7", "base-rs-14",
    "tune-ox-1.5", "tune-ox-7", "tune-ox-14",
    "tune-rs-1.5", "tune-rs-7", "tune-rs-14",
)
SIZES = ("1.5", "7", "14")
class ReportError(RuntimeError): ...
def load_cells(arm_dir: Path) -> list[dict]         # every gen-s*/cells.jsonl row
def gen_metrics(cells: list[dict]) -> dict          # see body below
def paired_pass1(a_cells, b_cells) -> dict          # {"delta_pp","two_se_pp","n_tasks"}
def unpaired_pass1(a_cells, b_cells) -> dict        # {"a","b","delta_pp","two_se_pp"}
def strict_repair_rate(probes_root: Path) -> dict   # {"rate","n"} via probe scoring
def require_complete(root: Path) -> None            # raises ReportError w/ missing arms
def build_report(root: Path) -> dict                # full pre-registered endpoint tree
def main(argv: list[str] | None = None) -> int      # python -m eval.experiment_report --root ...
```

- [ ] **Step 1: Read the probe scoring section**

Read `eval/probe.py` from line 205 to the end and note the committed
scoring entry points (the ownership studies computed strict repair
rates from probe cell dirs — reuse exactly those functions in
`strict_repair_rate`; do not reimplement scoring).

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_experiment_report.py
"""The analysis instrument: pre-registered endpoints, refusal until done.

Synthetic fixtures exercise the math; the acceptance test pins the
instrument against the committed v03 closing baseline (qwen oxide
first-pass 0.305, rust 0.565 — the published REPORT numbers).
"""
import json
from pathlib import Path

import pytest

from eval.experiment_report import (
    ARM_NAMES,
    ReportError,
    gen_metrics,
    load_cells,
    paired_pass1,
    require_complete,
    unpaired_pass1,
)


def _cell(task, first, final, attempts_to_pass=1, tokens_out=50):
    return {"task": task, "arm": "oxide", "first_passed": first,
            "final_passed": final, "attempts_to_pass": attempts_to_pass,
            "tokens_out": tokens_out, "attempts": attempts_to_pass}


def test_gen_metrics_shapes_and_censoring():
    cells = [
        _cell("t01", True, True, 1, 40),
        _cell("t01", False, True, 3, 90),
        _cell("t02", False, False, 5, 200),  # never green: sentinel 5
        _cell("t02", False, False, 5, 210),
    ]
    m = gen_metrics(cells)
    assert m["n"] == 4
    assert m["pass1"] == 0.25
    assert m["pass10_verifier"] == 0.5      # t01 green, t02 never
    assert m["tokens_to_green_mean"] == 65.0  # mean(40, 90) — censored excluded
    assert m["iters_to_green_mean"] == 2.0
    assert m["censored_sessions"] == 2


def test_gen_metrics_all_censored_is_none_not_zero():
    cells = [_cell("t01", False, False, 5, 100)]
    m = gen_metrics(cells)
    assert m["tokens_to_green_mean"] is None
    assert m["iters_to_green_mean"] is None
    assert m["censored_sessions"] == 1


def test_paired_pass1_hand_computed():
    a = [_cell("t01", True, True), _cell("t01", True, True),
         _cell("t02", False, False, 5), _cell("t02", True, True)]
    b = [_cell("t01", False, False, 5), _cell("t01", True, True),
         _cell("t02", False, False, 5), _cell("t02", False, False, 5)]
    r = paired_pass1(a, b)
    # per-task rates: a={t01:1.0,t02:0.5} b={t01:0.5,t02:0.0}; diffs 0.5,0.5
    assert r["delta_pp"] == 50.0
    assert r["two_se_pp"] == 0.0
    assert r["n_tasks"] == 2


def test_unpaired_pass1_hand_computed():
    a = [_cell("t01", True, True)] * 3 + [_cell("t01", False, False, 5)]
    b = [_cell("t01", False, False, 5)] * 4
    r = unpaired_pass1(a, b)
    assert r["a"] == 0.75 and r["b"] == 0.0
    assert r["delta_pp"] == 75.0
    assert r["two_se_pp"] == pytest.approx(2 * (0.75 * 0.25 / 4) ** 0.5 * 100, abs=0.1)


def test_require_complete_refuses_and_names_missing(tmp_path):
    for arm in ARM_NAMES[:-1]:
        d = tmp_path / arm
        d.mkdir()
        (d / ".DONE").write_text("")
    with pytest.raises(ReportError, match=ARM_NAMES[-1]):
        require_complete(tmp_path)
    d = tmp_path / ARM_NAMES[-1]
    d.mkdir()
    (d / ".DONE").write_text("")
    require_complete(tmp_path)  # now silent


def test_load_cells_reads_all_seed_runs(tmp_path):
    arm = tmp_path / "base-ox-7"
    for seed in (1, 2):
        run = arm / f"gen-s{seed}"
        run.mkdir(parents=True)
        (run / "cells.jsonl").write_text(
            json.dumps(_cell("t01", True, True)) + "\n", encoding="utf-8"
        )
    assert len(load_cells(arm)) == 2


def test_acceptance_v03_closing_baseline_qwen():
    root = Path("eval/results/v03-closing-baseline")
    runs = sorted(root.glob("*qwen*"))
    assert runs, "discover the real dir naming with ls and pin it here"
    cells = []
    for run in runs:
        cells += [json.loads(l) for l in
                  (run / "cells.jsonl").read_text(encoding="utf-8").splitlines()]
    oxide = [c for c in cells if c["arm"] == "oxide"]
    rust = [c for c in cells if c["arm"] == "rust"]
    assert gen_metrics(oxide)["pass1"] == pytest.approx(0.305, abs=1e-9)
    assert gen_metrics(rust)["pass1"] == pytest.approx(0.565, abs=1e-9)
```

Before running: `ls eval/results/v03-closing-baseline/` and adjust the
glob to the actual qwen run naming (then keep it PINNED — the test must
enumerate deterministically). If the published rates were computed over
a different key or run subset, STOP and report rather than loosening
the assertion: this acceptance pin is the instrument's licence.

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_experiment_report.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'eval.experiment_report'`

- [ ] **Step 4: Implement**

```python
# eval/experiment_report.py
"""Pre-registered endpoints for the RunPod fine-tune experiment.

Computes ONLY what the spec registers, and refuses to run before all
twelve arms are complete — the no-interim-analysis rule is enforced
here, in code, not by convention. Censored values are None and named,
never zero (a value that looks like a measurement but is not).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ARM_NAMES = (
    "base-ox-1.5", "base-ox-7", "base-ox-14",
    "base-rs-1.5", "base-rs-7", "base-rs-14",
    "tune-ox-1.5", "tune-ox-7", "tune-ox-14",
    "tune-rs-1.5", "tune-rs-7", "tune-rs-14",
)
SIZES = ("1.5", "7", "14")


class ReportError(RuntimeError):
    """The analysis cannot honestly run; nothing is computed."""


def load_cells(arm_dir: Path) -> list[dict]:
    cells: list[dict] = []
    for path in sorted(Path(arm_dir).glob("gen-s*/cells.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                cells.append(json.loads(line))
    return cells


def gen_metrics(cells: list[dict]) -> dict:
    if not cells:
        raise ReportError("no cells to score")
    n = len(cells)
    by_task: dict[str, list[dict]] = {}
    for c in cells:
        by_task.setdefault(c["task"], []).append(c)
    greens = [c for c in cells if c["final_passed"]]
    tokens = [c["tokens_out"] for c in greens]
    iters = [c["attempts_to_pass"] for c in greens]
    return {
        "n": n,
        "pass1": sum(bool(c["first_passed"]) for c in cells) / n,
        "pass10_verifier": sum(
            1 for cs in by_task.values() if any(c["final_passed"] for c in cs)
        ) / len(by_task),
        "tokens_to_green_mean": round(sum(tokens) / len(tokens), 1) if tokens else None,
        "iters_to_green_mean": round(sum(iters) / len(iters), 2) if iters else None,
        "censored_sessions": n - len(greens),
    }


def _rates_by_task(cells: list[dict]) -> dict[str, float]:
    by: dict[str, list[bool]] = {}
    for c in cells:
        by.setdefault(c["task"], []).append(bool(c["first_passed"]))
    return {t: sum(v) / len(v) for t, v in by.items()}


def paired_pass1(a_cells: list[dict], b_cells: list[dict]) -> dict:
    ta, tb = _rates_by_task(a_cells), _rates_by_task(b_cells)
    tasks = sorted(set(ta) & set(tb))
    if len(tasks) < 2:
        raise ReportError("paired delta needs >= 2 shared tasks")
    diffs = [ta[t] - tb[t] for t in tasks]
    delta = sum(diffs) / len(diffs)
    var = sum((d - delta) ** 2 for d in diffs) / (len(diffs) - 1)
    se = (var / len(diffs)) ** 0.5
    return {
        "delta_pp": round(delta * 100, 1),
        "two_se_pp": round(2 * se * 100, 1),
        "n_tasks": len(tasks),
    }


def unpaired_pass1(a_cells: list[dict], b_cells: list[dict]) -> dict:
    pa = sum(bool(c["first_passed"]) for c in a_cells) / len(a_cells)
    pb = sum(bool(c["first_passed"]) for c in b_cells) / len(b_cells)
    se = (pa * (1 - pa) / len(a_cells) + pb * (1 - pb) / len(b_cells)) ** 0.5
    return {
        "a": pa,
        "b": pb,
        "delta_pp": round((pa - pb) * 100, 1),
        "two_se_pp": round(2 * se * 100, 1),
    }


def strict_repair_rate(probes_root: Path) -> dict:
    """Reuse eval.probe's committed scoring over the campaign cell dirs."""
    raise NotImplementedError  # replaced in Step 5 after reading probe.py:205+


def require_complete(root: Path) -> None:
    missing = [a for a in ARM_NAMES if not (Path(root) / a / ".DONE").is_file()]
    if missing:
        raise ReportError(
            f"refusing to analyse: arms incomplete: {missing}. "
            f"No endpoint exists until all 12 arms are done."
        )


def build_report(root: Path) -> dict:
    require_complete(root)
    root = Path(root)
    arms = {a: gen_metrics(load_cells(root / a)) for a in ARM_NAMES}
    repair = {a: strict_repair_rate(root / a / "probes") for a in ARM_NAMES}
    primaries = {
        s: {
            "gen": paired_pass1(load_cells(root / f"tune-ox-{s}"),
                                load_cells(root / f"tune-rs-{s}")),
        }
        for s in SIZES
    }
    headline = {
        "gen": unpaired_pass1(load_cells(root / "tune-ox-7"),
                              load_cells(root / "base-rs-14")),
    }
    return {
        "arms": arms,
        "repair": repair,
        "primaries": primaries,
        "headline": headline,
        "window_trend_gen_pp": [primaries[s]["gen"]["delta_pp"] for s in SIZES],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args(argv)
    report = build_report(args.root)
    out = args.root / "ENDPOINTS.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Wire `strict_repair_rate` to the real probe scoring**

Replace the `NotImplementedError` body using the functions found in
Step 1 (the probe module's own cell-scoring entry point over
`probes_root`'s `<arm>-s<seed>/` cell dirs), returning
`{"rate": float, "n": int}`. Add to `build_report`'s `primaries[s]` a
`"repair"` key: `paired-style delta on strict rates is NOT possible
task-paired across languages` — instead compute
`{"tune_ox": rate, "tune_rs": rate, "delta_pp": round((a-b)*100,1)}`
with a 2-SE from the two binomials (same formula as `unpaired_pass1`
over probe outcomes), and a `"repair"` headline
(`tune-ox-7` vs `base-rs-14`). Add a synthetic-fixture test for it in
the same style as `test_unpaired_pass1_hand_computed`, plus — if a
committed probe campaign with published rates exists under
`eval/results/` (the ownership studies' qwen strict 73.0% oxide /
14.0% explicit) — an acceptance pin like the v03 one; if the committed
layout cannot reproduce a published number exactly, STOP and report
rather than approximating.

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_experiment_report.py -v`
Expected: all PASS (including the v03 acceptance pin).

- [ ] **Step 7: Mutation-check** (pyc preamble each run)

1. `require_complete`: drop the raise → refusal test must FAIL.
2. `gen_metrics`: compute `tokens_to_green_mean` over ALL cells →
   censoring tests must FAIL (both the value and the None case).
3. `paired_pass1`: replace `se` with population SD (divide by
   `len(diffs)` instead of `len(diffs)-1` without the /n) → the
   hand-computed test must FAIL. If it doesn't, the fixture is too
   symmetric — extend it until it does.
4. `pass10_verifier`: count `first_passed` instead of `final_passed` →
   `test_gen_metrics_shapes_and_censoring` must FAIL.
5. Acceptance: change `0.305` to `0.306` in the test → must FAIL
   (proves the pin actually reads the committed data). Restore.

- [ ] **Step 8: Commit**

```bash
git add eval/experiment_report.py tests/test_experiment_report.py
git commit -m "feat: experiment analysis — pre-registered endpoints, refusal until 12 arms done"
```

---

### Task 4: Campaign driver

**Files:**
- Create: `eval/exp_campaign.py`
- Modify: `eval/llamacpp.py` (add public `props()` method)
- Create: `tests/test_exp_campaign.py`

**Interfaces:**
- Consumes: `driver.run_session(..., include_lead=...)` (Task 2),
  `probe_campaign.run_campaign(..., include_card=...)` (Task 2),
  `LlamaCppClient`, `models.Generation`, `models.ModelError`.
- Produces:

```python
@dataclass(frozen=True, slots=True)
class ArmSpec:
    name: str            # experiment_report.ARM_NAMES entry
    gguf: str            # served file name, e.g. "tune-ox-7.q8_0.gguf"
    arm: str             # "oxide" | "rust"
    include_lead: bool   # baselines True, tuned False

ARM_SPECS: tuple[ArmSpec, ...]   # exactly 12, names == ARM_NAMES
SEEDS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
TEMPERATURE = 0.2
NUM_CTX = 8192
NUM_PREDICT = 2048
def make_client(spec: ArmSpec, host: str) -> LlamaCppClient
def identity_preflight(client: LlamaCppClient, spec: ArmSpec) -> dict
def run_arm(spec: ArmSpec, *, host: str, results_root: Path,
            tasks_path: Path | None = None,
            seeds: tuple[int, ...] = SEEDS,
            families: tuple[str, ...] = ("gen", "probes")) -> None
def main(argv: list[str] | None = None) -> int
# python -m eval.exp_campaign --arm tune-ox-7 --host http://127.0.0.1:8081 --root eval/results/runpod-exp
```

- `LlamaCppClient.props(self) -> dict` — public wrapper over the
  `/props` call (`self._call(f"{self.host}/props")`).

Behavioral contract for `run_arm` (the spec's rules, in code):
- If `results_root/name/.DONE` exists: return immediately (idempotent).
- Else if `results_root/name` exists WITHOUT `.DONE`: **delete the
  whole arm dir first** (`shutil.rmtree`) — an interrupted arm reruns
  from zero, never resumes (no splicing).
- `identity_preflight` asserts `props()["model_path"]` (or the
  equivalent field the server actually returns — inspect one live
  `/props` payload during Task 6 and pin the field name then; until
  then key on a `model_path`-named lookup with a clear `ModelError` if
  absent) ends with `spec.gguf`, then calls `client.preflight()`
  (n_ctx assertion); its dict lands in `provenance.json`.
- Generation family: for seed in seeds, for task sorted: one
  `run_session(client, run_id=f"{spec.name}-gen-s{seed}",
  task_id=..., arm=spec.arm, shots=0, results_root=arm_dir,
  raw_dir=arm_dir/f"gen-s{seed}"/"raw", seed=seed,
  include_lead=spec.include_lead)`; append the returned cell to
  `arm_dir/f"gen-s{seed}"/"cells.jsonl"` (sort_keys).
- Probe family: `probe_campaign.run_campaign(arm_dir/"probes",
  (spec.arm,), seeds, client_factory=lambda arm: client,
  provenance={... spec fields ...}, include_card=spec.include_lead)`.
- Finally write `arm_dir/".DONE"`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_exp_campaign.py
"""Campaign driver: 12-arm table, card-free plumbing, rerun-from-zero."""
import json
from pathlib import Path

from eval import harness
from eval.exp_campaign import ARM_SPECS, SEEDS, TEMPERATURE, run_arm
from eval.experiment_report import ARM_NAMES
from eval.models import Generation


def test_arm_specs_table():
    assert len(ARM_SPECS) == 12
    assert tuple(s.name for s in ARM_SPECS) == ARM_NAMES
    assert len({s.gguf for s in ARM_SPECS}) == 9  # base ggufs serve 2 arms
    for s in ARM_SPECS:
        if s.name.startswith("tune-"):
            assert s.include_lead is False
        else:
            assert s.include_lead is True
        assert s.arm == ("oxide" if "-ox-" in s.name else "rust")
    assert SEEDS == tuple(range(1, 11))
    assert TEMPERATURE == 0.2


class FakeClient:
    """Answers every prompt with one fixed reply; records the prompts."""

    def __init__(self, reply: str):
        self.reply = reply
        self.prompts: list[str] = []

    def generate(self, prompt: str, *, seed: int) -> Generation:
        self.prompts.append(prompt)
        return Generation(text=self.reply, tokens_in=10, tokens_out=5,
                          ms=1, truncated=False)


def _one_task_file(tmp_path: Path) -> Path:
    task = harness.load_tasks()["t01"]
    p = tmp_path / "tasks.jsonl"
    p.write_text(json.dumps(task) + "\n", encoding="utf-8")
    return p


def _passing_reply() -> str:
    src = Path("eval/solutions/oxide/t01.ox").read_text(encoding="utf-8")
    return f"```\n{src}\n```"


def test_run_arm_cardfree_end_to_end(tmp_path):
    spec = next(s for s in ARM_SPECS if s.name == "tune-ox-7")
    client = FakeClient(_passing_reply())
    tasks_path = _one_task_file(tmp_path)
    run_arm(spec, host="http://unused", results_root=tmp_path / "exp",
            tasks_path=tasks_path, seeds=(1,), families=("gen",),
            client=client)
    arm = tmp_path / "exp" / "tune-ox-7"
    cells = [json.loads(l) for l in
             (arm / "gen-s1" / "cells.jsonl").read_text().splitlines()]
    assert len(cells) == 1 and cells[0]["first_passed"] is True
    assert (arm / ".DONE").is_file()
    card = (harness._REPO_ROOT / harness.CARD_FILES["oxide"]).read_text(
        encoding="utf-8")
    for prompt in client.prompts:
        assert card[:80] not in prompt


def test_run_arm_baseline_prompt_has_card(tmp_path):
    spec = next(s for s in ARM_SPECS if s.name == "base-ox-7")
    client = FakeClient(_passing_reply())
    run_arm(spec, host="http://unused", results_root=tmp_path / "exp",
            tasks_path=_one_task_file(tmp_path), seeds=(1,),
            families=("gen",), client=client)
    card = (harness._REPO_ROOT / harness.CARD_FILES["oxide"]).read_text(
        encoding="utf-8")
    assert card[:80] in client.prompts[0]


def test_run_arm_reruns_from_zero(tmp_path):
    spec = next(s for s in ARM_SPECS if s.name == "tune-ox-7")
    arm = tmp_path / "exp" / "tune-ox-7"
    (arm / "gen-s1").mkdir(parents=True)
    (arm / "gen-s1" / "cells.jsonl").write_text("JUNK\n", encoding="utf-8")
    run_arm(spec, host="http://unused", results_root=tmp_path / "exp",
            tasks_path=_one_task_file(tmp_path), seeds=(1,),
            families=("gen",), client=FakeClient(_passing_reply()))
    cells = (arm / "gen-s1" / "cells.jsonl").read_text(encoding="utf-8")
    assert "JUNK" not in cells  # the junk arm dir was wiped, not resumed


def test_run_arm_done_is_idempotent(tmp_path):
    spec = next(s for s in ARM_SPECS if s.name == "tune-ox-7")
    arm = tmp_path / "exp" / "tune-ox-7"
    arm.mkdir(parents=True)
    (arm / ".DONE").write_text("")
    client = FakeClient(_passing_reply())
    run_arm(spec, host="http://unused", results_root=tmp_path / "exp",
            tasks_path=_one_task_file(tmp_path), seeds=(1,),
            families=("gen",), client=client)
    assert client.prompts == []
```

Note the test-only `client=` parameter: `run_arm` accepts
`client: object | None = None`; when None (production) it builds
`make_client(spec, host)` and runs `identity_preflight`; when given, it
skips the preflight (there is no server). This is the standard
injectable-instrument pattern the house already uses.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_exp_campaign.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'eval.exp_campaign'`

- [ ] **Step 3: Implement `eval/exp_campaign.py` and `LlamaCppClient.props`**

```python
# eval/exp_campaign.py
"""Drive one experiment arm against a llama-server: generation + probes.

The spec's serving rules live here: pinned sampler, unconstrained
decoding, identity preflight before any scored session, rerun-from-zero
for interrupted arms, `.DONE` as the only completion marker.
"""
from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

from eval import harness, probe_campaign
from eval.driver import run_session
from eval.llamacpp import LlamaCppClient
from eval.models import ModelError

SEEDS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
TEMPERATURE = 0.2
TOP_P = 0.95
NUM_CTX = 8192
NUM_PREDICT = 2048


@dataclass(frozen=True, slots=True)
class ArmSpec:
    name: str
    gguf: str
    arm: str
    include_lead: bool


def _specs() -> tuple[ArmSpec, ...]:
    rows: list[ArmSpec] = []
    for kind in ("base", "tune"):
        for lang, arm in (("ox", "oxide"), ("rs", "rust")):
            for size in ("1.5", "7", "14"):
                name = f"{kind}-{lang}-{size}"
                gguf = (f"base-{size}.q8_0.gguf" if kind == "base"
                        else f"{name}.q8_0.gguf")
                rows.append(ArmSpec(name, gguf, arm, kind == "base"))
    order = {n: i for i, n in enumerate((
        "base-ox-1.5", "base-ox-7", "base-ox-14",
        "base-rs-1.5", "base-rs-7", "base-rs-14",
        "tune-ox-1.5", "tune-ox-7", "tune-ox-14",
        "tune-rs-1.5", "tune-rs-7", "tune-rs-14",
    ))}
    return tuple(sorted(rows, key=lambda s: order[s.name]))


ARM_SPECS = _specs()


def make_client(spec: ArmSpec, host: str) -> LlamaCppClient:
    return LlamaCppClient(
        model=spec.gguf, grammar=None, temperature=TEMPERATURE,
        top_p=TOP_P, num_predict=NUM_PREDICT, num_ctx=NUM_CTX, host=host,
    )


def identity_preflight(client: LlamaCppClient, spec: ArmSpec) -> dict:
    props = client.props()
    path = props.get("model_path")
    if not isinstance(path, str) or not path.endswith(spec.gguf):
        raise ModelError(
            f"{spec.name}: server serves {path!r}, expected a path ending "
            f"in {spec.gguf!r} — wrong weights, refusing to measure"
        )
    client.preflight()
    return {"model_path": path}


def run_arm(
    spec: ArmSpec,
    *,
    host: str,
    results_root: Path,
    tasks_path: Path | None = None,
    seeds: tuple[int, ...] = SEEDS,
    families: tuple[str, ...] = ("gen", "probes"),
    client: object | None = None,
) -> None:
    arm_dir = Path(results_root) / spec.name
    if (arm_dir / ".DONE").is_file():
        return
    if arm_dir.exists():
        shutil.rmtree(arm_dir)  # interrupted arm: rerun from zero, never splice
    arm_dir.mkdir(parents=True)
    provenance: dict = {
        **asdict(spec),
        "temperature": TEMPERATURE, "top_p": TOP_P,
        "num_ctx": NUM_CTX, "num_predict": NUM_PREDICT,
        "seeds": list(seeds), "families": list(families),
    }
    if client is None:
        client = make_client(spec, host)
        provenance["identity"] = identity_preflight(client, spec)
    (arm_dir / "provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if "gen" in families:
        tasks = harness.load_tasks(tasks_path)
        for seed in seeds:
            run_dir = arm_dir / f"gen-s{seed}"
            cells_path = run_dir / "cells.jsonl"
            for task_id in sorted(tasks):
                cell = run_session(
                    client, run_id=f"{spec.name}-gen-s{seed}",
                    task_id=task_id, arm=spec.arm, shots=0,
                    results_root=arm_dir, raw_dir=run_dir / "raw",
                    tasks_path=tasks_path, seed=seed,
                    include_lead=spec.include_lead,
                )
                cells_path.parent.mkdir(parents=True, exist_ok=True)
                with open(cells_path, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(cell, sort_keys=True) + "\n")
    if "probes" in families:
        probe_campaign.run_campaign(
            arm_dir / "probes", (spec.arm,), seeds,
            client_factory=lambda arm: client,
            provenance=provenance,
            include_card=spec.include_lead,
        )
    (arm_dir / ".DONE").write_text("")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", required=True,
                        choices=[s.name for s in ARM_SPECS])
    parser.add_argument("--host", default="http://127.0.0.1:8081")
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args(argv)
    spec = next(s for s in ARM_SPECS if s.name == args.arm)
    run_arm(spec, host=args.host, results_root=args.root)
    print(f"{spec.name}: DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

In `eval/llamacpp.py`, add to `LlamaCppClient` (next to `preflight`):

```python
    def props(self) -> dict:
        """The server's /props payload (public: campaign identity checks)."""
        return self._call(f"{self.host}/props")
```

Note the `run_session` call runs the real transpile+rustc oracle per
submission — the fake-client tests genuinely compile t01's reference
solution, which is the point (an end-to-end fake-model, real-oracle
test).

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_exp_campaign.py -v && .venv/bin/pytest -q`
Expected: 5 new PASS; full suite green.

- [ ] **Step 5: Mutation-check** (pyc preamble each run)

1. Flip one tuned spec's `include_lead` to True in `_specs()` →
   `test_arm_specs_table` AND `test_run_arm_cardfree_end_to_end` must
   FAIL.
2. Remove the `shutil.rmtree` → `test_run_arm_reruns_from_zero` must
   FAIL.
3. In `run_session`'s repair-round call (Task 2's known gap), drop
   `include_lead=include_lead` from `build_repair_prompt`: use a
   NON-passing fake reply (`FakeClient("```\nfn main() { broken\n```")`)
   in a temporary scratch test so repair rounds fire, and assert the
   card leaks into `client.prompts[1]` under the mutation and does not
   under the fix. If writing the scratch test as a permanent test is
   cheap, keep it (name: `test_repair_rounds_stay_cardfree`); otherwise
   record its result in the report and delete it. Prefer keeping it.
4. Remove the `.DONE` early-return → `test_run_arm_done_is_idempotent`
   must FAIL.

- [ ] **Step 6: Commit**

```bash
git add eval/exp_campaign.py eval/llamacpp.py tests/test_exp_campaign.py
git commit -m "feat: campaign driver — 12-arm table, identity preflight, rerun-from-zero"
```

---

### Task 5: Pod-side scripts

**Files:**
- Create: `scripts/runpod/train_lora.py`
- Create: `scripts/runpod/merge_lora.py`
- Create: `scripts/runpod/convert_quant.sh`
- Create: `scripts/runpod/pod_setup.sh`
- Create: `scripts/runpod/serve_arm.sh`
- Create: `scripts/runpod/runpod_api.sh`

**Interfaces:**
- Consumes: `harness.build_prompt(..., include_lead=False)` (Task 2 —
  train_lora renders prompts through the SAME function eval uses;
  this is the train==eval invariant, enforced by construction),
  `eval/train/matched/{oxide,rust}.jsonl`, `eval/train/tasks.jsonl`.
- Produces: scripts Task 6–8 procedures invoke verbatim.

These run on the pod (torch 2.9.1, Python 3.12) — locally they are
syntax-checked only. No unit tests beyond that: the executable logic
that CAN run locally already lives in tested modules.

- [ ] **Step 1: Write `scripts/runpod/train_lora.py`**

```python
#!/usr/bin/env python3
"""QLoRA fine-tune on the matched corpus — one recipe for all six runs.

Runs on the pod (torch/cu129). The prompt rendering is
harness.build_prompt(include_lead=False) — the exact string the eval
client sends — with the checkpoint's own chat template applied by the
tokenizer, mirroring llama-server's /v1/chat/completions rendering.
Loss is masked to the completion (the matched supervised tokens).
"""
import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

import torch
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    Trainer,
    TrainingArguments,
)

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from eval import harness  # noqa: E402

SEED = 17
LORA = dict(
    r=16, lora_alpha=32, lora_dropout=0.0, bias="none",
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
)
LR = 1e-4
EPOCHS = 3
MAX_LEN = 1024
TRAIN_TASKS = REPO / "eval" / "train" / "tasks.jsonl"


class Examples(torch.utils.data.Dataset):
    def __init__(self, records, arm, tok):
        self.items = []
        for rec in records:
            user = harness.build_prompt(
                arm, rec["task"], tasks_path=TRAIN_TASKS, include_lead=False
            )
            prompt_ids = tok.apply_chat_template(
                [{"role": "user", "content": user}],
                add_generation_prompt=True, tokenize=True,
            )
            prog_ids = tok(rec["text"], add_special_tokens=False)["input_ids"]
            prog_ids = prog_ids + [tok.eos_token_id]
            ids = (prompt_ids + prog_ids)[:MAX_LEN]
            labels = ([-100] * len(prompt_ids) + prog_ids)[:MAX_LEN]
            self.items.append({"input_ids": ids, "labels": labels})

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        return self.items[i]


def collate(batch, pad_id):
    width = max(len(b["input_ids"]) for b in batch)
    ids, labels, mask = [], [], []
    for b in batch:
        pad = width - len(b["input_ids"])
        ids.append(b["input_ids"] + [pad_id] * pad)
        labels.append(b["labels"] + [-100] * pad)
        mask.append([1] * len(b["input_ids"]) + [0] * pad)
    return {
        "input_ids": torch.tensor(ids),
        "labels": torch.tensor(labels),
        "attention_mask": torch.tensor(mask),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)   # HF id, -Instruct checkpoint
    ap.add_argument("--data", required=True, type=Path)  # matched jsonl
    ap.add_argument("--arm", required=True, choices=["oxide", "rust"])
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    torch.manual_seed(SEED)
    random.seed(SEED)
    tok = AutoTokenizer.from_pretrained(args.base)
    bnb = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        args.base, quantization_config=bnb, device_map="auto",
        torch_dtype=torch.bfloat16,
    )
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, LoraConfig(task_type="CAUSAL_LM", **LORA))

    records = [json.loads(l) for l in
               args.data.read_text(encoding="utf-8").splitlines()]
    ds = Examples(records, args.arm, tok)
    targs = TrainingArguments(
        output_dir=str(args.out), num_train_epochs=EPOCHS,
        learning_rate=LR, lr_scheduler_type="cosine",
        per_device_train_batch_size=4, gradient_accumulation_steps=2,
        bf16=True, logging_steps=10, save_strategy="no",
        seed=SEED, report_to=[],
    )
    Trainer(
        model=model, args=targs, train_dataset=ds,
        data_collator=lambda b: collate(b, tok.pad_token_id or tok.eos_token_id),
    ).train()
    model.save_pretrained(args.out)
    (args.out / "provenance.json").write_text(json.dumps({
        "base": args.base, "arm": args.arm,
        "data": str(args.data),
        "data_sha256": hashlib.sha256(args.data.read_bytes()).hexdigest(),
        "recipe": {"seed": SEED, "lr": LR, "epochs": EPOCHS,
                   "max_len": MAX_LEN, **{k: v for k, v in LORA.items()
                                          if k != "target_modules"},
                   "target_modules": LORA["target_modules"]},
        "n_examples": len(ds),
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"trained {args.arm} on {args.base}: {len(ds)} examples -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Write `scripts/runpod/merge_lora.py`**

```python
#!/usr/bin/env python3
"""Merge a LoRA adapter into its bf16 base and save for GGUF conversion."""
import argparse
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--adapter", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    model = AutoModelForCausalLM.from_pretrained(
        args.base, torch_dtype=torch.bfloat16, device_map="cpu"
    )
    merged = PeftModel.from_pretrained(model, args.adapter).merge_and_unload()
    merged.save_pretrained(args.out, safe_serialization=True)
    AutoTokenizer.from_pretrained(args.base).save_pretrained(args.out)
    print(f"merged -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Write the shell scripts**

`scripts/runpod/pod_setup.sh`:

```bash
#!/usr/bin/env bash
# One-time pod setup: repo, deps, llama.cpp CUDA build. Idempotent.
set -euo pipefail
cd /workspace
if [ ! -d oxide ]; then
  git clone https://github.com/bricelancasterwcp-sudo/black-oxide.git oxide
fi
pip install --break-system-packages -q peft==0.20.0 bitsandbytes accelerate
# rustc is the harness oracle — the eval side of this pod needs it:
if ! command -v rustc >/dev/null; then
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal
  source "$HOME/.cargo/env"
fi
if [ ! -d llama.cpp ]; then
  git clone https://github.com/ggml-org/llama.cpp.git
  cmake -S llama.cpp -B llama.cpp/build -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release
  cmake --build llama.cpp/build -j "$(nproc)" --target llama-server llama-quantize
fi
git -C llama.cpp rev-parse HEAD > /workspace/llamacpp.commit
python -c "import torch; print(torch.__version__, torch.cuda.get_device_name(0))"
echo SETUP-OK
```

`scripts/runpod/convert_quant.sh`:

```bash
#!/usr/bin/env bash
# merged HF dir -> bf16 gguf -> q8_0 gguf, sha recorded.
# usage: convert_quant.sh <merged_dir> <out_name>   (writes /workspace/gguf/<out_name>.q8_0.gguf)
set -euo pipefail
MERGED="$1"; NAME="$2"; OUT=/workspace/gguf
mkdir -p "$OUT"
python /workspace/llama.cpp/convert_hf_to_gguf.py "$MERGED" \
  --outfile "$OUT/$NAME.bf16.gguf" --outtype bf16
/workspace/llama.cpp/build/bin/llama-quantize \
  "$OUT/$NAME.bf16.gguf" "$OUT/$NAME.q8_0.gguf" q8_0
rm "$OUT/$NAME.bf16.gguf"
sha256sum "$OUT/$NAME.q8_0.gguf" | tee -a "$OUT/SHAS.txt"
```

`scripts/runpod/serve_arm.sh`:

```bash
#!/usr/bin/env bash
# Serve one gguf and run one campaign arm; SIGKILL + port-down teardown.
# usage: serve_arm.sh <gguf_path> <arm_name>
set -euo pipefail
GGUF="$1"; ARM="$2"; PORT=8081; ROOT=/workspace/results
cd /workspace/oxide
/workspace/llama.cpp/build/bin/llama-server -m "$GGUF" -c 8192 -ngl 99 \
  --port "$PORT" --host 127.0.0.1 >"/workspace/serve-$ARM.log" 2>&1 &
SERVER=$!
trap 'kill -9 $SERVER 2>/dev/null || true' EXIT
for i in $(seq 1 120); do
  curl -sf "http://127.0.0.1:$PORT/health" >/dev/null && break
  sleep 5
  if [ "$i" = 120 ]; then echo "SERVER-NEVER-HEALTHY" >&2; exit 1; fi
done
python -m eval.exp_campaign --arm "$ARM" --host "http://127.0.0.1:$PORT" --root "$ROOT"
kill -9 $SERVER 2>/dev/null || true
for i in $(seq 1 60); do
  curl -sf "http://127.0.0.1:$PORT/health" >/dev/null || break
  sleep 1
done
echo "ARM-DONE $ARM"
```

`scripts/runpod/runpod_api.sh` (runs LOCALLY; key never echoed):

```bash
#!/usr/bin/env bash
# Minimal RunPod REST wrapper. usage: runpod_api.sh {pods|create|terminate <id>|spend}
set -euo pipefail
KEY="$(cat "$HOME/.config/runpod/api_key")"
API="https://rest.runpod.io/v1"
case "$1" in
  pods)      curl -sf -H "Authorization: Bearer $KEY" "$API/pods" ;;
  terminate) curl -sf -X DELETE -H "Authorization: Bearer $KEY" "$API/pods/$2" ;;
  create)    curl -sf -X POST -H "Authorization: Bearer $KEY" \
               -H "Content-Type: application/json" \
               -d @"$2" "$API/pods" ;;   # $2 = json spec file
  spend)     curl -sf -H "Authorization: Bearer $KEY" "$API/billing" ;;
  *) echo "usage: pods|create <spec.json>|terminate <id>|spend" >&2; exit 2 ;;
esac
```

(If the REST paths differ from the current RunPod API, fix them against
the live API docs during Task 6 — the bloomery spike used REST
`GET /pods` + GraphQL successfully on 2026-08-22; record whatever
endpoint shape actually works back into this script in the same
commit as the dry run's evidence.)

- [ ] **Step 4: Syntax-check everything locally**

Run:
```bash
.venv/bin/python -m py_compile scripts/runpod/train_lora.py scripts/runpod/merge_lora.py
bash -n scripts/runpod/*.sh
chmod +x scripts/runpod/*.sh
```
Expected: silent success. (train_lora imports torch at module top —
`py_compile` only parses, so this works on the torch-less venv.)

- [ ] **Step 5: Commit**

```bash
git add scripts/runpod/
git commit -m "feat: pod-side scripts — QLoRA recipe, merge/convert/quantize, serve wrapper, RunPod API"
git push
```

---

### Task 6: EXECUTION — pod bring-up and dry-run cost gate

This is a procedure, not TDD. STOP conditions are marked. All local
commands run from `~/workspace/oxide`.

- [ ] **Step 1: Preflight locally**

```bash
test -s ~/.config/runpod/api_key && echo KEY-OK
bash scripts/runpod/runpod_api.sh pods
```
Expected: `KEY-OK` and a JSON pod list (expect 0 pods). **STOP and
report BLOCKED if the key file is missing/empty or the API refuses
auth** — do not hunt for other credentials.

- [ ] **Step 2: Create the pod**

Write a spec JSON (adjust to the live API's field names if `create`
rejects it; the bloomery spike's proven parameters: community cloud,
`runpod/pytorch:1.1.0-cu1290-torch291-ubuntu2404` image): GPU type
"NVIDIA GeForce RTX 4090", container disk 80 GB, network volume NOT
required (artifacts rsync home instead — spec-amended below), expose
SSH. Create, then poll `pods` every 30s. **Ops rule (bloomery, paid
for): if `runtime` stays null with no port mapping for more than ~5
minutes, terminate and re-create — it bills while stuck.**

- [ ] **Step 3: Setup + record environment**

`ssh` in (RunPod proxy SSH from the pod list), then:
```bash
mkdir -p /workspace && cd /workspace
# copy the repo's scripts in via the cloned repo itself:
git clone https://github.com/bricelancasterwcp-sudo/black-oxide.git oxide
bash oxide/scripts/runpod/pod_setup.sh
```
Expected: `SETUP-OK`. Record into the session notes: GPU name, driver,
torch version, llama.cpp commit (`cat /workspace/llamacpp.commit`).

- [ ] **Step 4: Convert the 7B base and dry-run one slice**

```bash
cd /workspace
python - <<'EOF'
from huggingface_hub import snapshot_download
snapshot_download("Qwen/Qwen2.5-Coder-7B-Instruct", local_dir="/workspace/hf/base-7")
EOF
bash oxide/scripts/runpod/convert_quant.sh /workspace/hf/base-7 base-7
```
Then run a 2-task × 2-seed × gen-only slice of `base-rs-7`, timed —
create the slice tasks file on the pod:
```bash
cd /workspace/oxide
python - <<'EOF'
import json
from eval import harness
tasks = harness.load_tasks()
with open("/workspace/dry-tasks.jsonl", "w") as fh:
    for tid in ("t01", "t08"):
        fh.write(json.dumps(tasks[tid]) + "\n")
EOF
```
and a driver call (`serve_arm.sh` runs full arms; for the dry slice run
the server by hand, then):
```bash
time python - <<'EOF'
from pathlib import Path
from eval.exp_campaign import ARM_SPECS, run_arm
spec = next(s for s in ARM_SPECS if s.name == "base-rs-7")
run_arm(spec, host="http://127.0.0.1:8081",
        results_root=Path("/workspace/dry"),
        tasks_path=Path("/workspace/dry-tasks.jsonl"),
        seeds=(1, 2), families=("gen",))
EOF
```
Expected: `/workspace/dry/base-rs-7/.DONE` exists; 4 cells written.
**This is also the moment to pin `identity_preflight`'s `/props` field
name** — `curl -s http://127.0.0.1:8081/props | python -m json.tool | head -30`,
confirm which field carries the model path, and if it is not
`model_path`, fix `eval/exp_campaign.py` accordingly (commit the fix
from the local checkout, push, `git -C /workspace/oxide pull`).

- [ ] **Step 5: Extrapolate cost against the stop rule**

Compute, in the session (show the arithmetic in the report):
- `t_session` = wall seconds / 4 sessions from Step 4's `time`.
- Campaign generation sessions: 12 arms × 200 = 2400, scaled by size
  (1.5B ≈ 0.35×, 7B = 1×, 14B ≈ 2× of `t_session`; 4 arms each).
- Probe sessions: 12 × 200, single-attempt ≈ 0.5 × t_session, same
  size scaling.
- Add measured setup+conversion time so far, 6 trainings (bound: 30
  min total), 8 more conversions (bound: measured base-7 conversion
  × 8, 14B ≈ 2×), and 15% slack.
- Dollars = hours × the pod's actual $/h from the pod list.
**STOP RULE:** if projected total spend exceeds $23 minus spend so
far, terminate the pod NOW (whole-arm boundary: nothing measured yet
counts), report the projection, and wait for the 16:30 top-up.
Otherwise proceed directly to Task 7 (same pod).

- [ ] **Step 6: Record the dry run**

Write `docs/superpowers/evidence/2026-08-27-runpod-dryrun.md` locally:
pod id, GPU, $/h, image, llama.cpp commit, the `/props` field decision,
t_session, the full extrapolation table, and the go/pause decision.
Commit + push (evidence only, no code). Also append this dated footnote
to the experiment spec in the same commit (non-silent amendment):

```markdown
> **Amended 2026-08-27 (dry run):** artifacts persist on the pod and
> results rsync home after each tranche; the S3 store (and its fresh
> key) is not used. If the pod must terminate at the budget pause,
> adapters + ggufs are preserved by rsync before teardown or the
> conversions re-run from committed inputs — both paths reproducible.
```

---

### Task 7: EXECUTION — six trainings, nine ggufs, smoke

Same pod, procedure. The Task 1 committed attestation is the
tokenizer gate — it already passed or this plan never got here.

- [ ] **Step 1: Download the remaining bases**

```bash
cd /workspace && python - <<'EOF'
from huggingface_hub import snapshot_download
for size in ("1.5", "14"):
    snapshot_download(f"Qwen/Qwen2.5-Coder-{size}B-Instruct",
                      local_dir=f"/workspace/hf/base-{size}")
EOF
bash oxide/scripts/runpod/convert_quant.sh /workspace/hf/base-1.5 base-1.5
bash oxide/scripts/runpod/convert_quant.sh /workspace/hf/base-14 base-14
```

- [ ] **Step 2: Train six adapters** (OS-detached; sequential)

```bash
cd /workspace
for size in 1.5 7 14; do
  for arm in oxide rust; do
    short=$([ "$arm" = oxide ] && echo ox || echo rs)
    setsid nohup python oxide/scripts/runpod/train_lora.py \
      --base "Qwen/Qwen2.5-Coder-${size}B-Instruct" \
      --data "oxide/eval/train/matched/${arm}.jsonl" \
      --arm "$arm" \
      --out "/workspace/adapters/tune-${short}-${size}" \
      > "/workspace/train-${short}-${size}.log" 2>&1
  done
done
```
Each run is minutes (17k supervised tokens × 3 epochs). After each:
check the log tail shows the final loss line and
`adapters/…/provenance.json` exists. **STOP if any training crashes
twice on the same arm** — report the log tail.

- [ ] **Step 3: Merge + convert + quantize the six tuned models**

```bash
cd /workspace
for size in 1.5 7 14; do
  for short in ox rs; do
    python oxide/scripts/runpod/merge_lora.py \
      --base "Qwen/Qwen2.5-Coder-${size}B-Instruct" \
      --adapter "/workspace/adapters/tune-${short}-${size}" \
      --out "/workspace/merged/tune-${short}-${size}"
    bash oxide/scripts/runpod/convert_quant.sh \
      "/workspace/merged/tune-${short}-${size}" "tune-${short}-${size}"
    rm -rf "/workspace/merged/tune-${short}-${size}"
  done
done
cat /workspace/gguf/SHAS.txt   # 9 lines expected
```

- [ ] **Step 4: Smoke every gguf**

For each of the 9 ggufs: start llama-server, wait healthy, one chat
completion (`curl -s http://127.0.0.1:8081/v1/chat/completions -d
'{"messages":[{"role":"user","content":"Say OK"}],"max_tokens":8}'`),
assert non-empty content, SIGKILL + port-down. **STOP on any gguf that
fails to load or answers empty.**

- [ ] **Step 5: Preserve artifacts + record**

```bash
# from the LOCAL box:
rsync -av --progress "root@<pod-ssh>:/workspace/adapters" ~/workspace/oxide-runpod-artifacts/
rsync -av "root@<pod-ssh>:/workspace/gguf/SHAS.txt" ~/workspace/oxide-runpod-artifacts/
rsync -av "root@<pod-ssh>:/workspace/train-*.log" ~/workspace/oxide-runpod-artifacts/
```
Append the training ledger (per-run final loss, wall time, sha) to the
dry-run evidence file; commit + push.

---

### Task 8: EXECUTION — the 12-arm campaign

Procedure. Order (spec: baselines first, smallest first):
`base-ox-1.5, base-rs-1.5, base-ox-7, base-rs-7, base-ox-14,
base-rs-14, tune-ox-1.5, tune-rs-1.5, tune-ox-7, tune-rs-7,
tune-ox-14, tune-rs-14`.

- [ ] **Step 1: Run arms, one at a time, OS-detached**

For each arm in order (gguf per `ARM_SPECS`: base arms share
`base-<size>.q8_0.gguf`):
```bash
setsid nohup bash /workspace/oxide/scripts/runpod/serve_arm.sh \
  /workspace/gguf/<gguf> <arm-name> > /workspace/arm-<arm-name>.log 2>&1 &
```
Watch for `ARM-DONE`. An arm that dies mid-way is rerun from zero
(the driver wipes it automatically on restart).

- [ ] **Step 2: Sanity tripwires after the 7B baselines** (spec, chosen bounds)

After `base-rs-7` and `base-ox-7` complete:
```bash
cd /workspace/oxide && python - <<'EOF'
from pathlib import Path
from eval.experiment_report import gen_metrics, load_cells
rs = gen_metrics(load_cells(Path("/workspace/results/base-rs-7")))
ox = gen_metrics(load_cells(Path("/workspace/results/base-ox-7")))
print("base-rs-7 pass1", rs["pass1"], "bounds [0.30, 0.80]")
print("base-ox-7 pass1", ox["pass1"], "bounds [0.05, 0.60]")
EOF
```
**STOP the campaign if either lands outside its bounds** — that is an
infrastructure investigation, not a result. (Reading these two numbers
is pre-registered as a sanity check, not an interim analysis; no other
arm's numbers are read before completion.)

- [ ] **Step 3: Budget watch + tranche pause**

After each arm: `bash scripts/runpod/runpod_api.sh spend` (from the
local box) or read the console balance. When remaining budget cannot
cover the NEXT whole arm (use Task 6's per-arm projections):
```bash
# preserve everything, then stop the meter:
rsync -av "root@<pod-ssh>:/workspace/results" ~/workspace/oxide-runpod-artifacts/
rsync -av "root@<pod-ssh>:/workspace/gguf" ~/workspace/oxide-runpod-artifacts/
bash scripts/runpod/runpod_api.sh terminate <pod-id>
bash scripts/runpod/runpod_api.sh pods   # verify 0 pods, check twice
```
Resume after the 16:30 top-up: new pod, `pod_setup.sh`, rsync the
ggufs back up, continue at the next arm. Completed arms' `.DONE` dirs
rsync back up too (the driver's idempotence skips them).

- [ ] **Step 4: Campaign complete**

All 12 arms `.DONE`. Final rsync of `/workspace/results` home,
terminate the pod, verify 0 pods **twice** (REST), record final spend.

---

### Task 9: Analysis, report, push

- [ ] **Step 1: Land the results in the repo**

```bash
mkdir -p eval/results/runpod-exp
rsync -av ~/workspace/oxide-runpod-artifacts/results/ eval/results/runpod-exp/
ls eval/results/runpod-exp/*/.DONE | wc -l   # must print 12
```

- [ ] **Step 2: Compute the endpoints (once)**

```bash
.venv/bin/python -m eval.experiment_report --root eval/results/runpod-exp
```
Expected: `wrote eval/results/runpod-exp/ENDPOINTS.json`. This is the
first time any endpoint exists.

- [ ] **Step 3: Write `eval/results/runpod-exp/REPORT.md`**

Structure (every number from ENDPOINTS.json / provenance files; no
placeholders): environment provenance (pod GPU, image, llama.cpp
commit, gguf shas, sampler); the 12-arm table (pass@1,
pass@10-with-verifier, strict repair, iterations-to-green,
tokens-to-green with censored counts); the three pre-registered
readings — per-size primaries with 2-SE, the headline
(tune-ox-7 vs base-rs-14, generation AND repair), the window trend;
token-efficiency ratios; sanity-bound readouts; total spend vs the
$23 + top-up budget; and the decision-mapping paragraph quoting the
spec's mapping and stating which branch the numbers land in — stated
as the mapping's output, no fresh interpretation.

- [ ] **Step 4: Full suite + commit + push**

```bash
export PYTHONDONTWRITEBYTECODE=1
find . -name __pycache__ -type d -prune -exec rm -rf {} +
.venv/bin/pytest -q     # expect 0 failures
git add eval/results/runpod-exp docs/superpowers/evidence/
git commit -m "feat: RunPod fine-tune experiment — 12 arms measured, pre-registered endpoints computed"
git push
```
The findings write-up (public doc in the findings series) is a
separate, owner-reviewed cycle — out of scope here.

---

## Self-Review Notes (for the executor)

- Spec coverage: matrix (T4), training+attestation (T1, T5, T7),
  serving+identity (T4, T5), evaluation protocol (existing
  `run_session`/`probe_campaign` + T2 card-free), endpoints+refusal
  (T3), budget/phasing (T6, T8), decision mapping (T9 report). The
  spec's `eval/repair_loop.py` row is superseded by the Task 2 spec
  amendment (the harness already implements the loop).
- The `/props` model-path field name and the RunPod REST endpoint
  shapes are pinned during Task 6 against the live systems, by design
  — both are recorded in the dry-run evidence file when pinned.
- `probe_campaign.run_campaign(provenance=...)` is REQUIRED by that
  module — the campaign driver always passes it (Task 4 does).
- Known review flag: Task 4's fake-client tests execute the real
  rustc oracle — each test costs a transpile+compile (~seconds). If
  the suite time grows unacceptably, mark them `slow`, do not stub
  the oracle.
