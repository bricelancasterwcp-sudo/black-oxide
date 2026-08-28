# v0.4 Demand Census v2

Extends `eval/demand_census.py` (wave-1 Task 1) with the `+=`/`-=`/`*=` compound-assign family (`COMPOUND_FAMILY`), five pinned hand-rolled structural patterns (`HANDROLLED`), and a rejection cross-check that joins each first-attempt reply to whether that session's first attempt compiled -- `eval/demand_census.py`'s module comments document the join's shape, the two committed layouts it reads, and the reliability check performed before any join code was written.

This report contains no recommendations. The rankings are data for the wave's design-slate gate to read.

## v04-campaign: presence vs rejection-crossed (per arm)

### compound_assign

| spelling | base-ox-7 present | base-ox-7 rejected | base-rs-7 present | base-rs-7 rejected | tune-ox-7 present | tune-ox-7 rejected | tune-rs-7 present | tune-rs-7 rejected |
|---|---|---|---|---|---|---|---|---|
| minus_eq | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 |
| plus_eq | 64 | 64 | 71 | 0 | 9 | 9 | 80 | 0 |
| times_eq | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### contains

| spelling | base-ox-7 present | base-ox-7 rejected | base-rs-7 present | base-rs-7 rejected | tune-ox-7 present | tune-ox-7 rejected | tune-rs-7 present | tune-rs-7 rejected |
|---|---|---|---|---|---|---|---|---|
| method | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### index_assign

| spelling | base-ox-7 present | base-ox-7 rejected | base-rs-7 present | base-rs-7 rejected | tune-ox-7 present | tune-ox-7 rejected | tune-rs-7 present | tune-rs-7 rejected |
|---|---|---|---|---|---|---|---|---|
| bracket | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| set_method | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### minmax

| spelling | base-ox-7 present | base-ox-7 rejected | base-rs-7 present | base-rs-7 rejected | tune-ox-7 present | tune-ox-7 rejected | tune-rs-7 present | tune-rs-7 rejected |
|---|---|---|---|---|---|---|---|---|
| free | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 |
| method | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### option

| spelling | base-ox-7 present | base-ox-7 rejected | base-rs-7 present | base-rs-7 rejected | tune-ox-7 present | tune-ox-7 rejected | tune-rs-7 present | tune-rs-7 rejected |
|---|---|---|---|---|---|---|---|---|
| if_let | 2 | 2 | 0 | 0 | 1 | 1 | 0 | 0 |
| question | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| unwrap_or | 0 | 0 | 1 | 0 | 5 | 0 | 0 | 0 |

### ranges

| spelling | base-ox-7 present | base-ox-7 rejected | base-rs-7 present | base-rs-7 rejected | tune-ox-7 present | tune-ox-7 rejected | tune-rs-7 present | tune-rs-7 rejected |
|---|---|---|---|---|---|---|---|---|
| dotdot | 9 | 9 | 59 | 1 | 0 | 0 | 53 | 0 |
| range_call | 52 | 52 | 0 | 0 | 58 | 22 | 0 | 0 |
| to_method | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### sort

| spelling | base-ox-7 present | base-ox-7 rejected | base-rs-7 present | base-rs-7 rejected | tune-ox-7 present | tune-ox-7 rejected | tune-rs-7 present | tune-rs-7 rejected |
|---|---|---|---|---|---|---|---|---|
| free | 10 | 10 | 0 | 0 | 10 | 0 | 0 | 0 |
| method | 0 | 0 | 10 | 0 | 0 | 0 | 10 | 0 |

### strings

| spelling | base-ox-7 present | base-ox-7 rejected | base-rs-7 present | base-rs-7 rejected | tune-ox-7 present | tune-ox-7 rejected | tune-rs-7 present | tune-rs-7 rejected |
|---|---|---|---|---|---|---|---|---|
| format | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| join | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| split | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### sum

