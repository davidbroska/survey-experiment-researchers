"""Standalone, query-specific selection methods for the coauthor dashboard."""
import html
import json

from common import ROOT, digest, write_json
from render import render


def steps(key, data):
    if key == "original":
        search = ("We search for survey- and vignette-experiment phrases and descriptions of embedded experiments, "
                  "randomized reading assignments, information treatments and question-wording experiments. "
                  f"The search returns {data['retrieved']:,} distinct articles; a local phrase check retains "
                  f"{data['candidates']:,} candidates.")
    else:
        search = ("We search for survey- and vignette-experiment labels, alongside descriptions of experimental "
                  "framing, information, question wording and reading assignments. Broader procedural descriptions "
                  "must also occur with survey or participant language. "
                  f"The search returns {data['retrieved']:,} distinct candidate articles.")
    labels = data["pool_labels"]
    us = labels.get("us_explicit", 0) + labels.get("us_inferred", 0)
    # The recruitment cohort is frozen. Geography updates cannot change its membership.
    cohort = ("For sample review, we retain a fixed cohort of 120 researchers: all 114 at or above the "
              "total-count top-100 cutoff, including ties, plus six previously screened candidates.") if key != "original" else (
              "For sample review, we retain a fixed cohort of 120 previously screened researchers.")
    return [
        ("Define the journal set.", "We use the 3,401 journals in the recorded publication histories of investigators "
         "in Time-sharing Experiments for the Social Sciences (TESS). This gives us a broad starting set of journals "
         "used by experimental social scientists. Candidate donors need not have participated in TESS."),
        ("Find candidate survey experiments.", "Within these journals, we search Scopus titles, abstracts and keywords "
         "for journal articles published in 2010–2026. " + search),
        ("Identify researchers with repeated experience.", "We count each distinct article once for each first or last "
         "author; a sole author receives one credit. This is a proxy for research leadership. " + cohort),
        ("Rank by evidence of US samples.", f"We review titles, abstracts and keywords, consulting full texts when available. "
         f"The cohort has {data['pool_articles']:,} distinct credited articles under this query: {us:,} have US-sample evidence "
         f"and {labels.get('unclear', 0):,} remain geographically unclear. We combine explicit US recruitment statements with "
         "justified inference from study context, including American topics. The default ranking counts these US-evidence "
         "articles; total survey-experiment candidate counts remain available alongside it.")
    ]


GOAL = "Our goal is to identify potential data donors who have frequently conducted survey experiments, with particular interest in experiments using US samples."
INTERPRETATION = ("The US ranking compares this 120-person cohort, not every author in Scopus. Unclear geography is not treated "
                  "as non-US. Counts describe articles, not independent datasets. Annotations are AI-assisted and await human "
                  "validation; study eligibility and access to data and treatment materials require confirmation before invitations.")


def methodology_html(key, data):
    from variant_dashboards import readable_query
    items = "".join(f"<li><strong>{html.escape(title)}</strong> {html.escape(body)}</li>" for title, body in steps(key, data))
    credited = data["candidates"] - data["unresolved_bylines"]
    syntax = ("Brace phrases are exact matches; the local phrase check additionally checks punctuation.") if key == "original" else (
              "Quoted phrases allow wildcard word endings; they do not enforce exact punctuation.")
    return f'''<h2>How we selected researchers</h2>
<p>{GOAL}</p><ol class="selection-steps">{items}</ol>
<p class="methods-note">{INTERPRETATION}</p>
<details class="query-details" id="query-details"><summary>View the Scopus query</summary>
<p><code>TITLE-ABS-KEY</code> searches titles, abstracts and keywords; <code>ABS</code> searches abstracts. <code>*</code> allows word endings and <code>W/3</code> means within three words. {syntax} Retrieved records are restricted to the <a href="results/venue_frame.csv">journal set</a> using Scopus Source IDs.</p>
<div class="summary-actions"><button id="copy-query">Copy query</button><a href="{html.escape(data['query_path'])}" download>Download query</a></div>
<p id="query-copy-status" class="status" aria-live="polite"></p><textarea id="query-copy-fallback" readonly rows="8" hidden aria-label="Literal query to copy"></textarea>
<pre class="scopus-query"><code id="literal-query">{html.escape(readable_query(data['query']))}</code></pre></details>
<details class="methods-details"><summary>Counting and affiliation details</summary>
<p>{credited:,} candidates have complete author credits; {data['unresolved_bylines']} have unresolved bylines and receive no credit. Equal counts share a rank. Institutions, departments, countries and roles come from sourced profiles. The country column describes the researcher's institution; US-sample counts describe participants.</p></details>'''


def build():
    from variant_dashboards import load_inputs, make_payload, readable_query
    data, paths = make_payload("narrower", load_inputs())
    body = GOAL + "\n\n" + "\n\n".join(
        f"{i}. **{title}** {text}" for i, (title, text) in enumerate(steps("narrower", data), 1))
    body += "\n\n" + INTERPRETATION + "\n"
    summary = body + "\n[Researcher ranking](DASHBOARD_NARROWER.html) · [Methodology and query](METHODOLOGY.html).\n"
    methods = body + (f"\nOf {data['candidates']:,} candidates, {data['candidates'] - data['unresolved_bylines']:,} have complete "
                      f"author credits; {data['unresolved_bylines']} have unresolved bylines and receive no credit. "
                      "Equal counts share a rank. Affiliation fields are joined from sourced profiles and describe researchers, "
                      "not participant geography.\n\nThe query below searches journal articles published in 2010–2026. "
                      "The pipeline intersects its results with the [3,401-journal Source-ID list](results/venue_frame.csv). "
                      "Quoted phrases support wildcard endings rather than exact punctuation. `W/3` specifies words within "
                      "three positions; procedural proximity matching is restricted to abstracts.\n\n```text\n" +
                      readable_query(data["query"]) + "\n```\n\n[Download the query](" + data["query_path"] + ") · "
                      "[Open the ranking](DASHBOARD_NARROWER.html).\n")
    for name, text in (("COAUTHOR_SUMMARY", summary), ("METHODOLOGY", methods)):
        (ROOT / (name + ".md")).write_text(text)
        (ROOT / (name + ".html")).write_text(render(text, "Selecting survey-experiment data donors"))
    write_json(ROOT / "results/coauthor_update_2026_09_10/methodology_provenance.json", {
        "selected_query": data["query_path"], "query_sha256": digest(data["query"]),
        "cohort_size": 120, "query_article_count": data["retrieved"],
        "cohort_credited_articles": data["pool_articles"], "geography_counts": data["pool_labels"],
        "inputs": {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in paths},
        "human_validated": False})


if __name__ == "__main__":
    build()
