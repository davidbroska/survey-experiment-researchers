# SCORE prompt evaluation

**Work in progress: these are partial counts, not the completed 620-article result.**

Abstracts annotated: 620/620. Full texts reviewed: 0/620. Human verification: 0.

The reference assessments are provisional AI source reviews. These metrics describe agreement with those reviews, not human-validated accuracy. The 620 articles form an access-conditioned development collection; prior prompt development and targeted examples mean this is not an untouched holdout.

## Metrics

The binary comparisons use 0 paired articles with a YES or NO full-text judgment. 0 unresolved full-text judgments are excluded from binary denominators and shown in the table below. Unreviewed articles are never assigned NO.

| Decision being evaluated | Articles | Balanced accuracy | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Immediate YES: UNCLEAR is not an immediate positive | 0 | Not estimable | Not estimable | Not estimable | Not estimable |
| Retain for review: YES and UNCLEAR are positive | 0 | Not estimable | Not estimable | Not estimable | Not estimable |
| Definite answers only: abstract UNCLEAR excluded | 0 | Not estimable | Not estimable | Not estimable | Not estimable |

Definite-answer coverage among resolved references: Not estimable. The definite-only row can look better because it excludes difficult cases; read it alongside coverage.

## Interpretation

- Balanced accuracy is the average of recall for eligible articles and specificity for ineligible articles. It gives both reference classes equal weight.
- Precision is the share of positive decisions supported by a full-text YES. For the retention policy, this measures how many retained cases are eligible.
- Recall is the share of full-text YES articles found by the decision policy. For the retention policy, a missed positive received abstract NO.
- F1 combines precision and recall, giving a low score when either is low. It does not use true negatives.
- The strict-YES row measures immediate identification, not the meaning of UNCLEAR as a scientific judgment. It treats UNCLEAR as not yet selected. The retention row measures the practical queue for further review.

## All paired labels

Rows are full-text judgments; columns are abstract judgments.

| Full text / Abstract | YES | NO | UNCLEAR |
| --- | ---: | ---: | ---: |
| YES | 0 | 0 | 0 |
| NO | 0 | 0 | 0 |
| UNCLEAR | 0 | 0 | 0 |

See [individual disagreements](disagreements.csv). The wording review and critically vetted examples are recorded in [the error analysis](error_analysis.md).

The frozen supplied prompt is unchanged during this evaluation. The reported performance does not establish the benefit of a suggested revision; that requires a separate test.
