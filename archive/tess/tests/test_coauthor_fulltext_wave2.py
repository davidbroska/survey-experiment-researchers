from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import coauthor_fulltext_wave2 as wave
from precision_benchmark import identity


class CoauthorWaveTwoTests(unittest.TestCase):
    def test_namespace_restores_prior_importer_after_failure(self):
        before = wave.prior.PRIVATE, wave.prior.RESULTS, wave.prior.identity
        with self.assertRaises(RuntimeError):
            with wave.namespace():
                self.assertEqual(wave.prior.PRIVATE, wave.PRIVATE)
                self.assertNotEqual(wave.prior.PRIVATE, before[0])
                raise RuntimeError("synthetic import failure")
        self.assertEqual((wave.prior.PRIVATE, wave.prior.RESULTS, wave.prior.identity), before)

    def test_cached_identity_matches_original_rules_for_multiple_documents(self):
        matcher = wave.cached_identity()
        articles = [
            {"title": "A randomized survey of policy information", "doi": "10.1234/policy"},
            {"title": "Café choices and environmental preferences", "doi": "https://doi.org/10.1234/cafe"},
            {"title": "Unrelated research article with different content", "doi": "10.1234/other"},
        ]
        documents = [
            ["A randomized survey of policy information. Author manuscript."],
            ["Café choices and environmental preferences. DOI: 10.1234/cafe"],
            ["Policy information in a randomized survey. DOI: 10.1234/policy"],
            ["Unrelated short source without title or matching DOI"],
        ]
        for pages in documents:
            for article in articles:
                self.assertEqual(matcher(pages, article), identity(pages, article))
        # Repeated calls must retain document-specific opening text.
        for pages in reversed(documents):
            for article in articles:
                self.assertEqual(matcher(pages, article), identity(pages, article))


if __name__ == "__main__":
    unittest.main()
