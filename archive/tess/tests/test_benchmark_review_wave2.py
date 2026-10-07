import sys
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import benchmark_review_wave2 as wave


class WaveTwoTests(unittest.TestCase):
    def test_archive_survives_current_stage_changes_and_detects_archive_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            consensus = root / "results/precision_benchmark_2026_09_10/article_consensus.csv"
            consensus.parent.mkdir(parents=True)
            consensus.write_text("original 18-review stage\n")
            with patch.object(wave, "ROOT", root), patch.object(wave, "PRIVATE", root / "private/wave2"):
                archive, original = wave.archive_previous()
                consensus.write_text("a later stage\n")
                second, saved = wave.archive_previous()
                self.assertEqual(archive, second)
                self.assertEqual(original, saved)
                preserved = root / saved["files"][0]["archive_path"]
                self.assertEqual(preserved.read_text(), "original 18-review stage\n")
                preserved.write_text("changed archive")
                with self.assertRaises(ValueError):
                    wave.archive_previous()

    def test_validator_restores_original_namespace_even_on_failure(self):
        original = wave.benchmark.PRIVATE
        with patch.object(wave.benchmark, "validate_reviews", side_effect=ValueError("bad span")):
            with self.assertRaises(ValueError):
                wave.validate_reviews(Path("not-read.json"))
        self.assertEqual(wave.benchmark.PRIVATE, original)

    def test_geography_adjudication_requires_exact_source_and_cannot_change_other_axes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            private = root / "private/wave2"
            combined = private / "combined_stage"
            combined.mkdir(parents=True)
            pdf = private / "source.pdf"
            pdf.write_bytes(b"synthetic source bytes for hash validation")
            sha = wave.digest(pdf.read_bytes())
            page = "Participation was restricted to U.S. respondents."
            cache = private / "text.json"
            cache.write_text(json.dumps({"source_sha256": sha, "pages": [page]}))
            text_sha = wave.digest(cache.read_bytes())
            manifest = [{"benchmark_id": "PB-test", "scopus_id": "1", "documents": [{"pdf_sha256": sha,
                "pdf_path": str(pdf.relative_to(root)), "text_cache": str(cache.relative_to(root)), "text_sha256": text_sha}]}]
            packet = [{"benchmark_id": "PB-test", "readiness": "ready_for_fulltext_review", "documents": [
                {"document_sha256": sha, "text_sha256": text_sha, "pages": [{"pdf_page": 1, "text": page}]}]}]
            (combined / "availability_manifest.json").write_text(json.dumps(manifest))
            (combined / "reviewer_packet.json").write_text(json.dumps(packet))
            row = {"benchmark_id": "PB-test", "scopus_id": "1", "axis": "geography", "decision": "US_explicit",
                   "document_sha256": sha, "pdf_page": 1, "evidence_quote": "restricted to U.S. respondents",
                   "rationale": "Residence was explicitly restricted.", "reviewer": "root", "reviewer_type": "AI_assisted",
                   "review_date": "2026-09-10", "human_validated": False}
            path = private / "adjudications.json"
            with patch.object(wave, "ROOT", root), patch.object(wave, "PRIVATE", private):
                path.write_text(json.dumps([row]))
                self.assertEqual(wave.validate_adjudications(), [row])
                for changed in ({"evidence_quote": "invented text"}, {"document_sha256": "wrong"}, {"axis": "design"}):
                    path.write_text(json.dumps([{**row, **changed}]))
                    with self.assertRaises(ValueError):
                        wave.validate_adjudications()
            original = {"benchmark_id": "PB-test", "review_coverage": "double_pass", "geography": "unclear",
                        "coder_A_geography": "US_explicit", "coder_B_geography": "US_inferred", "design": "yes", "parser_compatible": "no"}
            result = wave.apply_geography_adjudications([original], [row])[0]
            self.assertEqual(result["geography"], "US_explicit")
            self.assertEqual(result["raw_consensus_geography"], "unclear")
            self.assertEqual(original["geography"], "unclear")
            for field in ("design", "parser_compatible", "coder_A_geography", "coder_B_geography"):
                self.assertEqual(result[field], original[field])


if __name__ == "__main__":
    unittest.main()
