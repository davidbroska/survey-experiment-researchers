"""Validate and combine fresh annotations; publish derived results only."""
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import parse_qsl, urlsplit
from annotate import ROOT, PRIVATE, PROMPT, LABELS, abstract_prompt, fulltext_prompt
from common import PRIVATE_QUERY, safe_url


def read_rows(path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_rows(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def index_rows(rows):
    indexed = {row["article_id"]: row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError("Duplicate article identifiers")
    return indexed


def public_text(value):
    def clean(match):
        url = match.group()
        parts = urlsplit(url)
        sensitive = any(re.search(PRIVATE_QUERY, key, re.I)
                        for key, _ in parse_qsl(parts.query + "&" + parts.fragment))
        return safe_url(url) if sensitive or parts.username else url
    return re.sub(r'''https?://[^\s<>"']+''', clean, value)


def validate_evidence(evidence):
    if isinstance(evidence, str):
        evidence = json.loads(evidence)
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("Evidence must be a nonempty list")
    counts = {}
    for item in evidence:
        if not isinstance(item, dict) or not {'quote', 'location', 'source'}.issubset(item):
            raise ValueError("Evidence needs quote, location and source")
        if any(not isinstance(item[key], str) or not item[key].strip() for key in ['quote', 'location', 'source']):
            raise ValueError("Evidence fields must be nonempty strings")
        source = item['source']
        if source != 'main' and not source.startswith(('https://', 'http://')):
            raise ValueError("Supporting evidence must identify a public source URL")
        counts[source] = counts.get(source, 0) + len(item['quote'].split())
    if any(count > 25 for count in counts.values()):
        raise ValueError("More than 25 quoted words from one source")
    return evidence


def validate_source_quotes(evidence, source):
    quotes = [item['quote'] for item in evidence if item['source'] == 'main']
    normalize = lambda value: ' '.join(value.replace('\u00ad', '').split())
    cached = json.loads(Path(source['text_cache']).read_text())
    text = normalize(' '.join(cached['pages']))
    missing = [quote for quote in quotes if normalize(quote) not in text]
    if missing and source['format'].lower() == 'pdf':
        # Layout extraction sometimes interleaves two columns. Check reading order too.
        text = subprocess.check_output(['pdftotext', source['fulltext_path'], '-'], text=True, stderr=subprocess.PIPE)
        missing = [quote for quote in missing if normalize(quote) not in normalize(text)]
    if missing:
        raise ValueError('Evidence quote does not match the main document')


def main():
    articles = index_rows(read_rows(PRIVATE / "articles.csv"))
    access = index_rows(read_rows(PRIVATE / "fulltext.csv"))
    prompt_hash = hashlib.sha256(PROMPT.read_bytes()).hexdigest()
    folder = PRIVATE / "annotation_batches"
    predictions = index_rows([row for path in sorted(folder.glob("abstract_*.csv"))
                              for row in read_rows(path)])
    references = index_rows([row for path in sorted(folder.glob("fulltext_*.csv"))
                             for row in read_rows(path)])
    for key, row in predictions.items():
        if key not in articles or row["annotation"] not in LABELS:
            raise ValueError("Invalid prediction")
        _, payload = abstract_prompt(articles[key])
        if row["prompt_sha256"] != prompt_hash or row["input_sha256"] != hashlib.sha256(payload.encode()).hexdigest():
            raise ValueError("Prediction prompt or input changed")
    for key, row in references.items():
        if key not in articles or row["annotation"] not in LABELS or not row["reasoning"] or not row["evidence"]:
            raise ValueError("Invalid source review")
        validate_source_quotes(validate_evidence(row['evidence']), access[key])
        if row["prompt_sha256"] != prompt_hash or row["source_sha256"] != access[key]["source_sha256"]:
            raise ValueError("Source review prompt or document differs")
        instructions, _ = fulltext_prompt(articles[key], [])
        if row["instructions_sha256"] != hashlib.sha256(instructions.encode()).hexdigest():
            raise ValueError("Full-text review instructions changed")
        source = Path(access[key]["fulltext_path"])
        if hashlib.sha256(source.read_bytes()).hexdigest() != row["source_sha256"]:
            raise ValueError("Source document changed")
    changes = read_rows(PRIVATE / "review_adjudications.csv")
    for change in changes:
        row = references[change["article_id"]]
        if row["annotation"] != change["previous_annotation"]:
            raise ValueError("Adjudication does not match initial review")
        if change['annotation'] not in LABELS or not change['reasoning'].strip():
            raise ValueError("Invalid adjudicated judgment")
        validate_source_quotes(validate_evidence(change['evidence']), access[change['article_id']])
        if change['source_sha256'] != row['source_sha256'] or not change['reviewed_at'] or not change['reviewer']:
            raise ValueError("Adjudication requires matching source and reviewer/date provenance")
        row["annotation"] = change["annotation"]
        row["evidence"] = change["evidence"]
        row["reasoning"] = change["reasoning"]
        row["adjudicator"] = change["reviewer"]
        row["adjudicated_at"] = change["reviewed_at"]
    ordering = lambda key: (articles[key]["journal"], -int(articles[key]["year"]), articles[key]["title"])
    for name, data in [("predictions", predictions), ("fulltext_reviews", references)]:
        rows = [data[key] for key in sorted(data, key=ordering)]
        fields = list(dict.fromkeys(field for row in rows for field in row))
        write_rows(PRIVATE / (name + ".csv"), rows, fields or ['article_id', 'annotation', 'evidence', 'reasoning'])
        public = []
        for key in sorted(data, key=ordering):
            row = {field: articles[key][field] for field in ["article_id", "doi", "journal", "year", "title"]}
            row["annotation"] = data[key]["annotation"]
            if name == "fulltext_reviews":
                row["evidence"] = public_text(data[key]["evidence"])
                row["reasoning"] = public_text(data[key]["reasoning"])
            public.append(row)
        public_fields = ["article_id", "doi", "journal", "year", "title", "annotation"]
        if name == "fulltext_reviews":
            public_fields += ["evidence", "reasoning"]
        write_rows(ROOT / "score" / (name + ".csv"), public, public_fields)
    print(f"Validated {len(predictions)}/620 abstract labels and {len(references)}/620 full-text reviews.")


if __name__ == "__main__":
    main()
