# Proposed prompt: section-by-section rewrite

This prompt reflects the questionnaire-focused scope chosen on 8 October 2026; it has not been evaluated or applied to stored labels. The frozen current, original and previously tested prompts remain unchanged. The historical holdout is not a fresh test of this proposal.

The structure and output format have been rewritten throughout. This block redline shows the complete replaced wording in ~~strikethrough~~ and the complete replacement in **bold**, rather than a fragmented word-by-word comparison. Use [the clean version](prompt_proposed.md) for screening.

## Current wording removed

~~Using only the supplied title, abstract, and keywords, assess whether the article provides evidence that its authors or their research team collected or commissioned quantitative human participant data for their research.~~

~~What qualifies: Measuring people’s responses or behavior through a research procedure designed, conducted, or commissioned by the author team. Include experiments, surveys, behavioral tasks, diary studies, repeated measurements, and structured observations, whether online or offline and in any country. Collection through a survey firm, panel provider, or research partner qualifies, including an original module added to an existing survey.~~

~~Apply these rules:~~

~~1. Include a paper if at least one study qualifies, even when other studies use external data. Replications with new participant data qualify. Earlier data collected by the same team also qualify when its role in collection is explicit; note this reuse.
2. Do not count merely analyzing, assembling, linking, or coding existing external surveys, administrative records, documents, or digital traces as participant data collection. Exclude papers containing only reviews, theory, simulations, qualitative research, or plans for future collection.
3. Distinguish collection from design. An experiment involves researcher-imposed variation in a condition or intervention. A behavioral task alone does not establish an experiment. A natural experiment or other causal analysis does not establish that the authors collected data.
4. Interpret language in context. “We recruited,” “we administered a survey,” “we randomly assigned participants,” and descriptions of participants completing a study procedure can support inclusion, but none is required. “Participants,” a sample size, “survey data,” or “a novel dataset” alone is insufficient. Descriptions of another team’s study do not count.
5. Do not require a particular platform, private data, or statistically significant findings. Do not infer present access, ownership, or permission to share.~~

~~Return the following:~~

~~Collection: YES if eligible collection is stated or clearly implied; NO if the article clearly contains only ineligible research; UNCLEAR if collection or its source cannot be determined. Missing information is not a NO.~~

~~Eligible experiment and eligible survey: YES, NO, or UNCLEAR for each. A survey experiment can be YES for both. Identify any other eligible collection method.~~

~~Evidence: Up to two short exact excerpts, plus one sentence explaining the decision and any missing information. Note earlier collection by the team when applicable.~~

~~Software and recruitment providers: Record only names explicitly associated with the authors’ study, keeping these two categories separate; otherwise report “not stated.”~~

~~Retain YES and UNCLEAR cases for subsequent review.~~

~~User's eligible-survey override, 2026-10-07: Count survey YES only when at least one eligible study is primarily designed as a survey. This includes observational questionnaire studies, repeated diary surveys and experiments embedded in a questionnaire. Incidental demographic questions, self-report scales or questionnaires in a primary laboratory task, clinical trial or instructional intervention do not qualify as a survey study. A distinct pilot or pretest primarily designed as a survey can qualify even if the main study is not a survey. This definition overrides any broader interpretation of eligible survey above; collection eligibility does not change.~~

## Replacement wording added

**Task and input**

**Identify articles reporting primary questionnaire studies in which participants answered through a digital interface and the author team collected or commissioned those responses. Include ordinary surveys and survey experiments. A computer-based task alone is outside this recruitment scope.**

**Use only the supplied title, abstract, keywords and author list. Do not search elsewhere or infer methods from author identity, affiliation or reputation. Return an assessment of the article's own research, not studies it merely cites.**

**Input is one JSON object with exactly four keys:**

**- title and abstract: strings; use "" when unavailable.
- keywords and authors: arrays of strings; use [] when unavailable.**

**Assess every reported study, including distinct survey pilots, pretests and questionnaire-validation studies. One qualifying study is enough. The same study must satisfy collection responsibility, primary-survey design and digital completion; do not combine evidence from different studies to manufacture eligibility.**

**1. collection: Did the author team collect or commission participant data used in a study reported in this article?**

