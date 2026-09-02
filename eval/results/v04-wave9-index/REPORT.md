# v0.4 wave 9 — indexing (`v[i]`), and what it bought statically

2026-09-02. SPEC 65. Built against wave 8's measurement, which ranked
this as the top design item. **GPU cost: $0** — this report covers the
static half only; the dynamic half needs a pod and is not claimed here.

## What shipped

`v[i]` reads a `Vec<T>` element and yields **`T`**, not `Option<T>`. It
is a postfix expression at the call tier, so `v[0] + 1` groups as
`(v[0]) + 1` and `r.values[1]` indexes the field. Out-of-range panics,
joining the SPEC 60.2 category `set` and `swap` already belong to.

Scope came from measured demand across 1014 model attempts, not taste:

| form | occurrences | shipped |
|---|---:|---|
| index read `v[i]` | **951** | yes |
| index assign `v[i] = x` | 12 | no — `set(v, i, x)` covers it |
| slice `v[a..b]` | 4 | no |

## The static result

**Large tier: 1.0622 → 1.0259**, from 28 rewritten sites. That closes
**58% of the gap to parity** in a single construct.

| class | before | after | delta |
|---|---:|---:|---:|
| vectors | 1.0825 | **1.0165** | −0.0660 |
| arithmetic/loops | 1.0222 | **0.9849** | −0.0373 |
| strings | 1.2208 | 1.1932 | −0.0276 |
| structs/option | 0.9312 | 0.9312 | 0 |

| stratum | after |
|---|---:|
| compositional | 1.0613 |
| **large-linear** | **0.9739** |

Arithmetic/loops and the whole large-linear stratum now sit **below
parity**. structs/option is unchanged because it never indexed — the
construct moved exactly what it should and nothing it shouldn't.

**The small eval tier is untouched at 0.9462.** No published endpoint
moved.

## The rewrite that had to be reverted, and why it matters

The small tier has two `unwrap_or(get(v, i), -1)` sites, in `t17`. A
mechanical rewrite converted them and **the oracle caught it**: `t17`
prints `20` then `-1`, because its task is *specifically* an
out-of-range lookup returning a default. Under `v[i]` it printed `20`
and panicked.

Three things follow, and they outrank the token count:

1. **`v[i]` is not a universal replacement for `unwrap_or(get(v, i), d)`**
   — only where the index is known in range, which is the overwhelming
   but not universal case.
2. **`get` remains necessary**, which retroactively validates keeping it
   rather than replacing it. A language with only `v[i]` could not
   express `t17` at all.
3. **The mechanical rewriter was unsafe and only the oracle stopped it.**
   Oracle-verified reference pairs exist for exactly this, and this is
   the first time in the project they have caught a rewrite the author
   believed was meaning-preserving.

## Two defects found while building, both by testing

**The cast needed parenthesising.** `v[i]` emits `v[(i) as usize]`
because Rust binds `as` tighter than arithmetic; without the parens
`v[len(v) - 1]` emits `v[len(v) - (1 as usize)]` and rustc rejects it.
Found by the second-commonest index expression there is.

**`]` was missing from the lexer's `TERMINATOR_SET`.** A NEWLINE is only
emitted after a token that can end a statement, so `let a = v[0]`
followed by another line produced no NEWLINE and the statement swallowed
the next one. Every index in the first test pass sat mid-line or inside
a call, so all 15 tests missed it; three large-tier references caught it
at once. The `QUESTION` entry directly above it in the same set carries a
comment describing the identical trap — the rule was documented and I
still walked into it.

Both are pinned by regression tests. Seven mutations run against the
implementation; the one survivor was a weak assertion (`".clone()" in
rust` passes on clones emitted elsewhere in the program), rewritten to
pin the clone on the index expression itself and to compile a program
that is rustc E0507 without it.

## What is NOT claimed

**Nothing dynamic.** Wave 8's finding was that the model produced
compiling Oxide 5.0–5.5% of the time on this tier, and the top failure
was `unexpected character '['`. Whether shipping `[` moves that rate is
**the** question, and it is unanswered here: it needs a pod, and it
should be run against the same arms and seeds as the wave-8 screen so
the comparison is like-for-like.

The static result is necessary but not sufficient evidence. A construct
that shortens references while the model still cannot use it would be
the wave-3 `swap` outcome — shipped on cost evidence, zero uptake.

## Feed-forward

1. **Re-run the wave-8 screen arms against the new language.** Same four
   arms, same seeds 1,2,3, same anchors. The pre-registered endpoint is
   the large-tier compile-rate ratio, which read 0.0652. Estimated
   ~$0.30 since the weights are unchanged and only the card and the
   transpiler move.
2. **The card gained 16 words** (1172 → 1188 of a 1200 limit). The next
   construct will need the limit raised, non-silently.
3. **`split`, `slice`, `map`, `floor`** remain the ranked stdlib demand.
   `strings` is still the worst class at 1.1932 and `split` is its
   largest single gap.
4. **Index-assign is deferred, not rejected**: 12 occurrences did not
   clear the gate, and it would be the first mutating statement form in
   a language whose vector convention is owned-in/owned-out.
