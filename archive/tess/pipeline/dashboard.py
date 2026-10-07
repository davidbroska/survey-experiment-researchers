"""Reproduce the researcher dashboard from frozen metadata and curated labels.

The pool is selected by first/last-author article volume BEFORE geography review.
No automatic geographic classification, remote service, or live API is used here.
"""
from collections import Counter, defaultdict
import json
import query
from urllib.parse import quote

from common import ROOT, digest, read_csv, write_csv, write_json
from enrich import LABELS, unique_index


def metadata_digest(article):
    return digest(json.dumps({k: article.get(k, '') for k in
                              ('title', 'abstract', 'keywords', 'indexed_keywords')},
                             sort_keys=True, ensure_ascii=False))


def select_pool(ranking, size, include_ties=False):
    if size < 1 or size > len(ranking):
        raise ValueError('Pool size must be within the available ranking')
    unique_index(ranking, 'authid')
    ordered = sorted(ranking, key=lambda r: (-int(r['n_articles']), int(r['authid'])))
    cutoff = int(ordered[size - 1]['n_articles'])
    pool = [r for r in ordered if int(r['n_articles']) >= cutoff] if include_ties else ordered[:size]
    selected = {r['authid'] for r in pool}
    ties = [{**r, 'in_dashboard_pool': str(r['authid'] in selected).lower()}
            for r in ordered if int(r['n_articles']) == cutoff]
    return pool, ties


def article_url(article):
    if article['doi']:
        return 'https://doi.org/' + quote(article['doi'], safe='/:;.-_')
    return 'https://www.scopus.com/record/display.uri?eid=' + quote(article['eid'])


def join(pool, affiliations, annotations, articles):
    people = unique_index(affiliations, 'authid')
    codes = unique_index(annotations, 'scopus_id')
    raw = unique_index(articles, 'scopus_id')
    unique_index(pool, 'authid')
    required = {sid for r in pool for sid in r['article_ids'].split('|')}
    if set(codes) != required or set(people) != {r['authid'] for r in pool}:
        raise ValueError('Affiliations and annotations must exactly cover the selected pool')
    for sid in sorted(required):
        c, a = codes[sid], raw[sid]
        if c['sample_us_label'] not in LABELS:
            raise ValueError(f'Invalid geography label: {sid}')
        if c['metadata_sha256'] != metadata_digest(a):
            raise ValueError(f'Metadata changed since annotation: {sid}')
        field = c['evidence_field']
        if field not in ('title', 'abstract', 'keywords', 'indexed_keywords'):
            raise ValueError(f'Invalid evidence field: {sid}')
        evidence = c['evidence_quote']
        if evidence not in a.get(field, '') or (c['sample_us_label'] != 'unclear' and not evidence):
            raise ValueError(f'Unverifiable evidence: {sid}')
        if not all(c.get(k) for k in ('rationale', 'reviewer', 'reviewer_type', 'review_date')):
            raise ValueError(f'Missing review provenance: {sid}')
        if c['us_and_non_us_samples_reported'] == 'true' and not c['sample_us_label'].startswith('us_'):
            raise ValueError(f'Mixed-country flag requires a US label: {sid}')
    authors, links = [], []
    for r in pool:
        aid = r['authid']
        p = people[aid]
        if not all(p.get(k) for k in ('full_name', 'institution', 'department', 'country', 'source_url', 'verified_on')):
            raise ValueError(f'Incomplete affiliation: {aid}')
        ids = r['article_ids'].split('|')
        if len(ids) != len(set(ids)) or len(ids) != int(r['n_articles']):
            raise ValueError(f'Article count mismatch: {aid}')
        first = last = sole = 0
        for sid in ids:
            a = raw[sid]
            f, l = aid == a['first_authid'], aid == a['last_authid']
            if not (f or l) or a['byline_complete'] != 'true':
                raise ValueError(f'Invalid authorship credit: {aid}, {sid}')
            first += f
            last += l
            sole += f and l
            links.append({'authid': aid, 'full_name': p['full_name'], 'scopus_id': sid,
                          'authorship_position': 'sole' if f and l else 'first' if f else 'last',
                          'sample_us_label': codes[sid]['sample_us_label']})
        if (first, last) != (int(r['n_first']), int(r['n_last'])) or first + last - sole != len(ids):
            raise ValueError(f'First/last/sole count mismatch: {aid}')
        counts = Counter(codes[sid]['sample_us_label'] for sid in ids)
        authors.append({**r, **p, 'n_sole': sole,
                        **{'n_' + label + '_articles': counts[label] for label in LABELS},
                        'n_us_articles': counts['us_explicit'] + counts['us_inferred'],
                        'n_mixed_country_us_articles': sum(codes[sid]['us_and_non_us_samples_reported'] == 'true' for sid in ids)})
    for r in authors:
        r['us_count_rank_within_pool'] = 1 + sum(x['n_us_articles'] > r['n_us_articles'] for x in authors)
        # A resolution scenario, not a statistical confidence bound: existing labels may also change.
        r['us_if_all_unclear_resolve_us'] = r['n_us_articles'] + r['n_unclear_articles']
    article_links = defaultdict(list)
    for link in links:
        article_links[link['scopus_id']].append(link)
    annotated = []
    for sid in sorted(required, key=int):
        a, c = raw[sid], codes[sid]
        aa = article_links[sid]
        annotated.append({**{k: a[k] for k in ('scopus_id', 'doi', 'year', 'journal', 'title')},
                          **c, 'article_url': article_url(a),
                          'credited_authids': '|'.join(x['authid'] for x in aa),
                          'credited_researchers': '; '.join(x['full_name'] for x in aa),
                          'n_credited_researchers': len(aa)})
    return authors, annotated, links


