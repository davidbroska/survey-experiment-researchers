# Proposed screening prompt — not yet validated

This is a new proposal, not yet evaluated or adopted. It keeps the user-confirmed rule that documented reuse of the team's own data qualifies; analysis of other teams' data does not. The primary-survey definition is unchanged. The [current operational prompt](prompt_current.md), [verbatim original](prompt_original.md), and [previous tested candidate](prompt_revised.md) remain unchanged.

The 620 papers now form a working development and validation collection. Their earlier holdout results describe the earlier prompt comparison; they are not an untouched test of this proposal. No new classifications have been run.

Using only the supplied title, abstract, and keywords, assess whether the article provides evidence that its authors or their research team collected or commissioned quantitative human participant data for their research.

**What qualifies:** Measuring people’s responses or behavior through a research procedure designed, conducted, or commissioned by the author team. Include experiments, surveys, behavioral tasks, diary studies, repeated measurements, and structured observations, whether online or offline and in any country. Collection through a survey firm, panel provider, or research partner qualifies, including an original module added to an existing survey.

**Apply these rules:**

1. Include a paper if at least one study qualifies, including a distinct pilot, pretest, validation study or original survey module, even when the main analysis or other studies use external data. Replications with new participant data qualify. Reanalysis of earlier data collected or commissioned by the same team also qualifies when that role is explicit; flag this reuse separately. Do not infer a collection role from an author name, affiliation or dataset citation alone.
2. Exclude analysis or reanalysis of data collected by other teams when no qualifying team collection is described. This includes using existing General Social Survey (GSS), American National Election Studies (ANES), other external surveys, administrative records, documents or digital traces. A new analysis, a subset of existing records, new measures coded from those records, or a merged dataset does not establish participant collection. A GSS or ANES mention alone does not determine the decision: an original module, team-commissioned collection, documented reuse of the team’s own data or a separate qualifying study can establish eligibility. Exclude papers containing only reviews, theory, simulations, qualitative research, or plans for future collection.
3. Distinguish collection from design. An experiment involves researcher-imposed variation in a condition or intervention. A behavioral task alone does not establish an experiment. A natural experiment or other causal analysis does not establish that the authors collected data.
4. Interpret language in context. “We recruited,” “we administered a survey,” “we randomly assigned participants,” and descriptions of participants completing a study procedure can support inclusion, but none is required. “Participants,” a sample size, “survey data,” or “a novel dataset” alone is insufficient. Descriptions of another team’s study do not count.
5. Do not require a particular platform, private data, or statistically significant findings. Public availability does not make team-collected data ineligible. Eligibility depends on the team’s collection or commissioning role; owning, hosting or sharing a dataset is neither required nor sufficient. Do not infer present access, ownership, or permission to share.

**Return the following:**

**Collection:**

- **YES:** Eligible team collection or commissioning is stated or clearly implied, including documented reuse of the team’s earlier data. One qualifying component is enough.
- **NO:** The supplied description supports only analysis of others’ existing data, or other clearly ineligible research, with no stated or clearly implied qualifying collection component. An ordinary description of secondary analysis of other teams’ data can establish NO; it need not use the word “only” or inventory every supporting study. Do not invent an unmentioned participant study.
- **UNCLEAR:** The supplied information does not resolve whether the team collected or commissioned participant data, including cases with unresolved provenance or conflicting descriptions. Missing provenance is not a NO. Conversely, the general possibility that an abstract omits a study does not by itself require UNCLEAR.

**Eligible experiment and eligible survey:** YES, NO, or UNCLEAR for each. These labels concern eligible team collection: analyzing another team’s experiment or survey does not make either YES. If collection is NO, both are NO. If collection is UNCLEAR, neither subtype may be YES; use NO only when that design is ruled out and UNCLEAR otherwise. A survey experiment can be YES for both. Identify any other eligible collection method.

**Evidence:** Up to two short exact excerpts, plus one sentence explaining the decision and any missing information. Identify the evidence for who collected or commissioned the data.

**Team-data reuse:** Report “stated” when the description explicitly identifies analysis of data previously collected or commissioned by the author team; otherwise report “not stated.” This flag does not exclude qualifying collection, and “not stated” does not establish that collection is new.

**Software and recruitment providers:** Record only names explicitly associated with the authors’ study, keeping these two categories separate; otherwise report “not stated.”

Retain YES and UNCLEAR cases for subsequent review.

**User's eligible-survey override, 2026-10-07:** Count survey YES only when at least one eligible study is primarily designed as a survey. This includes observational questionnaire studies, repeated diary surveys and experiments embedded in a questionnaire. Incidental demographic questions, self-report scales or questionnaires in a primary laboratory task, clinical trial or instructional intervention do not qualify as a survey study. A distinct pilot or pretest primarily designed as a survey can qualify even if the main study is not a survey. This definition overrides any broader interpretation of eligible survey above; collection eligibility does not change.
