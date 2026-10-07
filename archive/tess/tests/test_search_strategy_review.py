import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
from common import read_csv, write_csv, write_json
import search_strategy_review as review


class ReviewTests(unittest.TestCase):
    def test_disagreement_and_known_incompatibility_never_become_positive_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            packet = [{"scopus_id": str(i), "title": "Example "+str(i), "doi": "10.1/"+str(i),
                       "abstract": "Participants rated randomized materials.", "keywords": ""} for i in (1,2)]
            write_json(folder/"validation_packet.json", packet)
            write_csv(folder/"validation_sample.csv", [{"scopus_id": str(i)} for i in (1,2)])
            for coder in ("A", "B"):
                labels = []
                for i in (1,2):
                    labels.append({"scopus_id": str(i), "design": "no" if coder == "B" and i == 1 else "yes",
                        "new_data": "yes", "text_treatment": "yes", "parser_compatible": "no" if coder == "A" and i == 2 else "unclear",
                        "geography": "unclear", "rationale": "Fixture", "reviewer": coder,
                        "reviewer_type": "AI_assisted", "human_validated": "false",
                        "evidence_field": "abstract", "evidence_quote": "Participants rated randomized materials."})
                write_csv(folder/("validation_coder_"+coder+".csv"), labels)
            with patch.object(review, "PRIVATE", folder), patch.object(review, "RESULTS", folder), patch("builtins.print"):
                stats = review.summarize()
            self.assertEqual(stats["agreed_yes"], 1)
            self.assertEqual(stats["unclear_or_disagreement"], 1)
            self.assertEqual(stats["candidate_after_known_incompatibility_flags"], 0)
            rows = read_csv(folder/"validation_consensus.csv")
            self.assertEqual(rows[1]["parser_incompatibility_flag"], "true")


if __name__ == "__main__":
    unittest.main()
