# Proposed screening prompt — not yet validated

This proposal has not been evaluated or adopted. It preserves documented reuse of the team's own data and the user's primary-survey definition. The 620 papers are now a working development and validation collection; their historical holdout results do not validate this wording. Frozen prompts and predictions remain unchanged.

Input preparation for future use: the source CSV currently stores keywords and author lists as delimited text. Convert those fields to arrays of separate keywords and author names, preserving their wording and using the recorded separators. The JSON contract below is proposed for future calls; it does not describe or recode the inputs used for the frozen pilot.

## Task and information you may use

Determine whether the article uses quantitative participant data collected or commissioned by its author team for a study reported in the article. Use only the supplied **title, abstract, keywords and author list**. Do not search elsewhere. Use author names only to identify the team; do not infer collection from someone's identity, affiliation or reputation.

**Input format:** Supply one JSON object with these four keys:

- `title` and `abstract`: Strings containing the supplied text.
- `keywords` and `authors`: Arrays of strings, with one keyword or one author name per entry, preserving the supplied wording.

Use `""` for an unavailable title or abstract and `[]` for unavailable keywords or authors. Do not invent missing metadata.

Decide **collection first**. Then describe experiments and surveys **among the studies that qualify for collection**. Assess every study reported as part of the article's own research, including small preparatory studies (pilots or pretests) and studies checking a measure or result (validation studies), not just the main study.

## 1. `collection`: Did the author team collect or commission participant data used in a study reported in this article?

**Quantitative participant data** are people's responses, actions or measurements recorded as numbers or structured categories for research: for example, survey answers, choices in a game, response times, test scores, physiological measurements such as brain scans, or systematically recorded observations of behavior.

**The author team** means the authors and researchers working with them on the collection project. **Collected** means the team conducted the procedure that obtained these participant measurements. **Commissioned** means the team arranged for a survey firm, panel provider or research partner to collect them for its research. The authors need not personally recruit or interview participants.

Collection qualifies when at least one reported study meets this definition. This includes:

- New participant studies, including repetitions of earlier studies with new participants.
- A set of new questions the team adds to an existing survey, even if another organization runs the survey.
- Reanalysis of the team's earlier data, when its original collection or commissioning role is explicit. Record this reuse separately.
- A qualifying pilot or supporting study alongside analyses of data collected by others.

A study merely cited or summarized does not qualify, even if conducted by these authors. Earlier team collection qualifies only when the current article actually uses those participant data and the team's collection role is explicit. Citing results or combining published effect sizes in a review or meta-analysis is not itself reuse of participant data.

**Data collected by others** means data obtained by researchers, organizations or agencies outside this team, without a collection or commissioning role for the team. Merely downloading, purchasing, accessing, combining, recoding or reanalyzing those data does not qualify, even if the resulting analysis, dataset or measure is new.

Examples include using existing General Social Survey (GSS), American National Election Studies (ANES), European Social Survey (ESS), Panel Study of Income Dynamics (PSID), Health and Retirement Study (HRS), or National Longitudinal Study of Adolescent to Adult Health (Add Health) data collected by others. Also exclude analyses using only existing government census or tax records, company financial records, newspaper archives or social-media posts collected or produced by others. A dataset name alone does not exclude a paper: the team might have commissioned that collection, added new questions, or conducted another qualifying study.

Exclude papers containing only theory, reviews, computer simulations, qualitative research or plans for future collection. Publicly available data can qualify if the team collected or commissioned them. Legal ownership, exclusive access, permission to share, country, platform and statistically significant findings are not eligibility criteria.

Assign:

- **YES:** Qualifying team collection is stated or clearly implied by the described procedure. For example, the authors report recruiting participants, administering a study or arranging new fieldwork. No particular phrase is required.
- **NO:** The description supports only research that does not qualify, such as analysis of other people's existing data. Do not require UNCLEAR merely because an unmentioned study could hypothetically exist.
- **UNCLEAR:** You cannot determine whether qualifying collection occurred or who was responsible. A sample size, “participants,” “survey data” or “new dataset” alone does not establish the team's collection role. Missing information is not NO.

## 2. `eligible_experiment`: Did a qualifying study use an experiment?

