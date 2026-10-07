"""Apply verified replacements within the original 620 journal/year cells.

Run after the retrieval pass: python3 score/replace_sample.py
Original samples and predictions remain preserved; replacement labels stay blank.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path

from common import now, read_csv, write_csv, write_json
from fetch_fulltext import export, safe_url
from sample import PRIVATE_FIELDS, PUBLIC_FIELDS

ROOT = Path(__file__).resolve().parent.parent
PRIVATE = ROOT / 'private/score'
STAGED = PRIVATE / 'replacements'


def index(rows):
    result = {row['article_id']: row for row in rows}
    assert len(result) == len(rows), 'Duplicate article IDs'
    return result


def main():
    original = index(read_csv(PRIVATE / 'articles_initial.csv'))
    initial_access = index(read_csv(PRIVATE / 'fulltext_initial.csv'))
    previous_access = index(read_csv(PRIVATE / 'fulltext.csv'))
    proposed = index(read_csv(STAGED / 'replacement_articles.csv'))
    audited = index(read_csv(STAGED / 'source_audit.csv'))
    changes = read_csv(STAGED / 'replacements.csv')
    rejected = {row['article_id'] for row in json.loads(
        (STAGED / 'bibliographic_rejections.json').read_text())}
    # A direct recovery of an original selection takes priority over a substitute.
    recovered = {key for key in original if key not in rejected and json.loads(
        (PRIVATE / 'acquisition' / (key + '.json')).read_text())['status'] == 'verified_fulltext'}
    changes = [row for row in changes if row['old_article_id'] not in recovered]
    proposed = {row['new_article_id']: proposed[row['new_article_id']] for row in changes}
    assert len(original) == 620 and set(original) == set(initial_access)
    assert len(changes) == len(proposed)
    assert {row['new_article_id'] for row in changes} == set(proposed)
    assert len({row['old_article_id'] for row in changes}) == len(changes)
    change_by_id = {row['new_article_id']: row for row in changes}
    assert not (proposed.keys() & original.keys()), 'Replacement is an original selection'
    rows = dict(original)
    for change in changes:
        old_id, new_id = change['old_article_id'], change['new_article_id']
        old, new = original[old_id], proposed[new_id]
        assert initial_access[old_id]['status'] != 'verified_fulltext', old_id
        for field in ['journal_id', 'journal', 'year']:
            assert old[field] == new[field] == change[field], (old_id, field)
        assert old['doi'].lower() == change['old_doi'].lower()
        assert new['doi'].lower() == change['new_doi'].lower()
        new['split'] = 'not_in_original_pilot'
        del rows[old_id]
        rows[new_id] = new
    assert len(rows) == 620 and len({(r['journal_id'], r['year']) for r in rows.values()}) == 620
    assert len({r['doi'].lower() for r in rows.values()}) == 620
    assert {r['year'] for r in rows.values()} == {str(y) for y in range(2016, 2026)}
    assert set(Counter(r['journal_id'] for r in rows.values()).values()) == {10}
    keep = {key for key, row in previous_access.items()
        if row['status'] == 'verified_fulltext' and key not in rejected}
    assert keep <= rows.keys(), 'An available article would be displaced'
    assert not rows.keys() & rejected, 'A known wrong-journal record remains selected'
    records = []
    for key, row in rows.items():
        record = json.loads((PRIVATE / 'acquisition' / (key + '.json')).read_text())
        assert record['article_id'] == key and record['doi'].lower() == row['doi'].lower(), key
        if key in proposed:
            assert record['status'] == 'verified_fulltext' and record.get('identity_check'), key
            assert record['source_sha256'] == change_by_id[key]['source_sha256'], key
            checked = audited[key]
            assert checked['manual_review_current_hash'] == 'True' and not checked['issues'], key
            assert checked['version_annotation_pending'] == 'False', key
            assert checked['source_sha256'] == record['source_sha256'], key
            assert record.get('version_note', '') == change_by_id[key].get('version_note', ''), key
        if record['status'] == 'verified_fulltext':
            path = Path(record['fulltext_path'])
            assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == record['source_sha256'], key
            cache = json.loads(Path(record['text_cache']).read_text())
            assert cache.get('pages') and cache['source_sha256'] == record['source_sha256'], key
        records.append(record)
    ordered = sorted(rows.values(), key=lambda r: (r['journal'].casefold(), -int(r['year'])))
    for directory, fields in [(PRIVATE, PRIVATE_FIELDS), (ROOT / 'score', PUBLIC_FIELDS)]:
        temporary = directory / 'articles.csv.tmp'
        write_csv(temporary, ordered, fields)
        temporary.replace(directory / 'articles.csv')
    change_fields = ['journal_id', 'journal', 'year', 'old_article_id', 'old_doi',
        'new_article_id', 'new_doi', 'candidate_rank', 'frame_n', 'candidate_order_seed',
        'selection_phase', 'reason', 'source_url', 'source_sha256', 'format', 'version_note', 'selected_at']
    public_changes = [dict(row, source_url=safe_url(row['source_url'])
        if row['source_url'].startswith(('https://', 'http://')) else '') for row in changes]
    write_csv(ROOT / 'score/replacements.csv', public_changes, change_fields)
    export(records)
    verified = sum(row['status'] == 'verified_fulltext' for row in records)
    write_json(ROOT / 'score/sample_validation.json', {
        'articles': len(rows), 'journals': 62, 'years': list(range(2016, 2026)),
        'split': dict(Counter(row['split'] for row in ordered)),
        'sources': dict(Counter(row['metadata_source'] for row in ordered)),
        'with_abstract': sum(bool(row['abstract']) for row in ordered),
        'with_keywords': sum(bool(row['keywords']) for row in ordered),
        'with_author_list': sum(bool(row['authors']) for row in ordered),
        'local_fulltexts': verified, 'unique_dois': 620,
        'author_counts_complete': all(int(row['n_authors']) > 0 for row in ordered),
        'replacements': len(changes), 'retained_initial_articles': 620 - len(changes),
        'selection_conditional_on_fulltext_access': True,
        'replacement_labels_transferred': False,
        'original_sample': 'articles_initial.csv', 'checked_at': now()})
    print(f'Applied {len(changes)} replacements: 620 journal/year cells, {verified} full texts.')


if __name__ == '__main__':
    main()
