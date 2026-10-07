"""Acquire the fixed SCORE sample without replacing inaccessible articles.

Run: python3 score/fetch_fulltext.py --workers 6
Downloads and extracted text remain local; score/access.csv has status only.
Existing credentials are sent only to api.elsevier.com. No login is bypassed.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
from http.client import HTTPException
import json
from pathlib import Path
import re
import shutil
import subprocess
import threading
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'private/score'
LITERATURE = ROOT.parent / 'Literature/SCORE'
from common import credentials

UA = 'SocialTune-SCORE/1.0 (scholarly research; public and institutional access)'
LOCK = threading.Lock()
HOSTS = {}
SUPPORT = r'supplement|\.supp|appendi[xc]|osf\.io|aspredicted|10\.7910/|dataverse|zenodo|figshare|dryad|github\.com'


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + f'.{threading.get_ident()}.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)


def read_csv(path):
    with path.open(newline='') as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    with temp.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    temp.replace(path)


def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text).casefold() if c.isalnum())


def sha(data):
    return hashlib.sha256(data).hexdigest()


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected and urlsplit(newurl).hostname != 'api.elsevier.com':
            for name in ('X-els-apikey', 'X-els-insttoken', 'Authorization'):
                redirected.remove_header(name)
        return redirected


def fetch(url, accept='application/pdf,text/html,application/xml;q=0.8', retry=False):
    """Cache response bytes and a header-free request receipt, including failures."""
    if url.startswith('http://'):
        url = 'https://' + url[7:]
    url = quote(url, safe=":/?=&%#+@;,!$'()*[]~-_")
    if urlsplit(url).scheme not in {'http', 'https'}:
        return {'url': url, 'error': 'unsupported_url'}, b''
    key = sha((url + '\n' + accept).encode())
    path = PRIVATE / 'http' / (key + '.json')
    body_path = path.with_suffix('.bin')
    if path.exists():
        previous = json.loads(path.read_text())
        if not retry or not previous.get('error'):
            return previous, body_path.read_bytes() if body_path.exists() else b''
    headers = {'User-Agent': UA, 'Accept': accept}
    if urlsplit(url).hostname == 'api.elsevier.com':
        try:
            headers.update(credentials())
            headers['Accept'] = accept
        except RuntimeError:
            pass
    with LOCK:
        gate = HOSTS.setdefault(urlsplit(url).hostname, threading.Semaphore(2))
    receipt = {'url': url, 'checked_at': datetime.now(timezone.utc).isoformat()}
    data = b''
    try:
        with gate, build_opener(SafeRedirect()).open(Request(url, headers=headers), timeout=20) as response:
            data = response.read(40 * 1024 * 1024 + 1)
            if len(data) > 40 * 1024 * 1024:
                raise ValueError('response_too_large')
            receipt.update(http_status=response.status, final_url=response.url,
                           content_type=response.headers.get('Content-Type', ''))
    except (HTTPError, URLError, HTTPException, TimeoutError, OSError, ValueError) as error:
        data = b''
        receipt.update(error=type(error).__name__, http_status=getattr(error, 'code', None))
    path.parent.mkdir(parents=True, exist_ok=True)
    if data:
        body_path.write_bytes(data)
    save_json(path, receipt)
    return receipt, data


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.pdfs, self.supporting = [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta' and attrs.get('name', '').lower() in {'citation_pdf_url', 'eprints.document_url'}:
            self.pdfs.append(attrs.get('content', ''))
        url = attrs.get('href', '')
        if re.search(r'\.pdf(?:$|[?#])|/bitstream/|/bitstreams/.+/content|viewcontent\.cgi', url, re.I):
            self.pdfs.append(url)
        if re.search(SUPPORT, url, re.I):
            self.supporting.append(url)


def identity(pages, article):
    opening = normalize(' '.join(pages[:3]))
    title = normalize(article['title'])
    words = set(re.findall(r'\w{4,}', article['title'].casefold()))
    coverage = sum(normalize(w) in opening for w in words) / max(len(words), 1)
    doi = normalize(article.get('doi', ''))
    if len(title) >= 20 and title in opening:
        return 'title_match'
    if doi and doi in opening and coverage >= 0.85:
        return 'doi_and_title_match'
    return ''


def document(data, article, url, existing_cache=''):
    """Return verified main text only; incomplete and mismatched copies remain pending."""
    pages, kind = [], ''
    if data.lstrip().startswith(b'%PDF-'):
        kind = 'pdf'
        candidate = PRIVATE / 'candidates' / (article['article_id'] + '.pdf')
        candidate.parent.mkdir(parents=True, exist_ok=True)
        candidate.write_bytes(data)
        if existing_cache and Path(existing_cache).exists():
            cached = json.loads(Path(existing_cache).read_text())
            if cached.get('source_sha256') == sha(data):
                pages = cached.get('pages', [])
        if not pages and shutil.which('pdftotext'):
            try:
                result = subprocess.run(['pdftotext', '-layout', str(candidate), '-'],
                                        capture_output=True, text=True, errors="replace", timeout=60, check=True)
                pages = result.stdout.rstrip('\f').split('\f')
            except (subprocess.SubprocessError, OSError):
                return None, 'pdf_extraction_failed'
    elif data.lstrip().startswith(b'<') and b'<html' not in data[:1000].lower():
        try:
            tree = ET.fromstring(data)
        except ET.ParseError:
            return None, 'invalid_xml'
        bodies = [e for e in tree.iter() if e.tag.split('}')[-1] == 'body']
        if not bodies:
            bodies = sorted([e for e in tree.iter() if e.tag.split('}')[-1] == 'sections'],
                            key=lambda e: len(' '.join(e.itertext())), reverse=True)
        if bodies and len(' '.join(bodies[0].itertext())) > 2500:
            title = next((' '.join(e.itertext()) for e in tree.iter() if e.tag.split('}')[-1] == 'title'), '')
            # Keep acknowledgments, appendices and author contributions: they establish who collected data.
            articles = [e for e in tree.iter() if e.tag.split('}')[-1] in {'article', 'converted-article', 'simple-article'}
                        and any(child is bodies[0] for child in e.iter())]
            content = articles[-1] if articles else bodies[0]
            pages = [title + '\n\n' + ' '.join(content.itertext())]
            kind = 'xml'
    if not pages:
        return None, 'no_extractable_main_text'
    match = identity(pages, article)
    if not match:
        return None, 'identity_unverified'
    beginning = ' '.join(pages[:1])[:1000]
    if re.search(r'supplement|appendix', url, re.I) or re.search(r'online appendi(?:x|ces)|supplement(?:ary material| to)', beginning[:600], re.I):
        return None, 'supplement_not_main_article'
    text = '\n'.join(pages)
    sections = re.findall(r'\b(introduction|method|methods|results|discussion|conclusion|references)\b', text.casefold())
    if len(text) < 5000 or (kind == 'pdf' and len(text) < 12000 and len(set(sections)) < 2):
        return None, 'identity_verified_completeness_needs_review'
    return {'pages': pages, 'format': kind, 'identity_check': match, 'source_sha256': sha(data)}, ''


def document_links(path):
    """Read actual hyperlinks; PDF display text can wrap or truncate URLs."""
    path = Path(path)
    if path.suffix == '.pdf' and shutil.which('pdfinfo'):
        try:
            result = subprocess.run(['pdfinfo', '-url', str(path)], capture_output=True,
                                    text=True, errors="replace", timeout=30, check=True)
            return re.findall(r'https?://\S+', result.stdout)
        except (subprocess.SubprocessError, OSError):
            return []
    if path.suffix == '.xml':
        tree = ET.parse(path)
        return [v for e in tree.iter() for v in e.attrib.values() if v.startswith(('https://', 'http://'))]
    return []


def discovery(articles, retry=False):
    """Look up exact DOI matches; access does not influence the fixed sample."""
    works = {}
    dois = sorted({r['doi'].lower() for r in articles if r.get('doi')})
    for start in range(0, len(dois), 40):
        group = dois[start:start + 40]
        url = 'https://api.openalex.org/works?' + urlencode({
            'filter': 'doi:' + '|'.join('https://doi.org/' + d for d in group),
            'per_page': 100, 'select': 'doi,locations,best_oa_location'})
        receipt, data = fetch(url, 'application/json', retry)
        try:
            for work in json.loads(data).get('results', []):
                works[work['doi'].replace('https://doi.org/', '').lower()] = work
        except (ValueError, KeyError, TypeError):
            pass
    return works


def retain_document(record, parsed, data, url):
    """Keep a verified source and extracted text in the private literature store."""
    article_id = record['article_id']
    destination = LITERATURE / (article_id + '.' + parsed['format'])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    text_path = PRIVATE / 'texts' / (article_id + '.json')
    save_json(text_path, {**parsed, 'article_id': article_id, 'source_url': url,
        'note': 'XML text uses one document segment, not a physical page.' if parsed['format'] == 'xml' else ''})
    record.update(status='verified_fulltext', source_url=url, fulltext_path=str(destination),
                  text_cache=str(text_path), n_pages=len(parsed['pages']),
                  **{k: parsed[k] for k in ('format', 'identity_check', 'source_sha256')})
    links = re.findall(r'https?://[^\s<>"\)]+', '\n'.join(parsed['pages']))
    links += document_links(destination)
    record['supporting_links'] = sorted(set(record.get('supporting_links', []) +
        [u.rstrip('.,;') for u in links if re.search(SUPPORT, u, re.I)]))


def acquire(article, works, retry=False):
    article = dict(article, article_id=article.get('scopus_id') or article['article_id'])
    article_id = article['article_id']
    path = PRIVATE / 'acquisition' / (article_id + '.json')
    if path.exists():
        previous = json.loads(path.read_text())
        complete = previous['status'] == 'verified_fulltext'
        current_routes = previous.get('route_version', 0) >= 3
        if previous.get('doi') == article.get('doi') and (complete or (not retry and current_routes)):
            file = Path(previous.get('fulltext_path', ''))
            if previous['status'] != 'verified_fulltext' or (file.is_file() and sha(file.read_bytes()) == previous['source_sha256']):
                return previous
    record = {key: article.get(key, '') for key in ('article_id', 'scopus_id', 'doi', 'title', 'journal', 'year')}
    record.update(status='unavailable_after_checks', source_url='', source_sha256='', fulltext_path='',
                  text_cache='', format='', identity_check='', n_pages=0, attempts=[], supporting_links=[], route_version=3)
    pending = []
    local = article.get('fulltext_path', '')
    if local and Path(local).is_file():
        pending.append(('local:' + local, 'local'))
    work = works.get(article.get('doi', '').lower(), {})
    locations = [work.get('best_oa_location')] + work.get('locations', [])
    for location in locations:
        if location and location.get('is_oa'):
            pending += [(location[k], 'open_location') for k in ('pdf_url', 'landing_page_url') if location.get(k)]
            pmcid = re.search(r'PMC(\d+)|/pmc/articles/(\d+)', location.get('landing_page_url') or '', re.I)
            if pmcid:
                number = pmcid.group(1) or pmcid.group(2)
                pending.insert(0, ('https://www.ebi.ac.uk/europepmc/webservices/rest/PMC' + number + '/fullTextXML', 'repository_xml'))
    if article.get('pdf_url'):
        pending.insert(0, (article['pdf_url'], 'metadata_pdf'))
    doi = article.get('doi', '')
    if doi:
        receipt, data = fetch('https://api.crossref.org/works/' + quote(doi, safe=''), 'application/json', retry)
        record['attempts'].append(receipt)
        try:
            metadata = json.loads(data).get('message', {})
            pending += [(r['URL'], 'crossref_fulltext') for r in metadata.get('link', []) if r.get('URL')]
            for relation in metadata.get('relation', {}).values():
                for related in relation:
                    if related.get('id-type') == 'doi':
                        record['supporting_links'].append('https://doi.org/' + related['id'])
        except (ValueError, TypeError, KeyError):
            pass
        if doi.lower().startswith('10.1016/'):
            pending.insert(1 if local else 0, ('https://api.elsevier.com/content/article/doi/' + quote(doi, safe='/') + '?view=FULL', 'elsevier_xml'))
        pending.append(('https://doi.org/' + doi, 'publisher'))
    seen = set()
    while pending and len(seen) < 12:
        url, route = pending.pop(0)
        if url in seen:
            continue
        seen.add(url)
        if route == 'local':
            receipt, data = {'url': url, 'route': route}, Path(url[6:]).read_bytes()
        else:
            receipt, data = fetch(url, 'text/xml' if route == 'elsevier_xml' else 'application/pdf,text/html,application/xml;q=0.8', retry)
            receipt = {**receipt, 'route': route}
        parsed, reason = document(data, article, url, article.get('text_cache', '') if route == 'local' else '')
        receipt['document_check'] = reason or parsed['identity_check']
        record['attempts'].append(receipt)
        if parsed:
            retain_document(record, parsed, data, url)
            break
        if data and ('html' in receipt.get('content_type', '') or b'<html' in data[:1000].lower()):
            links = Links()
            links.feed(data.decode(errors='replace'))
            base = receipt.get('final_url', url)
            pending = [(urljoin(base, link), 'page_pdf') for link in links.pdfs[:6]] + pending
            record['supporting_links'] += [urljoin(base, link) for link in links.supporting]
    record['supporting_links'] = sorted(set(u.rstrip('.,;') for u in record['supporting_links']
        if re.search(SUPPORT, u, re.I)))
    record['n_attempts'] = len(record['attempts'])
    record['checked_at'] = datetime.now(timezone.utc).isoformat()
    save_json(path, record)
    return record


def export(records):
    # Keep the complete sample visible while a retry updates a subset.
    by_id = {r['article_id']: r for r in records}
    for article in read_csv(PRIVATE / 'articles.csv'):
        article_id = article['article_id']
        path = PRIVATE / 'acquisition' / (article_id + '.json')
        if article_id not in by_id and path.exists():
            by_id[article_id] = json.loads(path.read_text())
    sample_ids = {a['article_id'] for a in read_csv(PRIVATE / 'articles.csv')}
    records = [by_id[key] for key in sorted(sample_ids & by_id.keys())]
    fields = ['article_id', 'scopus_id', 'doi', 'title', 'journal', 'year', 'status', 'format',
              'identity_check', 'source_url', 'source_sha256', 'fulltext_path', 'text_cache',
              'n_pages', 'n_attempts', 'checked_at']
    write_csv(PRIVATE / 'fulltext.csv', records, fields)
    public = [dict(r, source_url='' if r['source_url'].startswith('local:') else r['source_url']) for r in records]
    write_csv(ROOT / 'score/access.csv', public, [f for f in fields if f not in {'fulltext_path', 'text_cache'}])
    missing = [dict(r, doi_url='https://doi.org/' + r['doi']) for r in records
               if r['status'] != 'verified_fulltext']
    write_csv(ROOT / 'score/manual_downloads.csv', missing,
              ['article_id', 'journal', 'year', 'title', 'doi', 'doi_url', 'status'])


def supporting(record, retry=False):
    """Save linked supporting documents for review; a link does not validate its claims."""
    if record.get('supporting_version') == 2 and not retry:
        return record
    if record.get('fulltext_path'):
        record['supporting_links'] += [u for u in document_links(record['fulltext_path'])
            if re.search(SUPPORT, u, re.I)]
    record['supporting_links'] = sorted(set(record['supporting_links']))
    documents = []
    pending = sorted(record.get('supporting_links', []), key=lambda u: (not bool(re.search(r'supp|append', u, re.I)), -len(u)))
    dataverse = sorted(set(m[0] for u in pending for m in [re.search(r'10\.7910/[^?\s]+', u)] if m))
    pending = ['https://dataverse.harvard.edu/api/datasets/:persistentId/?' +
               urlencode({'persistentId': 'doi:' + doi}) for doi in dataverse] + pending
    seen = set()
    while pending and len(seen) < 4:
        url = pending.pop(0)
        if url in seen:
            continue
        seen.add(url)
        receipt, data = fetch(url, retry=retry)
        item = {**receipt, 'status': 'unavailable', 'linked_from_article': record['article_id']}
        if data.lstrip().startswith(b'%PDF-'):
            destination = LITERATURE / (record['article_id'] + f'__support_{len(documents)+1}.pdf')
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            try:
                result = subprocess.run(['pdftotext', '-layout', str(destination), '-'],
                                        capture_output=True, text=True, errors="replace", timeout=60, check=True)
                pages = result.stdout.rstrip('\f').split('\f')
                text_path = PRIVATE / 'texts' / (destination.stem + '.json')
                save_json(text_path, {'article_id': record['article_id'], 'pages': pages,
                    'source_url': url, 'source_sha256': sha(data), 'role': 'linked_supporting_document_unreviewed'})
                item.update(status='supporting_pdf_unreviewed', path=str(destination),
                            text_cache=str(text_path), source_sha256=sha(data))
            except (subprocess.SubprocessError, OSError):
                item['status'] = 'supporting_pdf_extraction_failed'
        elif data and 'application/json' in receipt.get('content_type', ''):
            destination = LITERATURE / (record['article_id'] + f'__support_{len(documents)+1}.json')
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            item.update(status='supporting_repository_metadata_unreviewed', path=str(destination), source_sha256=sha(data))
            try:
                files = json.loads(data).get('data', {}).get('latestVersion', {}).get('files', [])
                pending = ['https://dataverse.harvard.edu/api/access/datafile/' + str(f['dataFile']['id'])
                           for f in files if f.get('dataFile', {}).get('filename', '').lower().endswith('.pdf')] + pending
            except (ValueError, TypeError, KeyError):
                pass
        elif data and 'html' in receipt.get('content_type', ''):
            links = Links()
            links.feed(data.decode(errors='replace'))
            base = receipt.get('final_url', url)
            pending = [urljoin(base, link) for link in links.pdfs[:2]] + pending
            destination = LITERATURE / (record['article_id'] + f'__support_{len(documents)+1}.html')
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            item.update(status='supporting_page_unreviewed', path=str(destination), source_sha256=sha(data))
        documents.append(item)
    record.update(supporting_documents=documents, supporting_checked=True, supporting_version=2)
    save_json(PRIVATE / 'acquisition' / (record['article_id'] + '.json'), record)
    return record


def import_local(directory, articles):
    """Import missing PDFs named <article_id>.pdf; preserve already verified sources."""
    records = []
    for article in articles:
        article_id = article['article_id']
        source = directory / (article_id + '.pdf')
        if not source.is_file():
            continue
        path = PRIVATE / 'acquisition' / (article_id + '.json')
        record = json.loads(path.read_text()) if path.exists() else {
            key: article.get(key, '') for key in ('article_id', 'scopus_id', 'doi', 'title', 'journal', 'year')}
        if record.get('status') == 'verified_fulltext':
            print(f'{article_id}: already verified; skipped')
            continue
        url, data = 'local:' + str(source.resolve()), source.read_bytes()
        parsed, reason = document(data, article, url)
        if not parsed:
            print(f'{article_id}: not imported ({reason})')
            continue
        retain_document(record, parsed, data, url)
        record.setdefault('attempts', []).append({'url': url, 'route': 'manual_local',
            'document_check': parsed['identity_check'], 'checked_at': datetime.now(timezone.utc).isoformat()})
        record.update(n_attempts=len(record['attempts']), checked_at=datetime.now(timezone.utc).isoformat())
        save_json(path, record)
        records.append(record)
        print(f'{article_id}: imported verified PDF')
    export(records)
    print(f'Imported {len(records)} new fulltexts; no network requests made.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--workers', type=int, default=6)
    parser.add_argument('--retry-failures', action='store_true')
    parser.add_argument('--supporting', action='store_true', help='Also fetch up to four linked supporting sources per article.')
    parser.add_argument('--import-local', type=Path, metavar='DIRECTORY',
                        help='Import missing PDFs named <article_id>.pdf without network access.')
    args = parser.parse_args()
    articles = read_csv(PRIVATE / 'articles.csv')
    if args.import_local:
        directory = args.import_local.expanduser()
        if not directory.is_dir():
            parser.error('--import-local requires an existing directory')
        import_local(directory, articles)
        return
    if args.limit:
        articles = articles[:args.limit]
    works = discovery(articles, args.retry_failures)
    records = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(acquire, article, works, args.retry_failures) for article in articles]
        for future in as_completed(futures):
            record = future.result()
            if args.supporting:
                record = supporting(record, args.retry_failures)
            records.append(record)
            records.sort(key=lambda r: r['article_id'])
            export(records)
            ready = sum(r['status'] == 'verified_fulltext' for r in records)
            print(f'Checked {len(records)}/{len(articles)}; verified full text {ready}', flush=True)


if __name__ == '__main__':
    main()
