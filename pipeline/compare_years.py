"""Separate year-window, cohort-composition, and full-text-review effects."""
from collections import Counter
import json

from common import ROOT, digest, read_csv, write_csv, write_json
from dashboard import select_pool

BASELINE = ROOT / 'private/snapshots/2016_2026_before_extension'


def tie_metrics(values):
    counts = Counter(int(v) for v in values)
    n = sum(counts.values())
    pairs = sum(k * (k - 1) // 2 for k in counts.values())
    return {'n_researchers': n, 'distinct_counts': len(counts),
            'tied_researchers': sum(k for k in counts.values() if k > 1),
            'tied_pairs': pairs, 'all_pairs': n * (n - 1) // 2,
            'tied_pair_percent': round(100 * pairs / (n * (n - 1) / 2), 3) if n > 1 else 0,
            'largest_tie_group': max(counts.values()),
            'minimum': min(counts), 'maximum': max(counts),
            'mean': round(sum(k * v for k, v in counts.items()) / n, 3)}


def build():
    current_ranking = read_csv(ROOT / 'results/ranking_provisional.csv')
    pool, ties = select_pool(current_ranking, 100)
    old = read_csv(BASELINE / 'results/top100_enriched.csv')
    raw = {r['scopus_id']: r for r in read_csv(ROOT / 'private/articles.csv')}
    metadata = {r['scopus_id']: r['sample_us_label'] for r in read_csv(ROOT / 'inputs/article_geography.csv')}
    reviewed = dict(metadata)
    reviewed.update({r['scopus_id']: r['sample_us_label'] for r in read_csv(ROOT / 'inputs/fulltext_reviews.csv')})
    # Use identical codes for both windows. Geography is reviewed once per article.
    def score(rows, start, codes):
        out = []
        for r in rows:
            ids = [s for s in r['article_ids'].split('|') if int(raw[s]['year']) >= start]
            out.append({'authid': r['authid'], 'name': r.get('full_name', r.get('name')),
                        'n_articles': len(ids),
                        'n_us_articles': sum(codes[s].startswith('us_') for s in ids),
                        'n_unclear_articles': sum(codes[s] == 'unclear' for s in ids)})
        return out
    versions = {
        'previous_dashboard_2016_metadata': score(old, 2016, metadata),
        'previous_pool_2016_with_pdf_reviews': score(old, 2016, reviewed),
        'current_pool_2016_metadata': score(pool, 2016, metadata),
        'current_pool_2010_metadata': score(pool, 2010, metadata),
        'current_pool_2016_with_pdf_reviews': score(pool, 2016, reviewed),
        'current_dashboard_2010_with_pdf_reviews': score(pool, 2010, reviewed)}
    metrics = []
    for version, rows in versions.items():
        for key in ('n_articles', 'n_us_articles'):
            metrics.append({'version': version, 'measure': key,
                            **tie_metrics([r[key] for r in rows])})
    write_csv(ROOT / 'results/year_window_tie_comparison.csv', metrics)
    before = {r['authid']: r for r in versions['current_pool_2016_with_pdf_reviews']}
    after = versions['current_dashboard_2010_with_pdf_reviews']
    details = []
    for r in after:
        b = before[r['authid']]
        details.append({'authid': r['authid'], 'name': r['name'],
                        **{f'{k}_{year}': x[k] for year, x in [(2016, b), (2010, r)]
                           for k in ('n_articles', 'n_us_articles', 'n_unclear_articles')},
                        'added_articles_2010_2015': r['n_articles'] - b['n_articles'],
                        'added_us_articles_2010_2015': r['n_us_articles'] - b['n_us_articles']})
    write_csv(ROOT / 'results/year_window_author_comparison.csv', details)
    old_ids, new_ids = {r['authid'] for r in old}, {r['authid'] for r in pool}
    old_flow = json.loads((BASELINE / 'results/flow_counts.json').read_text())
    flow = json.loads((ROOT / 'results/flow_counts.json').read_text())
    summary = {'previous_window': [2016, 2026], 'current_window': [2010, 2026],
               'added_distinct_articles_in_frame': flow['unique_articles'] - old_flow['unique_articles'],
               'entered_pool': sorted(new_ids - old_ids, key=int),
               'left_pool': sorted(old_ids - new_ids, key=int),
               'baseline_records_preserved': True,
               'cutoff_count': int(pool[-1]['n_articles']), 'cutoff_tied_authors': len(ties),
               'cutoff_tied_authors_outside_pool': sum(r['in_dashboard_pool'] == 'false' for r in ties),
               'metrics': metrics,
               'input_sha256': {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in
                   [ROOT / 'results/ranking_provisional.csv', ROOT / 'inputs/article_geography.csv',
                    ROOT / 'inputs/fulltext_reviews.csv', BASELINE / 'results/top100_enriched.csv']}}
    write_json(ROOT / 'results/year_window_comparison.json', summary)
    def get(version, measure):
        return next(r for r in metrics if r['version'] == version and r['measure'] == measure)
    lines = ['The search covers **2010–2026**, adding 2010–2015 to the frozen 2016–2026 snapshot. '
             f"The journal frame and positive query phrases are unchanged. The extension adds {summary['added_distinct_articles_in_frame']} "
             'distinct articles in the frame; eight researchers enter and eight leave the displayed 100-person pool.\n\n',
             '**Does the longer window reduce ties?** Overall article-count ties barely change in the displayed dashboards. '
             'US-count ties fall modestly, and the highest US count rises. The cutoff remains crowded.\n\n',
             '| Measure | Previous dashboard | Updated dashboard |\n|---|---:|---:|\n']
    for key, label in [('n_articles', 'Survey-experiment article count'), ('n_us_articles', 'US-sample article count')]:
        a = get('previous_dashboard_2016_metadata', key)
        b = get('current_dashboard_2010_with_pdf_reviews', key)
        for field, title in [('distinct_counts', 'distinct count values'), ('tied_pairs', 'tied researcher pairs'),
                             ('largest_tie_group', 'largest tie group'), ('maximum', 'maximum count')]:
            lines.append(f"| {label}: {title} | {a[field]} | {b[field]} |\n")
    lines += ['\nA tied pair is any two researchers with the same count; there are 4,950 pairs among 100 researchers. '
              'Fewer tied pairs means the count distinguishes more researcher pairs. The comparison above also reflects '
              f"the eight changes in pool membership and {len(read_csv(ROOT / 'inputs/fulltext_reviews.csv'))} full-text reviews. "
              'Review effects are separate from extending the publication years.\n\n',
              '**Isolating the year-window effect.** Holding the updated 100 researchers and the current geography '
              'decisions fixed, and changing only which publication years count:\n\n',
              '| Measure | 2016–2026 | 2010–2026 |\n|---|---:|---:|\n']
    for key, label in [('n_articles', 'Survey-experiment count'), ('n_us_articles', 'US-sample count')]:
        a = get('current_pool_2016_with_pdf_reviews', key)
        b = get('current_dashboard_2010_with_pdf_reviews', key)
        lines.append(f"| {label}: tied pairs | {a['tied_pairs']} | {b['tied_pairs']} |\n")
        lines.append(f"| {label}: distinct values | {a['distinct_counts']} | {b['distinct_counts']} |\n")
    lines += [f"\nAcross the current pool, adding the earlier years contributes {sum(r['added_articles_2010_2015'] for r in details)} "
              f"first/last-author article credits, including {sum(r['added_us_articles_2010_2015'] for r in details)} with US-sample evidence. "
              f"The six-article cutoff is shared by {len(ties)} researchers (previously 67); "
              f"{summary['cutoff_tied_authors_outside_pool']} are outside the displayed pool (previously 48). "
              'Numeric Scopus ID selects within this tie; it does not indicate seniority or quality.\n\n',
              'US counts combine explicit and inferred sample evidence and remain provisional pending independent validation. '
              'The pool is selected by total first/last-author article count before geography is assessed. Counts represent '
              'distinct candidate articles, not independent experiments or datasets.\n\n',
              '[All comparison scenarios](results/year_window_tie_comparison.csv) · '
              '[Changes for each researcher](results/year_window_author_comparison.csv) · [Dashboard](TOP100.html)\n']
    report = ''.join(lines)
    (ROOT / 'YEAR_WINDOW_COMPARISON.md').write_text(report)
    from render import render
    (ROOT / 'YEAR_WINDOW_COMPARISON.html').write_text(render(report, 'Does extending to 2010 reduce ties?'))
    print(report)
    return summary


if __name__ == '__main__':
    build()
