"""Create a blinded RA verification draft from completed full-text reviews.

One random article per available journal, then additional journal-balanced
articles to reach 62. Targeted cases are kept separate.
"""
import csv
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
PRIVATE = ROOT / 'private/score'
SEED = 20261007


def read_rows(name):
    path = PRIVATE / name
    if not path.exists():
        return []
    with path.open(newline='', encoding='utf-8-sig') as handle:
        return list(csv.DictReader(handle))


def write_rows(path, rows):
    temporary = path.with_suffix('.csv.tmp')
    with temporary.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def main():
    articles = {r['article_id']: r for r in read_rows('articles.csv')}
    reviews = {r['article_id']: r for r in read_rows('fulltext_reviews.csv')}
    access = {r['article_id']: r for r in read_rows('fulltext.csv')}
    verified = {k for k, r in access.items() if r['status'] == 'verified_fulltext'}
    if not verified.issubset(reviews):
        raise ValueError('Finish the available full-text reviews before drawing the RA draft')
    original = {r['article_id']: r for r in read_rows('predictions_original.csv')}
    revised = {r['article_id']: r for r in read_rows('predictions_revised.csv')}
    groups = {}
    for key in sorted(verified):
        groups.setdefault(articles[key]['journal_id'], []).append(key)
    rng = np.random.default_rng(SEED)
    journals = sorted(groups)
    extra_pool = [journal for journal in journals if len(groups[journal]) > 1]
    extra_n = 62 - len(journals)
    if not 0 <= extra_n <= len(extra_pool):
        raise ValueError('Need enough available journals to draw 62 cases with at most two per journal')
    extra_journals = set(rng.choice(extra_pool, extra_n, replace=False))
    random_ids = []
    for journal in journals:
        n = 2 if journal in extra_journals else 1
        random_ids.extend(rng.choice(groups[journal], n, replace=False).tolist())
    reasons = {}
    for key in sorted(verified - set(random_ids)):
        truth = reviews[key]
        if truth['collection'] == 'UNCLEAR':
            reasons[key] = 'unresolved collection provenance'
        elif any(p.get(key, {}).get('collection') == 'NO' and truth['collection'] == 'YES'
                 for p in [original, revised]):
            reasons[key] = 'metadata discards an eligible article'
        elif any(key in p and any(p[key][f] == 'NO' and truth[f] == 'YES' for f in ['experiment', 'survey'])
                 for p in [original, revised]):
            reasons[key] = 'metadata misses an eligible subtype'
        elif any(key in p and any(p[key][f] != truth[f] for f in ['collection', 'experiment', 'survey'])
                 for p in [original, revised]):
            reasons[key] = 'metadata/reference disagreement or abstention'
    priority = {'unresolved collection provenance': 0, 'metadata discards an eligible article': 1,
                'metadata misses an eligible subtype': 2, 'metadata/reference disagreement or abstention': 3}
    shuffled = rng.permutation(sorted(reasons)).tolist()
    targeted_ids = sorted(shuffled, key=lambda k: priority[reasons[k]])[:20]
    key_rows = []
    for assignment, selected in [('random', random_ids), ('targeted', targeted_ids)]:
        packet = []
        for key in selected:
            article, fulltext = articles[key], access[key]
            packet.append(dict(article_id=key, doi=article['doi'], title=article['title'],
                               journal=article['journal'], year=article['year'],
                               fulltext_path=fulltext['fulltext_path'], text_cache=fulltext['text_cache'],
                               source_url=fulltext['source_url'], collection='', experiment='', survey='',
                               evidence_excerpt='', evidence_location='', rationale='',
                               collection_role_evidence='', reviewer='', review_date=''))
            journal = article['journal_id']
            n = 2 if journal in extra_journals else 1
            key_rows.append(dict(article_id=key, assignment=assignment, journal_id=journal,
                                 journal_available_n=len(groups[journal]), journal_selected_n=n if assignment == 'random' else '',
                                 conditional_selection_probability=n / len(groups[journal]) if assignment == 'random' else '',
                                 selection_probability=(1 + (62 - len(journals)) / len(extra_pool)) / len(groups[journal])
                                 if assignment == 'random' and journal in extra_pool else 1 if assignment == 'random' else '',
                                 selection_reason='random within journal' if assignment == 'random' else reasons[key],
                                 original_collection=original.get(key, {}).get('collection', ''),
                                 revised_collection=revised.get(key, {}).get('collection', ''),
                                 ai_collection=reviews[key]['collection'], ai_experiment=reviews[key]['experiment'],
                                 ai_survey=reviews[key]['survey']))
        write_rows(PRIVATE / f'ra_{assignment}_blind.csv', packet)
    write_rows(PRIVATE / 'ra_selection_key.csv', key_rows)
    all_journals = {r['journal_id']: r['journal'] for r in articles.values()}
    summary = dict(seed=SEED, random_n=len(random_ids), random_journals=len(journals),
                   targeted_n=len(targeted_ids), available_articles=len(verified),
                   unavailable_journals={j: name for j, name in all_journals.items() if j not in groups},
                   random_reference_classes=dict(Counter(reviews[k]['collection'] for k in random_ids)),
                   reference_sha256=hashlib.sha256((PRIVATE / 'fulltext_reviews.csv').read_bytes()).hexdigest(),
                   limitation='Random within available reviewed articles; availability and the retained pilot articles prevent population-wide accuracy estimates.')
    (PRIVATE / 'ra_verification_manifest.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(f'Prepared {len(random_ids)} random cases across {len(journals)} journals and {len(targeted_ids)} separate targeted cases.')


if __name__ == '__main__':
    main()
