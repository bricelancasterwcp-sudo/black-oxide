# Usefulness fails first at scale

*Black Oxide findings series — 2026-09-02. All numbers are reproducible
from this repository; sources are linked inline. Paths are relative to
`eval/results/` unless stated.*

## The claim

Everything this project measured on 40–150 token programs — a language
below token parity with Rust, a fine-tuned 7B that beats the untuned
Rust control, a 14B at parity with no training — **inverts or collapses
on 200–600 token programs.** On that tier the language needs more tokens
than Rust, not fewer; the same tuned model that compiles 83% of its
small programs compiles 5% of its large ones; and doubling model size
moves the compile-rate ratio by 0.002. The mechanism is a lexer-level
gap (no indexing syntax) that a more capable model hits *more* often,
because sophisticated code indexes.

The consequence for the project's three objectives (SPEC §62): efficiency
is downstream of usefulness, and usefulness fails first at scale. You
cannot ask "how many tokens does a correct program cost" at a size where
correct programs are 5% of attempts.

## The instrument: a second tier

Wave 8 authored a large tier — 20 tasks at 200–600 tokens, both arms
written to the same discipline by one author, all oracle-verified
against a committed `expected_stdout`, sizes measured with the pinned
tokenizer ([`v04-wave8-large/REPORT.md`](../../eval/results/v04-wave8-large/REPORT.md)):

| arm | min | median | max |
|---|---:|---:|---:|
| oxide | 231 | 292.5 | 389 |
| rust | 201 | 276.5 | 346 |

Contamination is zero in both directions — against the held-out eval set
and against the training corpus the v5 adapters were trained on. The
guards against single-author bias were: author Rust first from the prompt
alone, then Oxide; then re-review under a criterion fixed before looking.
The re-review moved the ratio 1.4 points *toward* Oxide (below), which
is evidence the guard has teeth, not proof the bias is gone. Neither arm
uses hash-based collections, so the Rust arm could be shorter still: the
static number is conservative in Oxide's favour.

## Phase A: the static advantage inverts

| task set | programs | median oxide tokens | oxide / rust |
|---|---:|---:|---:|
| train references | 40 | 57 | 0.9871 |
| eval references (wave 7A, both arms reviewed) | 20 | 73 | 0.9462 |
| **large tier** | **20** | **292.5** | **1.0622** |

The pre-registered reading was that a rise toward 1.00 would mean the
advantage is a fixed prelude constant diluting with size. It does not
dilute; it inverts. By class:

| class | large tier | small tier (eval) |
|---|---:|---:|
| structs/option | **0.9312** | 0.9187 |
| arithmetic/loops | 1.0222 | 0.9978 |
| vectors | 1.0825 | 0.7682 |
| strings | 1.2208 | 1.0731 |

**Only structs/option survives the size change, and it survives almost
exactly.** That is the implicit-ownership win, and it is a
*per-declaration* saving: larger programs declare more, so it does not
decay. Vectors — the project's proudest number, 1.377 at wave 3's open
and 0.7682 on held-out small tasks — reads 1.0825 here. Four waves of
vector vocabulary transferred to held-out *small* tasks and not to large
ones.

The stratification the spec pre-committed to publish either way bought
almost nothing: compositional tasks 1.0718, large-linear tasks 1.0482,
both above parity. So the inversion is not about helper amortisation;
large linear programs with no helpers at all are also above parity.

The drivers, read off the pairs rather than posited: predicates cannot
capture (`OX0205`), so a *computed* threshold costs a five-line loop
where a literal one is free — a cost the small tiers structurally could
not see; no `map` / `max_by_key` / `any` / `all`; indexed access as
`unwrap_or(get(v, i), 0)` against `v[i]`; no string `split` or
`reverse`; push chains against `vec![...]`.

**The re-review changed the answer.** The first measurement read 1.0766.
The symmetric pass found six Oxide programs using a manual `while i <
len(v)` where the Rust arm had an idiomatic counted loop and Oxide has
`range`; converting exactly those six gave 1.0622. A 1.4-point authoring
asymmetry against the arm the author did not design, found only because
the result favoured the other arm.

## Phase B: the model cannot write the language at scale

Five arms, no training, no amplification, reusing the v5 adapters
([`v04-wave8-phaseb/REPORT.md`](../../eval/results/v04-wave8-phaseb/REPORT.md)):

