# Full-text collection update — 7 October 2026

The fixed sample still contains **620 articles**. This access pass added **82
usable main-article texts**, bringing the local collection from 288 to **370**:
238 PDFs and 132 XML documents. **250 articles still lack usable main text.**
Repository manuscripts and earlier versions are included where identified, with
explicit version caveats. Files are saved under `Literature/SCORE` in the local
research workspace.

The substantive source-review count remains **288**. The 82 newly downloaded
articles retain their existing metadata-only assessments until their methods and
collection provenance are reviewed. Downloading text does not change a label.
The original predictions, earlier prompt comparison, sample and historical
development/holdout assignments remain unchanged.

The local workbook `private/score/SCORE_validation_620.xlsx` contains all 620
articles, alphabetically by journal and then by year descending. It has separate
download, assessment-basis and source-version columns, preserves both metadata
and full-text assessments, and explains every column in its `Column guide` sheet.
It includes private abstracts and evidence and is not published on the website.

## What worked

| Route | Observed result in this pass |
|---|---|
| Wiley TDM API | The configured token delivered 62 additional main-article PDFs. Requests were paced to the provider's published limit. |
| OpenAlex cached content | The configured key delivered 19 additional PDFs and one Grobid XML article text. File identity and usability were checked separately from HTTP status. |
| Unpaywall | All 332 DOI lookups for previously unresolved articles succeeded. Returned open locations were tried; a successful lookup alone is not a downloaded article. |
| Existing publisher/repository routes | Valid prior files were preserved. Newly retrieved files were checked against the fixed article identities. |

OpenAlex reported **$0.2618 used from its $1 free daily allowance**, with $0.7382
remaining and no prepaid balance. No paid credits were used or purchased. No LLM
classification API was called. The downloader checks the available free allowance
before each cached-content request, including a fallback from PDF to XML.

Linked supporting checks for the new articles also saved 19 PDFs, 49 linked web
pages and seven repository metadata files across 35 articles. These are marked
unreviewed and are not counted as main articles. Eight additional matching
supplement candidates were kept separately.

## What needs further work

The [250-row download queue](manual_downloads.csv) records each article's DOI,
failure category and recommended action. The categories are mutually exclusive
summaries of the most useful next step; individual articles may have several
failed routes.

| Remaining issue | Articles | Next action |
|---|---:|---|
| Access denied on the routes tried | 186 | Try the DOI in a Stanford-authenticated library browser and save the main PDF; use library assistance if access still fails. |
| No usable main text returned | 60 | Inspect the publisher/library record for an alternative full text. A metadata page or link alone did not establish a usable main article. |
| Unreadable cached PDFs | 3 | Obtain a fresh intact copy. Offline repair failed; these cached bytes cannot support review. |
| Only a supplement was obtained | 1 | Download the main article; retain the supplement separately. |

No article is waiting for free OpenAlex credits. The three corrupted copies are
[local–global identity and price sensitivity](https://doi.org/10.1177/0022243719889028),
[Paths 2 the Future](https://doi.org/10.1177/0014402920924851), and the
[HEXACO and health meta-analysis](https://doi.org/10.1177/08902070231174574).
All 217 checked compressed streams were invalid; Ghostscript recovered no pages
or text. Original bytes and repair logs were preserved privately.

Five newly available copies also need a published-version check before being
treated as equivalent to the selected final journal article. These are already
among the 370 available texts, not additional missing articles:

| Selected article | Available version and caveat |
|---|---|
| [Evaluating Firm-Level Expected-Return Proxies](https://doi.org/10.1093/rfs/hhaa066), 2021 | Repository working-paper manuscript, dated 2020; published-version equivalence is unverified. |
| [Long forward probabilities, recovery, and the term structure of bond risk premiums](https://doi.org/10.1093/rfs/hhy042), 2018 | Grobid text from arXiv v1 dated January 2016; equivalence is unverified. |
| [Fostering Political Interest Among Youth](https://doi.org/10.3102/0013189x16683402), 2016 | Repository manuscript linked to the published article; equivalence is unverified. |
| [Reducing Implicit Racial Preferences: III](https://doi.org/10.1037/pspi0000339), 2021 | Repository manuscript with bundled supplements; manuscript stage and equivalence are unverified. |
| [Learning to Disclose](https://doi.org/10.1093/rfs/hhaf033), 2025 | Typeset advance article with the correct DOI but provisional year/page information; final paginated-version equivalence is unverified. |

To add a library download, name it `<article_id>.pdf` using the queue's identifier,
then run `python3 score/fetch_fulltext.py --import-local /path/to/downloaded_pdfs`.
The importer checks identity and readable main text and preserves existing
verified files. Supplements should not be named as main articles.

## Springer and the VPN

Read-only checks confirmed Cisco VPN was connected and requests to the Springer
API used a VPN interface. A sampled Springer PDF download returned a real PDF
over that connection. All **24 sampled articles with historical Springer DOIs**
were already available, including older Experimental Economics and Demography
articles as well as Journal of the Academy of Marketing Science.

The same connection received HTTP 401 from the full-text API when no API key was
provided. No Springer API key is configured or was created in this task.
Springer's developer portal requires an account and API key, and its licensed
full-text endpoint requires separate activation under a special agreement.
VPN access does not create those credentials. See the
[official full-text API documentation](https://dev.springernature.com/docs/api-endpoints/fulltext-api/)
and [account/key instructions](https://dev.springernature.com/docs/support/faqs/).
There is no outstanding Springer-download task for these 24 sampled papers.
For future API use, sign in to the portal and confirm full-text activation before
supplying a key locally; a metadata API key alone does not establish that access.

Stanford's current instructions specify a full-traffic VPN connection for
restricted library resources. See [Stanford off-campus access](https://library.stanford.edu/services/off-campus-access).

## Checks and records

Independent agents checked the new article identities, source hashes, repository
versions, workbook ordering and assessment provenance. Existing XML sources also
passed a stricter title/DOI check against the article's own structural metadata.
Credential routing, cached failures, free-budget enforcement and request pacing
were tested offline. Detailed retrieval receipts, raw files and audit records
remain private. The [proposed prompt edits](prompt_proposed_redline.md) are a
separate, untested proposal; no new eligibility classification was run here.
