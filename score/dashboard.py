"""Build the public SCORE dashboard from current derived labels."""
from collections import Counter
import html
import json
from annotate import ROOT
from review import read_rows, index_rows


def main():
    folder = ROOT / 'score'
    articles = sorted(read_rows(folder / 'articles.csv'), key=lambda r:(r['journal'], -int(r['year'])))
    predictions = index_rows(read_rows(folder / 'predictions.csv'))
    references = index_rows(read_rows(folder / 'fulltext_reviews.csv'))
    access = index_rows(read_rows(folder / 'access.csv'))
    counts = Counter(row['annotation'] for row in predictions.values())
    table = []
    for row in articles:
        key = row['article_id']
        doi = html.escape(row['doi'], quote=True)
        cells = [html.escape(row['journal']), row['year'], f'<a href="https://doi.org/{doi}">{html.escape(row["title"])}</a>',
                 'YES' if access.get(key, {}).get('status') == 'verified_fulltext' else 'NO',
                 predictions.get(key, {}).get('annotation', 'Pending'), references.get(key, {}).get('annotation', 'Pending')]
        table.append('<tr>' + ''.join('<td>' + value + '</td>' for value in cells) + '</tr>')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>SCORE researcher recruitment</title><style>
body{font:16px/1.5 system-ui,sans-serif;color:#203039;background:#f7f8f8;margin:0}main{max-width:1250px;margin:auto;padding:30px}
a{color:#12666a}nav{display:flex;gap:16px;flex-wrap:wrap}.cards{display:flex;gap:18px;flex-wrap:wrap;margin:24px 0}.card{padding:16px;background:white;border:1px solid #ccd7d8}.card strong{display:block;font-size:28px}table{border-collapse:collapse;background:white;width:100%}th,td{text-align:left;padding:12px;border-bottom:1px solid #ddd;vertical-align:top}th{background:#e4eeee}.scroll{overflow:auto}input{font:inherit;padding:10px;width:min(90%,600px)}.note{padding:16px;border-left:4px solid #36787c;background:#e9f0f1}
</style><main><h1>SCORE researcher recruitment</h1><p>620 articles · 62 journals · 2016–2025 · One article per journal and year</p>
<nav><a href="prompt.md">Screening prompt</a><a href="predictions.csv">Abstract predictions</a><a href="fulltext_reviews.csv">Full-text assessments</a><a href="report.md">Evaluation report</a><a href="error_analysis.md">Error analysis</a><a href="codebook.md">Spreadsheet columns</a><a href="articles.csv">Articles</a><a href="protocol.md">Protocol</a><a href="access_report.md">Source access</a><a href="../archive/tess/DASHBOARD_NARROWER.html">TESS archive</a></nav>
'''
    page += f'<div class="cards"><div class="card"><strong>{len(predictions)} / 620</strong>Fresh abstract labels</div><div class="card"><strong>{len(references)} / 620</strong>Fresh full-text reviews</div><div class="card"><strong>{sum(r.get("status") == "verified_fulltext" for r in access.values())} / 620</strong>Local main texts</div></div>'
    page += '<p class="note">The supplied prompt produces one label: YES, NO or UNCLEAR. Full-text review applies the same criteria and adds source evidence and reasoning. AI reference judgments remain provisional; human verification has not been completed. Pending means not yet assessed.</p>'
    page += '<p>Abstract counts: ' + ' · '.join(f'{label}: {counts[label]}' for label in ['YES','NO','UNCLEAR']) + '</p>'
    page += '<p>This collection includes access-based replacements and previously examined development examples. Reported agreement is not performance on an untouched holdout or a population prevalence estimate. Licensed abstracts and full texts remain local.</p>'
    evaluation = json.loads((folder / 'evaluation.json').read_text())
    if evaluation.get('complete'):
        page += '<h2>Comparison with AI full-text review</h2><p>These results use ' + str(evaluation['reference_resolved']) + ' resolved source judgments; ' + str(evaluation['reference_unclear']) + ' unresolved judgments are excluded. Human verification is pending.</p>'
        page += '<div class="scroll"><table><thead><tr><th>Decision</th><th>Balanced accuracy</th><th>Precision</th><th>Recall</th><th>F1</th></tr></thead><tbody>'
        for key, name in [('strict_yes', 'Select YES'), ('retain_yes_or_unclear', 'Retain YES and UNCLEAR for review')]:
            values = evaluation[key]
            cells = [name] + [f'{100 * values[field]:.1f}%' if values[field] is not None else 'Not estimable' for field in ['balanced_accuracy', 'precision', 'recall', 'f1']]
            page += '<tr>' + ''.join('<td>' + cell + '</td>' for cell in cells) + '</tr>'
        page += '</tbody></table></div><p>Precision describes how many selected articles qualify; recall describes how many qualifying articles are found. See the evaluation report for definitions and all three labels.</p>'
    page += '<h2>Articles</h2><input id="search" aria-label="Search articles" placeholder="Search journal, title or year"><div class="scroll"><table><thead><tr><th>Journal</th><th>Year</th><th>Article</th><th>Local full text</th><th>Abstract annotation</th><th>Full-text annotation</th></tr></thead><tbody id="papers">' + ''.join(table) + '</tbody></table></div></main>'
    page += '''<script>document.getElementById('search').addEventListener('input',function(){const query=this.value.toLowerCase();for(const row of document.querySelectorAll('#papers tr'))row.hidden=!row.textContent.toLowerCase().includes(query);});</script></html>'''
    (folder / 'index.html').write_text(page)
    print(f'Built dashboard for {len(articles)} articles.')


if __name__ == '__main__':
    main()
