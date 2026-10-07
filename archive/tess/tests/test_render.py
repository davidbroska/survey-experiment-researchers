import sys
from pathlib import Path
from html.parser import HTMLParser
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pipeline'))
from render import render
import query


class CodeText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inside = False
        self.text = ''

    def handle_starttag(self, tag, attrs):
        if tag == 'pre':
            self.inside = True

    def handle_endtag(self, tag):
        if tag == 'pre':
            self.inside = False

    def handle_data(self, text):
        if self.inside:
            self.text += text


class ReportRenderTest(unittest.TestCase):
    def test_executed_query_preserved_in_html(self):
        parser = CodeText()
        parser.feed(render('```text\n' + query.build() + '\n```', 'Query'))
        self.assertEqual(parser.text, query.build())

    def test_text_escaped_and_source_link_retained(self):
        result = render('<script>untrusted</script> [Source](https://example.org/?a=1&b=2)', 'Title')
        self.assertNotIn('<script>', result)
        self.assertIn('href="https://example.org/?a=1&amp;b=2"', result)


if __name__ == '__main__':
    unittest.main()
