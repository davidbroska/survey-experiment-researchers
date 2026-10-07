import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import design_audit as audit


class DesignAuditTests(unittest.TestCase):
    def test_literal_label_boundaries(self):
        for text in ("We conducted survey experiments.", "A survey-based experiment.", "Experimental surveys of voters."):
            self.assertTrue(audit.local_label({"abstract": text}), text)
        for text in ("We used a survey. Experiments followed.", "We used survey, experimental and interview methods.", "Our experimental, survey and other methods."):
            self.assertFalse(audit.local_label({"abstract": text}), text)
        self.assertFalse(audit.local_label({"title": "Survey", "abstract": "experiments in a laboratory"}))

    def test_generic_positive_queries(self):
        for variant in ("concepts", "exposure", "exposure_human"):
            q = audit.full_query(variant)
            self.assertIn("TITLE-ABS-KEY", q)
            self.assertIn("PUBYEAR > 2009", q)
            self.assertNotIn("AND NOT", q)
            for word in ("Pennycook", "Richeson", "misinformation", "racial", "conjoint", "nationally representative"):
                self.assertNotIn(word, q)
            self.assertEqual(q.count("("), q.count(")"))

    def test_doi_identity(self):
        self.assertEqual(audit.identity({"prism:doi": "https://doi.org/10.123/ABC", "dc:identifier": "SCOPUS_ID:1"}), "doi:10.123/abc")
        self.assertEqual(audit.identity({"dc:identifier": "SCOPUS_ID:1"}), "SCOPUS_ID:1")

    def test_doi_gain_does_not_create_added_and_lost_article(self):
        old = {"1": {"dc:identifier": "SCOPUS_ID:1"}}
        new = {"1": {"dc:identifier": "SCOPUS_ID:1", "prism:doi": "https://doi.org/10.123/ABC"}}
        normalized, conflicts = audit.canonicalize_snapshots({"old": old, "new": new})
        self.assertFalse(conflicts)
        self.assertEqual({audit.identity(e) for e in normalized["old"].values()},
                         {audit.identity(e) for e in normalized["new"].values()})
        self.assertNotIn("prism:doi", old["1"])
        new["1"]["prism:doi"] = "10.123/other"
        _, conflicts = audit.canonicalize_snapshots({"old": normalized["old"], "new": new})
        self.assertEqual(conflicts, [{"scopus_id": "1", "normalized_dois": "10.123/abc|10.123/other"}])

    def test_freeze_rejects_drift_before_writing(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit.write_csv(root / "results/venue_frame.csv", [{"source_id": "1"}])
            with patch.multiple(audit, ROOT=root, RESULTS=root / "results/audit", QUERIES=root / "queries/audit"):
                audit.freeze()
                original = (audit.QUERIES / "exposure.txt").read_bytes()
                protocol = (audit.RESULTS / "protocol.json").read_bytes()
                with patch.object(audit, "LABELS", audit.LABELS + ["new label"]):
                    with self.assertRaisesRegex(ValueError, "Frozen queries"):
                        audit.freeze()
                self.assertEqual(original, (audit.QUERIES / "exposure.txt").read_bytes())
                self.assertEqual(protocol, (audit.RESULTS / "protocol.json").read_bytes())
                audit.write_csv(root / "results/venue_frame.csv", [{"source_id": "2"}])
                with self.assertRaisesRegex(ValueError, "journal frame"):
                    audit.freeze()
                self.assertEqual(original, (audit.QUERIES / "exposure.txt").read_bytes())

    def test_exclusion_identity_aliases_and_empty_values(self):
        ledger = [{"scopus_id": "1", "doi": "https://doi.org/10.123/ABC",
                   "normalized_title_sha256": audit.title_hash("A survey-based finding: evidence")},
                  {"scopus_id": "", "doi": "", "normalized_title_sha256": ""}]
        indexes = audit.exclusion_indexes(ledger)
        for row in ({"all_scopus_ids": "2|1", "doi": "", "title": "Other"},
                    {"all_scopus_ids": "2", "doi": "10.123/abc", "title": "Other"},
                    {"all_scopus_ids": "2", "doi": "", "title": "A survey based finding—Evidence"}):
            self.assertTrue(audit.excluded_by_indexes(row, indexes))
        self.assertFalse(audit.excluded_by_indexes({"all_scopus_ids": "2", "doi": "", "title": ""}, indexes))

    def test_archived_exclusion_ledger_is_private_text_free_and_reusable(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            results, private = root / "results/audit", root / "private/audit"
            source_paths = [root.parent / "Opencall/QueryV2/positives/mining_input.csv",
                            root.parent / "Opencall/QueryV2/termeval/term_samples.csv",
                            private / "author_articles.csv", results / "counterexample_source_audit.csv"]
            for i, path in enumerate(source_paths):
                audit.write_csv(path, [{"scopus_id": str(i+1), "title": "Legacy " + str(i),
                                        "doi": "", "abstract": "LICENSED SECRET TEXT"}])
            with patch.multiple(audit, ROOT=root, RESULTS=results, PRIVATE=private):
                rows = audit.development_exclusions([], {"1": {"doi": "10.123/known"}})
                self.assertEqual(rows[0]["doi"], "10.123/known")
                text = (results / "development_exclusions.csv").read_text()
                self.assertNotIn("LICENSED SECRET TEXT", text)
                self.assertNotIn("Legacy", text)
                for path in source_paths:
                    path.unlink()
                self.assertEqual(rows, audit.development_exclusions([], {}))
                (results / "development_exclusions.csv").write_text(text + "\n")
                with self.assertRaisesRegex(ValueError, "ledger changed"):
                    audit.development_exclusions([], {})

    def test_sample_manifest_rejects_same_ids_with_changed_strata_or_variant(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "validation_sample.csv"
            rows = [{"scopus_id": "1", "stratum": "validation_union", "stratum_N": 1000, "stratum_n": 100}]
            settings = {"selected_variant": "exposure", "query_sha256": "old", "requested_n_per_stratum": 100}
            audit.freeze_selection(path, rows, settings)
            original = path.read_bytes()
            audit.freeze_selection(path, rows, settings)
            for changed_rows, changed_settings in [
                ([{**rows[0], "stratum_N": 1001}], settings),
                (rows, {**settings, "selected_variant": "concepts"}),
                (rows, {**settings, "query_sha256": "changed"}),
            ]:
                with self.assertRaisesRegex(ValueError, "Frozen sample"):
                    audit.freeze_selection(path, changed_rows, changed_settings)
                self.assertEqual(path.read_bytes(), original)

    def test_retrieval_does_not_imply_first_last_credit(self):
        row = {"scopus_id": "1", "doi": "10.123/abc", "source_id": "1", "doctype": "ar",
               "byline_complete": "true", "abstract": "We used a survey. Experiments followed."}
        self.assertIn("local phrase/context check", audit.author_omission_reason(row, {"1"}, {"1"}, True, set(), set()))
        row["abstract"] = "We conducted survey experiments."
        self.assertIn("middle author", audit.author_omission_reason(row, {"1"}, {"1"}, False, set(), set()))
        self.assertIn("absent from frozen", audit.author_omission_reason(row, {"1"}, {"1"}, True, set(), set()))
        self.assertEqual("included; first/last credit", audit.author_omission_reason(row, {"1"}, {"1"}, True, {"1"}, set()))
        self.assertEqual("included; first/last credit", audit.author_omission_reason(row, {"1"}, {"1"}, True, {"2"}, {"10.123/abc"}))


if __name__ == "__main__":
    unittest.main()
