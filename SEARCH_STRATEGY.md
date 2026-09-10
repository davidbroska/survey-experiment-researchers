**The counterexamples expose systematic omissions. A keyword match should identify a candidate article; eligibility review should determine whether it earns ranking credit.** Broadening the query alone creates substantial false positives. Use named designs and reading assignments as the main discovery route; treat the broader procedure block below as a separately screened supplement. The tested union is not sufficiently precise for automatic ranking.

Pennycook is in the complete current ranking with two first/last-author articles (shared score rank 984; deterministic display position 1,400), below the six-article top-100 cutoff. Six of his articles were retrieved; four place him in the middle of the byline. Richeson has no matches, although all 69 of her Scopus journal articles dated 2010–2026 are in the journal frame. These are not missing-journal or name-spelling problems. Among the 20 supplied examples, five Pennycook papers give first-author credit and nine Richeson papers give last-author credit. Primary-source review supports four clear first-author Pennycook examples and eight clear last-author Richeson examples; one of the latter falls outside the Article filter, leaving seven in scope. These AI-assisted judgments still require validation. The examples are development challenges, not an unbiased recall benchmark.

| Researcher | Current credited articles | Refined query: first/last candidates | Refined query: any author position |
| --- | --- | --- | --- |
| Gordon Pennycook | 2 | 7 | 20 |
| Jennifer A. Richeson | 0 | 1 | 2 |

The refinement improves Pennycook’s retrieval but still finds only one first/last candidate for Richeson. This is evidence against using even the refined query as a complete productivity measure. Richeson warrants inclusion in candidate review on the documented evidence; a final rank requires the same bibliography and eligibility checks for everyone.

The refined query retrieves 8/20 challenge papers under the document-type and year restrictions; this is coverage of a supplied list, not estimated recall. Some clear examples omit even experimental terminology from their indexed abstract. One supplied Richeson example involves an in-person video/interviewer intervention, and other examples combine several study types. They should not all be treated as uncomplicated parser-ready positives. [Paper-by-paper retrieval audit](results/search_strategy_2026_09_10/counterexample_retrieval.csv) · [Primary-source design audit](results/design_audit_2026_09_10/counterexample_source_audit.csv).