| spelling | base-ox-7 present | base-ox-7 rejected | base-rs-7 present | base-rs-7 rejected | tune-ox-7 present | tune-ox-7 rejected | tune-rs-7 present | tune-rs-7 rejected |
|---|---|---|---|---|---|---|---|---|
| free | 10 | 10 | 0 | 0 | 4 | 4 | 0 | 0 |
| method | 3 | 3 | 15 | 0 | 0 | 0 | 6 | 6 |

## v04-amp: presence vs rejection-crossed (per arm)

### compound_assign

| spelling | 1.5-ox present | 1.5-ox rejected | 1.5-rs present | 1.5-rs rejected | 14-ox present | 14-ox rejected | 14-rs present | 14-rs rejected | 7-ox present | 7-ox rejected | 7-rs present | 7-rs rejected |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| minus_eq | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 0 | 0 |
| plus_eq | 105 | 105 | 121 | 27 | 0 | 0 | 120 | 10 | 115 | 115 | 108 | 10 |
| times_eq | 20 | 20 | 20 | 0 | 1 | 1 | 20 | 0 | 17 | 17 | 10 | 0 |

### contains

| spelling | 1.5-ox present | 1.5-ox rejected | 1.5-rs present | 1.5-rs rejected | 14-ox present | 14-ox rejected | 14-rs present | 14-rs rejected | 7-ox present | 7-ox rejected | 7-rs present | 7-rs rejected |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| method | 10 | 10 | 11 | 2 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 |

### index_assign

| spelling | 1.5-ox present | 1.5-ox rejected | 1.5-rs present | 1.5-rs rejected | 14-ox present | 14-ox rejected | 14-rs present | 14-rs rejected | 7-ox present | 7-ox rejected | 7-rs present | 7-rs rejected |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bracket | 0 | 0 | 0 | 0 | 0 | 0 | 13 | 13 | 5 | 5 | 0 | 0 |
| set_method | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### minmax

| spelling | 1.5-ox present | 1.5-ox rejected | 1.5-rs present | 1.5-rs rejected | 14-ox present | 14-ox rejected | 14-rs present | 14-rs rejected | 7-ox present | 7-ox rejected | 7-rs present | 7-rs rejected |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| free | 1 | 1 | 0 | 0 | 12 | 8 | 0 | 0 | 1 | 1 | 0 | 0 |
| method | 3 | 3 | 12 | 0 | 0 | 0 | 20 | 0 | 11 | 11 | 10 | 0 |

### option

| spelling | 1.5-ox present | 1.5-ox rejected | 1.5-rs present | 1.5-rs rejected | 14-ox present | 14-ox rejected | 14-rs present | 14-rs rejected | 7-ox present | 7-ox rejected | 7-rs present | 7-rs rejected |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| if_let | 11 | 11 | 2 | 0 | 2 | 2 | 39 | 15 | 4 | 4 | 10 | 9 |
| question | 27 | 27 | 0 | 0 | 63 | 54 | 0 | 0 | 33 | 23 | 0 | 0 |
| unwrap_or | 1 | 1 | 4 | 3 | 11 | 8 | 0 | 0 | 9 | 9 | 0 | 0 |

### ranges

| spelling | 1.5-ox present | 1.5-ox rejected | 1.5-rs present | 1.5-rs rejected | 14-ox present | 14-ox rejected | 14-rs present | 14-rs rejected | 7-ox present | 7-ox rejected | 7-rs present | 7-rs rejected |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dotdot | 76 | 76 | 71 | 11 | 0 | 0 | 71 | 10 | 15 | 15 | 71 | 12 |
| range_call | 0 | 0 | 0 | 0 | 95 | 39 | 0 | 0 | 63 | 60 | 0 | 0 |
| to_method | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### sort

