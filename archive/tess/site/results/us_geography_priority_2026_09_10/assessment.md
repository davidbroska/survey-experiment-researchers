Across the compared queries, the same 120-researcher review pool contains 472 articles with US-sample evidence: 301 explicit and 171 inferred. Seven new public-PDF reviews and two contextual metadata reviews resolved nine of the 186 previously unclear articles, leaving 177 unclear among 1,042 distinct articles. The reference query contributes 1,036 of these articles, including 468 with US evidence (299 explicit; 169 inferred); its author counts use only those matching articles. The six other articles are retained for the query comparison. All articles in the combined review pool have a geography review; uncertain geography remains a separate category. These are AI-assisted annotations awaiting human validation. Geography evidence does not establish design eligibility, parser compatibility, or researchers’ ability to donate the data.

The additional reviews increase eleven researchers’ credited US article counts by one each because two articles credit more than one pool member. For example, Toby Bolsen increases from 11 to 12, Kevin J. Mullinix from 8 to 9, and Alexander Coppock from 7 to 8. The [author-change table](author_changes.csv) gives all changes and competition ranks within the same pool. Retrieval, total article counts, and first/last authorship credit are unchanged. US rankings remain conditional on this pool; they are not rankings of all researchers in the database.

Ten papers were selected before public-copy searches from the priority queue, each crediting at least one researcher in the pool’s US top 50. Seven usable PDFs were obtained and reviewed: three support explicit US geography and four support inference from US institutions or study context. US institutional context alone is coded inferred, consistently across reviews. The two additional metadata inferences concern a US presidential decision and a study explicitly comparing Democrats and Republicans. Generic panel-provider names and author affiliations do not establish participant geography. The [ten-paper search ledger](round10_status.csv), [public review rationales](fulltext_geography_reviews.csv), [metadata rationales](metadata_review_proposals.csv), and [source validation](fulltext_review_validation.json) document the decisions. Quotes, full text, and private file paths remain private.

Three selected papers remain unresolved; unsuccessful cases were not replaced. Two are manual-download candidates. The Taylor & Francis paper is awaiting an alternative copy because the user cannot obtain papers from that publisher. Its DOI below identifies the paper; no repeat publisher download is requested. Save any obtained PDFs in the SurveyExperimentRecruitment folder using the suggested Scopus-ID filenames in the [three-paper access list](remaining_round10_downloads.csv).

| Paper | Credited researcher | Access step | Suggested PDF filename |
| --- | --- | --- | --- |
| [Benchmarks and Citizen Judgments of Local Government Performance](https://doi.org/10.1080/14719037.2013.798027) | Gregg G. Van Ryzin | Await alternative manuscript/copy | 84918780367.pdf |
| [Affect, Efficacy, and Protest Intentions](https://digitalcommons.chapman.edu/sociology_articles/129/) | Blaine G. Robbins | Try repository browser download | 105008067194.pdf |
| [Managing PFAS risk amid uncertainty](https://doi.org/10.1177/13591053251338341) | Janet Z. Yang | Manual download | 105006979320.pdf |

The Chapman repository advertises an accepted manuscript, but its download returned HTTP 403; a browser download may succeed. The other searches yielded no usable public full text. These access outcomes do not imply anything about sample geography.

Unresolved papers remain relevant to the leading researchers: 85 credit an author in the total-count top 50, 65 credit an author in the pool’s US top 50, and 172 credit one of the 114 researchers retained when ties at the total-count cutoff are included. These sets overlap. Among total-count top-50 authors, the largest remaining uncertainties are:

| Researcher | Total candidate articles | Articles with US evidence | Geography unclear | US count if every unclear article proves US |
| --- | --- | --- | --- | --- |
| Janet Z. Yang | 14 | 5 | 9 | 14 |
| Stefano Pagliaro | 10 | 0 | 8 | 8 |
| Blaine G. Robbins | 13 | 6 | 7 | 13 |
| Rasmus Tue Pedersen | 14 | 1 | 5 | 6 |
| Gregg G. Van Ryzin | 13 | 7 | 4 | 11 |

The last column is a hypothetical upper scenario, not an estimate. The [complete author-uncertainty table](author_uncertainty.csv) covers all 120 researchers. The [complete priority queue](article_priority_queue.csv) covers all 177 unresolved articles. It separates [107 access-followup candidates with earlier acquisition attempts](manual_download_queue.csv), [67 candidates without a previous public-copy check](automatic_acquisition_queue.csv), two papers whose main texts already exist but need sampling supplements, and one paper the user has reported unavailable. The latter three are not requested again in the manual-download queue.

Priority is determined by how a US resolution could distinguish tied authors, with particular attention to the top 50 under either ranking. First and last authors receive one article credit each; a sole author receives one. Coauthors credited for the same paper move together. The procedure includes every unresolved article in the fixed pool, including those of authors with no US evidence yet. It does not score names, affiliations, or a guessed probability of US sampling. A new US observation can break some ties and create others, so hypothetical impacts across papers must not be added. This targeted acquisition exercise is development work, not an independent precision-validation sample.

The initial queue and frozen ten-paper selection are archived privately. Current inputs and outputs are recorded in the [priority manifest](priority_manifest.json), and the fixed search round in the [round manifest](round10_manifest.json). Rebuild the current queue from the recruitment folder with the authorized private inputs available:

```bash
python3 results/us_geography_priority_2026_09_10/build_priority.py
```
