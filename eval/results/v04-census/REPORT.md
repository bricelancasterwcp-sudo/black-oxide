# v0.4 Demand Census

Construct demand mined from committed campaign replies (`eval/results/runpod-exp/`, oxide arms only: base-ox-1.5, base-ox-14, base-ox-7, tune-ox-1.5, tune-ox-14, tune-ox-7) and the matched training corpus (`eval.token_match.load_matched_inputs`). Counts are per-file / per-program presence, not raw occurrences (see `eval/demand_census.py`'s module docstring for the pattern definitions and the refinements measured against this corpus).

This report contains no recommendations. The ranked table is data for the wave's design-slate gate (Task 2) to read.

## Model replies (oxide arms only, per arm)

### contains

| spelling | base-ox-1.5 | base-ox-14 | base-ox-7 | tune-ox-1.5 | tune-ox-14 | tune-ox-7 | total |
|---|---|---|---|---|---|---|---|
| method | 36 | 0 | 4 | 4 | 0 | 0 | 44 |

### index_assign

| spelling | base-ox-1.5 | base-ox-14 | base-ox-7 | tune-ox-1.5 | tune-ox-14 | tune-ox-7 | total |
|---|---|---|---|---|---|---|---|
| bracket | 0 | 0 | 28 | 0 | 0 | 0 | 28 |
| set_method | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### minmax

| spelling | base-ox-1.5 | base-ox-14 | base-ox-7 | tune-ox-1.5 | tune-ox-14 | tune-ox-7 | total |
|---|---|---|---|---|---|---|---|
| free | 0 | 0 | 0 | 28 | 1 | 0 | 29 |
| method | 20 | 0 | 0 | 0 | 0 | 0 | 20 |

### option

| spelling | base-ox-1.5 | base-ox-14 | base-ox-7 | tune-ox-1.5 | tune-ox-14 | tune-ox-7 | total |
|---|---|---|---|---|---|---|---|
| if_let | 16 | 15 | 0 | 4 | 0 | 0 | 35 |
| question | 4 | 89 | 16 | 0 | 0 | 0 | 109 |
| unwrap_or | 20 | 4 | 0 | 0 | 0 | 0 | 24 |

### ranges

| spelling | base-ox-1.5 | base-ox-14 | base-ox-7 | tune-ox-1.5 | tune-ox-14 | tune-ox-7 | total |
|---|---|---|---|---|---|---|---|
| dotdot | 264 | 0 | 28 | 0 | 0 | 0 | 292 |
| range_call | 0 | 202 | 264 | 81 | 164 | 62 | 773 |
| to_method | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### sort

| spelling | base-ox-1.5 | base-ox-14 | base-ox-7 | tune-ox-1.5 | tune-ox-14 | tune-ox-7 | total |
|---|---|---|---|---|---|---|---|
| free | 0 | 40 | 36 | 40 | 40 | 40 | 196 |
| method | 12 | 0 | 4 | 0 | 0 | 0 | 16 |

### strings

| spelling | base-ox-1.5 | base-ox-14 | base-ox-7 | tune-ox-1.5 | tune-ox-14 | tune-ox-7 | total |
|---|---|---|---|---|---|---|---|
| format | 4 | 0 | 0 | 0 | 0 | 0 | 4 |
| join | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| split | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### sum

| spelling | base-ox-1.5 | base-ox-14 | base-ox-7 | tune-ox-1.5 | tune-ox-14 | tune-ox-7 | total |
|---|---|---|---|---|---|---|---|
| free | 0 | 0 | 0 | 0 | 6 | 0 | 6 |
| method | 40 | 0 | 36 | 24 | 0 | 0 | 100 |

## Training corpus (reference + amplified, pooled oxide+rust arms, per class)

### contains

**reference**

| spelling | arithmetic/loops | strings | structs/option | vectors | total |
|---|---|---|---|---|---|
| method | 0 | 2 | 0 | 0 | 2 |

**amplified**

| spelling | arithmetic/loops | strings | structs/option | vectors | total |
|---|---|---|---|---|---|
| method | 0 | 1 | 0 | 0 | 1 |

### index_assign

**reference**

| spelling | arithmetic/loops | strings | structs/option | vectors | total |
|---|---|---|---|---|---|
| bracket | 0 | 0 | 0 | 0 | 0 |
| set_method | 0 | 0 | 0 | 0 | 0 |

**amplified**

| spelling | arithmetic/loops | strings | structs/option | vectors | total |
|---|---|---|---|---|---|
| bracket | 0 | 1 | 0 | 0 | 1 |
| set_method | 0 | 0 | 0 | 0 | 0 |

### minmax

**reference**

| spelling | arithmetic/loops | strings | structs/option | vectors | total |
|---|---|---|---|---|---|
| free | 0 | 0 | 0 | 0 | 0 |
| method | 0 | 0 | 0 | 2 | 2 |

**amplified**

| spelling | arithmetic/loops | strings | structs/option | vectors | total |
|---|---|---|---|---|---|
| free | 0 | 0 | 0 | 0 | 0 |
| method | 0 | 0 | 0 | 8 | 8 |

### option

**reference**

| spelling | arithmetic/loops | strings | structs/option | vectors | total |
|---|---|---|---|---|---|
| if_let | 0 | 1 | 0 | 0 | 1 |
| question | 0 | 0 | 2 | 0 | 2 |
| unwrap_or | 0 | 0 | 0 | 0 | 0 |

**amplified**

| spelling | arithmetic/loops | strings | structs/option | vectors | total |
|---|---|---|---|---|---|
| if_let | 0 | 0 | 2 | 1 | 3 |
| question | 1 | 0 | 0 | 0 | 1 |
| unwrap_or | 0 | 0 | 0 | 0 | 0 |

### ranges

**reference**

| spelling | arithmetic/loops | strings | structs/option | vectors | total |
|---|---|---|---|---|---|
| dotdot | 7 | 0 | 0 | 0 | 7 |
| range_call | 7 | 0 | 0 | 0 | 7 |
| to_method | 0 | 0 | 0 | 0 | 0 |

**amplified**

| spelling | arithmetic/loops | strings | structs/option | vectors | total |
|---|---|---|---|---|---|
| dotdot | 75 | 1 | 0 | 1 | 77 |
| range_call | 54 | 0 | 0 | 0 | 54 |
| to_method | 0 | 0 | 0 | 0 | 0 |

### sort

**reference**

| spelling | arithmetic/loops | strings | structs/option | vectors | total |
|---|---|---|---|---|---|
| free | 0 | 0 | 0 | 0 | 0 |
| method | 0 | 0 | 0 | 2 | 2 |

**amplified**

| spelling | arithmetic/loops | strings | structs/option | vectors | total |
|---|---|---|---|---|---|
| free | 0 | 0 | 0 | 0 | 0 |
| method | 0 | 0 | 0 | 9 | 9 |

### strings

**reference**

| spelling | arithmetic/loops | strings | structs/option | vectors | total |
|---|---|---|---|---|---|
| format | 0 | 0 | 0 | 0 | 0 |
| join | 0 | 0 | 0 | 0 | 0 |
| split | 0 | 1 | 0 | 0 | 1 |

**amplified**

| spelling | arithmetic/loops | strings | structs/option | vectors | total |
|---|---|---|---|---|---|
| format | 0 | 0 | 0 | 0 | 0 |
| join | 0 | 0 | 0 | 0 | 0 |
| split | 0 | 0 | 0 | 0 | 0 |

### sum

**reference**

| spelling | arithmetic/loops | strings | structs/option | vectors | total |
|---|---|---|---|---|---|
| free | 0 | 0 | 0 | 0 | 0 |
| method | 0 | 0 | 0 | 0 | 0 |

**amplified**

| spelling | arithmetic/loops | strings | structs/option | vectors | total |
|---|---|---|---|---|---|
| free | 0 | 0 | 0 | 0 | 0 |
| method | 9 | 0 | 0 | 0 | 9 |

## Ranked demand (replies, summed over arms and spellings)

| family | total demand | dominant spelling | dominant count |
|---|---|---|---|
| ranges | 1065 | range_call | 773 |
| sort | 212 | free | 196 |
| option | 168 | question | 109 |
| sum | 106 | method | 100 |
| minmax | 49 | free | 29 |
| contains | 44 | method | 44 |
| index_assign | 28 | bracket | 28 |
| strings | 4 | format | 4 |

