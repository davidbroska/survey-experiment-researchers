"""Regression tests for errors that could change researcher selection."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import query
import scopus
from analyse import deduplicate, rank, eligibility_status
from run import parse_entry


class PhraseTests(unittest.TestCase):
    def test_punctuation_boundary_false_positives(self):
        for punctuation in [", ", ". ", "; ", ": ", " / "]:
            with self.subTest(punctuation=punctuation):
                self.assertFalse(query.match({"abstract": "We conducted a survey"+punctuation+"Experimental findings follow."}))

    def test_field_and_keyword_boundaries(self):
        for row in [{"title": "National survey", "abstract": "Experiment conducted"},
                    {"keywords": "survey; experiment"}, {"keywords": "survey | experimental"}]:
            self.assertFalse(query.match(row))

    def test_exact_plural_hyphen_unicode(self):
        for phrase in ["survey experiment", "survey experiments", "survey-based experiments",
                       "survey based experiment", "survey‑embedded experiment", "survey-experimental"]:
            self.assertTrue(query.match({"abstract": "We ran "+phrase+"."}), phrase)

    def test_generic_randomization_and_vignettes_not_sufficient(self):
        for text in ["Respondents were randomly assigned to a drug.", "Respondents read a vignette.",
                     "Participants were randomly assigned to read."]:
            self.assertFalse(query.match({"abstract": text}))

    def test_text_assignment_guard(self):
        self.assertTrue(query.match({"abstract": "Survey respondents were randomly assigned to read a message."}))
        self.assertFalse(query.match({"abstract": "A survey was administered. Mice were randomly assigned to read."}))

    def test_recall_expansions(self):
        for text in ["We ran an experiment embedded in a survey.", "We conducted a randomized vignette experiment.",
                     "Respondents received a randomized information treatment.",
                     "A survey question-wording experiment was conducted."]:
            self.assertTrue(query.match({"abstract": text}), text)

    def test_removed_ambiguous_terms(self):
        for text in ["An experimental module covered a survey of proteins.",
                     "A split-ballot experiment in surveys tested recruitment letters."]:
            self.assertFalse(query.match({"abstract": text}))

    def test_design_mentions_are_review_cues_not_exclusions(self):
        for text in ["A conjoint survey experiment was conducted.", "A survey experiment used a split-ballot design.",
                     "A survey experiment used split ballot randomization.", "A survey experiment used a split‑ballot design."]:
            self.assertTrue(query.match({"abstract": text}))
            self.assertTrue(query.design_review_cue({"abstract": text}))
        self.assertTrue(query.design_review_cue({"title": "Survey experiment", "keywords": "conjoint analysis"}))

    def test_no_design_search_terms_or_explicit_exclusions(self):
        for q in query.groups():
            self.assertNotIn("AND NOT", q)
            self.assertNotIn("conjoint", q)
            self.assertNotIn("split ballot", q)
            self.assertNotIn("split-ballot", q)

    def test_panel_cues_do_not_determine_eligibility(self):
        self.assertEqual(query.panel_cues({"abstract": "We recruited respondents through Bovitz and Prolific."}), ["Bovitz", "Prolific"])
        self.assertFalse(query.match({"abstract": "An observational survey used Prolific."}))
        self.assertTrue(query.match({"abstract": "A survey experiment used a nationally representative sample."}))

    def test_no_wildcards_in_exact_phrases(self):
        import re
        for phrase in re.findall(r"\{([^}]+)\}", query.build()):
            self.assertNotIn("*", phrase)
            self.assertNotIn("?", phrase)


class RankingTests(unittest.TestCase):
    def test_donor_eligibility_requires_compatibility_and_data_access(self):
        d = {"survey_experiment": "yes", "new_data": "yes", "panel_provider": "Prolific"}
        self.assertEqual(eligibility_status(d), "pending")
        d.update(parser_compatible="yes", data_access="yes")
        self.assertEqual(eligibility_status(d), "confirmed")
        d["parser_compatible"] = "no"
        self.assertEqual(eligibility_status(d), "excluded")

    def row(self, sid="10", authors="1|2", first="1", last="2", doi=""):
        return {"scopus_id": sid, "authids": authors, "first_authid": first, "last_authid": last,
                "doi": doi, "byline_complete": "true", "abstract": "text"}

    def test_single_author_counted_once(self):
        ranks = rank([self.row(authors="1", last="1")], {}, set())
        self.assertEqual(ranks[0]["n_articles"], 1)
        self.assertEqual(ranks[0]["n_first"], 1)
        self.assertEqual(ranks[0]["n_last"], 1)

    def test_middle_author_not_credited(self):
        rows = rank([self.row(authors="1|2|3", last="3")], {}, set())
        self.assertEqual({r["authid"] for r in rows}, {"1", "3"})

    def test_tie_order_reproducible(self):
        rows = [self.row(sid="10", authors="9", first="9", last="9"),
                self.row(sid="11", authors="2", first="2", last="2")]
        self.assertEqual(rank(rows, {}, set()), rank(list(reversed(rows)), {}, set()))
        self.assertEqual(rank(rows, {}, set())[0]["authid"], "2")

    def test_doi_deduplication(self):
        rows, log = deduplicate([self.row(doi="10.123/ABC"), self.row(sid="11", doi="https://doi.org/10.123/abc")])
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(log), 1)

    def test_sequence_orders_authors_and_detects_missing_id(self):
        entry = {"dc:identifier": "SCOPUS_ID:10", "author": [
            {"@seq": "2", "authid": "99"}, {"@seq": "1", "authid": "12"}]}
        row, names = parse_entry(entry)
        self.assertEqual((row["first_authid"], row["last_authid"]), ("12", "99"))
        del entry["author"][0]["authid"]
        self.assertEqual(parse_entry(entry)[0]["byline_complete"], "false")

    def test_missing_sequence_not_guessed(self):
        entry = {"dc:identifier": "SCOPUS_ID:10", "author": [{"authid": "12"}]}
        self.assertEqual(parse_entry(entry)[0]["first_authid"], "")

    def test_merged_author_ids_flagged(self):
        entry = {"dc:identifier": "SCOPUS_ID:10", "author": [
            {"@seq": "1", "authid": "12"}, {"@seq": "2", "authid": "12"}]}
        self.assertEqual(parse_entry(entry)[0]["byline_complete"], "false")


class PaginationTests(unittest.TestCase):
    def response(self, total, ids, nxt=None):
        return {"retrieved_at": "2026-09-08", "body": {"search-results": {
            "opensearch:totalResults": str(total), "entry": [{"dc:identifier": "SCOPUS_ID:"+s} for s in ids],
            "cursor": {"@next": nxt} if nxt else {}}}}

    def test_all_pages_required(self):
        with patch.object(scopus, "request", side_effect=[self.response(2, ["1"], "next"), self.response(2, ["2"])]) as req:
            rows, manifest = scopus.search("q")
        self.assertEqual(len(rows), 2)
        self.assertTrue(manifest["complete"])
        self.assertEqual(req.call_count, 2)

    def test_truncation_fails(self):
        with patch.object(scopus, "request", return_value=self.response(2, ["1"])):
            with self.assertRaisesRegex(RuntimeError, "Incomplete"):
                scopus.search("q")

    def test_count_change_fails(self):
        with patch.object(scopus, "request", side_effect=[self.response(2, ["1"], "n"), self.response(3, ["2"]) ]):
            with self.assertRaisesRegex(RuntimeError, "changed"):
                scopus.search("q")


if __name__ == "__main__":
    unittest.main()
