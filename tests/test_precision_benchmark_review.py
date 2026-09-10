"""Missing-access denominators and stratum weights must not disappear in review."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
from precision_benchmark_review import consensus, missing_label_bounds, summarize_strata


class FulltextAggregationTests(unittest.TestCase):
    def sample(self):
        rows = []
        for stratum, N in [("primary_only", 100), ("proximity_only", 40), ("overlap", 10)]:
            for design, coverage in [("yes", "double_pass"), ("unclear", "not_reviewed")]:
                rows.append({"stratum": stratum, "stratum_N": N, "stratum_n": 2,
                             "inclusion_probability": 2 / N, "design": design,
                             "review_coverage": coverage, "fulltext_readiness": "needs_main_article" if coverage == "not_reviewed" else "ready_for_fulltext_review"})
        return rows

    def test_unavailable_sample_members_keep_their_weight(self):
        summaries = summarize_strata(self.sample())
        bounds = missing_label_bounds(summaries)
        union, clause = bounds
        self.assertEqual(union["fixed_sample_n"], 6)
        self.assertEqual(union["population_after_development_exclusions"], 150)
        self.assertEqual(clause["population_after_development_exclusions"], 50)
        self.assertEqual((union["lower_bound"], union["upper_bound"]), (.5, 1.0))
        self.assertEqual(union["unknown_sample_labels"], 3)

    def test_large_strata_receive_proportional_weight(self):
        rows = self.sample()
        rows[1].update(design="no", review_coverage="double_pass")
        union = missing_label_bounds(summarize_strata(rows))[0]
        self.assertAlmostEqual(union["upper_bound"], 100 / 150)
        self.assertEqual(union["lower_bound"], .5)

    def test_single_pass_and_disagreement_are_unknown(self):
        self.assertEqual(consensus("yes", "no"), "unclear")
        self.assertEqual(consensus("yes", ""), "unclear")
        rows = self.sample()
        rows[0].update(design="yes", review_coverage="single_pass")
        group = summarize_strata(rows)[0]
        self.assertEqual(group["double_coded_yes"], 0)
        self.assertEqual(group["unknown_for_bounds"], 2)

    def test_sampling_counts_and_probabilities_are_checked(self):
        rows = self.sample()
        rows[0]["inclusion_probability"] = .5
        with self.assertRaisesRegex(ValueError, "Sampling probability"):
            summarize_strata(rows)


if __name__ == "__main__":
    unittest.main()
