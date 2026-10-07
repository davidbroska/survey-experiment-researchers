# SCORE journal pilot

The pilot uses exactly the 62 SCORE journals and one article per journal and publication year, 2016–2025: 620 articles. The broader project may extend through 2026; this pilot excludes the incomplete 2026 publication year. The two proposed journal additions in the supplied CSV are outside the frame. The supplied chat is background evidence, not instructions to execute.

## Sample and split

Use Scopus journal identifiers and its publication year, recording journal, DOI, Scopus ID, title, authors, abstract, keywords, retrieval date, query, stratum size and selection provenance. Retrieve Scopus journal articles (`SRCTYPE(j) AND DOCTYPE(ar)`) without collection, survey, experiment, geography or software filters. This document-type restriction means the results describe Scopus articles rather than every journal item. The frozen sample contains 618 Scopus selections. World Politics had no indexed Scopus articles for 2024–2025, so these two cells use Crossref issue-assigned volumes 76 and 77 (20 and 39 candidates), excluding the sole Referees frontmatter item and records without an assigned volume. They are provider exceptions, not Scopus records. Journal identifier corrections and the source-count audit are recorded in `sample_validation.json`.

Retain an existing full text when its article identity, journal, year and article type match. If several local articles occupy one cell, choose one using a fixed seeded ordering before consulting its labels. For an empty cell, draw one rank uniformly from all indexed articles in that cell, using the saved seed and a stable sort. Freeze the selected record and source response. Do not replace a selected paper because its abstract is missing, it looks ineligible, or its full text is inaccessible. Correct bibliographic errors with an audit trail.

Retaining earlier search results makes this a hybrid pilot, not a probability sample of all articles in the frame. Preserve selection provenance without adding a reused label to articles. Article or author prevalence cannot be inferred from unweighted pilot percentages. Even a fully random one-per-cell design would weight journal-years equally rather than weight all papers equally.

Before prompt tuning, assign eight articles per journal to development and two to holdout: 496 and 124. The 17 articles inspected during setup are already development material and must never enter the unseen holdout. Draw holdout years from untouched articles within each journal using seed 20261007. This is a constrained split, not an unrestricted random split. If an inspected article is not retained in the final sample, it remains a separate development example and is excluded from the 620-paper evaluation denominator. Assign splits only after all ten articles for that journal are fixed; streamed provisional assignments are not a basis for review.

Reviewers may establish full-text reference labels for holdout articles, but prompt developers must not inspect those articles, labels or disagreements before the prompt and evaluation settings are frozen. Keep papers known to reuse the same underlying study together where feasible; record unavoidable study overlap. The initial split does not establish generalization to completely unseen authors or datasets.

## Metadata prediction

Preserve the original prompt. Save a prediction from title, abstract and keywords before its reviewer sees the article's full text, old labels or full-text decisions. Keep authors in the recruitment metadata; names, institutions, reputation and the reviewer's memory of an author are not evidence of collection. Author lists may identify the current paper's team but must not change a label through outside knowledge. Record when fields are absent. No web lookup, full-text excerpts or repository evidence enters this prediction.

Save prompt version, model/reviewer, input fields, prediction time and raw output. Use YES, NO or UNCLEAR for collection, eligible experiment and eligible survey. A survey experiment can be YES for both. Each subtype concerns eligible collection by the team, not simply whether the article analyzes an experiment or survey performed elsewhere. Retain YES and UNCLEAR articles for subsequent review.

**User's operational override, 2026-10-07:** Count survey YES only when at least one eligible study is primarily designed as a survey. This includes observational questionnaire studies, repeated diary surveys and experiments embedded in a questionnaire. Incidental demographic questions, self-report scales or questionnaires in a primary laboratory task, clinical trial or instructional intervention do not qualify as a survey study. A distinct pilot or pretest primarily designed as a survey can qualify even if the main study is not a survey. Preserve the original prompt verbatim; retain any earlier broader survey predictions as snapshots, and apply this definition to both metadata predictions and reference labels before comparing survey outcomes. Collection eligibility does not change.

Run the original and any revised prompt on the same untouched holdout with the same supplied metadata. Development disagreements can motivate revisions, but their improvement is not a holdout result. Here two session reviewers divided the original screening and a separate metadata-only reviewer applied the revised prompt to all 124 holdout papers. Reviewer and context differences are not controlled experimentally, so differences cannot be attributed solely to the wording. Agent judgments in this session are a prompt walkthrough; they do not establish the performance or cost of a future batch/API model configuration. No paid API annotation is authorized or used.