| tier | arm | compiles | pass@1 | pass@10v |
|---|---|---:|---:|---:|
| small | base-rs-7 (drift guard) | 99.5% | 0.565 | 0.600 |
| small | tune-ox-7 | 70.5% | 0.645 | 0.750 |
| small | tune-rs-7 | 95.0% | 0.870 | 0.900 |
| large | **tune-ox-7** | **5.5%** | **0.035** | 0.200 |
| large | tune-rs-7 | 81.5% | 0.200 | 0.450 |

**The tuned 7B produces *compiling* Oxide 5.5% of the time on large
tasks against 81.5% for the symmetrically-trained Rust arm.** Pass@1
falls 0.645 → 0.035 (18×) where Rust falls 0.870 → 0.200 (4.4×). Three
alternative explanations were checked and none survives:

- **Truncation:** 0 truncated generations in either arm on either tier;
  median output 1165 tokens against a 2048 cap.
- **A broken adapter or merge:** `tune-ox-7` reads 0.645 on the small
  tier — wave 4's published figure for this adapter, to the digit.
- **Distribution shift:** both arms were trained identically on
  small-task corpora and are equally out of distribution. That cannot
  explain a 15× compile gap. This is what the symmetric control was for.

The pre-registered efficiency endpoint on the large tier — the model's
surplus over the references — **did not measure**: it rests on 3 paired
green cells on one task, below the plan's floor of 5 fixed before the
run, so the 0.798 it prints is recorded and is not an endpoint. The
small tier did measure and reproduced the prior result in a fresh
environment: surplus 1.242 on 120 pairs across 13 tasks (wave 6: 1.276).

### The mechanism, read off 776 attempts

First diagnostic per failing attempt:

| tier | lexer (OX0001) | unknown identifier (OX0200) | parse (OX01xx) |
|---|---:|---:|---:|
| small | 5.1% | 24.8% | 42.7% |
| large | **27.6%** | **28.5%** | 30.0% |

