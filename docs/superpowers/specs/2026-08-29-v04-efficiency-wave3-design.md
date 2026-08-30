# v0.4 — the efficiency cycle, wave 3 (cost census + the vectors gap)

**Date:** 2026-08-29
**Purpose:** third turn of the efficiency design loop. The binding
purpose statement and the no-verdict discipline of the wave-1 spec carry
over unchanged: Black Oxide is a design project whose objective is
tokens per solved task, and measurement exists to feed the next design
decision, never to close the project. Input = the committed wave-2
feed-forward (`eval/results/v04-campaign2/REPORT.md`).
**Branch:** new branch off `main` (waves 1–2 merged 2026-08-29 at
`a9cabe51`).
**Status:** scoped and approved by the owner 2026-08-29, including the
§4 bias-rule amendment, with a **standing authorization to execute**
when community GPU capacity appears (§9).

## 1. Baseline (wave-2 close, the committed anchor)

Static reference ratios, pinned Qwen2.5-Coder tokenizer, 40 pairs:

| class | oxide | rust | ratio | surplus |
|---|---:|---:|---:|---:|
| arithmetic/loops | 509 | 504 | 1.010 | +5 |
| strings | 615 | 578 | 1.064 | +37 |
| structs/option | 623 | 677 | 0.920 | −54 |
| vectors | 789 | 573 | **1.377** | **+216** |
| **overall** | **2536** | **2332** | **1.0875** | **+204** |

Dynamic: control base-rs-7 = 0.565 (byte-exact ×4 environments),
tune-ox-7 = 0.755, composition-controlled token ratio 1.067.

**Vectors is the entire corpus surplus.** Strings (+37) and arithmetic
(+5) are all but cancelled by structs (−54); the +216 in vectors is
106% of the net. Any wave that does not move vectors does not move the
objective.

## 2. The finding that drives this wave

The vectors residual is not diffuse. Three of ten tasks carry +182 of
the +216:

| task | ratio | surplus | what Rust expresses that Oxide cannot |
|---|---:|---:|---|
| n043 | 2.367 | +82 | `v.swap(0, last)` — Oxide rebuilds the vector in a 14-line loop |
| n050 | 2.395 | +60 | `v.sort(); v.reverse();` — Oxide does max-extract-and-rebuild |
| n045 | 1.976 | +40 | direct indexing — but see §4: Oxide's own `unwrap_or` was never applied here |

**Both missing constructs have near-zero reply demand.** Wave 2's gate
deferred index assignment on exactly that ground (campaign presence 0),
while its absence was silently the single most expensive gap in the
corpus. The demand census measures what models *attempt*; the objective
is what correct programs *cost*. These are different quantities and
this wave stops conflating them.

Recorded as a method lesson, not just a wave input: an instrument that
answers a question adjacent to the objective will be read as if it
answered the objective, until something forces the comparison.

## 3. Cost census (the instrument work precedes everything)

A second census, sitting beside the demand census, keyed to cost rather
than attempts. It is also the "pairwise token-diff attribution"
instrument wave 2 queued for strings — one instrument serves both.

**Construction.** For every one of the 40 reference pairs: tokenize both
arms with the pinned tokenizer, record `(task, class, oxide_tokens,
rust_tokens, surplus, ratio)`, and rank by absolute surplus. Report
per-class subtotals and the whole-corpus total. Surplus is signed —
tasks where Oxide wins are counted, never clipped at zero, because the
structs class's −54 is load-bearing for the overall number.

**Honesty requirements.** A pair whose two sides do not both tokenize is
`None` and named in a `dropped` list, never scored 0. The report states
the tokenizer id and hash inline, so a ranking can never be read
without the lens that produced it.

**Two-eyed gate.** The wave's slate is gated on demand census × cost
census. A candidate ships if it scores on **either** axis; candidates
scoring on **both** are ordered first. Every deferral is recorded with
both its counts, as in waves 1 and 2.

## 4. Bias rule, amended (owner-approved 2026-08-29)

