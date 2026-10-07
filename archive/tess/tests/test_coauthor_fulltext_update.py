import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import coauthor_fulltext_update as update


class CoauthorImportTests(unittest.TestCase):
    def test_root_source_is_removed_only_after_identical_archive_exists(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "paper.pdf"
            source.write_bytes(b"supplied document")
            private = root / "private/update"
            with patch.object(update, "ROOT", root), patch.object(update, "PRIVATE", private):
                target, sha = update.archive_pdf(source)
                self.assertFalse(source.exists())
                self.assertEqual(target.read_bytes(), b"supplied document")
                self.assertEqual(update.digest(target.read_bytes()), sha)
                # A second copy with the same filename cannot replace old bytes.
                source.write_bytes(b"a different supplied document")
                other, _ = update.archive_pdf(source)
                self.assertNotEqual(target, other)
                self.assertEqual(target.read_bytes(), b"supplied document")
                self.assertEqual(other.read_bytes(), b"a different supplied document")

    def test_non_root_original_cannot_be_deleted(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "unrelated/paper.pdf"
            source.parent.mkdir()
            source.write_bytes(b"unrelated source")
            with patch.object(update, "ROOT", root), patch.object(update, "PRIVATE", root / "private/update"):
                with self.assertRaises(ValueError):
                    update.archive_pdf(source)
                self.assertTrue(source.exists())

    def test_issued_review_packet_cannot_change(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "packet.json"
            original = [{"scopus_id": "1", "source_sha256": "original source"}]
            update.write_immutable(path, original)
            with self.assertRaises(ValueError):
                update.write_immutable(path, [{"scopus_id": "1", "source_sha256": "different source"}])
            self.assertEqual(json.loads(path.read_text()), original)


if __name__ == "__main__":
    unittest.main()
