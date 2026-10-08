# SCORE prompt evaluation

Abstracts annotated: 620/620. Full texts reviewed: 620/620. Human verification: 0.

Metadata availability: 7 articles have no supplied abstract and 178 have no keywords. These records were screened using the remaining supplied fields; missing text was not invented or replaced with full-text information.

The reference assessments are provisional AI source reviews. These metrics describe agreement with those reviews, not human-validated accuracy. The 620 articles form an access-conditioned development collection; prior prompt development and targeted examples mean this is not an untouched holdout.

All abstract labels were produced by session agents. Source-review model counts: Codex session agent (GPT-6 family): 551; gpt-6-astra: 69. The user authorized API annotation after 551 session source reviews. Subsequent API requests use the same criteria, one article per request, without abstract predictions. This mixed reference process is documented in [the protocol](protocol.md); it does not measure the performance of a single API model on all abstracts.

Substantive source adjudications have changed 7 reference labels and corrected evidence or reasoning without changing 4 labels. Separate PDF extraction corrections are documented in the protocol. Initial source reviews were blind to abstract predictions and are retained privately. The numerical comparison before adjudication is retained in evaluation.json; the tables below use the adjudicated judgments.

## Metrics

The binary comparisons use 608 paired articles with a YES or NO full-text judgment. 12 unresolved full-text judgments are excluded from binary denominators and shown in the table below. Unreviewed articles are never assigned NO.

| Decision being evaluated | Articles | Balanced accuracy | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Immediate YES: UNCLEAR is not an immediate positive | 608 | 81.8% | 100.0% | 63.6% | 77.8% |
| Retain for review: YES and UNCLEAR are positive | 608 | 84.6% | 86.0% | 83.9% | 84.9% |
| Definite answers only: abstract UNCLEAR excluded | 501 | 89.9% | 100.0% | 79.8% | 88.7% |

The 69 API source reviews used 1,773,422 input tokens and 20,017 output tokens, including reasoning. Calculated cost: $23.17, within the approved $100 limit. This is usage-based accounting, not an invoice. Rates and cache-write charges follow [OpenAI pricing](https://developers.openai.com/api/docs/pricing); private receipts preserve the calculation.

An additional 3 Flex source rechecks cost $1.70; combined historical and recheck API usage cost is $24.87. See the [follow-up source checks](error_analysis.md).

Definite-answer coverage among resolved references: 82.4%. The definite-only row can look better because it excludes difficult cases; read it alongside coverage.

## Interpretation

Among resolved references, 201 immediate YES decisions are supported and 0 are contradicted. Retaining YES and UNCLEAR finds 265 of 316 eligible articles, but 51 eligible articles still receive NO. This supports using the prompt to identify clear positives and build a review queue; it does not support treating every NO as a dependable exclusion. No observed false positives does not guarantee perfect precision on new articles.

- Balanced accuracy is the average of recall for eligible articles and specificity for ineligible articles. It gives both reference classes equal weight.
- Precision is the share of positive decisions supported by a full-text YES. For the retention policy, this measures how many retained cases are eligible.
- Recall is the share of full-text YES articles found by the decision policy. For the retention policy, a missed positive received abstract NO.
- F1 combines precision and recall, giving a low score when either is low. It does not use true negatives.
- The strict-YES row measures immediate identification, not the meaning of UNCLEAR as a scientific judgment. It treats UNCLEAR as not yet selected. The retention row measures the practical queue for further review.

## All paired labels

Rows are full-text judgments; columns are abstract judgments.

| Full text / Abstract | YES | NO | UNCLEAR |
| --- | ---: | ---: | ---: |
| YES | 201 | 51 | 64 |
| NO | 0 | 249 | 43 |
| UNCLEAR | 0 | 8 | 4 |

See [individual disagreements](disagreements.csv). The wording review and critically vetted examples are recorded in [the error analysis](error_analysis.md).

The frozen supplied prompt is unchanged during this evaluation. The reported performance does not establish the benefit of a suggested revision; that requires a separate test.