The large tier's top two messages are `unexpected character '['` (126)
and `unexpected character "'"` (56). Oxide had no indexing syntax and
no character literals. First attempts containing `[`: **0.5%** on the
small tier, **17.0%** on the large tier — a 34× increase in reaching for
a construct the lexer cannot tokenise. Short programs iterate; long ones
index. The identifiers the model asked for by name, ranked: `split` 44,
`slice` 39, `map` 32, `floor` 27.

### Two instruments, one list

Phase A recorded what the author hit writing 20 large programs by hand;
Phase B recorded what the model hit over 776 attempts at the same tasks:

| Phase A (authoring) | Phase B (model failures) |
|---|---|
| indexing is `unwrap_or(get(v, i), 0)` vs `v[i]` | `unexpected character '['` — 126, the top failure |
| no string `split` (g10 hand-rolls 12 lines) | `unknown identifier 'split'` — 44 |
| no `map` / `max_by_key` | `unknown identifier 'map'` — 32 |
| no string `reverse` (g02 hand-rolls `rev_str`) | `unknown identifier 'reverse_str'` — 9 |
| predicates cannot capture a computed threshold | `\|x\| x > floor(avg(v))` — OX0205 |

## The 14B screen: scale does not rescue it

Four arms, seeds 1–3, no training
([`v04-wave8-14b-screen/REPORT.md`](../../eval/results/v04-wave8-14b-screen/REPORT.md)):

| | 7B | 14B |
|---|---:|---:|
| `tune-ox` large-tier compile rate | 5.5% | **5.0%** |
| `tune-rs` large-tier compile rate | 81.5% | **76.7%** |
| **compile-rate ratio ox / rs** | **0.067** | **0.0652** |

The pre-registered bands: ≥0.50 a 7B property, ≤0.20 a language
property, between them escalate. **The ratio moved by 0.002 across a
doubling of model size.** The two guards (`base-rs-14` at small, anchor
0.5500; `tune-ox-14` at small, anchor 0.8000) reproduced their
seed-matched anchors on all four metrics each — pass@1, pass@10v,
tokens-to-green, censored — eight of eight, exactly. The anchors had to
be seed-matched: `tune-ox-14` publishes 0.745 over ten seeds and reads
0.800 over seeds 1–3, and screening against the published figure would
have manufactured a 5.5-point anomaly out of sampling.

The mechanism at 14B: **75.5% of the Rust arm's large-tier attempts
index**, so at this size indexing is the dominant idiom. The `[` rate in
Oxide attempts rose from **16.8%** (7B) to **29.0%** (14B). A more
capable model writes more sophisticated code, and sophisticated code
indexes. `tune-ox-14` writes compiling Oxide 83.3% of the time on the
small tier and 5.0% on the large one — the same weights, same session,
zero truncations; its large-tier pass@1 is 0.000.

## Wave 9: what indexing bought, statically

`v[i]` shipped as SPEC §65, scoped by measured demand across 1014
attempts (index read 951, index assign 12, slice 4; only the read
shipped) ([`v04-wave9-index/REPORT.md`](../../eval/results/v04-wave9-index/REPORT.md)):

| | before | after | delta |
|---|---:|---:|---:|
| **large tier overall** | 1.0622 | **1.0259** | −0.0363 |
| vectors | 1.0825 | 1.0165 | −0.0660 |
| arithmetic/loops | 1.0222 | 0.9849 | −0.0373 |
| strings | 1.2208 | 1.1932 | −0.0276 |
| structs/option | 0.9312 | 0.9312 | 0 |

Twenty-eight rewritten sites closed 58% of the gap to parity in one
construct; structs/option did not move because it never indexed, so the
construct moved exactly what it should. The small tier is untouched at
0.9462. Three things from the build outrank the token count: a
mechanical rewrite of `unwrap_or(get(v, i), -1)` in `t17` was caught by
the oracle (the task is specifically an out-of-range lookup; under
`v[i]` it panicked), so `v[i]` is not a universal replacement and `get`
stays; the `as usize` cast had to be parenthesised (`v[len(v) - 1]`
otherwise emits `v[len(v) - (1 as usize)]`); and `]` was missing from
the lexer's statement-terminator set, so `let a = v[0]` on its own line
swallowed the next statement — every one of 15 unit tests had put the
index mid-line, and three large-tier references caught it at once.

**Nothing dynamic is claimed for wave 9 here.** Whether shipping `[`
moves the compile rate is the pre-registered re-screen — same four 14B
arms, same seeds, primary endpoint the large-tier compile-rate ratio
against 0.0652, secondary the `OX0001` share of first diagnostics against
0.338 (73 of 216 — the plan first quoted 73 of 191, a
denominator summed from a report table; corrected before the run). The plan states in advance that the rate will not jump
to 29%: clearing the lexer moves an attempt to its *next* error, and
unknown identifiers were already 43 of 216.

**Re-screen result pending.**
<!-- RESCREEN-PENDING: fill from eval/results/v04-wave9-rescreen/screen.json (compile ratio vs 0.0652; OX0001 share vs 0.338) -->

## What this does to the project's framing

1. **Every static claim is scale-bound.** "Below parity" is true of
   40–150 token programs and false of 200–600 token ones. Quote both or
   neither.
2. **Efficiency is downstream of usefulness.** At scale the language
   needs ~3–6% more tokens than Rust and the model can barely write it;
   the efficiency gap is the smaller problem.
3. **Fine-tuning did not generalise along the size axis.** The adapter
   that took the 7B to 0.645 on small tasks took it to 0.035 on large
   ones. No previous wave could have seen this, because every previous
   wave measured only the size where it holds.
4. **Scale is not a lever for this problem**, and it works against a
   novel notation: the pressure to use syntax the language lacks grows
   with capability.
5. **A lexer-level gap is fatal; a stdlib gap is merely verbose.** The
   order in which a notation's gaps bind is set by the compiler's
   stages, and the model hits the earliest one.

## Honest limits

- The large tier is 20 tasks, both arms authored by one person who spent
  eight waves designing one of them, with the guards stated above.
- One model family at scale (Qwen2.5-Coder 7B and 14B), q8_0, one QLoRA
  recipe, adapters trained on small-task corpora. The 14B screen is three
  seeds — enough to separate 5% from 77% with large margin, not enough
  for anything finer, and it said so in advance.
- For the 8 large-linear tasks the oracle is two-arm agreement plus
  independently computed values for four of them, not hand-tracing of
  every program.
- The large-tier surplus (0.798) is printed and is not an endpoint.
- The dynamic effect of indexing is unmeasured until the re-screen
  lands; a construct that shortens references while the model still
  cannot use it would be wave 3's `swap` outcome again.
