"""Aggregate independent full-text reviews without dropping inaccessible articles.

All fixed-sample members remain in stratum denominators. Missing, single-pass,
unclear and disputed design labels remain unknown in descriptive weighted bounds;
the accessible subset is never presented as a representative precision estimate.
"""
from collections import Counter
from fractions import Fraction
import json
import math

from common import digest, read_csv, write_csv, write_json
import precision_benchmark as benchmark

AXES = benchmark.AXES
STRATA = ("primary_only", "proximity_only", "overlap")


def consensus(a, b):
    return a if a and a == b else "unclear"


def summarize_strata(rows):
    out = []
    for stratum in STRATA:
        group = [r for r in rows if r["stratum"] == stratum]
        if not group:
            raise ValueError("Missing fixed-sample stratum: " + stratum)
        populations = {int(r["stratum_N"]) for r in group}
        declared = {int(r["stratum_n"]) for r in group}
        if len(populations) != 1 or declared != {len(group)}:
            raise ValueError("Inconsistent stratum population or sample count: " + stratum)
        N, n = populations.pop(), len(group)
        if not 0 < n <= N:
            raise ValueError("Invalid stratum sampling fraction: " + stratum)
        for row in group:
            if not math.isclose(float(row["inclusion_probability"]), n / N, rel_tol=1e-12):
                raise ValueError("Sampling probability disagrees with frozen stratum counts")
        double = [r for r in group if r["review_coverage"] == "double_pass"]
        yes = sum(r["design"] == "yes" for r in double)
        no = sum(r["design"] == "no" for r in double)
        out.append({"stratum": stratum, "population_N": N, "sample_n": n,
                    "ready_for_fulltext_review": sum(r["fulltext_readiness"] == "ready_for_fulltext_review" for r in group),
                    "not_reviewed": sum(r["review_coverage"] == "not_reviewed" for r in group),
                    "single_pass": sum(r["review_coverage"] == "single_pass" for r in group),
                    "double_pass": len(double), "double_coded_yes": yes, "double_coded_no": no,
                    "double_coded_unclear_or_disputed": len(double) - yes - no,
                    "pending_second_or_both_reviews": n - len(double),
                    "unknown_for_bounds": n - yes - no,
                    "inclusion_probability": n / N})
    return out


def missing_label_bounds(strata):
    rows = []
    for name, included in [("targeted_union", set(STRATA)), ("proximity_clause", {"proximity_only", "overlap"})]:
        selected = [s for s in strata if s["stratum"] in included]
        N = sum(s["population_N"] for s in selected)
        lower = sum((Fraction(s["double_coded_yes"], s["sample_n"]) * s["population_N"] for s in selected), Fraction(0))
        upper = sum((Fraction(s["double_coded_yes"] + s["unknown_for_bounds"], s["sample_n"]) * s["population_N"] for s in selected), Fraction(0))
        rows.append({"scope": name, "population_after_development_exclusions": N,
                     "fixed_sample_n": sum(s["sample_n"] for s in selected),
                     "double_coded_yes": sum(s["double_coded_yes"] for s in selected),
                     "double_coded_no": sum(s["double_coded_no"] for s in selected),
                     "unknown_sample_labels": sum(s["unknown_for_bounds"] for s in selected),
                     "weighted_affirmative_article_total": float(lower),
                     "weighted_affirmative_plus_unknown_total": float(upper),
                     "lower_bound": float(lower / N), "upper_bound": float(upper / N),
                     "bound_type": "descriptive stratum-weighted sample bounds over unresolved labels",
                     "interpretation": "Not confidence intervals or human-validated precision; bounds cover missing and disputed sample labels, not sampling error or annotation error.",
                     "human_validated": "false"})
    return rows


