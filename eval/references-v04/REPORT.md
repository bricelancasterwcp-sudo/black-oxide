# v0.4 wave 6 — the static/dynamic divergence was measured on two different task sets

2026-08-31. Wave 4's feed-forward named the static/dynamic divergence as
the project's central open problem and proposed building a per-construct
attribution instrument. Before building it, the two estimands were
checked for comparability. They were not comparable, and fixing that
changes the size of the problem rather than dissolving it.

## 1. The confound

| estimand | task set | references |
|---|---|---|
| static (published 0.9871) | **train**, n001–n067, 40 tasks | re-authored every wave |
| dynamic (1.1982) | **eval**, t01–t20, 20 tasks | **frozen since the initial commit** |

`eval/solutions/` was last modified on **2026-08-07, the repository's
first commit**. It contains zero uses of `sort`, `unwrap_or`, `+=`,
`swap`, `set`, `count_if` or `filter` — every construct waves 1–4
shipped. The train references, by contrast, were re-authored in each
wave and last touched 2026-08-30.

**Four waves of static improvement were measured only on the tasks we
re-authored.** The dynamic campaign runs on the tasks we never touched.
The two numbers were never measuring the same thing, and the recurring
finding "the language got shorter but the model did not follow" rested
on that mismatch.

Measured for the first time: the **eval-set** static ratio under the
frozen references is **1.1796** — essentially the wave-0 state (1.22),
which is what one expects of references written before the vocabulary
existed.

## 2. What was done

`eval/solutions/` is the **contamination reference** —
`train_corpus.contamination_report()` flags any training program whose
normalised source matches a committed eval solution. Modernising it
would shift that baseline and make train and eval look more alike, which
is the direction that could mask real leakage. **It is left untouched.**

Instead a separate measurement-only set was authored at
`eval/references-v04/oxide/`, nothing else reads it. Every one of the 20
programs was verified through the real oracle: transpile, rustc,
execute, byte-compare against the frozen `expected_stdout`. All 20 green.

Eight of twenty needed changes; the rest were already at or below parity
or use shapes the language still lacks.

| task | class | was | now | saved | ratio now |
|---|---|---:|---:|---:|---:|
| t11 | vectors | 150 | 37 | **+113** | 0.771 |
| t14 | strings | 133 | 73 | +60 | 0.880 |
| t09 | vectors | 85 | 34 | +51 | 0.791 |
| t08 | vectors | 99 | 52 | +47 | 0.776 |
| t17 | structs/option | 81 | 51 | +30 | 0.797 |
| t10 | vectors | 86 | 56 | +30 | 0.747 |
| t07 | arithmetic/loops | 63 | 42 | +21 | 0.840 |
| t15 | strings | 89 | 81 | +8 | 0.953 |

t11 is the clearest case: the frozen reference hand-rolls a `min_above`
helper and a selection-sort loop, 150 tokens, for "print these six
numbers in increasing order". With `sort` — shipped in wave 1 — it is 37
tokens. t09 hand-rolls reverse iteration where `reverse` exists. t14
defines its own `contains` when the builtin has existed since wave 1.

## 3. Result — the divergence is real, and larger than believed

| measurement | ratio |
|---|---:|
| eval-set static, frozen references | 1.1796 |
| **eval-set static, current vocabulary** | **0.9393** |
| train-set static (published) | 0.9871 |
| **model dynamic on eval tasks (7B, composition-controlled)** | **1.1982** |

The eval set now sits at **0.9393 — below the train set's 0.9871.** The
language expresses these tasks in 6% fewer tokens than Rust; the model
writes them in 20% more.

**On identical tasks, with both numbers finally measured on the same
task set, the model spends 27.6% more tokens than the language
requires.** That is the project's central problem stated without a
confound for the first time.

The earlier framing was wrong in its arithmetic and right in its
substance. Correcting the confound **strengthens** the finding: the gap
is not 0.9871-vs-1.1982 across different tasks, it is
0.9393-vs-1.1982 on the same ones.

## 4. Limitation, stated rather than buried

Only the Oxide side was modernised. The Rust references are unchanged
and were not systematically re-reviewed, so if they are suboptimal this
ratio flatters Oxide. Spot checks found them idiomatic — t11 is
`v.sort()` and a loop, t09 is `.iter().rev()`, both what a competent
Rust programmer writes — but that check was informal and is not a
substitute for the symmetric review the amended bias rule (SPEC §60.4)
would require before this number is published as an endpoint.

**This report therefore does not claim 0.9393 as a project endpoint.**
It claims that the previously published comparison was confounded, and
that a same-task comparison puts the model's surplus at roughly 28%.

## 5. Feed-forward

1. **Re-review the Rust eval references symmetrically**, then promote
   the eval-set static ratio to a reported endpoint alongside the
   train-set one. Until then the project has one endpoint measured on
   tasks its dynamic arm never runs.
2. **The 28% surplus is now the attributable quantity.** The
   per-construct attribution instrument wave 4 proposed is worth
   building *now*, because there is finally a well-posed question for
   it: which constructs account for the gap between the 0.9393
   references and the model's 1.1982 output, on the same 20 tasks.
3. **Twelve of twenty eval references needed no change.** Their surplus,
   if any, is not reachable with current vocabulary and is the honest
   place to look for the next language gap — the same cost-census logic
   that found `swap` and `reverse`, applied to the eval set.
4. **Process lesson, recorded because it cost four waves:** an estimand
   pair must be checked for comparability *before* their difference is
   named as a finding. The static and dynamic ratios were compared
   across five waves without anyone asking whether they ran on the same
   tasks. The check took one command.
