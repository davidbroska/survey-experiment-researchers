"""Summarize the recorded AI-assisted development audit; never call it a holdout."""
from collections import Counter, defaultdict
from common import ROOT, read_csv, write_csv, write_json
import query


def summarize():
    sample = {r["pilot_id"]: r for r in read_csv(ROOT / "private" / "pilot_sample.csv")}
    labels = read_csv(ROOT / "private" / "pilot_labels.csv")
    grouped, evidence, seen = defaultdict(Counter), [], set()
    for label in labels:
        index = label["pilot_id"]
        if index in seen:
            raise RuntimeError("Duplicate pilot label")
        seen.add(index)
        row = sample[index]
        if label["evidence_quote"] not in row["abstract"]:
            raise RuntimeError(f"Pilot evidence is not a verbatim substring: {index}")
        grouped[row["stratum"]][label["survey_experiment"]] += 1
        evidence.append({**row, **label})
    if seen != set(sample):
        raise RuntimeError("Pilot sample not completely coded")
    summary = [{"stratum": s, "n": sum(c.values()), "yes": c["yes"], "no": c["no"], "unclear": c["unclear"],
        "reviewer": "Codex; AI-assisted single review", "status": "development pilot; not independent validation"}
        for s, c in sorted(grouped.items())]
    write_csv(ROOT / "private" / "development_audit" / "pilot_summary.csv", summary)
    write_csv(ROOT / "private" / "pilot_reviewed.csv", evidence)
    write_csv(ROOT / "private" / "development_audit" / "pilot_decisions.csv", evidence,
        ["pilot_id", "scopus_id", "stratum", "survey_experiment", "text_treatment", "notes"])
    print(summary)


if __name__ == "__main__":
    summarize()
