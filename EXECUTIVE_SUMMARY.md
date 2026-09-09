Our goal is to identify data donors who have often conducted survey experiments. We have followed these steps:

1. We first need to define a set of journals where experimental social scientists would publish their research. We take all 3,401 journals that investigators in Time-sharing Experiments for the Social Sciences (TESS) have published in. Within these journals, we search titles, abstracts, and keywords for survey-experiment articles published in 2010–2026. Candidate donors need not have participated in TESS.

2. We then search for journal articles with search terms related to survey experiments. The search combines exact survey- and vignette-experiment phrases with specific descriptions of embedded experiments, randomized vignettes, reading assignments, information treatments, and question-wording experiments. Exact phrases preserve punctuation, reducing accidental matches between adjacent but unrelated words. The query is shown below:

```text
(
  (TITLE-ABS-KEY({survey experiment}
      OR {survey experiments}
      OR {survey-based experiment}
      OR {survey-based experiments}
      OR {survey based experiment}
      OR {survey based experiments}
      OR {survey-embedded experiment}
      OR {survey-embedded experiments}
      OR {survey embedded experiment}
      OR {survey embedded experiments}
      OR {survey-experimental}
      OR {survey experimental}))
  OR (TITLE-ABS-KEY({vignette experiment}
      OR {vignette experiments}
      OR {experimental vignette}
      OR {experimental vignettes}
      OR {vignette-based experiment}
      OR {vignette-based experiments}
      OR {vignette based experiment}
      OR {vignette based experiments}))
  OR (TITLE-ABS-KEY({framing experiment}
      OR {framing experiments}
      OR {information provision experiment}
      OR {information provision experiments}
      OR {information-provision experiment}
      OR {information-provision experiments}
      OR {scenario-based experiment}
      OR {scenario-based experiments}
      OR {scenario based experiment}
      OR {scenario based experiments}) AND TITLE-ABS-KEY(survey* OR questionnaire* OR respondent*))
  OR (TITLE-ABS-KEY({vignette-based survey}
      OR {vignette-based surveys}
      OR {vignette based survey}
      OR {vignette based surveys}) AND TITLE-ABS-KEY(random* OR experiment*))
  OR (TITLE-ABS-KEY({experiment embedded in a survey}
      OR {experiments embedded in a survey}
      OR {experiment embedded in an online survey}
      OR {experiments embedded in an online survey}
      OR {experiment embedded in a national survey}
      OR {experiments embedded in national surveys}
      OR {experiment embedded in a nationally representative survey}
      OR {experiments embedded in nationally representative surveys}
      OR {embedded survey experiment}
      OR {embedded survey experiments}
      OR {survey with an embedded experiment}
      OR {survey with embedded experiments}
      OR {surveys with embedded experiments}) AND TITLE-ABS-KEY(survey* OR questionnaire* OR respondent*))
  OR (TITLE-ABS-KEY({factorial survey}
      OR {factorial surveys}
      OR {factorial vignette experiment}
      OR {factorial vignette experiments}
      OR {randomized vignette experiment}
      OR {randomized vignette experiments}
      OR {randomised vignette experiment}
      OR {randomised vignette experiments}
      OR {randomized vignette}
      OR {randomized vignettes}
      OR {randomised vignette}
      OR {randomised vignettes}))
  OR (TITLE-ABS-KEY({randomly assigned to read}
      OR {randomly allocated to read}
      OR {randomly selected to read}
      OR {randomized to read}
      OR {randomised to read}
      OR {randomly assigned to a vignette}
      OR {randomly assigned a vignette}
      OR {randomly assigned to one of two vignettes}
      OR {randomly assigned to one of three vignettes}
      OR {randomly assigned to receive information}
      OR {randomly provided with information}
      OR {randomly presented with a vignette}
      OR {randomly presented with vignettes}
      OR {randomly presented with a scenario}
      OR {randomly shown a vignette}) AND TITLE-ABS-KEY(survey* OR questionnaire* OR respondent*))
  OR (TITLE-ABS-KEY({information treatment}
      OR {information treatments}
      OR {informational treatment}
      OR {informational treatments}) AND TITLE-ABS-KEY(survey* OR questionnaire* OR respondent*) AND TITLE-ABS-KEY(random* OR experiment*))
  OR (TITLE-ABS-KEY({question wording experiment}
      OR {question wording experiments}
      OR {question-wording experiment}
      OR {question-wording experiments}
      OR {wording experiment}
      OR {wording experiments}) AND TITLE-ABS-KEY(survey* OR questionnaire* OR respondent*))
)
AND SRCTYPE(j) AND DOCTYPE(ar) AND PUBYEAR > 2009 AND PUBYEAR < 2027
```

The pipeline restricts the retrieved records to the journal frame using Scopus Source IDs.

3. The search returns 7,305 article records, or 7,302 after duplicate removal. The provisional 100-researcher pool counts each candidate article once for each first or last author.

4. The sortable 100-researcher dashboard joins current institutions, departments, countries, and roles. Review of 870 distinct articles identifies 393 with US-sample evidence (248 explicit; 145 inferred, incorporating 65 full-text reviews); 127 remain unclear pending full-text review. US sorting compares this pool, not all researchers. Counts describe articles, not independent datasets, and the AI-assisted annotations await validation. A deduplicated download queue supports the next review round.

