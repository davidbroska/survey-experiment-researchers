import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import proximity_audit as audit


class ProximityAuditTests(unittest.TestCase):
    def test_fixed_sample_excludes_prior_aliases_and_cannot_change_denominators(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            results, private, old = root / "results", root / "private", root / "old"
            groups = (("true", "false"), ("false", "true"), ("true", "true"))
            rows = []
            for g, (primary, clause) in enumerate(groups):
                for i in range(30):
                    sid = str(1000 + g*100 + i)
                    rows.append({"scopus_id":sid,"doi":"10.test/"+sid,"title":"Study "+sid,
                        "all_scopus_ids":sid+"|"+str(int(sid)+10000),"identity":"doi:10.test/"+sid,
                        "targeted":"true","previous_primary":primary,"grouped_clause":clause})
            audit.write_csv(results / "membership.csv", rows)
            audit.write_csv(old / "validation_sample.csv", [{"scopus_id":"11000","doi":"","title":""}])
            audit.write_csv(old / "lost_record_review.csv", [], ["scopus_id","doi","title"])
            audit.write_csv(private / "author_bibliographies/author_articles.csv", [], ["scopus_id","doi","title"])
            audit.write_csv(root / "inputs/fulltext_reviews.csv", [], ["scopus_id"])
            protocol = {"query_sha256":{"targeted":"frozen"},"frame_sha256":"frame"}
            with patch.multiple(audit, ROOT=root, RESULTS=results, PRIVATE=private), \
                 patch.object(audit.previous,"RESULTS",old), \
                 patch.object(audit.previous,"frozen_exclusions",return_value=[]), \
                 patch.object(audit,"freeze",return_value=protocol):
                audit.fulltext_sample()
                sample = audit.read_csv(results / "fulltext_sample.csv")
                self.assertEqual(len(sample),60)
                self.assertNotIn("1000",{r["scopus_id"] for r in sample})
                first = [r for r in sample if r["stratum"] == "primary_only"]
                self.assertEqual({r["stratum_N"] for r in first},{"29"})
                self.assertEqual({float(r["inclusion_probability"]) for r in first},{20/29})
                before = (results / "fulltext_sample.csv").read_bytes()
                audit.fulltext_sample()
                self.assertEqual(before,(results / "fulltext_sample.csv").read_bytes())
                audit.write_csv(results / "membership.csv", rows[:-1])
                with self.assertRaisesRegex(ValueError,"Frozen sample"):
                    audit.fulltext_sample()

    def test_author_aliases_are_counted_once_and_incomplete_bylines_not_credited(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            members = []
            for sid in ("1","3"):
                r = {"scopus_id":sid,"doi":"10.test/"+sid,"all_scopus_ids":"1|2" if sid=="1" else "3","identity":"doi:10.test/"+sid}
                r.update({k:"true" for k in ("previous_expanded","previous_primary","previous_candidate","grouped_clause","targeted","minimal","candidate_plus_clause")})
                members.append(r)
            audit.write_csv(root / "membership.csv",members)
            authors = [{"scopus_id":sid,"doi":"10.test/1" if sid in ("1","2") else "10.test/3",
                "focal_author_name":"Researcher","first_or_last":"true","byline_complete":"false" if sid=="3" else "true"} for sid in ("1","2","3")]
            audit.write_csv(root / "author_bibliographies/author_articles.csv",authors)
            with patch.multiple(audit,RESULTS=root,PRIVATE=root):
                audit.author_comparison()
            for row in audit.read_csv(root / "author_comparison.csv"):
                self.assertEqual(row["any_author_position"],"2")
                self.assertEqual(row["first_last_candidate_articles"],"1")


if __name__ == "__main__":
    unittest.main()