The full methods of Majority No More? report original randomized experiments, but its Scopus record is classified as Review and fails DOCTYPE(ar). The [author manuscript](https://spcl.yale.edu/media/138/download?inline=) and the archived DOI lookup document this exception. Conversely, some records classified as Article are reviews or secondary analyses. Document type is a retrieval filter, not an eligibility decision.

The existing local matcher also rejects 196 records with intact design phrases and the required context elsewhere: 171 elsewhere within a field and 25 across fields. This differs from a false phrase such as survey followed by a comma or full stop and experimental. Literal phrase integrity and the relationship between a study's design and sample need separate checks. [Local-filter diagnostic](results/design_audit_2026_09_10/local_guard_diagnostic_counts.json).

We compared three short discovery alternatives, reviewed 160 fresh records in four disjoint strata, and then froze a refinement. The new sample excluded the inherited development data, nominated authors and challenge papers. Each stratum below contains 40 articles; pooling these equally sized strata would misrepresent their different population sizes.

| Development stratum | Affirmative design evidence | Not eligible | Unclear |
| --- | --- | --- | --- |
| concepts_beyond_exposure | 5 | 32 | 3 |
| exposure_beyond_labels | 13 | 22 | 5 |
| named_design | 36 | 4 | 0 |
| previous_only | 35 | 5 | 0 |

The broad concept and exposure variants were too noisy. The refinement retains productive named designs and randomized reading assignments, requires title/abstract evidence for its broader procedure route, uses a human-context gate, and avoids the ambiguous perception/preference and text-prefix terms in that branch. The term text* can reach words such as texture; the revised branch uses text, textual and written. These changes concern research methods rather than the topics or names of the nominated researchers.

The requested addition of participant* to the framing/scenario and embedded-survey clauses separately increases the expanded query from 8,074 to 8,142 distinct in-frame articles (+68, no losses). The embedded-survey change adds none because every phrase already contains survey. [Complete participant-expanded query](queries/participant_guards_2026_09_10/revised.txt) · [Comparison](results/participant_guards_2026_09_10/retrieval_comparison.csv).

The compact candidate contains 2,019 characters versus 4,706 in that expanded query. It retrieves 18,054 distinct articles in the 3,401-journal frame: 9,926 additions and 14 losses relative to the 8,142-article query. These are retrieval changes, not gains in verified experiments. [Full comparison](results/search_strategy_2026_09_10/retrieval_comparison.csv) · [Overlapping route counts](results/search_strategy_2026_09_10/route_counts.csv).

```text
(
  TITLE-ABS-KEY(
      "survey experiment*"
      OR "survey based experiment*"
      OR "survey embedded experiment*"
      OR "experimental survey*"
      OR "vignette experiment*"
      OR "experimental vignette*"
      OR "vignette based experiment*"
      OR "vignette based survey*"
      OR "factorial survey*"
      OR "randomized vignette*"
      OR "randomised vignette*"
      OR "question wording experiment*"
      OR "experiment* embedded in a survey"
      OR "experiment* embedded in an online survey"
      OR "experiment* within a survey"
      OR "experiment* within an online survey"
      OR "experiment* in a survey"
      OR "experiment* in an online survey"
      OR "survey based random* experiment*"
  )
  OR (
    TITLE-ABS-KEY(
        "framing experiment*"
        OR "information provision experiment*"
        OR "scenario based experiment*"
        OR "information treatment*"
        OR "informational treatment*"
        OR "information experiment*"
        OR "wording experiment*"
        OR "embedded experiment*"
    )
    AND TITLE-ABS-KEY(survey* OR questionnaire* OR respondent* OR participant*)
    AND TITLE-ABS-KEY(random* OR experiment*)
  )
  OR (
    TITLE-ABS(experiment* OR random* OR manipulat* OR "control condition*" OR "control group*")
    AND TITLE-ABS(attitud* OR belief* OR opinion* OR intention* OR judgment* OR judgement*)
    AND TITLE-ABS-KEY(participant* OR respondent* OR survey* OR questionnaire* OR human*)
    AND (
      TITLE-ABS(message* OR text OR textual OR written OR vignette* OR scenario* OR headline* OR prompt*)
      OR TITLE-ABS((read* OR view* OR expos* OR present* OR receiv* OR shown) W/5 information)
    )
  )
  OR (
    TITLE-ABS-KEY(
        "random* assign* to read"
        OR "random* allocat* to read"
        OR "random* select* to read"
        OR "random* to read"
    )
    AND TITLE-ABS-KEY(survey* OR questionnaire* OR respondent* OR participant*)
  )
)
AND SRCTYPE(j)
AND DOCTYPE(ar)
AND PUBYEAR > 2009
AND PUBYEAR < 2027
```

The first, second and fourth blocks recognize named designs or reading assignments and together retrieve 8,615 distinct candidates. The third supplies another 9,439 candidates and is a supplementary discovery route. Every route requires eligibility screening before counting. For separate use, download the [named-design and reading query](queries/search_strategy_2026_09_10/primary.txt) and the [procedure supplement](queries/search_strategy_2026_09_10/procedure.txt). These are projections of the frozen query, not terms fitted after validation. The quoted phrases are loose Scopus phrases; wildcards abbreviate word endings. [Elsevier documents this syntax](https://www.elsevier.support/scopus/answer/how-can-i-best-use-the-advanced-search). Our [cached punctuation probes](results/query_revision_2026_09_10/field_checks.csv) also show that braces cannot be relied on to eliminate every punctuation-boundary match. No researcher names, topic terms, vendor restrictions or explicit design exclusions appear in this candidate.

Two separate AI coding passes reviewed a fixed, disjoint sample of 100 candidate articles. They agreed on affirmative design evidence for 65, agreed that 29 were not eligible survey designs, and left 6 uncertain or disputed. After flagging designs that either coder identified as incompatible and records described as secondary-only, 60 remained affirmative candidates. This is not confirmation of parser support or data ownership. All labels remain AI-assisted and require independent human validation.

| Held-out subgroup | Reviewed | Both affirmative | Both negative | Unresolved | After known incompatibility flags |
| --- | --- | --- | --- | --- | --- |
| named_design_or_reading | 41 | 36 | 3 | 2 | 34 |
| procedure_only | 59 | 29 | 26 | 4 | 26 |

The two AI passes agreed on the three-way design classification in 96% of cases. This agreement is not an estimate of truth, and shared errors remain possible. The held-out sample concerns candidate articles outside development material, not all retrieved articles or all survey experiments. [Both coding passes and consensus](results/search_strategy_2026_09_10/validation_consensus.csv) · [Unresolved survey-design cases](results/search_strategy_2026_09_10/validation_unclear_queue.csv). This queue concerns design uncertainty; parser support or original data collection can remain uncertain even for affirmative designs.

Preserve the 14 candidates absent from the new query for screening; the union with the previous search contains 18,068 distinct articles. A separate post-validation [review of all 14 losses](results/search_strategy_2026_09_10/lost_record_review.csv) judged 13 eligible and one outside the target. Several describe outcomes as ratings, perceptions, acceptability or willingness to pay, illustrating the cost of narrowing outcome vocabulary. These additional AI-assisted judgments informed retention, not changes to the frozen query. Query revision should not silently erase prior evidence.

Before rebuilding the ranking, confirm study eligibility across this corpus and apply the same first/last rule to everyone. Define a candidate pool from eligible first/last authors and the existing TESS investigator roster, then check their complete 2010–2026 journal bibliographies before truncating to 100 researchers. Retain the same journal frame; log document-type exceptions for review rather than silently changing filters. Bibliography completion can recover studies whose abstracts omit search vocabulary, but cannot prove coverage of researchers absent from both discovery and the roster. Audit a random sample of unmatched articles within the frame to assess remaining omissions. Report screening coverage and uncertainty rather than treating unreviewed papers as zero. A missing search match is not evidence that a researcher lacks data. The current dashboard remains the documented, provisional earlier cohort. [Concise coauthor note](SEARCH_SUMMARY.html) · [Supporting-information draft](SEARCH_METHODS.html) · [Dashboard methodology](TOP100.html#summary).

Reproduce cached search comparisons with python3 pipeline/design_audit.py summarize and python3 pipeline/search_strategy.py summarize; reproduce coding checks with python3 pipeline/design_audit_report.py development and python3 pipeline/search_strategy_review.py; then run python3 pipeline/search_strategy_report.py. Licensed metadata are required for evidence-span validation and remain private. The public files contain query text, hashes, memberships, bibliographic metadata, original annotation rationales and summary counts.
