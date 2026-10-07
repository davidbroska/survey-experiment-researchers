# Post-benchmark development ablation

This additional candidate removes only two positive pairs from the proposed proximity clause: `read W/3 passage*` and `manipulat* W/3 information`. All other pairs and gates are preserved. The change was motivated after full-text review and is therefore development work, not a validated improvement. Earlier frozen queries, the 60 selected articles, and both sets of annotations were preserved.

Complete Scopus STANDARD retrieval gave 1,288 global articles versus 1,791 for the original clause; the new identifier set is a strict subset with no additions. Within the frozen journal frame, after canonical DOI deduplication, the clause retrieves 967 articles versus 1,297 (330 removed).

| Candidate | Unique articles | Change against relevant comparator |
|---|---:|---|
| Existing core OR narrower clause | 9,365 | +750 versus the 8,615-article core; −310 versus core OR original clause |
| Previous broad candidate OR narrower clause | 18,545 | +491 versus the 18,054-article broad candidate |

Within the 18 already reviewed full texts, core OR narrower clause retains 12 of the 13 broad design-positive articles and one of the five design-negative articles. It removes four negative articles about visuomotor or cognitive tasks and one broad positive article about a simulated interactive news network; both reviewers classified the latter as incompatible with the current parser. The retained negative is an evidence-synthesis/simulation article matched by the existing core. These observations describe an exposed, availability-limited subset and cannot establish independent precision or population recall. The remaining 42 selected full texts are unavailable and are not treated as negatives or replaced.

The ablation does not change retrieval of the two diagnostic authors compared with the original proximity clause. Core OR either clause retrieves one first/last-author article each for Kurt Gray and Jay J. Van Bavel. Combining the narrower clause with the earlier broad candidate retrieves two first/last-author articles each. Author checks use all 220 collected bibliography rows, complete-bylines only, and count each canonical article once; these are retrieval counts, not confirmed research-output totals.

The full query texts are in `queries/proximity_specific_2026_09_10/`. Public outputs provide complete membership and article-level set differences without abstracts or quoted full text. `protocol.json` records the development status, exact removed pairs and input/query hashes; `global_set_comparison.json` verifies actual identifier-set inclusion; `offline_reproducibility.json` records byte-identical regeneration of 14 artifacts with network calls disabled. Two focused tests verify that no other query pairs or primary-route content changed.
