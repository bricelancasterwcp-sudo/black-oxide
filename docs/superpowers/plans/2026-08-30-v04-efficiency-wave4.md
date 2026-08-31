# v0.4 Efficiency Cycle, Wave 4 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Test whether familiarity drives construct uptake, by re-spelling the predicate literal to Rust's `|x|` at constant corpus exposure, and find out whether wave 3's findings are a 7B artifact by adding a 14B quartet.

**Architecture:** A lexer token plus a parser change re-spell `x -> expr` as `|x| expr` with all semantics unchanged; `filter` ships beside `count_if` so efficiency and learnability point at different constructs and the model picks; a learnability estimand (uptake ÷ exposure) lands as tested code; the campaign grows from four arms to eight.

**Tech Stack:** Python 3.14 (stdlib + `tokenizers`), pytest, rustc as oracle, llama.cpp on a rented RunPod GPU.

**Spec:** `docs/superpowers/specs/2026-08-30-v04-efficiency-wave4-design.md`

## Global Constraints

- Branch: `v04-efficiency-wave4` (created off `main` @ `ec34528c`).
- Venv for everything: `.venv/bin/python -m pytest`.
- **pyc discipline:** `PYTHONDONTWRITEBYTECODE=1` and purge `__pycache__` before EVERY run, mutated and restored alike.
- **Commit messages via `git commit -F <file>`** with a quoted heredoc. Never `-m "…"` with backticks — that mangled `79e8b42c`.
- **Protected, read-only:** `eval/tasks.jsonl`, `eval/solutions/`, `eval/train/tasks.jsonl`, `eval/train/pairs/*/rust.rs`, `eval/probes.jsonl`, and every committed `eval/results/*` except the new dirs this plan creates.
- **The 40-pair reference corpus stays frozen.** No new tasks — spec §2: adding them breaks comparability with waves 1–3.
- **Identical-stdout law:** every re-authored oxide reference byte-identical stdout, `validate_pair` green on all 40, contamination 0.
- Suite baseline entering the wave: **1666 passed, 3 deselected**.
- Static baseline: overall 2300/2332 = **0.9863**; vectors 555/573 = 0.969; strings 613/578; structs 623/677; arithmetic 509/504.
- **Hard spend cap $3.00** against a $6.95 balance.

---

## File Structure

| File | Responsibility |
|---|---|
| `src/lexer/tokens.py`, `src/lexer/lexer.py` | New `PIPE` token for a bare `\|`. `\|\|` still lexes as `OROR` (two-char-first, SPEC §3.6). |
| `src/parser/expressions.py` | `\|x\| expr` parses to the existing `PredLit` node; the `->` form is removed. |
| `src/parser/ast.py` | `PredLit` docstring updated; node shape unchanged. |
| `src/sema/types.py` | `filter` signature: `(Vec<A>, Pred<A>) -> Vec<A>`. |
| `src/codegen/support.py` | `filter` prelude fn + `BUILTIN_REF` entry. |
| `eval/learnability.py` (new) | Uptake ÷ exposure, the §62.1 estimand, as tested code. |
| `tests/test_v04_wave4.py` (new) | Re-spelling and `filter` behaviour. |
| `tests/test_learnability.py` (new) | The estimand's arithmetic and its None-vs-zero discipline. |
| `SPEC.md` | §63: the re-spelling, `filter`, the learnability estimand, the reversal of wave 3's ruling. |
| `LANGUAGE_CARD*.md` | Card v0.7. |
| `eval/results/v04-cost-census/` | Regenerated after re-authoring. |
| `eval/results/v04-campaign4/`, `eval/results/v04-amp5/` | Wave-4 artifacts. |

---

## Task 1: Re-spell the predicate literal to `|x|`

**Files:** Modify `src/lexer/tokens.py`, `src/lexer/lexer.py`, `src/parser/expressions.py`, `src/parser/ast.py`; Create `tests/test_v04_wave4.py`

**Interfaces:**
- Consumes: `PredLit(node_id, span, param, body)` from `src/parser/ast.py` — unchanged; only its surface syntax moves.
- Produces: `|x| expr` parses to the same `PredLit`; `x -> expr` no longer parses as a predicate.

- [ ] **Step 1: Write the failing tests** in `tests/test_v04_wave4.py`, mirroring `tests/test_v04_predicate.py`'s helpers (`codes`, `run_oxide`, `requires_rustc`):

