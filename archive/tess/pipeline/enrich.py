"""Validate curated annotations and join geography to the first/last-author rank.

Labels are review inputs, not predictions from keyword counts. No network access
or model call is required to reproduce the join and reports.
"""
from collections import Counter
import html
import json

from common import ROOT, digest, read_csv, write_csv, write_json

LABELS = ('us_explicit', 'us_inferred', 'non_us', 'unclear', 'not_applicable')


def unique_index(rows, key):
    result = {}
    for row in rows:
        if not row.get(key) or row[key] in result:
            raise ValueError(f'Missing or duplicate {key}: {row.get(key)}')
        result[row[key]] = row
    return result


def join(top, affiliations, annotations, articles):
    """Return author and article tables; fail on incomplete or stale evidence."""
    people = unique_index(affiliations, 'authid')
    codes = unique_index(annotations, 'scopus_id')
    raw = unique_index(articles, 'scopus_id')
    unique_index(top, 'authid')
    required = {sid for author in top for sid in author['article_ids'].split('|')}
    if set(codes) != required or set(people) != {r['authid'] for r in top}:
        raise ValueError('Annotations and affiliations must exactly cover the current top 40')
    links, enriched = [], []
    for sid in required:
        a, r = codes[sid], raw[sid]
        if a['sample_us_label'] not in LABELS:
            raise ValueError(f'Invalid sample label: {sid}')
        if digest(r['abstract']) != a['abstract_sha256']:
            raise ValueError(f'Abstract changed since annotation: {sid}')
        if a['evidence_field'] != 'abstract' or not a['reviewer'] or not a['review_date']:
            raise ValueError(f'Incomplete annotation provenance: {sid}')
        quote = a['evidence_quote']
        if (a['sample_us_label'] != 'unclear' and not quote) or quote not in r['abstract']:
            raise ValueError(f'Unverifiable annotation evidence: {sid}')
        if not a['rationale']:
            raise ValueError(f'Missing annotation rationale: {sid}')
        if a['title_only_us_signal'] == 'true':
            if a['sample_us_label'] != 'unclear' or a['title_evidence'] != r['title']:
                raise ValueError(f'Invalid title-only evidence: {sid}')
        if a['us_and_non_us_samples_reported'] == 'true' and not a['sample_us_label'].startswith('us_'):
            raise ValueError(f'Mixed sample without US evidence: {sid}')
        if a['separate_us_sample_count_stated']:
            if int(a['separate_us_sample_count_stated']) < 1 or not a['separate_sample_count_quote'] or a['separate_sample_count_quote'] not in r['abstract']:
                raise ValueError(f'Invalid separate-sample count: {sid}')
    for author in top:
        aid = author['authid']
        ids = author['article_ids'].split('|')
        if len(set(ids)) != len(ids) or len(ids) != int(author['n_articles']):
            raise ValueError(f'Article score mismatch: {aid}')
        counts = Counter(codes[sid]['sample_us_label'] for sid in ids)
        first = last = sole = 0
        for sid in ids:
            r = raw[sid]
            is_first, is_last = aid == r['first_authid'], aid == r['last_authid']
            if not (is_first or is_last) or r['byline_complete'] != 'true':
                raise ValueError(f'Non-first/last or incomplete byline credited: {aid}, {sid}')
            first += is_first
            last += is_last
            sole += is_first and is_last
            links.append({'authid': aid, 'full_name': people[aid]['full_name'],
                          'scopus_id': sid, 'authorship_position': 'sole' if is_first and is_last else 'first' if is_first else 'last',
                          'sample_us_label': codes[sid]['sample_us_label']})
        if first != int(author['n_first']) or last != int(author['n_last']) or first + last - sole != len(ids):
            raise ValueError(f'First/last/sole credit mismatch: {aid}')
        row = {**author, **people[aid], 'n_sole': sole,
               'n_first_only': first - sole, 'n_last_only': last - sole,
               **{'n_' + label + '_articles': counts[label] for label in LABELS},
               'n_us_abstract_articles': counts['us_explicit'] + counts['us_inferred'],
               'n_us_mixed_country_articles': sum(codes[sid]['us_and_non_us_samples_reported'] == 'true' for sid in ids),
               'n_us_title_only_articles': sum(codes[sid]['title_only_us_signal'] == 'true' for sid in ids)}
        row['n_us_including_title_evidence_articles'] = row['n_us_abstract_articles'] + row['n_us_title_only_articles']
        row['us_abstract_share_of_ranked_articles'] = round(row['n_us_abstract_articles'] / len(ids), 6)
        enriched.append(row)
    annotated = []
    for sid in sorted(required, key=int):
        r = raw[sid]
        annotated.append({**{k: r[k] for k in ('scopus_id', 'doi', 'year', 'journal', 'title')},
                          **codes[sid], 'top40_authids': '|'.join(x['authid'] for x in links if x['scopus_id'] == sid),
                          'article_url': 'https://doi.org/' + r['doi'] if r['doi'] else 'https://www.scopus.com/record/display.uri?eid=' + r['eid']})
    return enriched, annotated, links


