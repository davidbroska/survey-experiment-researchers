"""Render the proximity-query audit and a public full-text benchmark inventory."""
from collections import Counter
import html
import json

from common import ROOT, digest, read_csv, write_json
import proximity_audit as audit
import precision_benchmark as benchmark
from render import render

HISTORICAL_NOTICE = ("**Archived query-development stage (18 full-text reviews).** "
                     "See the [latest ranking comparison, discovery query and recommendation](RANKING_COMPARISON_REPORT.html) "
                     "and [updated 45-article full-text inventory](FULLTEXT_BENCHMARK.html) for the subsequent evidence.\n\n")


def table(rows, columns):
    out = "| " + " | ".join(v for _,v in columns) + " |\n"
    out += "| " + " | ".join("---" for _ in columns) + " |\n"
    return out + "".join("| " + " | ".join(str(r.get(k,"")) for k,_ in columns) + " |\n" for r in rows)


def report():
    counts = {r["variant"]:r for r in read_csv(audit.RESULTS / "retrieval_counts.csv")}
    authors = read_csv(audit.RESULTS / "author_comparison.csv")
    availability = read_csv(benchmark.RESULTS / "availability_manifest.csv")
    consensus = read_csv(benchmark.RESULTS / "article_consensus.csv")
    strata = read_csv(benchmark.RESULTS / "stratum_summary.csv")
    sample_strata = read_csv(audit.RESULTS / "fulltext_sampling_strata.csv")
    ready = sum(r["fulltext_readiness"] == "ready_for_fulltext_review" for r in availability)
    double = [r for r in consensus if r["review_coverage"] == "double_pass"]
    outcomes = Counter(r["design"] for r in double)
    targeted = (audit.QUERIES / "targeted.txt").read_text().strip()
    specific = (ROOT / "queries/proximity_specific_2026_09_10/primary_plus_specific.txt").read_text().strip()
    short = (audit.QUERIES / "minimal.txt").read_text().strip()
    old = (ROOT / "queries/search_strategy_2026_09_10/candidate.txt").read_text().strip()
    size = lambda text:len(" ".join(text.split()))
    author_table = []
    for person in ("Kurt Gray","Jay J. Van Bavel"):
        records = {r["variant"]:r for r in authors if r["researcher"] == person}
        author_table.append({"researcher":person,"expanded":records["previous_expanded"]["first_last_candidate_articles"],
            "candidate":records["previous_candidate"]["first_last_candidate_articles"],
            "plus_clause":records["candidate_plus_clause"]["first_last_candidate_articles"],
            "targeted":records["targeted"]["first_last_candidate_articles"]})
    summary = ("**The proposed clause recovers relevant social-psychology experiments, but it does not resolve all missing work.** "
        "Scopus returns 1,791 journal articles globally and 1,297 within the existing 3,401-journal frame for 2010–2026. "
        "Adding it to the 8,142-article expanded search yields 9,208 distinct articles (+1,066, no losses); adding it to the broader 18,054-article candidate search yields 18,834 (+780, no losses). "
        "These are retrieval gains, not measured recall.\n\n"
        "The clause adds one source-verified eligible last-author article for each nominated researcher: Kurt Gray’s [Equating silence with violence](https://doi.org/10.1016/j.jesp.2022.104348) and Jay Van Bavel’s [Identity concerns drive belief](https://doi.org/10.1177/13684302211030004). "
        "The former varies anti-racist message wording and measures threat and resistance; the latter varies partisan messages and measures belief and sharing intentions.\n\n"
        + table(author_table,[("researcher","Researcher"),("expanded","Expanded search: first/last"),("candidate","Prior broad candidate: first/last"),("plus_clause","Broad candidate + clause: first/last"),("targeted","Shorter targeted query: first/last")]) + "\n"
        "The counts use complete Scopus bylines and distinct articles, with sole authors counted once. They remain candidate counts. "
        "Identity checks distinguished the NYU psychologist from a same-name allergy researcher. We retrieved complete Article bibliographies for Gray (114 records) and Van Bavel (106), then inspected four eligible full-text examples for each. "
        "All eight examples are in the journal frame; six fail the proposed clause because the abstract omits its narrow reading/manipulation wording, sometimes describing studies without experimental terminology. "
        "One already retrieved Van Bavel paper gives him middle-author status. The named cases diagnose the method and are excluded from precision evaluation. "
        "[Identity audit](results/proximity_audit_2026_09_10/author_identity_audit.csv) · [Eight full-text examples](results/proximity_audit_2026_09_10/author_fulltext_examples.csv) · [Article-by-article retrieval](results/proximity_audit_2026_09_10/author_article_retrieval.csv).\n\n"
        "The repeated proximity expressions can be grouped without changing retrieval. Both full global result sets contain the same 1,791 Scopus IDs, and both directional difference checks return zero. "
        "The [official Scopus syntax](https://dev.elsevier.com/sc_search_tips.html) permits OR groups within proximity expressions. The equivalent clause is:\n\n```text\n"
        + audit.clause(True) + "\n```\n\n"
        "Keep the read and manipulation material groups separate: merging both verbs with every material would add combinations that were not requested. W/3 permits either word order and does not ensure that the words describe the same study. The double-quoted design labels below are loose Scopus phrases; punctuation-sensitive evidence checks remain a separate screening step. "
        "Live probes show that read does not match an abstract containing only reading; read* also reaches readiness. We therefore preserve the requested read token in this test. "
        "[Complete-set equivalence](results/proximity_audit_2026_09_10/grouping_equivalence.json) · [Syntax probes](results/proximity_clause_semantics_2026_09_10/live_probes.csv).\n\n"
        "**First tested shorter candidate:** retain the previous named-design, contextual-design and randomized-reading core, and add the grouped clause. "
        "This identifies articles through recognizable design labels or specific reading/manipulation procedures. It removes the previous broad combination of experimental, material and outcome words. "
        f"The result contains {size(targeted):,} characters after normalizing whitespace, versus {size(old):,} in the preceding broad candidate (12% shorter) and 4,688 in the long expanded query (67% shorter). "
        "It retrieves 9,675 candidates: all 8,615 previous core candidates plus 1,060 additional articles. Compared with the prior 18,054-article broad candidate, it adds 780 and omits 9,159. Some omitted articles are eligible; the narrower query is a primary discovery route, not a replacement for archived evidence. "
        f"A more compressed two-block alternative has {size(short):,} characters and retrieves 8,839, but loses 836 core candidates. Earlier reviewed positives are among the losses, so shortening to that extent is not recommended. "
        "The core-plus-clause query misses 28 records from the older 8,142-article search; retain both those records and the broader archived candidates for screening. The shorter query yields one first/last candidate for each focal researcher, whereas adding the clause to the broader search yields two each. Full-text eligibility, parser compatibility and original data collection must be checked separately before ranking. "
        "[Retrieval comparison](results/proximity_audit_2026_09_10/retrieval_comparison.csv) · [Original tested candidate query](queries/proximity_audit_2026_09_10/targeted.txt).\n\n"
        "```text\n" + targeted + "\n```\n\n"
        "**Full-text evaluation set.** We froze 60 articles before checking access: 20 found only by the previous core, 20 found only by the proposed clause, and 20 found by both. "
        "The sample excludes inherited development material, the preceding 160-article and 100-article reviews, previously reviewed full texts, the loss audit, and all four nominated authors’ bibliographies. "
        "The remaining sampling populations are shown below; equal sample sizes require unequal stratum weights. The target is this previously unreviewed subset, not every retrieved article or all survey experiments.\n\n"
        + table(sample_strata,[("stratum","Sampling stratum"),("population_N","Unreviewed population"),("sample_n","Fixed sample")]) + "\n"
        f"We acquired readable, identity-verified main texts or author manuscripts for {ready}/60 selected articles; {60-ready} still need a usable copy. Missing articles were not replaced. "
        "Source versions, PDF hashes, page-indexed text, acquisition attempts and access failures are recorded. Accepted or author manuscripts may require comparison with the version of record before final validation. "
        f"Two independent AI coding passes completed {len(double)} articles: {outcomes['yes']} affirmative design agreements, {outcomes['no']} negative agreements and {outcomes['unclear']} unresolved judgments. "
        "Design, original data, text modality, parser compatibility, sample geography and data possession are separate axes. Both coders cite actual PDF pages; evidence spans and source hashes are checked. "
        "The packets omit search routes and prior labels, although authors remain visible in the papers. These are working AI-assisted annotations, not human-validated reference labels.\n\n"
        + table(strata,[("stratum","Sampling stratum"),("sample_n","Fixed sample"),("double_pass","Full texts double-coded"),("double_coded_yes","Eligible"),("double_coded_no","Ineligible"),("unknown_for_bounds","Still unresolved")]) + "\n"
        "Among the available papers found only by the new clause, four were eligible and four were not. The false positives include motor tracking, reading-comprehension testing and cognitive training: participants can read passages or receive manipulated information without taking part in a survey experiment. "
        "The primary-only negative was a cost-effectiveness simulation and evidence synthesis about survey experiments. Thus neither a specific design label nor the new procedural clause is a sufficient inclusion rule.\n\n"
        "**Recommended next validation candidate.** Following this review, we tested a separate development revision that removes only read W/3 passage* and manipulat* W/3 information from the added clause. "
        "The other nine pairs, population gates and earlier core are unchanged. The narrower clause returns 967 in-frame articles; the complete revised query returns 9,365, adding 750 to the 8,615-article core without losing core records. "
        "Against the earlier broad candidate, it adds 491 and omits 9,180; archived candidates therefore remain a separate screening queue. Both focal researchers retain their new last-author article. "
        "Within the 18 exposed full texts, the revised query retains 12 of 13 design-positive articles and one of five negatives. The omitted positive uses an interactive news network and was marked parser-incompatible by both reviewers. "
        "The other 305 removed articles were not assessed in this full-text exercise. Among the 12 retained positives, parser judgments are eight compatible, one incompatible and three unclear; this revision does not establish parser eligibility. "
        "This result motivated a narrower primary discovery route, but it is a post-hoc observation on an availability-limited set: these 18 papers are now development evidence for the revision, not independent validation. "
        "A fresh, prespecified evaluation is needed before claiming its precision. No negative keyword filters were introduced. "
        f"The full revised query has {size(specific):,} whitespace-normalized characters. [Development protocol and set comparison](results/proximity_specific_2026_09_10/development_summary.md) · [Download the next validation query](queries/proximity_specific_2026_09_10/primary_plus_specific.txt).\n\n"
        "```text\n" + specific + "\n```\n\n"
        "Availability and partial coding do not establish high query precision. The benchmark retains all 60 records in the accounting and reports stratum-weighted missing-label bounds instead of treating the accessible subset as representative. "
        "Complete the missing full texts and obtain independent human adjudication before reporting precision in a manuscript. Even a complete precision evaluation would not estimate recall; that needs an independently assembled positive reference set or an audit of unmatched articles. "
        "[Full-text inventory and download workflow](FULLTEXT_BENCHMARK.html) · [Fixed sample](results/proximity_audit_2026_09_10/fulltext_sample.csv) · [Working labels](results/precision_benchmark_2026_09_10/article_consensus.csv) · [Missing-label bounds](results/precision_benchmark_2026_09_10/missing_label_bounds.csv).\n\n"
        "A separate byline check found a Scopus record that lists a PNAS handling editor as the final author. The published byline instead ends with Van Bavel. "
        "That article-specific discrepancy is preserved as an audit finding; it does not establish another eligible experiment or change the ranking. "
        "[Raw and publisher-verified bylines](results/proximity_audit_2026_09_10/author_byline_discrepancies.csv).\n\n"
        "The dashboard continues to show its earlier provisional cohort. No researcher names, substantive topic requirements, vendor restrictions, or explicit conjoint/split-ballot exclusions were added to the query. "
        "The reproducible stages are python3 pipeline/proximity_audit.py summarize, python3 pipeline/proximity_audit.py author_comparison, python3 pipeline/precision_benchmark_review.py, and python3 pipeline/proximity_report.py. "
        "Licensed metadata, PDFs and verbatim evidence stay under private/. [Coauthor summary](PROXIMITY_SUMMARY.html) · [SI draft](PROXIMITY_METHODS.html) · [Earlier search audit](SEARCH_STRATEGY.html) · [Dashboard](TOP100.html#summary).\n")
    summary = HISTORICAL_NOTICE + summary
    (ROOT / "PROXIMITY_AUDIT.md").write_text(summary)
    (ROOT / "PROXIMITY_AUDIT.html").write_text(render(summary,"Reading and manipulation: query audit and full-text evaluation"))
    methods = ("We compared an additional procedural search with frozen Scopus searches for journal articles published in 2010–2026 within a 3,401-journal frame derived from TESS investigators’ publication histories. "
        "The new clause requires experimental terminology in titles, abstracts or keywords; reading or manipulation close to specified communicated materials in the abstract; and survey, questionnaire, respondent or participant language in the abstract. "
        "Grouping repeated proximity terms produced identical complete Scopus result sets. We united this clause with the previous named-design, contextual-design and reading-assignment core, deduplicating by DOI with Scopus ID fallback. "
        "The resulting candidate query retrieves 9,675 articles. Retrieval establishes candidate status; eligibility requires study-level review. Earlier candidates lost by query revision remain archived for screening.\n\n"
        "We fixed a 60-article evaluation sample before checking full-text availability, with 20 articles selected by reproducible pseudorandom hashes in each of three disjoint strata: core only, additional clause only, and overlap. "
        "Exclusions covered all prior development and reviewed records and the complete bibliographies of the four nominated researchers used as diagnostic cases. "
        "The remaining stratum populations were 6,792, 882 and 134, respectively. Inaccessible sampled articles were retained without replacement. "
        f"At this stage, {ready} main texts or author manuscripts were available and {len(double)} had two AI-assisted reviews. "
        "Reviewers used page-cited evidence and coded design eligibility, original data collection, written treatment, parser compatibility, sample geography and data possession separately. "
        "Packets concealed search-route membership and previous labels; author anonymity was not claimed. Source hashes and quoted page evidence were validated programmatically. "
        "Disagreement remained unresolved. Stratum-weighted missing-label bounds describe uncertainty from unfinished annotation and access; they are not confidence intervals or human-validated precision estimates. Human adjudication and completion of the fixed sample remain necessary.\n\n"
        "After inspecting the 18 available full texts, we froze and retrieved a separate development variant omitting two nonspecific pairs: read near passage and manipulation near information. "
        "The resulting core-plus-clause query retrieves 9,365 candidates, including all 8,615 core records and 750 additions. It retains 12 of 13 exposed design-positive papers and one of five negatives; the omitted positive was classified as parser-incompatible. "
        "These post-hoc observations do not validate the revised query. The original sample, queries and labels remain unchanged; a fresh prespecified sample is required for independent evaluation of the revision.\n\n"
        "For a revised ranking, each eligible distinct article contributes once to each distinct first or last author, with a sole author receiving one credit. Complete bibliographies should be reviewed under a uniform candidate-selection rule before truncation to the top 100. "
        "Counts describe publications, not independent datasets or confirmed data ownership. The existing dashboard has not been replaced by these unreviewed retrieval results.\n\n"
        "The next candidate for validation is shown below; the [original evaluated query](queries/proximity_audit_2026_09_10/targeted.txt) is archived separately.\n\n```text\n" + specific + "\n```\n\n"
        "The [journal Source IDs](results/venue_frame.csv) are applied as a separate frame intersection. [Complete audit](PROXIMITY_AUDIT.html) · [Evaluation set](FULLTEXT_BENCHMARK.html).\n")
    methods = HISTORICAL_NOTICE + methods
    (ROOT / "PROXIMITY_METHODS.md").write_text(methods)
    (ROOT / "PROXIMITY_METHODS.html").write_text(render(methods,"Proximity search and full-text evaluation: SI draft"))
    coauthor = ("We seek researchers who have repeatedly collected survey-experiment data. The search uses four recognizable signals: named survey/vignette designs; related experimental designs with survey-participant language; randomized reading assignments; and specific reading or manipulation procedures described in abstracts. Researcher names and substantive topics are not search criteria.\n\n"
        "Testing the proposed procedural clause adds relevant last-authored papers by both Kurt Gray and Jay Van Bavel, who were absent from the expanded search. A shorter revision retains the existing 8,615-article core and adds 750 candidates, yielding 9,365 articles in 3,401 journals during 2010–2026. This is additional retrieval, not measured recall. Earlier candidates remain archived for screening.\n\n"
        "We fixed a 60-article evaluation sample before checking access and obtained 18 full texts. Two AI review passes agreed on 13 eligible and five ineligible designs. The false positives motivated removal of two broad procedural phrase pairs; the revised query retains 12 positives and one negative in this exposed subset. The omitted positive requires an incompatible interactive design. This is development evidence, not an independent precision estimate.\n\n"
        "Forty-two sampled articles still need usable copies, and all labels require human validation. Eligibility, parser compatibility, geography and original data possession are assessed separately. Ranking will count each eligible article once for each first or last author, with sole authors counted once; the existing provisional ranking is unchanged.\n\n"
        "[Full query and SI methods](PROXIMITY_METHODS.html) · [Evidence and comparisons](PROXIMITY_AUDIT.html) · [Full-text inventory and download links](FULLTEXT_BENCHMARK.html).\n")
    coauthor = HISTORICAL_NOTICE + coauthor
    (ROOT / "PROXIMITY_SUMMARY.md").write_text(coauthor)
    (ROOT / "PROXIMITY_SUMMARY.html").write_text(render(coauthor,"Survey-experiment search: coauthor summary"))
    benchmark_page(availability,consensus)
    write_json(audit.RESULTS / "report_provenance.json", {"candidate_query_sha256":digest(targeted),
        "next_validation_query_sha256":digest(specific),"revision_status":"post_benchmark_development",
        "fulltext_sample_sha256":digest((audit.RESULTS / "fulltext_sample.csv").read_bytes()),
        "consensus_sha256":digest((benchmark.RESULTS / "article_consensus.csv").read_bytes()),
        "human_validated":False,"ranking_replaced":False,
        "reports":["PROXIMITY_AUDIT","PROXIMITY_METHODS","PROXIMITY_SUMMARY","FULLTEXT_BENCHMARK"]})
    print(f"Reports rendered; {ready}/60 full texts ready, {len(double)} double-coded; ranking unchanged")


