"""Offline development-only diagnostics; no Scopus-semantic or precision claim."""
from collections import Counter
import csv
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
import query
import query_revision
from common import digest, write_csv, write_json

D = re.compile(r"\b(?:experiment\w*|random\w*|manipulat\w*)\b")
S = re.compile(r"^(?:information|message\w*|text\w*|vignette\w*|scenario\w*|headline\w*|prompt\w*)$")
O = re.compile(r"\b(?:attitud\w*|belief\w*|opinion\w*|perception\w*|judgment\w*|judgement\w*|intention\w*|preference\w*)\b")
A = re.compile(r"^(?:read\w*|view\w*|expos\w*|present\w*|receiv\w*|shown)$")
FIELDS = ("title", "abstract", "keywords", "indexed_keywords")


def tokens(text):
    return re.findall(r"\b\w+\b", re.sub(r"<[^>]*>", " ", query.normalize(text)))


def proximity(text):
    values = tokens(text)
    stimulus = [i for i, t in enumerate(values) if S.fullmatch(t)]
    actions = [i for i, t in enumerate(values) if A.fullmatch(t)]
    # Five or fewer intervening tokens, unordered. This is deliberately labelled
    # an approximation, not asserted to duplicate Scopus W/5 behavior.
    return any(0 < abs(i-j) <= 6 for i in stimulus for j in actions)


def variants(row):
    fields = [query.normalize(row.get(f, "")) for f in FIELDS]
    text = " ".join(fields)
    design_response = bool(D.search(text) and O.search(text))
    stimulus = any(S.fullmatch(t) for f in fields for t in tokens(f))
    concept = design_response and stimulus
    exposure_field = design_response and any(proximity(f) for f in fields)
    exposure_sentence = design_response and any(proximity(unit) for f, unit, original in query.units(row))
    old = bool(query.match(row))
    revised = bool(query.match(row, query_revision.revised_families()))
    return {
        "previous_local_strict": old,
        "revised_local_strict": revised,
        "three_concepts_only": concept,
        "exposure_five_intervening_tokens_same_field_only": exposure_field,
        "exposure_five_intervening_tokens_same_sentence_only": exposure_sentence,
        "revised_or_three_concepts": revised or concept,
        "revised_or_exposure_same_field": revised or exposure_field,
        "revised_or_exposure_same_sentence": revised or exposure_sentence,
        "three_concepts_added_to_revised": concept and not revised,
        "exposure_same_field_added_to_revised": exposure_field and not revised,
        "exposure_same_sentence_added_to_revised": exposure_sentence and not revised,
    }


def run():
    target = ROOT / "results/design_audit_2026_09_10"
    source = ROOT.parent / "Opencall/QueryV2"
    summary, provenance, decisions = [], [], []
    for corpus, filename in [("investigator_development", "positives/mining_input.csv"),
                             ("term_stratified_development", "termeval/term_samples.csv")]:
        datafile = source / filename
        raw = list(csv.DictReader(datafile.open()))
        rows = [r for r in raw if 2010 <= int(r["year"]) <= 2026]
        annotations, paths = {}, [datafile]
        for path in sorted((datafile.parent / "results").glob("*.json")):
            paths.append(path)
            for ann in json.loads(path.read_text()):
                key = str(ann["idx"])
                if key in annotations:
                    raise ValueError("Duplicate annotation index")
                annotations[key] = ann
        records = {r["scopus_id"]: (r, annotations[r["idx"]]) for r in rows if r["idx"] in annotations}
        all_labels = Counter(a.get("is_survey_experiment", "unclear") for r, a in records.values())
        checks = {sid: variants(r) for sid, (r, ann) in records.items()}
        for variant in next(iter(checks.values())):
            ids = [sid for sid, variants_ in checks.items() if variants_[variant]]
            labels = Counter(records[sid][1].get("is_survey_experiment", "unclear") for sid in ids)
            summary.append({"corpus": corpus, "variant": variant,
                            "n_records": len(records), "n_legacy_yes": all_labels["yes"],
                            "n_legacy_no": all_labels["no"],
                            "n_legacy_unclear": len(records)-all_labels["yes"]-all_labels["no"],
                            "n_matched": len(ids), "matched_legacy_yes": labels["yes"],
                            "matched_legacy_no": labels["no"],
                            "matched_legacy_unclear": len(ids)-labels["yes"]-labels["no"],
                            "unmatched_legacy_yes": all_labels["yes"]-labels["yes"],
                            "status": "Development only; inherited AI broad-design labels; not validated precision or recall"})
        for sid, (r, ann) in records.items():
            decisions.append({"corpus": corpus, "scopus_id": sid, "title": r["title"],
                              "legacy_label": ann.get("is_survey_experiment", "unclear"),
                              **{k: str(v).lower() for k, v in checks[sid].items()}})
        provenance.extend({"path": str(path.relative_to(ROOT.parent)), "sha256": digest(path.read_bytes())} for path in paths)
    write_csv(target / "legacy_development_comparison.csv", summary)
    write_csv(ROOT / "private/design_audit_2026_09_10/legacy_development_article_matches.csv", decisions)
    write_json(target / "legacy_development_comparison_provenance.json", {
        "source_files": provenance, "script_sha256": digest(Path(__file__).read_bytes()),
        "previous_query_sha256": digest(query.build()),
        "revised_query_sha256": digest(query.build(query_revision.revised_families())),
        "proximity": "unordered, five or fewer intervening tokens; not a Scopus emulator",
        "design_and_response_scope": "Across title, abstract, keywords; no concatenation for exposure proximity",
    })
    for r in summary:
        print(r["corpus"], r["variant"], r["n_matched"], r["matched_legacy_yes"], r["matched_legacy_no"], r["matched_legacy_unclear"])


if __name__ == "__main__":
    run()
