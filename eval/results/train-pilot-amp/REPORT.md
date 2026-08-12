# Data-factory pilot — 40 tasks, and why passing every endpoint was not enough

**Date:** 2026-08-12
**Code state:** `finetune-data-factory` at the commit adding this file.
**Design:** the 40-task training corpus (`eval/train/tasks.jsonl`, ids
`n001`–`n040`) run through the constrained grid at K=30 — 3 families × 10
seeds × 40 tasks × 3 arms = **3,600 sessions**, prefixes `ampq`/`ampc`/
`ampg`. Wall clock 14h 26m, 19:11:17 (08-11) to 09:37:08 (08-12), no
stalls and no aborted cells.
**Spec:** `docs/superpowers/specs/2026-08-11-finetune-data-factory-design.md`

## The result in one line

**All four pre-registered endpoints are CONFIRMED, and the corpus should
not be scaled to 400 tasks as authored.** The endpoints could not have
told you that — the defect they miss is the subject of this report.

## Endpoint scorecard

| # | endpoint | threshold | measured | verdict |
|---|---|---|---|---|
| 1 | reference-pair yield | ≥ 90% | **40/40 = 100%** | CONFIRMED |
| 2 | amplification yield, unique oxide/task | mean ≥ 4.0 | **6.95** | CONFIRMED |
| 3 | zero-yield tasks | ≤ 30% | **5.0%** (2/40) | CONFIRMED |
| 4 | difficulty band, oxide first-pass | see below | all 3 inside | CONFIRMED |

Endpoint 4 detail:

| family | band | measured | |
|---|---|---|---|
| qwen | 20.5 – 40.5 | **35.8%** | inside |
| codegemma | 6.5 – 26.5 | **24.5%** | inside |
| granite | 0 – 19.5 | **15.5%** | inside |

Yield comfortably beats `v03c`'s own K=30 figures (mean 5.7, zeros 20%),
and the rust arm yields more still (mean 9.62, zeros 7.5%), which is the
comfortable direction: token matching will need to discard rust programs,
not find more.

Completeness was verified at the corpus-derived run length — 120 cells
per run, not the pinned 60 — with zero missing or short runs in all three
families. Contamination guard over the **amplified** corpus: 663 programs
scanned, **0 findings**.

## The v0.3-comparable rate table

n = 400 per arm per family (40 tasks × 10 seeds):

| family | arm | first-compile | first-pass | final-pass |
|---|---|---|---|---|
| qwen | oxide | 49.0% | 35.8% | 41.8% |
| qwen | explicit | 20.5% | 17.0% | 29.2% |
| qwen | rust | 95.8% | 56.8% | 60.8% |
| codegemma | oxide | 36.2% | 24.5% | 27.5% |
| codegemma | explicit | 22.2% | 13.5% | 16.5% |
| codegemma | rust | 89.5% | 34.5% | 40.0% |
| granite | oxide | 48.0% | 15.5% | 17.2% |
| granite | explicit | 28.7% | 8.2% | 10.5% |
| granite | rust | 85.2% | 47.0% | 53.0% |

## The finding: the corpus is systematically easier for Black Oxide

### Consistent across all three families, on first-compile

Oxide first-compile against each family's `v03c` figure:

| family | `v03c` | new corpus | Δ |
|---|---|---|---|
| qwen | 36.0% | 49.0% | **+13.0** |
| codegemma | 23.5% | 36.2% | **+12.7** |
| granite | 33.0% | 48.0% | **+15.0** |

Three independent families, same direction, spread of 2.3pp. Rust over
the same comparison moves −2.2 / +5.0 / +5.2 — no consistent direction.
This is the evidentiary form this project treats as real (it is what
carried §53 and §55) and it is pointing at a defect in my own corpus.

### It is concentrated in the vector and string classes

Oxide first-pass by task class, eval corpus → new corpus:

