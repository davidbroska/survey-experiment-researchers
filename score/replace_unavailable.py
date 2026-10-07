"""Stage retrievable replacements within the same SCORE journal and year.

Active articles, predictions and reviews are never rewritten by this script.
Candidates use a fixed hash order, independent of their topic or study design.
After initial trials, an optional second phase prioritizes Scopus gold/green OA
candidates in that same order. Skipped candidates remain untested.
Run: python3 score/replace_unavailable.py --rounds 3 --oa-rounds 10 --workers 6
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
from html import unescape
import json
from pathlib import Path
import time
from urllib.parse import urlencode

import fetch_fulltext as access
import sample

PRIVATE = access.PRIVATE
STAGE = PRIVATE / 'replacements'
ORDER_SEED = 'score-replacement-20261007-v1'


def next_candidate(state, frozen, phase, round_number):
    """Keep the original hash rank even when prioritizing OA candidates."""
    attempted = {int(a['candidate_rank']) for a in state['attempts']}
    if phase == 'initial_hash_order':
        ranks = [round_number] if round_number <= len(frozen['candidates']) else []
    else:
        # Elsevier Scopus API Guide: 1=gold, 2=green; the old boolean flag is
        # unreliable for green OA. Neither flag proves that a usable file exists.
        ranks = [rank for rank, row in enumerate(frozen['candidates'], 1)
                 if row.get('openaccess') in {'1', '2'}]
    for rank in ranks:
        if rank not in attempted:
            return rank, frozen['candidates'][rank - 1]
    return None


def blocked_publisher_routes(articles, states):
    """Skip equivalent publisher endpoints only after three observed barriers.

    Repository URLs and other endpoints still receive real retrieval attempts.
    These skips are logged as untested, never as article-specific HTTP failures.
    """
    publishers = {'journals.sagepub.com', 'academic.oup.com', 'www.journals.uchicago.edu',
        'pubsonline.informs.org', 'pubs.aeaweb.org', 'journals.aom.org', 'psycnet.apa.org',
        'read.dukeupress.edu'}
    ids = {a['article_id'] for a in articles}
    ids.update(a['candidate_article_id'] for state in states for a in state['attempts'])
    observations = {}
    for article_id in sorted(ids):
        path = PRIVATE / 'acquisition' / (article_id + '.json')
        if not path.exists(): continue
        for attempt in json.loads(path.read_text())['attempts']:
            url = attempt.get('url', '')
            if access.urlsplit(url).hostname not in publishers: continue
            barrier = attempt.get('access_barrier')
            if (access.urlsplit(attempt.get('final_url', '')).hostname == 'sso.apa.org' and
                    '/login' in access.urlsplit(attempt.get('final_url', '')).path):
                barrier = 'publisher_login_redirect'
            if barrier not in {'bot_challenge', 'sign_in_page', 'publisher_login_redirect'}: continue
            key = access.route_key(url)
            evidence = observations.setdefault(key, {'barrier': barrier, 'article_ids': set()})
            evidence['article_ids'].add(article_id)
    blocked = {key: {'barrier': value['barrier'], 'article_ids': sorted(value['article_ids'])}
               for key, value in observations.items() if len(value['article_ids']) >= 3}
    access.save_json(STAGE / 'skipped_publisher_routes.json', blocked)
    return blocked


def check_publisher_journal(article):
    """Scopus sometimes indexes an article under the wrong journal."""
    url = 'https://api.crossref.org/works/' + access.quote(article['doi'], safe='')
    receipt, data = access.fetch(url, 'application/json')
    try:
        message = json.loads(data)['message']
        titles = message.get('container-title', [])
    except (ValueError, KeyError, TypeError):
        return {'status': 'requires_manual_journal_check', 'url': url}
    if not titles:
        return {'status': 'requires_manual_journal_check', 'url': url}
    result = {'status': 'crossref_journal_match', 'journal_titles': titles,
              'url': url, 'checked_at': receipt.get('checked_at', now())}
    if not any(sample.normal(unescape(title)) == sample.normal(unescape(article['journal'])) for title in titles):
        result['status'] = 'conflicting_publisher_journal'
    return result


def original_recovered(state):
    """A browser-recovered original takes priority over any proposed replacement."""
    old = state['old']
    path = PRIVATE / 'acquisition' / (old['article_id'] + '.json')
    if not path.exists(): return False
    record = json.loads(path.read_text())
    if record['status'] != 'verified_fulltext': return False
    if check_publisher_journal(old)['status'] == 'conflicting_publisher_journal': return False
    for field in ('chosen', 'chosen_rank', 'chosen_phase', 'selected_at', 'pending_metadata', 'error'):
        state.pop(field, None)
    state.update(status='original_recovered', stop_reason='original_main_text_recovered_without_replacement')
    return True


def now():
    return datetime.now(timezone.utc).isoformat()


def metadata(params):
    """Use the entitled Scopus API; never save credential headers."""
    url = sample.BASE + '?' + urlencode(params)
    for attempt in range(3):
        receipt, data = access.fetch(url, 'application/json', retry=attempt > 0)
        try:
            body = json.loads(data)['search-results']
            return body, receipt
        except (ValueError, KeyError):
            if receipt.get('http_status') in {401, 403}:
                break
            time.sleep(attempt + 1)
    raise RuntimeError('Scopus metadata unavailable: ' + str(receipt.get('http_status', receipt.get('error'))))


def frame(old, excluded):
    """Freeze the whole article frame before choosing any candidate in this cell."""
    key = old['journal_id'] + '-' + old['year']
    path = STAGE / 'frames' / (key + '.json')
    if path.exists():
        saved = json.loads(path.read_text())
        if (saved['old_article_id'] != old['article_id'] or saved['query'] != old['query'] or
                saved['candidate_order_seed'] != ORDER_SEED):
            raise RuntimeError('Saved replacement frame does not match the active cell or seed')
        return saved
    entries, start, expected = [], 0, None
    while expected is None or start < expected:
        body, receipt = metadata({'query': old['query'], 'count': 200, 'start': start,
                                  'view': 'STANDARD', 'sort': '+coverDate,+title'})
        count = int(body['opensearch:totalResults'])
        if expected is not None and count != expected:
            raise RuntimeError('Scopus frame count changed while paging ' + key)
        expected = count
        page = body.get('entry', [])
        if not page or 'error' in page[0]:
            break
        entries.extend(page)
        start += len(page)
    candidates = []
    for rank, entry in enumerate(entries):
        row = sample.parse(entry)
        if row['year'] != old['year'] or sample.normal(row['journal']) != sample.normal(old['journal']):
            raise RuntimeError('Wrong journal/year in candidate frame ' + key)
        if row['scopus_id'] and row['scopus_id'] not in excluded:
            row['scopus_frame_rank'] = rank
            candidates.append(row)
    assert len(entries) == expected and len({r['scopus_id'] for r in candidates}) == len(candidates)
    candidates.sort(key=lambda r: hashlib.sha256((ORDER_SEED + ':' + r['scopus_id']).encode()).hexdigest())
    result = {'journal_id': old['journal_id'], 'journal': old['journal'], 'year': old['year'],
              'old_article_id': old['article_id'], 'query': old['query'], 'frame_n': expected,
              'candidate_order_seed': ORDER_SEED, 'retrieved_at': receipt['checked_at'],
              'candidates': candidates}
    access.save_json(path, result)
    return result


def complete_article(candidate, old, frozen):
    body, receipt = metadata({'query': old['query'] + ' AND EID(2-s2.0-' + candidate['scopus_id'] + ')',
                              'count': 1, 'view': 'COMPLETE'})
    if int(body['opensearch:totalResults']) != 1:
        raise ValueError('Candidate no longer belongs to its Scopus journal/year')
    row = sample.parse(body['entry'][0])
    if (row['scopus_id'] != candidate['scopus_id'] or row['year'] != old['year'] or
            sample.normal(row['journal']) != sample.normal(old['journal']) or
            row['doi'] != candidate['doi']):
        raise ValueError('COMPLETE metadata identity, journal/year or DOI changed')
    row['scopus_frame_rank'] = candidate['scopus_frame_rank']
    row = candidate_article(row, old, frozen, receipt['checked_at'])
    row['sample_rank'] = candidate['scopus_frame_rank']
    access.save_json(STAGE / 'metadata' / (row['article_id'] + '.json'), row)
    return row


def candidate_article(candidate, old, frozen, date=None):
    """Title and DOI suffice for retrieval; COMPLETE metadata is needed to choose."""
    row = dict(candidate)
    row.update(article_id=row['scopus_id'], journal_id=old['journal_id'], journal=old['journal'],
        group=old['group'], stratum_n=frozen['frame_n'], sample_rank=candidate['scopus_frame_rank'],
        selection_seed=ORDER_SEED, split='not_in_original_pilot', metadata_source='Scopus',
        source_date=date or frozen['retrieved_at'], query=old['query'], response_cache='',
        has_abstract=bool(row.get('abstract')), has_keywords=bool(row.get('keywords')),
        fulltext_path='', text_cache='', pdf_url='', fulltext_status='pending')
    row['_needs_complete_metadata'] = date is None
    return row


def cached_content(article, works):
    """Use free OpenAlex content only after ordinary publisher/repository attempts."""
    path = PRIVATE / 'acquisition' / (article['article_id'] + '.json')
    record = json.loads(path.read_text())
    if record['status'] == 'verified_fulltext':
        return record
    urls = works.get(article.get('doi', '').lower(), {}).get('content_urls') or {}
    for kind in ('pdf', 'grobid_xml'):
        if not urls.get(kind):
            continue
        budget = access.openalex_allowance()
        if budget is None or not budget['available']:
            record['openalex_content_status'] = 'free_allowance_not_verified' if budget is None else 'waiting_for_free_daily_allowance'
            record['next_retry_at'] = budget.get('resets_at', '') if budget else ''
            break
        url = access.safe_url(urls[kind])
        receipt, data = access.fetch(url)
        parsed, reason = access.document(data, article, url)
        record['attempts'].append({**receipt, 'route': 'openalex_cached_content',
                                  'content_format': kind, 'document_check': reason or parsed['identity_check']})
        if parsed:
            access.retain_document(record, parsed, data, url)
            record['openalex_content_status'] = 'retrieved'
            break
        access.retain_candidate(record, data, url, reason)
        record['openalex_content_status'] = 'attempted_not_usable'
    record.update(n_attempts=len(record['attempts']), checked_at=now())
    access.save_json(path, record)
    return record


def export_stage(states):
    replacements, articles, progress, attempts = [], [], [], []
    path = STAGE / 'bibliographic_rejections.json'
    wrong_journal = {r['article_id'] for r in json.loads(path.read_text())} if path.exists() else set()
    for state in states:
        old = state['old']
        key = old['journal_id'] + '-' + old['year']
        for attempt in state['attempts']:
            attempt.setdefault('selection_phase', 'initial_hash_order')
        access.save_json(STAGE / 'cells' / (key + '.json'), state)
        progress.append({'journal_id': old['journal_id'], 'journal': old['journal'], 'year': old['year'],
            'old_article_id': old['article_id'], 'status': state['status'],
            'candidates_attempted': len(state['attempts']), 'new_article_id': state.get('chosen', {}).get('article_id', ''),
            'stop_reason': state.get('stop_reason', ''), 'error': state.get('error', '')})
        attempts.extend(state['attempts'])
        if state.get('chosen'):
            row = state['chosen']; articles.append(row)
            source = json.loads((PRIVATE / 'acquisition' / (row['article_id'] + '.json')).read_text())
            reason = ('Original Scopus record assigned to the wrong journal; publisher journal of replacement verified.'
                if old['article_id'] in wrong_journal else 'Original main text unavailable after documented access attempts.')
            reason += ' First usable candidate found by the recorded hash-order search, with OA priority only in the second phase.'
            replacements.append({'journal_id': old['journal_id'], 'journal': old['journal'], 'year': old['year'],
                'old_article_id': old['article_id'], 'old_doi': old['doi'], 'new_article_id': row['article_id'],
                'new_doi': row['doi'], 'candidate_rank': state['chosen_rank'], 'frame_n': row['stratum_n'],
                'candidate_order_seed': ORDER_SEED, 'selection_phase': state.get('chosen_phase', 'initial_hash_order'),
                'reason': reason,
                'source_url': source['source_url'], 'source_sha256': source['source_sha256'],
                'format': source['format'], 'version_note': source.get('version_note', ''), 'selected_at': state['selected_at']})
    access.write_csv(STAGE / 'replacement_articles.csv', articles, sample.PRIVATE_FIELDS)
    access.write_csv(STAGE / 'replacements.csv', replacements,
        ['journal_id','journal','year','old_article_id','old_doi','new_article_id','new_doi','candidate_rank',
         'frame_n','candidate_order_seed','selection_phase','reason','source_url','source_sha256','format','version_note','selected_at'])
    access.write_csv(STAGE / 'progress.csv', progress, list(progress[0]))
    access.write_csv(STAGE / 'candidate_attempts.csv', attempts,
        ['journal_id','year','old_article_id','candidate_rank','selection_phase','candidate_article_id','doi','title','status','failure_category','checked_at'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rounds', type=int, default=3)
    parser.add_argument('--oa-rounds', type=int, default=0,
                        help='Additional OA-priority trials per unresolved cell; 0 skips this phase.')
    parser.add_argument('--workers', type=int, default=6)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--cells', nargs='+', help='Continue only listed journal/year cells, e.g. J01-2020; preserve other staged results.')
    parser.add_argument('--unpaywall-email', default=access.UNPAYWALL_EMAIL)
    args = parser.parse_args(); access.UNPAYWALL_EMAIL = args.unpaywall_email
    if args.rounds < 0 or args.oa_rounds < 0 or args.workers < 1 or (args.limit is not None and args.limit < 1):
        parser.error('Round counts must be nonnegative; workers and any limit must be positive.')
    baseline = PRIVATE / 'articles_initial.csv'
    articles = access.read_csv(baseline if baseline.exists() else PRIVATE / 'articles.csv')
    excluded = {r['article_id'] for r in articles}
    initial_access = PRIVATE / 'fulltext_initial.csv'
    before = {r['article_id']: r['status'] for r in access.read_csv(initial_access)} if initial_access.exists() else {}
    missing = [a for a in articles if before.get(a['article_id'],
        json.loads((PRIVATE / 'acquisition' / (a['article_id'] + '.json')).read_text())['status']) != 'verified_fulltext']
    if not missing:
        print('No unavailable active articles to replace.')
        return
    cell_keys = [a['journal_id'] + '-' + a['year'] for a in missing]
    active_cells = set(args.cells or cell_keys[:args.limit])
    if not active_cells <= set(cell_keys):
        parser.error('A requested cell is not an unavailable article in the active sample.')
    states = []
    rejected_path = STAGE / 'rejected_candidates.json'
    rejected = json.loads(rejected_path.read_text()) if rejected_path.exists() else {}
    for old in missing:
        path = STAGE / 'cells' / (old['journal_id'] + '-' + old['year'] + '.json')
        state = json.loads(path.read_text()) if path.exists() else {'old': old, 'status': 'pending', 'attempts': []}
        if state['old']['article_id'] != old['article_id'] or state['old']['query'] != old['query']:
            raise RuntimeError('Saved replacement state does not match the active article')
        chosen_id = state.get('chosen', {}).get('article_id')
        if chosen_id in rejected:
            for field in ('chosen', 'chosen_rank', 'chosen_phase', 'selected_at'):
                state.pop(field, None)
            state['status'] = 'bibliographic_validation_failed'
            set_attempt_status(state, chosen_id, 'bibliographic_validation_failed', rejected[chosen_id]['reason'])
        states.append(state)
    frames = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        jobs = {pool.submit(frame, state['old'], excluded): state for state in states}
        for i, job in enumerate(as_completed(jobs), 1):
            state = jobs[job]; key = state['old']['journal_id'] + '-' + state['old']['year']
            try: frames[key] = job.result()
            except Exception as error: state.update(status='metadata_blocked', error=str(error))
            if i % 20 == 0 or i == len(states):
                export_stage(states); print(f'Candidate frames {i}/{len(states)}', flush=True)
    rounds = [('initial_hash_order', rank) for rank in range(1, args.rounds + 1)]
    rounds += [('scopus_oa_priority', rank) for rank in range(1, args.oa_rounds + 1)]
    for phase, round_number in rounds:
        for state in states:
            original_recovered(state)
        if all(state.get('chosen') or state['status']=='original_recovered' for state in states): break
        jobs, candidates = {}, []
        blocked = blocked_publisher_routes(articles, states) if phase == 'scopus_oa_priority' else {}
        for state in states:
            if state['old']['journal_id'] + '-' + state['old']['year'] not in active_cells: continue
            pending = state.get('pending_metadata')
            if not pending: continue
            article = pending['article']
            record = json.loads((PRIVATE / 'acquisition' / (article['article_id'] + '.json')).read_text())
            choose(state, article, record, pending['rank'], pending['phase'])
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for state in states:
                old = state['old']; key = old['journal_id'] + '-' + old['year']; frozen = frames.get(key)
                if key not in active_cells: continue
                if state.get('chosen') or state.get('pending_metadata') or state['status']=='original_recovered' or not frozen: continue
                choice = next_candidate(state, frozen, phase, round_number)
                if choice is None:
                    if phase == 'scopus_oa_priority': state['status'] = 'oa_candidates_exhausted'
                    continue
                rank, candidate = choice
                if phase == 'scopus_oa_priority':
                    candidates.append((candidate_article(candidate, old, frozen), state, rank))
                else:
                    jobs[pool.submit(complete_article, candidate, old, frozen)] = (state, candidate, rank)
            for job in as_completed(jobs):
                state, candidate, rank = jobs[job]
                try: candidates.append((job.result(), state, rank))
                except Exception as error:
                    state.update(status='metadata_blocked', error=str(error))
                    state['attempts'].append({'journal_id': state['old']['journal_id'], 'year': state['old']['year'],
                        'old_article_id': state['old']['article_id'], 'candidate_rank': rank, 'selection_phase': phase,
                        'candidate_article_id': candidate['scopus_id'], 'doi': candidate['doi'], 'title': candidate['title'],
                        'status': 'metadata_blocked', 'failure_category': str(error), 'checked_at': now()})
        candidates.sort(key=lambda pair: (pair[0]['journal_id'], pair[0]['year']))
        works = access.discovery([a for a, state, rank in candidates])
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            jobs = {pool.submit(access.acquire, a, works, blocked_routes=blocked): (a, state, rank) for a, state, rank in candidates}
            for i, job in enumerate(as_completed(jobs), 1):
                article, state, rank = jobs[job]
                try: record = job.result()
                except Exception as error:
                    state.update(status='retrieval_error', error=type(error).__name__)
                    state['attempts'].append({'journal_id': article['journal_id'], 'year': article['year'],
                        'old_article_id': state['old']['article_id'], 'candidate_rank': rank, 'selection_phase': phase,
                        'candidate_article_id': article['article_id'], 'doi': article['doi'], 'title': article['title'],
                        'status': 'retrieval_error', 'failure_category': type(error).__name__, 'checked_at': now()})
                    continue
                state['current'] = article
                state['attempts'].append({'journal_id': article['journal_id'], 'year': article['year'],
                    'old_article_id': state['old']['article_id'], 'candidate_rank': rank, 'selection_phase': phase,
                    'candidate_article_id': article['article_id'], 'doi': article['doi'], 'title': article['title'],
                    'status': record['status'], 'failure_category': '' if record['status']=='verified_fulltext' else access.access_problem(record)['failure_category'],
                    'checked_at': now()})
                if record['status']=='verified_fulltext': choose(state, article, record, rank, phase)
                else: state['status']='candidate_unavailable'
                if i % 10 == 0 or i == len(jobs):
                    export_stage(states); print(f'{phase} round {round_number}: checked {i}/{len(jobs)}; staged {sum(bool(s.get("chosen")) for s in states)} replacements', flush=True)
        # Sequential content requests make the shared free allowance easy to verify.
        for article, state, rank in candidates:
            if original_recovered(state): continue
            if state.get('chosen') or state.get('pending_metadata') or state['status'] == 'metadata_validation_failed': continue
            if not (PRIVATE / 'acquisition' / (article['article_id'] + '.json')).exists(): continue
            record = cached_content(article, works)
            if state['attempts'] and state['attempts'][-1]['candidate_article_id']==article['article_id']:
                state['attempts'][-1].update(status=record['status'], failure_category='' if record['status']=='verified_fulltext' else access.access_problem(record)['failure_category'])
            if record['status']=='verified_fulltext': choose(state, article, record, rank, phase)
            export_stage(states)
        print(f'{phase} round {round_number} complete: {sum(bool(s.get("chosen")) for s in states)}/{len(states)} replacements staged', flush=True)
    for state in states:
        key = state['old']['journal_id'] + '-' + state['old']['year']
        if key not in active_cells: continue
        frozen = frames.get(key)
        if original_recovered(state):
            continue
        if state.get('chosen'):
            state['stop_reason'] = 'verified_main_text_and_complete_metadata'
        elif state.get('pending_metadata'):
            state['stop_reason'] = 'verified_source_awaits_complete_metadata'
        elif not frozen:
            state['stop_reason'] = 'candidate_frame_metadata_unavailable'
        elif not args.oa_rounds:
            state['stop_reason'] = 'initial_trials_complete_oa_followup_pending'
        elif next_candidate(state, frozen, 'scopus_oa_priority', 1) is None:
            state['stop_reason'] = 'all_scopus_oa_candidates_tested_non_oa_may_remain'
        else:
            state['stop_reason'] = 'oa_trial_limit_reached_untested_candidates_remain'
    export_stage(states)


def choose(state, article, record, rank, phase='initial_hash_order'):
    if original_recovered(state): return False
    original_article = article
    if article.get('_needs_complete_metadata'):
        old = state['old']
        frozen = json.loads((STAGE / 'frames' / (old['journal_id'] + '-' + old['year'] + '.json')).read_text())
        try:
            article = complete_article(frozen['candidates'][rank - 1], old, frozen)
            if article['doi'] != record['doi']:
                raise ValueError('Fresh metadata DOI differs from the verified source')
        except (ValueError, AssertionError) as error:
            state.update(status='metadata_validation_failed', error=str(error))
            state.pop('pending_metadata', None)
            set_attempt_status(state, article['article_id'], 'metadata_validation_failed', str(error))
            return False
        except Exception as error:
            # The source remains safely cached. A metadata outage must not allow
            # an unchecked journal/year or partial authors list into the sample.
            state.update(status='verified_source_metadata_blocked', error=str(error))
            state['pending_metadata'] = {'article': original_article, 'rank': rank, 'phase': phase}
            set_attempt_status(state, article['article_id'], 'verified_source_metadata_blocked', 'complete_metadata_unavailable')
            return False
    journal_check = check_publisher_journal(article)
    record['journal_identity_check'] = journal_check
    access.save_json(PRIVATE / 'acquisition' / (article['article_id'] + '.json'), record)
    if journal_check['status'] == 'conflicting_publisher_journal':
        rejection = {'reason': 'Publisher journal differs from the Scopus candidate cell',
            'expected_journal': article['journal'], 'journal_check': journal_check, 'checked_at': now()}
        path = STAGE / 'rejected_candidates.json'
        rejected = json.loads(path.read_text()) if path.exists() else {}
        rejected[article['article_id']] = rejection
        access.save_json(path, rejected)
        state.update(status='bibliographic_validation_failed', error=rejection['reason'])
        state.pop('pending_metadata', None)
        set_attempt_status(state, article['article_id'], 'bibliographic_validation_failed', rejection['reason'])
        return False
    article = dict(article, fulltext_status='verified_fulltext', fulltext_path=record['fulltext_path'],
                   text_cache=record['text_cache'], pdf_url=record['source_url'] if record['format']=='pdf' else '')
    state.update(chosen=article, chosen_rank=rank, chosen_phase=phase,
                 status='replacement_found', selected_at=now())
    state.pop('error', None)
    state.pop('pending_metadata', None)
    set_attempt_status(state, article['article_id'], 'verified_fulltext', '')
    return True


def set_attempt_status(state, article_id, status, reason):
    for attempt in reversed(state['attempts']):
        if attempt['candidate_article_id'] == article_id:
            attempt.update(status=status, failure_category=reason)
            break


if __name__ == '__main__':
    main()
