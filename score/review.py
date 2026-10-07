"""Combine reviewed batches and export derived labels without licensed text.

Run this before evaluate.py and dashboard.py. Never infer labels from access status.
"""
import csv
from pathlib import Path
import re
from urllib.parse import parse_qsl, urlsplit
from fetch_fulltext import PRIVATE_QUERY, safe_url

ROOT = Path(__file__).resolve().parent.parent
PRIVATE = ROOT / "private/score"
BATCHES = ("initial", "business", "education", "remaining", "psychology",
           "root_extra", "holdout_business", "social", "holdout_social", "pmc_additions")


def public_urls(value):
    """Remove access queries without changing other links in a multi-URL field."""
    def clean(match):
        url = match.group()
        parts = urlsplit(url)
        private_query = any(re.search(PRIVATE_QUERY, key, re.I)
            for key, _ in parse_qsl(parts.query, keep_blank_values=True))
        private_fragment = any(re.search(PRIVATE_QUERY, key, re.I)
            for key, _ in parse_qsl(parts.fragment, keep_blank_values=True))
        if not (parts.username or parts.password or private_query or private_fragment):
            return url
        fragment = '#' + parts.fragment if parts.fragment and not private_fragment else ''
        return safe_url(url) + fragment
    return re.sub(r'https?://[^\s<>;]+', clean, value)


def read_rows(path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_rows(path, rows, fields):
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def main():
    articles = {r["article_id"]: r for r in read_rows(PRIVATE / "articles.csv")}
    reviews = {}
    fields = []
    for batch in BATCHES:
        for row in read_rows(PRIVATE / f"fulltext_reviews_{batch}.csv"):
            key = row["article_id"]
            if key not in articles or key in reviews:
                raise ValueError(f"Outside-sample or duplicate reference: {key}")
            row["split"] = articles[key]["split"]
            reviews[key] = row
            fields += [field for field in row if field not in fields]
    for change in read_rows(PRIVATE / "adjudications.csv"):
        row = reviews[change["article_id"]]
        field = change["field"]
        if row[field] != change["previous_value"]:
            raise ValueError(f"Adjudication no longer matches {row['article_id']}")
        row[field] = change["new_value"]
        row["rationale"] += " Adjudication: " + change["rationale"]
        row["confidence"] = change.get("confidence", row["confidence"])
    rows = sorted(reviews.values(), key=lambda r: (r["journal"], r["year"]))
    write_rows(PRIVATE / "fulltext_reviews.csv", rows, fields)
    public_fields = ("article_id", "doi", "journal", "year", "title", "collection",
                     "experiment", "survey", "other_methods", "review_status", "confidence",
                     "reviewer", "review_date", "human_verified", "split", "source_url",
                     "pdf_pages_reviewed", "evidence_section", "rationale", "recruitment_providers",
                     "software", "team_data_reuse", "supporting_resource_url", "supporting_resource_status")
    public_rows = []
    for row in rows:
        public = {field: row.get(field, "") for field in public_fields}
        if not public["source_url"].startswith(("https://", "http://")):
            public["source_url"] = "https://doi.org/" + row["doi"]
        for field in ("source_url", "supporting_resource_url"):
            public[field] = public_urls(public[field])
        public_rows.append(public)
    write_rows(ROOT / "score/independent_review.csv", public_rows, public_fields)
    prediction_fields = ("article_id", "prompt_version", "collection", "experiment",
                         "survey", "other_methods", "rationale", "software",
                         "recruitment_providers", "reviewer")
    for version in ("original", "revised"):
        predictions = read_rows(PRIVATE / f"predictions_{version}.csv")
        write_rows(ROOT / f"score/predictions_{version}.csv", predictions, prediction_fields)
    print(f"Combined {len(rows)} sourced reviews; exported derived labels and paraphrases.")


if __name__ == "__main__":
    main()
