"""Summarize completed prospective labels with the actual sampling weights."""
from collections import Counter, defaultdict
from common import ROOT, read_csv, write_csv, write_json
from benchmark import wilson


def validate():
    sample = {r["scopus_id"]: r for r in read_csv(ROOT / "results" / "validation_sample_ids.csv")}
    path = ROOT / "inputs" / "validation_labels.csv"
    if not path.exists():
        write_csv(path, [], ["scopus_id", "reviewer_1", "reviewer_2", "adjudicator", "survey_experiment", "notes"])
        raise SystemExit("Created inputs/validation_labels.csv; complete independent labels before validation.")
    labels = read_csv(path)
    if len({r["scopus_id"] for r in labels}) != len(labels):
        raise SystemExit("Duplicate validation labels")
    if {r["scopus_id"] for r in labels} != set(sample):
        raise SystemExit("Labels must cover exactly the frozen validation sample; partial estimates are not emitted.")
    groups = defaultdict(Counter)
    for row in labels:
        if row["survey_experiment"] not in {"yes", "no", "unclear"}:
            raise SystemExit("Invalid label")
        if not row["reviewer_1"] or not row["reviewer_2"] or row["reviewer_1"] == row["reviewer_2"]:
            raise SystemExit("Record two distinct reviewers for prospective validation")
        groups[sample[row["scopus_id"]]["stratum"]][row["survey_experiment"]] += 1
    summary, totals = [], {"population": 0, "estimated_yes": 0.0, "estimated_unclear": 0.0}
    for stratum, counts in sorted(groups.items()):
        design = next(r for r in sample.values() if r["stratum"] == stratum)
        n, population = int(design["sample_n"]), int(design["population_n"])
        if sum(counts.values()) != n:
            raise SystemExit("Sample-size mismatch")
        p, lo, hi = wilson(counts["yes"], counts["yes"]+counts["no"])
        summary.append({"stratum": stratum, "population_n": population, "sample_n": n,
            "yes": counts["yes"], "no": counts["no"], "unclear": counts["unclear"],
            "precision_among_determinate": p, "wilson_low_determinate": lo, "wilson_high_determinate": hi})
        totals["population"] += population
        totals["estimated_yes"] += population * counts["yes"] / n
        totals["estimated_unclear"] += population * counts["unclear"] / n
    totals["weighted_yes_fraction"] = totals["estimated_yes"] / totals["population"]
    totals["weighted_yes_or_unclear_fraction"] = (totals["estimated_yes"]+totals["estimated_unclear"]) / totals["population"]
    totals["interpretation"] = "Fractions bracket unresolved classifications; they are not confidence bounds. No recall estimate."
    write_csv(ROOT / "results" / "prospective_validation.csv", summary)
    write_json(ROOT / "results" / "prospective_validation.json", totals)


if __name__ == "__main__":
    validate()
