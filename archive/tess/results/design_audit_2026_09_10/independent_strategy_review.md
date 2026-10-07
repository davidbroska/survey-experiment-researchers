# Independent search-strategy review, 10 September 2026

The examples reveal two distinct problems: disciplinary differences in how experiments are described, and differences between finding a relevant expression and verifying an eligible new experiment. A concise search can address the first. Article review is necessary for the second. Neither the present exact-phrase query nor a broader concept query can establish that an author collected the data, has permission to donate them, or used a design the parser can represent.

This review uses the existing, privately stored Scopus metadata. It does not change the published ranking, query, or eligibility decisions. All substantive article assessments below are AI-assisted diagnostic assessments from abstracts; they are not independently validated labels or estimates of precision.

## What the existing data show

The frozen corpus contains 9,111 records worldwide and 7,302 DOI-deduplicated articles in the journal frame. Of the latter, 7,035 satisfy the local exact-phrase rules; 267 do not. The local matcher requires the experimental expression and every additional context condition to occur in the same sentence or individual keyword entry. Scopus instead applies the query's separate `TITLE-ABS-KEY` conditions across the record.

When the exact phrase remains intact but its context conditions can occur elsewhere in the article's title, abstract, or keywords, **196 of those 267 articles acquire a match**. In 171 cases, the phrase and conditions already occur in the same field; 25 require evidence across fields. The remaining 71 have no match under this diagnostic. No article among the 267 has a missing abstract, although indexed keywords were unavailable throughout the archived extraction.

These counts describe text-rule differences, not 196 confirmed false negatives. The diagnostic preserves literal phrases and punctuation; it relaxes only the scope of their contextual guards. The disaggregated file, `local_guard_diagnostic.csv`, contains article identifiers, titles, phrases, and guard locations without distributing abstracts. The family counts overlap:

| Family rescued by article-level guards | Articles |
|---|---:|
| Framing, information-provision, or scenario design | 65 |
| Randomized text assignment | 64 |
| Information treatment | 49 |
| Vignette-based survey | 10 |
| Question wording | 8 |

The arbitrary same-sentence rule creates recognizable misses:

