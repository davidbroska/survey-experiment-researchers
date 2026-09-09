"""Prioritize unresolved papers by potential differentiation near the top 50.

This is a hypothetical US-positive resolution, not a predicted outcome. Total
article counts never change. Shared authorship is credited simultaneously.
"""
from itertools import combinations
from common import ROOT, read_csv, write_csv, write_json
from render import render


def assess(authors, queue, limit=50):
    people = {a['authid']: a for a in authors}
    counts = {k: {aid: int(a[k]) for aid, a in people.items()}
              for k in ('n_articles', 'n_us_articles')}
    ranks = {k: {aid: 1 + sum(n > value for n in values.values())
                 for aid, value in values.items()} for k, values in counts.items()}
    focus = {k: {aid for aid, rank in values.items() if rank <= limit}
             for k, values in ranks.items()}
    # Retain every author sharing the rank-50 boundary; avoid arbitrary ID cuts.
    uspairs = {tuple(sorted((a, b))) for a, b in combinations(focus['n_us_articles'], 2)
               if counts['n_us_articles'][a] == counts['n_us_articles'][b]}
    totalpairs = {tuple(sorted((a, b))) for a, b in combinations(focus['n_articles'], 2)
                  if counts['n_articles'][a] == counts['n_articles'][b]
                  and counts['n_us_articles'][a] == counts['n_us_articles'][b]}
    rows = []
    for q in queue:
        affected = set(q['credited_authids'].split('|'))
        if not affected <= people.keys():
            raise ValueError('Unknown credited author in priority queue')
        broken_us = {pair for pair in uspairs if len(set(pair) & affected) == 1}
        broken_total = {pair for pair in totalpairs if len(set(pair) & affected) == 1}
        distinct = broken_us | broken_total
        weight = sum(1 / min(ranks[k][a] for k in ('n_articles', 'n_us_articles')
                             for a in pair) for pair in distinct)
        updated = {a: n + (a in affected) for a, n in counts['n_us_articles'].items()}
        created = sum(counts['n_us_articles'][a] != counts['n_us_articles'][b]
                      and updated[a] == updated[b] for a, b in combinations(focus['n_us_articles'], 2))
        before_after = []
        for aid in sorted(affected, key=lambda aid: (ranks['n_us_articles'][aid], int(aid))):
            newrank = 1 + sum(n > updated[aid] for n in updated.values())
            before_after.append(f"{people[aid]['full_name']}: US {counts['n_us_articles'][aid]}→{updated[aid]}, rank {ranks['n_us_articles'][aid]}→{newrank}")
        rows.append({**q, 'top50_us_tied_pairs_separated_if_us': len(broken_us),
                     'top50_total_ties_differentiated_if_us': len(broken_total),
                     'distinct_tied_pairs_separated_if_us': len(distinct),
                     'new_top50_us_tied_pairs_if_us': created,
                     'potential_priority_weight': round(weight, 8),
                     'us_positive_scenario': '; '.join(before_after),
                     '_pairs': distinct})
    return rows, {'limit': limit, 'total_focus_authors_including_boundary_ties': len(focus['n_articles']),
                  'us_focus_authors_including_boundary_ties': len(focus['n_us_articles']),
                  'top50_us_tied_pairs': len(uspairs),
                  'top50_total_tied_pairs_with_equal_us_counts': len(totalpairs)}


