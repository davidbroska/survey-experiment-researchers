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

## Small changes worth testing

I would test these two short additions before expanding the list of named datasets:

1. **“When the supplied metadata leaves the experiment’s response measures unresolved, return UNCLEAR unless another criterion clearly fails. Do not assume unmentioned questionnaires were administered.”** This clarifies the existing missing-information rule. It may improve recall by moving some NO cases into review, with a corresponding increase in review workload. It should not make those cases automatic YES decisions.
2. **“Citing an earlier study does not qualify unless its participant responses are analyzed in the present article.”** This makes the own-data reuse rule more precise and addresses an observed error in the source review.

A short optional clarification is: **“Eligible responses can be a secondary component, such as a follow-up questionnaire or covariate.”** The current “at least one set” rule already implies this. Explicit wording may improve consistency when the metadata actually mentions those responses; it cannot recover details absent from the abstract.

These are proposed edits, not demonstrated improvements. The frozen prompt has not been replaced, and no performance gain is claimed without a separate comparison. Adding a long list of possible ancillary questionnaires could instead encourage unsupported YES decisions. Broadening the external-data examples alone would not address the omissions illustrated above.

## Eligibility choices that need to stay separate from prompt accuracy

The supplied wording does not require the article to be primarily a survey, require digital administration, or exclude questionnaires used only for screening or demographic description. Consequently, documented self-report scales within clinical studies, paper questionnaires and minor questionnaire components can qualify. Making those ineligible would change the target population, rather than merely improve adherence to this prompt.

Two other boundaries deserve explicit decisions in future prompt development: task-related reports versus questionnaire beliefs/experiences, and answers that are only part of an intervention versus responses used as research data. For example, [the identity-based suspension intervention](https://doi.org/10.3102/00028312211042251) asks students to select values and write, but measures outcomes through administrative records. Internal review changed its reference from YES to UNCLEAR because the current wording does not clearly settle treatment-only responses. Its uncertainty is not a failure to download the main article.

Similarly, [fourth graders' arithmetic strategies](https://doi.org/10.1016/j.learninstruc.2020.101311) are elicited through written calculations and retrospective verbal explanations. The source explicitly describes a verbal task protocol, while the prompt includes answers about reported behavior. Internal review changed YES to UNCLEAR because a confident decision would require settling this boundary. This does not justify excluding all oral or open-ended survey questions.

Ownership also needs careful wording. Restricted access does not establish team collection, while publicly sharing one's own responses does not erase collection responsibility. The current prompt measures documented collection/commissioning and reuse; it does not establish present exclusive access, legal ownership, willingness to collaborate or permission to share data.

Source verification must also establish the correct person. For [adolescent sedentary behavior and anxiety](https://doi.org/10.1017/S0033291720004948), an initial YES linked the abbreviated coauthor G. Lewis to survey investigator Glyn Lewis. Official university records instead associate the article with Gemma Lewis. This unresolved identity link led to UNCLEAR; it is a reference-review correction, not evidence that the metadata prompt needs a longer dataset list. The evidence and links are recorded in the full-text assessment.

## Limits and next verification

Some saved sources are accepted manuscripts or earlier working papers. Those versions and incomplete supporting-source access are recorded in the workbook and review reasoning. Complete main-text availability does not guarantee access to every appendix or establish equivalence to the final published version.

This 620-article collection includes previous prompt-development examples and replacements selected for retrievability. It is useful for diagnosing behavior, but is not an untouched holdout or a basis for estimating the prevalence of eligible research across all publications. The source reviews also combine session agents with the subsequently authorized API pass; the protocol records the split.

RA verification should include a documented random sample plus a separately identified sample of disagreements, uncertain ownership and questionnaire/task boundaries. Human verification should challenge both agreement and disagreement cases, because shared AI mistakes are possible. Preserve the current initial judgments and adjudications so the metrics can be recalculated after verification.