| class | qwen | codegemma | granite |
|---|---|---|---|
| arithmetic/loops | 44.3 → 45.0 (+0.7) | 31.4 → 35.0 (+3.6) | 12.9 → 12.0 (−0.9) |
| **vectors** | 5.0 → 27.0 (**+22.0**) | 10.0 → 22.0 (**+12.0**) | 2.5 → 5.0 (+2.5) |
| **strings** | 7.5 → 29.0 (**+21.5**) | 0.0 → 24.0 (**+24.0**) | 0.0 → 14.0 (**+14.0**) |
| structs/Option | 50.0 → 42.0 (−8.0) | 14.0 → 17.0 (+3.0) | 18.0 → 31.0 (+13.0) |

Arithmetic is matched to within ±3.6pp in every family — the authoring
was not uniformly easy. Vectors and strings are where it drifted, in all
three families.

### The mechanism, and it is not subtle

The eval's t08–t15 ask for things Black Oxide has **no builtin for**:
sort by hand (t11), reverse by hand (t09, t12), multi-part output (t08
prints a count *and* a maximum; t14), multi-input iteration (t13 checks
three texts, t15 parses three strings), and aggregate Option handling
(t15 sums only what parses).

My n011–n030 ask for sum, max, min, count, average, and letter tallies.
Not one requires implementing an algorithm the language does not supply.
The single crispest measure:

| | multi-line output | mean output lines | mean prompt words |
|---|---|---|---|
| eval t01–t20 | **65%** (13/20) | 2.30 | 25.2 |
| train n001–n040 | **5%** (2/40) | 1.12 | 18.2 |

A 13× difference in multi-output share. **I authored around the
language's weak spots without noticing**, which is exactly how a corpus
comes to flatter the language it is meant to train.

### Why this matters for the fine-tune

A token-matched LoRA trained on this distribution learns from tasks that
are ~13pp easier for Black Oxide at the compile stage than the eval's
are, while Rust is unchanged. The resulting Black-Oxide-vs-Rust
comparison would carry a corpus-induced advantage that has nothing to do
with the language, and the eval would not reveal it — the eval is held
out and *harder*, so the fine-tune would simply underperform its training
distribution in a way that looks like ordinary generalisation.

## The methodological finding, which is the pilot's real product

**Every one of these signatures was computable in seconds, with no GPU.**
Multi-line-output share, mean output lines, and prompt length are
statistics over two `tasks.jsonl` files. The difficulty check as I
designed it was post-hoc — author 40 tasks, spend 14 hours of GPU,
compare pass rates — when a structural comparison would have caught the
drift before a token was generated.

The design should gain a **pre-flight corpus-shape gate**: compare
multi-line-output share, mean output lines, prompt length, and per-class
task counts against the eval corpus, and fail authoring before the GPU is
touched. The 3,600-session run stays as confirmation; it stops being the
first line of defence.

**The deeper lesson is about the endpoints themselves.** All four passed.
They were falsifiable — that was checked before the run, and it was the
right check — but falsifiable is not the same as sufficient. Every
endpoint asked "did the factory produce enough usable programs?" and none
asked "are these the right programs?". A pre-registration can be honest,
specific, and complete on its own terms while still measuring the wrong
thing, and passing it can license exactly the mistake it was written to
prevent.

## v0.4 deferred-ledger demand

Over 1,200 oxide-arm first attempts, counting **distinct programs**:

| ledger item | occurrences | programs | share |
|---|---|---|---|
| `2.to(n)` numeric range method | 35 | 27 | 2.2% |
| `unwrap_or` | 15 | 7 | 0.6% |
| `if let` | 0 | 0 | 0.0% |
| `.set(i, v)` | 0 | 0 | 0.0% |
| type-based overloading | — | — | **not counted, by design** |

Overloading has no surface form to match — a program wanting it calls an
existing name with the wrong argument type and fails in the type checker
like any other error — so a count would be an invented signal.