def build():
    private, results = benchmark.PRIVATE, benchmark.RESULTS
    sample_path = private / "fixed_sample.csv"
    sample = read_csv(sample_path)
    if {r["stratum"] for r in sample} != set(STRATA):
        raise ValueError("Unexpected fixed-sample strata")
    availability_path = results / "availability_manifest.csv"
    available = {r["scopus_id"]: r for r in read_csv(availability_path)}
    if set(available) != {r["scopus_id"] for r in sample} or len(available) != len(sample):
        raise ValueError("Availability manifest must contain every fixed-sample article exactly once")
    coders, validation, hashes = {}, {}, {}
    for name in ("A", "B"):
        path = private / ("reviews_coder_" + name + ".json")
        if path.exists():
            validation[name] = benchmark.validate_reviews(path)
            reviews = json.loads(path.read_text())
            coders[name] = {r["benchmark_id"]: r for r in reviews if r["evaluation_status"] == "completed"}
            hashes[name] = digest(path.read_bytes())
        else:
            coders[name] = {}
            validation[name] = {"n_completed": 0, "status": "review file not yet present"}
    public, annotations = [], []
    for article in sample:
        availability = available[article["scopus_id"]]
        bid = availability["benchmark_id"]
        a, b = coders["A"].get(bid), coders["B"].get(bid)
        coverage = "double_pass" if a and b else "single_pass" if a or b else "not_reviewed"
        row = {"benchmark_id": bid, "scopus_id": article["scopus_id"], "doi": article["doi"],
               "title": article["title"], "year": article.get("year", ""), "journal": article.get("journal", ""),
               "stratum": article["stratum"], "stratum_N": article["stratum_N"], "stratum_n": article["stratum_n"],
               "inclusion_probability": article["inclusion_probability"],
               "fulltext_readiness": availability["fulltext_readiness"], "review_coverage": coverage,
               "human_validated": "false"}
        for axis in AXES:
            ad = a[axis]["decision"] if a else ""
            bd = b[axis]["decision"] if b else ""
            row["coder_A_" + axis], row["coder_B_" + axis] = ad, bd
            row[axis] = consensus(ad, bd) if coverage == "double_pass" else "unclear"
            for name, review in (("A", a), ("B", b)):
                if review:
                    item = review[axis]
                    annotations.append({"benchmark_id": bid, "scopus_id": article["scopus_id"], "coder": name,
                        "axis": axis, "decision": item["decision"], "rationale": item["rationale"],
                        "document_sha256": item.get("document_sha256", ""), "pdf_page": item.get("pdf_page", ""),
                        "reviewer": review["reviewer"], "reviewer_type": review["reviewer_type"],
                        "review_date": review["review_date"], "human_validated": "false"})
        # These are review flags, not a new definition of design eligibility.
        row["parser_incompatibility_flag"] = str(any(r and r["parser_compatible"]["decision"] == "no" for r in (a, b))).lower()
        row["secondary_only_flag"] = str(any(r and r["new_data"]["decision"] == "no" for r in (a, b))).lower()
        row["affirmative_design_after_known_incompatibility_flags"] = str(row["design"] == "yes" and
            row["parser_incompatibility_flag"] == "false" and row["secondary_only_flag"] == "false").lower()
        row["decision_basis"] = ("both coders agree" if coverage == "double_pass" and row["coder_A_design"] == row["coder_B_design"]
                                  else "coders disagree; unresolved" if coverage == "double_pass" else "second coding pass pending" if coverage == "single_pass"
                                  else "full-text review not completed")
        public.append(row)
    strata = summarize_strata(public)
    bounds = missing_label_bounds(strata)
    write_csv(results / "article_consensus.csv", public)
    write_csv(results / "axis_annotations.csv", annotations, ["benchmark_id", "scopus_id", "coder", "axis", "decision", "rationale",
              "document_sha256", "pdf_page", "reviewer", "reviewer_type", "review_date", "human_validated"])
    write_csv(results / "stratum_summary.csv", strata)
    write_csv(results / "missing_label_bounds.csv", bounds)
    coverage = Counter(r["review_coverage"] for r in public)
    double = [r for r in public if r["review_coverage"] == "double_pass"]
    summary = {"sample_n": len(sample), "ready_for_fulltext_review": sum(s["ready_for_fulltext_review"] for s in strata),
               "not_reviewed": coverage["not_reviewed"], "single_pass": coverage["single_pass"], "double_pass": coverage["double_pass"],
               "double_coded_yes": sum(r["design"] == "yes" for r in double),
               "double_coded_no": sum(r["design"] == "no" for r in double),
               "double_coded_unclear_or_disputed": sum(r["design"] == "unclear" for r in double),
               "unknown_for_bounds": sum(s["unknown_for_bounds"] for s in strata),
               "affirmative_design_after_known_incompatibility_flags": sum(r["affirmative_design_after_known_incompatibility_flags"] == "true" for r in public),
               "missing_label_bounds": bounds, "inaccessible_articles_replaced": False,
               "fulltext_review_unit": "Article; at least one eligible study supplies affirmative design evidence.",
               "all_axes_separate": True, "human_validated": False,
               "interpretation": "Unreviewed, singly reviewed, unclear and disputed designs remain unknown. Accessible articles are not a replacement sample or an unbiased precision denominator. Weighted bounds apply only to the post-development-exclusion sampling frame and quantify neither sampling uncertainty nor AI annotation error."}
    write_json(results / "review_summary.json", summary)
    write_json(results / "review_provenance.json", {"fixed_sample_sha256": digest(sample_path.read_bytes()),
        "availability_manifest_sha256": digest(availability_path.read_bytes()),
        "packet_sha256": digest((private / "reviewer_packet.json").read_bytes()),
        "coder_file_sha256": hashes, "validation": validation,
        "no_private_evidence_quotes_published": True, "human_validated": False})
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    build()
