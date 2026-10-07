# SCORE screening pilot: findings, 7 October 2026

This report records the completed 288-paper source-review snapshot. Later
downloads expand the local validation collection; they do not change these
reference labels or frozen predictions. See the [current access report](access_report.md)
for acquisition progress and the [proposed prompt edits](prompt_proposed_redline.md)
for the subsequent, untested clarification.

Use the [original prompt with the primary-survey definition](prompt_current.md)
as a provisional screen, retaining collection YES and UNCLEAR. The tested
[revision](prompt_revised.md) did not improve collection retention in the reviewed
holdout and substantially increased review workload. It should not replace the
original on this evidence. Neither version is a validated final exclusion rule.

## What was completed

The frozen sample contains **620 articles: exactly one per journal and year in
62 SCORE journals, 2016–2025**. Matching existing articles fill their eligible
slots; remaining selections use seeded random draws within journal and year.
There are no geographic, experimental-design or collection-keyword filters.
The study window remains 2016–2026; this pilot excludes incomplete 2026.

Scopus supplied 618 records. Two World Politics cells, 2024 and 2025, required
Crossref records because the Scopus journal queries returned no articles.
There are 612 abstracts, 441 keyword records and author lists for all 620 papers.
The supplied journal list required three electronic ISSN corrections; the
[journal audit](journal_audit.csv) and [sample validation](sample_validation.json)
document these. The two proposed additions are excluded.

All 620 received metadata-only original-prompt decisions. Before tuning, 124
papers were reserved as holdout, two per journal. The 17 previously inspected
papers were kept in development. The revised candidate was
frozen after development review, then applied to all 124 using the same metadata
without access to their full texts or reference labels. No paid LLM API calls
were used: these are session-agent judgments.

Retrieval was attempted for every selected paper. **288 main articles were
obtained and substantively reviewed**: 157 PDFs and 131 publisher/repository XML
documents, covering 51 of the 62 journals. These comprise 239 development and
49 holdout papers. The 332 other papers remain unresolved for access; unavailable
text is never coded as ineligible. All final retrieval receipts represent real
network requests; publisher HTTP 403 responses were the dominant obstacle.
Stanford access supported Scopus metadata and some Elsevier full text, but did
not provide automated access to every publisher.

Primary source review assessed all reported studies, including pilots and
supporting studies, team responsibility for collection, and the experiment and
primary-survey boundaries. Supporting methods, repositories and project records
were checked where needed. Source files, hashes, locations, short exact evidence
and adjudication histories are retained privately; the public
[reviews](independent_review.csv) contain derived labels and paraphrases.
The final collection reference labels are **189 YES, 98 NO and 1 UNCLEAR**.
These are AI source assessments; **none has yet been RA verified**.

## Held-out comparison

These results use the same **49 source-reviewed holdout articles**, including
32 eligible and 17 ineligible collection cases. “Retained” means metadata YES
or UNCLEAR; specificity is the fraction of ineligible cases assigned NO.

| Decision | Original: eligible retained | Candidate: eligible retained | Original: ineligible discarded | Candidate: ineligible discarded |
|---|---:|---:|---:|---:|
| Collection | 32/32 (100%) | 32/32 (100%) | 16/17 (94.1%) | 8/17 (47.1%) |
| Experiment | 23/23 (100%) | 23/23 (100%) | 21/26 (80.8%) | 11/26 (42.3%) |
| Primary survey | 19/21 (90.5%) | 18/21 (85.7%) | 25/28 (89.3%) | 16/28 (57.1%) |

Across all **124** held-out predictions, the original retains 79 (63.7%) for
collection review, versus 104 (83.9%) for the candidate. Collection UNCLEAR rises
from 27 to 51. Among the 49 reviewed cases, all eight additional retained cases
are ineligible according to source review. The candidate's conservative rule
therefore increases work without recovering an additional eligible collection
case in this subset.

Positive collection predictions agree with the AI reference in 22/22 original
and 23/23 candidate cases. These small, selected denominators do not establish
perfect population precision or recall. The remaining 75 holdout articles lack
reference reviews. Full three-by-three tables, definite-YES recall, abstention,
unresolved counts and denominators are in [evaluation.json](evaluation.json).

## What the detailed review changed

The original screen misses **7 of 157 eligible development papers** when NO is
discarded, retaining 150/157 (95.5%). It discards 66/81 ineligible development
papers. These development cases motivated the candidate; they are not an
independent validation of its changes.

Two misses demonstrate an information limit: papers whose abstracts emphasize
TED/Twitter records (Scopus 85101686392) and Super Bowl advertising records
(85064119805) also report newly collected participant ratings in their full
texts. A broad rule treating archival-looking abstracts as UNCLEAR avoids
overconfident exclusion but also admits many purely archival papers.

Team provenance needs particular care. Official project documentation established
collection roles in the ManKobE and TIMSS-Transition studies; an ALSPAC collection
grant identified a sampled coauthor as principal investigator. Other papers
mixed external surveys with the team's earlier experiments. These decisions
required more than detecting a familiar dataset or overlapping author name.
For the school-reopening/SOSS article (85115710111), the specific collection role
remains undocumented, so collection remains UNCLEAR.

Survey counts are especially sensitive to omitted subsidiary studies. The
original misses two eligible survey cases in the holdout; the candidate misses
those plus one more. Independent rechecks confirmed primary questionnaire or
vignette studies in all three (85006973897, 85191794805, 85048490203). Conversely,
incidental clinical scales, task ratings and demographic questionnaires do not
qualify under the user's primary-survey definition. A distinct primary-survey
pilot can qualify. Do not interpret a metadata survey NO as a reliable final
count of a researcher's survey publications.

## Interpretation and next use

This is a hybrid pilot, retaining existing articles and weighting journal-years
equally. Only 46.5% of its articles have reviewed full text, with substantial
journal and publisher differences. [Coverage](coverage.csv) separates availability
by journal, year and original metadata decision. Performance among available
papers cannot be extrapolated to the 332 inaccessible papers or to researcher
prevalence. Metadata reviewers and contexts also partly differ between versions;
this comparison cannot isolate a causal effect of prompt wording or predict
performance of a future API model configuration.

Keep the frozen holdout and failed candidate as research records. Retain YES and
UNCLEAR for recruitment screening; audit NO decisions before using them as
final exclusions, particularly when supporting collection or earlier team
collection may be omitted. Further prompt changes need new evaluation data.
An author-level invitation ranking has not been inferred from this small pilot.

The [RA protocol](ra_verification.md) accompanies a local blinded packet:
**62 random cases across the 51 accessible journals**, plus **20 separate targeted
cases**. The random packet contains 32 collection YES and 30 NO cases; the
targeted packet includes the unresolved case. Labels are hidden from reviewers. Selection
probabilities and the AI key are kept separately. Verification should assess
the primary AI source work; no assignments have been sent.

The [manual download queue](manual_downloads.csv) lists the 332 outstanding
articles. Additional entitled PDFs can be imported locally, then reviewed and
added without changing the frozen article sample or metadata predictions.
Main texts and supporting documents remain under `Literature/SCORE` outside
the public repository. The earlier [TESS dashboard](../archive/tess/DASHBOARD_NARROWER.html)
and source snapshot are preserved separately.
