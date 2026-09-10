"""Write the current selection method and literal query from the run outputs."""
import json
import re
from common import ROOT, digest, read_csv
import query


def reports():
    flow = json.loads((ROOT / "results" / "flow_counts.json").read_text())
    frame = json.loads((ROOT / "results" / "frame_manifest.json").read_text())
    retrieval = json.loads((ROOT / "results" / "retrieval_manifest.json").read_text())
    if flow["query_sha256"] != digest(query.build()) or retrieval["query_sha256"] != digest(query.build()):
        raise RuntimeError("Regenerate retrieval and analysis before writing reports")
    count_rows = read_csv(ROOT / "results" / "live_query_counts.csv")
    counts = {r["name"]: int(r["count"]) for r in count_rows}
    number = lambda n: f"{n:,}"
    # Change only whitespace to make the exact executed query readable.
    literal = re.sub(r" OR (?=\{)", "\n      OR ", query.build())
    if re.sub(r"\s+", " ", literal) != re.sub(r"\s+", " ", query.build()):
        raise RuntimeError("Report query differs from the executed query")
    fenced = "```text\n" + literal + "\n```"
    n_journals = number(frame["n_journals"])
    date = min(d[:10] for p in retrieval["parts"] for d in p["dates"])
    end_date = max(d[:10] for p in retrieval["parts"] for d in p["dates"])
    dates = date if date == end_date else date + " to " + end_date
    geography = None
    if (ROOT / 'inputs/article_geography.csv').exists():
        from dashboard import build
        geography = build()
    pool_size = geography['n_authors'] if geography else 40
    cutoff = geography['cutoff_article_count'] if geography else flow['top40_cutoff_article_count']
    cutoff_ties = geography['n_authors_tied_at_cutoff'] if geography else flow['authors_tied_at_cutoff']
    from coauthor_summary import content, standalone
    coauthor = content(geography, flow, frame)
    executive = coauthor['markdown']
    method = f"""**Selection of researchers for data-donation invitations.** We target researchers who have fielded survey experiments and can supply respondent-level data, treatment materials, and the corresponding survey instrument. Eligible studies manipulate material within a survey and measure respondents' judgments, beliefs, intentions, or choices. The treatment and response structure must be supported by the project's parser. Recruitment through Bovitz, Prolific, or another online panel is relevant evidence about how a study was fielded; the provider alone does not establish the authors' access to data. Text treatment and data access are coded separately. No country, sample-representativeness, or panel-provider restriction is imposed in the database query.

The journal frame is derived from the project's frozen roster of 589 TESS investigator records, containing 581 resolved Scopus author IDs. TESS provides a multidisciplinary survey-experiment platform. [TESS programme description](https://www.tessexperiments.org/info/introduction). We retrieve all journal articles by the resolved investigators through {query.END_YEAR}, without a lower publication-year bound or article-count cap, and retain every identifiable journal used by at least one investigator. This produces {n_journals} journals. Eight investigator records remain unresolved; four resolved profiles return no qualifying publications and one publication lacks an identifiable journal. Invitation candidates may be any researcher publishing eligible work in this journal frame.

We search Scopus titles, abstracts, and keywords for journal articles published in {query.START_YEAR}–{query.END_YEAR}, using the following query. Exact phrases enumerate singular, plural, and relevant hyphenated forms; broader experimental language requires survey context. The search contains positive retrieval terms and publication filters. Design compatibility is assessed during article and instrument screening.

{fenced}

Retrieval dates are {dates}. For the API, the query is executed as the union of {len(query.groups())} shorter parts, each partitioned by publication year. Expected and retrieved counts are checked, records are deduplicated by Scopus ID, and the union is intersected with the journal frame using Source IDs. A DOI check removes duplicate article records. This yields {number(flow['global_retrieved'])} records globally, {number(flow['in_frame'])} in the frame, and {number(flow['unique_articles'])} unique in-frame articles.

A local text check preserves punctuation, separates fields and keyword entries, and requires the contextual terms within the same sentence or keyword entry. It identifies {number(flow['locally_verified_candidates'])} candidates; {number(flow['unverified_match_needs_review'])} other records remain in a review queue. Scopus indexed keywords are not fully returned by the Search COMPLETE response, so a missing local match is not an exclusion. Review establishes experimental eligibility, parser compatibility, original data fielding, and access to the response data and survey materials. Article abstracts and vendor mentions alone cannot establish all these requirements.

Researchers receive one credit per eligible article on which they appear first or last. Sole authors receive one credit, and articles with multiple experiments also receive one credit. Scopus sequence numbers determine byline positions; {number(flow['incomplete_bylines_in_candidates'])} candidate records have unresolved bylines. The provisional {pool_size}-researcher review pool has a cutoff of {cutoff} articles, shared by {cutoff_ties} researchers. Numeric author ID orders ties reproducibly and determines which tied authors enter the fixed-size pool. This display order does not establish substantive differences among tied candidates. The eventual invitation list remains subject to review. Alternative journal thresholds and all-author counting are supplied as sensitivity analyses.

The current shortlist ranks query candidates. Final invitations depend on eligibility and identity checks. The journal frame, database coverage, publication frequency, and disciplinary authorship conventions can affect selection; no claim of representative disciplinary coverage, population-level precision, or recall is made.
"""
    rows = [
        ("Embedded experiments", "`{experiment embedded in a survey}`", "embedded_design"),
        ("Factorial surveys and randomized vignettes", "`{factorial survey}`, `{randomised vignette}`", "factorial_randomized_vignette"),
        ("Reading and information assignment", "`{randomly assigned to read}`", "text_assignment"),
        ("Information treatments", "`{information treatment}`", "survey_information"),
        ("Question wording", "`{question-wording experiment}`", "survey_wording"),
    ]
    table = "\n".join(f"| {label} | {example} | {number(counts[key+'_beyond_core'])} |" for label, example, key in rows)
    assessment = f"""The search identifies survey-experiment articles that can be screened for parser compatibility and data-donation potential. The full query below searches titles, abstracts, and keywords, with journal-article and {query.START_YEAR}–{query.END_YEAR} publication filters. [Download the same query](queries/recommended.txt).

{fenced}

Curly braces such as `{{survey experiment}} OR {{survey experiments}}` request exact phrases. Double quotes implement loose phrase matching, and wildcards inside braces are literal; singular and plural forms are therefore listed explicitly. [Elsevier search syntax](https://dev.elsevier.com/sc_search_tips.html). Although the documentation describes punctuation-sensitive matching, subsequent API checks returned some phrases across commas, full stops, and colons; see the [revision report](QUERY_REVISION.html). The local matcher preserves punctuation and prevents phrases from crossing title/abstract or keyword-entry boundaries. These checks address lexical matching; they do not establish study eligibility.

The following narrowly specified phrases supplement the exact design names. Their worldwide yields beyond the exact core are measured using the same publication window. Counts overlap and must not be added together.

| Term family | Example | Records beyond exact core |
|---|---|---:|
{table}

Survey context is `survey* OR questionnaire* OR respondent*`. The information-treatment branch additionally requires `random* OR experiment*`. Framing, scenario, and information-provision design labels require survey context, and vignette-based survey labels require experimental context. General phrases such as “randomly assigned” or “participants read” do not independently qualify an article. Information-provision experiments vary information available to respondents, but their administration and treatment modality still require inspection. [Haaland, Roth & Wohlfart, 2023](https://www.aeaweb.org/articles?id=10.1257/jel.20211658).

The query uses positive terms and publication filters; it does not exclude records by design keywords or recruitment provider. It can therefore retrieve an article whose design ultimately proves unsuitable for the parser. Suitability is established from the methods and, where needed, the survey instrument. A panel-provider mention does not establish that authors possess shareable response data. Similarly, “assigned to read” can describe a leaflet whose illustrations, rather than wording, are manipulated. Provider and text cues guide review and are not substitutes for eligibility decisions.

The archived search retrieves {number(flow['global_retrieved'])} records globally and {number(flow['in_frame'])} within {n_journals} journals. After DOI deduplication, {number(flow['unique_articles'])} articles remain; {number(flow['locally_verified_candidates'])} have a locally verified term match and {number(flow['unverified_match_needs_review'])} need additional inspection. An article may match indexed keywords unavailable in the downloaded metadata. Complete pagination manifests, clause counts, article evidence, and a stratified validation queue are provided. Precision and recall for parser-compatible donor studies have not yet been established.
"""
    if geography:
        method += '\n' + (ROOT / 'GEOGRAPHY_REPORT.md').read_text()
    elif (ROOT / 'inputs/top40_us_annotations.csv').exists():
        from enrich import enrich
        geography = enrich()
        explicit = geography['article_counts']['us_explicit']
        inferred = geography['article_counts']['us_inferred']
        executive += (f"\nThe [enriched top 40](TOP40.html) includes current institutions, departments, countries, and academic roles. "
                      f"Across their {geography['n_unique_articles']} distinct credited articles, abstract review identifies "
                      f"{explicit} with explicit US sample evidence and {inferred} more inferred from context "
                      f"({explicit + inferred} total). These are article counts, not independent datasets. "
                      "The AI-assisted annotations await independent validation; [evidence and methods](GEOGRAPHY_REPORT.md) accompany the table.\n")
        method += '\n' + (ROOT / 'results/geography_methods_paragraph.txt').read_text()
        method += '\nAuthor position serves as a proxy for possible PI involvement. It does not establish seniority, especially in fields using alphabetical authorship; academic roles are therefore supplied separately.\n'
    for name, text in [("EXECUTIVE_SUMMARY.md", executive), ("SUPPORTING_INFORMATION.md", method), ("QUERY_REPORT.md", assessment)]:
        (ROOT / name).write_text(text, encoding="utf-8")
        from render import render
        title = {'EXECUTIVE_SUMMARY.md': 'Researcher selection: methodology',
                 'SUPPORTING_INFORMATION.md': 'Researcher selection: supporting information',
                 'QUERY_REPORT.md': 'Survey-experiment search query'}[name]
        (ROOT / name.replace('.md', '.html')).write_text(render(text, title), encoding='utf-8')
    (ROOT / 'EXECUTIVE_SUMMARY.html').write_text(standalone(coauthor['html']), encoding='utf-8')
    print("Wrote current-method reports with the complete executed query.")


if __name__ == "__main__":
    reports()
