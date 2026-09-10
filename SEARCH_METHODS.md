We defined the journal frame using the complete publication histories through 2026 of the resolved investigators in a frozen TESS roster, yielding 3,401 Scopus Source IDs. Investigators outside TESS could enter the candidate pool. We searched records dated 2010–2026, limited to journal-source documents classified as articles, and intersected the results with this journal frame. Overlapping positive query parts were fully paginated, united by Scopus ID and deduplicated by normalized DOI, using Scopus ID when DOI was absent. Query texts, retrieval dates, source-frame hashes and record memberships were archived.

The candidate query identifies named survey and vignette designs, contextualized framing/information/scenario designs, randomized reading assignments, and descriptions combining experimental manipulation, communicated materials and attitudinal or judgment outcomes. Named designs and population context are searched in titles, abstracts and keywords. The broader procedural branch requires its design, material and outcome evidence in titles or abstracts to reduce ambiguous matches from indexed keywords. Loose phrases and wildcards compress grammatical variants. Subsequent screening should check phrase punctuation and field boundaries while allowing population context elsewhere in the metadata. The refined search does not yet apply this local check to the complete candidate union. A lexical match does not establish that an eligible experiment was conducted.

Article screening asks whether at least one study varies communicated content or question presentation for human respondents and measures their responses. Review-only, observational, simulation-only and incompatible intervention records are not credited; insufficient descriptions require full text. Text modality, original data collection, structural parser compatibility and data possession are separate decisions. National representativeness and sample vendors are not exclusion criteria or evidence of ownership. For a revised ranking, complete candidate bibliographies and eligibility review before truncating the researcher pool. Each eligible distinct article will contribute once to each distinct first or last author; a sole author receives one credit. Counts describe articles, not independent experiments or datasets. US geography is recorded separately from respondent evidence, with contextual inference distinguished from explicit statements. Current institutions, departments, countries and roles are joined separately from publication affiliations.

Query development used two nominated author bibliographies, 20 challenge papers, inherited development data and a 160-article stratified audit. The resulting query was frozen before drawing a simple random hash sample of 100 articles from 16,147 candidates outside all development material. Exclusions used Scopus aliases, DOI and normalized title; coding packets omitted authors and search-route membership. Two AI coders independently reviewed the same titles, abstracts and author keywords. Disagreement and insufficient evidence remained unresolved. This audit estimates neither population recall nor human-validated precision; independent human adjudication remains necessary. The named-design/reading and procedure-only subgroups yielded agreed affirmative evidence for 36/41 and 29/59 articles, respectively. These subgroup descriptions were computed after coding. The broader procedure route is therefore recommended only as a separately screened supplement, not as an automatic source of ranking credit. Bibliography completion and human adjudication are proposed next stages, not completed results. The current dashboard has not been replaced by unscreened results from this query.

The executed candidate query was:

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

The full journal-frame restriction is applied using [Source IDs](results/venue_frame.csv). [Query file](queries/search_strategy_2026_09_10/candidate.txt) · [Search comparison and audit results](SEARCH_STRATEGY.html).
