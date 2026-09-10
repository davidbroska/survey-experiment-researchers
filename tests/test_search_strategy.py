import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import search_strategy as strategy


class SearchStrategyTests(unittest.TestCase):
    def test_refined_procedure_separates_fields_and_removes_ambiguous_terms(self):
        clause = strategy.clauses()["procedure"]
        self.assertIn('TITLE-ABS(experiment* OR random* OR manipulat* OR "control condition*"', clause)
        self.assertIn("TITLE-ABS(attitud* OR belief* OR opinion* OR intention* OR judgment* OR judgement*)", clause)
        self.assertIn("TITLE-ABS-KEY(participant* OR respondent* OR survey* OR questionnaire* OR human*)", clause)
        self.assertIn("W/5 information", clause)
        for excluded in ("perception*", "preference*", "text*", "AND NOT"):
            self.assertNotIn(excluded, clause)

    def test_named_route_reuses_frozen_initial_query_and_reading_route_survives(self):
        self.assertEqual(strategy.part_query("named_base"), "(" + strategy.audit.routes()["labels"] + ") AND " + strategy.query.LIMITS)
        q = strategy.full_query()
        for phrase in strategy.BASE_LABELS + strategy.EXTRA_LABELS + strategy.GUARDED_LABELS + strategy.READING_LABELS:
            self.assertIn('"' + phrase + '"', q)
        self.assertIn("TITLE-ABS-KEY(" + strategy.SURVEY + ")", strategy.clauses()["reading_assignment"])
        self.assertEqual(q.count("("), q.count(")"))
        for excluded in ("Pennycook", "Richeson", "conjoint", "nationally representative", "AND NOT"):
            self.assertNotIn(excluded, q)

    def test_heldout_packet_excludes_all_identity_aliases_and_omits_route_author_fields(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            results, private = root / "results", root / "private"
            rows = [{"scopus_id": str(i), "doi": "10.123/" + str(i), "identity": "doi:10.123/" + str(i),
                     "all_scopus_ids": str(i), "title": "Article " + str(i), "abstract": "Original study description",
                     "year": "2020", "journal": "Example", "keywords": "Example", "candidate": "true",
                     "source_id": "1", "authors": "AUTHOR SECRET", "procedure": "true"} for i in range(1000, 1111)]
            strategy.write_csv(results / "membership.csv", [{k: v for k, v in r.items() if k not in {"abstract", "keywords", "authors"}} for r in rows])
            ledger = [{"scopus_id": "1000", "doi": "", "normalized_title_sha256": ""},
                      {"scopus_id": "old-id", "doi": "10.123/1001", "normalized_title_sha256": ""},
                      {"scopus_id": "another-id", "doi": "", "normalized_title_sha256": strategy.audit.title_hash("Article 1002")}]
            protocol = {"query_sha256": "frozen", "frame_sha256": "frame", "development_exclusion_sha256": "ledger",
                        "development_sample_sha256": "sample", "sample_estimand": "Held-out remainder"}
            with patch.multiple(strategy, RESULTS=results, PRIVATE=private), \
                    patch.object(strategy, "freeze", return_value=protocol), \
                    patch.object(strategy, "frozen_exclusions", return_value=ledger), \
                    patch.object(strategy, "available_metadata", return_value={r["scopus_id"]: r for r in rows}), \
                    patch.object(strategy, "fetch", side_effect=AssertionError("No network needed")):
                strategy.sample()
                selected = strategy.read_csv(results / "validation_sample.csv")
                self.assertEqual(len(selected), 100)
                self.assertFalse({"1000", "1001", "1002"} & {r["scopus_id"] for r in selected})
                self.assertEqual({r["stratum_N"] for r in selected}, {"108"})
                packet = json.loads((private / "validation_packet.json").read_text())
                self.assertEqual(set(packet[0]), {"scopus_id", "doi", "year", "journal", "title", "abstract", "keywords"})
                self.assertNotIn("AUTHOR SECRET", json.dumps(packet))
                self.assertNotIn("Original study description", (results / "validation_sample.csv").read_text())
                original = (private / "validation_packet.json").read_bytes()
                strategy.sample()
                self.assertEqual(original, (private / "validation_packet.json").read_bytes())
                with self.assertRaisesRegex(ValueError, "100 held-out"):
                    strategy.sample(99)

    def test_author_credit_deduplicates_doi_aliases_and_requires_complete_byline(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            results, previous, private = root / "new", root / "old", root / "private"
            members = [{"scopus_id": "1", "all_scopus_ids": "1|2", "doi": "10.123/a", "identity": "doi:10.123/a"},
                       {"scopus_id": "3", "all_scopus_ids": "3", "doi": "10.123/b", "identity": "doi:10.123/b"}]
            for row in members:
                row.update(candidate="true", latest_revised="true", labels="true", concepts="true", exposure="true", exposure_human="true")
            strategy.write_csv(results / "membership.csv", members)
            strategy.write_csv(previous / "membership.csv", members)
            bib = [{"scopus_id": sid, "doi": "10.123/a" if sid in {"1", "2"} else "10.123/b",
                    "focal": "pennycook", "first_last": "true", "byline_complete": "false" if sid == "3" else "true"}
                   for sid in ("1", "2", "3")]
            strategy.write_csv(private / "author_articles.csv", bib)
            with patch.object(strategy, "RESULTS", results), patch.multiple(strategy.audit, RESULTS=previous, PRIVATE=private):
                rows = strategy.author_comparison()
            for row in rows:
                if row["researcher"] == "pennycook":
                    self.assertEqual(row["articles_any_position"], 2)
                    self.assertEqual(row["first_last_candidate_articles"], 1)


if __name__ == "__main__":
    unittest.main()
