"""Guard against saving login pages or unrelated PDFs as article full texts."""
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pipeline'))
from open_access import PDFLinks, pdf_identity, is_supplement
from acquisition_report import enrich_queue
from common import digest, write_csv


class AcquisitionTests(unittest.TestCase):
    def test_html_response_is_not_a_pdf(self):
        ok, reason, pages = pdf_identity(b'<html>Please sign in</html>', {'scopus_id':'1','title':'A specific experimental study','doi':'10.1/example'})
        self.assertFalse(ok)
        self.assertEqual(reason, 'not_pdf')

    def test_unrelated_pdf_is_rejected_and_matching_title_is_accepted(self):
        with tempfile.TemporaryDirectory() as d, patch('open_access.OA_ROOT', Path(d)):
            a = {'scopus_id':'1','title':'Policy information and experimental voter preferences','doi':'10.1/example'}
            with patch('open_access.extract', return_value=(['An unrelated paper about astronomy'], 'test')):
                self.assertFalse(pdf_identity(b'%PDF-1.7 fake',a)[0])
            with patch('open_access.extract', return_value=([a['title'],'Methods','Results'], 'test')):
                self.assertTrue(pdf_identity(b'%PDF-1.7 fake',a)[0])
            with patch('open_access.extract', return_value=([a['title']], 'test')):
                self.assertEqual(pdf_identity(b'%PDF-1.7 fake',a)[1], 'short_pdf_needs_manual_completeness_check')

    def test_supplement_and_repository_links_are_identified(self):
        self.assertTrue(is_supplement('https://example.edu/paper_sup001.pdf'))
        self.assertTrue(is_supplement('https://example.edu/paper.pdf',['Online Appendix for the paper']))
        self.assertFalse(is_supplement('https://example.edu/article.pdf',['Research article']))
        p = PDFLinks();p.feed('<meta name="citation_pdf_url" content="/article.pdf"><a href="/bitstreams/123/download">PDF</a>')
        self.assertEqual(p.links, ['/article.pdf','/bitstreams/123/download'])

    def test_acquisition_hash_does_not_substitute_for_a_present_file(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root/'private/fulltext/inbox').mkdir(parents=True)
            data = b'%PDF-1.7 fixture'
            write_csv(root/'results/open_access_acquisition.csv',[{'scopus_id':'1','source_sha256':digest(data),'downloaded_filename':'1.pdf'}])
            queue=[{'scopus_id':'1','article_url':'https://doi.org/10.1/example','sample_us_label':'unclear'}]
            self.assertEqual(enrich_queue(queue,root)[0]['local_pdf_available'],'false')
            (root/'private/fulltext/inbox/1.pdf').write_bytes(data)
            self.assertEqual(enrich_queue(queue,root)[0]['local_pdf_available'],'true')
            self.assertEqual(enrich_queue(queue,root)[0]['sample_us_label'],'unclear')
            (root/'private/fulltext/inbox/1.pdf').write_bytes(b'%PDF-1.7 changed')
            with self.assertRaisesRegex(ValueError,'changed'):
                enrich_queue(queue,root)


if __name__ == '__main__':
    unittest.main()
