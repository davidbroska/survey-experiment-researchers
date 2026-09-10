"""Readable audit, coauthor note and SI draft from frozen search/review artifacts."""
import json

from common import ROOT, digest, read_csv, write_csv, write_json
import design_audit as audit
import search_strategy as strategy
from render import render


def table(rows, columns):
    header = "| " + " | ".join(label for _,label in columns) + " |\n"
    header += "| " + " | ".join("---" for _ in columns) + " |\n"
    return header + "".join("| " + " | ".join(str(row.get(key,"")) for key,_ in columns) + " |\n" for row in rows)


def build():
    rdir = strategy.RESULTS
    comparisons = read_csv(rdir / "retrieval_comparison.csv")
    comparison = next(r for r in comparisons if r["comparator"] == "latest_revised")
    validation = json.loads((rdir / "validation_summary.json").read_text())
    strata = read_csv(rdir / "validation_strata_summary.csv")
    development = read_csv(audit.RESULTS / "development_strata_summary.csv")
    authors = read_csv(rdir / "author_development_comparison.csv")
    n = int(comparison["candidate_unique_articles"])
    query = (strategy.QUERIES / "candidate.txt").read_text().strip()
    previous_query = (ROOT / "queries/participant_guards_2026_09_10/revised.txt").read_text().strip()
    case_rows = read_csv(audit.RESULTS / "counterexample_retrieval_audit.csv")
    memberships = read_csv(rdir / "membership.csv")
    by_sid = {sid: r for r in memberships for sid in r["all_scopus_ids"].split("|")}
    by_doi = {audit.normalize_doi(r["doi"]): r for r in memberships if r["doi"]}
    for row in case_rows:
        member = by_sid.get(row.get("scopus_id", ""), by_doi.get(audit.normalize_doi(row["doi"]), {}))
        row["refined_candidate_retrieved"] = member.get("candidate", "false")
        row["refined_first_last_candidate_credit"] = str(row["refined_candidate_retrieved"] == "true" and row["first_last_credit"] == "true").lower()
    write_csv(rdir / "counterexample_retrieval.csv", case_rows)
    captured = sum(r["refined_candidate_retrieved"] == "true" for r in case_rows)
    author_table = []
    for researcher, full_name, old in (("pennycook", "Gordon Pennycook", 2), ("richeson", "Jennifer A. Richeson", 0)):
        candidate = next(r for r in authors if r["researcher"] == researcher and r["variant"] == "candidate")
        author_table.append({"researcher": full_name, "current": old,
            "candidate_first_last": candidate["first_last_candidate_articles"],
            "candidate_any_position": candidate["articles_any_position"]})
    prov = json.loads((rdir / "validation_packet_provenance.json").read_text())
    primary_parts = ("named_base", "named_extra", "guarded_design", "reading_assignment")
    primary_n = sum(any(r.get(k) == "true" for k in primary_parts) for r in memberships)
    primary_query = "(\n  " + "\n  OR ".join("(" + strategy.clauses()[k] + ")" for k in primary_parts) + "\n)\nAND " + strategy.query.LIMITS
    (strategy.QUERIES / "primary.txt").write_text(primary_query + "\n")
    source_note = ("The full methods of Majority No More? report original randomized experiments, but its Scopus record is classified as Review and fails DOCTYPE(ar). "
                   "The [author manuscript](https://spcl.yale.edu/media/138/download?inline=) and the archived DOI lookup document this exception. "
                   "Conversely, some records classified as Article are reviews or secondary analyses. Document type is a retrieval filter, not an eligibility decision.")
    evidence = (f"Two separate AI coding passes reviewed a fixed, disjoint sample of {validation['n']} candidate articles. "
                f"They agreed on affirmative design evidence for {validation['agreed_yes']}, agreed that {validation['agreed_no']} were not eligible survey designs, "
                f"and left {validation['unclear_or_disagreement']} uncertain or disputed. "
                f"After flagging designs that either coder identified as incompatible and records described as secondary-only, {validation['candidate_after_known_incompatibility_flags']} remained affirmative candidates. "
                "This is not confirmation of parser support or data ownership. All labels remain AI-assisted and require independent human validation.")
    concise = ("The missing researchers reveal a systematic search problem. Gordon Pennycook has two credited papers in the current full ranking; Jennifer Richeson has none. "
        "Many of their experiments describe information, prompts or exposure without a survey-experiment label. Middle authorship explains some omissions, and one Richeson article is indexed as a Review.\n\n"
        "I recommend named survey/vignette designs and randomized reading assignments as the main discovery route, with broader procedure language as a separately screened supplement. "
        "Preserve previously found candidates for review. Confirm content manipulation and respondent outcomes in the same study before awarding first/last-author credit, and complete candidate bibliographies under the same rule before selecting the top 100. The search uses no researcher names or explicit design exclusions.\n\n"
        f"The [compact candidate query](SEARCH_STRATEGY.html) retrieves {n:,} distinct articles in the existing journal frame. "
        "In the 100-article held-out check, both AI coders found affirmative design evidence for 36/41 named-design or reading candidates, versus 29/59 procedure-only candidates. "
        "The refined search raises Pennycook’s first/last candidate count to seven, but Richeson’s only to one; it still undercovers documented work. The dashboard retains its earlier provisional cohort. "
        "The manuscript should describe a candidate search plus eligibility review, with human validation completed before claims about precision or final donor rankings.\n")
    methods = ("We defined the journal frame using the complete publication histories through 2026 of the resolved investigators in a frozen TESS roster, yielding 3,401 Scopus Source IDs. "
        "Investigators outside TESS could enter the candidate pool. We searched records dated 2010–2026, limited to journal-source documents classified as articles, and intersected the results with this journal frame. "
        "Overlapping positive query parts were fully paginated, united by Scopus ID and deduplicated by normalized DOI, using Scopus ID when DOI was absent. "
        "Query texts, retrieval dates, source-frame hashes and record memberships were archived.\n\n"
        "The candidate query identifies named survey and vignette designs, contextualized framing/information/scenario designs, randomized reading assignments, and descriptions combining experimental manipulation, communicated materials and attitudinal or judgment outcomes. "
        "Named designs and population context are searched in titles, abstracts and keywords. The broader procedural branch requires its design, material and outcome evidence in titles or abstracts to reduce ambiguous matches from indexed keywords. "
        "Loose phrases and wildcards compress grammatical variants. Subsequent screening should check phrase punctuation and field boundaries while allowing population context elsewhere in the metadata. The refined search does not yet apply this local check to the complete candidate union. A lexical match does not establish that an eligible experiment was conducted.\n\n"
        "Article screening asks whether at least one study varies communicated content or question presentation for human respondents and measures their responses. Review-only, observational, simulation-only and incompatible intervention records are not credited; insufficient descriptions require full text. "
        "Text modality, original data collection, structural parser compatibility and data possession are separate decisions. National representativeness and sample vendors are not exclusion criteria or evidence of ownership. "
        "For a revised ranking, complete candidate bibliographies and eligibility review before truncating the researcher pool. Each eligible distinct article will contribute once to each distinct first or last author; a sole author receives one credit. Counts describe articles, not independent experiments or datasets. US geography is recorded separately from respondent evidence, with contextual inference distinguished from explicit statements. Current institutions, departments, countries and roles are joined separately from publication affiliations.\n\n"
        "Query development used two nominated author bibliographies, 20 challenge papers, inherited development data and a 160-article stratified audit. "
        f"The resulting query was frozen before drawing a simple random hash sample of 100 articles from {prov['n_after_development_exclusions']:,} candidates outside all development material. "
        "Exclusions used Scopus aliases, DOI and normalized title; coding packets omitted authors and search-route membership. Two AI coders independently reviewed the same titles, abstracts and author keywords. "
        "Disagreement and insufficient evidence remained unresolved. This audit estimates neither population recall nor human-validated precision; independent human adjudication remains necessary. "
        "The named-design/reading and procedure-only subgroups yielded agreed affirmative evidence for 36/41 and 29/59 articles, respectively. These subgroup descriptions were computed after coding. The broader procedure route is therefore recommended only as a separately screened supplement, not as an automatic source of ranking credit. "
        "Bibliography completion and human adjudication are proposed next stages, not completed results. The current dashboard has not been replaced by unscreened results from this query.\n\n"
        "The executed candidate query was:\n\n```text\n" + query + "\n```\n\n"
        "The full journal-frame restriction is applied using [Source IDs](results/venue_frame.csv). "
        "[Query file](queries/search_strategy_2026_09_10/candidate.txt) · [Search comparison and audit results](SEARCH_STRATEGY.html).\n")
    detailed = ("**The counterexamples expose systematic omissions. A keyword match should identify a candidate article; eligibility review should determine whether it earns ranking credit.** "
        "Broadening the query alone creates substantial false positives. Use named designs and reading assignments as the main discovery route; treat the broader procedure block below as a separately screened supplement. The tested union is not sufficiently precise for automatic ranking.\n\n"
        "Pennycook is in the complete current ranking with two first/last-author articles (shared score rank 984; deterministic display position 1,400), below the six-article top-100 cutoff. "
        "Six of his articles were retrieved; four place him in the middle of the byline. Richeson has no matches, although all 69 of her Scopus journal articles dated 2010–2026 are in the journal frame. "
        "These are not missing-journal or name-spelling problems. Among the 20 supplied examples, five Pennycook papers give first-author credit and nine Richeson papers give last-author credit. "
        "Primary-source review supports four clear first-author Pennycook examples and eight clear last-author Richeson examples; one of the latter falls outside the Article filter, leaving seven in scope. These AI-assisted judgments still require validation. "
        "The examples are development challenges, not an unbiased recall benchmark.\n\n"
        + table(author_table, [("researcher","Researcher"),("current","Current credited articles"),("candidate_first_last","Refined query: first/last candidates"),("candidate_any_position","Refined query: any author position")]) + "\n"
        "The refinement improves Pennycook’s retrieval but still finds only one first/last candidate for Richeson. This is evidence against using even the refined query as a complete productivity measure. Richeson warrants inclusion in candidate review on the documented evidence; a final rank requires the same bibliography and eligibility checks for everyone.\n\n"
        f"The refined query retrieves {captured}/20 challenge papers under the document-type and year restrictions; this is coverage of a supplied list, not estimated recall. "
        "Some clear examples omit even experimental terminology from their indexed abstract. One supplied Richeson example involves an in-person video/interviewer intervention, and other examples combine several study types. "
        "They should not all be treated as uncomplicated parser-ready positives. [Paper-by-paper retrieval audit](results/search_strategy_2026_09_10/counterexample_retrieval.csv) · "
        "[Primary-source design audit](results/design_audit_2026_09_10/counterexample_source_audit.csv).\n\n" + source_note + "\n\n"
        "The existing local matcher also rejects 196 records with intact design phrases and the required context elsewhere: 171 elsewhere within a field and 25 across fields. "
        "This differs from a false phrase such as survey followed by a comma or full stop and experimental. Literal phrase integrity and the relationship between a study's design and sample need separate checks. "
        "[Local-filter diagnostic](results/design_audit_2026_09_10/local_guard_diagnostic_counts.json).\n\n"
        "We compared three short discovery alternatives, reviewed 160 fresh records in four disjoint strata, and then froze a refinement. "
        "The new sample excluded the inherited development data, nominated authors and challenge papers. Each stratum below contains 40 articles; pooling these equally sized strata would misrepresent their different population sizes.\n\n"
        + table(development, [("stratum","Development stratum"),("design_yes","Affirmative design evidence"),("design_no","Not eligible"),("design_unclear","Unclear")]) + "\n"
        "The broad concept and exposure variants were too noisy. The refinement retains productive named designs and randomized reading assignments, requires title/abstract evidence for its broader procedure route, uses a human-context gate, and avoids the ambiguous perception/preference and text-prefix terms in that branch. "
        "The term text* can reach words such as texture; the revised branch uses text, textual and written. These changes concern research methods rather than the topics or names of the nominated researchers.\n\n"
        f"The requested addition of participant* to the framing/scenario and embedded-survey clauses separately increases the expanded query from 8,074 to 8,142 distinct in-frame articles (+68, no losses). "
        "The embedded-survey change adds none because every phrase already contains survey. "
        "[Complete participant-expanded query](queries/participant_guards_2026_09_10/revised.txt) · [Comparison](results/participant_guards_2026_09_10/retrieval_comparison.csv).\n\n"
        f"The compact candidate contains {len(query):,} characters versus {len(previous_query):,} in that expanded query. "
        f"It retrieves {n:,} distinct articles in the 3,401-journal frame: {int(comparison['added']):,} additions and {int(comparison['lost']):,} losses relative to the 8,142-article query. "
        "These are retrieval changes, not gains in verified experiments. [Full comparison](results/search_strategy_2026_09_10/retrieval_comparison.csv) · "
        "[Overlapping route counts](results/search_strategy_2026_09_10/route_counts.csv).\n\n"
        "```text\n" + query + "\n```\n\n"
        f"The first, second and fourth blocks recognize named designs or reading assignments and together retrieve {primary_n:,} distinct candidates. The third supplies another {n-primary_n:,} candidates and is a supplementary discovery route. Every route requires eligibility screening before counting. "
        "For separate use, download the [named-design and reading query](queries/search_strategy_2026_09_10/primary.txt) and the [procedure supplement](queries/search_strategy_2026_09_10/procedure.txt). These are projections of the frozen query, not terms fitted after validation. "
        "The quoted phrases are loose Scopus phrases; wildcards abbreviate word endings. "
        "[Elsevier documents this syntax](https://www.elsevier.support/scopus/answer/how-can-i-best-use-the-advanced-search). "
        "Our [cached punctuation probes](results/query_revision_2026_09_10/field_checks.csv) also show that braces cannot be relied on to eliminate every punctuation-boundary match. "
        "No researcher names, topic terms, vendor restrictions or explicit design exclusions appear in this candidate.\n\n"
        + evidence + "\n\n"
        + table(strata, [("stratum","Held-out subgroup"),("sample_n","Reviewed"),("agreed_yes","Both affirmative"),("agreed_no","Both negative"),("unclear_or_disagreement","Unresolved"),("candidate_after_known_incompatibility_flags","After known incompatibility flags")]) + "\n"
        f"The two AI passes agreed on the three-way design classification in {validation['raw_design_agreement']:.0%} of cases. "
        "This agreement is not an estimate of truth, and shared errors remain possible. The held-out sample concerns candidate articles outside development material, not all retrieved articles or all survey experiments. "
        "[Both coding passes and consensus](results/search_strategy_2026_09_10/validation_consensus.csv) · "
        "[Unresolved survey-design cases](results/search_strategy_2026_09_10/validation_unclear_queue.csv). This queue concerns design uncertainty; parser support or original data collection can remain uncertain even for affirmative designs.\n\n"
        f"Preserve the {comparison['lost']} candidates absent from the new query for screening; the union with the previous search contains {n+int(comparison['lost']):,} distinct articles. A separate post-validation [review of all 14 losses](results/search_strategy_2026_09_10/lost_record_review.csv) judged 13 eligible and one outside the target. Several describe outcomes as ratings, perceptions, acceptability or willingness to pay, illustrating the cost of narrowing outcome vocabulary. These additional AI-assisted judgments informed retention, not changes to the frozen query. Query revision should not silently erase prior evidence.\n\n"
        "Before rebuilding the ranking, confirm study eligibility across this corpus and apply the same first/last rule to everyone. Define a candidate pool from eligible first/last authors and the existing TESS investigator roster, then check their complete 2010–2026 journal bibliographies before truncating to 100 researchers. "
        "Retain the same journal frame; log document-type exceptions for review rather than silently changing filters. Bibliography completion can recover studies whose abstracts omit search vocabulary, but cannot prove coverage of researchers absent from both discovery and the roster. Audit a random sample of unmatched articles within the frame to assess remaining omissions. Report screening coverage and uncertainty rather than treating unreviewed papers as zero. "
        "A missing search match is not evidence that a researcher lacks data. The current dashboard remains the documented, provisional earlier cohort. "
        "[Concise coauthor note](SEARCH_SUMMARY.html) · [Supporting-information draft](SEARCH_METHODS.html) · [Dashboard methodology](TOP100.html#summary).\n\n"
        "Reproduce cached search comparisons with python3 pipeline/design_audit.py summarize and python3 pipeline/search_strategy.py summarize; "
        "reproduce coding checks with python3 pipeline/design_audit_report.py development and python3 pipeline/search_strategy_review.py; "
        "then run python3 pipeline/search_strategy_report.py. Licensed metadata are required for evidence-span validation and remain private. "
        "The public files contain query text, hashes, memberships, bibliographic metadata, original annotation rationales and summary counts.\n")
    for name, text, title in (("SEARCH_SUMMARY", concise, "Survey-experiment search: coauthor note"),
                              ("SEARCH_METHODS", methods, "Survey-experiment search: supporting-information draft"),
                              ("SEARCH_STRATEGY", detailed, "Survey-experiment search audit and revised strategy")):
        (ROOT / (name+".md")).write_text(text)
        (ROOT / (name+".html")).write_text(render(text, title))
    write_json(rdir / "report_provenance.json", {"query_sha256": digest(query),
        "primary_query_sha256": digest(primary_query), "primary_candidate_articles": primary_n,
        "primary_query_status": "Post-coding projection of unchanged frozen named-design/reading routes; not a newly validated query",
        "validation_summary_sha256": digest((rdir/"validation_summary.json").read_bytes()),
        "current_dashboard_replaced": False, "human_validated": False,
        "reports": ["SEARCH_SUMMARY", "SEARCH_METHODS", "SEARCH_STRATEGY"]})
    print("Rendered search audit, coauthor note and SI draft; frozen ranking unchanged.")


if __name__ == "__main__":
    build()