def prioritize(authors, queue, root=ROOT):
    rows, info = assess(authors, queue)
    status_path = root / 'inputs/manual_download_status.csv'
    statuses = {r['scopus_id']: r for r in read_csv(status_path)} if status_path.exists() else {}
    for r in rows:
        r['manual_retrieval_status'] = statuses.get(r['scopus_id'], {}).get('status', '')
        r['manual_retrieval_note'] = statuses.get(r['scopus_id'], {}).get('note', '')
    candidates = [r for r in rows if r['local_pdf_available'] != 'true'
                  and r['manual_retrieval_status'] != 'user_unavailable' and r['_pairs']]
    # Greedy batch selection spreads requests across different tied pairs.
    ordered, covered = [], set()
    while candidates:
        best = min(candidates, key=lambda r: (-len(r['_pairs'] - covered),
                   -r['potential_priority_weight'], -r['distinct_tied_pairs_separated_if_us'], int(r['scopus_id'])))
        candidates.remove(best)
        best['new_pair_coverage_in_batch'] = len(best['_pairs'] - covered)
        covered |= best['_pairs']
        ordered.append(best)
        if len(ordered) % 10 == 0:
            covered = set()
    positions = {r['scopus_id']: i for i, r in enumerate(ordered, 1)}
    for r in rows:
        r['tie_priority_position'] = positions.get(r['scopus_id'], '')
        r['tie_priority_batch'] = (positions[r['scopus_id']]-1)//10+1 if r['scopus_id'] in positions else ''
        r.setdefault('new_pair_coverage_in_batch', 0)
        del r['_pairs']
    rows.sort(key=lambda r: (r['manual_retrieval_status'] == 'user_unavailable',
                            not bool(r['tie_priority_position']), r['tie_priority_position'] or int(r['queue_position'])))
    priority = [r for r in rows if r['tie_priority_position']]
    write_csv(root / 'results/top50_priority_downloads.csv', priority, list(rows[0]))
    write_json(root / 'results/top50_review_priority_summary.json', {
        **info, 'n_priority_downloads': len(priority),
        'n_user_unavailable': sum(r['manual_retrieval_status'] == 'user_unavailable' for r in rows),
        'total_article_counts_change': False,
        'interpretation': 'Potential distinction if this article has US participants; no probability or guaranteed net reduction in ties.'})
    lines = [f"{len(priority)} missing articles could distinguish at least one currently tied researcher pair near the top 50. "
             f"The focus includes {info['total_focus_authors_including_boundary_ties']} authors by total count and "
             f"{info['us_focus_authors_including_boundary_ties']} by US count, retaining all ties at rank 50.\n\n",
             "For each paper we simulate one additional US-article credit for every first/last author simultaneously. "
             "We count equal-US pairs that separate within the US top 50, and equal-total/equal-US pairs that become distinguishable "
             "on US evidence within the total-count top 50. A shared article cannot separate two authors who both receive its credit. "
             "Total article counts do not change. This is a possible outcome, not a prediction; a non-US resolution adds no US credit, "
             "and a US resolution may create new ties elsewhere.\n\n",
             "Each ten-paper batch greedily covers previously uncovered tied pairs. Ties in this priority use a weight favoring pairs "
             "closer to the top, then the number of pairs and Scopus ID. Papers already saved locally and papers reported unavailable "
             "are omitted. The CSV retains both separated and newly created US pairs. Recompute priorities after each review round.\n\n",
             "[Priority CSV](results/top50_priority_downloads.csv) · [Dashboard](TOP100.html#downloads) · "
             "[Complete manual queue](MANUAL_DOWNLOADS.html)\n\n"]
    for r in priority:
        if (r['tie_priority_position'] - 1) % 10 == 0:
            lines.append(f"**Batch {r['tie_priority_batch']}**\n\n")
        lines.append(f"{r['tie_priority_position']}. [{r['title']}]({r['manual_download_url']}) · "
                     f"[DOI / publisher]({r['article_url']}). Save as `{r['suggested_filename']}`. "
                     f"Potential: {r['top50_us_tied_pairs_separated_if_us']} US-ranking pairs; "
                     f"{r['top50_total_ties_differentiated_if_us']} total-count ties differentiated using US evidence. "
                     f"If US: {r['us_positive_scenario']}.\n\n")
    text = ''.join(lines)
    (root / 'PRIORITY_DOWNLOADS.md').write_text(text)
    (root / 'PRIORITY_DOWNLOADS.html').write_text(render(text, 'Downloads to distinguish tied top-50 researchers'))
    return rows
