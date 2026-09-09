"""Exploratory comparisons with inherited machine annotations, never a holdout."""
from collections import Counter
import json
import math

from common import ROOT, REPO, read_csv, write_csv, write_json, digest
import query


def wilson(positive, total):
    if total == 0:
        return "", "", ""
    z = 1.959963984540054
    p = positive / total
    denom = 1 + z*z/total
    centre = (p + z*z/(2*total))/denom
    half = z * math.sqrt(p*(1-p)/total + z*z/(4*total*total))/denom
    return p, max(0, centre-half), min(1, centre+half)


def benchmark():
    reports, family_rows, examples, provenance = [], [], [], []
    for corpus, data_name in [("investigator_development", "positives/mining_input.csv"),
                              ("term_stratified_development", "termeval/term_samples.csv")]:
        base = REPO / "Opencall" / "QueryV2"
        data = read_csv(base / data_name)
        data = [r for r in data if query.START_YEAR <= int(r["year"]) <= query.END_YEAR]
        annotations = {}
        files = [base / data_name]
        for path in sorted((base / data_name.split('/')[0] / "results").glob("*.json")):
            files.append(path)
            for r in json.loads(path.read_text()):
                if str(r["idx"]) in annotations:
                    raise RuntimeError(f"Duplicate legacy annotation index {r['idx']}")
                annotations[str(r["idx"])] = r
        records = {}
        for row in data:
            if row["idx"] in annotations:
                records[row["scopus_id"]] = (row, annotations[row["idx"]])
        positives = sum(a.get("is_survey_experiment") == "yes" for r, a in records.values())
        matches = {sid: query.match(r) for sid, (r, a) in records.items()}
        baseline = {sid: query.baseline_match(r) for sid, (r, a) in records.items()}
        variants = {
            "user_terms_local": lambda sid: baseline[sid],
            "exact_core_local": lambda sid: any(h["family"] in {f["id"] for f in query.FAMILIES if f["role"] != "expansion"} for h in matches[sid]),
            "recommended_local": lambda sid: bool(matches[sid]),
            "recommended_added_vs_user_local": lambda sid: bool(matches[sid]) and not baseline[sid],
        }
        for name, fn in variants.items():
            ids = [sid for sid in records if fn(sid)]
            labels = Counter(records[sid][1].get("is_survey_experiment", "unclear") for sid in ids)
            yes, no = labels["yes"], labels["no"]
            p, lo, hi = wilson(yes, yes+no)
            reports.append({"corpus": corpus, "variant": name, "n_records": len(records),
                "n_labelled_positive": positives, "n_matched": len(ids), "yes": yes, "no": no,
                "unclear": len(ids)-yes-no, "label_agreement_precision_known": p,
                "wilson_lower_descriptive": lo, "wilson_upper_descriptive": hi,
                "positive_capture": yes/positives if positives else "",
                "status": "Exploratory broad-survey LLM labels; nonprobability sample; not parser compatibility or data access"})
        for family in query.FAMILIES:
            ids = [sid for sid in records if not baseline[sid] and any(h["family"] == family["id"] for h in matches[sid])]
            labels = Counter(records[sid][1].get("is_survey_experiment", "unclear") for sid in ids)
            family_rows.append({"corpus": corpus, "family": family["id"], "added_vs_user": len(ids),
                "yes": labels["yes"], "no": labels["no"], "unclear": len(ids)-labels["yes"]-labels["no"],
                "note": "Families overlap; not additive; no corpus precision estimate"})
            for sid in ids:
                row, ann = records[sid]
                hit = next(h for h in matches[sid] if h["family"] == family["id"])
                examples.append({"corpus": corpus, "family": family["id"], "scopus_id": sid,
                    "title": row["title"], "label": ann.get("is_survey_experiment", "unclear"),
                    "evidence": hit["evidence"]})
        provenance.extend({"source": str(p.relative_to(REPO)), "sha256": digest(p.read_bytes())} for p in files)
    write_csv(ROOT / "results" / "exploratory_comparison.csv", reports)
    write_csv(ROOT / "results" / "exploratory_expansion_yield.csv", family_rows)
    write_csv(ROOT / "private" / "exploratory_examples.csv", examples)
    write_json(ROOT / "results" / "benchmark_provenance.json", provenance)
    print("Wrote exploratory comparisons; these are not independent estimates of precision or recall.")