def make_queue(authors, annotated, batch_size):
    if batch_size < 1:
        raise ValueError('Batch size must be positive')
    lookup = unique_index(authors, 'authid')
    pending = [a for a in annotated if a['sample_us_label'] == 'unclear']
    def priority(a):
        people = [lookup[aid] for aid in a['credited_authids'].split('|')]
        return (-len(people), -max(int(p['n_articles']) for p in people),
                -max(int(p['n_us_articles']) for p in people), int(a['scopus_id']))
    queue = []
    for i, a in enumerate(sorted(pending, key=priority), 1):
        queue.append({'queue_position': i, 'batch': (i - 1) // batch_size + 1,
                      'scopus_id': a['scopus_id'], 'suggested_filename': a['scopus_id'] + '.pdf',
                      **{k: a[k] for k in ('title', 'year', 'journal', 'doi', 'article_url',
                                          'credited_authids', 'credited_researchers', 'n_credited_researchers', 'rationale')},
                      'question': 'Does at least one experimental sample include US-based participants?',
                      'requested_evidence': 'Methods/sampling page, participant country, and which experiment it applies to.'})
    return queue


def build():
    config = json.loads((ROOT / 'inputs/dashboard_config.json').read_text())
    paths = {'ranking': ROOT / 'results/ranking_provisional.csv',
             'affiliations': ROOT / 'inputs/researcher_affiliations.csv',
             'annotations': ROOT / 'inputs/article_geography.csv',
             'articles': ROOT / 'private/articles.csv',
             'original_top40_annotations': ROOT / 'inputs/top40_us_annotations.csv',
             'config': ROOT / 'inputs/dashboard_config.json'}
    pool, ties = select_pool(read_csv(paths['ranking']), config['pool_size'], config['include_cutoff_ties'])
    # Curated inputs retain earlier cohorts; validate exact coverage after selecting this pool.
    aids = {r['authid'] for r in pool}
    sids = {sid for r in pool for sid in r['article_ids'].split('|')}
    affiliations = [r for r in read_csv(paths['affiliations']) if r['authid'] in aids]
    annotations = [r for r in read_csv(paths['annotations']) if r['scopus_id'] in sids]
    authors, annotated, links = join(pool, affiliations, annotations, read_csv(paths['articles']))
    # Reviewed full-text overrides are optional, validated separately, and never overwrite metadata labels.
    overrides_path = ROOT / 'inputs/fulltext_reviews.csv'
    if overrides_path.exists() and read_csv(overrides_path):
        from fulltext import apply_reviews
        authors, annotated, links = apply_reviews(authors, annotated, links,
                                                [r for r in read_csv(overrides_path) if r['scopus_id'] in sids])
        paths['fulltext_reviews'] = overrides_path
    queue = make_queue(authors, annotated, config['download_batch_size'])
    from acquisition_report import enrich_queue, write_reports as acquisition_reports
    queue = enrich_queue(queue)
    from review_priority import prioritize
    queue = prioritize(authors, queue)
    manual_queue, available_queue = acquisition_reports(queue)
    for key, relative in [('open_access_acquisition', 'results/open_access_acquisition.csv'),
                          ('open_access_sources', 'inputs/open_access_sources.csv'),
                          ('manual_download_status', 'inputs/manual_download_status.csv'),
                          ('fulltext_followups', 'inputs/fulltext_followups.csv')]:
        if (ROOT / relative).exists():
            paths[key] = ROOT / relative
    local_files = sorted({name for r in available_queue for name in r['local_filenames'].split('|')})
    counts = Counter(a['sample_us_label'] for a in annotated)
    original40 = {r['scopus_id'] for r in read_csv(paths['original_top40_annotations'])}
    summary = {'n_authors': len(authors), 'n_unique_articles': len(annotated),
               'n_author_article_credits': len(links), 'article_counts': {k: counts[k] for k in LABELS},
               'n_us_articles': counts['us_explicit'] + counts['us_inferred'],
               'n_unclear_articles': counts['unclear'],
               'n_new_articles_beyond_top40': sum(a['scopus_id'] not in original40 for a in annotated),
               'n_fulltext_reviewed_articles': sum(a.get('source_review') == 'full_text' for a in annotated),
               'n_us_author_article_credits': sum(r['n_us_articles'] for r in authors),
               'n_mixed_country_us_articles': sum(a['us_and_non_us_samples_reported'] == 'true' for a in annotated),
               'cutoff_article_count': min(int(r['n_articles']) for r in authors),
               'n_authors_tied_at_cutoff': len(ties),
               'n_cutoff_tied_authors_outside_pool': sum(t['in_dashboard_pool'] == 'false' for t in ties),
               'n_download_batches': (len(manual_queue) + config['download_batch_size'] - 1) // config['download_batch_size'],
               'n_local_pdfs_awaiting_review': len(available_queue),
               'n_manual_download_needed': len(manual_queue),
               'local_pdf_sha256': {name: digest((ROOT / 'private/fulltext/inbox' / name).read_bytes())
                                    for name in local_files},
               'annotation_date': max(a['review_date'] for a in annotated),
               'affiliation_date_min': min(a['verified_on'] for a in authors),
               'affiliation_date_max': max(a['verified_on'] for a in authors),
               'publication_start_year': query.START_YEAR,
               'publication_end_year': query.END_YEAR,
               'human_validated_articles': sum(a['human_validated'] == 'true' for a in annotated),
               'institution_country_counts': dict(sorted(Counter(r['country'] for r in authors).items())),
               'affiliation_verification_counts': dict(sorted(Counter(r['verification_status'] for r in authors).items())),
               'first_last_credit_verified': True,
               'scope': 'US-sample ranking within a pool selected by total first/last-author article count; not a global top 100 by US samples.',
               'input_sha256': {k: digest(p.read_bytes()) for k, p in paths.items()}}
    for name, rows in [('top100_provisional', pool), ('top100_enriched', authors),
                       ('top100_article_annotations', annotated), ('top100_author_article_links', links),
                       ('top100_cutoff_ties', ties), ('fulltext_download_queue', queue)]:
        write_csv(ROOT / f'results/{name}.csv', rows)
    write_json(ROOT / 'results/top100_enrichment_summary.json', summary)
    write_reports(authors, summary, queue)
    payload = {'authors': authors, 'articles': annotated,
               'queue': [{**r, 'batch': r['manual_batch']} for r in manual_queue],
               'downloaded_pending': available_queue, 'summary': summary}
    from coauthor_summary import content
    coauthor = content(summary, json.loads((ROOT / 'results/flow_counts.json').read_text()),
                       json.loads((ROOT / 'results/frame_manifest.json').read_text()))
    payload['query'] = coauthor['query']
    template = (ROOT / 'pipeline/dashboard_template.html').read_text()
    css = (ROOT / 'pipeline/dashboard.css').read_text()
    js = (ROOT / 'pipeline/dashboard.js').read_text()
    data = json.dumps(payload, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    output = template.replace('/* INLINE_CSS */', css).replace('/* INLINE_JS */', js).replace('JSON_PAYLOAD', data).replace('SUMMARY_CONTENT', coauthor['html'])
    (ROOT / 'TOP100.html').write_text(output, encoding='utf-8')
    # Preserve the user's existing entry point; both files contain the same current dashboard.
    (ROOT / 'TOP40.html').write_text(output, encoding='utf-8')
    print(json.dumps(summary, indent=2))
    return summary


def write_reports(authors, s, queue):
    c = s['article_counts']
    method = (f"We selected {s['n_authors']} researchers by their number of distinct first/last-author survey-experiment candidate articles, "
              f"then reviewed the union of their {s['n_unique_articles']} articles using titles, abstracts, and available keywords. "
              f"The US-sample count combines {c['us_explicit']} articles with explicit evidence and {c['us_inferred']} with contextual inference "
              f"({s['n_us_articles']} articles). {s['n_fulltext_reviewed_articles']} articles have subsequent reviewed full-text evidence; "
              f"where supplied, full-text labels supersede metadata labels and retain file hashes and page citations. "
              f"Another {c['non_us']} have non-US study evidence, {c['unclear']} have unclear geography, "
              f"and {c['not_applicable']} identify no applicable original experimental sample. "
              "A US political topic supports contextual inference only when the study plausibly samples that public; "
              "US policy evaluated by explicitly foreign respondents does not qualify. Generic topics, panel vendors, author affiliations, "
              "and an unspecified national or international sample do not locate participants. Non-US means no US experimental sample "
              "was identified in the metadata; it does not rule out a US sample elsewhere in the full text. "
              "Indexed keywords were unavailable in the retrieved Search COMPLETE records; author keywords were reviewed where supplied. "
              "Each label retains its evidence field, verbatim span, rationale, reviewer, date, and metadata hash. "
              "These are AI-assisted annotations awaiting independent human validation.\n\n"
              "Counts represent articles with evidence of at least one US experimental sample, not the number of experiments, "
              "independent samples, or datasets. Mixed-country articles count once as US-associated. "
              "Shared articles count once per credited researcher but once in article-level totals. "
              "The primary count is first + last − sole-authored articles; both first and last include sole authors. "
              "Geographic review does not change the frozen candidate count. Articles without original experimental samples "
              "remain visible in that provisional count and require eligibility screening. Author position is a proxy for PI involvement, "
              "weakened by alphabetical bylines and disciplinary conventions. Roles are provided separately.\n\n"
              f"The {s['cutoff_article_count']}-article cutoff is shared by {s['n_authors_tied_at_cutoff']} researchers, "
              f"of whom {s['n_cutoff_tied_authors_outside_pool']} fall outside the displayed pool. Numeric Scopus author ID determines "
              "pool membership within this tie, as in the frozen ranking. US-count sorting is therefore conditional on this pool; "
              "it is not a global ranking of all researchers by US samples. Identical counts share competition ranks. "
              "Secondary sorting stabilizes display and does not break substantive ties. The 'US if all unclear resolve US' "
              "field is a sensitivity scenario, not a confidence bound: existing inferred and non-US labels can also change after review.\n\n"
              "Institution, department or unit, country, and role were checked against primary institutional or researcher-maintained sources "
              f"between {s['affiliation_date_min']} and {s['affiliation_date_max']}. Country denotes the work institution or campus, not nationality or sample location. "
              "Dated sources and role disagreements are flagged in the profile notes. Study-level screening must still establish "
              "original fielding, parser compatibility, and access to response data and treatment materials.\n")
    (ROOT / 'GEOGRAPHY_REPORT.md').write_text(method + '\n[Sortable dashboard](TOP100.html) · [Researcher data](results/top100_enriched.csv) · '
                                            '[Article annotations](results/top100_article_annotations.csv) · [Download queue](FULLTEXT_REVIEW.md)\n')
    (ROOT / 'results/geography_methods_paragraph.txt').write_text(method.split('\n\n')[0] + '\n')
    lines = [f"{len(queue)} distinct articles need full-text confirmation of sample geography. Each paper is listed once, "
             "with all affected researchers. Priority is: number of affected researchers, highest total article count, "
             "highest current US count, then numeric Scopus ID. This prioritizes review impact; it does not predict whether the sample is American.\n\n",
             f"Local PDFs are available for {s['n_local_pdfs_awaiting_review']} of these articles; "
             f"{s['n_manual_download_needed']} still need manual retrieval. "
             "Use the [remaining manual-download list](MANUAL_DOWNLOADS.html) or the dashboard's Full-text downloads tab "
             "for batches that omit files already acquired. The complete review inventory below retains its original batch numbers; "
             "these differ from the remaining download batches. Downloading a file does not change its geography label.\n\n",
             "Open a paper's DOI or Scopus link through your institutional access, download the PDF, and save it under the suggested filename in "
             "`private/fulltext/inbox/`. Uploads are unnecessary when the file is in this shared folder. You can also save the methods or supplement "
             "as `<scopus_id>__supplement.pdf`. If a paper is unavailable, skip it and continue; the queue retains it. "
             "The dashboard has ten-paper batches, a checklist export, and local download checkboxes. Those checkboxes track your browser only; "
             "they do not change annotations or claim a PDF is present.\n\n",
             "After a batch is saved, run `python3 pipeline/fulltext.py` to inventory files and extract text for review. "
             "Text extraction uses `pdftotext` if installed, otherwise the optional `pypdf` package; a missing extractor leaves the file marked for review. "
             "No file is uploaded or sent elsewhere. Review the methods for participant location and which experiment it describes; "
             "a US address or a US treatment topic alone is insufficient. Record decisions, PDF filename, page, and a short evidence span in "
             "`inputs/fulltext_reviews.csv`, then run `python3 pipeline/run.py dashboard`. Validated full-text labels update every credited author. "
             "The original metadata labels remain preserved.\n\n"]
    current = None
    for r in sorted(queue, key=lambda r: int(r['queue_position'])):
        if r['batch'] != current:
            current = r['batch']; lines.append(f"\n**Batch {current}**\n\n")
        availability = ('Local file available; awaiting review. ' if r['local_pdf_available'] == 'true'
                        else f"Save as `{r['suggested_filename']}`. ")
        lines.append(f"{r['queue_position']}. [{r['title']}]({r['article_url']}) ({r['year']}). "
                     f"{availability}Affects: {r['credited_researchers']}.\n\n")
    (ROOT / 'FULLTEXT_REVIEW.md').write_text(''.join(lines), encoding='utf-8')
    from render import render
    for name in ('GEOGRAPHY_REPORT', 'FULLTEXT_REVIEW'):
        (ROOT / f'{name}.html').write_text(render((ROOT / f'{name}.md').read_text(), name.replace('_', ' ').title()))


if __name__ == '__main__':
    build()