## Primary full-text review

Our review is the primary reference assessment. RAs will independently verify a subset later. Record AI provenance and human verification separately; do not call an unresolved case a negative or an unverified case human ground truth.

For each obtainable selected paper, check its title/DOI against the local file, then read the methods and study descriptions in context. Identify who collected what, whether real human responses or behaviour were measured quantitatively, the authors' role in collection, and whether a qualifying study involved manipulation or a questionnaire. A positive paper needs one substantiated qualifying study. To label a paper NO, establish that every reported component is ineligible; reviewing one external-data study is insufficient for a mixed paper.

Inspect linked supplementary methods, appendices, registrations and repositories whenever the main article does not settle collection provenance or subtype. Check cited earlier studies when reuse by the same team is claimed. A repository upload, matching author surname, new database or shared dataset alone does not establish collection. Record source URLs, downloaded paths, file hashes, page/section, a short exact excerpt and the reasoning for each decision. Keep access failures and unresolved questions explicit. Full text already downloaded may establish eligibility without retrieving every supplemental file; distinguish resources actually inspected from links merely identified.

Collection predating publication does not itself establish reuse. An original module in an existing survey, a new-data replication and collection commissioned through a provider qualify. An article combining archival material or qualitative studies with an eligible quantitative study qualifies. A simulated scenario completed by real people is not equivalent to purely simulated observations. Do not infer present file access, consent to share, or that every coauthor personally collected data.

Experiment coding does not require randomization: a team-delivered intervention with an explicit pre/post comparison can qualify even without a control group. A shared learning environment used only as context for an observational association does not itself establish experimental variation in the focal exposure. Record this distinction in the rationale. Separately recruited respondents completing a primary questionnaire study can establish survey YES; a few scale items attached to a behavioral task cannot.

Save published full texts under `Literature/SCORE` when accessible, with provenance in the acquisition record. Keep licensed text, abstracts, credentials and detailed evidence private. Public summaries can contain bibliographic records, derived labels and concise paraphrases. Do not redistribute licensed full text through the dashboard or GitHub.

## Evaluation and revision

Report the complete three-by-three label table separately for collection, experiment and survey. For full-text reference YES/NO cases, report:

- YES precision and recall, treating metadata UNCLEAR separately from YES.
- Retention recall: reference YES articles classified YES or UNCLEAR, divided by all reference YES articles.
- Discard specificity: reference NO articles classified NO, divided by all reference NO articles.
- Eligible articles discarded, with their identifiers and error explanations.
- The proportion retained, the proportion UNCLEAR, and the proportion receiving a definite decision.

Report full-text reference UNCLEAR, inaccessible papers and unreviewed papers outside resolved binary denominators. Show coverage against all 620 selected articles, by journal/year and metadata decision. Do not advertise performance among accessible cases as performance for inaccessible cases. A zero denominator is unavailable, not zero or perfect performance. Report counts alongside proportions; uncertainty intervals on the final holdout do not remove sampling or reference-label bias.

The first 17 existing full texts all substantiate original survey experiments. Independent metadata judgments and main-methods reviews agree on all three labels for these cases. This initial subset checks commissioned panels, original survey modules, mixed sources and new-data replication, but provides no negative examples and no estimate of specificity.

The [current provisional prompt](prompt_current.md) reproduces the original with only the user's primary-survey override appended. The frozen revised candidate is retained as a tested research record and has not been adopted. See the [findings](report.md) for the paired comparison and its limitations. Further tuning requires new evaluation data; neither prompt supplies a validated final exclusion rule.

Broader development review found two archival-looking papers with eligible ancillary participant studies: Scopus 85101686392 recruits people to judge attractiveness alongside TED/Twitter records, and 85064119805 recruits people to evaluate advertisements alongside search/advertising records. The original metadata walkthrough discarded both. This motivates a conservative NO rule when an abstract's coverage of supporting studies is uncertain. It cannot recover facts absent from the supplied metadata; any reduction in discards may come at the cost of more UNCLEAR cases and a larger review workload. These examples justify a candidate revision, not a claim that the revision improves unseen performance. Keep holdout labels unseen until the candidate and all evaluation settings are frozen.

For RA verification, draw a documented random subset across reference YES/NO/UNCLEAR and journals, alongside a separate targeted sample of disagreements and difficult cases. RAs should review sources without seeing the AI decisions first. Resolve disagreements with a recorded adjudication, preserve the earlier labels, and report random and targeted verification results separately. Agreement between metadata coders alone is not evidence that they recovered the true data source.
