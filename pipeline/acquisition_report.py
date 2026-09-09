"""Join file availability to the geography queue without changing annotations."""
from urllib.parse import quote

from common import ROOT, digest, read_csv, write_csv, write_json
from render import render


def enrich_queue(queue, root=ROOT):
    path = root / 'results/open_access_acquisition.csv'
    records = {r['scopus_id']: r for r in read_csv(path)} if path.exists() else {}
    followup_path = root / 'inputs/fulltext_followups.csv'
    followups = {r['scopus_id']: r for r in read_csv(followup_path)} if followup_path.exists() else {}
    out = []
    for r in queue:
        sid, a = r['scopus_id'], records.get(r['scopus_id'], {})
        folder = root / 'private/fulltext/inbox'
        files = [p for p in [folder / (sid+'.pdf'), *sorted(folder.glob(sid+'__*.pdf'))]
                 if '__abstract' not in p.name and p.is_file() and p.read_bytes()[:1024].lstrip().startswith(b'%PDF-')]
        if a.get('source_sha256') and files and a.get('downloaded_filename'):
            named = folder / a['downloaded_filename']
            if named.exists() and digest(named.read_bytes()) != a['source_sha256']:
                raise ValueError(f'Acquired PDF changed: {sid}')
        url = quote(a.get('open_location_url') or r['article_url'], safe=':/?&=%#;,+@')
        out.append({**r, 'local_pdf_available': str(bool(files)).lower(),
                    'local_filenames': '|'.join(p.name for p in files),
                    'download_status': 'local_pdf_awaiting_review' if files else 'manual_download_needed',
                    'open_access_status': a.get('oa_status', 'not_checked'),
                    'open_access_note': a.get('reason', 'Open availability not yet checked'),
                    'needed_material': followups.get(sid, {}).get('needed_material', 'complete article'),
                    'fulltext_review_note': followups.get(sid, {}).get('note', ''),
                    'manual_download_url': url, 'acquired_from_url': a.get('source_url', '')})
    return out


def write_reports(queue, root=ROOT):
    manual = [r for r in queue if r['local_pdf_available'] != 'true']
    available = [r for r in queue if r['local_pdf_available'] == 'true']
    manual = [{**r, 'manual_position': i, 'manual_batch': (i-1)//10+1} for i, r in enumerate(manual, 1)]
    fields = list(queue[0]) if queue else ['scopus_id']
    write_csv(root / 'results/manual_download_queue.csv', manual, fields+['manual_position','manual_batch'])
    write_csv(root / 'results/downloaded_awaiting_review.csv', available, fields)
    lines = [f"{len(queue)} articles still have unclear sample geography. Local PDFs or supplements are now available for "
             f"{len(available)} of them; {len(manual)} need manual download. Acquisition does not resolve geography: "
             "the current US counts remain unchanged until the texts are reviewed.\n\n",
             "Save each downloaded article under the filename below in `SurveyExperimentRecruitment/private/fulltext/inbox/`. "
             "Save supplements as `<scopus_id>__supplement.pdf`. The first link uses an indexed open location where available; "
             "the DOI link provides institutional access or an alternative route. An unsuccessful automatic download does not "
             "mean that an article is paywalled. Skip unavailable papers and continue.\n\n",
             "The first batches prioritize potential tie differentiation near the top 50; [see the priority method](PRIORITY_DOWNLOADS.html). "
             "A paper reported unavailable is retained at the end for completeness and should be skipped.\n\n"
             "[Manual-download checklist](results/manual_download_queue.csv) · "
             "[Already downloaded; awaiting review](results/downloaded_awaiting_review.csv) · [Dashboard](TOP100.html#downloads)\n\n"]
    batch = None
    for r in manual:
        if r['manual_batch'] != batch:
            batch = r['manual_batch']; lines.append(f'**Batch {batch}**\n\n')
        lines.append(f"{r['manual_position']}. [{r['title']}]({r['manual_download_url']}) · "
                     f"[DOI / publisher]({r['article_url']}). Save as `{r['suggested_filename']}`. "
                     f"Affects: {r['credited_researchers']}. "
                     f"{r.get('manual_retrieval_note', '')}\n\n")
    text = ''.join(lines)
    (root / 'MANUAL_DOWNLOADS.md').write_text(text)
    (root / 'MANUAL_DOWNLOADS.html').write_text(render(text, 'Manual full-text downloads'))
    write_json(root / 'results/fulltext_availability_summary.json', {
        'n_unclear_articles': len(queue), 'n_articles_with_local_pdf': len(available),
        'n_manual_download_needed': len(manual), 'n_manual_batches': (len(manual)+9)//10,
        'n_local_files_for_unclear_articles': sum(len(r['local_filenames'].split('|')) for r in available),
        'geography_labels_changed_by_acquisition': False})
    return manual, available


if __name__ == '__main__':
    write_reports(enrich_queue(read_csv(ROOT / 'results/fulltext_download_queue.csv')))