def enrich():
    inputs = {
        'ranking': ROOT / 'results/top40_provisional.csv',
        'affiliations': ROOT / 'inputs/top40_affiliations.csv',
        'annotations': ROOT / 'inputs/top40_us_annotations.csv',
        'articles': ROOT / 'private/articles.csv',
    }
    top, annotated, links = join(*(read_csv(inputs[k]) for k in ('ranking', 'affiliations', 'annotations', 'articles')))
    write_csv(ROOT / 'results/top40_enriched.csv', top)
    write_csv(ROOT / 'results/top40_article_annotations.csv', annotated)
    write_csv(ROOT / 'results/top40_author_article_links.csv', links)
    raw = unique_index(read_csv(inputs['articles']), 'scopus_id')
    write_csv(ROOT / 'private/top40_abstract_review.csv',
              [{**r, 'abstract': raw[r['scopus_id']]['abstract']} for r in annotated])
    counts = Counter(r['sample_us_label'] for r in annotated)
    countries = Counter(r['country'] for r in top)
    summary = {
        'annotation_date': max(r['review_date'] for r in annotated),
        'n_authors': len(top), 'n_unique_articles': len(annotated),
        'n_author_article_credits': len(links),
        'article_counts': {label: counts[label] for label in LABELS},
        'n_us_abstract_articles': counts['us_explicit'] + counts['us_inferred'],
        'n_mixed_country_us_articles': sum(r['us_and_non_us_samples_reported'] == 'true' for r in annotated),
        'n_title_only_us_articles': sum(r['title_only_us_signal'] == 'true' for r in annotated),
        'institution_country_counts': dict(sorted(countries.items())),
        'affiliation_verification_counts': dict(Counter(r['verification_status'] for r in top)),
        'human_validated_articles': sum(r['human_validated'] == 'true' for r in annotated),
        'unit': 'Articles with evidence of at least one US experimental sample; not independent samples or datasets',
        'first_last_credit_verified': True,
        'input_sha256': {k: digest(v.read_bytes()) for k, v in inputs.items()},
    }
    write_json(ROOT / 'results/top40_enrichment_summary.json', summary)
    write_reports(top, annotated, summary)
    print(json.dumps(summary, indent=2))
    return summary


