Compare the three sortable dashboards, each with its own **Ranking**, **Methodology** and download tabs:

- [Original query](DASHBOARD_ORIGINAL.html): 7,302 retrieved articles; the historical local phrase check retains 7,035 candidates, of which 7,031 have author credits.
- [Core + complete clause](DASHBOARD_COMPLETE.html): 9,675 retrieved candidates, adding guarded reading and manipulation language in abstracts.
- [Core + narrower clause](DASHBOARD_NARROWER.html): 9,365 candidates; removes only `read W/3 passage*` and `manipulat* W/3 information` from the complete clause.

The expanded queries identify the same displayed top 100 and the same 114 researchers including cutoff ties. Both introduce 16 displayed researchers relative to the historical top 100; ten of the 16 displayed departures still qualify when all cutoff ties are included. Among the 114 leaders, only Janet Z. Yang’s total count differs between the expanded queries (14 complete; 13 narrower). Each canonical article credits each distinct first or last author once; sole authors receive one credit. The recommendation remains to retain the complete query for discovery and use the narrower query to prioritize screening. [Comparison report](RANKING_COMPARISON_REPORT.html) · [Side-by-side comparison](RANKING_COMPARISON.html).

The comparable US view covers the same **120 researchers and 1,042 distinct articles** across versions. All have geography judgments: **472 have US evidence (301 explicit; 171 inferred), 380 are non-US, 177 remain unclear and 13 are not applicable**. This update resolves nine previously unclear articles using seven public full texts and two metadata reviews. The expanded queries give identical US counts throughout this pool. These are conditional ranks, not a completed global US top 100. Geography combines explicit recruitment statements with justified inference from study context; affiliations and generic vendor names do not establish participant country. All annotations remain AI-assisted and await human validation. [Coverage](results/query_rankings_2026_09_10/geography_summary.json) · [Remaining article priorities](results/us_geography_priority_2026_09_10/article_priority_queue.csv) · [Author uncertainty](results/us_geography_priority_2026_09_10/author_uncertainty.csv).

The fixed 60-article benchmark now has **53 articles independently reviewed twice**: 43 agreed survey-experiment designs, nine negatives and one unresolved design disagreement. The latest eight supplied PDFs are preserved privately. Seven papers remain unavailable, including six Taylor & Francis papers affected by the user’s reported publisher-access limitation; a bounded public-copy lookup found no alternatives. Earlier 18- and 45-review stages remain frozen. Accessible-paper agreement does not establish population precision. [Benchmark inventory](FULLTEXT_BENCHMARK.html) · [Current decisions](results/benchmark_review_wave3_2026_09_10/article_consensus.csv) · [Access status](results/benchmark_review_wave3_2026_09_10/publisher_access_issues.csv).

