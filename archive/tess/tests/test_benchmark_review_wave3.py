import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import benchmark_review_wave3 as wave


class WaveThreeTests(unittest.TestCase):
    def test_issued_packet_cannot_be_changed(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "packet.json"
            rows = [{"benchmark_id": "PB-1", "documents": [{"document_sha256": "original"}]}]
            wave.write_packet_once(path, rows)
            original = path.read_bytes()
            wave.write_packet_once(path, rows)
            self.assertEqual(path.read_bytes(), original)
            with self.assertRaises(ValueError):
                wave.write_packet_once(path, [{"benchmark_id": "PB-1", "documents": []}])
            self.assertEqual(path.read_bytes(), original)

    def test_merge_retains_missing_sample_and_rejects_prior_document_replacement(self):
        old = [{"benchmark_id": "PB-old", "readiness": "ready_for_fulltext_review"},
               {"benchmark_id": "PB-new", "readiness": "unavailable"},
               {"benchmark_id": "PB-missing", "readiness": "unavailable"}]
        new = [{"benchmark_id": "PB-new", "readiness": "ready_for_fulltext_review"}]
        result = wave.merge_new_records(old, new, require_unready=True)
        self.assertEqual(len(result), 3)
        self.assertEqual(sum(r["readiness"] == "ready_for_fulltext_review" for r in result), 2)
        self.assertEqual(old[1]["readiness"], "unavailable")
        for bad in ([old[0]], [{"benchmark_id": "PB-outside"}], new + new):
            with self.assertRaises(ValueError):
                wave.merge_new_records(old, bad, require_unready=True)

    def test_frozen_prior_stage_is_immutable_and_independent_of_live_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            results = root / "results" / wave.PRIOR_VERSION
            results.mkdir(parents=True)
            consensus = results / "article_consensus.csv"
            consensus.write_text("frozen 45 reviews\n")
            (results / "review_summary.json").write_text(json.dumps({"double_pass": 45}))
            with patch.object(wave, "ROOT", root), patch.object(wave, "PRIVATE", root / "private/wave3"):
                archive, saved = wave.freeze_prior()
                consensus.write_text("later stage\n")
                self.assertEqual(wave.freeze_prior(), (archive, saved))
                preserved = root / saved["files"][0]["archive_path"]
                preserved.write_text("corrupted archive")
                with self.assertRaises(ValueError):
                    wave.freeze_prior()

    def test_validation_restores_namespace_after_failure(self):
        original = wave.benchmark.PRIVATE
        with patch.object(wave.benchmark, "validate_reviews", side_effect=ValueError("invalid page evidence")):
            with self.assertRaises(ValueError):
                wave.validate_reviews(Path("not-read.json"))
        self.assertEqual(wave.benchmark.PRIVATE, original)


if __name__ == "__main__":
    unittest.main()