def write_reports(top, annotated, s):
    c = s['article_counts']
    country_list = ', '.join(f'{country} ({count})' for country, count in sorted(s['institution_country_counts'].items()))
    intro = (f"The provisional top 40 have {s['n_author_article_credits']} first/last-author article credits across "
             f"{s['n_unique_articles']} distinct articles. All abstracts were available. "
             f"The abstract annotations identify **{c['us_explicit']} articles with explicit US sample evidence** "
             f"and **{c['us_inferred']} additional articles with US samples inferred from context**: "
             f"**{s['n_us_abstract_articles']} in total ({s['n_us_abstract_articles']/s['n_unique_articles']:.1%})**. "
             f"Another {c['non_us']} have evidence of non-US study populations, {c['unclear']} remain unclear, "
             f"and {c['not_applicable']} describe no applicable experimental sample. "
             f"{s['n_mixed_country_us_articles']} of the US-coded articles also describe non-US experimental samples.\n\n")
    method = ("We annotated the abstracts of the union of articles credited to the current top 40, then joined the labels "
              "to researchers by Scopus author ID. Explicit evidence names American respondents, a US sample or setting, "
              "or findings directly attributed to Americans. Contextual inference uses the study's US electoral, institutional, "
              "or social setting without a direct sampling statement; each inference has a recorded rationale. "
              "Non-US includes explicit and strongly contextual non-US study settings and means no US experimental sample "
              "was identified in the abstract, rather than proof that the full paper contains none. A US policy discussed "
              "by foreign respondents does not establish a US sample. Author affiliation, a panel vendor, generic political "
              "topics, or the word ‘national’ alone are insufficient. One inference rests on coverage of the 12 largest "
              "OECD importing countries; its country list needs confirmation.\n\n"
              "Counts refer to articles with at least one US experimental sample. An article may contain several experiments, "
              "reuse a sample, or analyze archived experiments. Abstracts cannot establish the number of independent datasets. "
              "The separately stated sample-count field records only an unambiguous report of separate US samples; blanks "
              "mean unavailable, not zero. These labels do not establish original fielding, parser compatibility, or data ownership.\n\n"
              "Ranking remains the number of distinct articles on which a researcher appears first or last: "
              "**score = first + last − sole-authored articles**. First and last columns both include sole-authored papers. "
              "Shared articles count once for each credited researcher but once in the overall article denominator. "
              "Author position is a proxy for PI involvement, not proof of seniority; alphabetical bylines and disciplinary "
              "conventions can weaken it. Current academic roles are supplied separately. Ties retain the existing numeric-ID "
              "display order; 22 authors share the eight-article cutoff, so displayed positions are not distinct score ranks.\n\n"
              "Affiliations were checked on 8 September 2026 using primary institutional or researcher-maintained sources. "
              "Country denotes the primary institution or campus, not citizenship or sample location. Joint units and secondary "
              f"appointments are retained in the affiliation notes. Institution/employer countries are {country_list}. "
              "The US entries include one dated nonacademic employer reference whose continuation and personal location "
              "require confirmation.\n\n"
              "The annotations were produced through one AI-assisted review using the actual abstracts, with earlier project "
              "annotations consulted as draft references. They have not been independently human-validated. Evidence spans, "
              "rationales, reviewer provenance, and abstract hashes are retained. All contextual inferences and unclear records "
              "should be checked before making definitive sample-geography claims in a publication.\n\n")
    title_note = (f"A separate title check identifies {s['n_title_only_us_articles']} additional articles whose titles specify "
                  f"a US setting or population while their abstracts do not. Including this clearly separated evidence yields "
                  f"{s['n_us_abstract_articles'] + s['n_title_only_us_articles']} US-associated articles. These title signals "
                  "are excluded from the primary abstract-based count.\n\n")
    lines = [intro, title_note, method,
             "[Enriched researcher CSV](results/top40_enriched.csv) · [Article annotations](results/top40_article_annotations.csv) · "
             "[Searchable table](TOP40.html) · [Complete selection query and methods](SUPPORTING_INFORMATION.md)\n\n",
             "| Position | Researcher | Institution / department | Country | First | Last | Sole | Score | US explicit | US inferred |\n",
             "|---:|---|---|---|---:|---:|---:|---:|---:|---:|\n"]
    for r in top:
        lines.append(f"| {r['position']} | {r['full_name']} | [{r['institution']}]({r['source_url']}); {r['department']} | "
                     f"{r['country']} | {r['n_first']} | {r['n_last']} | {r['n_sole']} | {r['n_articles']} | "
                     f"{r['n_us_explicit_articles']} | {r['n_us_inferred_articles']} |\n")
    lines.append("\nBrian Calfano's latakoo role is supported by an employer item dated June 2025; "
                 "current continuation requires confirmation. No academic department is verified. "
                 "Maykel Verkuyten is emeritus. Neither status changes the bibliographic ranking.\n")
    (ROOT / 'GEOGRAPHY_REPORT.md').write_text(''.join(lines), encoding='utf-8')
    (ROOT / 'results/geography_methods_paragraph.txt').write_text(
        f"For the provisional top {s['n_authors']}, we annotated sample geography in all {s['n_unique_articles']} credited article abstracts and linked "
        "the annotations by Scopus author ID. We distinguished explicit US sampling evidence from contextual US inference, "
        "non-US evidence, unclear geography, and no applicable experimental sample. An article with a US and non-US sample "
        "counted once as US-associated. Counts represent articles, not independent samples or datasets. Each non-unclear "
        "label retains an abstract evidence span; inference rationales, reviewer provenance, and source hashes permit audit. "
        "Current institution, department, role, and country were checked against primary profiles on 8 September 2026, "
        "with dated or less certain entries flagged. The AI-assisted annotations await independent human validation.\n",
        encoding='utf-8')
    table_html(top, intro + title_note)


