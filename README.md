The active project is the [SCORE recruitment pilot](score/index.html): 620 articles,
one per journal and year across 62 journals, 2016–2025. All 620 main texts are
available locally; 288 have earlier AI source reviews under broader criteria.
Recruitment now targets primary questionnaires completed by participants through
a digital interface, including survey experiments. RAs will verify a sample of
the source assessments after the new criteria are applied.

[Article list](score/articles.csv) · [Screening prompt](score/prompt_proposed.md) ·
[Spreadsheet codebook](score/codebook.md) · [Access and source limitations](score/access_report.md) ·
[Review protocol](score/protocol.md) · [Historical findings](score/report.md)

The private workbook, `private/score/SCORE_validation_620.xlsx`, contains all
articles and a column guide, sorted by journal and descending year. Availability,
metadata judgments and substantive source reviews are separate. Downloading a
document does not establish that it has been reviewed. Some sources are
manuscripts with missing supporting assets, recorded in the workbook.

The proposed prompt separates team collection, primary-survey design, participant
digital completion and in-scope survey experiments. Its questionnaire focus has
not been evaluated or applied to stored labels. Article IDs stay in code and data; the model receives bibliographic
content and returns assessment fields only. Code attaches the corresponding ID
to the result. Existing labels preserve the criteria used when they were made.

The collection retains 380 previously available articles, recovers 46 original
selections and replaces 194 within the same journal and year. Selection depends
on full-text access. The [replacement log](score/replacements.csv) and
[selection report](score/replacement_report.md) document this process.
Private initial article/access snapshots remain inputs to the historical
evaluation. Completed construction scripts and duplicate public snapshots have
been removed; their public versions remain in Git history.

The folders are:

- `score/`: active code, prompts, bibliography, derived assessments and dashboard.
- `inputs/`: journal frame and private background transcript.
- `private/score/`: licensed metadata, source receipts, assessments and workbook.
- `../Literature/SCORE/`: main articles and supporting documents.
- `archive/tess/`: preserved earlier recruitment work.

Keep Python short and readable, using NumPy for numerical analysis and the
standard library for routine files and retrieval. Use tidyverse style for R.
Michael Howes's [ppi_py](https://github.com/Michael-Howes/ppi_py) is the readability
reference. Prefer a few clear functions over classes or layers of helpers.

From this folder, rebuild the derived outputs:

```bash
python3 score/review.py
python3 score/evaluate.py
python3 score/coverage.py
python3 score/workbook.py
python3 score/dashboard.py
python3 score/publish.py
```

Full analysis requires the private files. The public repository rebuilds its
website with `python3 score/publish.py`. Screening judgments are made by session
agents; these scripts do not call an LLM API. No paid API annotation is authorized.

`python3 score/fetch_fulltext.py --help` describes supported retrieval and local
PDF import. Provider credentials come from the environment or the parent `.env`;
PDF extraction requires Poppler's `pdftotext`. Keep credentials, full abstracts,
full texts, extracted text and private correspondence off GitHub.

Prepare a fresh blinded RA packet after the available articles have source
assessments under the questionnaire-focused criteria. Earlier blank drafts and
their obsolete generator were removed. The [verification protocol](score/ra_verification.md)
describes the future draw.

The previously published [TESS dashboard](archive/tess/DASHBOARD_NARROWER.html)
and public source archive remain available. TESS journals and U.S. restrictions
do not define the SCORE frame.
