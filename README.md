The active project is the [SCORE recruitment pilot](score/index.html): 620 articles,
one from each of 62 journals in each year 2016–2025. Recruitment includes researchers
who collect quantitative human participant data, in any country. Experiments and
studies primarily designed as surveys have separate labels.

[Findings](score/report.md) · [Review protocol](score/protocol.md) ·
[Journal frame](score/journals.csv) · [Article list](score/articles.csv) ·
[Revised prompt (untested)](score/prompt_proposed.md) · [Original + survey definition](score/prompt_current.md) ·
[Verbatim original](score/prompt_original.md) ·
[Tested candidate](score/prompt_revised.md) ·
[Proposed edits](score/prompt_proposed_redline.md) · [Current access report](score/access_report.md) ·
[Spreadsheet codebook](score/codebook.md) · [Replacement results](score/replacement_report.md) ·
[Publisher access steps](score/systematic_access.md)

The latest revised prompt defines collection first and gives explicit instructions
and JSON formats for each variable. It has passed internal review but has not
been evaluated empirically. Existing decisions preserve their original criteria.
The earlier tested candidate remains a historical result. Audit NO decisions before
final exclusion. Session reviewers and contexts differed in the original comparison;
that comparison does not isolate wording effects or validate a future model.

The substantive AI source review is the primary, provisional assessment. RAs will verify a
sample; no labels have yet been human verified. Metadata screening and source
review are stored separately. Unavailable full text is unresolved, never a NO.
This session uses agents and incurs no paid API annotation spending.

The working validation collection has 620 journal/year cells. The user authorized
replacing unavailable or corrupt articles with retrievable alternatives in the
same cell, keeping the 380 articles already available. Candidates are tried in a
fixed order within retrieval phases without topic or eligibility filters; later attempts
prioritize open-access alternatives. Selection is conditional on access.
Original sample files and comparisons are preserved separately. Replacement
articles have no inherited decisions or historical evaluation assignments.
The local workbook
`private/score/SCORE_validation_620.xlsx` contains every article, grouped
alphabetically by journal and ordered by year descending. Its `Column guide`
sheet explains each column, its type, allowed values and missing-value meaning in order.
The public codebook contains the same definitions and aggregate counts. Download availability, actual assessment
basis, metadata decisions and completed source reviews remain distinct.
New downloads of original articles retain metadata-based assessments until source
review is completed. Replacement articles without assessments have blank labels.
The workbook includes private abstracts and evidence and is kept off GitHub.
Available main texts may be PDFs, XML, or verified PMC article HTML. The workbook
records source-version caveats; XML/HTML document segments are not physical pages,
and linked figures or supplements may require separate retrieval.

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
python3 score/replacement_report.py
python3 score/coverage.py
python3 score/workbook.py
python3 score/dashboard.py
python3 score/publish.py
```

The public repository can rebuild the website from committed derived outputs
using only `python3 score/publish.py`. Full analysis requires the local private
files. Screening judgments were made by session agents; the scripts do not call
an LLM API or pretend to reproduce those judgments automatically.

The original draw is preserved in `score/articles_initial.csv`; its historical results
continue to use that snapshot. `score/replace_sample.py` applies the privately staged
replacement records after verifying the full texts and journal/year identities.
The initial sampler refuses to overwrite an active replacement sample.
`score/fetch_fulltext.py --help` describes retrieval retries. Existing entitled
Scopus credentials are read from the environment or the parent project's `.env`.
Do not publish credentials, full abstracts, PDFs, extracted text or the supplied
conversation transcript.

The [manual download queue](score/manual_downloads.csv) lists articles still
missing usable main text after current retrieval attempts. The
[access report](score/access_report.md) records the latest counts, working API
routes and remaining tasks. Provider logins, subscription coverage and browser
challenges can differ even while the Stanford VPN is connected.

The downloader reads `SCOPUS_API_KEY`, `WILEY_TDM_TOKEN` (or `WILEY_API_KEY`),
`OPENALEX_API_KEY` (or `OPEN_ALEX`), and optional `UNPAYWALL_EMAIL` from the local
environment or the parent project's `.env`. It never prints credential values.
If the Unpaywall email is not saved there, supply `--unpaywall-email` on the
command line. `--openalex-content` tries cached open copies only while a verified
free daily allowance remains. It does not purchase credits.

```bash
python3 score/fetch_fulltext.py --retry-failures --openalex-content
```

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
