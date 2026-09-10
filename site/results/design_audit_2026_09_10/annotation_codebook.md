This audit evaluates **candidate retrieval**, separately from donor eligibility. The target is an article reporting at least one human experiment that varies communicated content or question presentation and measures respondents' judgments, attitudes, beliefs, intentions, preferences, or comparable survey responses. Original experiments using hypothetical cases and vignettes qualify across substantive disciplines. An article can contain eligible and ineligible studies. Do not equate one article with one experiment or dataset.

Code each record from the supplied title, abstract and author keywords. Do not use author reputation, journal reputation, search-route membership, or presumed country. The coding packets omit author identities and query membership. Do not open full text for the probability sample: unresolved abstract evidence is recorded as unclear, making assessment reproducible at the indexed-metadata level. The separately identified counterexample audit may use full text and must not be mixed into precision estimates.

Use these fields:

| Field | Values and rule |
|---|---|
| design | yes: sufficient evidence of an actual eligible experiment; no: clearly not eligible; unclear: insufficient design detail. A named survey experiment reported as conducted supplies design evidence, but a general discussion of this method does not. |
| new_data | yes: authors report collecting/fielding data; no: review, simulation, synthesis or explicitly secondary-only analysis; unclear: origin is not stated. A statement that authors conducted an experiment is sufficient abstract evidence. |
| text_treatment | yes: reading, wording, written information, or a text/vignette manipulation is identifiable; no: clearly exclusively nontext; unclear: modality missing or ambiguous. Mixed text/video designs may contain a text treatment. |
| parser_compatible | no: only conjoint/discrete-choice profile combinations, an adaptive conversation, or a clearly incompatible intervention; unclear: usual default without questionnaire/full methods; yes only if actual structure establishes compatibility. Do not assume every factorial vignette is conjoint. |
| geography | US_explicit: explicit US residents/adults or equivalent sample statement; US_inferred: respondent context supports US residence but not explicit; non_US: explicit exclusively elsewhere; mixed_includes_US: explicit multination sample includes US; unclear: geography unresolved. US topics alone do not establish location when a foreign sample is stated. A vendor does not establish country. |
| rationale | One concise, original sentence identifying the design evidence or specific ambiguity. |
| evidence_quote | Private short verbatim span from a supplied field; support design classification rather than copying the abstract. |
| evidence_field | title, abstract, or keywords. |
| reviewer / reviewer_type / human_validated | Named coding agent; AI_assisted; false. |

Clinical treatments, training programs, physical interventions, brain scans, motor/perceptual laboratory tasks, and actual field behavior followed by a questionnaire are not automatically survey experiments. If the available account clearly describes only such work, code design=no. If the account could contain an eligible self-administered content experiment but lacks enough detail, code unclear. Survey-style judgments of hypothetical medical, legal, or workplace scenarios may qualify; the subject matter itself is not an exclusion. Ordinary observational surveys, interviews, algorithm benchmarks, synthetic-respondent experiments, reviews, and meta-analyses without new eligible experiments are design=no. A discussion of future experiments is not evidence that an experiment occurred.

Do not impose national representativeness or vendor exclusions. Do not infer possession of raw data, PI status, willingness to donate, or availability of a questionnaire. These are later researcher-level checks. First/last authorship remains the counting rule after article screening, with sole authors counted once.

Report yes/no/unclear separately. The share with affirmative abstract evidence is not gold-standard precision; unknowns are not automatically false positives. Any interval reported from an AI-coded random sample describes sampling uncertainty only, not annotation error. A held-out sample is disjoint from query development; human adjudication remains required before manuscript claims about validated precision.
