import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
from query_ranking_geography import resolve, harmonize, rank_authors, select_review_pool


def ev(value, priority=1, sid="1", doi=""):
    return {"label": value, "priority": priority, "mixed": False, "evidence_id": value + str(priority),
            "rationale": "Recorded review.", "scopus_id": sid, "doi": doi, "human_validated": False}


def article(sid, first="10", last="20", **extra):
    return {"identity": "SCOPUS_ID:" + sid, "scopus_id": sid, "doi": "", "all_scopus_ids": sid,
            "original_query": "true", "narrower_query": "true", "first_authid": first,
            "last_authid": last, "byline_complete": "true", **extra}


class GeographyTests(unittest.TestCase):
    def test_unknown_and_fulltext_precedence_do_not_silence_conflict(self):
        self.assertEqual(resolve([])["sample_us_label"], "unreviewed")
        result = resolve([ev("non_us"), ev("us_explicit", 2)])
        self.assertEqual(result["sample_us_label"], "us_explicit")
        self.assertTrue(result["conflict"])
        self.assertEqual(result["conflict_resolution"], "fulltext_supersedes_metadata")
        self.assertEqual(resolve([ev("non_us", 2), ev("us_explicit", 2)])["sample_us_label"], "unclear")

    def test_alias_and_doi_join(self):
        a = article("1", all_scopus_ids="1|2", doi="10.1000/example")
        labels, grouped, missing = harmonize([a], [ev("us_inferred", sid="2"), ev("us_explicit", sid="3", doi="HTTPS://DOI.ORG/10.1000/EXAMPLE")])
        self.assertEqual(labels[0]["sample_us_label"], "us_explicit")
        self.assertEqual(len(grouped[a["identity"]]), 2)
        self.assertFalse(missing)

    def test_validated_adjudication_preserves_raw_disagreement_flag(self):
        original = {**ev("unclear", 2), "review_conflict": True}
        result = resolve([original, ev("us_explicit", 3)])
        self.assertEqual(result["sample_us_label"], "us_explicit")
        self.assertTrue(result["conflict"])
        self.assertTrue(result["adjudicated"])
        self.assertEqual(result["conflict_resolution"], "validated_geography_adjudication")
        self.assertEqual(result["source_review"], "full_text")

    def test_sole_author_once_unknown_upper_and_frozen_credits(self):
        articles = [article("1", "10", "10"), article("2"), article("3")]
        labels, _, _ = harmonize(articles, [ev("us_explicit"), ev("unclear", sid="2")])
        rows = rank_authors(articles, labels, "original_query")
        row = next(r for r in rows if r["authid"] == "10")
        self.assertEqual((row["n_articles"], row["n_us_articles"], row["n_us_upper"]), (3, 1, 3))
        self.assertEqual((row["n_unclear"], row["n_unreviewed"]), (1, 1))
        frozen = rank_authors(articles, labels, "original_query", frozen_credits={articles[0]["identity"]: {"99"}})
        self.assertEqual([(r["authid"], r["n_articles"]) for r in frozen], [("99", 1)])

    def test_review_pool_includes_total_ties_and_possible_us(self):
        rows = [{"authid": "1", "n_articles": 10, "n_us_articles": 4, "n_us_upper": 4},
                {"authid": "2", "n_articles": 10, "n_us_articles": 0, "n_us_upper": 0},
                {"authid": "3", "n_articles": 6, "n_us_articles": 0, "n_us_upper": 6},
                {"authid": "4", "n_articles": 3, "n_us_articles": 0, "n_us_upper": 3}]
        pool, _ = select_review_pool({"original_query": rows}, size=1)
        self.assertEqual(pool, {"1", "2", "3"})


if __name__ == "__main__":
    unittest.main()
