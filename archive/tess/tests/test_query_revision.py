"""Checks for the requested revision and its retrieval-count interpretation."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import query
import query_revision as revision


class RevisedQueryTests(unittest.TestCase):
    def setUp(self):
        self.families = revision.revised_families()

    def matches(self, text):
        return query.match({"abstract": text}, self.families)

    def test_participant_context_recovers_text_and_wording(self):
        for text in ["Participants were randomly assigned to read a message.",
                     "We conducted question-wording experiments with Azerbaijani participants."]:
            self.assertFalse(query.match({"abstract": text}))
            self.assertTrue(self.matches(text))

    def test_participant_does_not_broaden_other_families(self):
        for text in ["Participants completed a scenario-based experiment.",
                     "Participants were randomly assigned to a drug."]:
            self.assertFalse(self.matches(text))
        self.assertTrue(self.matches("Respondents received a randomized information treatment."))
        self.assertTrue(self.matches("Participants received a randomized information treatment."))

    def test_additional_requested_design_descriptions(self):
        for text in ["An experimental survey study examined support for peace.",
                     "We ran survey based randomised experiments.",
                     "We ran experiments within an online survey.",
                     "Participants were randomly shown information.",
                     "Participants completed an information experiment."]:
            self.assertTrue(self.matches(text))
        self.assertFalse(self.matches("Mice completed an information experiment."))

    def test_message_assignments_need_population_context(self):
        for phrase in revision.ADDED:
            self.assertTrue(self.matches("Participants were " + phrase + "."))
            self.assertFalse(self.matches("Mice were " + phrase + "."))
        self.assertFalse(self.matches("Participants answered a survey. Mice were randomly exposed to a message."))

    def test_removing_national_routes_is_not_a_country_exclusion(self):
        for phrase in revision.REMOVED:
            self.assertTrue(query.match({"abstract": phrase}))
            self.assertFalse(self.matches(phrase))
        self.assertTrue(self.matches("A survey experiment used a nationally representative sample."))
        self.assertNotIn("AND NOT", query.build(self.families))

    def test_existing_plural_and_punctuation_behavior_preserved(self):
        self.assertTrue(self.matches("We ran survey-based experiments."))
        for punctuation in [", ", ". ", "; ", ": "]:
            self.assertFalse(self.matches("We ran a survey" + punctuation + "Experimental findings follow."))
        for text in ["Five studies used experimental, survey, and experience sampling methods.",
                     "Participants recalled information. Experiment 1 used visual scenes.",
                     "Clinical trial registration information: Treatment for depressed participants."]:
            self.assertFalse(self.matches(text))

    def test_revision_does_not_mutate_archived_definitions(self):
        original = json.dumps(revision.previous_families(), sort_keys=True)
        self.families[0]["phrases"].append("unrelated phrase")
        self.assertEqual(original, json.dumps(revision.previous_families(), sort_keys=True))
        self.assertEqual(query.build().strip(), (revision.QDIR / "previous.txt").read_text().strip())


class ComparisonTests(unittest.TestCase):
    def entry(self, sid, doi=""):
        return {"dc:identifier": "SCOPUS_ID:" + sid, "prism:doi": doi}

    def test_new_database_id_for_same_doi_is_not_an_added_article(self):
        old = {"1": self.entry("1", "10.123/ABC")}
        new = {"2": self.entry("2", "https://doi.org/10.123/abc")}
        result = revision.contrast(old, new, "test")
        self.assertEqual(result["added_records"], 1)
        self.assertEqual(result["removed_records"], 1)
        self.assertEqual(result["added_unique_articles"], 0)
        self.assertEqual(result["removed_unique_articles"], 0)

    def test_record_additions_and_losses_are_reported_separately(self):
        old = {sid: self.entry(sid) for sid in ["1", "2"]}
        new = {sid: self.entry(sid) for sid in ["2", "3", "4"]}
        result = revision.contrast(old, new, "test")
        self.assertEqual((result["shared_records"], result["added_records"], result["removed_records"]), (1, 2, 1))
        self.assertEqual(result["net_unique_articles"], 1)


if __name__ == "__main__":
    unittest.main()
