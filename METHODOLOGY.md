Our goal is to identify potential data donors who have frequently conducted survey experiments, with particular interest in experiments using US samples.

1. **Define the journal set.** We use the 3,401 journals with at least one recorded publication from investigators in Time-sharing Experiments for the Social Sciences (TESS). This gives us a broad starting set of journals used by experimental social scientists. Candidate donors need not have participated in TESS.

2. **Find candidate survey experiments.** Within these journals, we search Scopus titles, abstracts and keywords for journal articles published in 2010–2026. We search for survey- and vignette-experiment labels, alongside descriptions of experimental framing, information, question wording and reading assignments. Broader procedural descriptions must also occur with survey or participant language. The search returns 9,365 distinct candidate articles.

3. **Identify potential research leaders.** We count each distinct article once for each first or last author; a sole author receives one credit. This is a proxy for research leadership.

4. **Rank by evidence of US samples.** We then review sample locations for 120 researchers: the top 100 by article count, expanded to 114 because of ties, plus six additional candidates retained from the initial review list. We use article information and available full texts to identify US samples, either explicitly reported or reasonably inferred from the study context. Among the 1,035 distinct articles associated with these 120 researchers, 489 have US-sample evidence and 147 remain geographically unclear. The dashboard sorts by US-sample articles by default; total survey-experiment candidate counts are also available.

The US ranking compares these 120 researchers, not every author in Scopus. Unclear geography is not treated as non-US. Counts describe articles, not independent datasets. Annotations are AI-assisted and await human validation; study eligibility and access to data and treatment materials require confirmation before invitations.

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
