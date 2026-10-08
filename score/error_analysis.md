# Error analysis of the supplied prompt

The active prompt remains unchanged. [The evaluation report](report.md) contains the current denominators, confusion table and metrics; [the disagreement file](disagreements.csv) identifies every differing label. This analysis distinguishes mistakes in applying the criteria from information that an abstract simply does not contain. The abstract model returned only a label, so explanations of why it made a particular decision are inferences from the available inputs, not recorded model explanations.

## Main finding

The metadata judgments were conservative about saying YES on this collection. A recurring pattern among checked disagreements is missed eligible questionnaires, including auxiliary questionnaires within papers whose abstracts emphasize laboratory tasks, field interventions, administrative outcomes or existing records. Retaining UNCLEAR improves retrieval, but does not recover eligible articles already classified NO. Conversely, an abstract UNCLEAR followed by full-text YES is often appropriate uncertainty under the metadata-only instruction, rather than an annotation error.

The full-text reference itself needed correction. Initial source judgments were recorded without the new abstract labels; subsequent checks retain both the original judgment and any correction. AI agreement is not human-validated accuracy, and apparent perfect precision in any partial or completed run must not be interpreted as a guarantee for new articles.

## Examples checked against source methods

| Article | Source finding | What this teaches us |
| --- | --- | --- |
| [Planning prompts and overdue taxes](https://doi.org/10.1287/mnsc.2020.3744) | Beyond the administrative field outcomes, the discussion reports an author-run experiment with 167 students rating the notices. | A field experiment may contain a separate qualifying questionnaire that the abstract omits. |
| [Learning by enacting](https://doi.org/10.1016/j.learninstruc.2017.09.008) | Text segment 4 describes the team's post-lesson questionnaire on enjoyment, interest, confidence and mental effort. | Educational performance tasks do not make the entire paper ineligible when a questionnaire component is present. |
| [Flip a coin or vote?](https://doi.org/10.1007/s10683-021-09724-9) | The downloaded supplementary appendix, pages 18–19, documents political-orientation and risk-attitude questions after the laboratory experiment. | The qualifying evidence can be in a supplement. Game choices alone need not establish the decision. |
| [Behavioral constraints on implementation mechanisms](https://doi.org/10.1257/aer.20170297) | PDF pages 14–15 describe own-team reciprocity and belief questionnaire items alongside the game. | When metadata describes an experiment but leaves its response measures unresolved, UNCLEAR can be more defensible than NO. Do not infer an unmentioned questionnaire and return YES. |
| [The Self-Referencing task](https://doi.org/10.1016/j.jesp.2017.02.006) | Text segments 4–5 establish reanalysis of participant-level responses from 53 experiments run by the same lab, including explicit attitude ratings. | The meta-analysis exclusion is conditional on the absence of eligible responses. Documented reuse of the team's own responses still qualifies. |
| [Swiss Job Market Monitor](https://doi.org/10.1093/esr/jcac002) | PDF pages 3–4 describe the team's annual company questionnaire used in constructing and checking the job-advertisement collection. | A paper about documents can also use eligible questionnaire reports. Its principal dataset need not be a survey. |
| [Marital experiences and depression](https://doi.org/10.1086/714272) | The article uses CVFS questionnaire responses; the official project documentation identifies coauthor William Axinn as study director and a baseline design-team member. | A public named dataset is not automatically someone else's data. The team’s documented collection role matters. |
| [Electoral consequences of household indebtedness](https://doi.org/10.1111/ajps.12708) | PDF pages 10 and 13 identify a new module within the independently conducted British Election Study wave. | A newly introduced module still contains externally collected responses; analyzing it does not establish team collection. The inspected pages do not identify the article author as the module designer. |
| [Taking to the Streets](https://doi.org/10.1177/0010414018806540) | Current analyses use Afrobarometer and event data. Earlier author-run survey findings are cited, not reanalyzed as participant responses here. | Internal review corrected the initial source YES to NO. Citations to earlier work must not be mistaken for reuse of its responses. |

Source excerpts and reasoning are in the full-text sheet. Page references refer to the saved source version, not necessarily the printed journal page. XML/HTML segment numbers identify extracted text blocks. The own-team CVFS check also used the [official project team page](https://cvfs.isr.umich.edu/about/people/) and [ICPSR study record](https://www.icpsr.umich.edu/web/DSDR/studies/04538/summary).

## Concise amendments supported by this review

The prompt used for the reported evaluation remains frozen. The following are proposed amendments, not tested improvements. The user has now confirmed two substantive scope decisions: demographics used only to describe a sample do not qualify; questionnaire answers collected as an intervention do qualify even if those answers are not analyzed.

After the survey definition, add:

> Qualifying questionnaires may be a secondary study component. Questionnaire answers collected as part of an intervention qualify even if those answers are not analyzed. Demographic questions used only to describe the sample do not qualify on their own.

After the own-team reuse sentence, add:

> Citing earlier findings or using published effect estimates does not establish reuse of the team's participant responses.

In the UNCLEAR definition, add:

> If described answers, ratings or choices could be questionnaire responses or task outcomes and the supplied text does not resolve this, return UNCLEAR unless another criterion clearly fails. Do not infer an unmentioned questionnaire.

These additions address separate problems. The first makes the desired population explicit. The second distinguishes reuse of responses from citation or aggregate-only meta-analysis. The third concerns ambiguity in responses actually described; it does not imply every laboratory or administrative-outcome study should be UNCLEAR because an unmentioned survey might exist. Any improvement in recall or precision must be measured in a new comparison; the current metrics do not test these additions.

## What the examples mean

The tax-notice paper illustrates missing input, rather than an obvious rule error: its abstract describes tax filing and payment outcomes, whereas the full text also reports an experiment with 167 students rating the notices. The chemistry-learning paper likewise omits the decisive post-lesson experience questionnaire from its abstract. Neither omission can be solved by teaching the model to invent a questionnaire. A secondary-component clarification helps only when the supplied metadata actually mentions the relevant responses.

The Self-Referencing paper illustrates documented reuse: full methods establish that the lab ran the 53 experiments and reanalyzes participant-level responses, including explicit attitude ratings. By contrast, Taking to the Streets cites earlier author-run surveys but analyzes external Afrobarometer responses. The latter correction was a full-text reference-review error, not an observed abstract false positive.

The user's intervention clarification resolves the conceptual issue in the identity-based suspension intervention: students choose personal values and write as part of the treatment, while suspension outcomes come from school records. Under the clarified scope those questionnaire answers count. The same clarification applies to the questionnaire components of the implicit-preference interventions. These are scope decisions, not recovered downloads.

The demographic exclusion affects some existing YES judgments as well as unresolved cases. It therefore needs consistent application across all 620 papers before reporting metrics for the revised prompt. It would be misleading to relabel only a few difficult cases and call the resulting number revised-prompt accuracy.

A remaining boundary is cognitive-task explanations. The arithmetic paper records written calculations and immediate verbal explanations, then codes the strategy used. This differs from an ordinary question asking about beliefs or experiences, but the existing broad reported-behavior definition does not settle the boundary. Do not exclude all oral or open-ended survey questions to resolve this one case.

Ownership remains about documented collection or commissioning, not private access. Publicly sharing one's own responses does not erase the collection role; restricted access to someone else's survey does not create it. Institutional affiliation or matching an abbreviated author name alone is not proof of responsibility for a particular response set.

## Recheck of the 13 unresolved full-text judgments

The original 13 were full-text UNCLEAR judgments, whereas 111 abstract predictions were UNCLEAR. All 13 main texts were available and readable. The recheck revisited methods and supporting evidence; it did not replace articles or alter the 620 strata. Three cases received new Flex API reviews with recovered evidence, followed by independent source checks. The original prompt remains fixed for the numerical comparison: one reference becomes YES and 12 remain UNCLEAR. The proposed new scope is shown separately below, rather than silently included in the reported accuracy.

| Article | What the recheck established | Effect of the new clarification / remaining issue |
| --- | --- | --- |
| [Identity-based suspension intervention](https://doi.org/10.3102/00028312211042251) | Complete methods; values selections and writing are intervention components. | New intervention rule supports YES. |
| [Unwanted fertility trends](https://doi.org/10.1215/00703370-9644472) | Main is readable; Table A1 naming local surveys remains unavailable. | Collection responsibility still unresolved. |
| [School reopening politics](https://doi.org/10.3102/0013189x211048840) | Official survey documentation recovered; author-specific commissioning not established. | Still unresolved. |
| [Doctoral publication differences](https://doi.org/10.3102/0013189x17738746) | Appendix and university role documentation recovered; responsibility for the specific response sets remains uncertain. | Still unresolved. |
| [Vocabulary intervention](https://doi.org/10.1177/0014402918789162) | Teacher-questionnaire poster recovered; exact linkage to the focal cohorts remains unconfirmed. | Demographics alone would not qualify; substantive teacher questionnaire needs cohort linkage. |
| [Justice and fMRI](https://doi.org/10.1037/apl0000048) | Prior fairness survey is cited, not demonstrated as current response reuse; current medical screening format is unspecified. | Still unresolved. |
| [Kindergarten mathematical precursors](https://doi.org/10.1037/edu0000369) | Complete task methods; family-background data appear only in sample description. | New demographic exclusion supports NO. |
| [Personality and philanthropy](https://doi.org/10.1037/pspp0000556) | R code and published correlations recovered. Including the team’s prior study does not establish response-level reuse; eight reported recomputations remain unmapped. | Still unresolved; recovered evidence favors published-effect extraction, but does not prove every possible response-level calculation absent. |
| [Reducing implicit racial preferences](https://doi.org/10.1037/pspi0000339) | Main manuscript includes intervention questionnaires; the paper excludes their answers from outcome analyses. | New intervention rule supports YES. |
| [Fourth graders’ subtraction strategies](https://doi.org/10.1016/j.learninstruc.2020.101311) | Complete task procedures; written workings and immediate verbal explanations are coded as strategies. | Questionnaire-versus-task boundary remains. |
| [Bipolar versus depressive disorder MRI](https://doi.org/10.1017/s0033291722001490) | Cohort protocol recovered; clinician ratings are not proof of respondent questionnaires used here. Focal supplement remains unavailable. | Still unresolved. |
| [Adolescent sedentary behaviour and anxiety](https://doi.org/10.1017/s0033291720004948) | Funding evidence and a new ORCID work record inspected; conflicting Glyn/Gemma author attribution remains. | Still unresolved; institutional/author confirmation could settle responsibility. |
| [Disability and cervical screening](https://doi.org/10.1016/j.socscimed.2025.117807) | Same-cohort companion confirms demographic questionnaire; original-prompt judgment changes UNCLEAR to YES. | New demographic exclusion supports NO, independently of the successful retrieval. |

The most useful remaining manual downloads are [the fertility survey-list supplement](https://pmc.ncbi.nlm.nih.gov/articles/instance/8989246/bin/NIHMS1785582-supplement-1.pdf) and [the MRI paper’s supplementary methods](https://static.cambridge.org/content/id/urn%3Acambridge.org%3Aid%3Aarticle%3AS0033291722001490/resource/name/S0033291722001490sup001.docx). PMC returned a browser-download interstitial; the Cambridge file returned a server error, with alternate routes also unsuccessful. A later philanthropy conversion-script version also remained unavailable. These are supporting-source gaps, not missing main papers. Download availability alone will not resolve author-role or questionnaire-definition ambiguities.

The API returned YES for all three rechecks. Source QA accepts the cervical result under the original wording; it does not accept the other two YES judgments. The clinical answer inferred participant questionnaires from clinician ratings and a generic cohort battery. The philanthropy answer inferred response reuse from inclusion of an earlier author-collected study. This illustrates why source-grounded adjudication is needed after model output. All raw responses and the reasons for retaining uncertainty are preserved privately.

## Limits and next verification

Some saved sources are accepted manuscripts or earlier working papers. Those versions and incomplete supporting-source access are recorded in the workbook and review reasoning. Complete main-text availability does not guarantee access to every appendix or establish equivalence to the final published version.

This 620-article collection includes previous prompt-development examples and replacements selected for retrievability. It is useful for diagnosing behavior, but is not an untouched holdout or a basis for estimating the prevalence of eligible research across all publications. The source reviews also combine session agents with the subsequently authorized API pass; the protocol records the split.

RA verification should include a documented random sample plus a separately identified sample of disagreements, uncertain ownership and questionnaire/task boundaries. Human verification should challenge both agreement and disagreement cases, because shared AI mistakes are possible. Preserve the current initial judgments and adjudications so the metrics can be recalculated after verification.
