# Recruitment ranking: methodological assessment

**Recommendation:** retain the 9,675-article union of the core and complete proximity clause as the discovery pool. Use the 9,365-article narrower union to prioritize screening and display ranking sensitivity. Current evidence does not justify treating its 310 removals as ineligible research. Neither query establishes a definitive ranking of survey experimentalists or data donors.

## What the comparison establishes

The narrower clause removes only `read W/3 passage*` and `manipulat* W/3 information`; it adds no exclusions, author names or research topics. Complete Scopus identifier comparisons verify set inclusion. After intersection with the frozen 3,401-journal frame and canonical DOI deduplication:

| Retrieval set | Articles | Additions beyond the 8,615-article core |
|---|---:|---:|
| Core plus complete proximity clause | 9,675 | 1,060 |
| Core plus narrower proximity clause | 9,365 | 750 |
| Removed from the combined discovery pool | 310 | 310 |

The change removes 3.2% of the complete union but 29.2% of the proximity route's additions beyond the core. The standalone proximity clause loses 330 articles; 20 remain in the union because the core also retrieves them. These are measured retrieval differences, not measured changes in precision or recall. Sources: [complete membership](../proximity_specific_2026_09_10/membership.csv), [set comparison](../proximity_specific_2026_09_10/retrieval_comparison.csv) and [development protocol](../proximity_specific_2026_09_10/protocol.json).

## What is known about the removed articles

The fixed 60-article full-text benchmark contains eight of the 310 removals. At the original development stage, five had two completed AI-assisted reviews: four were judged outside the broad survey-experiment definition, while one was judged a survey experiment but incompatible with the current parser because it involved an interactive news network. Three were unavailable at that stage. Across all 18 accessible benchmark articles, narrowing retains 12 of 13 broad design positives and one of five negatives; it retains all 11 positives remaining after the recorded parser-incompatibility flags. The retained negative is a synthesis/simulation article retrieved by the core. See [article decisions](../precision_benchmark_2026_09_10/article_consensus.csv) and [retention table](../proximity_specific_2026_09_10/exposed_benchmark_summary.csv).

This motivated the narrower clause, so it is **post-hoc development evidence**. At that development stage, only 18 of the fixed 60 articles were accessible, and the labels have not been human validated. The apparent improvement among those 18 cannot estimate population precision; unavailable articles are not negatives. It also cannot establish recall, which requires eligible articles outside the retrieved set.

Other existing evidence cautions against blanket removal. Matching canonical Scopus identifiers/DOIs finds no removed articles in the previously coded 160- or 100-article metadata samples. Matching the inherited development corpora finds ten distinct removals: two investigator-corpus articles, both previously labelled survey experiments, and eight term-corpus articles, five labelled yes and three no. These convenience corpora and their AI labels are not a representative audit. Nevertheless, the removed cases include:

| Article | Existing development evidence requiring review |
|---|---|
| *The heart behind the art: Motives for making art and how they influence audience appreciation* (Scopus 105034183699) | Experimental variation of information about artists' motives, followed by audience judgments. |
| *Gender Norms, Dominance Theory, and the Endorsement of Aversive Training Methods With Pet Dogs* (105038898483) | Information manipulation and reported endorsement outcomes. |
| *Defending or defying democracy?* (105048615569) | Fictitious-vignette manipulations with democratic-attitude outcomes. |

These are screening leads, not newly confirmed donation-compatible studies. The ten-record diagnostic uses `is_survey_experiment` from `Opencall/QueryV2/positives/results/` and `termeval/results/`, joined through their respective `mining_input.csv` and `term_samples.csv`; definitions and parser suitability differ from current eligibility rules. Titles and prior labels do not establish data possession. Removing the two pairs therefore changes coverage of plausible social-attitude experiments as well as cognitive/motor studies. We cannot quantify that trade-off without reviewing more of the 310.

## Ranking researchers defensibly

Compute candidate first/last-author counts from the **entire discovery pool**, deduplicating each article once per author, including a sole author only once. Displaying the top 100 is a presentation choice; it must not define eligibility for US-sample annotation or the US ranking. Until design screening is complete, label these as *candidate survey-experiment articles*. Show the two query versions' counts and rank changes as sensitivity results, without interpreting stability as proof of validity. Keep equal counts tied; an arbitrary display order should not imply evidence of greater experience.

For recruitment decisions, distinguish confirmed eligible articles, pending articles, parser compatibility, original data collection and evidence of access to the data. An article may contain one compatible experiment alongside other designs; a broad design-positive label alone does not settle these other questions. Article counts measure publications, not independent datasets. Panel-vendor or nationally representative recruitment does not by itself identify who controls or can donate the data.

First/last authorship is the requested proxy for seniority and PI involvement, not verification of either. Alphabetical ordering, co-first/co-last authorship and middle-author PIs can produce field-dependent omissions. Retain the count rule consistently, supplement invitation decisions with contribution/role evidence, and audit author identifiers rather than merging people by name alone. The TESS-derived journal frame, journal-article document filter and 2010–2026 window also bound coverage; a rank is conditional on this frame and the retrieval strategy, not on all social-science research. Additional bibliography screening, if adopted, should use the same eligibility trigger for every candidate, rather than special treatment of diagnostic names.

US counts require article-level sample geography, separate from institutional country. Preserve explicit, inferred and unresolved evidence internally even if the dashboard combines the first two. Report annotation coverage and unresolved eligible articles alongside the known US count; missing geography is not evidence of a non-US sample. A US ranking limited to a previously selected overall top 100, or to articles prioritized for breaking its ties, cannot identify the top US-sample researchers across the expanded pool. Use the full candidate pool and disclose incomplete coverage; known-US counts and possible additional US counts can indicate rank uncertainty while screening continues.

Complete the fixed benchmark where possible. An independent evaluation of the narrower candidate also needs a fresh, prespecified probability sample of retained and removed articles, excluding development records, with human adjudication and separate design/parser/data-access decisions. Sampling only the removed articles can characterize losses but cannot establish the narrower query's precision. Broad candidate discovery followed by documented eligibility review is defensible now; the narrower query remains a workload and sensitivity tool until fresh evidence supports a stronger claim.

The later user-download round increased acquisition to 45 of the fixed 60 articles, all with two AI-assisted reviews (35 design positives, nine negatives and one unresolved). All eight sampled removals are now reviewed: six design negatives and two design positives, all with parser-incompatible judgments. The narrower query retains all 27 reviewed articles judged both design-positive and parser-compatible. This supports prioritizing the narrower set for review without establishing population precision or ruling out eligible losses among the other removals. The additional reviews and the immutable original 18-stage labels are reported separately in the [updated ranking comparison](../../RANKING_COMPARISON_REPORT.html) and [combined review summary](../benchmark_review_wave2_2026_09_10/review_summary.json). Completing this original sample does not retroactively make the narrower query an independently prespecified validation target.
