# Replacement search and current validation collection

The collection still contains **620 articles in 620 journal/year cells**: 62 journals, 2016–2025. All 380 previously available articles were retained. **194 unavailable, corrupt or bibliographically invalid selections were replaced**; 46 original selections were recovered. This gives **620 available main texts** and **0 unresolved cells**.

Current formats: 25 HTML, 459 PDF, 136 XML.

Completed substantive AI source reviews remain **288**. The 194 replacement articles have not been classified: their decisions are blank and their assessment basis is Not assessed. Document identity checking is separate from collection/design review. No human verification or paid LLM API annotation was performed.

| Publisher/platform of displaced or unresolved selections | Initially missing | Replaced | Original recovered | Still unresolved |
| --- | ---: | ---: | ---: | ---: |
| Sage | 76 | 65 | 11 | 0 |
| APA | 62 | 34 | 28 | 0 |
| Oxford | 38 | 36 | 2 | 0 |
| Chicago | 24 | 22 | 2 | 0 |
| INFORMS | 17 | 16 | 1 | 0 |
| American Economic Association | 11 | 11 | 0 | 0 |
| Academy of Management | 9 | 9 | 0 | 0 |
| Duke | 3 | 1 | 2 | 0 |

## How alternatives were selected

Complete Scopus article frames were saved for all 240 missing cells, containing 18,240 alternatives after excluding original selections. Candidate ordering uses a fixed seed and article identifier, without topic, collection, experiment, survey or geographic filters. Journal/source identity, publication year and article type were checked in the indexed frame. These are raw Scopus-indexed counts; the entire candidate universe has not been publisher-verified. Accepted source documents receive a separate actual-journal and identity check, and confirmed indexing errors are excluded with a recorded reason.

The first phase tries the first three candidates in that order, stopping a cell after a verified main text. The continuation tries up to ten additional Scopus-marked open-access candidates per unresolved cell in the same saved order, including green OA. Closed-access candidates skipped in that phase remain untested. The search is bounded; unsuccessful attempts do not establish that every article in a journal/year is unavailable.

At this checkpoint, **1008 distinct alternatives** have saved attempts. The initial phase accounts for 604 attempts and 100 current replacements; the open-access phase accounts for 404 attempts and 94 replacements. The [cell-by-cell status](replacement_status.csv) gives attempted and untested counts and why each search stopped. The [replacement log](replacements.csv) records old/new DOIs, rank, phase, source and version caveats.

Selection is conditional on discoverable full-text access. This is a stratified working validation collection, not a probability sample of all publications. Accessibility may correlate with research methods, so future prompt results should not be treated as population prevalence or universal accuracy.

## What the failures mean

Successful alternatives show that some cells can be filled despite failure of the original article. They do not prove that the original failure was an article-specific defect: an alternative may simply have an accessible repository copy. Login redirects and browser challenges can affect a publisher route systematically while copies elsewhere remain retrievable. A 403 response alone does not establish subscription denial. Candidate receipts separately record corrupt files, wrong documents, access barriers and free-allowance limits.

The [current DOI queue](manual_downloads.csv) contains 0 articles. For future access requests, see the [official systematic-access steps](systematic_access.md). These are project-access routes to confirm with Stanford; a Scopus metadata key does not unlock other publishers’ full texts.

## Source and historical-result safeguards

Every accepted replacement must have readable main text, an article identity check, a saved file hash and a matching extraction-cache hash. Independent review checks source versions and flags manuscripts or missing appendices. A main-text file is not proof that all supporting material is present or that a manuscript is identical to the published article.

The [original 620 selections](articles_initial.csv), frozen predictions, 288 source reviews and historical evaluation are preserved. Replacements do not inherit labels or development/holdout membership. The [latest prompt](prompt_proposed.md) has received independent internal review but has no new empirical performance result. The private workbook remains 620 rows × 63 variables, alphabetized by journal and then by year descending.