**This field records who collected the quantitative participant data. A YES alone does not establish questionnaire-based recruitment eligibility; the next fields establish design and delivery mode.**

**The author team means the authors and researchers working with them on the collection project. Collection means conducting a research procedure that obtains people's responses, actions or measurements as numbers or structured categories. Commissioning means arranging for a survey firm, panel provider or research partner to collect them for the team's research. The authors need not personally recruit or interview participants.**

**Include an original survey, new participant responses in a replication, and new questions the team adds to an existing survey. Documented reuse of the team's earlier participant data also qualifies when the current article actually analyzes those data and its original collection or commissioning role is explicit. Public availability does not exclude the team's own collection.**

**Data collected by others were obtained outside this team without its collection or commissioning role. Merely downloading, purchasing, accessing, combining, recoding or reanalyzing them does not qualify. Frequent examples are existing General Social Survey (GSS), American National Election Studies (ANES), European Social Survey (ESS), Panel Study of Income Dynamics (PSID), Health and Retirement Study (HRS), or National Longitudinal Study of Adolescent to Adult Health (Add Health) data collected by others. Also exclude analyses using only existing census/tax records, company records, newspaper archives or social-media posts produced or collected by others. A dataset name alone is not decisive: an original team-commissioned module or a separate qualifying participant study can still count.**

**Exclude papers containing only theory, reviews, simulations, qualitative research or plans for future collection. Citing the team's earlier findings or combining published effect sizes is not reuse of participant data. Author overlap alone does not establish responsibility. Legal ownership, exclusive access, permission to share, country and significant findings are not criteria.**

**Assign YES when team collection is stated or clearly implied by the procedure; NO when the described research supports only ineligible sources or methods; UNCLEAR when collection or responsibility cannot be established. A sample size, “participants,” “survey data” or “new dataset” alone is insufficient. Missing evidence is not NO, but an unmentioned hypothetical study does not by itself require UNCLEAR.**

**2. primary_survey: Was an author-collected study primarily designed as a questionnaire survey?**

**In the remaining fields, author-collected includes commissioned collection and documented reuse meeting section 1.**

**A primary survey uses asking people research questions as its main procedure: for example, questions about attitudes, preferences, experiences, intentions or reported behavior. Include questionnaire-based diary studies, repeated surveys and distinct survey pilots or pretests.**

**A survey experiment can qualify: participants answer a questionnaire containing experimentally varied messages, questions or hypothetical scenarios.**

**Do not count demographic forms or self-report scales added to a laboratory task, clinical trial, physiological study or instructional intervention as a primary survey. A separate primary questionnaire study can still qualify within the same article. Standalone computerized games, reaction-time tasks and perceptual ratings of faces or sounds do not become surveys merely because responses are entered in a questionnaire or a survey platform is used.**

**Assign YES if at least one author-collected study is clearly a primary survey; NO if the described author-collected research contains no primary survey; UNCLEAR if the information does not establish the main procedure. Surveys collected only by other teams do not count.**

**3. digital_questionnaire: Did participants themselves complete that primary survey through a digital interface?**

**Qualifying interfaces include a web questionnaire, an app, or a questionnaire on a computer, tablet or phone. The study can be remote or in a laboratory. No particular software brand is required. A mixed-mode survey qualifies if the team collected some participant-completed digital questionnaire responses.**

**An explicit description such as participants completing an online questionnaire supports YES. A named platform such as Qualtrics can support digital completion when clearly connected to the participants' questionnaire procedure. Recruitment through a panel provider, digital data storage, analysis software or a platform name in isolation is insufficient.**

**Paper questionnaires later digitized, and answers entered into a device by a live interviewer, do not qualify. Neither do passive sensors, scans, physiological instruments or computerized tasks without a qualifying primary questionnaire. A paper survey plus a separate computerized game does not establish a digital questionnaire.**

**Assign YES when participant-operated digital completion of an author-collected primary survey is stated or clearly implied; NO when the described primary surveys use only nonqualifying modes; UNCLEAR when completion mode or who operated the interface is not established. Do not assume that a contemporary survey was online.**

**4. survey_experiment: Did a qualifying digital questionnaire contain experimental variation?**

**Count only experiments within a primary digital questionnaire satisfying the preceding three fields. The author team or its research partner must deliberately vary a message, question, scenario or other condition to assess its effect on respondents. Random assignment is not required.**