```python
@requires_rustc
def test_bar_predicate_counts_matching_elements(tmp_path):
    src = """fn main() {
    let v = vec(5, 12, 3, 18, 9)
    print(count_if(v, |x| x < 10))
}
"""
    assert run_oxide(src, tmp_path) == "3\n"


def test_bar_predicate_still_cannot_capture():
    src = """fn main() {
    let v = vec(1, 2, 3)
    let t = 2
    print(count_if(v, |x| x < t))
}
"""
    assert "OX0205" in codes(src)


def test_boolean_or_still_lexes_as_oror():
    """`||` must keep winning over a bare `|` (two-char-first, SPEC 3.6),
    or every disjunction in the corpus becomes a predicate literal."""
    src = """fn main() {
    let a = true
    let b = false
    if a || b {
        print(1)
    }
}
"""
    assert codes(src) == []


def test_arrow_form_is_gone():
    src = """fn main() {
    let v = vec(1, 2, 3)
    print(count_if(v, x -> x < 2))
}
"""
    assert codes(src) != []
```

- [ ] **Step 2: Run to verify failure.** `PYTHONDONTWRITEBYTECODE=1`, purge `__pycache__`, `.venv/bin/python -m pytest tests/test_v04_wave4.py -q`. Expect failures on the bar forms.

- [ ] **Step 3: Add the `PIPE` token.** In `src/lexer/tokens.py` add `PIPE = auto()  # |` beside `OROR`. In `src/lexer/lexer.py` add `"|": TokenKind.PIPE` to the single-char table; the two-char table already maps `"||"` first, which the existing two-char-first rule preserves.

- [ ] **Step 4: Move the parser.** In `src/parser/expressions.py::_nud`, delete the `IDENT` + `ARROW` branch and add, beside the other prefix forms:

```python
        if kind is TokenKind.PIPE:
            return self._pred_lit()
```

Rewrite `_pred_lit` to consume `PIPE IDENT PIPE` then parse the body at binding power 0:

```python
    def _pred_lit(self) -> Expr:
        """`|x| expr` (SPEC 63.1). Re-spelled from wave 3's `x -> expr`
        on measured evidence: at equal corpus exposure the tuned model
        chose the bar form over the arrow about 10:1. Semantics are
        unchanged -- still no captures, still `Pred<T>`."""
        bar = self._advance()  # |
        param = self._expect(TokenKind.IDENT, "predicate parameter")
        self._expect(TokenKind.PIPE, "'|' closing the predicate parameter")
        body = self._parse_expr(0)
        span = Span(bar.span.start, body.span.end)
        return PredLit(self._new_id(), span, param.lexeme, body)
```

