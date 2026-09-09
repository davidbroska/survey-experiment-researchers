import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pipeline'))
from common import digest, read_csv, write_csv, write_json
from dashboard import join, make_queue, metadata_digest, select_pool
from fulltext import apply_reviews, file_id, inventory


def fixture():
    raw = [dict(scopus_id='101', first_authid='1', last_authid='1', byline_complete='true',
                title='US voters', abstract='Geography unstated.', keywords='', indexed_keywords='',
                doi='10.1000/example', eid='2-s2.0-101', year='2020', journal='Journal'),
           dict(scopus_id='102', first_authid='1', last_authid='2', byline_complete='true',
                title='Study', abstract='Location not reported.', keywords='', indexed_keywords='',
                doi='', eid='2-s2.0-102', year='2021', journal='Journal')]
    pool = [dict(authid='1', n_articles='2', n_first='2', n_last='1', article_ids='101|102'),
            dict(authid='2', n_articles='1', n_first='0', n_last='1', article_ids='102')]
    aff = [dict(authid=str(i), full_name='Researcher ' + str(i), institution='University', department='Department',
                country='Country', source_url='https://example.edu', verified_on='2026-09-08') for i in (1,2)]
    annotations = [dict(scopus_id=a['scopus_id'], sample_us_label='unclear', evidence_field='abstract',
                        evidence_quote='', rationale='Unknown country', metadata_sha256=metadata_digest(a),
                        reviewer='Reviewer', reviewer_type='AI_assisted', review_date='2026-09-08',
                        human_validated='false', us_and_non_us_samples_reported='false') for a in raw]
    annotations[0].update(sample_us_label='us_explicit', evidence_field='title', evidence_quote='US voters')
    return pool, aff, annotations, raw


class DashboardTests(unittest.TestCase):
    def test_shared_and_sole_counts_and_title_evidence(self):
        authors, articles, links = join(*fixture())
        self.assertEqual([a['n_us_articles'] for a in authors], [1,0])
        self.assertEqual([a['n_sole'] for a in authors], [1,0])
        self.assertEqual(len(links), 3)
        queue = make_queue(authors, articles, 10)
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0]['n_credited_researchers'], 2)
        self.assertEqual(queue[0]['suggested_filename'], '102.pdf')

    def test_pool_cutoff_ties_and_numeric_id_order(self):
        ranking = [dict(authid=str(i), n_articles=str(n)) for i,n in [(11,6),(2,6),(4,8),(3,6)]]
        pool, ties = select_pool(ranking, 2)
        self.assertEqual([a['authid'] for a in pool], ['4','2'])
        self.assertEqual(len(ties), 3)
        self.assertEqual(sum(t['in_dashboard_pool'] == 'false' for t in ties), 2)
        self.assertEqual(len(select_pool(ranking,2,True)[0]),4)

    def test_stale_title_or_keywords_fail(self):
        for key in ('title','keywords','abstract'):
            args = fixture(); args[3][0][key] += ' changed'
            with self.assertRaisesRegex(ValueError, 'Metadata changed'):
                join(*args)

    def test_invalid_position_or_coverage_fail(self):
        args = fixture(); args[3][1]['last_authid'] = '9'
        with self.assertRaisesRegex(ValueError, 'Invalid authorship'):
            join(*args)
        args = fixture(); args[2].pop()
        with self.assertRaisesRegex(ValueError, 'exactly cover'):
            join(*args)

    def test_unclear_tie_rank_and_sensitivity_scenario(self):
        args = fixture(); args[2][0].update(sample_us_label='unclear',evidence_quote='')
        authors, _, _ = join(*args)
        self.assertEqual([a['us_count_rank_within_pool'] for a in authors],[1,1])
        self.assertEqual([a['us_if_all_unclear_resolve_us'] for a in authors],[2,1])


class FulltextTests(unittest.TestCase):
    def test_fulltext_updates_all_shared_authors_with_verified_page(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_csv(root / 'inputs/article_geography.csv',fixture()[2])
            inbox = root / 'private/fulltext/inbox'; inbox.mkdir(parents=True)
            path = inbox / '102.txt'; path.write_text('We recruited 500 adults residing in the United States.')
            self.assertEqual(inventory(root)[0]['status'], 'text_ready_for_review')
            base = join(*fixture())
            review = dict(scopus_id='102', sample_us_label='us_explicit', filename='102.txt',
                          source_sha256=digest(path.read_bytes()), page='1',
                          evidence_quote='adults residing in the United States', rationale='Sampling statement.',
                          us_and_non_us_samples_reported='false', reviewer='Reviewer', reviewer_type='human',
                          review_date='2026-09-08', human_validated='true')
            authors, articles, links = apply_reviews(*base,[review],root)
            self.assertEqual([a['n_us_articles'] for a in authors],[2,1])
            self.assertEqual([a['n_articles'] for a in authors],['2','1'])
            self.assertEqual(len(make_queue(authors,articles,10)),0)
            self.assertEqual(articles[1]['metadata_sample_us_label'],'unclear')
            self.assertTrue(all(l['sample_us_label']=='us_explicit' for l in links))
            bad = {**review,'evidence_quote':'an invented sampling statement'}
            with self.assertRaisesRegex(ValueError,'not found'):
                apply_reviews(*base,[bad],root)
            with self.assertRaisesRegex(ValueError,'Invalid PDF page'):
                apply_reviews(*base,[{**review,'page':'2'}],root)
            path.write_text('Changed source')
            with self.assertRaisesRegex(ValueError,'changed full text'):
                apply_reviews(*base,[review],root)

    def test_file_names_reject_path_traversal_and_wrong_extensions(self):
        for name in ('../102.pdf','102/notes.pdf','102.html','../../102.txt'):
            with self.assertRaises(ValueError): file_id(name)
        self.assertEqual(file_id('102__supplement.pdf'),'102')


if __name__ == '__main__':
    unittest.main()
