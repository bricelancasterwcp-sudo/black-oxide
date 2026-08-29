# v0.4 — the efficiency cycle, wave 2 (vectors residual + strings + census v2)

**Date:** 2026-08-28 (evening)
**Purpose:** second turn of the efficiency design loop; the binding
purpose statement and no-verdict discipline of the wave-1 spec carry
over unchanged. Input = the committed wave-1 feed-forward
(`eval/results/v04-campaign/REPORT.md`). Branch: continues on
`v04-efficiency-wave1` (one reviewable v0.4 arc; stacked on
`finetune-experiment`, whose merge remains the owner's decision).
**Status:** initiated on the owner's "keep going" after the wave-1
report; decisions below are presented in-flight and remain
owner-overridable at any point.

## Baseline (wave-1 close, the committed anchor)

Static reference ratios: arithmetic 1.038, strings 1.159, structs
0.923, vectors 1.389, overall 1.121 (means ox 52.3/67.0/62.5/79.6,
rs 50.4/57.8/67.7/57.3). Dynamic tokens-to-green ratio 1.13. G1 floor
0.455 unmet at 7.4k training tokens (diagnosed corpus-size); control
0.565 exact ×3 environments.

## Objective and pre-registered endpoints (chosen goals, amendable non-silently)

- **Static, after wave-2 re-authoring:** overall **≤ 1.05**, vectors
  **≤ 1.15** (retry at second vocabulary rung), strings **≤ 1.08**,
  arithmetic **≤ 1.02** *if* `+=` ships (else hold 1.038 ± 0.02),
  structs/option **≤ 1.00** (hold). Consistency: at exactly-on-target
  class values the overall computes to ≈ 1.04 — the pair is
  arithmetic-consistent with slack. Cross-wave goal stays ≤ 1.00.
- **Corpus-scale gate (new, from the wave-1 G1 lesson):** the tuned
  dynamic read runs ONLY once the wave-2 matched corpus reaches
  **≥ 15k supervised tokens per arm** (wave-0 scale). Under-scale, the
  dynamic read is postponed to a pooled later run — never again read
  against the floor at mismatched scale. Amplification plan: pool the
  committed v04-amp verified programs with a fresh card-v0.4.1
  amplification at 3 sizes × 20 seeds; raise seeds further if the
  pool still falls short.
- **G1:** control base-rs-7 within ±0.10 of 0.565; tune-ox-7 floor
  **0.455 met, not re-derived**, at restored scale. Both tuned arms
  retrain symmetrically on the wave-2 matched corpus.
- **G2:** per-construct uptake counted in card-arm and tuned-arm
  outputs; zero-uptake = failed candidate, ruled next wave.
- **Efficiency:** tokens-to-green ratio, target direction only
  (< 1.13); descriptive.

## Census v2 (the instrument work precedes everything)

Wave-1's instrument gaps, closed before any gate ruling:

1. **Rejection cross-check:** a pattern hit counts as *unmet demand*
   only when the same reply's session failed to compile at first
   attempt (join census hits against the run's triples/cells verdicts;
   report both raw presence and rejection-crossed counts side by
   side). The `range(a,b)` lesson, mechanized.
2. **`+=` / compound-assignment family** (also `-=`, `*=` as separate
   spellings): absent from the language, present in failing replies,
   never censused.
3. **Hand-rolled-pattern census over programs** (the wave-1 gap): pinned
   structural patterns for occurrence-counting loops, removal/rebuild
   loops, string-build char loops, min/max/sum scans (now expected ~0
   in re-authored references — the census proves the re-author), per
   class, over references and the v04-amp verified pool.
4. Fresh reply data: the committed wave-1 campaign + v04-amp raw
   replies (both in `eval/results/`), so the census reads
   post-card-v0.4 behavior.

## Provisional slate (census v2 gates it; cap 8 constructs again)

- **Vectors residual:** `count(v, x) -> Int`; `remove_at(v, i) ->
  Vec<T>` (consuming, like push/sort; OOB mirrors get's contract) OR
  bracket index assignment `v[i] = x` as syntax — the census's
  rejection-crossed bracket count decides which surface ships;
  possibly `first(v)`/`last(v) -> Option<T>` if hand-rolled counts
  demand them.
- **Strings:** decided by the hand-rolled census over strings-class
  programs (candidates: `split(s, sep) -> Vec<Str>`, `join(v, sep) ->
  Str`, `char_at(s, i) -> Str`, `substr(s, a, b) -> Str`,
  `str_contains(s, sub) -> Bool`); ship the top hand-rolled patterns
  only, cap-limited.
- **`if let Some(x) = e { }`** — demand rose 35→89 with card v0.4;
  ships if census v2 confirms ≥ that level, as parser sugar desugaring
  to single-arm match (byte-identity test against the hand-written
  equivalent).
- **`+=` and friends** — statement-level sugar (`x += e` desugars to
  `x = x + e`) if rejection-crossed demand confirms; arithmetic's
  target moves only if this ships.

All new builtins go through the three-seam mechanism with the
shadowing rule automatically covering collisions; all syntax sugar
desugars to existing AST (no new sema semantics).

## Loop mechanics (unchanged from wave 1 where not stated)

Bias rules for re-authoring, mutation discipline, identical-stdout
law, frozen eval corpus, card mirroring with the matched-length
tolerance, RunPod runbook with all recorded ops lessons (count-verified
rsyncs now mandatory), budget ceiling for the wave-2 dynamic loop:
**$10** (program spend to date ≈ $3.40 of $23).

## Out of scope

Ownership semantics; the learnability experiment; merges (owner's);
public write-up (owner-gated); wave-3 planning beyond the feed-forward
this wave's report will produce.

> **Amended 2026-08-28 (census-v2 gate, before any implementation):**
> the gated slate is `+=`/`-=`/`*=` (statement sugar; 64/64 = 100%
> mechanical rejection at presence in base-ox-7, 660 amp presence) and
> `count(v, x)` (occurrence_count hand-rolled 11 refs / 12 amp).
> Deferred with counts: `if let` (68 amp presence < the pre-registered
> 89 bar), bracket index-assign (0 campaign presence), `remove_at`
> (2 hand-rolled refs), strings vocabulary (string_build 1/1 — the
> strings residual is not hand-rolled-pattern-shaped; wave 3 gets a
> pairwise token-diff attribution instrument instead). Slate-dependent
> targets re-set per the spec's own conditional-target pattern:
> overall ≤ 1.09, vectors ≤ 1.25, arithmetic ≤ 1.02, strings hold
> 1.159 ± 0.03, structs hold ≤ 1.00 (consistency at exact hits
> ≈ 1.083).

> **Amended 2026-08-29 (scale-gate STOP, owner ruling):** the corpus-
> scale gate held twice (8.8k → 11.0k/arm after the pre-registered
> +20-seed escalation; single-family seed-scaling flattens: 74→143→188
> uniques). Owner ruled option (a): amplification re-runs at
> **temperature 0.8 for corpus generation only** — the sampler pin
> (0.2) binds measurement arms, not corpus generation, whose quality
> is oracle-guarded (only compiler-verified programs enter the pool).
> The final pool = v04-amp (0.2) + amp2 (0.2) + amp3 (0.8), each
> pool's sampler recorded in provenance; the ≥15k gate and the 0.455
> floor stand unchanged.
