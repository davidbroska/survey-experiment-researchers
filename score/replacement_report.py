"""Summarize the saved replacement search without exposing licensed metadata."""
from collections import Counter
import json
from pathlib import Path

from common import read_csv, write_csv

ROOT = Path(__file__).resolve().parent
PRIVATE = ROOT.parent / 'private/score'
SEARCH = PRIVATE / 'replacements'
PLATFORMS = {'10.1037': 'APA', '10.1177': 'Sage', '10.3102': 'Sage', '10.1509': 'Sage',
    '10.1093': 'Oxford', '10.1086': 'Chicago', '10.1287': 'INFORMS',
    '10.1257': 'American Economic Association', '10.5465': 'Academy of Management',
    '10.1215': 'Duke'}


def main():
    original = {r['article_id']: r for r in read_csv(PRIVATE / 'fulltext_initial.csv')}
    missing = {key: r for key, r in original.items() if r['status'] != 'verified_fulltext'}
    changes = read_csv(ROOT / 'replacements.csv')
    replaced = {r['old_article_id'] for r in changes}
    attempts = read_csv(SEARCH / 'candidate_attempts.csv')
    access = read_csv(ROOT / 'access.csv')
    available = [r for r in access if r['status'] == 'verified_fulltext']
    recovered = {r['article_id'] for r in available} & missing.keys()
    before = Counter(PLATFORMS[r['doi'].split('/')[0].lower()] for r in missing.values())
    found = Counter(PLATFORMS[missing[key]['doi'].split('/')[0].lower()] for key in replaced)
    recovered_by_platform = Counter(PLATFORMS[missing[key]['doi'].split('/')[0].lower()] for key in recovered)
    cells = []
    for row in read_csv(SEARCH / 'progress.csv'):
        key = row['old_article_id']
        frame = json.loads((SEARCH / 'frames' / f"{row['journal_id']}-{row['year']}.json").read_text())
        tested = {a['candidate_article_id'] for a in attempts if a['old_article_id'] == key}
        cell = dict(row, alternatives=len(frame['candidates']), candidates_attempted=len(tested),
            alternatives_untested=len(frame['candidates']) - len(tested))
        if key in recovered:
            cell.update(status='original_recovered', new_article_id='',
                stop_reason='original_main_text_recovered_without_replacement')
        cells.append(cell)
    fields = ['journal_id', 'journal', 'year', 'old_article_id', 'status',
              'new_article_id', 'candidates_attempted', 'alternatives', 'alternatives_untested', 'stop_reason']
    cells.sort(key=lambda r: (r['journal'].casefold(), -int(r['year'])))
    write_csv(ROOT / 'replacement_status.csv', cells, fields)
    tested = len({(a['old_article_id'], a['candidate_article_id']) for a in attempts})
    phase_attempts = Counter(a['selection_phase'] for a in attempts)
    phase_selected = Counter(r['selection_phase'] for r in changes)
    formats = Counter(r['format'].upper() for r in available)
    reviewed = len(read_csv(ROOT / 'independent_review.csv'))
    lines = ['# Replacement search and current validation collection', '',
        f'The collection still contains **620 articles in 620 journal/year cells**: 62 journals, 2016–2025. '
        f'All 380 previously available articles were retained. **{len(changes)} unavailable, corrupt or bibliographically invalid selections '
        f'were replaced**; {len(recovered)} original selections were recovered. This gives '
        f'**{len(available)} available main texts** and **{620 - len(available)} unresolved cells**.', '',
        'Current formats: ' + ', '.join(f'{v} {k}' for k, v in sorted(formats.items())) + '.', '',
        f'Completed substantive AI source reviews remain **{reviewed}**. The {len(changes)} replacement articles '
        'have not been classified: their decisions are blank and their assessment basis is Not assessed. '
        'Document identity checking is separate from collection/design review. No human verification or paid LLM API annotation was performed.', '',
        '| Publisher/platform of displaced or unresolved selections | Initially missing | Replaced | Original recovered | Still unresolved |',
        '| --- | ---: | ---: | ---: | ---: |']
    lines += [f'| {name} | {n} | {found[name]} | {recovered_by_platform[name]} | {n - found[name] - recovered_by_platform[name]} |'
              for name, n in sorted(before.items(), key=lambda item: -item[1])]
    lines += ['', '## How alternatives were selected', '',
        'Complete Scopus article frames were saved for all 240 missing cells, containing 18,240 alternatives '
        'after excluding original selections. Candidate ordering uses a fixed seed and article identifier, '
        'without topic, collection, experiment, survey or geographic filters. Journal/source identity, '
        'publication year and article type were checked in the indexed frame. These are raw Scopus-indexed '
        'counts; the entire candidate universe has not been publisher-verified. Accepted source documents '
        'receive a separate actual-journal and identity check, and confirmed indexing errors are excluded '
        'with a recorded reason.', '',
        'The first phase tries the first three candidates in that order, stopping a cell after a verified main text. '
        'The continuation tries up to ten additional Scopus-marked open-access candidates per unresolved cell '
        'in the same saved order, including green OA. '
        'Closed-access candidates skipped in that phase remain untested. The search is bounded; unsuccessful attempts '
        'do not establish that every article in a journal/year is unavailable.', '',
        f'At this checkpoint, **{tested} distinct alternatives** have saved attempts. '
        f"The initial phase accounts for {phase_attempts['initial_hash_order']} attempts and "
        f"{phase_selected['initial_hash_order']} current replacements; the open-access phase accounts for "
        f"{phase_attempts['scopus_oa_priority']} attempts and {phase_selected['scopus_oa_priority']} replacements. "
        'The [cell-by-cell status](replacement_status.csv) gives attempted and untested counts and why each search stopped. '
        'The [replacement log](replacements.csv) records old/new DOIs, rank, phase, source and version caveats.', '',
        'Selection is conditional on discoverable full-text access. This is a stratified working validation '
        'collection, not a probability sample of all publications. Accessibility may correlate with research '
        'methods, so future prompt results should not be treated as population prevalence or universal accuracy.', '',
        '## What the failures mean', '',
        'Successful alternatives show that some cells can be filled despite failure of the original article. '
        'They do not prove that the original failure was an article-specific defect: an alternative may simply '
        'have an accessible repository copy. Login redirects and browser challenges can affect a publisher route '
        'systematically while copies elsewhere remain retrievable. A 403 response alone does not establish '
        'subscription denial. Candidate receipts separately record corrupt files, wrong documents, access '
        'barriers and free-allowance limits.', '',
        f'The [current DOI queue](manual_downloads.csv) contains {620 - len(available)} articles. For future access requests, see the '
        '[official systematic-access steps](systematic_access.md). These are project-access routes to confirm '
        'with Stanford; a Scopus metadata key does not unlock other publishers’ full texts.', '',
        '## Source and historical-result safeguards', '',
        'Every accepted replacement must have readable main text, an article identity check, a saved file hash '
        'and a matching extraction-cache hash. Independent review checks source versions and flags manuscripts '
        'or missing appendices. A main-text file is not proof that all supporting material is present or that '
        'a manuscript is identical to the published article.', '',
        'The [original 620 selections](articles_initial.csv), frozen predictions, 288 source reviews and historical '
        'evaluation are preserved. Replacements do not inherit labels or development/holdout membership. '
        'The [latest prompt](prompt_proposed.md) has received independent internal review but has no new empirical '
        'performance result. The private workbook remains 620 rows × 63 variables, alphabetized by journal '
        'and then by year descending.', '']
    (ROOT / 'replacement_report.md').write_text('\n'.join(lines))
    print(f'Replacement report: {len(changes)} replacements; {tested} alternatives attempted.')


if __name__ == '__main__':
    main()
