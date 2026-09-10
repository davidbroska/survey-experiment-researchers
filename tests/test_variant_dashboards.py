"""Check immutable query identity, frozen credits, and shared geography joins."""
from collections import Counter
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from common import read_csv
from variant_dashboards import VARIANTS, load_inputs, make_payload, query_tokens, readable_query, verified_priority_pdf


class Document(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.data = []
        self.capture = False
        self.links = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script" and attrs.get("id") == "dashboard-data":
            self.capture = True
        if tag == "a":
            self.links.append(attrs.get("href", ""))

    def handle_endtag(self, tag):
        if tag == "script":
            self.capture = False

    def handle_data(self, data):
        if self.capture:
            self.data.append(data)


class VariantDashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.documents = {key: Document((ROOT / c["file"]).read_text()) for key, c in VARIANTS.items()}
        cls.payloads = {key: json.loads("".join(d.data)) for key, d in cls.documents.items()}

    def test_each_page_exposes_its_actual_query(self):
        hashes = set()
        for key, c in VARIANTS.items():
            d = self.payloads[key]
            self.assertEqual(d["query"], (ROOT / c["query"]).read_text().strip())
            self.assertEqual(d["key"], key)
            self.assertIn("PUBYEAR > 2009", d["query"])
            self.assertIn("PUBYEAR < 2027", d["query"])
            hashes.add(d["query"])
            readable = readable_query(d['query'])
            self.assertEqual(query_tokens(readable), query_tokens(d['query']))
            for line in readable.splitlines():
                self.assertLessEqual(query_tokens(line).count('OR'), 1)
        self.assertEqual(len(hashes), 3)

    def test_legacy_counts_are_frozen_and_zero_is_explicit(self):
        authors = {a["authid"]: a for a in self.payloads["original"]["authors"]}
        old = read_csv(ROOT / "results/query_rankings_2026_09_10/current_published_ranking.csv")
        for r in old:
            self.assertEqual(authors[r["authid"]]["n_articles"], int(r["n_articles"]))
        self.assertEqual(authors["7003917566"]["n_articles"], 0)
        self.assertIsNone(authors["7003917566"]["rank"])

    def test_same_pool_and_updated_article_evidence(self):
        sets = []
        for d in self.payloads.values():
            pool = {a["authid"] for a in d["authors"] if a["in_pool"]}
            sets.append(pool)
            self.assertEqual(len(pool), 120)
            by_author = {}
            for a in d["articles"]:
                for aid in a["authors"]:
                    by_author.setdefault(aid, Counter())[a["geography"]] += 1
            for a in d["authors"]:
                c = by_author.get(a["authid"], Counter())
                self.assertEqual(a["us_count"], c["us_explicit"] + c["us_inferred"])
                self.assertEqual(a["n_articles"], sum(c.values()))
                if a["in_pool"]:
                    self.assertEqual(a["unreviewed"], 0)
        self.assertEqual(sets[0], sets[1])
        self.assertEqual(sets[1], sets[2])

    def test_narrowing_preserves_article_identity_and_no_invented_affiliations(self):
        full = {a["sid"] for a in self.payloads["complete"]["articles"]}
        narrow = {a["sid"] for a in self.payloads["narrower"]["articles"]}
        self.assertTrue(narrow < full)
        self.assertEqual(len(full - narrow), 310)
        for d in self.payloads.values():
            for a in d["authors"]:
                if a["institution"] or a["department"] or a["country"]:
                    self.assertTrue(a["profile_url"].startswith(("https://", "http://")))

    def test_local_links_resolve_and_no_private_sources_are_embedded(self):
        for key, doc in self.documents.items():
            for link in doc.links:
                if not link or link.startswith(("https://", "http://", "#")):
                    continue
                self.assertTrue((ROOT / link).exists(), (key, link))
            raw = json.dumps(self.payloads[key])
            self.assertNotIn("/Users/", raw)
            self.assertNotIn('"abstract"', raw)
            self.assertNotIn('"evidence_quote"', raw)
            self.assertNotIn('private/', raw)
        for path in (ROOT / 'results/variant_dashboards_2026_09_10').glob('*_provenance.json'):
            self.assertNotIn('private/', path.read_text())

    def test_latest_fulltexts_and_known_access_limits(self):
        latest = read_csv(ROOT / 'results/benchmark_review_wave3_2026_09_10/availability_manifest.csv')
        ready = {r['scopus_id'] for r in latest if r['fulltext_readiness'] == 'ready_for_fulltext_review'}
        pending = {r['scopus_id'] for r in latest if r['publisher_access_issue']}
        priority = ROOT / 'results/us_geography_priority_2026_09_10/fulltext_geography_reviews.csv'
        ready.update(r['scopus_id'] for r in read_csv(priority))
        for data in self.payloads.values():
            articles = {a['sid']: a for a in data['articles']}
            for sid in ready & articles.keys():
                self.assertTrue(articles[sid]['pdf_available'], sid)
                self.assertFalse(articles[sid]['alternative_copy_pending'], sid)
            for sid in pending & articles.keys():
                self.assertFalse(articles[sid]['pdf_available'], sid)
                self.assertTrue(articles[sid]['alternative_copy_pending'], sid)
            if '85110788543' in articles:
                a = articles['85110788543']
                self.assertTrue(a['alternative_copy_pending'])
                self.assertIn('User could not download', a['access_note'])

    def test_public_only_availability_and_provenance_match_private_verified_build(self):
        private = ROOT / 'private/us_geography_priority_2026_09_10/fulltext_reviews.csv'
        private_present = private.exists()
        with patch('variant_dashboards.verified_priority_pdf', wraps=verified_priority_pdf) as verify:
            baseline = load_inputs()
            self.assertEqual(verify.call_count, 7 if private_present else 0)
        exists = Path.exists
        with patch.object(Path, 'exists', lambda p: False if p == private else exists(p)):
            with patch('variant_dashboards.verified_priority_pdf', side_effect=AssertionError('Public-only build must not claim source revalidation')):
                public_only = load_inputs()
        self.assertEqual(baseline, public_only)
        self.assertTrue(all(not p.is_relative_to(ROOT / 'private') for p in public_only['paths']))
        for key in VARIANTS:
            self.assertEqual(make_payload(key, baseline), make_payload(key, public_only))


if __name__ == "__main__":
    unittest.main()