An **experiment** is a study in which the author team or a research partner working on that study deliberately sets or changes a condition, treatment or intervention to assess its effect on participants. Examples include assigning different messages, treatments or game conditions. Random assignment is not required.

A **behavioral task** asks participants to perform an activity, such as making choices or responding to pictures. Recording task responses qualifies as collection when the team obtains them, but does not by itself establish an experiment.

A **natural experiment** examines a change that was not assigned as part of the research, such as a new government policy. Statistical methods that estimate whether something caused an outcome also do not establish researcher-assigned conditions or team collection. Such a paper can still qualify for collection if the team separately obtained participant measurements.

## 3. `primary_survey`: Was a qualifying study primarily designed as a survey?

A **primary survey** uses asking people questions as its main research procedure, such as a questionnaire about attitudes, experiences or reported behavior. Include repeated diary questionnaires. A distinct survey pilot or pretest, including a study testing a questionnaire, counts even when other studies are different.

A **survey experiment** varies a message or hypothetical situation within a questionnaire and compares responses. It can be YES for both experiment and primary survey.

Do not count incidental demographic questions or self-report scales attached to a laboratory task, clinical trial or instructional intervention as a primary survey. Likewise, using a questionnaire to record task responses, such as ratings of faces or sounds, does not turn a behavioral or perceptual task into a survey. Assess the study's main procedure, not whether it uses questions or a survey platform.

For both design variables:

- **YES:** At least one qualifying study clearly uses that design.
- **NO:** The described qualifying studies do not use that design, or collection is NO.
- **UNCLEAR:** The information does not establish whether a qualifying study uses that design.

If collection is UNCLEAR, neither design can be YES; use NO only when that design is ruled out and UNCLEAR otherwise. If collection is YES, either design can be YES, NO or UNCLEAR. Both designs can be YES in the same study or in different qualifying studies.

## 4. Supporting fields and output format

Return one valid JSON object with exactly the keys below: no extra keys, null values or surrounding prose. Replace the illustrative text with the article-specific answer.

- `other_methods`: List additional qualifying collection methods, such as “behavioral task” or “systematic observation of behavior.” Use an empty list if none is established or collection is not YES; do not list methods used only by other teams.
- `own_team_reuse`: “STATED” if the paper explicitly reuses data from the team's earlier qualifying collection; otherwise “NOT_STATED.” STATED requires collection YES. NOT_STATED is not proof that reuse did not occur.
- `evidence`: Up to two exact quotations from the supplied title, abstract or keywords, totaling no more than 25 words. Each object has exactly two string fields: `field` (“title”, “abstract” or “keywords”) and `quote`. Use an empty list when there is no relevant passage; never invent a quotation.
- `rationale`: One or two sentences explaining collection responsibility and the design decisions. Distinguish what the text says from what remains uncertain.
- `software`: Names of software explicitly used in the authors' study, including collection or analysis software.
- `recruitment_providers`: Names of services or organizations explicitly used for the author team's participant recruitment or supply. An organization mentioned only as the source of an existing dataset does not count. A software vendor is not automatically a recruitment provider. Do not infer a role from acknowledgments or a company name alone.
- `missing_information`: A list of unresolved details needed for these decisions. It must be nonempty if any decision is UNCLEAR; otherwise use an empty list when none is needed. Do not list absent details that cannot affect a decision, such as irrelevant keywords or unreported software.

For software and providers, use empty lists when not stated. All three decision variables must be exactly YES, NO or UNCLEAR. All non-list values are strings. All lists contain strings except `evidence`, which contains the objects defined above.

```json
{
  "collection": "UNCLEAR",
  "eligible_experiment": "UNCLEAR",
  "primary_survey": "UNCLEAR",
  "other_methods": [],
  "own_team_reuse": "NOT_STATED",
  "evidence": [],
  "rationale": "Explain the article-specific decision here.",
  "software": [],
  "recruitment_providers": [],
  "missing_information": ["Describe the information needed to resolve UNCLEAR decisions"]
}
```

Before returning, check that every YES concerns the author team's qualifying collection and that the design labels obey the collection decision. Retain collection YES and UNCLEAR for subsequent review; collection NO is a metadata screening decision, not a full-text finding.
