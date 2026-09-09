import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pipeline'))
from review_priority import assess


class PriorityTests(unittest.TestCase):
    def people(self):
        return [dict(authid=str(i), full_name=f'Author {i}', n_articles=10, n_us_articles=n)
                for i,n in enumerate([4,4,5],1)]

    def test_shared_paper_cannot_separate_shared_authors(self):
        rows,info=assess(self.people(),[dict(credited_authids='1|2')],limit=3)
        self.assertEqual(rows[0]['distinct_tied_pairs_separated_if_us'],0)
        self.assertEqual(rows[0]['new_top50_us_tied_pairs_if_us'],2)

    def test_single_credit_breaks_existing_tie_but_creates_another(self):
        rows,_=assess(self.people(),[dict(credited_authids='1')],limit=3)
        self.assertEqual(rows[0]['top50_us_tied_pairs_separated_if_us'],1)
        self.assertEqual(rows[0]['top50_total_ties_differentiated_if_us'],1)
        self.assertEqual(rows[0]['distinct_tied_pairs_separated_if_us'],1)
        self.assertEqual(rows[0]['new_top50_us_tied_pairs_if_us'],1)

    def test_boundary_ties_are_included(self):
        _,info=assess(self.people(),[],limit=2)
        self.assertEqual(info['total_focus_authors_including_boundary_ties'],3)
        self.assertEqual(info['us_focus_authors_including_boundary_ties'],3)

    def test_unknown_author_is_an_error(self):
        with self.assertRaisesRegex(ValueError,'Unknown credited author'):
            assess(self.people(),[dict(credited_authids='9')])
