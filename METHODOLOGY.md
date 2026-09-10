Our goal is to identify potential data donors who have frequently conducted survey experiments, with particular interest in experiments using US samples.

1. **Define the journal set.** We use the 3,401 journals in the recorded publication histories of investigators in Time-sharing Experiments for the Social Sciences (TESS). This gives us a broad starting set of journals used by experimental social scientists. Candidate donors need not have participated in TESS.

2. **Find candidate survey experiments.** Within these journals, we search Scopus titles, abstracts and keywords for journal articles published in 2010–2026. We search for survey- and vignette-experiment labels, alongside descriptions of experimental framing, information, question wording and reading assignments. Broader procedural descriptions must also occur with survey or participant language. The search returns 9,365 distinct candidate articles.

3. **Identify researchers with repeated experience.** We count each distinct article once for each first or last author; a sole author receives one credit. This is a proxy for research leadership. For sample review, we retain a fixed cohort of 120 researchers: all 114 at or above the total-count top-100 cutoff, including ties, plus six previously screened candidates.

4. **Rank by evidence of US samples.** We review titles, abstracts and keywords, consulting full texts when available. The cohort has 1,035 distinct credited articles under this query: 483 have US-sample evidence and 153 remain geographically unclear. We combine explicit US recruitment statements with justified inference from study context, including American topics. The default ranking counts these US-evidence articles; total survey-experiment candidate counts remain available alongside it.

The US ranking compares this 120-person cohort, not every author in Scopus. Unclear geography is not treated as non-US. Counts describe articles, not independent datasets. Annotations are AI-assisted and await human validation; study eligibility and access to data and treatment materials require confirmation before invitations.

Of 9,365 candidates, 9,359 have complete author credits; 6 have unresolved bylines and receive no credit. Equal counts share a rank. Affiliation fields are joined from sourced profiles and describe researchers, not participant geography.

The query below searches journal articles published in 2010–2026. The pipeline intersects its results with the [3,401-journal Source-ID list](results/venue_frame.csv). Quoted phrases support wildcard endings rather than exact punctuation. `W/3` specifies words within three positions; procedural proximity matching is restricted to abstracts.

```text
(
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
    AND TITLE-ABS-KEY(
      survey*
      OR questionnaire*
      OR respondent*
      OR participant*
    )
    AND TITLE-ABS-KEY(
      random*
      OR experiment*
    )
  )
  OR (
    TITLE-ABS-KEY(
      "random* assign* to read"
      OR "random* allocat* to read"
      OR "random* select* to read"
      OR "random* to read"
    )
    AND TITLE-ABS-KEY(
      survey*
      OR questionnaire*
      OR respondent*
      OR participant*
    )
  )
  OR (
    TITLE-ABS-KEY(
      experiment*
    )
    AND ABS(
      (
        read W/3(
          vignette*
          OR scenario*
          OR message*
          OR article*
          OR news
        )
      )
      OR (
        manipulat* W/3(
          vignette*
          OR scenario*
          OR message*
          OR wording
        )
      )
    )
    AND ABS(
      survey*
      OR questionnaire*
      OR respondent*
      OR participant*
    )
  )
)
AND SRCTYPE(
  j
)
AND DOCTYPE(
  ar
)
AND PUBYEAR > 2009
AND PUBYEAR < 2027
```

[Download the query](queries/proximity_specific_2026_09_10/primary_plus_specific.txt) · [Open the ranking](DASHBOARD_NARROWER.html).
