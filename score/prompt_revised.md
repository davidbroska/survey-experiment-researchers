# Revised screening prompt — development candidate, 2026-10-07

Development review found two archival-looking abstracts whose full texts contained additional participant-rating studies (Scopus 85101686392 and 85064119805). This revision clarifies when to abstain and incorporates the user's primary-survey definition. It has not yet demonstrated improved performance on an untouched holdout. The original prompt remains preserved separately.

Using only the supplied title, abstract and keywords, assess whether the article provides evidence that its authors or their research team collected or commissioned quantitative human participant data for their research. Author names may identify the paper's team; do not use their identities, reputation, your memory of their work, or external sources to infer collection.

**Qualifying collection:** Measuring real people's responses or behaviour through a research procedure designed, conducted or commissioned by the team. Include experiments, surveys, behavioural tasks, diary studies, repeated measurements and structured observations, in any country. Collection through a provider or research partner qualifies, as does an original module added to an existing survey.

1. Include the article if at least one study qualifies, including a distinct pilot, pretest or supporting study. Other components may use external data or qualitative methods. Replications with new participant data qualify. Explicit reuse of data previously collected by the same team also qualifies; flag that reuse. A collection date earlier than publication does not by itself establish reuse.
2. Merely analyzing, assembling, linking or coding existing external surveys, administrative records, documents or digital traces does not qualify. Papers containing only reviews, theory, computer-generated simulations, qualitative research or future collection plans do not qualify. A simulated scenario completed by real human participants can qualify.
3. Establish collection separately from design. An experiment involves researcher-imposed variation in a condition or intervention; a task alone does not establish manipulation. A natural experiment or causal estimate does not establish team collection. Count a survey only when at least one eligible study is primarily designed as a questionnaire survey, including repeated diary surveys and experiments embedded in a survey. Incidental questionnaires, demographics or self-report scales within a laboratory task, clinical trial or instructional intervention are insufficient. A survey experiment can be YES for both. A distinct primary-survey pretest can qualify even when the main study uses another design.
4. Interpret descriptions in context. Recruitment, survey administration, random assignment and participants completing a study procedure can support inclusion without any required phrase. A sample size, the word “participants,” “survey data” or “novel dataset” alone is insufficient. Descriptions of another team's research are not evidence about this team's collection.
5. An abstract focused on archival analysis may omit a qualifying supporting study. Do not infer that every component uses external data simply because only the main analysis is described. Use UNCLEAR when the supplied description leaves that possibility unresolved; never invent an unmentioned participant study. NO requires affirmative support that the article contains only ineligible work, such as an explicit review-only or simulation-only account.
6. Do not require a particular platform, private data or significant findings. Do not infer present access, ownership, sharing permission or each coauthor's personal role.

Return one record:

- `collection`: YES if qualifying collection is stated or clearly implied; NO only if the article clearly contains solely ineligible research; otherwise UNCLEAR. Missing information is not NO.
- `experiment`, `survey`: YES, NO or UNCLEAR for each **eligible** subtype. YES requires evidence for both team collection and that design. If collection is NO, both are NO. If collection is UNCLEAR, neither may be YES; a subtype is NO only when it is ruled out by the supplied information.
- `other_methods`: any other qualifying collection method, or “not stated.”
- `team_data_reuse`: note explicit reuse of the team's earlier data; otherwise “not stated.”
- `evidence`: up to two short exact excerpts from the supplied fields, together no more than 25 words, or an empty list if no excerpt supports the decision.
- `rationale`: one sentence explaining the decision and any missing information.
- `software`, `recruitment_providers`: separate lists of names explicitly associated with the authors' own study, or empty lists when not stated. A name can occupy both categories only if both roles are explicit.

Retain YES and UNCLEAR cases for subsequent review.
