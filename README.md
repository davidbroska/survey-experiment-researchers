Open the [researcher ranking](DASHBOARD_NARROWER.html). It defaults to US-sample article counts and retains total survey-experiment candidate counts alongside them. Both columns are sortable. [Coauthor summary](COAUTHOR_SUMMARY.html) · [Methodology and Scopus query](METHODOLOGY.html).

The selected query retrieves **9,365 distinct journal articles** published in 2010–2026 within a recorded set of 3,401 journals used by TESS investigators. Each article contributes once to each distinct first or last author; a sole author receives one credit. Candidate donors need not have participated in TESS.

The US ranking compares a fixed **120-person review cohort**, including all 114 researchers at or above the total-count top-100 cutoff and six previously screened candidates. Its **1,035 distinct credited articles** include **483 with US-sample evidence** (306 explicit; 177 inferred) and **153 with unclear geography**. US inference may use American study contexts; author affiliations or generic panel names do not establish sample country. Every cohort article has a geography judgment, but uncertain cases remain unresolved. This is a ranking within the reviewed cohort, not a completed ranking of every Scopus author.

The latest 17 supplied PDFs are archived privately and have source-validated geography reviews. Ten support US samples, six support non-US samples, and one needs further sample-location clarification despite its full text being available. Separate design notes record experimental eligibility and parser concerns; these flags do not silently change candidate counts. [Review records](results/coauthor_update_wave2_2026_09_10/geography_reviews.csv) · [Design review notes](results/coauthor_update_wave2_2026_09_10/design_parser_flags.csv).

Counts describe articles, not independent datasets. AI-assisted annotations await human validation; experimental eligibility, parser suitability and access to respondent data and treatment materials need confirmation before invitations. Institutions, departments, countries and roles are joined from sourced profiles. The country column concerns researchers’ institutions; the US-sample count concerns participants.

Run from this folder. The public package can regenerate the dashboard and coauthor documents without private source files:

```bash
python3 pipeline/variant_dashboards.py
python3 pipeline/recruitment_methods.py
python3 pipeline/build_site.py
python3 -m unittest discover -s tests -v
```

With the restricted local retrieval and review snapshots available, apply source-validated geography updates first:

```bash
python3 pipeline/coauthor_fulltext_update.py --validate
python3 pipeline/coauthor_fulltext_wave2.py --aggregate
python3 pipeline/query_ranking_geography.py
python3 pipeline/variant_dashboards.py
python3 pipeline/recruitment_methods.py
python3 pipeline/build_site.py
```

Full retrieval reproduction requires an entitled Scopus connection and the recorded journal-source frame. The [literal selected query](queries/proximity_specific_2026_09_10/primary_plus_specific.txt), versioned inputs, article memberships, author credits and source hashes are retained for auditability. Original PDFs, full abstracts, extracted page text and supporting quotations remain under `private/` and are omitted from the website.

New requested PDFs may be saved in `SurveyExperimentRecruitment/` with the Scopus-ID filename provided by the dashboard. Each subsequent review round should preserve previously issued packets and judgments. Importing a file does not assign geography or design eligibility.
