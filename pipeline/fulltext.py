"""Inventory locally supplied full texts; validate and apply reviewed evidence.

Optional PDF extraction: a local pdftotext executable or pypdf. No network calls.
"""
from collections import Counter
from datetime import date
import importlib.util
import json
import re
import shutil
import subprocess

from common import ROOT, digest, read_csv, write_csv, write_json
from enrich import LABELS, unique_index

FIELDS = ['scopus_id', 'sample_us_label', 'filename', 'source_sha256', 'page',
          'evidence_quote', 'rationale', 'us_and_non_us_samples_reported',
          'reviewer', 'reviewer_type', 'review_date', 'human_validated']


def file_id(filename):
    match = re.fullmatch(r'(\d+)(?:__[a-zA-Z0-9_-]+)?\.(?:pdf|txt)', filename)
    if not match:
        raise ValueError('Use <scopus_id>.pdf or <scopus_id>__supplement.pdf (or .txt)')
    return match.group(1)


def extract(path):
    if path.suffix == '.txt':
        return [path.read_text(encoding='utf-8')], 'plain_text'
    executable = shutil.which('pdftotext')
    if executable:
        run = subprocess.run([executable, '-layout', str(path), '-'], capture_output=True,
                             text=True, check=True, timeout=120)
        pages = run.stdout.split('\f')
        if pages and not pages[-1].strip():
            pages.pop()
        return pages, 'pdftotext'
    if importlib.util.find_spec('pypdf'):
        from pypdf import PdfReader
        return [p.extract_text() or '' for p in PdfReader(path).pages], 'pypdf'
    return [], 'extractor_unavailable'


def inventory(root=ROOT):
    folder = root / 'private/fulltext/inbox'
    folder.mkdir(parents=True, exist_ok=True)
    known = {r['scopus_id'] for r in read_csv(root / 'inputs/article_geography.csv')}
    rows, drafts = [], []
    for path in sorted(folder.iterdir()):
        if not path.is_file() or path.name.startswith('.'):
            continue
        row = {'filename': path.name, 'scopus_id': '', 'status': '', 'n_pages': 0,
               'source_sha256': digest(path.read_bytes()), 'text_cache': ''}
        try:
            sid = file_id(path.name)
            row['scopus_id'] = sid
            if sid not in known:
                raise ValueError('ID is outside the annotated researcher pool')
            pages, extractor = extract(path)
            row.update(n_pages=len(pages), status='text_ready_for_review' if any(p.strip() for p in pages)
                       else 'extractor_unavailable' if extractor == 'extractor_unavailable' else 'needs_ocr_or_manual_text')
            cache = root / 'private/fulltext/texts' / (path.name + '.json')
            cache.parent.mkdir(parents=True, exist_ok=True)
            write_json(cache, {'filename': path.name, 'source_sha256': row['source_sha256'],
                               'extractor': extractor, 'pages': pages})
            row['text_cache'] = str(cache.relative_to(root))
            drafts.append({**dict.fromkeys(FIELDS, ''), 'scopus_id': sid, 'filename': path.name,
                           'source_sha256': row['source_sha256'], 'human_validated': 'false'})
        except (ValueError, OSError, subprocess.SubprocessError) as error:
            row['status'] = str(error)
        except Exception as error:
            # A malformed/encrypted PDF must not stop inventorying the rest of a batch.
            row['status'] = 'extraction_error: ' + type(error).__name__
        rows.append(row)
    write_csv(root / 'private/fulltext/inventory.csv', rows,
              ['filename', 'scopus_id', 'status', 'n_pages', 'source_sha256', 'text_cache'])
    write_csv(root / 'private/fulltext/review_template.csv', drafts, FIELDS)
    print(f'{len(rows)} local files; {sum(r["status"] == "text_ready_for_review" for r in rows)} ready for evidence review.')
    return rows


