"""Extend the frozen 2016–2026 search backwards, retaining its records verbatim.

The shorter original queries for 2016–2026 are logically equivalent within
their year partitions. Only 2010–2015 require new requests. A fresh complete
retrieval remains available through run.py retrieve.
"""
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

from common import ROOT, digest, read_csv, write_csv, write_json
import query
import scopus
from run import parse_entry

SNAPSHOT = ROOT / 'private/snapshots/2016_2026_before_extension'


def extend():
    old = json.loads((SNAPSHOT / 'results/retrieval_manifest.json').read_text())
    if not old['complete'] or query.START_YEAR >= 2016 or query.END_YEAR != 2026:
        raise ValueError('Extension requires a complete 2016–2026 baseline and an earlier start')
    frame_hash = digest((ROOT / 'results/venue_frame.csv').read_bytes())
    if old['frame_sha256'] != frame_hash:
        raise ValueError('Journal frame changed; cannot isolate the year-window effect')
    rows = read_csv(SNAPSHOT / 'private/articles.csv')
    if any(not 2016 <= int(r['year']) <= 2026 for r in rows):
        raise ValueError('Baseline contains an unexpected year')
    # Verify that only the lower bound differs from the current phrase query.
    old_query = (SNAPSHOT / 'queries/recommended.txt').read_text().strip()
    if old_query.replace('PUBYEAR > 2015', f'PUBYEAR > {query.START_YEAR-1}') != query.build().strip():
        raise ValueError('Query phrases changed; this is not a year-only extension')
    parts = [q + f' AND PUBYEAR = {y}' for q in query.groups()
             for y in range(query.START_YEAR, 2016)]
    entries, membership, manifests = {}, defaultdict(set), list(old['parts'])
    def fetch(item):
        i, q = item
        values, manifest = scopus.search(q)
        manifest['part'] = len(old['parts']) + i
        return values, manifest
    with ThreadPoolExecutor(max_workers=4) as pool:
        for f in as_completed([pool.submit(fetch, item) for item in enumerate(parts)]):
            values, m = f.result()
            manifests.append(m)
            for e in values:
                sid = e['dc:identifier']
                if sid not in entries or json.dumps(e, sort_keys=True) < json.dumps(entries[sid], sort_keys=True):
                    entries[sid] = e
                membership[sid].add(m['part'])
            print(f"Added {len(manifests)-len(old['parts'])}/{len(parts)} partitions; {len(entries)} older articles", flush=True)
    names = {r['authid']: r for r in read_csv(SNAPSHOT / 'inputs/author_names.csv')}
    older_names = {}
    frame = {r['source_id'] for r in read_csv(ROOT / 'results/venue_frame.csv')}
    for sid in sorted(entries, key=lambda s: int(s.split(':')[-1])):
        row, authors = parse_entry(entries[sid])
        row['retrieved_by_parts'] = '|'.join(str(i+1) for i in sorted(membership[sid]))
        row['in_frame'] = str(row['source_id'] in frame).lower()
        rows.append(row)
        older_names.update({a['authid']: a for a in authors})
    older_names.update(names)  # Preserve names from the more recent frozen records.
    rows.sort(key=lambda r: int(r['scopus_id']))
    if len({r['scopus_id'] for r in rows}) != len(rows):
        raise ValueError('Unexpected overlap across disjoint year windows')
    write_csv(ROOT / 'private/articles.csv', rows)
    write_csv(ROOT / 'inputs/author_names.csv', sorted(older_names.values(), key=lambda r: int(r['authid'])))
    write_json(ROOT / 'results/retrieval_manifest.json', {
        'query_sha256': digest(query.build()), 'frame_sha256': frame_hash,
        'n_articles': len(rows), 'n_in_frame': sum(r['in_frame'] == 'true' for r in rows),
        'complete': all(m['complete'] for m in manifests),
        'parts': sorted(manifests, key=lambda m: m['part']),
        'missing_abstracts': sum(not r['abstract'] for r in rows),
        'incomplete_bylines': sum(r['byline_complete'] != 'true' for r in rows),
        'indexed_keywords': old['indexed_keywords'],
        'extension': {'baseline_start': 2016, 'added_start': query.START_YEAR, 'added_end': 2015,
                      'baseline_articles_sha256': digest((SNAPSHOT / 'private/articles.csv').read_bytes()),
                      'baseline_records_unchanged': True,
                      'note': 'Baseline year partitions retain their equivalent original lower bound.'}})


if __name__ == '__main__':
    extend()