def benchmark_page(availability,consensus, results_folder="results/precision_benchmark_2026_09_10"):
    labels = {r["scopus_id"]:r for r in consensus}
    rows = []
    for r in availability:
        c = labels[r["scopus_id"]]
        rows.append({**r,"review_coverage":c["review_coverage"],"design":c["design"]})
    rows.sort(key=lambda r:r["benchmark_id"])
    ready = sum(r["fulltext_readiness"] == "ready_for_fulltext_review" for r in rows)
    current_wave = "benchmark_review_wave2" in results_folder
    destination = "SurveyExperimentRecruitment/" if current_wave else "SurveyExperimentRecruitment/private/precision_benchmark_2026_09_10/inbox/"
    command = "python3 pipeline/benchmark_review_wave2.py" if current_wave else "python3 pipeline/precision_benchmark.py prepare --sample results/proximity_audit_2026_09_10/fulltext_sample.csv"
    judgments = Counter(r["design"] for r in rows if r["review_coverage"] == "double_pass")
    reviewed = sum(judgments.values())
    md = (f"The fixed sample contains 60 retrieved articles, selected before full-text lookup. {ready} have readable identity-verified main texts or author manuscripts; {60-ready} need a usable copy. "
        "No inaccessible paper is replaced with a more convenient article. AI-assisted annotations require human validation.\n\n"
        f"{reviewed} articles have two reviews: {judgments['yes']} agreed eligible survey-experiment designs, {judgments['no']} agreed negatives, and {reviewed-judgments['yes']-judgments['no']} unresolved or disputed designs. Parser compatibility and sample geography are recorded separately.\n\n"
        f"Save requested PDFs as the listed Scopus ID plus .pdf in {destination} "
        "Select Needs a copy to see the remaining download queue. Each article has a publisher link and a filename to copy.\n\n"
        "[Current ranking comparison](RANKING_COMPARISON_REPORT.html) · [Original sampling method](PROXIMITY_AUDIT.html) · "
        f"[Inventory CSV]({results_folder}/availability_manifest.csv) · [Manual download CSV]({results_folder}/manual_download_queue.csv) · [Working labels]({results_folder}/article_consensus.csv).\n")
    (ROOT / "FULLTEXT_BENCHMARK.md").write_text(md + "\n" + table(rows,[("benchmark_id","ID"),("title","Article"),("fulltext_readiness","Availability"),("review_coverage","Review status"),("suggested_filename","Filename")]))
    page = render(md,"Full-text evaluation set: 60 fixed articles")
    controls = f'''<div class="controls"><label>Show <select id="filter"><option value="all">All 60 articles</option><option value="ready">Full texts available ({ready})</option><option value="missing">Needs a copy ({60-ready})</option></select></label><label>Search <input id="search" type="search" placeholder="Title, DOI or identifier"></label><p id="count" aria-live="polite"></p></div><div id="articles"></div><details><summary>Refresh the inventory after adding PDFs</summary><p>From SurveyExperimentRecruitment, run <code>{command}</code> to check identity and refresh the private reviewer packet. Acquisition does not assign study labels. All originals and alternate copies are preserved privately.</p></details>'''
    data = json.dumps(rows,ensure_ascii=False).replace("<","\\u003c").replace("&","\\u0026")
    script = '''<script>
const DATA=__DATA__;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function draw(){const filter=document.getElementById('filter').value,q=document.getElementById('search').value.toLowerCase();
const selected=DATA.filter(r=>{const ready=r.fulltext_readiness==='ready_for_fulltext_review';return(filter==='all'||(filter==='ready'?ready:!ready))&&[r.title,r.doi,r.benchmark_id,r.scopus_id].join(' ').toLowerCase().includes(q)});
document.getElementById('count').textContent=selected.length+' articles shown';
document.getElementById('articles').innerHTML=selected.map(r=>`<article class="card"><h2>${esc(r.title)}</h2><p>${esc(r.year)} · ${esc(r.journal)} · ${esc(r.benchmark_id)}</p><p><strong>${r.fulltext_readiness==='ready_for_fulltext_review'?'Full text available':'Needs a usable copy'}</strong> · ${esc(r.review_coverage.replaceAll('_',' '))}${r.review_coverage==='double_pass'?' · Design: '+esc(r.design):''}</p><p><a href="${esc(r.article_url)}" target="_blank" rel="noopener">Publisher / DOI ↗</a>${r.source_url?' · <a href="'+esc(r.source_url)+'" target="_blank" rel="noopener">Source copy ↗</a>':''}</p><p>Filename: <code>${esc(r.suggested_filename)}</code> <button data-copy="${esc(r.suggested_filename)}">Copy filename</button></p></article>`).join('');}
document.getElementById('filter').addEventListener('change',draw);document.getElementById('search').addEventListener('input',draw);
document.getElementById('articles').addEventListener('click',async e=>{const b=e.target.closest('[data-copy]');if(!b)return;try{await navigator.clipboard.writeText(b.dataset.copy);b.textContent='Copied';}catch{b.textContent='Select filename to copy';}});draw();
</script>'''.replace("__DATA__",data)
    style='<style>.controls{display:flex;gap:1rem;flex-wrap:wrap;align-items:center;padding:1rem;background:#f0f5f8}.controls input,.controls select{font:inherit;padding:.4rem;max-width:100%}.card{border:1px solid #dbe3e8;border-radius:8px;padding:1rem;margin:1rem 0}.card h2{font-size:1.12rem;line-height:1.4;margin-top:0}button{font:inherit;padding:.3rem .6rem}p,code,a{overflow-wrap:anywhere}</style>'
    # The shared renderer uses an implicit HTML body.
    page=page.replace('</html>',style+controls+script+'</html>')
    (ROOT / "FULLTEXT_BENCHMARK.html").write_text(page)


if __name__ == "__main__":
    report()
