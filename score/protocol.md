# SCORE annotation protocol

The fixed collection is 620 articles: one per journal and indexed year for the 62 SCORE journals, 2016–2025. Existing full texts and authorized replacements are retained. Selection is conditional on retrieval and includes previously examined examples; this is a development evaluation, not an untouched holdout or a probability sample of articles.

## One prompt

`prompt.md` contains the user's supplied screening wording. Markdown formatting is normalized; wording, including the duplicated “to to,” is preserved. `annotate.py` wraps it in Python, supplies one JSON object with journal title, article title, abstract and keywords, and validates one YES/NO/UNCLEAR response. Code records IDs and provenance outside model input and output. No paid API calls are used.

Fresh Codex session agents annotate the metadata one article at a time. They do not receive author lists, previous predictions, source reviews or full texts. Each agent's context contains preceding articles in its own queue; these are sequential session judgments, not independent stateless API requests. The exact API model identifier is not exposed. Prompt/input hashes, reviewer and timestamps are saved privately. The user requested deletion of earlier SCORE prompts and predictions; those artifacts are no longer inputs to the pipeline.

## Full-text reference review

The user authorized applying the same eligibility criteria to full text and supporting materials, with annotation, evidence and reasoning outputs. The Python wrapper derives these instructions from the same prompt file, adapting input and output only. A fresh source reviewer must record an initial judgment without viewing the new abstract prediction. A main-text download alone never counts as a review.

Read the article's study descriptions and methods in context. Establish who obtained which responses and whether at least one set meets both criteria. Review all reported components before NO; a paper combining external data with a qualifying questionnaire can be YES. Inspect relevant supplements, repositories or earlier study sources when needed to settle provenance or procedure. Record what was actually inspected and unresolved access limits. XML/HTML segment numbers are not physical PDF pages.

Save one annotation plus concise evidence, source locations and reasoning. Keep quotations to at most 25 words per source; lengthy licensed text stays private. Store source hashes, input pages/segments read, prompt hash, reviewer and timestamp as audit metadata. Full-text judgments are provisional AI reference assessments, not human-verified ground truth. RAs will verify a sample later.

## Evaluation and error review

Compare the abstract labels with independently recorded source labels. Show the full three-by-three table. Exclude unresolved full-text judgments from binary denominators and show their count. Report balanced accuracy, precision, recall and F1 for three explicit decisions: immediate YES (UNCLEAR is not yet selected), retention (YES or UNCLEAR), and definite answers only. Report coverage for definite-only results. Undefined denominators remain unavailable, not zero.

Review discrepancies against the actual sources before calling an abstract judgment an error. Check reference errors, unavailable abstract evidence, changes in criteria, ambiguity and input/source quality. Keep initial source labels and adjudication changes separate. Error-informed wording suggestions do not alter the frozen supplied prompt; their value requires another evaluation. Previously inspected cases remain development evidence even if they carried an old holdout label.

## Local and public outputs

The private workbook has separate abstract and full-text sheets, both sorted by journal then descending year. Each has one annotation column; the full-text sheet also has evidence and reasoning. Complete abstracts, licensed documents, credentials and correspondence remain local. Public exports contain bibliography, labels, brief source evidence and reasoning, methods and evaluation. The TESS archive is retained as historical work and does not define the SCORE frame.
