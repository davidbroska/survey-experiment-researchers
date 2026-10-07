"""Regression checks for the two remaining participant population guards."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import participant_guards as revision
import query
import query_revision


class ParticipantGuardTests(unittest.TestCase):
    def test_changes_only_two_context_flags(self):
        old = query_revision.revised_families()
        before = json.dumps(old, sort_keys=True)
        revised = revision.revised_families()
        for family in old:
            if family["id"] in revision.CHANGED_FAMILIES:
                family["participant_context"] = True
        self.assertEqual(old, revised)
        self.assertEqual(before, json.dumps(query_revision.revised_families(), sort_keys=True))

    def test_contextual_participants_are_recognized(self):
        row = {"abstract": "Participants completed a scenario-based experiment."}
        self.assertFalse(query.match(row, query_revision.revised_families()))
        self.assertTrue(query.match(row, revision.revised_families()))
        self.assertFalse(query.match({"abstract": "Mice completed a scenario-based experiment."}, revision.revised_families()))

    def test_embedded_population_guard_is_already_satisfied_by_phrase(self):
        for phrase in next(f for f in revision.revised_families() if f["id"] == "embedded_design")["phrases"]:
            row = {"abstract": phrase}
            self.assertTrue(query.match(row, query_revision.revised_families()))
            self.assertTrue(query.match(row, revision.revised_families()))

    def test_article_scope_does_not_create_phrase_across_sentence_boundary(self):
        families = revision.revised_families()
        row = {"abstract": "Participants recalled information. Experiment 1 used visual scenes."}
        self.assertFalse(revision.article_context_match(row, families))
        row = {"abstract": "An information experiment was conducted. Participants reported their beliefs."}
        self.assertFalse(query.match(row, families))
        self.assertTrue(revision.article_context_match(row, families))

    def test_no_national_routes_or_explicit_exclusions_added(self):
        text = query.build(revision.revised_families())
        self.assertNotIn("AND NOT", text)
        for phrase in query_revision.REMOVED:
            self.assertNotIn("{" + phrase + "}", text)


if __name__ == "__main__":
    unittest.main()
