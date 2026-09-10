# Legacy development comparison, 10 September 2026

This is an offline diagnostic using the same two inherited datasets and annotation mapping as `pipeline/benchmark.py`. Neither dataset is a probability sample of the new query's output or a held-out validation set. Their inherited AI labels concern a broader survey-experiment concept and do not establish original data collection, parser compatibility, data ownership, or sample geography. Counts below must not be reported as validated precision or recall.

After restricting to 2010–2026 and retaining records with mapped annotations, the investigator-development corpus contains 1,939 unique Scopus articles: 393 inherited yes labels, 1,423 no labels, and 123 unclear labels. The term-stratified corpus contains 3,891 articles: 2,358 yes, 1,449 no, and 84 unclear. The two corpora are reported separately; overlapping articles have not been removed across corpora.

The three-concept diagnostic requires all of:

```
D: experiment* OR random* OR manipulat*
S: information OR message* OR text* OR vignette* OR scenario* OR headline* OR prompt*
O: attitud* OR belief* OR opinion* OR perception* OR judgment* OR judgement*
   OR intention* OR preference*
```

The exposure variant additionally requires a stimulus term S near an action from `read* OR view* OR expos* OR present* OR receiv* OR shown`. For this local approximation, two distinct token positions can have at most five intervening tokens, in either order. Proximity is measured within a field; an alternative additionally prevents matches across sentence or keyword-entry boundaries. HTML tags are removed for tokenization. D and O can appear anywhere in title, abstract, or keywords. This is **not an implementation of Scopus W/5 semantics**, which must be measured using actual database retrieval. The exact regular expressions are in the reproducible script.

The comparator is the executed 10 September expanded phrase query's existing strict local matcher (`query_revision.revised_families()`). Thus, the union rows below add a diagnostic procedure route to that matcher; they do not represent the complete final simplified query, nor a database result count. In particular, this comparator still applies the existing same-sentence guard rules.

| Corpus and variant | Matched articles | Inherited yes | Inherited no | Inherited unclear |
|---|---:|---:|---:|---:|
| Investigator: revised phrase matcher | 103 | 100 | 0 | 3 |
| Investigator: revised OR three concepts | 212 | 175 | 26 | 11 |
| Investigator: revised OR exposure, same field | 132 | 125 | 4 | 3 |
| Investigator: revised OR exposure, same sentence | 132 | 125 | 4 | 3 |
| Term-stratified: revised phrase matcher | 1,196 | 1,142 | 44 | 10 |
| Term-stratified: revised OR three concepts | 1,786 | 1,612 | 152 | 22 |
| Term-stratified: revised OR exposure, same field | 1,481 | 1,387 | 78 | 16 |
| Term-stratified: revised OR exposure, same sentence | 1,471 | 1,380 | 77 | 14 |

Relative to the revised matcher, unrestricted concepts add 109 investigator-corpus articles (75 yes, 26 no, 8 unclear) and 590 term-stratified articles (470 yes, 108 no, 12 unclear). Exposure proximity adds 29 (25 yes, 4 no, 0 unclear) and 285 (245 yes, 34 no, 6 unclear), respectively. Enforcing the same sentence reduces the latter addition to 275 (238 yes, 33 no, 4 unclear); it leaves the investigator-corpus union unchanged. Stronger linkage narrows the review workload and the number of inherited negatives, while also losing inherited positives. An evaluation must determine whether that trade-off improves the intended target definition.

Inspection of inherited-negative exposure additions illustrates risks that survive proximity:

- **Perspectives of U.S. harm reduction advocates on persuasive message strategies** (85168349851): 15 qualitative interviews; an exposure-like phrase describes interviewees viewing messages as persuasive, while experimental research appears only as a future recommendation.
- **Structured matching models in multimodal information fusion: An optimized Kuhn-Munkres algorithm** (105022671085): a sentence about integrating text presenting a challenge links `text*` with `present*`; experiments evaluate an algorithm and opinion appears in a dataset name.
- **Contributions of shape and reflectance information to social judgments from faces** (85074940248): human experiments concern manipulated face images and visual information. A communicated-information word does not establish a text treatment.
- **How do social media users process cancer prevention messages on Facebook? An eye-tracking study** (85079074559): the reported endpoint is visual attention; attitude language appears in the background. Article-level concepts need not describe the same outcome.

These are diagnostic assessments from available abstracts, not independent adjudications of all inherited labels. They motivate explicit study-level screening, particularly for future-study recommendations, sensory tasks, clinical interventions, mixed paradigms, and nonhuman experiments.

`legacy_development_comparison.csv` contains all 22 aggregate variant rows. Source-file and script hashes are in `legacy_development_comparison_provenance.json`; article-level matches remain private. Reproduce from the project workspace with:

```
python3 SurveyExperimentRecruitment/results/design_audit_2026_09_10/reproduce_legacy_development_comparison.py
```

The command reads the inherited corpora from the adjacent `Opencall/QueryV2/` directories. Those private source corpora are not distributed with the public recruitment repository.
