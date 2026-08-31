# v0.4 wave 7 (Phase A) — the 28% is helper functions

2026-08-31. Spec: `docs/superpowers/specs/2026-08-31-v04-wave7-attribution-design.md`.
Diagnostic phase, run entirely on committed data. **GPU cost: $0.**

## Result

| | tokens |
|---|---:|
| modernised references, 15 eval tasks with green cells | 1092 |
| tuned 7B model output (median green per task) | 1397 |
| **surplus** | **+305 (+27.9%)** |
| **helper-function definitions** | **+272 — 89% of the surplus** |
| unattributed | +33 — 11% |

**76% of the model's helper functions are called exactly once** (67 of
88 across 132 green programs). A function defined and invoked a single
time costs a signature, a return type and a call site to save nothing.

Per the spec's pre-committed outcomes this is **state 1: a teaching
problem, not a language gap.** No vocabulary would fix it. **No Phase B
is proposed, and none should be funded.**

## A1 — symmetric Rust re-review

Wave 6 modernised only the Oxide side, so its 0.9393 was not an
endpoint. The criterion was fixed before looking: *rewrite only where a
Rust reference hand-rolls something std provides; style is not grounds.*

**One hit in twenty.** `t17` used `match v.get(i)` where
`.copied().unwrap_or(-1)` exists — the same facility Oxide's `t17`
gained from, so symmetry required it. Rust 64 → 53 tokens.

**The ratio moved against Oxide: 0.9393 → 0.9462.** Small, and that is
the point — the reviewer authored the Oxide side, so a review finding
nothing wrong with Rust would have been worthless. The other 19 were
idiomatic (`.filter().count()`, `.max().unwrap()`,
`.chars().rev().collect()`) or algorithmic tasks where the algorithm is
the work.

**Endpoint candidate: 0.9462** on the eval set, both arms reviewed.

## A2 — eval-set cost census

| class | ratio | surplus |
|---|---:|---:|
| vectors | **0.7682** | −54 |
| structs/option | 0.9187 | −44 |
| arithmetic/loops | 0.9978 | −1 |
| **strings** | **1.0731** | **+19** |
| **overall** | **0.9462** | −80 |

**Vectors went from the project's worst class to its best.** It opened
wave 3 at 1.377 on the train set and reads **0.768** here — on tasks
never authored against. Four waves of vector vocabulary transferred to
held-out work, which is the strongest evidence so far that the design
loop generalises rather than overfitting its own corpus.

**Strings is the only class above parity**, concentrated in `t13` (+22)
and `t12` (+11) — both string-reversal, where Oxide hand-rolls a
`concat` loop for want of a string `reverse`. That is the next language
gap, found by the same cost-census logic that found `swap` and
`reverse`.

## A3 — attribution

Categories were derived from reading the model's actual output, not
posited in advance. Frequencies across 132 green programs:

| pattern | share |
|---|---:|
| helper fn defined | 45% |
| duplicate struct literal (rebuild) | 17% |
| comment left in code | 5% |
| defensive `clone()` | **0%** |
| `push` chain instead of `vec(...)` | **0%** |

The zeros matter as much as the counts: the model has **fully
internalised waves 1–2 vocabulary**. It is not writing bad Oxide. It is
writing *production-style* Oxide — named helpers, descriptive
identifiers — for 40-token problems.

Comments cost 44 tokens total across all 132 programs. Negligible, and
worth recording so nobody optimises it.

### The struct-rebuild pattern is a misconception, not a constraint

17% of programs rebuild a struct to avoid a move. Example (`t19`,
model 108 tokens vs reference 53):

```
print(area(rect))
let rect_copy = Rectangle { width: 7, height: 4 } // Reuse the struct for perimeter
print(perimeter(rect_copy))
```

The model understood linear ownership and paid tokens to work around
it — **but the workaround is unnecessary.** SPEC §623: a param is `own`
only if some path uses it in a MOVE context; read-mode non-copy params
are caller-owned borrows. Verified directly: calling `area(x)` twice
raises no diagnostic. **Oxide is more permissive than the model
believes**, and the model is applying a Rust mental model to it.

This is the one place a card change has a specific, evidenced
misconception to correct — unlike wave 5's operator table, which
documented something the model already knew and moved nothing.

## What this means for the estimand

On tasks of 40–150 tokens, *any* abstraction is overhead. The
measurement is therefore partly capturing **the model's disposition to
factor code**, not its token efficiency. On tasks large enough for a
helper to pay for itself, the model's habit would be correct and the
references' inlining would be the anomaly.

That is a property of a benchmark built from toy tasks, and it bounds
what the dynamic ratio can mean. It does not invalidate the static
work — the language genuinely expresses these tasks in fewer tokens —
but it does mean "the model wastes 28%" should be read as "the model
writes helpers this benchmark is too small to amortise."

## Feed-forward

1. **Do not fund a Phase B for this.** The surplus is not a language
   gap. Shipping vocabulary against it would be building for a finding
   the diagnostic did not make.
2. **The card can correct one specific misconception**: that passing a
   struct to a user function consumes it. This has evidence behind it
   (17% of programs) where wave 5's operator table had none. Expect a
   small effect and pre-register it that way.
3. **String `reverse` is the next language gap** — `t13` +22, `t12`
   +11, the only class above parity.
4. **The benchmark's task size is now a known limit.** Any future claim
   about model token efficiency should either use larger tasks or state
   that abstraction cannot amortise at this scale.
5. **Vectors transferring from 1.377 to 0.768 on held-out tasks is the
   headline the project should keep.** It is direct evidence the design
   loop generalises.
