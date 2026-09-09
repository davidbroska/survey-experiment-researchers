"""Find and download public PDF copies of articles with unresolved geography.

OpenAlex supplies DOI-matched open locations. Only public publisher/repository
links are used, without cookies or credentials. PDFs must pass content and
bibliographic identity checks before entering the private full-text inbox.
Acquisition does not assign or change sample-geography labels.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
import json
import re
import shutil
import threading
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urljoin, urlsplit
from urllib.request import Request, urlopen

from common import ROOT, digest, now, read_csv, write_csv, write_json
from fulltext import extract

OA_ROOT = ROOT / 'private/open_access'
UA = 'SocialTuneLiteratureReview/1.0 (public scholarly full-text discovery)'
LOCK = threading.Lock()
HOST_LOCKS = {}


def normalize(value):
    value = unicodedata.normalize('NFKD', value).casefold()
    return ''.join(c for c in value if c.isalnum())


def doi_key(value):
    return re.sub(r'^https?://(?:dx\.)?doi\.org/', '', value or '', flags=re.I).casefold().strip()


def is_supplement(url, pages=()):
    return bool(re.search(r'supplement|_supp\.|sup\d+\.pdf|appendix', url, re.I)
                or (pages and re.match(r'\s*(?:online appendix|supplement to|supplementary (?:material|information))', pages[0], re.I)))


def metadata(url):
    path = OA_ROOT / 'metadata' / (digest(url) + '.json')
    if path.exists():
        return json.loads(path.read_text())
    try:
        with urlopen(Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'}), timeout=35) as response:
            result = {'url': url, 'checked_at': now(), 'body': json.load(response)}
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
        result = {'url': url, 'checked_at': now(), 'error': type(error).__name__,
                  'http_status': getattr(error, 'code', None)}
    write_json(path, result)
    return result


def discover(queue):
    by_doi, lookup_errors = {}, {}
    dois = sorted({doi_key(r['doi']) for r in queue if r['doi']})
    for start in range(0, len(dois), 40):
        group = dois[start:start+40]
        params = {'filter': 'doi:' + '|'.join('https://doi.org/' + d for d in group),
                  'per_page': 100, 'select': 'id,doi,title,open_access,best_oa_location,locations'}
        result = metadata('https://api.openalex.org/works?' + urlencode(params))
        if 'error' in result:
            lookup_errors.update({d: result['error'] for d in group})
        else:
            for work in result['body']['results']:
                d = doi_key(work.get('doi'))
                if d in group:
                    by_doi[d] = work
        print(f'OpenAlex metadata: {min(start+40,len(dois))}/{len(dois)} DOIs checked', flush=True)
    out = {}
    for row in queue:
        d = doi_key(row['doi'])
        work = by_doi.get(d)
        # Missing DOI or unindexed DOI: exact normalized-title match only.
        if not work and d not in lookup_errors:
            result = metadata('https://api.openalex.org/works?' + urlencode({
                'search': row['title'], 'per_page': 5,
                'select': 'id,doi,title,open_access,best_oa_location,locations'}))
            if 'body' in result:
                matches = [w for w in result['body']['results']
                           if normalize(w.get('title', '')) == normalize(row['title'])
                           and (not d or not w.get('doi') or doi_key(w['doi']) == d)]
                if len(matches) == 1:
                    work = matches[0]
        out[row['scopus_id']] = {'work': work, 'lookup_error': lookup_errors.get(d, '')}
    write_json(OA_ROOT / 'discovery.json', out)
    return out


class PDFLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'meta' and a.get('name', '').lower() in ('citation_pdf_url', 'eprints.document_url'):
            if a.get('content'):
                self.links.append(a['content'])
        if tag in ('a', 'link'):
            url = a.get('href', '')
            if re.search(r'\.pdf(?:$|[?#])|/bitstream/|/bitstreams/.+/(?:content|download)|/viewcontent\.cgi\?', url, re.I):
                self.links.append(url)


def fetch(url):
    if urlsplit(url).scheme not in ('http', 'https'):
        return {'error': 'unsupported_url'}
    host = urlsplit(url).netloc
    with LOCK:
        semaphore = HOST_LOCKS.setdefault(host, threading.Semaphore(2))
    path = OA_ROOT / 'responses' / (digest(url) + '.json')
    body_path = OA_ROOT / 'responses' / (digest(url) + '.bin')
    if path.exists():
        record = json.loads(path.read_text())
        return {**record, 'body': body_path.read_bytes() if body_path.exists() else b''}
    with semaphore:
        try:
            with urlopen(Request(url, headers={'User-Agent': UA, 'Accept': 'application/pdf,text/html;q=0.8'}), timeout=20) as response:
                data = response.read(40*1024*1024+1)
                if len(data) > 40*1024*1024:
                    raise ValueError('response_too_large')
                record = {'url': url, 'final_url': response.url, 'checked_at': now(),
                          'http_status': response.status, 'content_type': response.headers.get('Content-Type', '')}
                body_path.parent.mkdir(parents=True, exist_ok=True)
                body_path.write_bytes(data)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
            data = b''
            record = {'url': url, 'checked_at': now(), 'error': type(error).__name__,
                      'http_status': getattr(error, 'code', None)}
    write_json(path, record)
    return {**record, 'body': data}


def pdf_identity(data, article):
    if not data.lstrip().startswith(b'%PDF-'):
        return False, 'not_pdf', []
    temp = OA_ROOT / 'candidates' / (article['scopus_id'] + '.pdf')
    temp.parent.mkdir(parents=True, exist_ok=True)
    temp.write_bytes(data)
    try:
        pages, extractor = extract(temp)
    except Exception:
        return False, 'unreadable_pdf', []
    if len(pages) < 3:
        return False, 'short_pdf_needs_manual_completeness_check', pages
    initial = normalize(' '.join(pages[:3]))
    title = normalize(article['title'])
    if title and len(title) >= 20 and title in initial:
        return True, 'title_match_in_first_three_pages', pages
    # DOI + title words supports small punctuation, hyphenation, and layout changes.
    words = {normalize(w) for w in re.findall(r'\w{4,}', article['title'])}
    coverage = sum(w in initial for w in words) / len(words) if words else 0
    if article['doi'] and normalize(article['doi']) in initial and coverage >= .85:
        return True, 'doi_and_title_words_match_in_first_three_pages', pages
    return False, 'bibliographic_identity_needs_review', pages


def acquire(article, discovery):
    sid = article['scopus_id']
    work = discovery.get('work') or {}
    record = {**article, 'openalex_id': work.get('id', ''),
              'oa_status': work.get('open_access', {}).get('oa_status', 'unknown'),
              'acquisition_status': 'manual_download_needed', 'source_url': '', 'source_sha256': '',
              'identity_check': '', 'checked_at': now(), 'n_attempted_urls': 0,
              'open_location_found': 'false', 'reason': '', 'downloaded_filename': '', 'pdf_kind': ''}
    existing = ROOT / 'private/fulltext/inbox' / (sid + '.pdf')
    if existing.exists():
        previous = OA_ROOT / 'records' / (sid + '.json')
        if previous.exists():
            saved = json.loads(previous.read_text())
            if saved.get('source_sha256') == digest(existing.read_bytes()):
                return saved
        record.update(acquisition_status='already_in_inbox', source_sha256=digest(existing.read_bytes()))
        return record
    locations = [w for w in [work.get('best_oa_location'), *work.get('locations', [])]
                 if w and w.get('is_oa')]
    extra = ROOT / 'inputs/open_access_sources.csv'
    if extra.exists():
        locations += [{'is_oa': True, 'pdf_url': r['url']} for r in read_csv(extra) if r['scopus_id'] == sid]
    record['open_location_found'] = str(bool(locations)).lower()
    pending, seen = [], set()
    for location in locations:
        for key in ('pdf_url', 'landing_page_url'):
            url = location.get(key)
            if url and url.startswith('http://'):
                url = 'https://' + url[7:]
            if url and url not in pending:
                pending.append(url)
    record['open_location_url'] = pending[0] if pending else ''
    attempts = []
    while pending and len(seen) < 8:
        pending.sort(key=lambda u: is_supplement(u))
        url = pending.pop(0)
        if url in seen:
            continue
        seen.add(url)
        response = fetch(url)
        data = response.pop('body', b'')
        attempt = {**response, 'n_bytes': len(data)}
        if data.lstrip().startswith(b'%PDF-'):
            valid, identity, pages = pdf_identity(data, article)
            attempt['identity_check'] = identity
            if valid:
                supplement = is_supplement(url, pages)
                destination = existing.with_name(sid + '__supplement.pdf') if supplement else existing
                destination.parent.mkdir(parents=True, exist_ok=True)
                # Never overwrite a locally supplied file.
                if not destination.exists():
                    with destination.open('xb') as handle:
                        handle.write(data)
                elif digest(destination.read_bytes()) != digest(data):
                    attempts.append({**attempt, 'error': 'existing_file_conflict'})
                    continue
                sha = digest(data)
                write_json(ROOT / 'private/fulltext/texts' / (destination.name + '.json'),
                           {'filename': destination.name, 'source_sha256': sha,
                            'extractor': 'local_pdf_extraction', 'pages': pages})
                record.update(acquisition_status='downloaded_open_copy', source_url=url,
                              source_sha256=sha, identity_check=identity, reason='PDF acquired; geography review pending',
                              downloaded_filename=destination.name, pdf_kind='supplement' if supplement else 'article_or_manuscript')
                attempts.append(attempt)
                if not supplement:
                    break
                continue
        elif data and ('html' in response.get('content_type', '') or b'<html' in data[:1000].lower()):
            parser = PDFLinks()
            parser.feed(data.decode('utf-8', errors='replace'))
            for link in reversed(parser.links[:10]):
                absolute = urljoin(response.get('final_url', url), link)
                if absolute.startswith('http://'):
                    absolute = 'https://' + absolute[7:]
                if absolute not in seen and absolute not in pending:
                    pending.insert(0, absolute)
        attempts.append(attempt)
    record['n_attempted_urls'] = len(seen)
    if record['acquisition_status'] == 'manual_download_needed':
        record['reason'] = ('Metadata lookup failed; open availability undetermined' if discovery.get('lookup_error') else
                            'Open location indexed, but no verified PDF could be downloaded automatically' if locations else
                            'No open location found in the checked metadata; manual search or institutional access may succeed')
    write_json(OA_ROOT / 'attempts' / (sid + '.json'), attempts)
    return record


def run():
    OA_ROOT.mkdir(parents=True, exist_ok=True)
    snapshot = OA_ROOT / 'source_queue.csv'
    if not snapshot.exists():
        shutil.copy2(ROOT / 'results/fulltext_download_queue.csv', snapshot)
    queue = read_csv(snapshot)
    discovery = discover(queue)
    records = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(acquire, r, discovery[r['scopus_id']]): r for r in queue}
        for future in as_completed(futures):
            row = future.result()
            records.append(row)
            write_json(OA_ROOT / 'records' / (row['scopus_id'] + '.json'), row)
            print(f"Checked {len(records)}/{len(queue)}; {sum(r['acquisition_status'] == 'downloaded_open_copy' for r in records)} PDFs downloaded", flush=True)
    records.sort(key=lambda r: int(r['queue_position']))
    fields = list(queue[0]) + ['openalex_id','oa_status','acquisition_status','source_url','source_sha256',
              'identity_check','checked_at','n_attempted_urls','open_location_found','open_location_url','reason','downloaded_filename','pdf_kind']
    write_csv(ROOT / 'results/open_access_acquisition.csv', records, fields)
    manual = [r for r in records if r['acquisition_status'] == 'manual_download_needed']
    write_csv(ROOT / 'results/manual_download_queue.csv', manual, fields)
    write_json(ROOT / 'results/open_access_summary.json', {
        'n_checked': len(records), 'n_downloaded': sum(r['acquisition_status'] == 'downloaded_open_copy' for r in records),
        'n_already_in_inbox': sum(r['acquisition_status'] == 'already_in_inbox' for r in records),
        'n_manual_download_needed': len(manual),
        'n_with_indexed_open_locations': sum(bool((v.get('work') or {}).get('open_access', {}).get('is_oa')) for v in discovery.values()),
        'n_with_open_locations_after_web_search': sum(r['open_location_found'] == 'true' for r in records),
        'geography_labels_changed': False, 'source_queue_sha256': digest(snapshot.read_bytes()),
        'method': 'DOI-matched OpenAlex open locations, supplemented by targeted searches of primary author and institutional websites; public PDF retrieval and bibliographic verification within the first three pages. No indexed open copy is not proof of paywall-only availability.'})


if __name__ == '__main__':
    run()
