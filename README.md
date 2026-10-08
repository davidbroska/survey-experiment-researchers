The SCORE recruitment pilot contains 620 articles: one per journal and year across 62 journals, 2016–2025. All main texts are available locally. The current task is fresh abstract annotation followed by independent full-text review under the user's single screening prompt.

[Dashboard](score/index.html) · [Prompt](score/prompt.md) · [Abstract predictions](score/predictions.csv) · [Full-text assessments](score/fulltext_reviews.csv) · [Evaluation](score/report.md) · [Error analysis](score/error_analysis.md) · [Protocol](score/protocol.md)

`score/prompt.md` is the only active prompt. `score/annotate.py` wraps it for one article at a time and records one YES/NO/UNCLEAR response. Full-text instructions adapt input and output from that same source; the eligibility wording is shared. Session agents supply the model judgments. No paid API calls are authorized or used.

The local workbook is `private/score/SCORE_validation_620.xlsx`. It has separate Abstract screening and Full-text review sheets, each with one annotation column. Evidence and reasoning accompany the full-text annotation. Rows are grouped by journal and sorted by descending year. [Column definitions](score/codebook.md) distinguish blank pending cells from UNCLEAR judgments.

The folders are:

- `score/`: active code, one prompt, public bibliography, derived labels and dashboard.
- `inputs/`: the journal frame and private background transcript.
- `private/score/`: licensed metadata, annotation records, source receipts and workbook.
- `../Literature/SCORE/`: downloaded main articles and supporting files.
- `../Literature/SCORE_prompt_examples/`: four previously inspected development examples.
- `archive/tess/`: preserved earlier recruitment work.

Keep Python short and readable, using NumPy for numerical work and the standard library for routine files and retrieval. Use tidyverse style for R. Michael Howes's [ppi_py](https://github.com/Michael-Howes/ppi_py) is the readability reference. Prefer straightforward functions over additional frameworks.

After annotation, rebuild the outputs from this folder:

```bash
python3 -B score/review.py
python3 -B score/evaluate.py
python3 -B score/workbook.py
python3 -B score/dashboard.py
python3 -B score/publish.py
```

The public repository can stage its website with `python3 score/publish.py`; the other commands require private inputs. Superseded SCORE prompts, predictions and derived judgments were removed at the user's request. Git history retains previously published versions. Retrieval provenance and the TESS archive remain separate from current screening results.

The collection includes retained articles and access-based replacements. It is not a population prevalence sample or an untouched holdout. AI full-text judgments remain provisional; RAs will verify a subset. See the [source limitations](score/access_report.md) and [verification plan](score/ra_verification.md).
