"""Stage an allowlisted GitHub Pages site; never publish or copy private data."""
from html.parser import HTMLParser
from pathlib import Path
import shutil
from urllib.parse import unquote, urlsplit
import zipfile

from common import ROOT, digest, write_json

REPORTS = ('EXECUTIVE_SUMMARY', 'SUPPORTING_INFORMATION', 'QUERY_REPORT',
           'GEOGRAPHY_REPORT', 'FULLTEXT_REVIEW', 'YEAR_WINDOW_COMPARISON', 'MANUAL_DOWNLOADS', 'PRIORITY_DOWNLOADS', 'QUERY_REVISION')
CSV_FILES = ('top100_enriched', 'top100_provisional', 'top100_article_annotations',
             'top100_author_article_links', 'top100_cutoff_ties', 'fulltext_download_queue',
             'year_window_author_comparison', 'year_window_tie_comparison',
             'manual_download_queue', 'downloaded_awaiting_review', 'top50_priority_downloads')


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, tag, attrs):
        self.targets.extend(v for k, v in attrs if k in ('href', 'src') and v)


def check_links(site):
    checked = 0
    for path in sorted(site.rglob('*.html')):
        links = Links()
        links.feed(path.read_text())
        for target in links.targets:
            url = urlsplit(target)
            if url.scheme or url.netloc or not url.path:
                continue
            dest = (path.parent / unquote(url.path)).resolve()
            if not dest.is_relative_to(site.resolve()) or not dest.is_file():
                raise ValueError(f'Broken or escaping site link: {path.name}: {target}')
            checked += 1
    return checked


def build():
    site = ROOT / 'site'
    site.mkdir(exist_ok=True)
    files = ['TOP100.html', 'TOP40.html', 'queries/recommended.txt']
    files += [f'{r}.{ext}' for r in REPORTS for ext in ('md', 'html')]
    files += [f'results/{r}.csv' for r in CSV_FILES]
    files += [f'queries/revision_2026_09_10/{name}.txt' for name in ('previous', 'revised', 'additional_embedded_variants')]
    files += [f'results/query_revision_2026_09_10/{name}.csv' for name in
              ('retrieval_comparison', 'sequential_changes', 'changed_article_metadata', 'local_verification_by_change', 'field_checks')]
    for name in files:
        dest = site / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, dest)
    shutil.copy2(ROOT / 'TOP100.html', site / 'index.html')
    (site / '.nojekyll').write_text('')
    (site / 'README.md').write_text('Survey-experiment researcher dashboard, publications 2010–2026.\n\n'
                                  'Open [the dashboard](index.html) or [the selection method and query](SUPPORTING_INFORMATION.html). '
                                  'Counts represent first/last-author candidate articles. US labels combine explicit and inferred '
                                  'evidence and await independent validation. Source PDFs, full abstracts, API credentials, and '
                                  'Scopus caches are not included.\n')
    expected = set(files) | {'index.html', '.nojekyll', 'README.md'}
    actual = {str(p.relative_to(site)) for p in site.rglob('*') if p.is_file()}
    # Unexpected files require deliberate handling rather than being silently published or deleted.
    if actual != expected:
        raise ValueError(f'Unexpected site contents: {sorted(actual ^ expected)}')
    checked = check_links(site)
    manifest = [{'path': name, 'sha256': digest((site / name).read_bytes())} for name in sorted(expected)]
    write_json(ROOT / 'results/site_manifest.json', {'entry': 'index.html', 'files': manifest,
               'local_links_checked': checked, 'private_files_included': False, 'published': False})
    with zipfile.ZipFile(ROOT / 'github-pages-site.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(expected):
            info = zipfile.ZipInfo(name, (2026, 9, 9, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, (site / name).read_bytes())
    print(f'Staged {len(manifest)} files; checked {checked} local links. No publication performed.')


if __name__ == '__main__':
    build()