Wave 2's re-authoring rule permitted a substitution only where the Rust
control used the analogous construct. It was written against a real
failure (wave 1's n041 tightening, caught by review and reverted) and it
stays in force for its original purpose: no restructuring, no inlined
bindings, no change beyond what the shipped construct replaces.

Its per-statement Rust gate is **withdrawn**. In n046 the Rust control
writes `v.iter().filter(|&&x| x < 10).count()`, so the gate forbade
Oxide's hand-rolled loop from using the `+=` this project shipped —
making Oxide pessimistic precisely where the two languages diverge
idiomatically, which is the subject under study.

**Amended rule.** Each arm is written as well as its own language
allows. A substitution is admissible when it uses only shipped
vocabulary and does not restructure the program beyond what that
construct replaces. Every admissible substitution must be applied
(a missed one is a defect, not a conservative choice), and every changed
pair is verified by the rustc/stdout oracle — byte-identical
`expected_stdout`, `validate_pair` green, contamination guard clean —
and diffed in the wave report with its token delta.

**Known authoring debt this exposes** (already measured, to be applied
under the amended rule): n045 `match` → `unwrap_or` (−26 tokens, shipped
wave 1); n046 and n065 loops → `+=` (−4, −2, shipped wave 2). A full
40-pair sweep for further missed substitutions is part of the wave.

## 5. Provisional slate (the two-eyed gate rules on it)

Measured projections, counted with the pinned tokenizer:

| construct | evidence | measured effect |
|---|---|---|
| `swap(v, i, j)` | cost: n043 +82 (rank 1) | n043 142 → **60 tokens, exact parity with Rust** |
| `reverse(v)` | cost: n050 +60 (rank 2) | n050 103 → 39 (ratio 0.907) |
| `set(v, i, x)` | demand: 18 present / 18 rejected on amp; cost: general | n043 alone → 99, so it does not substitute for `swap` |

`swap` and `set` both ship: `set` is the general, demanded primitive,
`swap` is the token-efficient spelling of the exchange shape, and the
measurement above shows one does not obviate the other. All three
follow the established convention of consuming and returning the vector
(`v = swap(v, 0, last)`), consistent with `push`.

**Open design question for the implementing task, to be answered in
SPEC before code:** out-of-range behaviour for `set` and `swap`. `get`
returns `Option`; these return a vector. The candidates are a
diagnostic error at transpile time where indices are constant, a
runtime panic matching Rust's, or a silent no-op. A silent no-op is
rejected in advance — it would be a value that looks like a
successful operation and is not.

**Projected corpus effect** of the slate plus the §4 authoring debt:
overall **1.0875 → 1.0137**, vectors **1.377 → ~1.08**.

## 6. Pre-registered endpoints (derived, amendable non-silently)

- **Static, after re-authoring:** overall **≤ 1.02**; vectors **≤ 1.10**;
  strings hold **≤ 1.07**; arithmetic hold **≤ 1.02**; structs hold
  **≤ 0.93**.
  *Consistency, stated rather than papered over:* at their individual
  ceilings the class targets compute to an overall of 1.026, which
  exceeds the overall target. This is deliberate — the overall target
  binds, the class targets are diagnostic, and the measured projection
  (1.014) clears the overall bar with 0.006 of room. If class values
  land at their ceilings and the overall misses, that miss is the
  honest signal and is reported as one.
- **Cross-wave goal:** overall **< 1.00**. Now quantified rather than
  aspirational: after this slate the corpus sits ~32 tokens above
  parity, and those tokens are concentrated in the predicate-count
  shapes of n046 and n065.
- **Dynamic (primary, per SPEC §59.7):** the composition-controlled
  paired ratio — pair by `(seed, task)`, require green in both arms,
  restrict to the cells green in every wave compared, report set size
  and task count beside the ratio. Target direction only: **< 1.067**.
  The unconditional mean is reported as a secondary and binds nothing.
- **Corpus-scale gate:** unchanged at **≥ 15k supervised tokens per
  arm**. Amplification at 3 sizes × 20 seeds, temperature 0.8 for
  corpus generation only (wave-2's owner ruling, which produced
  29.8k/30.0k — no escalation is expected).
- **G1:** control base-rs-7 within ±0.10 of 0.565; tune-ox-7 floor
  **0.455 met, not re-derived**. Both tuned arms retrain symmetrically.
- **G2:** per-construct uptake in card-arm and tuned-arm outputs,
  reported per spelling, never folded into a family total. Wave 2's
  `-=`/`*=` zero tuned-arm uptake is re-read this wave.

## 7. Loop mechanics

Unchanged from wave 2 where not stated: SDD with a fresh implementer and
reviewer per task; census → gate → implement → card v0.5 → re-author →
static read → amplify → corpus gate → symmetric retrain → 4-arm campaign
→ report → feed-forward. Adapter preservation at teardown is mandatory
and count-verified. Committed artifacts land under
`eval/results/v04-campaign3/` and `eval/results/v04-amp4/`.

## 8. Out of scope, with the reason quantified

**Closures / block arguments / a predicate surface.** The wave-2 report
named this as the vectors residual's likely requirement. The cost census
contradicts that: the predicate-count shapes (n046, n065) are worth ~41
tokens combined, against ~146 for two trivial builtins. A closure
surface also collides directly with implicit linear ownership — closures
capturing owned values is the hardest open question in the language —
and buying 41 tokens is not a reason to open it. Revisit in wave 4 with
the post-slate number in hand.

Also out of scope: strings vocabulary (the class sits at 1.064 and its
residual is not pattern-shaped); `if let` (68 against the 89 bar,
re-gated only if the cost census ranks it); the 954-line
`demand_census.py` split (owner-flagged, independent of this wave).

## 9. Standing authorization and stop conditions

The owner has authorized execution without a further check-in when
community GPU capacity appears (poll running; community RTX 3090 ≈$0.22/h
or RTX 4090 ≈$0.34/h, projected loop cost **≈$1.45–2.00** against
≈$10.6 remaining of the $23 tranche).

Execution stops and asks when:

1. the corpus-scale gate fails after one escalation;
2. a G1 guard trips (control outside ±0.10, or the 0.455 floor unmet at
   restored scale);
3. the slate turns out to need a language change larger than a builtin;
4. any irreversible or outward-facing step beyond the wave's own branch
   and artifacts.

Everything else is ruled in-flight and recorded in the ledger, per the
standing SDD discipline.
