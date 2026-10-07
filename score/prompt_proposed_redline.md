# Proposed prompt: changes from the current operational version

This proposal has not been evaluated or adopted. It preserves the confirmed rule that documented reuse of the team's own data qualifies. The 620 papers are now a working development and validation collection; their historical holdout results do not validate this new wording. No new classifications have been run. Frozen prompts and predictions remain unchanged.

**Bold adds text; ~~strikethrough~~ removes text.** The prompt has also been shortened and reorganized. Unchanged wording is plain.

~~Using only the supplied title, abstract, and keywords, assess whether the article provides evidence that its authors or their research team collected or commissioned quantitative human participant data for their research.~~

**Using only the supplied title, abstract, keywords and author list, assess whether the authors or their research team collected or commissioned quantitative human participant data. Use the author list only to identify the team.**

~~What qualifies: Measuring people’s responses or behavior through a research procedure designed, conducted, or commissioned by the author team. Include experiments, surveys, behavioral tasks, diary studies, repeated measurements, and structured observations, whether online or offline and in any country. Collection through a survey firm, panel provider, or research partner qualifies, including an original module added to an existing survey.~~

**What qualifies**

**The team measured people’s responses or behavior through a research procedure it conducted or commissioned. Include experiments, surveys, behavioral tasks, diary studies, repeated measurements and structured observations, in any country. Collection through a survey firm, panel provider or research partner qualifies, including an original module added to an existing survey.**

~~Apply these rules:~~

~~1. Include a paper if at least one study qualifies, even when other studies use external data. Replications with new participant data qualify. Earlier data collected by the same team also qualify when its role in collection is explicit; note this reuse.~~

~~2. Do not count merely analyzing, assembling, linking, or coding existing external surveys, administrative records, documents, or digital traces as participant data collection. Exclude papers containing only reviews, theory, simulations, qualitative research, or plans for future collection.~~

~~3. Distinguish collection from design. An experiment involves researcher-imposed variation in a condition or intervention. A behavioral task alone does not establish an experiment. A natural experiment or other causal analysis does not establish that the authors collected data.~~

~~4. Interpret language in context. “We recruited,” “we administered a survey,” “we randomly assigned participants,” and descriptions of participants completing a study procedure can support inclusion, but none is required. “Participants,” a sample size, “survey data,” or “a novel dataset” alone is insufficient. Descriptions of another team’s study do not count.~~

~~5. Do not require a particular platform, private data, or statistically significant findings. Do not infer present access, ownership, or permission to share.~~

**What does not qualify**

**Exclude papers that only analyze data collected by other researchers, organizations or agencies outside the author team, without a qualifying collection role for the team. Examples include secondary analyses of existing General Social Survey (GSS), American National Election Studies (ANES), European Social Survey (ESS), Panel Study of Income Dynamics (PSID), Health and Retirement Study (HRS), or National Longitudinal Study of Adolescent to Adult Health (Add Health) data.**

~~Return the following:~~

~~Collection: YES if eligible collection is stated or clearly implied; NO if the article clearly contains only ineligible research; UNCLEAR if collection or its source cannot be determined. Missing information is not a NO.~~

**Merely downloading, purchasing, obtaining access to, analyzing, combining, or coding other people’s existing data does not qualify. Neither do new analyses, subsets or derived measures made from those data. This includes existing government census or tax records, company financial records, newspaper archives and social-media posts collected or produced by others. Exclude papers containing only reviews, theory, computer simulations, qualitative research or future collection plans.**

~~Eligible experiment and eligible survey: YES, NO, or UNCLEAR for each. A survey experiment can be YES for both. Identify any other eligible collection method.~~

**Apply these rules**

**1. Include a paper if any study qualifies, including a pilot, pretest or validation study, even when its main analysis uses external data. A dataset’s name does not automatically exclude the paper. Check for an original module, commissioned collection or another qualifying study. Replications with new participant data qualify.**

**2. Reanalysis of the team’s own earlier data qualifies when its collection or commissioning role is explicit. Flag this reuse separately. Do not infer that role from author names, affiliations or dataset citations alone.**

