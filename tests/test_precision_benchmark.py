"""Identity, fixed-denominator and page-citation checks for full-text evaluation."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import precision_benchmark as benchmark
from common import digest, write_json


class PrecisionBenchmarkTests(unittest.TestCase):
    def test_identity_is_distinct_from_completeness(self):
        title = "A study of social judgments and information"
        self.assertTrue(benchmark.identity([title], {"title": title}).startswith("verified_"))
        self.assertEqual(benchmark.readiness({"identity_status": "verified_title_in_opening_pages",
            "document_kind": "abstract_only", "text_characters": 5000, "n_pages": 4}), "needs_main_article")
        self.assertEqual(benchmark.readiness({"identity_status": "needs_identity_review",
            "document_kind": "article_or_manuscript", "text_characters": 9000, "n_pages": 9}), "needs_identity_review")

    def test_frozen_sample_rejects_substitution_and_duplicate_doi(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "sample.csv"
            source.write_text("scopus_id,doi,title\n1,10.12/test,An article title\n")
            with patch.multiple(benchmark, PRIVATE=root / "private", RESULTS=root / "results"):
                benchmark.freeze_sample(source)
                source.write_text("scopus_id,doi,title\n2,10.12/other,A replacement title\n")
                with self.assertRaisesRegex(ValueError, "sample is frozen"):
                    benchmark.freeze_sample(source)
                source.write_text("scopus_id,doi,title\n1,10.12/test,A first title\n2,https://doi.org/10.12/TEST,A duplicate title\n")
                with self.assertRaisesRegex(ValueError, "duplicate article"):
                    benchmark.freeze_sample(source)

    def review_fixture(self, root):
        private = root / "private"
        private.mkdir()
        pdf = private / "article.pdf"
        pdf.write_bytes(b"%PDF-test-source")
        sha = digest(pdf.read_bytes())
        cache = private / "text.json"
        pages = ["We randomly assigned participants\nto read a message."]
        write_json(cache, {"source_sha256": sha, "pages": pages})
        text_sha = digest(cache.read_bytes())
        write_json(private / "reviewer_packet.json", [{"benchmark_id": "PB-1", "readiness": "ready_for_fulltext_review",
            "documents": [{"document_sha256": sha, "text_sha256": text_sha,
                           "pages": [{"pdf_page": 1, "text": pages[0]}]}]}])
        write_json(private / "availability_manifest.json", [{"benchmark_id": "PB-1", "documents": [
            {"pdf_sha256": sha, "text_sha256": text_sha, "pdf_path": "private/article.pdf", "text_cache": "private/text.json"}]}])
        evidence = {"decision": "yes", "document_sha256": sha, "pdf_page": 1,
                    "evidence_quote": "randomly assigned participants to read a message", "rationale": "Assigned text is described."}
        review = {"benchmark_id": "PB-1", "evaluation_status": "completed", "reviewer": "test", "reviewer_type": "AI_assisted",
                  "review_date": "2026-09-10", "human_validated": False, "studies": [],
                  **{axis: {"decision": "unclear", "rationale": "Not established by this source."} for axis in benchmark.AXES}}
        review["design"] = evidence
        review["parser_compatible"] = {**evidence, "decision": "no", "rationale": "Separate structural assessment."}
        target = private / "reviews.json"
        write_json(target, [review])
        return private, target, review

    def test_design_does_not_require_parser_or_possession_yes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            private, target, review = self.review_fixture(root)
            with patch.multiple(benchmark, ROOT=root, PRIVATE=private):
                result = benchmark.validate_reviews(target)
                self.assertEqual(result["design_counts"], {"yes": 1})
                self.assertEqual(result["n_completed"], 1)

    def test_review_rejects_wrong_page_quote_source_and_human_claim(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            private, target, review = self.review_fixture(root)
            with patch.multiple(benchmark, ROOT=root, PRIVATE=private):
                for field, value in [("pdf_page", 2), ("evidence_quote", "invented quotation"), ("document_sha256", "unknown")]:
                    changed = deepcopy(review)
                    changed["design"][field] = value
                    write_json(target, [changed])
                    with self.assertRaises(ValueError):
                        benchmark.validate_reviews(target)
                write_json(target, [{**review, "human_validated": True}])
                with self.assertRaisesRegex(ValueError, "cannot claim"):
                    benchmark.validate_reviews(target)
                write_json(target, [review])
                (private / "article.pdf").write_bytes(b"changed source")
                with self.assertRaisesRegex(ValueError, "changed source PDF"):
                    benchmark.validate_reviews(target)

    def test_targeted_public_sources_precede_old_open_locations(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "inputs").mkdir()
            (root / "inputs/precision_benchmark_sources.csv").write_text(
                "scopus_id,url,source_type,note\n1,https://author.example/paper.pdf,author_site,Accepted manuscript\n")
            work = {"id": "W1", "doi": "https://doi.org/10.12/test", "title": "An example paper",
                    "locations": [{"is_oa": True, "pdf_url": "https://publisher.example/old.pdf"}]}
            with patch.multiple(benchmark, ROOT=root, PRIVATE=root / "private"):
                client = benchmark.PublicCopies()
                with patch.object(client, "metadata", return_value={"body": {"results": [work]}}):
                    result = client.discover([{"scopus_id": "1", "doi": "10.12/test", "title": "An example paper"}])["1"]
                self.assertEqual(result["urls"][0], "https://author.example/paper.pdf")
                self.assertEqual(result["curated_sources"][0]["note"], "Accepted manuscript")

    def test_url_budget_and_prior_attempts_are_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.multiple(benchmark, PRIVATE=root):
                write_json(root / "attempts/1.json", [{"url": "https://old.example/article", "http_status": 403}])
                client = benchmark.PublicCopies()
                with patch.object(client, "fetch", side_effect=lambda url: {"url": url, "body": b"", "http_status": 403}) as fetch:
                    result = client.acquire({"scopus_id": "1", "doi": "", "title": "A fixed sampled paper"},
                        {"urls": [f"https://public.example/{n}.pdf" for n in range(12)]})
                self.assertEqual(fetch.call_count, 8)
                self.assertEqual(result["n_urls_this_pass"], 8)
                self.assertEqual(result["n_distinct_urls_all_passes"], 9)
                self.assertEqual(result["attempts"][0]["url"], "https://old.example/article")


if __name__ == "__main__":
    unittest.main()