| Article | Available evidence | Why the old local matcher fails |
|---|---|---|
| [Public perception and acceptance of negative emission technologies](https://doi.org/10.1007/s10584-021-03150-9) | Abstract describes an online survey of 693 Swiss citizens and a between-subjects manipulation of three frames. A keyword is “Framing experiment.” | The keyword expression and survey context occupy different fields. |
| [The Effect of Macroeconomic Uncertainty on Firm Decisions](https://doi.org/10.3982/ECTA21004) | A survey of New Zealand firms, randomized information treatments, and a follow-up survey are described in consecutive sentences. | The treatment sentence does not itself contain a survey or respondent noun. |
| [Countering vaccine hesitancy among pregnant women in England](https://doi.org/10.3390/ijerph17144984) | Web-based self-report survey followed by random assignment to disease-risk, myth-busting, or control information; questionnaire outcomes follow. | The random-assignment sentence says participants; the old gate accepts survey, questionnaire, or respondent only in that same sentence. |
| [Half of obsessive-compulsive disorder cases misdiagnosed](https://doi.org/10.4088/JCP.14m09110) | Online vignette-based survey; the following sentence describes eight randomized vignettes and the abstract reports diagnostic judgments. | The phrase and randomization evidence occupy different sentences. |

Some rescued records also demonstrate why simply crediting all 196 would be inappropriate. [Exposure to written content eliciting weight stigmatization](https://doi.org/10.1002/oby.23917) randomizes reading but includes brain scanning and food-image ratings. [Designing Effective and Acceptable Road Pricing Schemes](https://doi.org/10.1007/s10640-021-00564-y) combines information treatments with a discrete-choice design. Both need an explicit design-eligibility decision; the presence of a readable treatment alone does not establish suitability.

## Exact design labels do not establish new data collection

The existing eligibility input, `inputs/article_decisions.csv`, has no completed rows. The geography annotations answer where samples were recruited; they do not validate experimental eligibility or original data collection. Consequently, current article counts are counts of query candidates that pass the local text rule.

Six concrete records in the locally verified candidate set describe reviews or meta-analyses in their available abstracts. These examples were selected to demonstrate the mechanism, not sampled to estimate its prevalence:

- [Field Experiments on Social Media](https://doi.org/10.1177/09637214211054761): reviews methodological innovations, including survey experiments.
- [The use of experimental vignettes in studying police procedural justice](https://doi.org/10.1007/s11292-022-09529-7): systematic review of 20 publications.
- [Corruption Information and Vote Share](https://doi.org/10.1017/S000305542000012X): meta-analysis contrasting field and survey experiments.
- [A Meta-Analysis of Attitudes Towards Migrants and Displaced Persons](https://doi.org/10.1017/S0007123425101075): synthesis of 118 studies.
- [A Meta-analysis of the Relative Effectiveness of the Item Count Technique](https://doi.org/10.1177/0049124119882468): synthesis of 54 studies.
- [Disclosure of sensitive behaviors across self-administered survey modes](https://doi.org/10.3758/s13428-014-0533-4): synthesis of 460 effect sizes.

`DOCTYPE(ar)` therefore does not eliminate all research syntheses. A negative query for review or meta-analysis would also discard mixed articles: [What is the Future of Survey-Based Data Collection for Local Government Research?](https://doi.org/10.1177/10780874231175837) reports both a systematic review and an original survey follow-up experiment. Eligibility should be decided at the article/study level, with a retained evidence trail.

## Recommended design: two retrieval routes, followed by eligibility review

Freeze a concise, general query before evaluating it further:

1. **Recognized design labels:** established survey-experiment and vignette-experiment terminology.
2. **Experimental procedure:** evidence of an experimental design, a communicated stimulus, and an elicited judgment or response.

The second route should combine three conceptual blocks: experimental design (`experiment*`, `random*`, `manipulat*`); communicated stimuli (such as text, messages, information, scenarios, vignettes, headlines, or prompts); and responses (such as beliefs, attitudes, opinions, intentions, preferences, judgments, perceptions, or evaluations). The final implemented query and all token choices should be fixed and archived before the prospective validation sample is drawn. Terms should describe study components, not particular topics, institutions, authors, or platforms.

Do not require the word participant as a universal gate. Abstracts can describe their samples as White Americans, adults, voters, physicians, consumers, or employees. A closed list of population nouns would create another arbitrary language dependence. An exposure verb close to its communicated stimulus can provide a more coherent procedural description than unrestricted article-level co-occurrence. Its word distance is an operational choice to freeze and evaluate; passive wording and descriptions across sentences may still be missed.

**Count-pilot update.** The root audit's live Scopus count probes returned 155,925 global records for the unrestricted concept route, 64,412 with a human-population gate, and 16,477 with exposure-verb–stimulus proximity of five words. These are reported count-pilot results, not independently reproduced results of this offline review, and should be read alongside the root audit's exact archived queries. The unconstrained version creates a substantially greater screening burden. Selecting the proximity variant for prospective evaluation is therefore reasonable; it binds the action to the proposed stimulus and avoids an exhaustive population-noun list. Retrieval volume alone does not establish superior precision. Retain the unrestricted variant as a count-only sensitivity probe, and test the proximity variant's losses against independent examples before adopting it as the final search.

The generic procedure route will retrieve some clinical reading interventions, sensory or memory experiments, analyses of other studies, and articles whose stimulus and outcome concepts belong to different studies. Terms such as perception and evaluation are particularly broad. This is a foreseeable review burden, not evidence that the query has already achieved high precision. Screen the retained candidate articles against an operational definition requiring an experimentally varied communicated treatment and participant responses recorded in a survey or questionnaire task, then separately record original data collection and parser compatibility. An author's right or willingness to donate requires later confirmation and cannot be inferred from a bibliographic query.

Retain punctuation-sensitive verification of design expressions and record matched evidence spans. Do not treat the absence of an intact expression in extracted fields as definitive noneligibility when database-only keywords are missing. Article-level guards should be allowed when they support the same study; cross-study linkage is a review decision. No explicit query exclusions for conjoint or split-ballot designs are necessary; design complexity belongs in the eligibility rubric.

The focal authors' papers are diagnostic challenge cases. They should not define the target population, receive special rank credit, or become an independent recall estimate. A known relevant article whose metadata never states experimental design may remain outside the search; disclose that limitation rather than adding topic language merely to recover that article.

## Validation and ranking protocol

1. Freeze the eligibility definition, query, journal frame, years, deduplication rules, and first/last-author rule. Retain both old and new searches with retrieval dates and hashes.
2. Form disjoint strata: old/new overlap, newly retrieved by the procedure route, newly retrieved by design labels, old-only losses, and local-rule disagreements. Randomly sample within each stratum using a recorded seed and known inclusion probabilities. Keep focal-author challenge cases separate from this probability sample.
3. Annotate original human experimental data, communicated treatment, survey/questionnaire response, parser compatibility, and uncertainty as separate fields. Require short verifiable evidence and source provenance. Mark abstracts that cannot resolve eligibility as requiring full text. Do not convert missing evidence into a negative label.
4. Have two reviewers independently validate a held-out sample and adjudicate disagreements. AI labels can accelerate preparation, but must be identified as such. A substantial revision after seeing the evaluation sample requires a new held-out evaluation set.
5. Estimate precision by weighting stratum-specific eligible proportions by stratum population sizes; report uncertainty and the unresolved fraction. Estimate recall only relative to an independent positive reference set or independently screened broad sampling frame. The old corpus alone cannot reveal work missed by both queries. Known-author case recovery is a separate diagnostic.
6. Present the precision–coverage trade-off, removed eligible articles, and review workload alongside added counts. An enriched set of difficult examples cannot support an overall precision percentage.
7. Recompute researcher scores only from the declared eligibility tier. Credit one article once to each first or last author, counting sole authors once. Report middle-author contributions separately if desired. Keep author identity resolution, journal-frame losses, query misses, and rank cutoffs distinct when explaining absent researchers.
8. Update geography annotations for all articles credited to the expanded author pool before comparing US-sample rankings. Report ties and sensitivity to uncertain eligibility/geography. Do not infer seniority or ownership solely from last-author position, whose meaning varies across social sciences.

## Suggested appendix wording

We identified candidate articles through two complementary routes: explicit survey- or vignette-experiment labels, and descriptions combining an experimental design, a communicated stimulus, and an elicited participant judgment or response. We searched titles, abstracts, and keywords in a prespecified journal frame for articles published in 2010–2026. We then reviewed candidate articles for original survey-experimental data and design compatibility, retaining evidence for each decision. The search was fixed before its validation sample was drawn. Researcher scores counted eligible articles on which a researcher was first or last author, with each article counted at most once per researcher. The search does not establish data ownership or willingness to share, which require subsequent contact.

This wording describes a completed screening and validation workflow only after those steps have actually been performed. Until then, use “candidate articles,” describe AI-assisted assessments as provisional, and avoid claiming a validated high-precision search.
