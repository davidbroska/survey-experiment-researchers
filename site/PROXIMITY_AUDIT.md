**Archived query-development stage (18 full-text reviews).** See the [latest ranking comparison, discovery query and recommendation](RANKING_COMPARISON_REPORT.html) and [updated full-text inventory](FULLTEXT_BENCHMARK.html) for the subsequent evidence.

**The proposed clause recovers relevant social-psychology experiments, but it does not resolve all missing work.** Scopus returns 1,791 journal articles globally and 1,297 within the existing 3,401-journal frame for 2010–2026. Adding it to the 8,142-article expanded search yields 9,208 distinct articles (+1,066, no losses); adding it to the broader 18,054-article candidate search yields 18,834 (+780, no losses). These are retrieval gains, not measured recall.

The clause adds one source-verified eligible last-author article for each nominated researcher: Kurt Gray’s [Equating silence with violence](https://doi.org/10.1016/j.jesp.2022.104348) and Jay Van Bavel’s [Identity concerns drive belief](https://doi.org/10.1177/13684302211030004). The former varies anti-racist message wording and measures threat and resistance; the latter varies partisan messages and measures belief and sharing intentions.

| Researcher | Expanded search: first/last | Prior broad candidate: first/last | Broad candidate + clause: first/last | Shorter targeted query: first/last |
| --- | --- | --- | --- | --- |
| Kurt Gray | 0 | 1 | 2 | 1 |
| Jay J. Van Bavel | 0 | 1 | 2 | 1 |

The counts use complete Scopus bylines and distinct articles, with sole authors counted once. They remain candidate counts. Identity checks distinguished the NYU psychologist from a same-name allergy researcher. We retrieved complete Article bibliographies for Gray (114 records) and Van Bavel (106), then inspected four eligible full-text examples for each. All eight examples are in the journal frame; six fail the proposed clause because the abstract omits its narrow reading/manipulation wording, sometimes describing studies without experimental terminology. One already retrieved Van Bavel paper gives him middle-author status. The named cases diagnose the method and are excluded from precision evaluation. [Identity audit](results/proximity_audit_2026_09_10/author_identity_audit.csv) · [Eight full-text examples](results/proximity_audit_2026_09_10/author_fulltext_examples.csv) · [Article-by-article retrieval](results/proximity_audit_2026_09_10/author_article_retrieval.csv).

The repeated proximity expressions can be grouped without changing retrieval. Both full global result sets contain the same 1,791 Scopus IDs, and both directional difference checks return zero. The [official Scopus syntax](https://dev.elsevier.com/sc_search_tips.html) permits OR groups within proximity expressions. The equivalent clause is:

```text
TITLE-ABS-KEY(experiment*)
AND ABS((read W/3 (vignette* OR scenario* OR passage* OR message* OR article* OR news)) OR (manipulat* W/3 (vignette* OR scenario* OR message* OR information OR wording)))
AND ABS(survey* OR questionnaire* OR respondent* OR participant*)
```

Keep the read and manipulation material groups separate: merging both verbs with every material would add combinations that were not requested. W/3 permits either word order and does not ensure that the words describe the same study. The double-quoted design labels below are loose Scopus phrases; punctuation-sensitive evidence checks remain a separate screening step. Live probes show that read does not match an abstract containing only reading; read* also reaches readiness. We therefore preserve the requested read token in this test. [Complete-set equivalence](results/proximity_audit_2026_09_10/grouping_equivalence.json) · [Syntax probes](results/proximity_clause_semantics_2026_09_10/live_probes.csv).

**First tested shorter candidate:** retain the previous named-design, contextual-design and randomized-reading core, and add the grouped clause. This identifies articles through recognizable design labels or specific reading/manipulation procedures. It removes the previous broad combination of experimental, material and outcome words. The result contains 1,525 characters after normalizing whitespace, versus 1,733 in the preceding broad candidate (12% shorter) and 4,688 in the long expanded query (67% shorter). It retrieves 9,675 candidates: all 8,615 previous core candidates plus 1,060 additional articles. Compared with the prior 18,054-article broad candidate, it adds 780 and omits 9,159. Some omitted articles are eligible; the narrower query is a primary discovery route, not a replacement for archived evidence. A more compressed two-block alternative has 954 characters and retrieves 8,839, but loses 836 core candidates. Earlier reviewed positives are among the losses, so shortening to that extent is not recommended. The core-plus-clause query misses 28 records from the older 8,142-article search; retain both those records and the broader archived candidates for screening. The shorter query yields one first/last candidate for each focal researcher, whereas adding the clause to the broader search yields two each. Full-text eligibility, parser compatibility and original data collection must be checked separately before ranking. [Retrieval comparison](results/proximity_audit_2026_09_10/retrieval_comparison.csv) · [Original tested candidate query](queries/proximity_audit_2026_09_10/targeted.txt).

```text
(
  (TITLE-ABS-KEY("survey experiment*" OR "survey based experiment*" OR "survey embedded experiment*" OR "experimental survey*" OR "vignette experiment*" OR "experimental vignette*" OR "vignette based experiment*" OR "vignette based survey*" OR "factorial survey*" OR "randomized vignette*" OR "randomised vignette*" OR "question wording experiment*" OR "experiment* embedded in a survey" OR "experiment* embedded in an online survey" OR "experiment* within a survey" OR "experiment* within an online survey" OR "experiment* in a survey" OR "experiment* in an online survey" OR "survey based random* experiment*"))
  OR (TITLE-ABS-KEY("framing experiment*" OR "information provision experiment*" OR "scenario based experiment*" OR "information treatment*" OR "informational treatment*" OR "information experiment*" OR "wording experiment*" OR "embedded experiment*") AND TITLE-ABS-KEY(survey* OR questionnaire* OR respondent* OR participant*) AND TITLE-ABS-KEY(random* OR experiment*))
  OR (TITLE-ABS-KEY("random* assign* to read" OR "random* allocat* to read" OR "random* select* to read" OR "random* to read") AND TITLE-ABS-KEY(survey* OR questionnaire* OR respondent* OR participant*))
  OR (TITLE-ABS-KEY(experiment*)
AND ABS((read W/3 (vignette* OR scenario* OR passage* OR message* OR article* OR news)) OR (manipulat* W/3 (vignette* OR scenario* OR message* OR information OR wording)))
AND ABS(survey* OR questionnaire* OR respondent* OR participant*))
)
AND SRCTYPE(j) AND DOCTYPE(ar) AND PUBYEAR > 2009 AND PUBYEAR < 2027
```

**Full-text evaluation set.** We froze 60 articles before checking access: 20 found only by the previous core, 20 found only by the proposed clause, and 20 found by both. The sample excludes inherited development material, the preceding 160-article and 100-article reviews, previously reviewed full texts, the loss audit, and all four nominated authors’ bibliographies. The remaining sampling populations are shown below; equal sample sizes require unequal stratum weights. The target is this previously unreviewed subset, not every retrieved article or all survey experiments.

| Sampling stratum | Unreviewed population | Fixed sample |
| --- | --- | --- |
| primary_only | 6792 | 20 |
| proximity_only | 882 | 20 |
| overlap | 134 | 20 |

We acquired readable, identity-verified main texts or author manuscripts for 18/60 selected articles; 42 still need a usable copy. Missing articles were not replaced. Source versions, PDF hashes, page-indexed text, acquisition attempts and access failures are recorded. Accepted or author manuscripts may require comparison with the version of record before final validation. Two independent AI coding passes completed 18 articles: 13 affirmative design agreements, 5 negative agreements and 0 unresolved judgments. Design, original data, text modality, parser compatibility, sample geography and data possession are separate axes. Both coders cite actual PDF pages; evidence spans and source hashes are checked. The packets omit search routes and prior labels, although authors remain visible in the papers. These are working AI-assisted annotations, not human-validated reference labels.

| Sampling stratum | Fixed sample | Full texts double-coded | Eligible | Ineligible | Still unresolved |
| --- | --- | --- | --- | --- | --- |
| primary_only | 20 | 6 | 5 | 1 | 14 |
| proximity_only | 20 | 8 | 4 | 4 | 12 |
| overlap | 20 | 4 | 4 | 0 | 16 |

Among the available papers found only by the new clause, four were eligible and four were not. The false positives include motor tracking, reading-comprehension testing and cognitive training: participants can read passages or receive manipulated information without taking part in a survey experiment. The primary-only negative was a cost-effectiveness simulation and evidence synthesis about survey experiments. Thus neither a specific design label nor the new procedural clause is a sufficient inclusion rule.

**Recommended next validation candidate.** Following this review, we tested a separate development revision that removes only read W/3 passage* and manipulat* W/3 information from the added clause. The other nine pairs, population gates and earlier core are unchanged. The narrower clause returns 967 in-frame articles; the complete revised query returns 9,365, adding 750 to the 8,615-article core without losing core records. Against the earlier broad candidate, it adds 491 and omits 9,180; archived candidates therefore remain a separate screening queue. Both focal researchers retain their new last-author article. Within the 18 exposed full texts, the revised query retains 12 of 13 design-positive articles and one of five negatives. The omitted positive uses an interactive news network and was marked parser-incompatible by both reviewers. The other 305 removed articles were not assessed in this full-text exercise. Among the 12 retained positives, parser judgments are eight compatible, one incompatible and three unclear; this revision does not establish parser eligibility. This result motivated a narrower primary discovery route, but it is a post-hoc observation on an availability-limited set: these 18 papers are now development evidence for the revision, not independent validation. A fresh, prespecified evaluation is needed before claiming its precision. No negative keyword filters were introduced. The full revised query has 1,498 whitespace-normalized characters. [Development protocol and set comparison](results/proximity_specific_2026_09_10/development_summary.md) · [Download the next validation query](queries/proximity_specific_2026_09_10/primary_plus_specific.txt).

```text
(
  (TITLE-ABS-KEY("survey experiment*" OR "survey based experiment*" OR "survey embedded experiment*" OR "experimental survey*" OR "vignette experiment*" OR "experimental vignette*" OR "vignette based experiment*" OR "vignette based survey*" OR "factorial survey*" OR "randomized vignette*" OR "randomised vignette*" OR "question wording experiment*" OR "experiment* embedded in a survey" OR "experiment* embedded in an online survey" OR "experiment* within a survey" OR "experiment* within an online survey" OR "experiment* in a survey" OR "experiment* in an online survey" OR "survey based random* experiment*"))
  OR (TITLE-ABS-KEY("framing experiment*" OR "information provision experiment*" OR "scenario based experiment*" OR "information treatment*" OR "informational treatment*" OR "information experiment*" OR "wording experiment*" OR "embedded experiment*") AND TITLE-ABS-KEY(survey* OR questionnaire* OR respondent* OR participant*) AND TITLE-ABS-KEY(random* OR experiment*))
  OR (TITLE-ABS-KEY("random* assign* to read" OR "random* allocat* to read" OR "random* select* to read" OR "random* to read") AND TITLE-ABS-KEY(survey* OR questionnaire* OR respondent* OR participant*))
  OR (TITLE-ABS-KEY(experiment*)
AND ABS((read W/3 (vignette* OR scenario* OR message* OR article* OR news)) OR (manipulat* W/3 (vignette* OR scenario* OR message* OR wording)))
AND ABS(survey* OR questionnaire* OR respondent* OR participant*))
)
AND SRCTYPE(j) AND DOCTYPE(ar) AND PUBYEAR > 2009 AND PUBYEAR < 2027
```

Availability and partial coding do not establish high query precision. The benchmark retains all 60 records in the accounting and reports stratum-weighted missing-label bounds instead of treating the accessible subset as representative. Complete the missing full texts and obtain independent human adjudication before reporting precision in a manuscript. Even a complete precision evaluation would not estimate recall; that needs an independently assembled positive reference set or an audit of unmatched articles. [Full-text inventory and download workflow](FULLTEXT_BENCHMARK.html) · [Fixed sample](results/proximity_audit_2026_09_10/fulltext_sample.csv) · [Working labels](results/precision_benchmark_2026_09_10/article_consensus.csv) · [Missing-label bounds](results/precision_benchmark_2026_09_10/missing_label_bounds.csv).

A separate byline check found a Scopus record that lists a PNAS handling editor as the final author. The published byline instead ends with Van Bavel. That article-specific discrepancy is preserved as an audit finding; it does not establish another eligible experiment or change the ranking. [Raw and publisher-verified bylines](results/proximity_audit_2026_09_10/author_byline_discrepancies.csv).

The dashboard continues to show its earlier provisional cohort. No researcher names, substantive topic requirements, vendor restrictions, or explicit conjoint/split-ballot exclusions were added to the query. The reproducible stages are python3 pipeline/proximity_audit.py summarize, python3 pipeline/proximity_audit.py author_comparison, python3 pipeline/precision_benchmark_review.py, and python3 pipeline/proximity_report.py. Licensed metadata, PDFs and verbatim evidence stay under private/. [Coauthor summary](PROXIMITY_SUMMARY.html) · [SI draft](PROXIMITY_METHODS.html) · [Earlier search audit](SEARCH_STRATEGY.html) · [Dashboard](TOP100.html#summary).
