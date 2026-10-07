The revised query retrieves **8,074 distinct articles** within the same 3,401-journal frame and 2010–2026 publication window. Relative to a fresh run of the previous query, it adds 788 articles and loses 18, a net change of **+770** (10.5%). These are candidate articles for screening, not confirmed eligible datasets or donors.

| Retrieval measure | Previous query, rerun | Revised query | Net change |
|---|---:|---:|---:|
| Global Scopus records | 9,113 | 10,507 | +1,394 |
| Records in the journal frame | 7,307 | 8,077 | +770 |
| Distinct in-frame articles after DOI deduplication | 7,304 | 8,074 | +770 |

The earlier archived search contained 7,302 distinct in-frame articles. Rerunning that unchanged query now produces 7,304; this +2 difference is database change, separate from the query revision. The dashboard's existing reviewed cohort remains attached to its archived query; the new retrieval has not yet been incorporated into its geography annotations or rankings.

The following changes are cumulative in the displayed order. Overlapping matches are credited once, so these contributions sum to the net change; they are not independent estimates of each phrase's value.

| Query change | Change in distinct in-frame articles | Cumulative articles |
|---|---:|---:|
| Add participant* to text assignment and question wording | +254 | 7,558 |
| Add the initial eight information/message assignment phrases | +4 | 7,562 |
| Remove the four national-survey embedded-experiment phrases | -18 | 7,544 |
| Add the 12 explicit survey-design phrases | +430 | 7,974 |
| Add the eight generic in/within-survey phrases | +13 | 7,987 |
| Add the remaining six information/message assignment phrases | +3 | 7,990 |
| Expand information experiments and add its participant* context | +84 | 8,074 |

“Survey-based experiments” was already present, together with its singular and unhyphenated forms. The revision adds 40 exact phrases, removes the four requested national-survey phrases, and permits `participant*` in the text-assignment, question-wording, and information-treatment context requirements. It introduces no design, country, provider, or representativeness exclusions. An article describing a national sample can still match another retained term. Longer phrases such as “experimental survey study” overlap with “experimental survey”; their presence does not imply an independent retrieval gain.

We also tested generic variants involving “embedded within,” plural “surveys,” and intervening verbs, such as “experiment was embedded in a survey.” That [separate diagnostic](queries/revision_2026_09_10/additional_embedded_variants.txt) identifies 10 further in-frame records beyond the revised query (14 globally). These variants are recorded separately from the requested query below.

**Retrieval and review.** The previous, revised, and intermediate versions were executed as unions of positive Scopus phrase-family searches. Identical clauses share the same archived responses. Every result page was retrieved and checked against the reported total; Source IDs determine journal-frame membership. We compare Scopus IDs locally and then compare normalized DOI identities, falling back to Scopus ID when DOI is absent. Full metadata for all added and removed records is retained privately for screening. Retrieval ran from 2026-09-10T10:59:02.609024+00:00 to 2026-09-10T11:23:10.176191+00:00. [Counts](results/query_revision_2026_09_10/retrieval_comparison.csv), [cumulative contributions](results/query_revision_2026_09_10/sequential_changes.csv), and [added/removed article metadata](results/query_revision_2026_09_10/changed_article_metadata.csv) accompany the complete manifests in the repository.

Of the 788 added in-frame records, **628 pass the strict local phrase/context check** and 160 do not. The latter remain in a review queue: missing indexed keywords, context in another sentence, and punctuation-crossing database matches are possible reasons. Passing this check does not establish study eligibility. [Local verification by change](results/query_revision_2026_09_10/local_verification_by_change.csv).

The final information-family expansion adds 84 in-frame records, but only **7** pass the local check for that stage. The returned records include clinical-treatment and visual-memory studies. “Experimental survey” also retrieves useful manipulated-scenario studies, survey-recruitment experiments, and a paper recommending an experimental survey as future research. These broad additions therefore require screening before researcher counts change; their additional hits should not be described as confirmed survey experiments.

Field-specific Scopus API checks found `ABS({experimental survey})` matching “experimental, survey” and `ABS({information experiment})` matching “information. Experiment.” `ABS({information treatment})` also matched “information: Treatment” in clinical-trial registration text. For these examples, the same phrase returned zero title and keyword matches. Thus braces alone did not prevent the punctuation errors in the tested endpoint. The local matcher rejects these strings. [Queries and observed field counts](results/query_revision_2026_09_10/field_checks.csv) document the tests; the underlying responses and full abstracts remain private.

Retrieval gains do not establish precision or recall. Eligibility requires inspection of the treatment, response structure, original fielding, and access to respondent data and survey materials. These additions have not received geography annotation or independent eligibility validation.

