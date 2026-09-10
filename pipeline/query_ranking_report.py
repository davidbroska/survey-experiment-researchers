"""Report query-ranking sensitivity without replacing the frozen dashboard."""
from collections import Counter
import json

from common import ROOT, digest, read_csv, write_csv, write_json
from render import render

RESULTS = ROOT / 'results/query_rankings_2026_09_10'


def integer(row, *keys):
    for key in keys:
        if row.get(key, '') not in ('', None):
            return int(row[key])
    return None


def ranked(rows, key):
    ordered = sorted(rows, key=lambda r: (-int(r[key]), int(r['authid'])))
    for i, r in enumerate(ordered):
        r = dict(r)
        r['display_position'] = i + 1
        r['competition_rank'] = 1 + sum(int(x[key]) > int(r[key]) for x in ordered)
        yield r


def markdown_table(rows, columns):
    def value(r, key):
        v = r.get(key)
        return '—' if v in ('', None) else str(v).replace('|', '/')
    return ('| ' + ' | '.join(label for _, label in columns) + ' |\n'
            + '| ' + ' | '.join('---' for _ in columns) + ' |\n'
            + ''.join('| ' + ' | '.join(value(r, k) for k, _ in columns) + ' |\n' for r in rows))


def collect():
    all_rows = {v: read_csv(RESULTS / (name + '_ranking.csv')) for v, name in
                [('full', 'original_query'), ('narrow', 'narrower_query'), ('current', 'current_published')]}
    us_rows = {v: read_csv(RESULTS / (name + '_us_ranking.csv')) for v, name in
               [('full', 'original_query'), ('narrow', 'narrower_query')]}
    us_rows['current'] = list(ranked(read_csv(ROOT / 'results/top100_enriched.csv'), 'n_us_articles'))
    affiliations = {r['authid']: r for r in read_csv(ROOT / 'inputs/researcher_affiliations.csv')}
    for r in read_csv(ROOT / 'inputs/query_ranking_name_reviews.csv'):
        affiliations.setdefault(r['authid'], {}).update(full_name=r['full_name'])
    authors = {}
    for v, rows in all_rows.items():
        for r in rows:
            aid = r['authid']
            a = authors.setdefault(aid, {'authid': aid, 'name': affiliations.get(aid, {}).get('full_name') or r['name']})
            a.update({v + '_all_count': int(r['n_articles']),
                      v + '_all_rank': integer(r, 'competition_rank', 'score_rank'),
                      v + '_all_position': integer(r, 'display_position', 'position')})
    for v, rows in us_rows.items():
        for r in rows:
            aid = r['authid']
            a = authors.setdefault(aid, {'authid': aid, 'name': affiliations.get(aid, {}).get('full_name') or r.get('name', aid)})
            a.update({v + '_us_count': integer(r, 'n_us_articles'),
                      v + '_us_rank': integer(r, 'us_competition_rank', 'us_rank', 'competition_rank', 'score_rank', 'us_count_rank_within_pool'),
                      v + '_us_position': integer(r, 'us_display_position', 'us_position', 'display_position', 'position'),
                      v + '_unclear': integer(r, 'n_unclear', 'n_unclear_articles'),
                      v + '_unreviewed': integer(r, 'n_unreviewed', 'n_unreviewed_articles') or 0,
                      v + '_us_upper': integer(r, 'n_us_upper', 'us_if_all_unclear_resolve_us')})
    for v, name in [('full', 'original_query'), ('narrow', 'narrower_query'), ('current', 'current_published')]:
        for r in read_csv(RESULTS / ('uniform_pool_' + name + '_us_ranking.csv')):
            a = authors[r['authid']]
            a.update({v + '_pool_count': int(r['n_us_articles']),
                      v + '_pool_rank': int(r['us_competition_rank']),
                      v + '_pool_position': int(r['us_display_position'])})
    for r in read_csv(RESULTS / 'focal_author_comparison.csv'):
        a = authors.setdefault(r['authid'], {'authid': r['authid'], 'name': r['name']})
        for v, name in [('full', 'original_query'), ('narrow', 'narrower_query'), ('current', 'current_published')]:
            a.update({v + '_all_count': int(r[name + '_n_articles']),
                      v + '_all_rank': integer(r, name + '_competition_rank'),
                      v + '_all_position': integer(r, name + '_display_position')})
    # A query-negative author has zero retrieved candidates; absent historical
    # US values instead remain unavailable because the old pool was restricted.
    for a in authors.values():
        if 'current_all_count' not in a:
            a.update(current_all_count=0, current_all_rank=None, current_all_position=None)
        for v in ('full', 'narrow'):
            if v + '_all_count' not in a or a[v + '_all_count'] == 0:
                a.update({v + '_all_count': 0, v + '_all_rank': None, v + '_all_position': None,
                          v + '_us_count': 0, v + '_us_rank': None, v + '_us_position': None,
                          v + '_unclear': 0, v + '_unreviewed': 0, v + '_us_upper': 0})
    fields = ['authid', 'name'] + [v + '_' + k for v in ('current', 'full', 'narrow')
                for k in ('all_count', 'all_rank', 'all_position', 'us_count', 'us_rank', 'us_position',
                          'pool_count', 'pool_rank', 'pool_position', 'unclear', 'unreviewed', 'us_upper')]
    out = [{k: a.get(k) for k in fields} for aid, a in sorted(authors.items(), key=lambda x: int(x[0]))]
    write_csv(RESULTS / 'comparison_authors.csv', out, fields)
    return out