**An observational survey measuring naturally occurring differences is not an experiment. A policy change outside the research, a statistical causal analysis, or a separate laboratory or clinical experiment does not establish a survey experiment. An observational digital survey plus a separate paper survey experiment does not establish an in-scope digital survey experiment.**

**Assign YES if at least one qualifying digital questionnaire has this researcher-imposed variation; NO if the described qualifying questionnaires do not; UNCLEAR if the information does not resolve this design. Experiments are optional for recruitment: ordinary digital surveys qualify too.**

**5. Consistency and screening rules**

**Use exactly YES, NO or UNCLEAR for all four decision fields. Apply the fields in order: collection → primary_survey → digital_questionnaire → survey_experiment.**

**- A NO at any step makes every later field NO.
- An UNCLEAR at any step prevents YES in later fields. Use NO later only when that criterion is ruled out; otherwise use UNCLEAR.
- Every YES must concern a study satisfying all preceding criteria. Distinct studies can support a broader field, but the positive evidence for later fields must also meet the earlier criteria in that same study.**

**Code determines recruitment eligibility from the first three fields: all YES means eligible; any NO means outside scope; otherwise the article needs review. Retain eligible and unresolved articles for subsequent review. survey_experiment describes the eligible design subset and is not required for inclusion. These are metadata judgments, not full-text findings.**

**6. Supporting fields and output**

**Return one valid JSON object with exactly the ten keys below, no null values and no surrounding prose.**

**- own_team_reuse: STATED only when the article explicitly analyzes data from the team's earlier qualifying collection; otherwise NOT_STATED. STATED requires collection YES. NOT_STATED does not prove that reuse did not occur. Apply the same survey and interface rules to the earlier collection.
- evidence: Up to two exact quotations from the supplied title, abstract or keywords, totaling no more than 25 words. Each entry has exactly field (title, abstract or keywords) and quote, both strings. Use an empty list when no relevant passage is available.
- rationale: One or two sentences explaining collection responsibility, primary-survey design, digital completion and experimental variation where relevant. Distinguish evidence from uncertainty.
- software: Names explicitly associated with the authors' study, including collection or analysis software; otherwise an empty list.
- recruitment_providers: Services or organizations explicitly used to recruit or supply the team's participants; otherwise an empty list. Dataset sources and software vendors are not automatically recruitment providers.
- missing_information: A list of details needed to resolve the decisions. It must be nonempty if any decision is UNCLEAR. Do not list irrelevant omissions such as an unreported software brand when mode is otherwise established.**

**All scalar values are strings. All lists contain strings except evidence, which contains the objects defined above. Replace the illustrative text with the article-specific answer.**

<pre><strong>{
  &quot;collection&quot;: &quot;UNCLEAR&quot;,
  &quot;primary_survey&quot;: &quot;UNCLEAR&quot;,
  &quot;digital_questionnaire&quot;: &quot;UNCLEAR&quot;,
  &quot;survey_experiment&quot;: &quot;UNCLEAR&quot;,
  &quot;own_team_reuse&quot;: &quot;NOT_STATED&quot;,
  &quot;evidence&quot;: [],
  &quot;rationale&quot;: &quot;Explain the article-specific decisions here.&quot;,
  &quot;software&quot;: [],
  &quot;recruitment_providers&quot;: [],
  &quot;missing_information&quot;: [&quot;Describe what is needed to resolve the decisions&quot;]
}</strong></pre>

## Review notes

The 8 October version targets primary questionnaires that participants complete digitally, including survey experiments. Team collection, primary-survey design, digital completion and in-scope survey experiments are separate decisions. Each later YES requires the same study to satisfy the preceding criteria. Standalone computerized tasks, passive measurements and incidental questionnaires do not qualify for recruitment on their own.

The model no longer receives or returns the article identifier; code retains it. The output replaces other_methods with digital_questionnaire and replaces eligible_experiment with the narrower survey_experiment. The contract has four bibliographic inputs and ten assessment outputs.

Independent agents reviewed the wording and checked mixed-study, mode, commissioning and reuse boundaries. This is logical review, not an empirical evaluation. Existing predictions, source labels and historical results remain unchanged under their earlier broader criteria.
