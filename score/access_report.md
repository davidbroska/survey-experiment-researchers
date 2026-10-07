# Full-text collection update — 7 October 2026

The fixed sample contains **620 articles**, one per SCORE journal and year for
2016–2025. **380 usable main texts are saved locally: 248 PDFs and
132 XML documents. 240 articles still lack usable main text.**
Files are in `Literature/SCORE` in the local research workspace. Some available
copies are manuscripts or working papers; availability does not establish
identity with the final published version. Version caveats are in the workbook.

**288 articles have completed substantive AI source reviews.** The other
92 downloaded articles still await source review and retain their metadata
assessments. Downloading an article or checking its identity is not an eligibility
review. No new classifications or human verifications were performed in this pass.

The private workbook `private/score/SCORE_validation_620.xlsx` contains
**620 rows and 63 variables**, alphabetically by journal and then by year descending.
The Column guide sheet and [public codebook](codebook.md) explain every variable,
allowed values, missing meanings and current counts. Licensed text remains private.

## What we fixed before requesting manual help

The earlier credential pass recovered 82 articles: 62 through Wiley's TDM API,
19 through OpenAlex PDF content and one through OpenAlex Grobid XML. Unpaywall
lookups worked but did not themselves deliver additional usable main articles.
No paid API credits were used. No LLM API was called.

This follow-up recovered **10 more articles** by searching exact titles and
following repository and author links beyond DOI-based discovery. It replaced
two corrupt cached PDFs with intact copies and found a main manuscript for an
article previously represented only by its appendix. A bounded ERIC search
checked 33 unresolved education articles and recovered four additional PDFs.
The World Bank supplied a published QJE copy. All accepted documents had their
article identities and readable main text checked; version inspection is separate.

The downloader now records observable browser-challenge and login-page evidence
when available. HTTP 200 is not treated as full text, and HTTP 403 alone is not
called a subscription failure. Old failures without response-body evidence remain
qualified as access denial with an unestablished cause.

## What still blocks access

**The VPN is connected.** Fresh routing checks sent APA, Sage and Oxford requests
through VPN interface `utun6`. The problem is therefore not simply a disconnected
VPN. It does not follow that every publisher recognizes the connection or grants
our automated requests access.

All 62 remaining APA articles have recorded redirects to APA's login page rather
than PDFs. The official Stanford catalog's PsycArticles link was also tried; it
returned a 403 in this session. That does not establish that Stanford lacks a
subscription, or that an ordinary APA personal account would solve the problem.

Fresh representative article requests to Sage, Oxford, Chicago, INFORMS, AEA, Academy
of Management and Duke returned Cloudflare browser-security challenges. Sage
and Oxford also remained at security verification in a clean Chrome browser with
normal JavaScript enabled. These are platform probes, **not individual entitlement
checks for every missing paper**. They show why a VPN or another metadata API key
alone does not resolve the tested routes. Login sessions and institutional access
may become a separate issue after a browser challenge is cleared.

The remaining articles are distributed as follows:

| Publisher/platform | Missing articles |
|---|---:|
| Sage | 76 |
| APA | 62 |
| Oxford University Press | 38 |
| University of Chicago Press | 24 |
| INFORMS | 17 |
| American Economic Association | 11 |
| Academy of Management | 9 |
| Duke University Press | 3 |