| spelling | 1.5-ox present | 1.5-ox rejected | 1.5-rs present | 1.5-rs rejected | 14-ox present | 14-ox rejected | 14-rs present | 14-rs rejected | 7-ox present | 7-ox rejected | 7-rs present | 7-rs rejected |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| free | 5 | 5 | 0 | 0 | 20 | 2 | 0 | 0 | 24 | 24 | 0 | 0 |
| method | 1 | 1 | 3 | 0 | 6 | 6 | 10 | 0 | 3 | 3 | 10 | 0 |

### strings

| spelling | 1.5-ox present | 1.5-ox rejected | 1.5-rs present | 1.5-rs rejected | 14-ox present | 14-ox rejected | 14-rs present | 14-rs rejected | 7-ox present | 7-ox rejected | 7-rs present | 7-rs rejected |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| format | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| join | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| split | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### sum

| spelling | 1.5-ox present | 1.5-ox rejected | 1.5-rs present | 1.5-rs rejected | 14-ox present | 14-ox rejected | 14-rs present | 14-rs rejected | 7-ox present | 7-ox rejected | 7-rs present | 7-rs rejected |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| free | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 4 | 4 | 0 | 0 |
| method | 4 | 4 | 3 | 3 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 |

## Hand-rolled structural patterns (reference + amplified, per class)

### minmax_scan

**reference**

| class | count |
|---|---|
| arithmetic/loops | 0 |
| strings | 0 |
| structs/option | 0 |
| vectors | 0 |
| **total** | **0** |

**amplified**

| class | count |
|---|---|
| arithmetic/loops | 0 |
| strings | 0 |
| structs/option | 0 |
| vectors | 0 |
| **total** | **0** |

### occurrence_count

**reference**

| class | count |
|---|---|
| arithmetic/loops | 6 |
| strings | 3 |
| structs/option | 0 |
| vectors | 2 |
| **total** | **11** |

**amplified**

| class | count |
|---|---|
| arithmetic/loops | 10 |
| strings | 0 |
| structs/option | 0 |
| vectors | 2 |
| **total** | **12** |

### removal_rebuild

**reference**

| class | count |
|---|---|
| arithmetic/loops | 0 |
| strings | 0 |
| structs/option | 0 |
| vectors | 2 |
| **total** | **2** |

**amplified**

| class | count |
|---|---|
| arithmetic/loops | 0 |
| strings | 0 |
| structs/option | 0 |
| vectors | 0 |
| **total** | **0** |

### string_build

**reference**

| class | count |
|---|---|
| arithmetic/loops | 0 |
| strings | 1 |
| structs/option | 0 |
| vectors | 0 |
| **total** | **1** |

**amplified**

| class | count |
|---|---|
| arithmetic/loops | 0 |
| strings | 1 |
| structs/option | 0 |
| vectors | 0 |
| **total** | **1** |

### sum_scan

**reference**

| class | count |
|---|---|
| arithmetic/loops | 2 |
| strings | 0 |
| structs/option | 0 |
| vectors | 2 |
| **total** | **4** |

**amplified**

| class | count |
|---|---|
| arithmetic/loops | 6 |
| strings | 0 |
| structs/option | 0 |
| vectors | 5 |
| **total** | **11** |

## Ranked demand (v04-campaign, REJECTION-CROSSED)

| family | total rejected | total present |
|---|---|---|
| ranges | 84 | 231 |
| compound_assign | 73 | 230 |
| sum | 23 | 38 |
| sort | 10 | 40 |
| option | 3 | 9 |
| contains | 0 | 0 |
| index_assign | 0 | 0 |
| minmax | 0 | 5 |
| strings | 0 | 0 |

## Ranked demand (v04-amp, REJECTION-CROSSED)

| family | total rejected | total present |
|---|---|---|
| compound_assign | 308 | 660 |
| ranges | 223 | 462 |
| option | 166 | 216 |
| sort | 41 | 82 |
| minmax | 24 | 70 |
| contains | 20 | 29 |
| index_assign | 18 | 18 |
| sum | 14 | 14 |
| strings | 3 | 3 |