def members(rows, variant, metric):
    return {r['authid'] for r in rows if r.get(f'{variant}_{metric}_position') is not None
            and r[f'{variant}_{metric}_position'] <= 100}


def changes(rows):
    lookup = {r['authid']: r for r in rows}
    details, counts = [], []
    for metric in ('all', 'pool', 'us'):
        for candidate, comparator in [('full', 'current'), ('narrow', 'current'), ('narrow', 'full')]:
            a, b = members(rows, candidate, metric), members(rows, comparator, metric)
            counts.append({'metric': metric, 'candidate': candidate, 'comparator': comparator,
                           'candidate_n': len(a), 'comparator_n': len(b), 'shared': len(a & b),
                           'enter': len(a - b), 'leave': len(b - a)})
            for status, ids in [('enter', a - b), ('leave', b - a)]:
                for aid in sorted(ids, key=int):
                    details.append({'metric': metric, 'candidate': candidate, 'comparator': comparator,
                                    'change': status, **lookup[aid]})
    write_csv(RESULTS / 'display_membership_changes.csv', details)
    write_csv(RESULTS / 'display_membership_summary.csv', counts)
    return details, counts


def build():
    rows = collect()
    details, counts = changes(rows)
    geo = json.loads((RESULTS / 'geography_summary.json').read_text())
    cutoffs = {}
    for v in ('current', 'full', 'narrow'):
        for m in ('all', 'pool', 'us'):
            selected = [r for r in rows if r[f'{v}_{m}_position'] == 100]
            cutoffs[v + '_' + m] = selected[0][v + '_' + m + '_count'] if selected else None
    data = {'authors': rows, 'cutoffs': cutoffs,
            'all_scope': 'All ranks compare first/last-author candidate articles. Current means the published ranking after a local phrase check; see the report for a harmonized retrieval-only baseline.',
            'us_scope': 'Current US ranks are within the old 100-person pool. New US ranks sort identified US evidence across the retrieved author universe; inspect unresolved coverage before interpreting movements.',
            'pool_scope': 'US ranks compare the same 120 researchers: the previous 100 plus both new total-count leaders including cutoff ties. Previous-query baseline means the original credited-article set with the same updated geography evidence. This is a conditional pool comparison, not a global US top 100.',
            'all_caveat': 'Query matches are candidates. These counts do not certify survey-experiment eligibility, parser compatibility, unique datasets or data ownership.',
            'us_caveat': 'US evidence combines explicit and contextual annotations. Unreviewed and unclear articles remain unresolved, so these are provisional evidence-count rankings, not a validated global US ranking.',
            'headlines': ['Complete clause: 9,675 candidates', 'Narrower clause: 9,365 candidates', '310 articles differ', 'First + last − sole authorship']}
    write_json(RESULTS / 'comparison_dashboard_data.json', data)
    serialized = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c').replace('&', '\\u0026')
    template = (ROOT / 'pipeline/query_ranking_template.html').read_text()
    (ROOT / 'RANKING_COMPARISON.html').write_text(template.replace('__DATA__', serialized))
    report(rows, details, counts, geo)
    from proximity_report import benchmark_page
    wave = ROOT / 'results/benchmark_review_wave2_2026_09_10'
    benchmark_page(read_csv(wave / 'availability_manifest.csv'),
                   read_csv(wave / 'article_consensus.csv'), str(wave.relative_to(ROOT)))
    write_json(RESULTS / 'comparison_report_provenance.json', {
        'input_sha256': {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in
                        [RESULTS / 'author_rank_comparison.csv', RESULTS / 'geography_summary.json',
                         RESULTS / 'original_query_us_ranking.csv', RESULTS / 'narrower_query_us_ranking.csv']},
        'dashboard_replaced': False, 'human_validated': False})
    print(f'Comparison rendered: {len(rows):,} researchers across preserved query variants')


