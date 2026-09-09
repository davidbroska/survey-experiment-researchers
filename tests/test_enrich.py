import copy
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pipeline'))
from common import digest
from enrich import join


class GeographyJoinTest(unittest.TestCase):
    def setUp(self):
        self.top = [dict(authid='1', article_ids='10|11', n_articles='2', n_first='2', n_last='1'),
                    dict(authid='2', article_ids='11', n_articles='1', n_first='0', n_last='1')]
        self.aff = [dict(authid='1', full_name='A'), dict(authid='2', full_name='B')]
        self.raw = [dict(scopus_id='10', first_authid='1', last_authid='1', byline_complete='true',
                         abstract='US adults', title='A study', doi='10/example', year='2020', journal='Journal'),
                    dict(scopus_id='11', first_authid='1', last_authid='2', byline_complete='true',
                         abstract='US and Danish adults', title='A second study', doi='10/other', year='2021', journal='Journal')]
        self.codes = [dict(scopus_id=r['scopus_id'], sample_us_label='us_explicit', evidence_field='abstract',
                           evidence_quote='US', abstract_sha256=digest(r['abstract']), reviewer='test', review_date='2026-09-08',
                           rationale='Test population', title_only_us_signal='false',
                           us_and_non_us_samples_reported='true' if r['scopus_id']=='11' else 'false',
                           separate_us_sample_count_stated='') for r in self.raw]

    def test_sole_shared_and_mixed_country_counts(self):
        people, papers, links = join(self.top, self.aff, self.codes, self.raw)
        self.assertEqual((len(papers), len(links)), (2, 3))
        self.assertEqual(people[0]['n_sole'], 1)
        self.assertEqual(people[0]['n_first_only'], 1)
        self.assertEqual(people[0]['n_us_abstract_articles'], 2)
        self.assertEqual(people[0]['n_us_mixed_country_articles'], 1)
        self.assertEqual(people[1]['n_us_abstract_articles'], 1)

    def test_incomplete_or_duplicate_labels_fail(self):
        for codes in (self.codes[:1], self.codes + self.codes[:1]):
            with self.assertRaises(ValueError):
                join(self.top, self.aff, codes, self.raw)

    def test_stale_or_unverifiable_evidence_fails(self):
        for field, value in [('abstract_sha256', 'stale'), ('evidence_quote', 'not in the abstract')]:
            codes = copy.deepcopy(self.codes)
            codes[0][field] = value
            with self.assertRaises(ValueError):
                join(self.top, self.aff, codes, self.raw)

    def test_middle_author_cannot_receive_credit(self):
        self.raw[1]['last_authid'] = '3'
        with self.assertRaises(ValueError):
            join(self.top, self.aff, self.codes, self.raw)

    def test_title_only_separate_from_abstract_count(self):
        self.codes[0].update(sample_us_label='unclear', evidence_quote='',
                             title_only_us_signal='true', title_evidence='A study')
        people, _, _ = join(self.top, self.aff, self.codes, self.raw)
        self.assertEqual(people[0]['n_us_abstract_articles'], 1)
        self.assertEqual(people[0]['n_us_title_only_articles'], 1)
        self.assertEqual(people[0]['n_us_including_title_evidence_articles'], 2)


if __name__ == '__main__':
    unittest.main()
