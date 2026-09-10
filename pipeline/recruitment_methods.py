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
    selection = ("We then review sample locations for 120 researchers: the top 100 by article count, expanded to 114 "
                 "because of ties, plus six additional candidates retained from the initial review list.") if key != "original" else (
                 "We review sample locations for the same fixed list of 120 previously reviewed researchers.")
    return [
        ("Define the journal set.", "We use the 3,401 journals with at least one recorded publication from investigators "
         "in Time-sharing Experiments for the Social Sciences (TESS). This gives us a broad starting set of journals "
         "used by experimental social scientists. Candidate donors need not have participated in TESS."),
        ("Find candidate survey experiments.", "Within these journals, we search Scopus titles, abstracts and keywords "
         "for journal articles published in 2010–2026. " + search),
        ("Identify potential research leaders.", "We count each distinct article once for each first or last "
         "author; a sole author receives one credit. This is a proxy for research leadership."),
        ("Rank by evidence of US samples.", selection + " We use article information and available full texts to identify "
         "US samples, either explicitly reported or reasonably inferred from the study context. "
         f"Among the {data['pool_articles']:,} distinct articles associated with these 120 researchers, "
         f"{us:,} have US-sample evidence and {labels.get('unclear', 0):,} remain geographically unclear. "
         "The dashboard sorts by US-sample articles by default; total survey-experiment candidate counts are also available.")
    ]


GOAL = "Our goal is to identify potential data donors who have frequently conducted survey experiments, with particular interest in experiments using US samples."
INTERPRETATION = ("The US ranking compares these 120 researchers, not every author in Scopus. Unclear geography is not treated "
                  "as non-US. Counts describe articles, not independent datasets. Annotations are AI-assisted and await human "
                  "validation; study eligibility and access to data and treatment materials require confirmation before invitations.")


def methodology_html(key, data):
    from variant_dashboards import readable_query
    items = "".join(f"<li><strong>{html.escape(title)}</strong> {html.escape(body)}</li>" for title, body in steps(key, data))
    syntax = ("Brace phrases are exact matches; the local phrase check additionally checks punctuation.") if key == "original" else (
              "Quoted phrases allow wildcard word endings; they do not enforce exact punctuation.")
    return f'''<h2>How we selected researchers</h2>
<p>{GOAL}</p><ol class="selection-steps">{items}</ol>
<p class="methods-note">{INTERPRETATION}</p>
<section class="query-details" id="query-details" aria-labelledby="query-heading"><h3 id="query-heading">Scopus query</h3>
<p><code>TITLE-ABS-KEY</code> searches titles, abstracts and keywords; <code>ABS</code> searches abstracts. <code>*</code> allows word endings and <code>W/3</code> means within three words. {syntax} Retrieved records are restricted to the <a href="results/venue_frame.csv">journal set</a> using Scopus Source IDs.</p>
<div class="summary-actions"><button id="copy-query">Copy query</button><a href="{html.escape(data['query_path'])}" download>Download query</a></div>
<p id="query-copy-status" class="status" aria-live="polite"></p><textarea id="query-copy-fallback" readonly rows="8" hidden aria-label="Literal query to copy"></textarea>
<pre class="scopus-query"><code id="literal-query">{html.escape(readable_query(data['query']))}</code></pre></section>'''


def build():
    from variant_dashboards import load_inputs, make_payload, readable_query
    data, paths = make_payload("narrower", load_inputs())
    body = GOAL + "\n\n" + "\n\n".join(
        f"{i}. **{title}** {text}" for i, (title, text) in enumerate(steps("narrower", data), 1))
    body += "\n\n" + INTERPRETATION + "\n"
    summary = body + "\n[Researcher ranking](DASHBOARD_NARROWER.html) · [Methodology and query](METHODOLOGY.html).\n"
    methods = body + ("\nThe query below searches journal articles published in 2010–2026. "
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
