"""Build the private, fixed-sample SCORE workbook without changing assessments.

Run: python3 score/workbook.py
Requires openpyxl; writes private/score/SCORE_validation_620.xlsx.
"""
import hashlib
from collections import Counter
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter

from evaluate import index_rows, read_rows, validate_reviews

ROOT = Path(__file__).resolve().parent.parent
PRIVATE = ROOT / 'private/score'
CRITERIA = 'Frozen 2026-10-07 pilot: original collection rules + primary-survey definition'
# Keys, visible headers, definitions, and display widths follow the workbook order.
COLUMNS = [
    ('article_id', 'Article ID', 'Stable Scopus ID, or a Crossref-derived ID for the two World Politics records.', 18),
    ('journal', 'Journal', 'SCORE journal name; rows are alphabetized by journal.', 33),
    ('year', 'Year', 'Publication year; ordered 2025 down to 2016 within each journal.', 9),
    ('title', 'Article title', 'Complete bibliographic article title.', 62),
    ('doi', 'DOI', 'Article DOI; click to open its publisher landing page.', 30),
    ('authors', 'Authors', 'Complete author list supplied by the bibliographic source.', 45),
    ('available', 'Verified local full text', 'YES only if the acquisition record is verified and its local document exists with the recorded SHA-256.', 18),
    ('format', 'Full-text format', 'PDF or XML for verified local main text; blank when unavailable.', 15),
    ('a_version_note', 'Available source version / caveat', 'Explicit manuscript/version notes recorded from the available source. Version not separately recorded means no version assessment was saved; availability does not establish equivalence to the final published article.', 60),
    ('local_file', 'Open local full text', 'Local main-document path and hyperlink; works on the research computer.', 45),
    ('basis', 'Assessment basis', 'Full-text review; Metadata only; or Metadata only — full text awaiting review. Downloading a file never establishes review.', 38),
    ('collection', 'Collection — best available', 'Completed source-review label when available; otherwise frozen original metadata label. Missing full text never becomes NO.', 21),
    ('experiment', 'Experiment — best available', 'Eligible researcher-imposed variation, using the same assessment source as collection.', 22),
    ('survey', 'Survey — best available', 'Eligible primary questionnaire survey, including survey experiments and diary surveys; incidental scales do not qualify.', 21),
    ('human_verified', 'Best assessment human verified', 'TRUE only when the selected source review explicitly records human verification; AI assessments are FALSE.', 21),
    ('criteria', 'Assessment criteria', 'Frozen pilot rules. Later policy proposals and untested revisions have not been applied retrospectively.', 45),
    ('m_collection', 'Metadata collection', 'Frozen original assessment using the fields recorded in Metadata input fields; retained even when source review differs.', 20),
    ('m_experiment', 'Metadata experiment', 'Frozen original eligible-experiment assessment.', 20),
    ('m_survey', 'Metadata survey', 'Frozen original primary-survey assessment under the user’s survey definition.', 20),
    ('m_evidence', 'Metadata evidence', 'Short exact excerpts from the supplied bibliographic fields; no full-text evidence was available to this assessment.', 55),
    ('m_rationale', 'Metadata rationale', 'Explanation saved with the frozen metadata decision.', 60),
    ('m_other_methods', 'Metadata other methods', 'Other qualifying collection methods named in the frozen metadata assessment.', 28),
    ('m_software', 'Metadata software', 'Software names explicitly associated with the study in the supplied metadata.', 25),
    ('m_recruitment_providers', 'Metadata recruitment providers', 'Recruitment or panel providers explicitly named in the supplied metadata.', 28),
    ('m_team_data_reuse', 'Metadata earlier team data', 'Original assessment of explicit reuse of the team’s earlier data; not a flag for retained local articles.', 35),
    ('m_prompt_version', 'Metadata prompt version', 'Version stored in the frozen original predictions, including the primary-survey override.', 35),
    ('m_reviewer', 'Metadata reviewer', 'Session reviewer identifier saved with the metadata decision.', 26),
    ('m_prediction_time', 'Metadata decision time', 'Timestamp saved with the frozen metadata decision; Not recorded means no timestamp was saved.', 27),
    ('m_input_fields', 'Metadata input fields', 'Actual recorded input fields; Not recorded means the reviewer did not save this audit field. Bibliographic columns do not establish what the reviewer used.', 38),
    ('m_authors_supplied', 'Metadata authors supplied', 'Recorded author-input flag; Not recorded means unknown, not FALSE. Availability does not imply author identity was used to infer collection.', 24),
    ('r_collection', 'Full-text collection', 'Completed source-based reference label; blank means no completed review, not NO.', 20),
    ('r_experiment', 'Full-text experiment', 'Completed source-based eligible-experiment label; blank if unreviewed.', 20),
    ('r_survey', 'Full-text survey', 'Completed source-based primary-survey label; blank if unreviewed.', 20),
    ('r_evidence_excerpt', 'Full-text evidence', 'Short exact excerpt supporting the reference assessment.', 55),
    ('r_evidence_section', 'Evidence location', 'Methods section, page numbers, or other locations inspected by the source reviewer.', 50),
    ('r_rationale', 'Full-text rationale', 'Source-review explanation, including collection provenance and relevant study components.', 65),
    ('r_other_methods', 'Full-text other methods', 'Other collection methods identified through source review.', 28),
    ('r_software', 'Full-text software', 'Software recorded from inspected study sources.', 26),
    ('r_recruitment_providers', 'Full-text recruitment providers', 'Recruitment providers recorded from inspected study sources.', 28),
    ('r_team_data_reuse', 'Full-text earlier team data', 'Whether the reviewed study uses data previously collected or commissioned by the team, with supporting detail.', 45),
    ('r_confidence', 'Full-text reviewer confidence', 'Reviewer’s stated confidence; not a calibrated probability.', 22),
    ('r_reviewer', 'Full-text reviewer', 'Identifier of the primary source reviewer.', 30),
    ('r_review_date', 'Full-text review date', 'Date of the completed source assessment.', 19),
    ('r_review_status', 'Full-text review status', 'Stored review status; source reviews remain AI assessments until human verification.', 30),
    ('r_human_verified', 'Full-text human verified', 'Stored human-verification flag; blank when there is no reference review.', 22),
    ('r_source_url', 'Reviewed source URL', 'Online location recorded for the reviewed main source.', 45),
    ('r_source_path', 'Reviewed source cache', 'Local extracted-text or document path used for the review; click to open.', 45),
    ('r_source_sha256', 'Reviewed document SHA-256', 'Fingerprint of the source document, not of the extracted-text cache.', 40),
    ('r_supporting_resource_url', 'Supporting sources URL', 'Additional repository, supplement, or project evidence recorded by the reviewer.', 45),
    ('r_supporting_resource_status', 'Supporting sources checked', 'What supporting sources were actually inspected and what remains unresolved.', 60),
    ('a_status', 'Retrieval status', 'Latest acquisition status, independent of eligibility or review completion.', 28),
    ('a_checked_at', 'Retrieval checked at', 'Timestamp of the latest saved acquisition check.', 27),
    ('a_identity_check', 'Retrieval identity check', 'How the acquisition process matched the document to the selected article.', 24),
    ('a_source_url', 'Acquired source URL', 'Online location of the latest verified main text or recorded acquisition result.', 45),
    ('a_source_sha256', 'Acquired document SHA-256', 'Fingerprint checked against the current local main document.', 40),
    ('a_text_cache', 'Current extracted text', 'Local cache for searching the current main text; a cache does not mean it was reviewed.', 45),
    ('split', 'Frozen evaluation split', 'Historical development/holdout assignment from the first pilot; not an untouched test for the later proposed prompt. New downloads do not change the assignment.', 24),
    ('metadata_source', 'Bibliographic source', 'Scopus or Crossref. Bibliographic provenance is independent of full-text retrieval.', 23),
    ('source_date', 'Bibliographic retrieval date', 'Date recorded for the bibliographic response.', 27),
    ('source_url', 'Bibliographic source URL', 'DOI landing page or source URL from the metadata record.', 45),
    ('n_authors', 'Author count', 'Number of authors supplied by the bibliographic source.', 14),
    ('abstract', 'Abstract — screening input', 'Complete supplied abstract; blank means unavailable. Private licensed metadata.', 90),
    ('keywords', 'Keywords — screening input', 'Complete supplied keywords; blank means unavailable. Private licensed metadata.', 65),
]


