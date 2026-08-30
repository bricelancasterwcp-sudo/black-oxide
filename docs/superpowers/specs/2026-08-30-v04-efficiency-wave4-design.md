# v0.4 — the efficiency cycle, wave 4 (familiarity, and the 7B question)

**Date:** 2026-08-30
**Purpose:** fourth turn of the efficiency design loop. The binding
purpose and no-verdict discipline carry over. Input = the committed
wave-3 feed-forward (`eval/results/v04-campaign3/REPORT.md`) as amended,
and SPEC §62's three objectives.
**Branch:** `v04-efficiency-wave4`, off `main` @ `ec34528c`.
**Status:** owner-approved 2026-08-30, with a **$3.00 hard spend cap**
against a $6.95 remaining balance.

## 1. What wave 3 left

Static **0.9863** (below parity); dynamic **1.1315** and moving the wrong
way. G2 showed the model declined most of the new vocabulary, and the
same-day amendment showed why: the pipeline taught it in as few as 2 of
294 examples, and uptake tracks **exposure × familiarity** (§6.1).

Two levers follow. This wave pulls **familiarity** only, for a reason
stated below.

## 2. Why exposure is not this wave's lever

Raising a construct's corpus share looks like the obvious move and is not
cheaply available:

- **Authoring new reference tasks** changes the frozen 40-pair corpus, so
  the static ratio stops being comparable to waves 1–3. The whole
  1.22 → 0.9863 trajectory rests on that corpus being fixed.
- **Oversampling** training examples containing a construct breaks the
  token-matching between arms. Rust has no `swap`-equivalent to
  oversample symmetrically, so Oxide would gain tokens Rust does not and
  the matched corpus stops being matched — which is the control the whole
  dynamic estimand depends on.

Exposure therefore needs a wave designed around it (a second reference
corpus, or a matching scheme that survives weighting). Deferred with the
reason recorded, not dropped.

**Familiarity, by contrast, is free and clean**: re-spelling a construct
changes neither its corpus share nor the token-matching. Wave 4 is a
controlled single-variable test of the §62 claim that familiarity drives
uptake.

## 3. What ships

### 3.1 The predicate literal re-spells to `|x|`

`x -> expr` becomes `|x| expr`. Everything else about the construct is
unchanged: it still **cannot capture** (`OX0205`), still has type
`Pred<T>`, still emits the same Rust closure.

This reverses a wave-3 design ruling on measured evidence. That ruling
argued an unfamiliar spelling would make the no-capture restriction
legible; the tuned arm chose `|x|` over the arrow about **10:1** at equal
exposure. Per §62.1 the correct reading is that familiarity is a *win* on
objective 3, not a concession. The restriction is taught by the
diagnostic instead of by the syntax.

Static cost: `|x|` measured 1 token *more* per use than the arrow
(17 vs 16), so the re-spelling costs ~2 tokens corpus-wide. **The wave
deliberately spends static efficiency to buy learnability** — the first
time the project has traded one objective against another with both
measured, and exactly the trade §62 says to make.

### 3.2 `filter(v, |x| ...)` ships alongside `count_if`

Both remain available, and the wave measures which the model reaches for:

| | tokens for "count matching" | familiarity |
|---|---|---|
| `count_if(v, p)` | fewer | C++ idiom; the model used it 0 times in wave 3 |
| `len(filter(v, p))` | more | `filter` is near-universal; the model writes it unprompted |

This is a **direct §62 experiment**: efficiency and learnability point at
different constructs, both are offered at equal exposure, and the model
decides. Whichever wins informs how the next wave weighs the two
objectives. `filter` also generalises where `count_if` does not — it is
the surface `argmax(items, |item| ...)` implies.

### 3.3 The 14B quartet

`base-ox-14`, `base-rs-14`, `tune-ox-14`, `tune-rs-14` join the campaign.

