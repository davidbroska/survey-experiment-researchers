"""Use one Markdown prompt for one article; keep identifiers in code.

Session agents perform annotation; this module makes no paid API calls.
"""
import csv
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRIVATE = ROOT / "private/score"
PROMPT = ROOT / "score/prompt.md"
LABELS = ("YES", "NO", "UNCLEAR")


def article_input(article):
    keywords = article.get("keywords", "")
    if isinstance(keywords, str):
        keywords = [word.strip() for word in keywords.split("|") if word.strip()]
    return {"journal_title": article.get("journal_title", article.get("journal", "")),
            "title": article.get("title", ""), "abstract": article.get("abstract", ""),
            "keywords": keywords}


def abstract_prompt(article):
    """Return the exact screening instructions and one four-field input."""
    return PROMPT.read_text(), json.dumps(article_input(article), ensure_ascii=False)


def fulltext_prompt(article, pages):
    """Adapt only the input and output; eligibility rules share the same source."""
    prompt = PROMPT.read_text()
    introduction, criteria = prompt.split("\n\n", 1)
    definitions = prompt.split("YES: ", 1)[1].split("\n# Input supplied by code", 1)[0].strip()
    criteria = criteria.split("\n# Output\n", 1)[0]
    prompt = ("Inspect this article's full text and relevant supporting materials to decide "
              "whether its research team collected or commissioned participant responses "
              "through a survey or survey experiment used in the research reported in the article.\n\n"
              + criteria + "\n\n# Output\n\n"
              "Return one JSON object with annotation (YES, NO or UNCLEAR), evidence "
              "(short source excerpts with page or section references, at most 25 quoted words "
              "in total per source), and reasoning. Inspect all reported study components "
              "before assigning NO. Follow supporting sources when needed to resolve "
              "collection responsibility or questionnaire use; distinguish sources inspected "
              "from sources merely linked. If the available sources cannot resolve eligibility, "
              "return UNCLEAR and explain the missing information.\n\nYES: " + definitions)
    payload = {"journal_title": article.get("journal", ""), "title": article.get("title", ""),
               "pages": [{"page_or_segment": i + 1, "text": page}
                         for i, page in enumerate(pages)]}
    return prompt, json.dumps(payload, ensure_ascii=False)


def save_prediction(article, response, reviewer, destination):
    """Validate one label and attach provenance outside the model response."""
    label = response.strip()
    if label not in LABELS:
        raise ValueError("Expected exactly YES, NO or UNCLEAR")
    _, payload = abstract_prompt(article)
    row = {"article_id": article["article_id"], "annotation": label,
           "prompt_sha256": hashlib.sha256(PROMPT.read_bytes()).hexdigest(),
           "input_sha256": hashlib.sha256(payload.encode()).hexdigest(),
           "reviewer": reviewer, "model": "Codex session agent (GPT-6 family)",
           "annotated_at": datetime.now(timezone.utc).isoformat(), "raw_response": label}
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        with destination.open(newline="") as handle:
            existing = list(csv.DictReader(handle))
        if any(old["article_id"] == row["article_id"] for old in existing):
            raise ValueError("This article already has a saved prediction")
    with destination.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        if handle.tell() == 0:
            writer.writeheader()
        writer.writerow(row)


def annotate_abstract(article, model):
    """Call an authorized model callable and require its single-label response."""
    instructions, payload = abstract_prompt(article)
    response = model(instructions, payload).strip()
    if response not in LABELS:
        raise ValueError("Expected exactly YES, NO or UNCLEAR")
    return response


def main():
    parser = argparse.ArgumentParser(description="Show one article, then save its single-label response.")
    parser.add_argument("--batch", required=True)
    parser.add_argument("--label", choices=LABELS)
    args = parser.parse_args()
    folder = PRIVATE / "annotation_batches"
    ids = json.loads((folder / f"{args.batch}.json").read_text())
    destination = folder / f"{args.batch}.csv"
    with (PRIVATE / "articles.csv").open(newline="") as handle:
        articles = {row["article_id"]: row for row in csv.DictReader(handle)}
    if destination.exists():
        with destination.open(newline="") as handle:
            done = {row["article_id"] for row in csv.DictReader(handle)}
    else:
        done = set()
    pending = [key for key in ids if key not in done]
    if args.label:
        if not pending:
            raise ValueError("Batch already complete")
        save_prediction(articles[pending[0]], args.label, args.batch, destination)
        pending.pop(0)
    if pending:
        print(abstract_prompt(articles[pending[0]])[1])
    else:
        print(f"Complete: {len(ids)} articles recorded.")


if __name__ == "__main__":
    main()