**Complete revised query.** The query searches titles, abstracts, and keywords. Curly braces request exact phrases, with singular/plural and spelling variants enumerated explicitly. [Elsevier's documented syntax](https://dev.elsevier.com/sc_search_tips.html) describes punctuation-sensitive matching; the observed exceptions above make a separate local check necessary. The pipeline applies the journal frame using Source IDs. [Download revised query](queries/revision_2026_09_10/revised.txt) · [Previous query](queries/revision_2026_09_10/previous.txt).

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
      OR {survey experimental}
      OR {experimental survey}
      OR {experimental surveys}
      OR {experimental survey study}
      OR {experimental survey studies}
      OR {survey-based randomized experiment}
      OR {survey-based randomized experiments}
      OR {survey based randomized experiment}
      OR {survey based randomized experiments}
      OR {survey-based randomised experiment}
      OR {survey-based randomised experiments}
      OR {survey based randomised experiment}
      OR {survey based randomised experiments}))
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
      OR {embedded survey experiment}
      OR {embedded survey experiments}
      OR {survey with an embedded experiment}
      OR {survey with embedded experiments}
      OR {surveys with embedded experiments}
      OR {experiment in an online survey}
      OR {experiments in an online survey}
      OR {experiment within an online survey}
      OR {experiments within an online survey}
      OR {experiment in a survey}
      OR {experiments in a survey}
      OR {experiment within a survey}
      OR {experiments within a survey}) AND TITLE-ABS-KEY(survey* OR questionnaire* OR respondent*))
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
      OR {randomly shown a vignette}
      OR {randomly presented with information}
      OR {randomly exposed to information}
      OR {randomly assigned to receive a message}
      OR {randomly assigned to receive messages}
      OR {randomly presented with a message}
      OR {randomly presented with messages}
      OR {randomly exposed to a message}
      OR {randomly exposed to messages}
      OR {randomly shown information}
      OR {randomly assigned information}
      OR {randomly assigned a message}
      OR {randomly assigned messages}
      OR {randomly shown a message}
      OR {randomly shown messages}) AND TITLE-ABS-KEY(survey* OR questionnaire* OR respondent* OR participant*))
  OR (TITLE-ABS-KEY({information treatment}
      OR {information treatments}
      OR {informational treatment}
      OR {informational treatments}
      OR {information experiment}
      OR {information experiments}
      OR {randomized information experiment}
      OR {randomized information experiments}
      OR {randomised information experiment}
      OR {randomised information experiments}) AND TITLE-ABS-KEY(survey* OR questionnaire* OR respondent* OR participant*) AND TITLE-ABS-KEY(random* OR experiment*))
  OR (TITLE-ABS-KEY({question wording experiment}
      OR {question wording experiments}
      OR {question-wording experiment}
      OR {question-wording experiments}
      OR {wording experiment}
      OR {wording experiments}) AND TITLE-ABS-KEY(survey* OR questionnaire* OR respondent* OR participant*))
)
AND SRCTYPE(j) AND DOCTYPE(ar) AND PUBYEAR > 2009 AND PUBYEAR < 2027
```

Reproduce the archived comparison with `python3 pipeline/query_revision.py report`; `retrieve` resumes the dated API snapshot, and `all` retrieves and reports. A subsequent live comparison requires a new dated namespace to preserve this snapshot.

**Illustrative abstract checks.** These selected examples describe eligibility concerns and useful additions; they are not a precision estimate.

| Article | Abstract-based assessment |
|---|---|
| [Taking climate change here and now – mitigating ideological polarization with psychological distance](https://doi.org/10.1016/j.gloenvcha.2018.09.013) | Reports a framing manipulation and policy/behavior outcomes in an American adult sample; a useful candidate for treatment-material review. |
| [Between fearmongers and Samaritans: Does information provision affect attitudes towards the right of asylum in Germany?](https://doi.org/10.1111/kykl.12349) | Reports a self-designed survey with randomized information about asylum seekers; a useful addition for the intended donor search. |
| [Reference-Dependency of Happiness Ratings](https://doi.org/10.1007/s10902-014-9567-7) | Mentions an experimental survey as future research. The abstract does not establish random assignment in the reported study, despite passing the local phrase check. |
| [Effect of numbering of return envelopes on participation, explicit refusals, and bias: Experiment and meta-analysis](https://doi.org/10.1186/1471-2288-14-6) | Manipulates mail-return envelope numbering and measures participation. This is a recruitment-method experiment, outside the target of treatments embedded in survey questions. |
| [Self-expansion and flow: The roles of challenge, skill, affect, and activation](https://doi.org/10.1111/pere.12062) | The Scopus abstract-field check matches experimental survey across a comma; the local phrase check correctly fails. The abstract combines several methods without establishing a survey-embedded manipulation. |
| [Gist in time: Scene semantics and structure enhance recall of searched objects](https://doi.org/10.1016/j.actpsy.2016.05.013) | Reports visual-search and object-memory tasks. The Scopus abstract-field check matches information experiment across a full stop; the local check fails. |
| [Dialectical Behavior Therapy Compared with Enhanced Usual Care for Adolescents with Repeated Suicidal and Self-Harming Behavior: Outcomes over a One-Year Follow-Up](https://doi.org/10.1016/j.jaac.2016.01.005) | Reports a clinical psychotherapy trial. The Scopus abstract-field check matches information treatment across a colon in registration text; the local check fails. |
| [Information effects on consumer preferences for alternative animal feedstuffs](https://doi.org/10.1016/j.foodpol.2021.102192) | Uses a discrete-choice experiment with multiple attributes. Information-treatment language alone does not establish compatibility with the parser. |

[Open the reviewed researcher dashboard](TOP100.html#summary).
