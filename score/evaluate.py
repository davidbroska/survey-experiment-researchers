"""Compare frozen metadata predictions with substantive, sourced full-text reviews.

Run: python3 score/evaluate.py
AI review agreement is reported separately from human verification.
"""
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
PRIVATE = ROOT / "private/score"
LABELS = ("YES", "NO", "UNCLEAR")
PREDICTION_FILES = ("predictions_original.csv", "predictions_revised.csv")
REVISED_PROMPT_SHA256 = "73957ab52b1a9b7f2a302a36525c677fb217e171bb4e31a2c9854cccb0887aa9"


def read_rows(path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def index_rows(rows, key="article_id"):
    result = {}
    for row in rows:
        article = row[key]
        if not article:
            raise ValueError(f"Empty {key}")
        if article in result:
            raise ValueError(f"Duplicate {key}: {article}")
        result[article] = row
    return result


def proportion(numerator, denominator):
    return float(numerator / denominator) if denominator else None


def validate_decisions(rows):
    for key, row in rows.items():
        collection, experiment, survey = (row.get(field) for field in ("collection", "experiment", "survey"))
        if any(value not in LABELS for value in (collection, experiment, survey)):
            raise ValueError(f"Invalid decision label: {key}")
        if collection == "NO" and (experiment != "NO" or survey != "NO"):
            raise ValueError(f"Ineligible collection has an eligible or unresolved subtype: {key}")
        if collection == "UNCLEAR" and "YES" in (experiment, survey):
            raise ValueError(f"Unresolved collection has an eligible subtype: {key}")


def validate_predictions(predictions, articles, path):
    validate_decisions(predictions)
    if not set(predictions).issubset(articles):
        raise ValueError(f"Predictions outside the current sample: {path.name}")
    if path.name == "predictions_original.csv":
        versions = {"original", "original_with_primary_survey_definition"}
        expected_ids = set(articles)
    else:
        versions = {"revised"}
        expected_ids = {key for key, row in articles.items() if row["split"] == "holdout"}
        prompt = ROOT / "score/prompt_revised.md"
        if hashlib.sha256(prompt.read_bytes()).hexdigest() != REVISED_PROMPT_SHA256:
            raise ValueError("Revised prompt differs from the frozen holdout prompt")
        if any(row.get("prompt_sha256") != REVISED_PROMPT_SHA256 for row in predictions.values()):
            raise ValueError("Revised predictions do not identify the frozen prompt")
        manifest = json.loads((PRIVATE / "predictions_revised_manifest.json").read_text())
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["prediction_sha256"]:
            raise ValueError("Revised predictions differ from their frozen manifest")
    if any(row.get("prompt_version") not in versions for row in predictions.values()):
        raise ValueError(f"Unexpected prompt version in {path.name}")
    if set(predictions) != expected_ids:
        raise ValueError(f"Final prediction file has incomplete or unexpected coverage: {path.name}")


def source_file(value):
    path = Path(value)
    candidates = [path] if path.is_absolute() else [ROOT / path, ROOT.parent / path]
    return next((p for p in candidates if p.is_file()), None)


def validate_reviews(reviews, articles, fulltexts):
    """JSON extracts carry the source document hash, not their own file hash."""
    validate_decisions(reviews)
    for key, row in reviews.items():
        if key not in articles:
            raise ValueError(f"Reference article is outside the current sample: {key}")
        if row.get("doi") and row["doi"].lower() != articles[key].get("doi", "").lower():
            raise ValueError(f"Reference DOI differs from the sample: {key}")
        if not row.get("source_path") or not row.get("rationale"):
            raise ValueError(f"Full-text review lacks source or rationale: {key}")
        source = source_file(row["source_path"])
        expected = row.get("source_sha256", "")
        if source is None or len(expected) != 64:
            raise ValueError(f"Reference source is missing or has no SHA-256: {key}")
        if source.suffix.lower() == ".json":
            cached = json.loads(source.read_text())
            if cached.get("source_sha256") != expected or not cached.get("pages"):
                raise ValueError(f"Reference text cache has a different source or no pages: {key}")
            document = fulltexts.get(key, {}).get("fulltext_path", "")
            original = source_file(document) if document else None
            if original is None:
                filename = cached.get("filename", "")
                original = source.parent.parent / "inbox" / filename if filename else None
            source = original
        if source is None or not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Reference document is missing or differs from its SHA-256: {key}")
        if any(row.get(field) not in LABELS for field in ("collection", "experiment", "survey")):
            raise ValueError(f"Invalid reference label: {key}")
        if row.get("human_verified", "false").lower() not in {"true", "false"}:
            raise ValueError(f"Invalid human-verification flag: {key}")


def compare(predictions, reviews, field):
    """Exclude unresolved reference labels from binary performance denominators."""
    paired = [key for key in predictions if key in reviews]
    truth = np.array([reviews[key].get(field, "") for key in paired])
    predicted = np.array([predictions[key].get(field, "") for key in paired])
    all_predictions = np.array([row.get(field, "") for row in predictions.values()])
    if not set(truth).issubset(LABELS) or not set(all_predictions).issubset(LABELS):
        raise ValueError(f"Invalid {field} labels")
    resolved = np.isin(truth, ["YES", "NO"])
    positive = truth == "YES"
    negative = truth == "NO"
    retained = predicted != "NO"
    yes = predicted == "YES"
    no = predicted == "NO"
    matrix = [[int(np.sum((truth == a) & (predicted == b))) for b in LABELS]
              for a in LABELS]
    return {
        "predicted": len(predictions),
        "paired": len(paired),
        "without_reference": len(predictions) - len(paired),
        "retained_all_predictions": int(np.sum(all_predictions != "NO")),
        "retention_fraction_all_predictions": proportion(np.sum(all_predictions != "NO"), len(predictions)),
        "unclear_all_predictions": int(np.sum(all_predictions == "UNCLEAR")),
        "abstention_rate_all_predictions": proportion(np.sum(all_predictions == "UNCLEAR"), len(predictions)),
        "resolved_reference": int(resolved.sum()),
        "unresolved_reference": int((truth == "UNCLEAR").sum()),
        "confusion_matrix": matrix,
        "matrix_labels": list(LABELS),
        "matrix_rows": "fulltext", "matrix_columns": "metadata",
        "yes_precision_resolved": proportion(np.sum(yes & positive), np.sum(yes & resolved)),
        "yes_precision_denominator": int(np.sum(yes & resolved)),
        "yes_recall": proportion(np.sum(yes & positive), positive.sum()),
        "retention_recall": proportion(np.sum(retained & positive), positive.sum()),
        "retention_recall_denominator": int(positive.sum()),
        "retention_precision_resolved": proportion(np.sum(retained & positive), np.sum(retained & resolved)),
        "discard_specificity": proportion(np.sum(no & negative), negative.sum()),
        "discard_specificity_denominator": int(negative.sum()),
        "false_negatives": [key for key, flag in zip(paired, no & positive) if flag],
        "metadata_unclear": int(np.sum(predicted == "UNCLEAR")),
        "exact_agreement_resolved": proportion(np.sum((truth == predicted) & resolved), resolved.sum()),
    }


def main():
    articles = index_rows(read_rows(ROOT / "score/articles.csv"))
    reviews = index_rows(read_rows(PRIVATE / "fulltext_reviews.csv"))
    fulltexts = index_rows(read_rows(PRIVATE / "fulltext.csv"))
    validate_reviews(reviews, articles, fulltexts)
    reports = []
    for filename in PREDICTION_FILES:
        path = PRIVATE / filename
        if not path.exists():
            continue
        predictions = index_rows(read_rows(path))
        validate_predictions(predictions, articles, path)
        for split in ("development", "holdout"):
            selected = {key: row for key, row in predictions.items()
                        if articles[key]["split"] == split}
            if not selected:
                continue
            result = {"prediction_file": path.name, "split": split,
                      "predicted": len(selected),
                      "sample_articles_in_split": sum(row["split"] == split for row in articles.values()),
                      "reference": "AI full-text review",
                      "collection": compare(selected, reviews, "collection"),
                      "experiment": compare(selected, reviews, "experiment"),
                      "survey": compare(selected, reviews, "survey")}
            reports.append(result)
    report = {
        "planned_articles": 620, "sampled_articles": len(articles),
        "fulltext_reviews": len(reviews),
        "human_verified": sum(row.get("human_verified", "false").lower() == "true"
                              for row in reviews.values()),
        "interpretation": "Agreement with AI full-text review; not human-validated accuracy. "
                          "Available paired cases may differ from inaccessible or unreviewed cases. "
                          "The pilot retains matching existing articles, so it is not a probability sample.",
        "evaluations": reports,
    }
    target = ROOT / "score/evaluation.json"
    target.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Saved {target.name}: {len(reviews)} full-text reviews, {len(reports)} comparisons.")


if __name__ == "__main__":
    main()
