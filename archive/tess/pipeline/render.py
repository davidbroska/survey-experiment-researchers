"""Small HTML renderer for the paragraphs, tables and code in generated reports."""
import html
import re


def inline(text):
    # Escape source before adding the limited markup emitted by reports.py.
    text = html.escape(text, quote=True)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    return re.sub(r'\[([^\]]+)\]\(([^\s)]+)\)', r'<a href="\2">\1</a>', text)


def render(text, title):
    output, paragraph, code = [], [], None
    table = False

    def flush():
        if paragraph:
            output.append('<p>' + inline(' '.join(paragraph)) + '</p>')
            paragraph.clear()

    for line in text.splitlines():
        if line.startswith('```'):
            flush()
            if code is None:
                code = []
            else:
                output.append('<pre><code>' + html.escape('\n'.join(code)) + '</code></pre>')
                code = None
            continue
        if code is not None:
            code.append(line)
            continue
        if line.startswith('|'):
            flush()
            cells = [v.strip() for v in line.strip().strip('|').split('|')]
            if all(re.fullmatch(r':?-+:?', v) for v in cells):
                continue
            tag = 'td' if table else 'th'
            if not table:
                output.append('<div class="scroll"><table>')
                table = True
            output.append('<tr>' + ''.join(f'<{tag}>' + inline(v) + f'</{tag}>' for v in cells) + '</tr>')
            continue
        if table:
            output.append('</table></div>')
            table = False
        if line.strip():
            paragraph.append(line)
        else:
            flush()
    flush()
    if code is not None:
        raise ValueError('Unclosed report code fence')
    if table:
        output.append('</table></div>')
    return (f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>'
            '<style>body{font:16px/1.6 system-ui,sans-serif;max-width:1080px;margin:3rem auto;padding:0 1rem;color:#192b36}h1{line-height:1.2}a{color:#136294}'
            'pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f0f5f8;padding:1.2rem;font-size:13px}code{font-family:ui-monospace,monospace}'
            'table{border-collapse:collapse;width:100%}th,td{text-align:left;border-bottom:1px solid #dbe3e8;padding:.5rem}.scroll{overflow:auto}</style>'
            f'<h1>{html.escape(title)}</h1>' + '\n'.join(output) + '</html>\n')