def apply_reviews(authors, articles, links, reviews, root=ROOT):
    reviewed = unique_index(reviews, 'scopus_id')
    lookup = unique_index(articles, 'scopus_id')
    if not set(reviewed) <= set(lookup):
        raise ValueError('Full-text review references an article outside the pool')
    normalize = lambda s: ' '.join(s.split())
    for sid, review in reviewed.items():
        label = review['sample_us_label']
        if label not in LABELS or label == 'unclear':
            raise ValueError(f'Full-text override must resolve geography: {sid}')
        if file_id(review['filename']) != sid:
            raise ValueError(f'Full-text filename does not match article: {sid}')
        source = root / 'private/fulltext/inbox' / review['filename']
        cache = root / 'private/fulltext/texts' / (review['filename'] + '.json')
        if not source.is_file() or digest(source.read_bytes()) != review['source_sha256']:
            raise ValueError(f'Missing or changed full text: {sid}')
        evidence = json.loads(cache.read_text())
        if evidence['source_sha256'] != review['source_sha256']:
            raise ValueError(f'Stale extracted full text: {sid}')
        page = int(review['page'])
        if not 1 <= page <= len(evidence['pages']):
            raise ValueError(f'Invalid PDF page: {sid}')
        quote = normalize(review['evidence_quote'])
        if not quote or quote not in normalize(evidence['pages'][page - 1]):
            raise ValueError(f'Full-text evidence not found on cited page: {sid}')
        if not all(review.get(k) for k in ('rationale', 'reviewer', 'reviewer_type', 'review_date')):
            raise ValueError(f'Missing full-text review provenance: {sid}')
        date.fromisoformat(review['review_date'])
        if review['human_validated'] not in ('true', 'false'):
            raise ValueError(f'Invalid human-validation flag: {sid}')
        if review['reviewer_type'] == 'AI_assisted' and review['human_validated'] != 'false':
            raise ValueError(f'AI-only review cannot claim human validation: {sid}')
        if review['us_and_non_us_samples_reported'] not in ('true', 'false'):
            raise ValueError(f'Invalid mixed-country flag: {sid}')
        if review['us_and_non_us_samples_reported'] == 'true' and not label.startswith('us_'):
            raise ValueError(f'Mixed-country full-text review requires US evidence: {sid}')
    articles = [{**a, 'metadata_sample_us_label': a['sample_us_label'],
                 'source_review': 'metadata', 'fulltext_filename': '', 'fulltext_page': '',
                 'fulltext_source_sha256': ''} for a in articles]
    for a in articles:
        if a['scopus_id'] not in reviewed:
            continue
        r = reviewed[a['scopus_id']]
        a.update({k: r[k] for k in ('sample_us_label', 'evidence_quote', 'rationale',
                                   'us_and_non_us_samples_reported', 'reviewer', 'reviewer_type',
                                   'review_date', 'human_validated')})
        a.update(evidence_field='full_text', source_review='full_text', fulltext_filename=r['filename'],
                 fulltext_page=r['page'], fulltext_source_sha256=r['source_sha256'])
    codes = unique_index(articles, 'scopus_id')
    authors = [dict(r) for r in authors]
    for r in authors:
        ids = r['article_ids'].split('|')
        counts = Counter(codes[sid]['sample_us_label'] for sid in ids)
        r.update({'n_' + label + '_articles': counts[label] for label in LABELS})
        r['n_us_articles'] = counts['us_explicit'] + counts['us_inferred']
        r['n_mixed_country_us_articles'] = sum(codes[sid]['us_and_non_us_samples_reported'] == 'true' for sid in ids)
        r['us_if_all_unclear_resolve_us'] = r['n_us_articles'] + counts['unclear']
    for r in authors:
        r['us_count_rank_within_pool'] = 1 + sum(x['n_us_articles'] > r['n_us_articles'] for x in authors)
    links = [{**l, 'sample_us_label': codes[l['scopus_id']]['sample_us_label']} for l in links]
    return authors, articles, links


if __name__ == '__main__':
    inventory()