`if let` and `.set` reading exactly zero is itself a consequence of the
drift above: these tasks never ask for indexing or pattern-matched
binding, so they cannot elicit demand for either. **These two zeros are
not evidence of absent demand** and must not be cited as such; the
corpus that would test them has not been authored yet. The `2.to(n)`
figure at 2.2% is the only ledger number here worth carrying forward, and
it is consistent with g3's finding that `to_int` was range sugar wearing
a conversion's name.

## What this does not show

- **Nothing about whether a fine-tune helps.** No training was run. That
  is specs 2–4 of this track.
- **The four endpoints are confirmed on their own terms** and are not
  retroactively downgraded. They measured what they said they measured.
  The corpus defect is an *additional* finding they did not cover.
- **The rust arm was never banded.** I specified a difficulty band on the
  oxide arm only. codegemma's rust first-pass moved −10.5pp on the new
  corpus, larger than its oxide move, and no endpoint would have caught
  it. Stated because it was my omission, not because the data hid it.
- **Single authoring source.** 40 tasks from one author in four batches;
  batching reduces near-duplicate prompts but does not make the corpus
  multi-author, and nothing here claims it does.
- **granite carries its 4096-window covariate** throughout, as in every
  campaign since G0.
- **The +13pp first-compile gap is measured against `v03c`**, which is
  itself one shot condition on one 20-task corpus. It is a comparison
  between two small corpora, not against a population of tasks.

## Recommendation

**Do not scale to 400 tasks as authored.** Before the next authoring
round:

1. Add the pre-flight corpus-shape gate and require the new tasks to
   match the eval's structural profile — multi-line-output share near
   65%, mean output lines near 2.3.
2. Author the vector and string classes against t08–t15's *demands*:
   sorting, reversing, indexing, in-place mutation, multi-pass string
   work, and aggregate Option handling.
3. Band the **rust** arm as well as the oxide arm, and add a per-class
   band rather than a whole-corpus one — the whole-corpus band passed in
   all three families while two classes drifted more than 20pp.
4. Re-run the 40 existing tasks through the shape gate; those that fail
   it are re-authorable without discarding their verified pairs.

The 663 verified programs already collected remain valid training data
for the classes that did not drift, and the harness, guard, gate, and
collector all work end to end.

## Provenance

Families, tags and blob digests are the G0/`v03c` ladder unchanged:
`qwen2.5-coder:7b-instruct-q8_0` (`sha256:24b532e5…`),
`codegemma:7b-instruct-q8_0` (`sha256:20b20ee7…`),
`granite-code:8b-instruct-q8_0` (`sha256:7f84501f…`), resolved from
ollama's store and asserted per run via `--expect-model-path`. Backend
llama.cpp Vulkan `~/llama.cpp/build-vk/bin/llama-server`, `-ngl 99`,
`num_ctx` 8192/8192/**4096**, temperature 0.8, top_p 0.95, shots 0, seeds
1–10, constrained on oxide and explicit, never on rust.

```bash
# rates and completeness (note --tasks: runs are 120 cells, not 60)
.venv/bin/python -m eval.g0_report --root eval/results/train-pilot-amp \
  --models qwen7b --seeds 1-10 --run-prefix ampq \
  --tasks eval/train/tasks.jsonl        # and ampc/codegemma7b, ampg/granite8b

# yield endpoints
.venv/bin/python -c "from eval import train_corpus as tc; \
  print(tc.collect_verified('eval/results/train-pilot-amp'))"

# contamination guard
.venv/bin/pytest tests/test_train_corpus.py -q

# ledger demand
.venv/bin/python -c "from eval import demand; print(demand.LEDGER_KEYS)"
```

Raw: 30 run dirs (`amp{q,c,g}-<slug>-0shot-s1…s10`), each with
`cells.jsonl` + `triples.jsonl` + `manifest.json` + `raw/`.
