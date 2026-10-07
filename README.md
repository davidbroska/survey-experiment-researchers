The active project is the [SCORE recruitment pilot](score/index.html): 620 articles,
one from each of 62 journals in each year 2016–2025. Recruitment includes researchers
who collect quantitative human participant data, in any country. Experiments and
studies primarily designed as surveys have separate labels.

[Findings](score/report.md) · [Review protocol](score/protocol.md) ·
[Journal frame](score/journals.csv) · [Article list](score/articles.csv) ·
[Current prompt](score/prompt_current.md) · [Verbatim original](score/prompt_original.md) ·
[Tested candidate](score/prompt_revised.md)

The provisional screen is the original prompt plus the user's primary-survey
definition, retaining collection YES and UNCLEAR. The tested candidate remains
a research record and has not been adopted. Audit NO decisions before final
exclusion. Session reviewers and contexts differed between versions; the
comparison does not isolate wording effects or validate a future model.

The substantive AI source review is the primary, provisional assessment. RAs will verify a
sample; no labels have yet been human verified. Metadata screening and source
review are stored separately. Unavailable full text is unresolved, never a NO.
This session uses agents and incurs no paid API annotation spending.

The folders are:

- `score/`: current code, prompts, bibliography, derived labels and dashboard.
- `inputs/`: the supplied journal frame and local background transcript.
- `private/score/`: licensed metadata, retrieval receipts, frozen predictions,
  detailed source reviews and the blinded RA packet.
- `../Literature/SCORE/`: downloaded main articles and supporting documents.
- `archive/tess/`: preserved earlier recruitment work, outside the active frame.

Python uses NumPy and the standard library. Prefer short, readable functions;
use tidyverse style for R. Michael Howes's [ppi_py](https://github.com/Michael-Howes/ppi_py)
is the readability reference. PDF extraction requires `pdftotext` from Poppler.

From this folder, rebuild derived outputs from the existing private reviews:

```bash
python3 score/review.py
python3 score/evaluate.py
python3 score/coverage.py
python3 score/dashboard.py
python3 score/publish.py
```

The public repository can rebuild the website from committed derived outputs
using only `python3 score/publish.py`. Full analysis requires the local private
files. Screening judgments were made by session agents; the scripts do not call
an LLM API or pretend to reproduce those judgments automatically.

The sample is frozen. `score/sample.py export` reconstructs it from saved selections;
`score/fetch_fulltext.py --help` describes retrieval retries. Existing entitled
Scopus credentials are read from the environment or the parent project's `.env`.
Do not publish credentials, full abstracts, PDFs, extracted text or the supplied
conversation transcript.

The [manual download queue](score/manual_downloads.csv) lists the 332 articles
still missing usable main text after network retrieval attempts. Among these,
268 encountered HTTP 403 responses, 64 reached APA login pages, and 26 encountered
browser challenges; these categories overlap. The Stanford connection allowed
Scopus metadata and many Elsevier full texts, but did not provide every publisher's
browser login or download entitlement.

For an article obtained through a library browser, save the actual PDF in a local
folder as `<article_id>.pdf`, using its ID from the queue. From this folder run:

```bash
python3 score/fetch_fulltext.py --import-local /path/to/downloaded_pdfs
```

This makes no network requests. It checks the PDF signature, readable main text
and title/DOI identity, saves accepted files in `../Literature/SCORE/`, and updates
the access and manual-download tables. It skips already verified sources and
rejects mismatched articles, login pages and identifiable supplements. A new
download still needs a source review before it contributes a reference label.
Keep supplements separately; do not name an appendix as the main article.

The TESS work was already published at commit
[`e73ddb2`](https://github.com/davidbroska/survey-experiment-researchers/commit/e73ddb294a0b9a38853d8e9f5ac2525044d1d2cf).
Its [dashboard](archive/tess/DASHBOARD_NARROWER.html) and full public source snapshot
are retained. The old U.S. and TESS restrictions do not apply to SCORE.
