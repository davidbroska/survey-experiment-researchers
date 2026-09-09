Open the [100-researcher dashboard](TOP100.html), [Coauthor summary tab](TOP100.html#summary), or [supporting-information methods and complete query](SUPPORTING_INFORMATION.html). The **Ranking** tab has sortable researcher columns. The **Coauthor summary** tab contains the four selection steps and the complete Scopus query, with copy and download controls. A [standalone summary](EXECUTIVE_SUMMARY.html) is also available. **Survey-experiment articles** is the primary first/last-author count; **US-sample articles** combines explicit and inferred evidence from titles, abstracts, available keywords, and reviewed full texts. Click a name to inspect article evidence. [Researcher CSV](results/top100_enriched.csv) · [Geography report](GEOGRAPHY_REPORT.html).

The current pool has 870 distinct articles published in 2010–2026. Of these, 393 have US-sample evidence and 127 remain unclear. There are 65 page-cited full-text decisions, including 55 new resolutions in the latest review round (34 US-associated and 21 non-US). Two available articles still need sampling details; 125 articles lack a usable full text, including one reported unavailable. The **Full-text downloads** tab puts [top-50 tie priorities](PRIORITY_DOWNLOADS.html) first, in batches of ten. Save PDFs under the suggested filenames in `private/fulltext/inbox/`. [All manual links](MANUAL_DOWNLOADS.html) · [Review workflow](FULLTEXT_REVIEW.html). `TOP40.html` opens the same current dashboard.

Pool membership is determined by total first/last-author volume before geography review. Seventy authors share the six-article cutoff; 65 are outside the fixed 100-person display. The [cutoff table](results/top100_cutoff_ties.csv) identifies them. US sorting is conditional on this pool, not a global top 100 by US experiments. Geographic evidence does not establish original fielding, independent datasets, parser compatibility, or data ownership. The shortlist is provisional.

This folder is independent of the earlier attempts. Python 3.10 or newer and the standard library are sufficient. Run these commands from this folder:

```bash
python3 pipeline/run.py queries
python3 pipeline/run.py analyse
python3 pipeline/run.py dashboard
python3 pipeline/run.py reports
python3 pipeline/compare_years.py
python3 pipeline/build_site.py
python3 -m unittest discover -s tests -v
```

The current retrieval is stored locally, so analysis works offline. To reconstruct retrieval from the frozen investigator roster:

```bash
python3 pipeline/run.py refresh-frame
python3 pipeline/run.py counts
python3 pipeline/run.py retrieve
python3 pipeline/compare_live.py
python3 pipeline/run.py benchmark
python3 pipeline/run.py analyse
python3 pipeline/run.py reports
```

Scopus requests use `SCOPUS_API_KEY` from the environment or the parent repository's `.env`, with optional `SCOPUS_INSTTOKEN`. Abstract access needs an entitled network connection. Credentials are sent in headers and are not written to the cache. `bootstrap` is needed only when first importing the legacy seed inputs; it initially builds the old frame and should be followed by `refresh-frame`. It does not refresh or validate the TESS roster.

| Location | Contents |
|---|---|
| `pipeline/` | Query construction, cached retrieval, frame construction, matching, ranking, validation and comparison code |
| `queries/` | Complete query, equivalent API parts, original comparator, and clause definitions |
| `inputs/` | Frozen seed roster, journal links, author names, provenance, and review inputs |
| `results/` | Retrieval manifests, flow counts, bibliography, candidate ranks, cutoff ties, sensitivity results and audit summaries |
| `private/` | Licensed abstracts, raw API cache, verbatim evidence, development sample, validation queue and shortlist review dossier |
| `tests/` | Regression checks for punctuation, field boundaries, query guards, pagination, deduplication and author counting |

Complete the review tables according to [CODEBOOK.md](CODEBOOK.md), including parser compatibility and access to respondent data and survey materials, then rerun `analyse` and `reports`. Provider mentions such as Bovitz or Prolific are supporting cues, not automatic inclusion requirements. `python3 pipeline/validate.py` creates a blank validation-label table on first use and summarizes it only after every sampled record has a valid label and reviewer provenance. Its design labels alone do not establish donor eligibility. Supporting quotations and restricted Scopus payloads belong in `private/`; inspect distribution permissions before sharing them. The summary and methods files contain no abstracts or credentials.

The cache is an archived retrieval, not a request to refresh live data. To start a new snapshot, move `private/cache/` and `private/frame/` to a dated archive before running the retrieval stages. Dates and hashes are recorded; do not overwrite the prior snapshot. The article window is defined in `pipeline/query.py`. Regenerate queries and retrieval after changing it. The `benchmark` command requires the earlier `Opencall/QueryV2` development annotations and is supplementary; the main retrieval and ranking use this folder's inputs.

The roster has 109 inherited medium-confidence profile assignments and eight unresolved entries. Its legacy label “high” is not a new verification. `seed_identity_review.csv`, missing-source records, incomplete bylines, and unverified matches identify the outstanding data-quality work. First/last counting does not establish seniority or contribution and can favor particular disciplinary byline conventions. No discipline quotas or population-representativeness claim are imposed.

The dashboard join is reproducible offline from `inputs/researcher_affiliations.csv`, `inputs/article_geography.csv`, `inputs/dashboard_config.json`, the frozen ranking, and archived article metadata. `dashboard` (also available through `enrich`) validates complete pool coverage, author positions, count arithmetic, unique IDs, metadata hashes, and evidence spans. Changed pool membership or metadata requires updated annotations; stale or incomplete coverage fails explicitly. `reports` rebuilds the dashboard and supporting reports.

`inputs/fulltext_reviews.csv` holds subsequent reviewed corrections. Each requires the local source file, its SHA-256 hash, PDF page number, verbatim evidence, rationale, and reviewer provenance. `fulltext.py` extracts local text without assigning labels. The optional PDF extractor can be installed with `python3 -m pip install -r requirements-pdf.txt`; an existing `pdftotext` executable is also supported. Plain UTF-8 `.txt` files work with the standard library. Scanned PDFs need OCR or manual transcription. Metadata labels remain intact when full-text decisions update counts for all credited authors. The [codebook](CODEBOOK.md) defines these fields.

The earlier `top40_*` geography input and enriched result CSVs remain historical snapshots; `top40_provisional.csv` is regenerated by the current analysis. The current canonical inputs are the unprefixed affiliation/geography tables and the current outputs are `top100_*`. Full abstracts and locally supplied PDFs remain under `private/`. The dashboard includes bibliographic metadata and short evidence spans, and makes no network requests when opened; its links open external source pages only when selected.

Browser integration checks use Node's standard library and an isolated local Chrome session: `node tests/browser_check.mjs` connects to Chrome's DevTools port 9224. The saved check covers the three tabs, literal query and copy control, keyboard navigation, acquired-file filtering, all 12 column sorts in both directions, US sorting, article filters, searches, download batches, checklist persistence, CSV content, and mobile overflow. Screenshots are private. [GitHub Pages instructions](GITHUB_HOSTING.md) describe publishing the generated `site/` folder. The dedicated repository is [survey-experiment-researchers](https://github.com/davidbroska/survey-experiment-researchers). Its GitHub Actions workflow checks the pipeline and deploys only `site/` to Pages after a main-branch update.

The 2016–2026 baseline is preserved under `private/snapshots/2016_2026_before_extension/`. `pipeline/extend_years.py` appends only 2010–2015 to this immutable baseline, checking that the query phrases and journal frame agree. The retained 2016–2026 API partitions keep their original, logically equivalent lower bound. [Year-window comparison](YEAR_WINDOW_COMPARISON.html) separates changes in years, pool composition, and PDF review. `compare_years.py` requires the baseline snapshot; it reports both historical dashboards and the same current researchers under both windows. Current curated inputs retain 910 articles and 108 profiles across the two cohorts; each dashboard validates and exports only its selected pool.

Public-PDF acquisition is a separate, resumable stage:

```bash
python3 pipeline/open_access.py
python3 pipeline/fulltext.py
python3 pipeline/run.py reports
python3 pipeline/build_site.py
```

The acquisition stage needs public internet access and a PDF text extractor. It matches DOIs against OpenAlex open locations, with exact-title fallback, and incorporates primary author or institutional URLs in `inputs/open_access_sources.csv`. The first run freezes its source queue under `private/open_access/source_queue.csv`; a new review cohort requires archiving this acquisition directory before starting a new run. Responses and failures are cached. Each acquired PDF must have a PDF header and bibliographic title/DOI evidence on its opening pages before entering the inbox. Supplements are named separately. SHA-256 hashes and source URLs are recorded in `results/open_access_acquisition.csv`; article availability is reconciled against actual local files when rebuilding the dashboard. An unavailable indexed copy or failed automatic request is not proof of a paywall. Acquiring or extracting a PDF never assigns a sample-geography label.

`results/fulltext_download_queue.csv` remains the complete unresolved geography inventory. `results/manual_download_queue.csv` contains only articles still needing retrieval, with new consecutive batches; `results/downloaded_awaiting_review.csv` lists available files. The downloadable website includes these checklists, but excludes all PDFs, extracted full texts, and acquisition caches.


`pipeline/review_priority.py` simulates a US-positive resolution for missing papers and prioritizes differentiation among tied researchers at competition rank 50 or better on either measure. All boundary ties are included. The module accounts for shared first/last authorship, records potential new ties, and spreads each batch across different affected pairs. Total article counts stay fixed. `inputs/manual_download_status.csv` keeps user-reported retrieval problems out of these priorities; `inputs/fulltext_followups.csv` records incomplete or inconclusive available texts. [Changes after the latest full-text round](results/fulltext_review_round_author_changes.csv) show each researcher’s updated count and rank.
