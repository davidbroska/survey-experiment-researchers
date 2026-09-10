from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import coauthor_fulltext_wave3 as wave


class CoauthorWaveThreeTests(unittest.TestCase):
    def test_nested_namespace_restores_both_prior_waves_on_failure(self):
        workflow = wave.workflow
        base = workflow.prior
        outer = workflow.PRIVATE, workflow.RESULTS, workflow.REVIEWERS
        inner = base.PRIVATE, base.RESULTS, base.identity
        with self.assertRaises(RuntimeError):
            with wave.namespace():
                self.assertEqual(workflow.REVIEWERS, ("root", "participant"))
                with workflow.namespace():
                    self.assertEqual(base.PRIVATE, wave.PRIVATE)
                    self.assertEqual(base.RESULTS, wave.RESULTS)
                    raise RuntimeError("synthetic extraction failure")
        self.assertEqual((workflow.PRIVATE, workflow.RESULTS, workflow.REVIEWERS), outer)
        self.assertEqual((base.PRIVATE, base.RESULTS, base.identity), inner)


if __name__ == "__main__":
    unittest.main()
