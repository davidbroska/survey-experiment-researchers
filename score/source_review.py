"""Navigate one local source and record an independent three-field review."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
from annotate import ROOT, PRIVATE, PROMPT, LABELS, fulltext_prompt
from review import read_rows, index_rows, public_text, validate_evidence, validate_source_quotes


def normalized(value):
    return ' '.join(value.replace('\u00ad', '').split())


def source_pages(record):
    cached = json.loads(Path(record['text_cache']).read_text())
    if cached['source_sha256'] != record['source_sha256']:
        raise ValueError('Extraction does not match source')
    if record['format'].lower() == 'pdf':
        return cached['pages'], 'PDF page'
    text = normalized('\n'.join(cached['pages']))
    return [text[start:start + 8000] for start in range(0, len(text), 8000)], 'text segment (not a PDF page)'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch', required=True)
    parser.add_argument('--instructions', action='store_true')
    parser.add_argument('--pages', help='Inclusive page/segment range, for example 3:8')
    parser.add_argument('--reading-order', action='store_true', help='For PDF pages, use text reading order instead of preserved column layout')
    parser.add_argument('--find', help='Case-insensitive regular expression for source navigation')
    parser.add_argument('--offset', type=int, default=0)
    parser.add_argument('--save', help='Path to a JSON response containing annotation, evidence, reasoning')
    parser.add_argument('--links', action='store_true', help='Show known supporting links; these are not inspection receipts')
    parser.add_argument('--support-receipt', help='JSON with source URL, status, sections and optional local_file after inspecting a supporting source')
    args = parser.parse_args()
    folder = PRIVATE / 'annotation_batches'
    ids = json.loads((folder / (args.batch + '.json')).read_text())
    destination = folder / (args.batch + '.csv')
    completed = index_rows(read_rows(destination))
    pending = [key for key in ids if key not in completed]
    if not pending:
        print(f'Complete: {len(ids)} articles recorded.')
        return
    key = pending[0]
    article = index_rows(read_rows(PRIVATE / 'articles.csv'))[key]
    access = index_rows(read_rows(PRIVATE / 'fulltext.csv'))[key]
    pages, unit = source_pages(access)
    prompt, _ = fulltext_prompt(article, [])
    if args.instructions:
        print(prompt)
        return
    log_path = folder / (args.batch + '_access.jsonl')
    if args.links:
        path = PRIVATE / 'acquisition' / (key + '.json')
        record = json.loads(path.read_text()) if path.exists() else {}
        print(public_text(json.dumps({'supporting_links_not_yet_inspected': record.get('supporting_links', [])})))
        return
    if args.support_receipt:
        receipt = json.loads(Path(args.support_receipt).read_text())
        if receipt.get('status') not in ['inspected', 'access_failed'] or not receipt.get('source', '').startswith(('http://', 'https://')) or not receipt.get('sections'):
            raise ValueError('Receipt needs source URL, status (inspected/access_failed) and sections or failure details')
        receipt['source'] = public_text(receipt['source'])
        if receipt.get('local_file'):
            receipt['source_sha256'] = hashlib.sha256(Path(receipt['local_file']).read_bytes()).hexdigest()
        receipt.update(article_id=key, read_at=datetime.now(timezone.utc).isoformat())
        with log_path.open('a') as handle:
            handle.write(json.dumps(receipt) + '\n')
        print('Supporting-source access receipt saved.')
        return
    if args.save:
        response = json.loads(Path(args.save).read_text())
        if set(response) != {'annotation', 'evidence', 'reasoning'} or response['annotation'] not in LABELS:
            raise ValueError('Expected annotation, evidence and reasoning only')
        if not response['reasoning'] or not response['evidence']:
            raise ValueError('Evidence and reasoning are required')
        validate_evidence(response['evidence'])
        validate_source_quotes(response['evidence'], access)
        reads = [json.loads(line) for line in log_path.read_text().splitlines()] if log_path.exists() else []
        inspected = {row.get('source') for row in reads if row['article_id'] == key and row.get('status') == 'inspected'}
        if any(item['source'] != 'main' and item['source'] not in inspected for item in response['evidence']):
            raise ValueError('Record supporting-source inspection before citing its evidence')
        viewed = sorted({number for row in reads if row['article_id'] == key for number in row.get('pages', [])})
        if not viewed:
            raise ValueError('Read actual source pages before saving')
        row = {'article_id': key, 'annotation': response['annotation'],
               'evidence': json.dumps(response['evidence'], ensure_ascii=False),
               'reasoning': response['reasoning'], 'reviewer': args.batch,
               'model': 'Codex session agent (GPT-6 family)',
               'reviewed_at': datetime.now(timezone.utc).isoformat(),
               'prompt_sha256': hashlib.sha256(PROMPT.read_bytes()).hexdigest(),
               'instructions_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
               'source_sha256': access['source_sha256'], 'source_format': access['format'],
               'pages_or_segments_read': ','.join(map(str, viewed)),
               'human_verified': 'false'}
        with destination.open('a', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(row))
            if handle.tell() == 0:
                writer.writeheader()
            writer.writerow(row)
        print('Saved review. Run the wrapper again for the next article.')
        return
    if args.pages:
        bounds = [int(value) for value in args.pages.split(':')]
        start, end = bounds[0], bounds[-1]
        if not 1 <= start <= end <= len(pages):
            raise ValueError(f'Range must lie within 1:{len(pages)}')
        displayed = pages[start - 1:end]
        if args.reading_order:
            if access['format'].lower() != 'pdf':
                raise ValueError('Reading-order option is for PDFs only')
            text = subprocess.check_output(['pdftotext', '-f', str(start), '-l', str(end), access['fulltext_path'], '-'], text=True, stderr=subprocess.PIPE)
            displayed = text.split('\f')[:end - start + 1]
            if len(displayed) != end - start + 1:
                raise ValueError('Unexpected PDF page count')
        with log_path.open('a') as handle:
            handle.write(json.dumps({'article_id': key, 'pages': list(range(start, end + 1)),
                                     'reading_order': args.reading_order,
                                     'read_at': datetime.now(timezone.utc).isoformat()}) + '\n')
        print(json.dumps({'journal_title': article['journal'], 'title': article['title'], 'unit': unit,
                          'pages': [{'number': start + index, 'text': re.sub(r'[ \t]+', ' ', page).strip()}
                                    for index, page in enumerate(displayed)]}, ensure_ascii=False))
        return
    if args.find:
        matches = []
        for number, page in enumerate(pages, 1):
            for match in re.finditer(args.find, page, re.I):
                matches.append({'page_or_segment': number,
                                'context': normalized(page[max(0,match.start()-180):match.end()+350])})
        print(json.dumps({'matches_total': len(matches), 'offset': args.offset,
                          'matches': matches[args.offset:args.offset + 35]}, ensure_ascii=False))
        return
    print(json.dumps({'journal_title': article['journal'], 'title': article['title'], 'source_format': access['format'],
                      'unit': unit, 'n_pages_or_segments': len(pages), 'version_note': access.get('version_note',''),
                      'guide': [{'number': number, 'characters': len(page), 'opening': normalized(page)[:140]}
                                for number, page in enumerate(pages, 1)]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
