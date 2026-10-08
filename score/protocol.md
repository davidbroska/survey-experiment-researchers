# SCORE annotation protocol

The fixed collection is 620 articles: one per journal and indexed year for the 62 SCORE journals, 2016–2025. Existing full texts and authorized replacements are retained. Selection is conditional on retrieval and includes previously examined examples; this is a development evaluation, not an untouched holdout or a probability sample of articles.

## One prompt

`prompt.md` contains the user's supplied screening wording. Markdown formatting is normalized; wording, including the duplicated “to to,” is preserved. `annotate.py` wraps it in Python, supplies one JSON object with journal title, article title, abstract and keywords, and validates one YES/NO/UNCLEAR response. Code records IDs and provenance outside model input and output.

Fresh Codex session agents annotate the metadata one article at a time. They do not receive author lists, previous predictions, source reviews or full texts. Each agent's context contains preceding articles in its own queue; these are sequential session judgments, not independent stateless API requests. The exact API model identifier is not exposed. Prompt/input hashes, reviewer and timestamps are saved privately. The user requested deletion of earlier SCORE prompts and predictions; those artifacts are no longer inputs to the pipeline.

After all 620 metadata labels and 551 initial source reviews were saved, the user authorized the lab's API key for subsequent annotation. Completed session judgments are retained. The remaining 69 source reviews use independent GPT-6 Astra API requests under the verified lab organization, with medium reasoning and the same eligibility wording. Each request supplies one article's complete extracted text, with numbered pages/segments and normalized whitespace; it contains no abstract prediction or previous source judgment. Supporting material not supplied to a request is not treated as inspected. API records distinguish pages supplied from session reading receipts and retain exact input hashes, model, settings, raw outputs and token usage privately. The process change is reported; this is not a homogeneous benchmark of API predictions. The run stops at $100.

All 69 API requests completed, with calculated usage costing $23.17 and no paid retries. Twenty-two initial citation validations failed because of PDF column order or line-break hyphenation. Same-page reading-order extraction resolved 19 without altering the returned text. For three, the reviewer inspected the rendered PDF page and shortened the excerpt without changing its meaning, label or reasoning. Raw responses, original citations and correction records are retained. Substantive source adjudications are recorded separately from these extraction corrections.

## Full-text reference review

The user authorized applying the same eligibility criteria to full text and supporting materials, with annotation, evidence and reasoning outputs. The Python wrapper derives these instructions from the same prompt file, adapting input and output only. A fresh source reviewer must record an initial judgment without viewing the new abstract prediction. A main-text download alone never counts as a review.

Read the article's study descriptions and methods in context. Establish who obtained which responses and whether at least one set meets both criteria. Review all reported components before NO; a paper combining external data with a qualifying questionnaire can be YES. Inspect relevant supplements, repositories or earlier study sources when needed to settle provenance or procedure. Record what was actually inspected and unresolved access limits. XML/HTML segment numbers are not physical PDF pages.

Save one annotation plus concise evidence, source locations and reasoning. Keep quotations to at most 25 words per source; lengthy licensed text stays private. Store source hashes, input pages/segments read, prompt hash, reviewer and timestamp as audit metadata. Full-text judgments are provisional AI reference assessments, not human-verified ground truth. RAs will verify a sample later.

## Evaluation and error review

Compare the abstract labels with independently recorded source labels. Show the full three-by-three table. Exclude unresolved full-text judgments from binary denominators and show their count. Report balanced accuracy, precision, recall and F1 for three explicit decisions: immediate YES (UNCLEAR is not yet selected), retention (YES or UNCLEAR), and definite answers only. Report coverage for definite-only results. Undefined denominators remain unavailable, not zero.

Review discrepancies against the actual sources before calling an abstract judgment an error. Check reference errors, unavailable abstract evidence, changes in criteria, ambiguity and input/source quality. Keep initial source labels and adjudication changes separate. Error-informed wording suggestions do not alter the frozen supplied prompt; their value requires another evaluation. Previously inspected cases remain development evidence even if they carried an old holdout label.

## Local and public outputs

The private workbook has separate abstract and full-text sheets, both sorted by journal then descending year. Each has one annotation column; the full-text sheet also has evidence and reasoning. Complete abstracts, licensed documents, credentials and correspondence remain local. Public exports contain bibliography, labels, brief source evidence and reasoning, methods and evaluation. The TESS archive is retained as historical work and does not define the SCORE frame.

## Recheck of the 13 unresolved references

The user asked whether the 13 UNCLEAR results were abstract predictions or full-text judgments. They were full-text judgments;111 metadata predictions were UNCLEAR. All 13 main texts were saved and readable. The follow-up checked relevant methods and collection responsibility, retried supporting sources and preserved every original judgment. Downloading a main text does not establish that every appendix is available.

Three cases with recovered supporting material received new independent GPT-6 Astra API reviews with medium reasoning and `service_tier="flex"`. These requests contained the complete saved main text plus identified supporting documents or explicitly marked workbook excerpts, without prior labels or abstract predictions. Flex was explicitly requested and confirmed in all three responses, with no standard-tier fallback. Source and input hashes, returned text and usage remain private. Calculated additional cost was $1.70; cumulative usage was $24.87 of the authorized $100. No paid retries were made.

A valid JSON response is not sufficient evidence of a correct classification. Independent agents and the primary reviewer checked the returned reasoning against the underlying methods and analysis files before any adjudication. One citation check failed because the PDF layout extraction interleaved columns; the exact quotations were verified on the stated pages in reading order. That formatting issue is separate from the substantive eligibility decision.

The user subsequently clarified that demographic questions used only to describe a sample do not qualify on their own, while questionnaire answers collected as part of an intervention qualify even if those answers are not analyzed. Proposed prompt amendments record both decisions. The existing prompt and its metadata predictions remain frozen: the reported metrics do not test the new scope. A census of all 620 saved source judgments identifies cases to revisit consistently, including existing YES cases, before a revised-scope evaluation.
