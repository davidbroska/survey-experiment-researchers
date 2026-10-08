"""Acquire main texts for the current SCORE articles; sample selection is separate.

Run: python3 score/fetch_fulltext.py --workers 6
Downloads and extracted text remain local; score/access.csv has status only.
Credentials are restricted to their provider's API hosts. No login is bypassed.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import gzip
import hashlib
from html.parser import HTMLParser
from http.client import HTTPException
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'private/score'
LITERATURE = ROOT.parent / 'Literature/SCORE'
from common import credentials, settings
csv.field_size_limit(sys.maxsize)

UA = 'SocialTune-SCORE/1.0 (scholarly research; public and institutional access)'
LOCK = threading.Lock()
HOSTS = {}
NEXT_REQUEST = {}
ACCESS = settings()
UNPAYWALL_EMAIL = ACCESS.get('UNPAYWALL_EMAIL', '')
SUPPORT = r'supplement|\.supp|appendi[xc]|osf\.io|aspredicted|10\.7910/|dataverse|zenodo|figshare|dryad|github\.com'
PRIVATE_QUERY = r'^(code|state|expires|googleaccessid|view_only)$|key|token|signature|credential|authorization|email|x-amz-'


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


def doi_key(text):
    """DOI case is insignificant; punctuation inside the identifier is not."""
    return text.strip().casefold().removeprefix('https://doi.org/').removeprefix('http://doi.org/').removeprefix('doi:').strip()


def sha(data):
    return hashlib.sha256(data).hexdigest()


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected:
            host = urlsplit(newurl).hostname
            allowed = {'X-els-apikey': {'api.elsevier.com'}, 'X-els-insttoken': {'api.elsevier.com'},
                       'Wiley-tdm-client-token': {'api.wiley.com'},
                       'Authorization': {'api.openalex.org', 'content.openalex.org'}}
            for name, hosts in allowed.items():
                if host not in hosts or urlsplit(newurl).scheme != 'https':
                    redirected.remove_header(name)
        return redirected


def safe_url(url):
    """Remove credentials and signed-download parameters from saved URLs."""
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not re.search(PRIVATE_QUERY, k, re.I)]
    return urlunsplit((parts.scheme, parts.netloc.rsplit('@', 1)[-1], parts.path, urlencode(query), ''))


def page_barrier(data):
    """Recognize explicit challenge/sign-in pages; a status alone is insufficient."""
    if not re.search(br'<html(?:\s|>)|<!doctype\s+html', data[:2000], re.I):
        return '', ''
    text = data[:65536].decode('utf-8', errors='replace')
    title = re.search(r'<title[^>]*>(.*?)</title>', text, re.I | re.S)
    title = re.sub(r'<[^>]+>', '', title.group(1)).strip() if title else ''
    if re.search(r'just a moment|checking your browser|security verification|access denied', title, re.I) and re.search(r'captcha|cf-chl|cloudflare|challenge', text, re.I):
        return 'bot_challenge', 'Browser-verification title and challenge markers'
    if re.search(r'^(?:login|log in|sign in)(?:\s|$)|(?:APA|PsycNet).*\b(?:login|log in|sign in)\b', title, re.I):
        return 'sign_in_page', 'Sign-in page title'
    if 'Article Full-Text Access' in text and 'Institutional Access' in text:
        return 'institutional_access_options', 'Article Full-Text Access / Institutional Access options'
    return '', ''


def fetch(url, accept='application/pdf,text/html,application/xml;q=0.8', retry=False, refresh=False):
    """Cache response bytes and a header-free request receipt, including failures."""
    if url.startswith('http://'):
        url = 'https://' + url[7:]
    url = quote(url, safe=":/?=&%#+@;,!$'()*[]~-_")
    if urlsplit(url).scheme not in {'http', 'https'}:
        return {'url': url, 'error': 'unsupported_url'}, b''
    if urlsplit(url).hostname == 'api.osf.io' and accept == 'application/pdf,text/html,application/xml;q=0.8':
        accept = 'application/json'  # Otherwise OSF can return its API documentation as HTML.
    key = sha((url + '\n' + accept).encode())
    path = PRIVATE / 'http' / (key + '.json')
    body_path = path.with_suffix('.bin')
    if path.exists() and not refresh:
        previous = json.loads(path.read_text())
        if not retry or not previous.get('error'):
            return previous, body_path.read_bytes() if body_path.exists() and not previous.get('error') else b''
    host = urlsplit(url).hostname
    if host == 'api.openalex.org' and urlsplit(url).path == '/works' and urlsplit(url).query:
        budget = openalex_allowance('list')
        if budget is None or not budget['available']:
            receipt = {'url': safe_url(url), 'checked_at': datetime.now(timezone.utc).isoformat(),
                       'error': 'FreeAllowanceUnavailable', 'failure_category': 'free_metadata_allowance_not_available'}
            body_path.unlink(missing_ok=True)
            save_json(path, receipt)
            return receipt, b''
    headers = {'User-Agent': UA, 'Accept': accept}
    if host == 'api.elsevier.com':
        try:
            headers.update(credentials())
            headers['Accept'] = accept
        except RuntimeError:
            pass
    if host == 'api.wiley.com' and (ACCESS.get('WILEY_API_KEY') or ACCESS.get('WILEY_TDM_TOKEN')):
        headers['Wiley-TDM-Client-Token'] = ACCESS.get('WILEY_TDM_TOKEN') or ACCESS['WILEY_API_KEY']
    if host in {'api.openalex.org', 'content.openalex.org'}:
        token = ACCESS.get('OPENALEX_API_KEY') or ACCESS.get('OPEN_ALEX')
        if token:
            headers['Authorization'] = 'Bearer ' + token
    with LOCK:
        gate = HOSTS.setdefault(host, threading.Semaphore(1 if host == 'api.wiley.com' else 2))
    receipt = {'url': safe_url(url), 'checked_at': datetime.now(timezone.utc).isoformat()}
    data = b''
    try:
        with gate:
            with LOCK:
                # Pace actual request starts, including requests previously waiting for a slot.
                interval = {'api.wiley.com': 10.1, 'api.unpaywall.org': 0.5,
                            'api.ies.ed.gov': 1.0}.get(host, 0)
                delay = max(0, NEXT_REQUEST.get(host, 0) - time.monotonic())
                NEXT_REQUEST[host] = time.monotonic() + delay + interval
            if delay:
                time.sleep(delay)
            receipt['checked_at'] = datetime.now(timezone.utc).isoformat()
            with build_opener(SafeRedirect()).open(Request(url, headers=headers), timeout=20) as response:
                data = response.read(40 * 1024 * 1024 + 1)
                if len(data) > 40 * 1024 * 1024:
                    raise ValueError('response_too_large')
                if data.startswith(b'\x1f\x8b'):
                    data = gzip.decompress(data)
                receipt.update(http_status=response.status, final_url=safe_url(response.url),
                               content_type=response.headers.get('Content-Type', ''))
                barrier, evidence = page_barrier(data)
                if barrier:
                    receipt.update(access_barrier=barrier, barrier_evidence=evidence)
    except (HTTPError, URLError, HTTPException, TimeoutError, OSError, ValueError, EOFError) as error:
        data = b''
        receipt.update(error=type(error).__name__, http_status=getattr(error, 'code', None))
        if isinstance(error, HTTPError):
            try:
                error_page = error.read(65536)
                barrier, evidence = page_barrier(error_page)
                if error.headers.get('cf-mitigated') == 'challenge':
                    barrier, evidence = 'bot_challenge', 'cf-mitigated: challenge'
                if barrier:
                    receipt.update(access_barrier=barrier, barrier_evidence=evidence)
            except (OSError, HTTPException):
                pass
        if isinstance(error, URLError):
            receipt['network_error_type'] = type(error.reason).__name__
        code = receipt['http_status']
        receipt['failure_category'] = ({403: 'invalid_or_unregistered_tdm_token',
            404: 'no_entitlement_or_article_not_available', 429: 'rate_limited'}.get(code, 'request_failed')
            if host == 'api.wiley.com' else
            {401: 'authentication_required', 403: 'forbidden', 404: 'not_found',
             429: 'rate_or_budget_limit', 500: 'provider_server_error'}.get(code, 'network_or_request_error'))
    path.parent.mkdir(parents=True, exist_ok=True)
    if data and host in {'api.openalex.org', 'api.unpaywall.org'}:
        for name, value in ACCESS.items():
            if value and name != 'UNPAYWALL_EMAIL':
                data = data.replace(value.encode(), b'[redacted]')
    if data:
        body_path.write_bytes(data)
    else:
        body_path.unlink(missing_ok=True)
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


def xml_identity(tree, article):
    """Match the main article metadata, never titles or DOIs in its references."""
    def child(element, name):
        return next((e for e in element if e.tag.split('}')[-1] == name), None) if element is not None else None

    metadata = child(tree, 'coredata')  # Elsevier full-text API.
    if tree.tag.split('}')[-1] == 'TEI':  # Grobid: only the header describes this article.
        file_desc = child(child(tree, 'teiHeader'), 'fileDesc')
        bibliography = child(child(file_desc, 'sourceDesc'), 'biblStruct')
        analytic = child(bibliography, 'analytic')
        title = child(analytic, 'title')
        if title is None:
            title = child(child(file_desc, 'titleStmt'), 'title')
        metadata = list(bibliography) if bibliography is not None else []
        metadata += list(analytic) if analytic is not None else []
    elif metadata is not None:
        title = child(metadata, 'title')
    else:
        main_article = tree if tree.tag.split('}')[-1] == 'article' else child(tree, 'article')
        metadata = child(child(main_article, 'front'), 'article-meta')  # JATS / Europe PMC.
        title = child(child(metadata, 'title-group'), 'article-title')
    if metadata is None or title is None:
        return ''
    dois = [''.join(e.itertext()).strip() for e in metadata
            if e.tag.split('}')[-1] == 'doi' or
            (e.tag.split('}')[-1] == 'article-id' and e.get('pub-id-type') == 'doi') or
            (e.tag.split('}')[-1] == 'idno' and e.get('type', '').casefold() == 'doi')]
    expected = doi_key(article.get('doi', ''))
    if dois and expected and not any(doi_key(doi) == expected for doi in dois):
        return ''
    return identity([' '.join(title.itertext()) + ' ' + ' '.join(dois)], article)


class PMCArticle(HTMLParser):
    """Read only the main article, excluding navigation and executable elements."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.metadata, self.stack, self.parts, self.links = {}, [], [], []
        self.roles, self.body_parts = [], []

    def append_text(self, text):
        if not self.stack or {'script','style','nav','button'}.intersection(self.stack): return
        self.parts.append(text)
        if (any('main-article-body' in role for role in self.roles) and
                not any({'abstract','ref-list'}.intersection(role) for role in self.roles)):
            self.body_parts.append(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta' and attrs.get('name', '').startswith('citation_'):
            self.metadata.setdefault(attrs['name'], attrs.get('content', ''))
        if self.stack or tag == 'article':
            if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:
                self.stack.append(tag)
                self.roles.append(set(attrs.get('class', '').split()))
            if tag in {'p','div','section','li','tr','h1','h2','h3','h4','br'}:
                self.append_text('\n')
            if tag == 'a' and attrs.get('href'):
                self.links.append(attrs['href'])

    def handle_endtag(self, tag):
        if tag in self.stack:
            index = len(self.stack) - 1 - self.stack[::-1].index(tag)
            self.stack = self.stack[:index]
            self.roles = self.roles[:index]
            self.append_text('\n')

    def handle_data(self, data):
        self.append_text(data)


def pmc_document(data, article, url):
    """An abstract or PDF challenge must never become an available main text."""
    if urlsplit(url).hostname not in {'pmc.ncbi.nlm.nih.gov', 'www.ncbi.nlm.nih.gov'}:
        return None, 'no_extractable_main_text'
    if not re.fullmatch(r'/(?:pmc/)?articles/(?:PMC)?\d+/?', urlsplit(url).path, re.I):
        return None, 'no_extractable_main_text'
    page = PMCArticle()
    page.feed(data.decode('utf-8', errors='replace'))
    title, doi = page.metadata.get('citation_title', ''), page.metadata.get('citation_doi', '')
    if doi and article.get('doi') and doi_key(doi) != doi_key(article['doi']):
        return None, 'identity_unverified'
    match = identity([title + ' ' + doi], article)
    if not match: return None, 'identity_unverified'
    text = re.sub(r'\n\s*\n+', '\n\n', ''.join(page.parts)).strip()
    body = ''.join(page.body_parts)
    if (re.search(r'online appendi(?:x|ces)|supplement(?:ary material| to)', text[:600], re.I) or
            re.search(r'^\s*(?:online appendi(?:x|ces)|supplement(?:ary (?:material|information)| to))\b', body[:600], re.I)):
        return None, 'supplement_not_main_article'
    headings = {line.strip().casefold().rstrip(':') for line in text.splitlines()}
    body_headings = {line.strip().casefold().rstrip(':') for line in body.splitlines()}
    sections = body_headings & {'introduction','method','methods','results','discussion','conclusion','conclusions'}
    if len(text) < 12000 or len(body) < 5000 or len(sections) < 2 or 'references' not in headings:
        return None, 'identity_verified_completeness_needs_review'
    version = 'PMC author manuscript; equivalence to the published version is unverified.' if re.search(
        r'author manuscript|accepted manuscript', text[:1500], re.I) else 'PMC full article HTML; source version requires independent confirmation.'
    version += ' Saved as one document segment, not physical pages. Images remain repository links; extracted text includes their captions.'
    return {'pages': [text], 'format': 'html', 'identity_check': 'pmc_metadata_' + match,
            'source_sha256': sha(data), 'version_note': version}, ''


def document(data, article, url, existing_cache=''):
    """Return verified main text only; incomplete and mismatched copies remain pending."""
    barrier, evidence = page_barrier(data)
    if barrier:
        return None, barrier
    if re.search(br'<html(?:\s|>)|<!doctype\s+html', data[:2000], re.I):
        return pmc_document(data, article, url)
    pages, kind, xml_match, xml_body = [], '', '', ''
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
        xml_match = xml_identity(tree, article)
        bodies = [e for e in tree.iter() if e.tag.split('}')[-1] == 'body']
        if not bodies:
            bodies = sorted([e for e in tree.iter() if e.tag.split('}')[-1] == 'sections'],
                            key=lambda e: len(' '.join(e.itertext())), reverse=True)
        if bodies and len(' '.join(bodies[0].itertext())) > 2500:
            xml_body = ' '.join(bodies[0].itertext())
            title = next((' '.join(e.itertext()) for e in tree.iter() if e.tag.split('}')[-1] == 'title'), '')
            # Keep acknowledgments, appendices and author contributions: they establish who collected data.
            articles = [e for e in tree.iter() if e.tag.split('}')[-1] in {'article', 'converted-article', 'simple-article', 'TEI'}
                        and any(child is bodies[0] for child in e.iter())]
            content = articles[-1] if articles else bodies[0]
            pages = [title + '\n\n' + ' '.join(content.itertext())]
            kind = 'xml'
    if not pages:
        return None, 'no_extractable_main_text'
    match = xml_match if kind == 'xml' else identity(pages, article)
    if not match:
        return None, 'identity_unverified'
    beginning = (xml_body if kind == 'xml' else ' '.join(pages[:1]))[:1000]
    if re.search(r'supplement|appendix', url, re.I) or re.search(r'online appendi(?:x|ces)|supplement(?:ary material| to)', beginning[:600], re.I):
        return None, 'supplement_not_main_article'
    if kind == 'xml' and tree.tag.split('}')[-1] == 'TEI':
        abstracts = [' '.join(e.itertext()) for e in tree.iter() if e.tag.split('}')[-1] == 'abstract']
        if not any(len(text.strip()) >= 100 for text in abstracts):
            # GROBID can attach the main paper's title to an appendix-only file.
            # Such a source needs an independent completeness check before use.
            return None, 'identity_verified_completeness_needs_review'
    text = '\n'.join(pages)
    sections = re.findall(r'\b(introduction|method|methods|results|discussion|conclusion|references)\b', text.casefold())
    if len(text) < 5000 or (kind == 'pdf' and len(text) < 12000 and len(set(sections)) < 2):
        return None, 'identity_verified_completeness_needs_review'
    return {'pages': pages, 'format': kind, 'identity_check': match, 'source_sha256': sha(data)}, ''


def document_links(path, source_url=''):
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
    if path.suffix == '.html':
        page = PMCArticle(); page.feed(path.read_text(errors='replace'))
        links = [urljoin(source_url, u) for u in page.links if not u.startswith('#')]
        return [u for u in links if u.startswith(('https://', 'http://'))]
    return []


def discovery(articles, retry=False):
    """Look up exact DOI matches; access does not influence the fixed sample."""
    works = {}
    dois = sorted({r['doi'].lower() for r in articles if r.get('doi')})
    for start in range(0, len(dois), 40):
        group = dois[start:start + 40]
        url = 'https://api.openalex.org/works?' + urlencode({
            'filter': 'doi:' + '|'.join('https://doi.org/' + d for d in group),
            'per_page': 100, 'select': 'id,doi,locations,best_oa_location,has_content,content_urls'})
        receipt, data = fetch(url, 'application/json', retry)
        try:
            for work in json.loads(data).get('results', []):
                works[work['doi'].replace('https://doi.org/', '').lower()] = work
        except (ValueError, KeyError, TypeError):
            pass
    return works


def eric_sources(article):
    """ERIC sometimes hosts author manuscripts absent from OA aggregators."""
    url = 'https://api.ies.ed.gov/eric/?' + urlencode({
        'search': 'title:"' + article['title'] + '"', 'format': 'json', 'rows': 20})
    receipt, data = fetch(url, 'application/json')
    receipt['route'] = 'eric_discovery'
    try:
        entries = json.loads(data)['response']['docs']
    except (ValueError, KeyError, TypeError):
        return receipt, []
    ids = [r['id'] for r in entries if normalize(r.get('title', '')) == normalize(article['title'])
           and re.fullmatch(r'E[DJ]\d+', r.get('id', ''))]
    return receipt, ['https://files.eric.ed.gov/fulltext/' + article_id + '.pdf' for article_id in sorted(set(ids))]


def retain_document(record, parsed, data, url):
    """Keep a verified source and extracted text in the private literature store."""
    article_id = record['article_id']
    destination = LITERATURE / (article_id + '.' + parsed['format'])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    text_path = PRIVATE / 'texts' / (article_id + '.json')
    url = safe_url(url)
    save_json(text_path, {**parsed, 'article_id': article_id, 'source_url': url,
        'note': 'XML/HTML text uses one document segment, not a physical page.' if parsed['format'] in {'xml','html'} else ''})
    record.update(status='verified_fulltext', source_url=url, fulltext_path=str(destination),
                  text_cache=str(text_path), n_pages=len(parsed['pages']),
                  **{k: parsed[k] for k in ('format', 'identity_check', 'source_sha256')})
    if parsed.get('version_note'):
        record['version_note'] = parsed['version_note']
    links = re.findall(r'https?://[^\s<>"\)]+', '\n'.join(parsed['pages']))
    links += document_links(destination, url)
    record['supporting_links'] = sorted(set(record.get('supporting_links', []) +
        [safe_url(u.rstrip('.,;')) for u in links if re.search(SUPPORT, u, re.I)]))


def retain_candidate(record, data, url, reason):
    """Keep identity-matched incomplete files and supplements separate from main text."""
    roles = {'identity_verified_completeness_needs_review': 'incomplete_main_candidate',
             'supplement_not_main_article': 'supplement_candidate'}
    if reason not in roles or not data:
        return
    kind = 'pdf' if data.lstrip().startswith(b'%PDF-') else 'html' if re.search(br'<html(?:\s|>)|<!doctype\s+html', data[:2000], re.I) else 'xml'
    digest = sha(data)
    destination = LITERATURE / (record['article_id'] + '__' + roles[reason] + '_' + digest[:12] + '.' + kind)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    item = {'url': safe_url(url), 'path': str(destination), 'source_sha256': digest,
            'format': kind, 'status': roles[reason] + '_unreviewed'}
    candidates = record.setdefault('candidate_documents', [])
    if not any(c['source_sha256'] == digest for c in candidates):
        candidates.append(item)


def route_key(url):
    """Group equivalent publisher routes, while keeping different endpoints apart."""
    parsed = urlsplit(url)
    return (parsed.hostname or '') + '/'.join(parsed.path.split('/')[:3])


def acquire(article, works, retry=False, blocked_routes=None):
    article = dict(article, article_id=article.get('scopus_id') or article['article_id'])
    article_id = article['article_id']
    path = PRIVATE / 'acquisition' / (article_id + '.json')
    if path.exists():
        previous = json.loads(path.read_text())
        complete = previous['status'] == 'verified_fulltext'
        current_routes = previous.get('route_version', 0) >= 4
        if previous.get('doi') == article.get('doi') and (complete or (not retry and current_routes)):
            file = Path(previous.get('fulltext_path', ''))
            if previous['status'] != 'verified_fulltext' or (file.is_file() and sha(file.read_bytes()) == previous['source_sha256']):
                return previous
    record = {key: article.get(key, '') for key in ('article_id', 'scopus_id', 'doi', 'title', 'journal', 'year')}
    record.update(status='unavailable_after_checks', source_url='', source_sha256='', fulltext_path='',
                  text_cache='', format='', identity_check='', n_pages=0, attempts=[], supporting_links=[], route_version=4)
    if path.exists():
        # Keep earlier attempts as provenance when newly configured routes are tried.
        record['attempts'] = previous.get('attempts', [])
        record['supporting_links'] = previous.get('supporting_links', [])
        record['supporting_documents'] = previous.get('supporting_documents', [])
        record['candidate_documents'] = previous.get('candidate_documents', [])
        record['version_note'] = previous.get('version_note', '')
        record['cached_pdf_repair_status'] = previous.get('cached_pdf_repair_status', '')
    pending = []
    local = article.get('fulltext_path', '')
    if local and Path(local).is_file():
        pending.append(('local:' + local, 'local'))
    work = works.get(article.get('doi', '').lower(), {})
    locations = [work.get('best_oa_location')] + work.get('locations', [])
    doi = article.get('doi', '')
    if doi and UNPAYWALL_EMAIL:
        receipt, data = fetch('https://api.unpaywall.org/v2/' + quote(doi, safe='') + '?' +
                              urlencode({'email': UNPAYWALL_EMAIL}), 'application/json', retry)
        record['attempts'].append({**receipt, 'route': 'unpaywall_discovery'})
        try:
            unpaywall = json.loads(data)
            locations += [dict(location, is_oa=True) for location in unpaywall.get('oa_locations', [])]
        except (ValueError, TypeError, KeyError):
            pass
    for location in locations:
        if location and location.get('is_oa'):
            pdf = location.get('pdf_url') or location.get('url_for_pdf')
            landing = location.get('landing_page_url') or location.get('url_for_landing_page')
            pending += [(u, 'open_location') for u in (pdf, landing) if u]
            pmcid = re.search(r'PMC(\d+)|/pmc/articles/(\d+)', landing or '', re.I)
            if pmcid:
                number = pmcid.group(1) or pmcid.group(2)
                pending.append(('https://pmc.ncbi.nlm.nih.gov/articles/PMC' + number + '/', 'repository_main_html'))
                pending.insert(0, ('https://www.ebi.ac.uk/europepmc/webservices/rest/PMC' + number + '/fullTextXML', 'repository_xml'))
    if article.get('pdf_url'):
        pending.insert(0, (article['pdf_url'], 'metadata_pdf'))
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
        wiley = doi.lower().startswith(('10.1111/', '10.1002/', '10.3982/'))
        if wiley or any('api.wiley.com' in u for u, route in pending):
            if ACCESS.get('WILEY_TDM_TOKEN') or ACCESS.get('WILEY_API_KEY'):
                pending.insert(1 if local else 0, ('https://api.wiley.com/onlinelibrary/tdm/v1/articles/' +
                               quote(doi, safe=''), 'wiley_tdm'))
        pending.append(('https://doi.org/' + doi, 'publisher'))
    seen = set()
    while pending and len(seen) < 20:
        url, route = pending.pop(0)
        if url in seen:
            continue
        seen.add(url)
        blocked = (blocked_routes or {}).get(route_key(url))
        if blocked:
            record['attempts'].append({'url': safe_url(url), 'route': route,
                'document_check': 'not_retried_after_repeated_platform_barrier',
                'previous_barrier': blocked['barrier'],
                'reference_article_ids': blocked['article_ids']})
            continue
        if 'onlinelibrary.wiley.com' in (urlsplit(url).hostname or ''):
            record['attempts'].append({'url': safe_url(url), 'route': route,
                'document_check': 'use_wiley_tdm_api', 'failure_category': 'publisher_api_required'})
            continue
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
        retain_candidate(record, data, url, reason)
        if data and ('html' in receipt.get('content_type', '') or b'<html' in data[:1000].lower()):
            links = Links()
            links.feed(data.decode(errors='replace'))
            base = receipt.get('final_url', url)
            pending = [(urljoin(base, link), 'page_pdf') for link in links.pdfs[:6]] + pending
            record['supporting_links'] += [urljoin(base, link) for link in links.supporting]
    record['supporting_links'] = sorted(set(safe_url(u.rstrip('.,;')) for u in record['supporting_links']
        if re.search(SUPPORT, u, re.I)))
    record['n_attempts'] = len(record['attempts'])
    record['checked_at'] = datetime.now(timezone.utc).isoformat()
    save_json(path, record)
    return record


def access_problem(record):
    """Give an honest next step without treating every failure as a paywall."""
    candidates = record.get('candidate_documents', [])
    latest = {a.get('url'): a for a in record.get('attempts', [])
              if not a.get('route', '').endswith('_discovery') and
              'api.crossref.org' not in a.get('url', '')}
    attempts = list(latest.values())
    category, action = 'no_usable_main_text', 'Locate a main article PDF through the DOI page or an institutional repository.'
    if record.get('openalex_content_status') == 'waiting_for_free_daily_allowance':
        category, action = 'free_allowance_exhausted', 'Retry free OpenAlex access after the listed reset time.'
    elif record.get('openalex_content_status') == 'free_allowance_not_verified':
        category, action = 'free_allowance_not_verified', 'Retry the OpenAlex free-allowance check before requesting content.'
    elif any(a.get('document_check') == 'pdf_extraction_failed' and a.get('route') == 'openalex_cached_content' for a in attempts):
        category, action = 'cached_pdf_unreadable', 'Obtain a fresh intact publisher or library PDF; the cached copy cannot be read.'
        if record.get('cached_pdf_repair_status') == 'unrecoverable_from_cached_bytes':
            action += ' Offline repair was attempted without recovering any pages.'
    elif any(c.get('status') == 'incomplete_main_candidate_unreviewed' for c in candidates):
        category, action = 'incomplete_main_text_candidate', 'Inspect the locally saved candidate and obtain any missing main-text pages.'
    elif any(c.get('status') == 'supplement_candidate_unreviewed' for c in candidates):
        category, action = 'supplement_without_main_text', 'Obtain the main article; a matching supplement is saved separately.'
    elif any(a.get('access_barrier') == 'sign_in_page' or
             (urlsplit(a.get('final_url', '')).hostname == 'sso.apa.org' and
              '/login' in urlsplit(a.get('final_url', '')).path) for a in attempts):
        category, action = 'publisher_login_redirect', 'Open the DOI through Stanford library/PsycArticles in your regular browser. If access still fails, ask the library to check the licensed platform and IP recognition.'
    elif any(a.get('access_barrier') == 'institutional_access_options' for a in attempts):
        category, action = 'publisher_access_options', 'Open the article through your library; access options alone do not establish whether your institution subscribes.'
    elif any(a.get('access_barrier') == 'bot_challenge' for a in attempts):
        category, action = 'robot_challenge_on_available_routes', 'Try a normal institutional browser or a repository copy; the challenge does not establish subscription status.'
    elif any(a.get('http_status') in {401, 403} for a in attempts):
        category, action = 'access_denied_on_available_routes', 'Open the DOI page in an institutionally authenticated browser and save the main article PDF.'
    elif any(a.get('error') in {'URLError', 'TimeoutError', 'RemoteDisconnected'} for a in attempts):
        category, action = 'network_or_server_failure', 'Retry the DOI or repository link; inspect it in an institutional browser if requests keep failing.'
    supplements = [c.get('url', '') for c in candidates if c.get('status') == 'supplement_candidate_unreviewed']
    return {'failure_category': category, 'recommended_action': action,
            'candidate_count': len(candidates), 'supplement_url': supplements[0] if supplements else ''}


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
              'n_pages', 'n_attempts', 'checked_at', 'openalex_content_status', 'next_retry_at', 'version_note']
    write_csv(PRIVATE / 'fulltext.csv', records, fields)
    public = [dict(r, source_url='' if r['source_url'].startswith('local:') else r['source_url']) for r in records]
    write_csv(ROOT / 'score/access.csv', public, [f for f in fields if f not in {'fulltext_path', 'text_cache'}])
    missing = [dict(r, doi_url='https://doi.org/' + r['doi'], **access_problem(r)) for r in records
               if r['status'] != 'verified_fulltext']
    write_csv(ROOT / 'score/manual_downloads.csv', missing,
              ['article_id', 'journal', 'year', 'title', 'doi', 'doi_url', 'status',
               'openalex_content_status', 'next_retry_at', 'failure_category', 'recommended_action',
               'candidate_count', 'supplement_url'])