LEVELS = {
    **{key: 'YES / NO / UNCLEAR' for key in ['collection', 'experiment', 'survey',
        'm_collection', 'm_experiment', 'm_survey', 'm_team_data_reuse',
        'r_collection', 'r_experiment', 'r_survey']},
    'available': 'YES / NO', 'format': 'PDF / XML', 'human_verified': 'TRUE / FALSE',
    'basis': 'Full-text review / Metadata only / Metadata only — full text awaiting review',
    'criteria': CRITERIA, 'm_prompt_version': 'original_with_primary_survey_definition',
    'm_authors_supplied': 'true / false / Not recorded', 'r_human_verified': 'true / false',
    'r_confidence': 'high / moderate / medium / low; stored spellings are preserved',
    'r_review_status': 'primary_ai_fulltext_review / provisional_ai_review',
    'a_status': 'verified_fulltext / unavailable_after_checks',
    'a_identity_check': 'title_match / doi_and_title_match / title_authors_journal_year_visually_verified / title_authors_and_repository_doi_independently_verified',
    'split': 'development / holdout', 'metadata_source': 'Scopus / Crossref',
}
MISSING = {
    'a_version_note': 'Blank = no verified local text; Version not separately recorded = no saved version assessment.',
    'm_evidence': 'Blank = no exact excerpt saved; not proof of ineligibility.',
    'm_other_methods': 'Blank = no other method recorded; not proof that none exists.',
    'm_software': 'not stated = no explicit software name in supplied metadata.',
    'm_recruitment_providers': 'not stated = no explicit provider name in supplied metadata.',
    'm_prediction_time': 'Not recorded = no saved timestamp; never inferred.',
    'm_input_fields': 'Not recorded = input fields were not logged; never inferred from available bibliography.',
    'm_authors_supplied': 'Not recorded = unknown; false means explicitly not supplied.',
    'r_supporting_resource_url': 'Blank = no supporting URL recorded, or no completed review; not proof that no resource exists.',
    'abstract': 'Blank = no abstract supplied by the bibliographic source.',
    'keywords': 'Blank = no keywords supplied by the bibliographic source.',
}


