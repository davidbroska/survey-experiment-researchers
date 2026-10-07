# Participant-term assessment: corrected and superseded

The initial assessment found relevant survey experiments described using “participants,” including [Bearing the burden of peace](https://doi.org/10.1111/pops.13008). The requested expansion has now been executed with the additional survey, embedded-experiment, text-assignment, and information-experiment phrases. See the [complete revision and retrieval comparison](QUERY_REVISION.md).

The initial diagnostic queries placed `AND NOT` before the publication filters. Under the [documented Scopus precedence rules](https://dev.elsevier.com/sc_search_tips.html), this can put those filters inside the negated expression. Those initial totals must therefore not be interpreted as properly restricted 2010–2026 journal-article yields. The correction groups all positive criteria and publication filters before applying `AND NOT` to the original context terms.

| Diagnostic family | Initial count with ambiguous filter placement | Correctly filtered count |
|---|---:|---:|
| contextual_design | 193 | 154 |
| survey_information | 50 | 47 |
| survey_wording | 1 | 1 |
| text_assignment | 395 | 340 |

These corrected totals describe global family-specific searches for participant terminology without the original three context terms. They overlap with other retained query branches and are not the incremental yield of the complete revised search. The initial first-page examples remain exploratory observations, not a precision sample. [Corrected queries, counts, and dates](results/participant_term_probe_corrected_counts.csv) and the [initial request provenance](results/participant_term_probe.csv) are retained for audit.

The full revision instead retrieves positive query families, completes pagination, and computes overlap and differences from article IDs locally. This avoids negative-query precedence ambiguities. It also demonstrates that broad information-treatment language plus `participant*` can retrieve clinical studies, including matches spanning punctuation. The local verification and eligibility review in the revision report are necessary before these results enter researcher rankings.