**3. Public availability does not disqualify team-collected data. The criterion is responsibility for collection or commissioning, not legal ownership, exclusivity or permission to share. No particular platform or statistically significant result is required.**

**4. Recruitment, survey administration, random assignment and participants completing a research procedure can establish collection in context. A sample size, “participants,” “survey data” or “novel dataset” alone cannot. Descriptions of other teams’ studies do not count.**

~~Evidence: Up to two short exact excerpts, plus one sentence explaining the decision and any missing information. Note earlier collection by the team when applicable.~~

**Designs**

**An experiment involves researcher-imposed variation in a condition or intervention. A behavioral task, natural experiment or causal analysis alone does not establish an eligible experiment.**

~~Software and recruitment providers: Record only names explicitly associated with the authors’ study, keeping these two categories separate; otherwise report “not stated.”~~

~~Retain YES and UNCLEAR cases for subsequent review.~~

**Count a survey only when an eligible study is primarily designed as a survey. Include observational questionnaires, repeated diary surveys and survey experiments using vignettes or other questionnaire manipulations. Incidental demographics or self-report scales within a laboratory task, clinical trial or instructional intervention do not qualify as survey studies. Questionnaires used only to record behavioral or perceptual task responses do not make those tasks surveys. A distinct primary-survey pilot or pretest can qualify. A survey experiment can be both.**

~~User's eligible-survey override, 2026-10-07: Count survey YES only when at least one eligible study is primarily designed as a survey. This includes observational questionnaire studies, repeated diary surveys and experiments embedded in a questionnaire. Incidental demographic questions, self-report scales or questionnaires in a primary laboratory task, clinical trial or instructional intervention do not qualify as a survey study. A distinct pilot or pretest primarily designed as a survey can qualify even if the main study is not a survey. This definition overrides any broader interpretation of eligible survey above; collection eligibility does not change.~~

**Return**

**- Collection: YES when qualifying team collection is stated or clearly implied. NO when the description supports only analysis of others’ data or other ineligible research. UNCLEAR when collection responsibility or provenance cannot be determined. Missing provenance is not NO; a hypothetical omitted study does not by itself require UNCLEAR.**

**- Eligible experiment and eligible survey: YES, NO or UNCLEAR separately. If collection is NO, both are NO. If collection is UNCLEAR, neither can be YES; use NO only when that design is ruled out and UNCLEAR otherwise. Identify other eligible methods.**

**- Evidence: Up to two short exact excerpts and one sentence explaining the decision, collection responsibility and missing information.**

**- Team-data reuse: “stated” for explicit reuse of the team’s earlier collection; otherwise “not stated.”**

**- Software and recruitment providers: Record names explicitly associated with the authors’ study separately; otherwise “not stated.”**

**Retain collection YES and UNCLEAR for subsequent review.**

## Why these changes

1. The exclusion now directly identifies data collected by people or organizations outside the author team. Named examples include GSS and ANES plus ESS, PSID, HRS and Add Health; the latter four appear in the sampled abstracts.
2. Collection or commissioning responsibility determines eligibility. Public release and legal ownership do not. Documented reuse of the team's own data, commissioned fieldwork and original modules remain eligible.
3. Mixed papers retain eligibility when a pilot, validation study or other component qualifies. Dataset names alone are not exclusion rules. The pilot found both external-data-only papers and mixed papers using familiar datasets alongside team collection.
4. NO remains available when the supplied description supports secondary analysis only. Unknown responsibility remains UNCLEAR, without repeating the earlier candidate's blanket abstention for archival-looking work. The proposal needs new evaluation data before any performance claim.

Dataset names were checked against their official documentation: [GSS](https://gss.norc.org/about-the-gss.html), [ANES](https://electionstudies.org/about-us/), [ESS](https://www.europeansocialsurvey.org/about/participating-countries), [PSID](https://psidonline.isr.umich.edu/Guide/FAQ.aspx), [HRS](https://hrs.isr.umich.edu/), and [Add Health](https://addhealth.cpc.unc.edu/). These examples identify data sources, not automatic exclusion labels. Historical pilot findings remain in [report.md](report.md).
