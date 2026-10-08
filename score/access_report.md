# Full-text collection checkpoint — 7 October 2026

The working collection has **620 articles**, one per SCORE journal and indexed
publication year for 2016–2025. **620 main texts are saved locally**
(25 HTML, 459 PDF, 136 XML); **0 cells remain unresolved**.
All 380 previously available articles were retained. The pass added
194 verified replacements and recovered 46 original selections.
See the [replacement results](replacement_report.md) for the selection procedure
and the [cell-level search record](replacement_status.csv) for attempted and untested alternatives.

Files are in `Literature/SCORE`. Some sources are manuscripts; source availability
does not establish equivalence to the final published version. PDF, XML and HTML
are recorded separately. XML/HTML extraction segments are not physical pages;
linked images and supplements may still need separate retrieval. Version and
completeness caveats are recorded in the private workbook.

Known assets to check during substantive source review include:

| Article | Source limitation |
| --- | --- |
| [Movers and shakers](https://doi.org/10.1093/qje/qjw021) | Accepted manuscript lacks numbered pages 23–34 and the cited Appendix; main body and references are present. |
| [Examining the relationship between daily changes in support and smoking around a self-set quit date](https://doi.org/10.1037/hea0000286) | Manuscript includes an Appendix.docx link stub, not the appendix itself. |
| [Really Rewarding Rewards: Strategic Licensing in Long-Term Healthy Food Consumption](https://doi.org/10.1093/jcr/ucab059) | Manuscript includes main text and tables but omits its separately referenced web appendix. |
| [Contextual Factors Predict Self-Reported Confession Decision-Making: A Field Study of Suspects’ Actual Police Interrogation Experiences](https://doi.org/10.1037/lhb0000459) | Derby manuscript has the main narrative and references but omits separate Tables 1–5 and an author/title cover. |

These are main-text copies with recorded limitations, not 620 complete publisher
versions with every table, figure and supplement. The source review must seek
missing material when it is needed to establish collection or study design.

**288 articles have substantive AI source reviews under the earlier broader criteria.** The questionnaire-focused scope chosen on 8 October has not been applied to the saved labels. The remaining
332 available articles await source review. Replacements have
blank assessment fields and basis **Not assessed**. Recovered originals retain
their earlier metadata assessments. No new eligibility labels or human
verifications were performed during this retrieval pass.

The private `SCORE_validation_620.xlsx` has **620 rows and 63 variables**, sorted
alphabetically by journal and then by year descending. Its Column guide and the
[public codebook](codebook.md) distinguish availability, actual assessment basis,
metadata judgments, source reviews and missing values.

## What worked

- The earlier API/repository pass added 82 texts: 62 through Wiley TDM, 19 through
  OpenAlex PDF content and one through OpenAlex XML. A subsequent exact-title and
  repository search added ten more, bringing the pre-replacement total to 380.
- Within-cell replacement searches tried saved candidates without topic or
  eligibility filters, then prioritized indexed open-access alternatives.
  Actual source identity and journal checks caught bibliographic indexing errors.
  An appendix-only XML was replaced by a verified main manuscript.
- Ordinary institutional browser access recovered **15 original APA papers**.
  Browser routes also delivered original Sage, Oxford and INFORMS PDFs. Earlier
  automated login/challenge responses therefore did not establish subscription
  denial or permanent publisher-wide unavailability.
- Verified PMC main-article HTML is now supported when the PDF or XML route fails.
  Abstracts, challenges, supplements and short/incomplete body extracts are rejected.

No paid API credits were used and no LLM API was called. No email-link requests
were sent: direct downloads worked before APA imposed its hourly limit.

## Current unresolved cells

| Publisher/platform | Cells without verified main text |
| --- | ---: |
| None | 0 |

The [remaining DOI queue](manual_downloads.csv) contains 0 articles.
A failed search does not prove that every article in the same journal/year is
unavailable. Alternative-candidate failures and publisher-wide workflow pauses
are preserved separately from the selected article's own retrieval record.

## Access barriers encountered and future remedies

**APA institutional downloads:** after 15 original PDFs were saved, APA explicitly
displayed its hourly full-text limit and a security-verification page. Automated
APA downloads stopped immediately. This is an observed download limit, not a
claim that Stanford lacks a subscription. No challenge was bypassed and no email
requests were made. Further institutional downloads should wait until the
publisher permits them; use the normal browser and complete any offered human
verification yourself. For a sustained corpus, ask Stanford for the supported
systematic-access arrangement described in [the access guide](systematic_access.md).

APA's [official access instructions](https://www.apa.org/pubs/databases/access/)
also document institutional-email, single-use PDF links. That option was not
needed for the successfully downloaded papers, and it was not used to work around
the later security gate. The requested destination remains private in our receipts.

**OpenAlex:** cached-content requests stopped at the guarded free daily allowance;
no prepaid balance was used. Publisher and independent public-repository retrieval
continued. For future collection extensions, retry budget-limited cached copies
after the listed daily reset rather than buying credits. Quota waits are not
publisher entitlement failures.

**Browser access:** routing checks sent APA traffic through VPN interface `utun6`,
and actual publisher PDFs were delivered through Stanford access. The Cisco CLI
did not establish the active profile name. Stanford's
[VPN instructions](https://uit.stanford.edu/service/vpn/mac_secureclient)
recommend the full-traffic profile for restricted library resources. A publisher
page loading successfully does not guarantee its PDF endpoint will succeed;
Oxford also presented a separate PDF security check for a cell subsequently
covered by a verified replacement.

All 24 initial articles with historical Springer DOIs were already available.
A missing Springer key is not blocking this collection. Scopus supplies metadata;
its key does not grant other publishers' full-text access.

## Review and publication safeguards

Independent agents checked source identities, journals, publication-year
boundaries, completeness, hashes and manuscript caveats. Indexed publication
years can precede final issue years; those differences are documented. Confirmed
wrong-journal records are excluded, and corrupted/supplement-only sources are kept
apart from accepted main texts.

Original selections and frozen predictions/reviews remain preserved. The
[new prompt](prompt_proposed.md) and [redline](prompt_proposed_redline.md) received
independent logical review against known cases, but have no new empirical
performance result. The original holdout is no longer an untouched test.
Licensed full texts, abstracts, browser access links/tokens and private correspondence
remain outside the public repository.