One cached PDF remains unreadable:
[The Differential Effect of Local–Global Identity Among Males and Females](https://doi.org/10.1177/0022243719889028).
Offline repair could not recover its pages. The other two originally corrupt
copies have now been replaced. A fresh intact copy is required for this one.
This article is included in the publisher counts above.

## Practical next steps

1. Open an unresolved DOI in your regular browser through Stanford's library
   access route. Use the library's Lean Library extension or full-traffic VPN as
   described in [Stanford's off-campus access instructions](https://library.stanford.edu/services/off-campus-access).
2. For APA, start with [Stanford's PsycArticles catalog record](https://searchworks.stanford.edu/view/4685614).
   If it still fails, ask library support to check the licensed platform and
   Stanford IP recognition. Do not buy a personal subscription just to test this.
3. For the challenged publishers, complete any normal interactive verification
   yourself if offered, then try the PDF. A successful regular-browser download
   would establish access for that article; it would not automatically authorize
   or enable bulk API access. For batch retrieval, ask library staff whether an
   approved publisher TDM route or library delivery route is available.
4. Save downloaded main PDFs as `<article_id>.pdf`, using identifiers from the
   [remaining download queue](manual_downloads.csv). Import them with
   `python3 score/fetch_fulltext.py --import-local /path/to/downloaded_pdfs`.
   The importer checks identity, readable main text and file hashes. If no
   subscribed or repository copy is available, use the library's article-request
   service. Keep supplements separate.

**No article is waiting for OpenAlex free credits.** The provided Wiley and
OpenAlex credentials worked. The remaining publisher-browser barriers are not
fixed by requesting another Scopus key. All 24 sampled articles with historical
Springer DOIs were already obtained. A missing Springer API key is therefore not
blocking this sample; its licensed full-text API has separate activation rules
([Springer documentation](https://dev.springernature.com/docs/api-endpoints/fulltext-api/)).

## Copies added in this follow-up

| Article | Version note |
|---|---|
| [CAN POLLUTION MARKETS WORK IN DEVELOPING COUNTRIES? EXPERIMENTAL EVIDENCE FROM INDIA](https://doi.org/10.1093/qje/qjaf009) | Publisher-formatted article: Quarterly Journal of Economics (2025),1003–1060; obtained from World Bank hosting. |
| [What Makes a Decision Fair? Relative Earnings, Gender, and Justifications for Couples’ Decision-Making1](https://doi.org/10.1086/735618) | OSF-hosted author manuscript associated with the published DOI; equivalence to the final published version has not been established. |
| [English learner and non-English learner students with disabilities: Content acquisition and comprehension](https://doi.org/10.1177/0014402915619419) | Publisher-formatted article: Exceptional Children 82(4),428–442 (2016), with an ERIC funding cover sheet. |
| [The impact of maternal literacy and participation programs: Evidence from a randomized evaluation in India](https://doi.org/10.1257/app.20150390) | J-PAL-hosted working paper dated February 2017; title and all authors match the published article. Equivalence to the final published version has not been established. |
| [Sex Differences in Doctoral Student Publication Rates](https://doi.org/10.3102/0013189x17738746) | Publisher-formatted article: Educational Researcher 47(1),76–81 (2018); obtained from ERIC. |
| [Racing Against the Vocabulary Gap: Matthew Effects in Early Vocabulary Instruction and Intervention](https://doi.org/10.1177/0014402918789162) | Publisher-formatted article: Exceptional Children 85(2),163–179 (2019); obtained from ERIC. |
| [Paths 2 the Future: Evidence for the Efficacy of a Career Development Intervention for Young Women With Disabilities](https://doi.org/10.1177/0014402920924851) | Publisher-formatted article: Exceptional Children 87(1),54–73 (2020); obtained from ERIC. |
| [Policies That Define Instruction: A Systematic Review of States’ and Districts’ Recommendations for Evaluating Special Educators](https://doi.org/10.3102/0013189x20935039) | Boston University-hosted manuscript explicitly says it is not the copy of record and may differ from the final article; published DOI and authors match. |
| [Quality Indicators of Secondary Data Analyses in Special Education Research: A Preregistration Guide](https://doi.org/10.1177/00144029221141029) | Publisher-formatted article: Exceptional Children 89(4),397–411 (2023); obtained from ERIC. |
| [Who is healthier? A meta-analysis of the relations between the HEXACO personality domains and health outcomes](https://doi.org/10.1177/08902070231174574) | Publisher-formatted article: European Journal of Personality 38(2),342–364 (2024); obtained from the author website. |

Earlier manuscript/version caveats remain in the workbook, including the RFS
working papers, the Educational Researcher manuscript, the JPSP manuscript and
the RFS advance article. Obtaining their final versions is a version-check task,
not an additional missing-main-text count.

## Review and reproducibility

Independent agents checked recovered document identities, source versions,
workbook structure and classification boundaries. Private receipts retain failed
routes, challenge evidence, source hashes and exact-title discovery records.
The [new proposed prompt](prompt_proposed.md) and [redline](prompt_proposed_redline.md)
are untested. Frozen predictions, source labels, sample membership and historical
split assignments were preserved. The historical holdout is not an untouched
test of the latest wording.