def supporting(record, retry=False):
    """Save linked supporting documents for review; a link does not validate its claims."""
    if record.get('supporting_version') == 2 and not retry:
        return record
    if record.get('fulltext_path'):
        record['supporting_links'] += [u for u in document_links(record['fulltext_path'], record.get('source_url', ''))
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
                    'source_url': safe_url(url), 'source_sha256': sha(data), 'role': 'linked_supporting_document_unreviewed'})
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


def openalex_allowance(endpoint='content'):
    """Read the free allowance; never authorize spending from prepaid credits."""
    receipt, data = fetch('https://api.openalex.org/rate-limit', 'application/json', refresh=True)
    try:
        budget = json.loads(data)['rate_limit']
        daily = float(budget['daily_budget_usd'])
        used = float(budget['daily_used_usd'])
        cost = float(budget['endpoint_costs_usd'][endpoint])
        if not all(math.isfinite(value) and value >= 0 for value in (daily, used, cost)) or cost == 0:
            raise ValueError('invalid_budget_values')
    except (ValueError, KeyError, TypeError):
        return None
    save_json(PRIVATE / 'openalex_budget.json', {key: budget.get(key) for key in
        ['daily_budget_usd', 'daily_used_usd', 'daily_remaining_usd', 'resets_at', 'endpoint_costs_usd']})
    # Reserve one cent for concurrent metadata requests, and cap any higher account allowance.
    return {'available': min(1.0, daily) - used >= cost + 0.01,
            'resets_at': budget.get('resets_at', '')}