The [historical 100-researcher dashboard](TOP100.html), its [Methodology tab](TOP100.html#summary), [summary](EXECUTIVE_SUMMARY.html) and [SI methods](SUPPORTING_INFORMATION.html) preserve the earlier cohort and query. That dashboard reviews 870 articles, with 402 US-associated and 117 geographically unclear; its counts and download priorities are historical comparators, not the expanded recommendation above. `TOP40.html` opens this historical dashboard. Its separate geography-review workflow uses `private/fulltext/inbox/` and [these instructions](FULLTEXT_REVIEW.html).

The [preceding reading/manipulation audit](PROXIMITY_AUDIT.html) documents the proposed proximity clause and diagnostic author checks. A more drastic two-block query loses 836 core candidates and is not recommended. [Coauthor summary](PROXIMITY_SUMMARY.html) · [SI draft](PROXIMITY_METHODS.html). Earlier audits below remain versioned research records; the ranking comparison above states the current recommendation.

Run commands from this folder. Public comparison artifacts can be rendered without Scopus credentials or licensed abstracts:

```bash
python3 pipeline/query_ranking_report.py
python3 pipeline/variant_dashboards.py
python3 pipeline/build_site.py
```

With the restricted local retrieval and review snapshots present, rebuild the all-author counts, verify them, and apply geography reviews:

```bash
python3 pipeline/query_rankings.py rank
python3 pipeline/query_rankings.py verify
python3 pipeline/query_ranking_geography.py
python3 pipeline/query_ranking_report.py
python3 pipeline/variant_dashboards.py
```

Full Scopus reproduction and evidence-span validation require the private licensed inputs; the public repository supplies queries, manifests, memberships, annotations and rendered results. `python3 pipeline/query_rankings.py enrich --allow-network --workers 4` obtains missing complete bylines with an entitled Scopus connection. Cached enrichment works without `--allow-network`.

To reproduce the latest eight-paper benchmark extension with its private evidence present:

```bash
python3 pipeline/benchmark_review_wave3.py --validate private/benchmark_review_wave3_2026_09_10/reviews_coder_A.json
python3 pipeline/benchmark_review_wave3.py --validate private/benchmark_review_wave3_2026_09_10/reviews_coder_B.json
python3 pipeline/benchmark_review_wave3.py --aggregate
python3 pipeline/query_ranking_geography.py
python3 pipeline/query_ranking_report.py
python3 pipeline/variant_dashboards.py
python3 pipeline/build_site.py
```

New downloads may be placed in `SurveyExperimentRecruitment/` using the dashboard’s Scopus-ID filenames. Import subsequent benchmark PDFs into a new dated review wave: issued packets and prior coding must not be overwritten. Geography review is separate from benchmark design coding. Downloaded PDFs and verbatim sampling evidence stay under `private/`; only article metadata, labels, original rationales and source links are published. Acquisition itself assigns no study labels.

The [evidence-based search audit](SEARCH_STRATEGY.html), [short coauthor note](SEARCH_SUMMARY.html), and [new SI methods draft](SEARCH_METHODS.html) investigate the Pennycook and Richeson counterexamples. The audit covers their complete Scopus article bibliographies, 20 nominated papers, 160 fresh development articles and 100 held-out articles independently coded twice. Adding `participant*` to the remaining population gates increases the expanded search from 8,074 to 8,142 distinct in-frame articles. A shorter candidate query retrieves 18,054, but remains too noisy and incomplete for automatic ranking: both AI reviewers find affirmative design evidence in 36/41 named-design or reading candidates versus 29/59 procedure-only candidates. All annotations await human validation. The proposed workflow preserves earlier candidates, screens every route, and completes candidate bibliographies before selecting the top 100. The existing dashboard retains its earlier provisional cohort.

The [preceding query revision](QUERY_REVISION.html) retrieves 8,074 distinct in-frame articles, compared with 7,304 for a fresh run of the previous query: 788 added and 18 removed. It incorporates the requested survey-design, embedded-experiment, text/message-assignment, and information-experiment phrases. Of the added records, 628 pass the strict local phrase/context check and 160 require further match review; these are not eligibility decisions. The [initial participant diagnostic](PARTICIPANT_TERM_ASSESSMENT.md) has been corrected and superseded.

This folder is independent of the earlier attempts. Python 3.10 or newer and the standard library are sufficient for the core analysis and reports; PDF extraction has optional dependencies described below. The following `run.py` commands reproduce the historical dashboard and reports:

```bash
python3 pipeline/run.py queries
python3 pipeline/run.py analyse
python3 pipeline/run.py dashboard
python3 pipeline/run.py reports
python3 pipeline/compare_years.py
python3 pipeline/build_site.py
python3 -m unittest discover -s tests -v
```

The historical retrieval is stored locally, so its analysis works offline when the private snapshot is present. To reconstruct that retrieval from the frozen investigator roster:

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

The earlier `top40_*` geography input and enriched result CSVs remain historical snapshots; `top40_provisional.csv` is regenerated by the legacy analysis. The historical dashboard uses the unprefixed affiliation/geography inputs and `top100_*` outputs. The expanded comparison uses `results/query_rankings_2026_09_10/`. Full abstracts and locally supplied PDFs remain under `private/`. The historical dashboard includes bibliographic metadata and short evidence spans, and makes no network requests when opened; its links open external source pages only when selected.

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

Reproduce the revised-query comparison with `python3 pipeline/query_revision.py all --workers 4`, or regenerate its report offline with `python3 pipeline/query_revision.py report`. Query definitions are under `queries/revision_2026_09_10/`; result sets, cumulative contributions, local verification, and manifests are under `results/query_revision_2026_09_10/`. Licensed payloads remain in the corresponding `private/` snapshot. The existing `run.py` stages reproduce the reviewed dashboard retrieval; the dated revision stage preserves that query/count pairing while its additions await screening.

The subsequent audit is versioned separately under `participant_guards_2026_09_10`, `design_audit_2026_09_10`, and `search_strategy_2026_09_10` in `queries/`, `results/`, and `private/`. Rebuild cached comparisons and reports with:

```bash
python3 pipeline/participant_guards.py report
python3 pipeline/design_audit.py summarize
python3 pipeline/design_audit_report.py development
python3 pipeline/search_strategy.py summarize
python3 pipeline/search_strategy.py author_comparison
python3 pipeline/search_strategy_review.py
python3 pipeline/search_strategy_report.py
```

The reading/manipulation revision and original 18-review evaluation stage use separate `proximity_audit_2026_09_10` and `precision_benchmark_2026_09_10` snapshots. The commands below reproduce that historical stage; use the wave-3 commands above for the latest 53-review extension:

```bash
python3 pipeline/proximity_audit.py summarize
python3 pipeline/proximity_audit.py author_comparison
python3 pipeline/proximity_audit.py fulltext_sample
python3 pipeline/precision_benchmark.py prepare --sample results/proximity_audit_2026_09_10/fulltext_sample.csv
python3 pipeline/precision_benchmark_review.py
python3 pipeline/proximity_report.py
python3 pipeline/build_site.py
```

The sample command verifies the frozen selection and refuses changed membership or denominators; it never redraws according to availability. `precision_benchmark.py acquire` uses the same `--sample` argument to resume public-copy discovery. Source locations added to `inputs/precision_benchmark_sources.csv` take priority, and historical failed attempts remain archived. Main copies and author-manuscript versions are identified separately from design eligibility. Review files are `private/precision_benchmark_2026_09_10/reviews_coder_A.json` and `reviews_coder_B.json`; each coded axis requires original rationale and page evidence, with unknown decisions retained. Public consensus and weighted missing-label bounds include all sampled records and require human adjudication before publication precision claims.

Query hashes, journal-frame hashes, complete route memberships, development exclusions, fixed sample manifests, annotation provenance and original rationales are public. Licensed abstracts and evidence quotations remain private and are needed to validate evidence spans. The [audit codebook](results/design_audit_2026_09_10/annotation_codebook.md) separates survey design, original data, text treatment, parser compatibility and geography. The earlier broad candidate query was frozen before the 100-article validation packet was coded. The narrower proximity query was developed using the original 18 full-text reviews; later reviews remain separately identified. Separate AI coding passes are not a substitute for human validation. The new comparison ranks query candidates while preserving the historical dashboard; it does not relabel unreviewed matches as confirmed survey experiments.

The post-benchmark development revision is frozen separately under `proximity_specific_2026_09_10`. Rebuild its cached comparisons with `python3 pipeline/proximity_specific.py summarize`. This removes only two positive action/material pairs; it does not overwrite the original query, fixed sample or reviews. Query refinement and independent precision evaluation remain separate stages.