def field_details(key):
    """Describe storage and missingness without recoding the saved assessments."""
    kind, values = 'Text', 'Free text; no fixed levels.'
    if key in LEVELS:
        kind, values = 'Categorical text', LEVELS[key]
    elif key == 'journal':
        kind, values = 'Categorical text', 'The 62 journal names listed below; 10 articles per journal.'
    elif key in ['year', 'n_authors']:
        kind, values = 'Integer', '2016–2025 inclusive' if key == 'year' else 'Positive author count; current range 1–26.'
    elif key == 'article_id':
        kind, values = 'Identifier text', 'Scopus identifier, or cr_ followed by the Crossref fallback identifier.'
    elif key == 'doi':
        kind, values = 'Identifier text', 'DOI string (10.…/…); hyperlink opens its DOI landing page.'
    elif key.endswith('_sha256'):
        kind, values = 'Hash text', '64 hexadecimal characters: SHA-256 of the source document.'
    elif key.endswith('_url'):
        kind, values = 'URL text', 'Recorded source URL; supporting sources may contain several URLs.'
    elif key in ['local_file', 'r_source_path', 'a_text_cache']:
        kind, values = 'Path text', 'Local file path; clickable when that file exists.'
    elif key in ['m_prediction_time', 'a_checked_at', 'source_date', 'r_review_date']:
        kind, values = 'Date/time text', 'YYYY-MM-DD' if key == 'r_review_date' else 'Recorded timestamp; metadata decision time may be Not recorded.'
    elif key == 'm_input_fields':
        kind, values = 'Categorical text', 'title;abstract;keywords;authors / title;abstract;keywords;indexed_keywords / Not recorded'
    elif key in ['m_reviewer', 'r_reviewer']:
        kind, values = 'Identifier text', 'Saved reviewer identifier; current identifiers are shown in Observed.'
    missing = 'Blank not expected; none currently missing.'
    if key.startswith('r_'):
        missing = 'Blank = no completed source review; never NO.'
    if key in ['format', 'local_file', 'a_identity_check', 'a_source_url', 'a_source_sha256', 'a_text_cache']:
        missing = 'Blank = no verified local main text.'
    return kind, values, MISSING.get(key, missing)


def observed_values(key, rows):
    counts = Counter(row.get(key, '') for row in rows)
    blank = counts.pop('', 0)
    if key in LEVELS or key in ['m_input_fields', 'm_reviewer', 'r_reviewer']:
        result = '; '.join(f'{value}: {count}' for value, count in sorted(counts.items()))
    elif key in ['year', 'n_authors']:
        result = f'Range {min(counts)}–{max(counts)}; {len(counts)} distinct values'
    else:
        result = f'{sum(counts.values())} nonblank; {len(counts)} distinct values'
        for value in ['Not recorded', 'not stated', 'Version not separately recorded']:
            if value in counts:
                result += f'; {value}: {counts[value]}'
    return result + f'; blank: {blank}'