def openalex_content(articles, works, retry=False):
    """Try PDF then Grobid XML, verifying the free allowance before each request."""
    if not (ACCESS.get('OPENALEX_API_KEY') or ACCESS.get('OPEN_ALEX')):
        print('OpenAlex content skipped: no configured key.')
        return
    records = []
    for index, article in enumerate(articles):
        path = PRIVATE / 'acquisition' / (article['article_id'] + '.json')
        record = json.loads(path.read_text())
        if record['status'] == 'verified_fulltext':
            continue
        urls = works.get(article.get('doi', '').lower(), {}).get('content_urls') or {}
        if not urls:
            continue
        for kind in ('pdf', 'grobid_xml'):
            if not urls.get(kind):
                continue
            budget = openalex_allowance()
            if budget is None:
                record.update(openalex_content_status='free_allowance_not_verified', next_retry_at='')
                save_json(path, record)
                export([])
                print('OpenAlex content stopped: free allowance could not be verified.')
                return
            if not budget['available']:
                for pending in articles[index:]:
                    pending_path = PRIVATE / 'acquisition' / (pending['article_id'] + '.json')
                    pending_record = json.loads(pending_path.read_text())
                    content = works.get(pending.get('doi', '').lower(), {}).get('content_urls')
                    if pending_record['status'] != 'verified_fulltext' and content:
                        pending_record.update(openalex_content_status='waiting_for_free_daily_allowance',
                                              next_retry_at=budget['resets_at'])
                        save_json(pending_path, pending_record)
                export([])
                print('OpenAlex content stopped at the free daily allowance; no prepaid balance used.')
                return
            url = safe_url(urls[kind])
            receipt, data = fetch(url, retry=retry)
            parsed, reason = document(data, article, url)
            record['attempts'].append({**receipt, 'route': 'openalex_cached_content', 'content_format': kind,
                                      'document_check': reason or parsed['identity_check']})
            if parsed:
                retain_document(record, parsed, data, url)
            else:
                retain_candidate(record, data, url, reason)
            record.update(openalex_content_status='retrieved' if parsed else 'attempted_not_usable', next_retry_at='')
            record.update(n_attempts=len(record['attempts']), checked_at=datetime.now(timezone.utc).isoformat())
            save_json(path, record)
            if parsed:
                break
        records.append(record)
        export(records)
        if urls:
            print(f"OpenAlex {article['article_id']}: {record['status']}", flush=True)


def main():
    global UNPAYWALL_EMAIL
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--workers', type=int, default=6)
    parser.add_argument('--retry-failures', action='store_true')
    parser.add_argument('--supporting', action='store_true', help='Also fetch up to four linked supporting sources per article.')
    parser.add_argument('--import-local', type=Path, metavar='DIRECTORY',
                        help='Import missing PDFs named <article_id>.pdf without network access.')
    parser.add_argument('--unpaywall-email', default=UNPAYWALL_EMAIL,
                        help='Contact email for free Unpaywall DOI lookups; never included in public outputs.')
    parser.add_argument('--openalex-content', action='store_true',
                        help='Try cached OA copies while staying inside the verified free daily allowance.')
    args = parser.parse_args()
    UNPAYWALL_EMAIL = args.unpaywall_email
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
            if len(records) % 20 == 0 or len(records) == len(articles):
                export(records)
            ready = sum(r['status'] == 'verified_fulltext' for r in records)
            print(f'Checked {len(records)}/{len(articles)}; verified full text {ready}', flush=True)
    if args.openalex_content:
        openalex_content(articles, works, args.retry_failures)


if __name__ == '__main__':
    main()
