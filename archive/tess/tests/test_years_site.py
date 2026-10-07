"""Checks for year-comparison interpretation and publication link integrity."""
import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pipeline'))
import query
from compare_years import tie_metrics
from build_site import check_links


class YearAndSiteTests(unittest.TestCase):
    def test_ties_count_unordered_pairs_including_zero(self):
        m = tie_metrics([3, 3, 2, 0, 0])
        self.assertEqual(m['tied_pairs'], 2)
        self.assertEqual(m['all_pairs'], 10)
        self.assertEqual(m['distinct_counts'], 3)
        self.assertEqual(m['tied_researchers'], 4)

    def test_inclusive_2010_window(self):
        for q in [query.build(), query.baseline_query(), *query.groups()]:
            self.assertIn('PUBYEAR > 2009', q)
            self.assertIn('PUBYEAR < 2027', q)

    def test_nested_links_and_missing_or_outside_files(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory) / 'site'
            (site / 'results').mkdir(parents=True)
            (site / 'results/data.csv').write_text('a,b\n')
            p = site / 'index.html'
            p.write_text('<a href="results/data.csv">Data</a><a href="https://example.org">External</a>')
            self.assertEqual(check_links(site), 1)
            p.write_text('<a href="missing.html">Missing</a>')
            with self.assertRaisesRegex(ValueError, 'Broken or escaping'):
                check_links(site)
            (Path(directory) / 'outside.txt').write_text('private')
            p.write_text('<a href="../outside.txt">Outside</a>')
            with self.assertRaisesRegex(ValueError, 'Broken or escaping'):
                check_links(site)


if __name__ == '__main__':
    unittest.main()