def report(rows, details, counts, geo):
    def leaders(v, m, n=15):
        return sorted((r for r in rows if r[v + '_' + m + '_position'] is not None),
                      key=lambda r: r[v + '_' + m + '_position'])[:n]
    def change_names(metric, candidate, comparator, status):
        names = [r['name'] for r in details if (r['metric'], r['candidate'], r['comparator'], r['change'])
                 == (metric, candidate, comparator, status)]
        return '; '.join(names) if names else 'None.'
    metric_labels = {'all': 'All candidate articles', 'pool': 'US evidence, same 120 people',
                     'us': 'US evidence, partial global review'}
    variant_labels = {'full': 'Complete clause', 'narrow': 'Narrower clause', 'current': 'Historical baseline'}
    membership_table = [{**r, 'metric': metric_labels[r['metric']],
                         'candidate': variant_labels[r['candidate']],
                         'comparator': variant_labels[r['comparator']]} for r in counts]
    text = ('**Retain the complete-clause search for discovery and use the narrower query as a review-priority and sensitivity view.** '
            'The broader search preserves 310 additional articles, some of which are plausible survey experiments. The narrower query has not demonstrated higher precision in an independent sample. Study-level eligibility review provides a more defensible basis for donor recruitment than dropping ambiguous procedural language at retrieval.\n\n'
            '[Interactive ranking comparison](RANKING_COMPARISON.html) · [Full comparison CSV](results/query_rankings_2026_09_10/comparison_authors.csv) · [Queries and validation history](PROXIMITY_AUDIT.html).\n\n'
            'Both searches use the same 3,401-journal frame and 2010–2026 window. Every distinct article contributes once to each distinct first or last author; sole authors receive one credit. Six candidates in each new query remain uncredited because their bylines are unresolved. Two author lists capped at 100 were repaired using full ordered bylines. Equal counts share competition ranks; numeric author IDs determine the displayed order within ties. Names, topics, panel vendors and sample geography do not determine entry to the retrieval pool.\n\n'
            '**Top-100 membership changes.** The following table concerns the first 100 displayed researchers. Changes at a tied cutoff are not evidence of different productivity. Historical US membership means the old 100-person pool, which was selected by total article count. New US membership is based on the available US evidence across the wider author universe.\n\n'
            + markdown_table(membership_table, [('metric', 'Count'), ('candidate', 'Candidate'), ('comparator', 'Compared with'), ('shared', 'Retained'), ('enter', 'Enter'), ('leave', 'Leave')]) + '\n')
    text += ('**All-article leaders under both queries.**\n\n' + markdown_table(leaders('full', 'all'),
              [('name', 'Researcher'), ('current_all_rank', 'Current rank'), ('current_all_count', 'Current count'),
               ('full_all_rank', 'Complete rank'), ('full_all_count', 'Complete count'),
               ('narrow_all_rank', 'Narrower rank'), ('narrow_all_count', 'Narrower count')]) + '\n'
             + 'Enter the displayed top 100 under either query: ' + change_names('all', 'full', 'current', 'enter') + '\n\n'
             + 'Leave the displayed top 100 under either query: ' + change_names('all', 'full', 'current', 'leave') + '\n\n')
    text += ('**US-sample evidence.** Geography combines explicit US sample statements and justified contextual inference; author affiliations and generic panel names do not establish a US sample. Missing annotations are not coded non-US. '
             'The historical US list was restricted to the 100-person total-count pool. Its ranks therefore cannot be interpreted as ranks among all retrieved researchers. The new tables expose annotation coverage and unresolved-count scenarios.\n\n')
    text += (f"For a fair main comparison we reviewed the same {geo['union_current_and_new_total_leaders_authors']}-person pool: the historical 100 plus the new leaders including every cutoff tie. "
             f"All {geo['union_leader_pool_articles']:,} distinct articles across those versions have a geography judgment, including 160 newly reviewed metadata records; "
             f"{geo['union_leader_pool_articles_unreviewed']} remain unreviewed, while {geo['union_leader_pool_article_labels']['unclear']} still have unclear geography. "
             "The two new queries yield identical US-evidence counts for every researcher in this pool. The all-author US view remains partially annotated and must not be presented as a completed global top 100.\n\n")
    text += ('**US-evidence leaders within the same 120-person pool.** Both new queries give the ranks and counts below.\n\n' + markdown_table(leaders('full', 'pool'),
              [('name', 'Researcher'), ('current_pool_rank', 'Historical-credit rank, same pool'), ('current_pool_count', 'Historical-credit US count'),
               ('full_pool_rank', 'New within-pool rank'), ('full_pool_count', 'US evidence count'),
               ('full_unclear', 'Unclear'), ('full_unreviewed', 'Unreviewed')]) + '\n')
    focal_ids = {r['authid'] for r in read_csv(RESULTS / 'focal_author_comparison.csv')}
    text += ('**Diagnostic researchers.** These cases were used to test coverage, not as selection criteria. Neither new query puts them in the top 100; zero means no credited candidate, not no relevant research.\n\n'
             + markdown_table([r for r in rows if r['authid'] in focal_ids],
                 [('name', 'Researcher'), ('current_all_count', 'Published candidate count'),
                  ('full_all_count', 'Complete-clause count'), ('full_all_rank', 'Complete-clause rank'),
                  ('narrow_all_count', 'Narrower count'), ('narrow_all_rank', 'Narrower rank')]) + '\n')
    wave = ROOT / 'results/benchmark_review_wave2_2026_09_10'
    if (wave / 'review_summary.json').exists():
        acquisition = json.loads((wave / 'summary.json').read_text())
        reviews = json.loads((wave / 'review_summary.json').read_text())
        text += (f"**Additional full texts.** The user supplied {acquisition['download_files']} files matching {acquisition['unique_verified_download_articles']} additional fixed-sample articles. "
                 f"All originals and alternate copies are preserved privately. The benchmark now has {acquisition['articles_available_after_wave2']}/60 usable full texts, with {acquisition['articles_still_missing']} still missing. "
                 f"At this update, {reviews['double_pass']} articles have two AI-assisted reviews: {reviews['double_coded_yes']} agreed survey-experiment designs, {reviews['double_coded_no']} agreed negatives and {reviews['double_coded_unclear_or_disputed']} unresolved or disputed designs. "
                 "The original 18-review development stage remains immutable; later reviews are added in a separate stage. Neither availability nor AI agreement establishes human-validated precision. "
                 "One sample-geography disagreement was resolved by a separate page-cited adjudication; original coder judgments remain available. "
                 "[Updated inventory and download queue](FULLTEXT_BENCHMARK.html) · [Combined article judgments](results/benchmark_review_wave2_2026_09_10/article_consensus.csv) · [Adjudication](results/benchmark_review_wave2_2026_09_10/geography_adjudications.csv).\n\n")
        membership = {r['scopus_id']: r for r in read_csv(ROOT / 'results/proximity_specific_2026_09_10/membership.csv')}
        review_rows = read_csv(wave / 'article_consensus.csv')
        comparison = []
        for group, keep in [('Complete query', lambda r: True),
                            ('Retained by narrower query', lambda r: membership[r['scopus_id']]['primary_plus_specific'] == 'true'),
                            ('Removed by narrower query', lambda r: membership[r['scopus_id']]['primary_plus_specific'] != 'true')]:
            selected = [r for r in review_rows if keep(r)]
            reviewed = [r for r in selected if r['review_coverage'] == 'double_pass']
            labels = Counter(r['design'] for r in reviewed)
            comparison.append({'group': group, 'sampled': len(selected), 'double_reviewed': len(reviewed),
                               'design_yes': labels['yes'], 'design_no': labels['no'],
                               'design_unresolved': len(reviewed)-labels['yes']-labels['no'],
                               'design_yes_parser_yes': sum(r['design'] == 'yes' and r['parser_compatible'] == 'yes' for r in reviewed),
                               'parser_no': sum(r['parser_compatible'] == 'no' for r in reviewed)})
        write_csv(RESULTS / 'benchmark_retention_after_downloads.csv', comparison)
        text += ('The completed reviews strengthen the case for **reviewing the narrower set first**. All eight sampled removals are now available: six are design negatives and two are broad design positives; all eight were judged incompatible with the parser. All 27 design-positive, parser-compatible articles are retained. '\
                 'These are observed sample results; unequal sampling, incomplete access, AI annotation and post-hoc query development prevent interpreting the raw fractions as population precision.\n\n'
                 + markdown_table(comparison, [('group', 'Benchmark group'), ('sampled', 'Sampled'), ('double_reviewed', 'Reviewed'),
                                               ('design_yes', 'Design yes'), ('design_no', 'Design no'), ('design_unresolved', 'Unresolved'),
                                               ('design_yes_parser_yes', 'Design yes + parser yes')]) + '\n')
    text += ('**Interpretation and recruitment.** Count changes include differences in retrieval, byline completeness and the historical local phrase check. '
             'The [harmonized retrieval comparison](results/query_rankings_2026_09_10/author_rank_comparison.csv) separates the current raw-query baseline from the published ranking. '
             'The two new queries are nested and use identical metadata and annotations, making their comparison more direct. Twenty-eight older candidates that neither new query retrieves remain archived separately for screening.\n\n'
             'The historical dashboard uses frozen published credits and the geography then available for its original 100 researchers. The harmonized previous-query US baseline uses those same article-author credit pairs with present geography evidence and the same 120-person comparison pool as the new queries. These are different baselines.\n\n'
             'The new all-article top 100 is identical under both queries, including the same 114 researchers when cutoff ties are retained. Of the 16 displayed departures from the historical top 100, ten still have seven articles and share rank 83; they remain in the 114-person group. The six below the new cutoff are John Gastil, Jonas Tallberg, Giuliano Bonoli, André Blais, Oliver James and Geoffrey P. R. Wallace, each with six articles. Among the 114 leaders, only Janet Z. Yang has a different count under the two new queries (14 complete; 13 narrower); the resulting rank changes reflect ties.\n\n'
             'Use the complete query to define the discovery pool, screen articles for an actual randomized survey experiment and parser suitability, then rank eligible first/last-author articles. Apply US geography after discovery and report all cutoff ties. '
             'Before invitations, confirm whether researchers can provide respondent-level data and treatment materials; publication counts alone cannot establish ownership or the number of independent datasets. '
             'First/last authorship is a consistent proxy for possible PI involvement, not verified seniority. The TESS-derived journal frame still restricts the candidate universe and should be named in the methods.\n\n'
             '[Removal audit and methodological assessment](results/query_rankings_2026_09_10/methodological_assessment.md) · '
             '[Geography coverage and provenance](results/query_rankings_2026_09_10/geography_summary.json) · '
             '[All cutoff ties](results/query_rankings_2026_09_10/tie_metrics.csv). The original dashboard remains a historical comparison; all new annotations are provisional.\n')
    query = (ROOT / 'queries/proximity_audit_2026_09_10/targeted.txt').read_text().strip()
    text += ('\n**Discovery query.** The search combines three core routes—survey/vignette design labels, related experiment terms with a survey-participant context, and randomized reading assignments—with the proposed reading/manipulation proximity route. '
             'The first routes search titles, abstracts and keywords. The proximity route requires the procedural language and participant context in the abstract. '
             'Scopus double-quoted phrases support wildcards but do not preserve punctuation as exact brace phrases do; therefore query matches alone cannot establish design eligibility. '
             'Apply the [frozen journal Source IDs](results/venue_frame.csv) as a separate intersection. The query contains no researcher names or negative design keywords.\n\n'
             + '```text\n' + query + '\n```\n\n'
             'The [narrower sensitivity query](queries/proximity_specific_2026_09_10/primary_plus_specific.txt) removes only `read W/3 passage*` and `manipulat* W/3 information` from the final route; all core routes and filters remain identical. '
             '[Complete query file](queries/proximity_audit_2026_09_10/targeted.txt).\n')
    (ROOT / 'RANKING_COMPARISON_REPORT.md').write_text(text)
    (ROOT / 'RANKING_COMPARISON_REPORT.html').write_text(render(text, 'Query choice and researcher-ranking sensitivity'))


if __name__ == '__main__':
    build()
