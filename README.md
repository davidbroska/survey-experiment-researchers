The SCORE recruitment pilot contains 620 articles: one per journal and year across 62 journals, 2016–2025. All 620 main texts are available locally, and all articles have fresh abstract annotations and provisional full-text assessments under the user's single screening prompt.

[Dashboard](score/index.html) · [Prompt](score/prompt.md) · [Abstract predictions](score/predictions.csv) · [Full-text assessments](score/fulltext_reviews.csv) · [Evaluation](score/report.md) · [Error analysis](score/error_analysis.md) · [Protocol](score/protocol.md)

`score/prompt.md` is the only active prompt. `score/annotate.py` wraps it for one article at a time and records one YES/NO/UNCLEAR response. Full-text instructions adapt input and output from that same source; the eligibility wording is shared. Session agents completed all 620 metadata labels and 551 initial source reviews. The remaining 69 source reviews used the subsequently authorized lab API key with GPT-6 Astra, at a calculated cost of $23.17. Completed judgments are retained, and the two sources of model judgments are documented separately in the protocol. Independent source checks and adjudications precede the reported comparison.

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