def write_codebook(rows, details, journals):
    """Publish the schema and aggregate counts, never article metadata or excerpts."""
    basis = Counter(row['basis'] for row in rows)
    lines = ['# SCORE validation workbook codebook', '',
        'The private workbook has 620 article rows and 63 variables. Journals are alphabetical; years run from 2025 down to 2016 within each journal.', '',
        'Each row is one selected article. Only year and author count are stored as Excel numbers; identifiers, categories, dates and narrative fields are stored as text.', '',
        'Current assessment basis: ' + '; '.join(f'{key}: {value}' for key, value in basis.items()) + '.', '',
        '`m_` fields preserve the original metadata assessments; `r_` fields preserve completed source reviews; `a_` fields describe current acquisition. Best-available labels use the source review when present and otherwise the original metadata assessment. Downloading a document never implies that it was reviewed.', '',
        'YES = qualifying evidence; NO = ineligible under that assessment; UNCLEAR = unresolved. Missing full text is not a NO. Survey means a primary questionnaire survey, including survey experiments and diary surveys, rather than incidental scales. No country restriction applies. Human-verified best assessments: ' + str(sum(row['human_verified'] == 'TRUE' for row in rows)) + '/620.', '',
        'Allowed levels describe the field; Observed reports the actual snapshot. Free-text fields have no finite level list. Blank cells and the literal values `UNCLEAR`, `not stated`, and `Not recorded` are distinct. The historical development/holdout split is not an untouched test for the later proposed prompt.', '',
        '| # | Machine field | Workbook column | Meaning | Type | Allowed levels / format | Missing means | Observed |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for detail in details:
        lines.append('| ' + ' | '.join(str(value).replace('|', '\\|').replace('\n', ' ') for value in detail) + ' |')
    lines += ['', '## Journal levels', '', 'These are all 62 allowed journal values; each has 10 rows.', '',
              '| Journal | Rows |', '| --- | --- |']
    lines += [f'| {journal} | 10 |' for journal in journals]
    lines += ['', 'The workbook contains licensed abstracts, author lists, exact evidence, and local paths and remains private. This codebook contains definitions and aggregate counts only.', '',
              'Regenerate the workbook and this codebook together with `python3 score/workbook.py`.', '']
    target = ROOT / 'score/codebook.md'
    temporary = target.with_suffix('.tmp')
    temporary.write_text('\n'.join(lines))
    temporary.replace(target)


def main():
    articles = index_rows(read_rows(PRIVATE / 'articles.csv'))
    metadata = index_rows(read_rows(PRIVATE / 'predictions_original.csv'))
    reviews = index_rows(read_rows(PRIVATE / 'fulltext_reviews.csv'))
    access = index_rows(read_rows(PRIVATE / 'fulltext.csv'))
    assert len(articles) == 620 and set(metadata) == set(articles) == set(access)
    assert len({(r['journal'], r['year']) for r in articles.values()}) == 620
    validate_reviews(reviews, articles, access)
    ordered = sorted(articles.values(), key=lambda r: (r['journal'].casefold(), -int(r['year'])))
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Articles'
    sheet.append([label for key, label, description, width in COLUMNS])
    rows = []
    for article in ordered:
        key = article['article_id']
        acquired, prediction, review = access[key], metadata[key], reviews.get(key)
        verified = acquired['status'] == 'verified_fulltext'
        if verified:
            path = Path(acquired['fulltext_path'])
            assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == acquired['source_sha256'], key
        chosen = review or prediction
        row = dict(article, available='YES' if verified else 'NO', format=acquired['format'].upper() if verified else '',
                   local_file=acquired['fulltext_path'] if verified else '', criteria=CRITERIA,
                   basis='Full-text review' if review else 'Metadata only — full text awaiting review' if verified else 'Metadata only',
                   human_verified=review.get('human_verified', 'false').upper() if review else 'FALSE')
        row.update({field: chosen[field] for field in ['collection', 'experiment', 'survey']})
        for prefix, source in [('m_', prediction), ('r_', review or {}), ('a_', acquired)]:
            row.update({prefix + field: value for field, value in source.items()})
        for field in ['m_prediction_time', 'm_input_fields', 'm_authors_supplied']:
            row[field] = row.get(field) or 'Not recorded'
        row['a_version_note'] = row.get('a_version_note') or ('Version not separately recorded' if verified else '')
        row['year'], row['n_authors'] = int(row['year']), int(row['n_authors'])
        rows.append(row)
        sheet.append([row.get(field, '') for field, label, description, width in COLUMNS])
    guide = workbook.create_sheet('Column guide')
    guide.append(['Order', 'Machine field', 'Workbook column', 'Meaning', 'Type', 'Allowed levels / format', 'Missing means', 'Observed'])
    details = []
    journals = sorted({row['journal'] for row in rows}, key=str.casefold)
    for position, (key, label, description, width) in enumerate(COLUMNS, 1):
        detail = [position, key, label, description, *field_details(key), observed_values(key, rows)]
        details.append(detail)
        guide.append(detail)
        sheet.column_dimensions[get_column_letter(position)].width = width
    guide.append(['', '', 'Private workbook', 'Contains abstracts, author lists, evidence, and local paths. Keep out of public GitHub and dashboards.'])
    guide.append(['', '', 'Label interpretation', 'YES = qualifying evidence; NO = ineligible according to that assessment; UNCLEAR = unresolved. There are no country or significance restrictions.'])
    guide.append(['', '', 'Frozen criteria', CRITERIA + '. New policy proposals are untested and have not replaced any saved label.'])
    guide.append(['', '', 'Newly available documents', 'Verified downloads without completed reviews retain metadata-based best labels and show Metadata only — full text awaiting review.'])
    guide.append(['', 'journal', 'All journal levels', 'Each of these 62 categorical values has 10 article rows.'])
    for journal in journals:
        guide.append(['', 'journal', journal, '10 article rows'])
    for worksheet in [sheet, guide]:
        worksheet.freeze_panes = 'E2' if worksheet == sheet else 'D2'
        for cell in worksheet[1]:
            cell.fill = PatternFill('solid', fgColor='173F4F')
            cell.font = Font(color='FFFFFF', bold=True)
            cell.alignment = Alignment(vertical='center', wrap_text=True)
        worksheet.row_dimensions[1].height = 42
        worksheet.sheet_view.zoomScale = 80
        for cells in worksheet.iter_rows(min_row=2):
            for cell in cells:
                if isinstance(cell.value, str):
                    assert len(cell.value) <= 32767, 'Excel cell text exceeds its limit'
                    cell.data_type = 's'  # Source text must never become an Excel formula.
                cell.alignment = Alignment(vertical='top', wrap_text=True)
            worksheet.row_dimensions[cells[0].row].height = 66 if worksheet == sheet else 90
    table = Table(displayName='ScoreArticles', ref=f'A1:{get_column_letter(len(COLUMNS))}621')
    table.tableStyleInfo = TableStyleInfo(name='TableStyleMedium2', showRowStripes=True)
    sheet.add_table(table)
    for cells in sheet.iter_rows(min_row=2):
        for (key, label, description, width), cell in zip(COLUMNS, cells):
            value = cell.value
            if not value:
                continue
            if key == 'doi':
                cell.hyperlink = 'https://doi.org/' + value
            elif key in ['local_file', 'r_source_path', 'a_text_cache']:
                path = Path(value)
                if not path.is_absolute():
                    path = ROOT / path if (ROOT / path).exists() else ROOT.parent / path
                if path.is_file():
                    cell.hyperlink = path.resolve().as_uri()
            elif key.endswith('url') and value.startswith(('https://', 'http://')):
                cell.hyperlink = value
            if cell.hyperlink:
                cell.font = Font(color='0563C1', underline='single')
    for column, width in zip('ABCDEFGH', [8, 28, 35, 75, 20, 60, 65, 65]):
        guide.column_dimensions[column].width = width
    guide.auto_filter.ref = 'A1:H64'
    target = PRIVATE / 'SCORE_validation_620.xlsx'
    temporary = target.with_name(target.stem + '.tmp.xlsx')
    workbook.save(temporary)
    check = load_workbook(temporary, read_only=True)
    assert check['Articles'].max_row == 621 and check['Articles'].max_column == len(COLUMNS)
    assert [r[0] for r in check['Articles'].iter_rows(min_row=2, values_only=True)] == [r['article_id'] for r in ordered]
    check.close()
    temporary.replace(target)
    write_codebook(rows, details, journals)
    print(f'Saved {target.name}: 620 articles, {len(COLUMNS)} columns, {len(reviews)} completed full-text reviews.')


if __name__ == '__main__':
    main()
