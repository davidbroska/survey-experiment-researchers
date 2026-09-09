"""The user's four-step coauthor summary, with counts and the executed query."""
import html
import re
import query


def content(summary, flow, frame):
    s = summary
    introductory = 'Our goal is to identify data donors who have often conducted survey experiments. We have followed these steps:'
    steps = [
        f"We first need to define a set of journals where experimental social scientists would publish their research. "
        f"We take all {frame['n_journals']:,} journals that investigators in Time-sharing Experiments for the Social Sciences "
        f"(TESS) have published in. Within these journals, we search titles, abstracts, and keywords for survey-experiment "
        f"articles published in {query.START_YEAR}–{query.END_YEAR}. Candidate donors need not have participated in TESS.",
        "We then search for journal articles with search terms related to survey experiments. The search combines exact "
        "survey- and vignette-experiment phrases with specific descriptions of embedded experiments, randomized vignettes, "
        "reading assignments, information treatments, and question-wording experiments. Exact phrases preserve punctuation, "
        "reducing accidental matches between adjacent but unrelated words. The query is shown below:",
        f"The search returns {flow['in_frame']:,} article records, or {flow['unique_articles']:,} after duplicate removal. "
        f"The provisional {s['n_authors']}-researcher pool counts each candidate article once for each first or last author.",
        f"The sortable {s['n_authors']}-researcher dashboard joins current institutions, departments, countries, and roles. "
        f"Review of {s['n_unique_articles']} distinct articles identifies {s['n_us_articles']} with US-sample evidence "
        f"({s['article_counts']['us_explicit']} explicit; {s['article_counts']['us_inferred']} inferred, incorporating "
        f"{s['n_fulltext_reviewed_articles']} full-text reviews); {s['n_unclear_articles']} remain unclear pending full-text review. "
        "US sorting compares this pool, not all researchers. Counts describe articles, not independent datasets, and the "
        "AI-assisted annotations await validation. A deduplicated download queue supports the next review round."]
    literal = re.sub(r' OR (?=\{)', '\n      OR ', query.build())
    note = 'The pipeline restricts the retrieved records to the journal frame using Scopus Source IDs.'
    md = introductory + '\n\n'
    fragment = '<p>' + html.escape(introductory) + '</p><ol class="selection-steps">'
    for i, step in enumerate(steps, 1):
        md += f'{i}. {step}\n\n'
        fragment += '<li><p>' + html.escape(step) + '</p>'
        if i == 2:
            md += '```text\n' + literal + '\n```\n\n' + note + '\n\n'
            fragment += '<pre class="scopus-query"><code id="summary-query">' + html.escape(literal) + '</code></pre>'
            fragment += '<p class="review-note">' + html.escape(note) + '</p>'
        fragment += '</li>'
    fragment += '</ol>'
    return {'markdown': md, 'html': fragment, 'query': literal}


def standalone(fragment):
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Coauthor summary</title><style>body{font:16px/1.65 system-ui,sans-serif;max-width:1040px;margin:3rem auto;padding:0 1rem;color:#192b36}'
            'li{padding-left:.5rem;margin-bottom:1.4rem}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f0f5f8;padding:1rem;font-size:12px}'
            'a{color:#136294}.review-note{font-size:13px;color:#536575}</style><h1>Coauthor summary</h1>' + fragment +
            '<p><a href="TOP100.html#summary">Open in dashboard</a> · <a href="queries/recommended.txt">Download Scopus query</a></p></html>\n')