def table_html(top, intro):
    # Self-contained and usable offline; external links are citations only.
    cols = [('position', 'Position'), ('full_name', 'Researcher'), ('institution', 'Institution'),
            ('department', 'Department / unit'), ('country', 'Country'), ('role', 'Role'),
            ('n_first', 'First'), ('n_last', 'Last'), ('n_sole', 'Sole'), ('n_articles', 'Score'),
            ('n_us_explicit_articles', 'US explicit'), ('n_us_inferred_articles', 'US inferred'),
            ('n_us_title_only_articles', 'US title only'), ('n_unclear_articles', 'Unclear'),
            ('verification_status', 'Affiliation evidence')]
    head = ''.join(f'<th><button type="button" data-col="{i}">{html.escape(label)}</button></th>' for i, (_, label) in enumerate(cols))
    body = []
    for r in top:
        cells = []
        for k, _ in cols:
            text = html.escape(str(r[k]))
            if k == 'institution':
                text = f'<a href="{html.escape(r["source_url"], quote=True)}">{text}</a>'
            cells.append('<td>' + text + '</td>')
        body.append('<tr>' + ''.join(cells) + '</tr>')
    document = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Survey experiment recruitment: top 40</title><style>
body{font:15px/1.5 system-ui,sans-serif;margin:2rem;color:#192b36}h1{font-size:1.8rem}p{max-width:1000px}
input{font:inherit;padding:.6rem;width:min(90%,550px);margin:1rem 0}.scroll{overflow:auto}table{border-collapse:collapse;width:100%}
th,td{padding:.6rem;text-align:left;border-bottom:1px solid #dbe3e8;vertical-align:top}th{background:#edf4f8;position:sticky;top:0}
th button{font:inherit;font-weight:600;border:0;background:none;cursor:pointer}tr:nth-child(even){background:#f8fafb}a{color:#136294}
td:nth-child(n+7):nth-child(-n+14){text-align:right}small{color:#445968}</style>
<h1>Survey experiment recruitment: provisional top 40</h1>'''
    document += '<p>' + html.escape(intro.replace('**', '')).replace('\n\n', '</p><p>') + '</p>'
    document += '''<p>Score = first + last − sole-authored articles. Author position indicates possible PI involvement; it does not establish seniority.
Labels are AI-assisted and await human validation. Country refers to the institution, not the samples.</p>
<p><a href="results/top40_enriched.csv">Download researcher CSV</a> · <a href="results/top40_article_annotations.csv">Article annotations</a> ·
<a href="GEOGRAPHY_REPORT.md">Methods and evidence notes</a> · <a href="SUPPORTING_INFORMATION.html">Full selection query</a></p>
<label for="search">Filter by researcher, institution, department, country, or role</label><br><input id="search" type="search">
<p id="count" aria-live="polite">40 researchers</p><div class="scroll"><table><thead><tr>'''
    document += head + '</tr></thead><tbody>' + ''.join(body) + '</tbody></table></div>'
    document += '''<p><small>Affiliations checked 8 September 2026. Calfano's employer reference dates to June 2025; continuation needs confirmation.
The title-only column is a subset of unclear abstracts and must not be added to that column. Click column headings to sort; displayed position preserves the original ranking.</small></p>
<script>
const tbody=document.querySelector('tbody'), rows=Array.from(tbody.rows), search=document.getElementById('search');
search.addEventListener('input',()=>{let n=0;for(const row of rows){row.hidden=!row.textContent.toLowerCase().includes(search.value.toLowerCase());if(!row.hidden)n++;}document.getElementById('count').textContent=n+' researchers';});
let previous=-1,ascending=true;for(const button of document.querySelectorAll('th button'))button.addEventListener('click',()=>{
const col=Number(button.dataset.col);ascending=previous===col?!ascending:true;previous=col;
rows.sort((a,b)=>{let x=a.cells[col].textContent,y=b.cells[col].textContent;const cmp=x!==''&&y!==''&&!isNaN(x)&&!isNaN(y)?Number(x)-Number(y):x.localeCompare(y);return ascending?cmp:-cmp;});
for(const row of rows)tbody.appendChild(row);});</script></html>'''
    (ROOT / 'TOP40.html').write_text(document, encoding='utf-8')


if __name__ == '__main__':
    enrich()
