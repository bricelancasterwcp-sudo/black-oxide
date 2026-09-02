# wave 9 — re-screen (seeds 1,2,3), read against wave 8

- guard `base-rs-14` pass@1 **0.55** (anchor 0.55, seeds 1-3): **REPRODUCED**
- guard `tune-ox-14` pass@1 **0.7833333333333333** (anchor 0.8, seeds 1-3): **MISSED**

| large tier | compiled | n | rate |
|---|---:|---:|---:|
| tune-ox-14 | 3 | 60 | 0.050 |
| tune-rs-14 | 43 | 60 | 0.717 |

**compile-rate ratio ox/rs = 0.0698** (wave 8: 0.0652; delta None) → **GUARDS-MISSED**

Oxide first-diagnostic mix over 213 failing attempts: `{'OX0101': 77, 'OX0200': 54, 'OX0103': 32, 'OX0100': 29, 'OX0400': 7, 'OX0300': 6, 'OX0001': 4, 'OX0308': 1, 'OX0303': 1, 'OX0205': 1, 'OX0403': 1}`

**OX0001 (lexer) share 0.019** (wave 8: 0.338; confirmed if < 0.15) → **ATTRIBUTION-CONFIRMED**


**A guard did not reproduce.** Per stop 1 the environment or the merge is suspect, and NO RATIO above may be published against wave 8; it is printed for the record only.