- [ ] **Step 5: Run tests and the full suite.** Expect the wave-4 tests green and `tests/test_v04_predicate.py` to fail on its arrow sources — update those sources to the bar form in the same commit (the tests' *behaviour* is unchanged, only the surface syntax).

- [ ] **Step 6: Mutation-check the two-char-first rule.** Remove `"||"` from the two-char table so `a || b` would lex as two `PIPE`s; `test_boolean_or_still_lexes_as_oror` must FAIL. Restore, purge, confirm green. This is the one change that could silently corrupt every disjunction in the corpus.

- [ ] **Step 7: Commit** with `git commit -F` and a quoted heredoc.

---

## Task 2: `filter(v, |x| ...) -> Vec<T>`

**Files:** Modify `src/sema/types.py`, `src/codegen/support.py`, `src/parser/expressions.py` (`BUILTIN_METHOD_NAMES`); extend `tests/test_v04_wave4.py`

**Interfaces:**
- Consumes: `TCon("Pred", (_A,))` from Task 1's unchanged `PredLit` typing.
- Produces: `filter(v, p) -> Vec<T>`, reading its vector like `count_if`.

- [ ] **Step 1: Write failing tests:**

```python
@requires_rustc
def test_filter_keeps_matching_elements(tmp_path):
    src = """fn main() {
    let v = vec(5, 12, 3, 18, 9)
    for x in filter(v, |x| x < 10) {
        print(x)
    }
}
"""
    assert run_oxide(src, tmp_path) == "5\n3\n9\n"


@requires_rustc
def test_len_of_filter_equals_count_if(tmp_path):
    """The §62 experiment's two spellings must agree numerically."""
    src = """fn main() {
    let v = vec(5, 12, 3, 18, 9)
    print(len(filter(v, |x| x < 10)))
    print(count_if(v, |x| x < 10))
}
"""
    assert run_oxide(src, tmp_path) == "3\n3\n"


def test_filter_is_in_all_three_seams():
    from src.parser.expressions import BUILTIN_METHOD_NAMES
    from src.codegen.support import BUILTIN_REF
    from src.sema.types import BUILTINS
    assert "filter" in BUILTINS and "filter" in BUILTIN_REF
    assert "filter" in BUILTIN_METHOD_NAMES
```

- [ ] **Step 2: Run to verify failure.**

- [ ] **Step 3: Add the signature** in `src/sema/types.py`, after `count_if`:

```python
    # filter(v, pred) -> Vec<T>: the elements satisfying the predicate.
    # Reads its vector (like count_if) and returns a fresh one, so the
    # source stays usable -- `len(filter(v, p))` and a later `len(v)` are
    # both legal. Ships ALONGSIDE count_if deliberately (SPEC 63.2): the
    # two spell the same intent at different token costs and different
    # familiarity, and the wave measures which the model reaches for.
    "filter": BuiltinSig(
        params=(TCon("Vec", (_A,)), TCon("Pred", (_A,))),
        ret=TCon("Vec", (_A,)),
        modes=("read", "read"),
        generics=(_A,),
    ),
```

- [ ] **Step 4: Add the prelude fn and ref tuple** in `src/codegen/support.py`. Verify with rustc BEFORE writing it in (the wave-2 lesson):

```python
    (
        "filter",
        "fn filter<T: Clone>(v: &Vec<T>, p: impl Fn(&T) -> bool) -> Vec<T> {\n"
        "    v.iter().filter(|e| p(e)).cloned().collect()\n"
        "}",
    ),
```

and `"filter": (True, False),` in `BUILTIN_REF`. Add `"filter"` to `BUILTIN_METHOD_NAMES` (alphabetical; `tests/test_parser.py:551` asserts set equality with `BUILTINS`).

- [ ] **Step 5: Update the independent prelude pin** in `tests/test_codegen.py` — it deliberately does not import `PRELUDE`, so adding a prelude fn must be a visible edit.

- [ ] **Step 6: Run the full suite.** Expect 1666 + new tests.

- [ ] **Step 7: Commit.**

---

## Task 3: The learnability estimand

**Files:** Create `eval/learnability.py`, `tests/test_learnability.py`

**Interfaces:**
- Consumes: G2 uptake counts (per construct, per arm) and corpus-exposure fractions (share of training examples containing the construct) — both plain dicts supplied by the caller, so the module has no I/O and is trivially testable.
- Produces: `learnability(uptake, exposure) -> dict` with `ratio`, `uptake`, `exposure` per construct; `rank(rows)`.

- [ ] **Step 1: Write failing tests:**

```python
from eval.learnability import learnability, rank


def test_ratio_is_uptake_over_exposure():
    rows = learnability({"reverse": 50}, {"reverse": 0.017})
    assert round(rows["reverse"]["ratio"], 1) == round(50 / 0.017, 1)


def test_zero_exposure_is_none_not_infinity():
    """A construct the corpus never taught has NO learnability reading --
    it is unmeasured, not infinitely learnable and not zero."""
    rows = learnability({"swap": 0}, {"swap": 0.0})
    assert rows["swap"]["ratio"] is None


def test_zero_uptake_at_real_exposure_is_a_measured_zero():
    rows = learnability({"count_if": 0}, {"count_if": 0.024})
    assert rows["count_if"]["ratio"] == 0.0


def test_both_terms_are_carried_so_a_ratio_is_never_read_alone():
    rows = learnability({"swap": 0}, {"swap": 0.007})
    assert rows["swap"]["uptake"] == 0 and rows["swap"]["exposure"] == 0.007


def test_rank_orders_most_learnable_first_and_puts_unmeasured_last():
    rows = learnability({"a": 50, "b": 10, "c": 0}, {"a": 0.02, "b": 0.02, "c": 0.0})
    assert [r[0] for r in rank(rows)] == ["a", "b", "c"]


def test_wave3_acceptance():
    """Pins the §6.1 table: reverse outlearns count_if despite lower
    exposure -- the observation the estimand exists to express."""
    uptake = {"reverse": 50, "count_if": 0, "+=": 194}
    exposure = {"reverse": 0.017, "count_if": 0.024, "+=": 0.241}
    rows = learnability(uptake, exposure)
    assert rows["reverse"]["ratio"] > rows["count_if"]["ratio"]
    assert rows["reverse"]["ratio"] > rows["+="]["ratio"]
```

- [ ] **Step 2: Run to verify failure** (`ModuleNotFoundError`).

- [ ] **Step 3: Implement `eval/learnability.py`.** Ratio is `uptake / exposure`; exposure of 0 yields `ratio: None` and the construct is named in an `unmeasured` list; both terms are always carried in the row. `rank` sorts by ratio descending with `None` last, ties broken on name.

- [ ] **Step 4: Run tests; then mutation-check three behaviours** — (a) `None` on zero exposure changed to `0.0` must fail `test_zero_exposure_is_none_not_infinity`; (b) dropping `uptake`/`exposure` from the row must fail the carry test; (c) `rank` sorting ascending must fail the ordering test. Restore and confirm green after each.

- [ ] **Step 5: Commit.**

---

## Task 4: SPEC §63 and card v0.7

- [ ] **Step 1: Append SPEC §63** with: **63.1** the re-spelling, stating plainly that it reverses wave 3's ruling on measured evidence and that the ~2-token static cost is deliberately spent to buy learnability (§62's first explicit trade between objectives); **63.2** `filter` beside `count_if` as the efficiency-vs-learnability experiment; **63.3** the learnability estimand promoted from §62.1 into a measured instrument; **63.4** stale-text sweep — grep `SPEC.md` and both cards for `->`-spelled predicates and amend every hit in place, old text struck through, never deleted (§61.1 is the main site).