Every efficiency, uptake and learnability claim from waves 1–3 is a **7B
claim**; the only scale evidence is wave 0's 12-arm matrix, which trended
*against* Oxide as size grew (`tune-rs-14` reached 0.990). Larger models
plausibly learn novel constructs more readily, so wave 3's low-uptake
findings may be a 7B artifact. This is the cheapest available test of
whether the project has been optimising against the wrong-sized subject.

## 4. Pre-registered endpoints

- **Learnability (new, first-class per §62.1):** uptake ÷ corpus
  exposure, per construct, per arm. Reported as a ratio with both terms
  visible; a construct is never called "rejected" without its exposure
  stated beside it.
  - **The wave's central prediction, falsifiable:** at equal exposure,
    `|x|` draws materially more uptake than `x -> expr` did (4 uses,
    2.4% exposure). If uptake does not move, familiarity is not the
    lever §62 claims and §62.2's quadrant ordering is wrong.
- **Static:** overall **≤ 0.99** (holding below parity while paying ~2
  tokens for the re-spelling); vectors **≤ 1.00**; other classes hold.
- **Dynamic (primary, §59.7):** composition-controlled paired ratio on
  cells green in every wave compared, set size reported with the ratio.
  Target direction only: **< 1.1315**.
- **Scale:** the 14B arms are reported as their own G1/G2/efficiency
  block. **No cross-size claim is pre-registered** — this is the first
  14B read since wave 0 and its job is to generate a hypothesis, not
  settle one.
- **G1:** control `base-rs-7` within ±0.10 of 0.565; `tune-ox-7` floor
  0.455. 14B arms carry no floor (no prior at this corpus scale).
- **Corpus-scale gate:** ≥ 15k supervised tokens per arm, fresh-first as
  in wave 3.

## 5. Budget and stops

**Hard cap $3.00** of a $6.95 balance. Estimate $1.85 on a community
RTX 3090 at $0.22/h (8.4 pod-hours: setup 0.6, amplification 4.5,
trainings 1.2, campaign 2.1).

Measured basis for the estimate, from wave 3 on the same hardware: 7B→14B
costs **1.77×** (amplification legs 77 → 136 min); 7B campaign arms
averaged 11.8 min; both 7B trainings plus merges and converts took ~0.4h.

Note for the runbook: the community 3090 is not a budget compromise for
this pipeline. Same amplification work measured 4.27h on a 4090 and 4.48h
on a 3090 — **5% slower at 30% of the price**.

~~because every session carries a rustc compile and the workload is
CPU-bound.~~ **Amended 2026-08-30, before this wave's numbers were
read.** That mechanism was asserted without measurement and is wrong:
rustc is ~5% of amplification (15,247 compiles at ~18 ms check + ~33 ms
build ≈ 14 min of 269). The plain explanation is memory bandwidth — the
two cards are 936 vs 1008 GB/s, **7% apart**, and decode is
bandwidth-bound, which fits the observed 5% directly. The conclusion
stands on the corrected basis, and the corrected basis also predicts
what a faster card would buy: very little, because bandwidth scales
slowly across the tiers we can afford. See
`eval/results/v04-campaign3/REPORT.md` §7's amendment for the full
arithmetic.

Execution stops and asks when:

1. **14B QLoRA does not fit 24 GB.** Verified *before* committing hours.
   The wave does **not** silently move to a 48 GB card at $0.44/h (~$5.00
   for the wave, 72% of the balance). It drops to 7B-only and reports the
   14B arms as not-run, with the reason.
2. The corpus-scale gate fails after one escalation.
3. A G1 guard trips.
4. Projected spend would exceed the $3.00 cap.

## 6. Out of scope

- **Exposure raising** — deferred with the reason in §2; needs its own
  design.
- **`swap`'s zero uptake** — cannot be honestly diagnosed without the
  exposure lever. It stays shipped and unjudged.
- **`argmax`/`max_by`** — `filter` first; adding two higher-order
  builtins at once would confound §3.2's comparison.
- **`/=`**, the census-family debt, and the 954-line `demand_census.py`
  split — standing items, unrelated to this wave's question.