- [ ] **Step 2: Update both cards** to the bar spelling and add `filter`. Core card headroom is 42 words (limit 1150 after §61.3); if it crosses, raise `CORE_WORD_LIMIT` **non-silently** per §60.5's standing instruction and re-verify the pin bites.

- [ ] **Step 3: Run `tests/test_cards.py` and the full suite. Commit.**

---

## Task 5: Re-author references and read the static endpoints

- [ ] **Step 1:** Re-spell the two predicate sites — `eval/train/pairs/n046/oxide.ox` and `n065/oxide.ox` — from `x -> …` to `|x| …`. No other change.

- [ ] **Step 2:** Sweep all 40 pairs for any `filter`-admissible substitution under the amended bias rule (each arm written as well as its own language allows). Record the negatives too: a missed substitution is a defect, not caution.

- [ ] **Step 3: Oracle.** `validate_pair` green on all 40, stdout byte-identical, `git diff --exit-code eval/train/pairs/*/rust.rs` empty.

- [ ] **Step 4: Rebuild and read.** `python -m eval.token_match`, `python -m eval.cost_census`. Record every class against target: overall ≤ 0.99, vectors ≤ 1.00, others hold. **Report each as HIT or MISS; a miss is a miss.** Update the cost-census acceptance pin in the same commit, carrying the prior figures in the docstring.

- [ ] **Step 5: Full suite. Commit.**

---

## Task 6: Dynamic loop, eight arms (controller, inline)

1. Boot a community RTX 3090 at $0.22/h; **verify `torch.cuda` before committing hours**; pin `allowedCudaVersions`. Liveness is tested by SSH, never by the `runtime` field (wave-3 runbook correction).
2. **Verify 14B QLoRA fits 24 GB before the long legs run.** If it OOMs: do NOT move to a 48 GB card — drop to the 7B quartet, report the 14B arms as not-run with the reason, and tell the owner.
3. Setup, downloads, base converts for 1.5B / 7B / 14B.
4. Amplify at card v0.7, 3 sizes × 20 seeds, temperature 0.8 (corpus generation only).
5. Fresh-first rematch with the ≥15k gate and the stale-verdict re-validation, both as in wave 3.
6. Retrain symmetrically at **7B and 14B** — four adapters.
7. Campaign, eight arms: `base-{ox,rs}-7`, `tune-{ox,rs}-7`, `base-{ox,rs}-14`, `tune-{ox,rs}-14`.
8. Read G1, G2, learnability (§62.1 ratio, both terms shown), and the composition-controlled ratio via `paired_tokens_to_green`.
9. **Count-verified rsync home including all four adapters**; terminate; verify zero pods twice; record spend against the $3.00 cap.

---

## Task 7: Report and close (controller, inline)

- [ ] Land `eval/results/v04-campaign4/` and `eval/results/v04-amp5/`.
- [ ] Write `eval/results/v04-campaign4/REPORT.md`: what shipped and why; static table with HIT/MISS; the corpus gate; the 8-arm dynamic table; G1; **the wave's central test — `|x|` uptake against wave 3's arrow at equal exposure, stated as confirmed or falsified**; the `filter`-vs-`count_if` result; the 14B block as its own section with no cross-size claim pre-registered; learnability ratios with both terms; spend; feed-forward.
- [ ] Full suite green; commit; push; verify `origin` in sync; update memory; close the ledger.

## Self-Review

**Spec coverage.** §3.1 re-spelling → Task 1. §3.2 `filter` → Task 2. §3.3 14B quartet → Task 6. §4 learnability estimand → Task 3, read in Task 6, reported in Task 7. §4 static/dynamic/G1/corpus-gate → Tasks 5 and 6. §5 budget and the four stops → Task 6. §6 out-of-scope items appear in no task. No gaps.

**Placeholder scan.** The `filter` prelude text is given verbatim but carries an explicit instruction to rustc-verify before it is written in — the wave-2 lesson that implementers transcribe plan code faithfully, bugs included. No TBDs.

**Type consistency.** `PredLit(node_id, span, param, body)` is unchanged from wave 3 and constructed identically in Task 1. `filter` and `count_if` share the `(Vec<A>, Pred<A>)` parameter shape, differing only in return type, so Task 2's signature cannot drift from Task 1's typing. `learnability(uptake, exposure)` returns rows keyed by construct with `ratio`/`uptake`/`exposure` in both the tests and the implementation.
