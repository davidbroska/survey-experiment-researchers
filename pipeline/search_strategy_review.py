"""Double-code the held-out search sample; keep disagreements and uncertainty visible."""
from collections import Counter
import json

from common import ROOT, digest, read_csv, write_csv, write_json
from design_audit_report import GEO, PUBLIC_FIELDS, wilson

RESULTS = ROOT / "results/search_strategy_2026_09_10"
PRIVATE = ROOT / "private/search_strategy_2026_09_10"


def load_coder(name, packet):
    path = PRIVATE / ("validation_coder_" + name + ".csv")
    labels = {}
    for r in read_csv(path):
        sid = r["scopus_id"]
        if sid not in packet or sid in labels:
            raise ValueError("Unknown or duplicate coder record: " + sid)
        for k in ("design", "new_data", "text_treatment", "parser_compatible"):
            if r.get(k) not in {"yes", "no", "unclear"}:
                raise ValueError("Invalid " + k + ": " + sid)
        if r.get("geography") not in GEO or not r.get("rationale") or not r.get("reviewer"):
            raise ValueError("Missing geography/rationale/provenance: " + sid)
        if r.get("reviewer_type") != "AI_assisted" or r.get("human_validated") != "false":
            raise ValueError("Missing AI provenance: " + sid)
        field, quote = r.get("evidence_field"), r.get("evidence_quote", "")
        norm = lambda s: " ".join(s.split())
        if field not in {"title", "abstract", "keywords"} or not quote or norm(quote) not in norm(packet[sid].get(field, "")):
            raise ValueError("Evidence is not in the supplied packet: " + sid)
        labels[sid] = r
    if set(labels) != set(packet):
        raise ValueError("Incomplete coding by " + name)
    write_csv(RESULTS / ("validation_coder_" + name + ".csv"), sorted(labels.values(), key=lambda r:int(r["scopus_id"])), PUBLIC_FIELDS)
    return labels


def summarize():
    packet = {r["scopus_id"]: r for r in json.loads((PRIVATE / "validation_packet.json").read_text())}
    membership_path = RESULTS / "membership.csv"
    memberships = {r["scopus_id"]: r for r in read_csv(membership_path)} if membership_path.exists() else {}
    a, b = (load_coder(n, packet) for n in ("A", "B"))
    rows, disagreements, queue = [], [], []
    for sid in sorted(packet, key=int):
        x, y = a[sid], b[sid]
        row = {"scopus_id": sid, "title": packet[sid]["title"], "doi": packet[sid]["doi"],
               "coder_A_design": x["design"], "coder_B_design": y["design"],
               "design": x["design"] if x["design"] == y["design"] else "unclear",
               "decision_basis": "coders_agree" if x["design"] == y["design"] else "coder_disagreement",
               "rationale_A": x["rationale"], "rationale_B": y["rationale"], "human_validated": "false"}
        for field in ("new_data", "text_treatment", "parser_compatible", "geography"):
            row[field] = x[field] if x[field] == y[field] else "unclear"
        row["parser_incompatibility_flag"] = str("no" in (x["parser_compatible"],y["parser_compatible"])).lower()
        row["secondary_data_flag"] = str("no" in (x["new_data"],y["new_data"])).lower()
        # Agreement on a broad design does not certify its usability for this project.
        row["candidate_after_known_incompatibility_flags"] = str(row["design"] == "yes" and row["parser_incompatibility_flag"] == "false" and row["secondary_data_flag"] == "false").lower()
        m = memberships.get(sid, {})
        row["search_stratum"] = ("named_design_or_reading" if any(m.get(k) == "true" for k in ("named_base", "named_extra", "guarded_design", "reading_assignment")) else "procedure_only") if m else "unavailable"
        rows.append(row)
        if row["decision_basis"] == "coder_disagreement":
            disagreements.append(row)
        if row["design"] == "unclear":
            queue.append({"scopus_id": sid, "title": row["title"], "doi": row["doi"],
                "url": "https://doi.org/"+row["doi"] if row["doi"] else "https://www.scopus.com/record/display.uri?eid=2-s2.0-"+sid,
                "reason": row["decision_basis"], "rationale_A": row["rationale_A"], "rationale_B": row["rationale_B"]})
    write_csv(RESULTS / "validation_consensus.csv", rows)
    write_csv(RESULTS / "validation_disagreements.csv", disagreements, list(rows[0]))
    write_csv(RESULTS / "validation_unclear_queue.csv", queue, ["scopus_id", "title", "doi", "url", "reason", "rationale_A", "rationale_B"])
    counts = Counter(r["design"] for r in rows)
    ca, cb = (Counter(r["design"] for r in coder.values()) for coder in (a,b))
    n = len(rows)
    agreement = sum(x["design"] == b[sid]["design"] for sid,x in a.items())/n
    chance = sum(ca[k]*cb[k]/(n*n) for k in ("yes", "no", "unclear"))
    summary = {"n": n, "agreed_yes": counts["yes"], "agreed_no": counts["no"],
        "unclear_or_disagreement": counts["unclear"], "design_disagreements": len(disagreements),
        "raw_design_agreement": agreement, "cohens_kappa_descriptive": (agreement-chance)/(1-chance) if chance < 1 else None,
        "agreed_yes_share": counts["yes"]/n, "agreed_yes_share_wilson_95": wilson(counts["yes"], n),
        "agreed_yes_or_unresolved_share": (counts["yes"]+counts["unclear"])/n,
        "candidate_after_known_incompatibility_flags": sum(r["candidate_after_known_incompatibility_flags"] == "true" for r in rows),
        "coder_A": dict(ca), "coder_B": dict(cb),
        "geography_agreement_counts": dict(Counter(r["geography"] for r in rows)),
        "human_validated": False,
        "estimand": "Query-selected articles outside archived development material and the 160-record development sample",
        "interpretation": "Two AI coding passes; disagreements remain unresolved. Agreement and intervals are descriptive; shared AI errors and parser/data-ownership uncertainty remain. No validated precision or recall claim.",
        "sampling_uncertainty_note": "Wilson interval describes agreed affirmative evidence, not truth-label precision; it does not account for annotation error."}
    write_json(RESULTS / "validation_summary.json", summary)
    strata = []
    for stratum in sorted({r["search_stratum"] for r in rows}):
        group = [r for r in rows if r["search_stratum"] == stratum]
        c = Counter(r["design"] for r in group)
        strata.append({"stratum": stratum, "sample_n": len(group), "agreed_yes": c["yes"],
            "agreed_no": c["no"], "unclear_or_disagreement": c["unclear"],
            "candidate_after_known_incompatibility_flags": sum(r["candidate_after_known_incompatibility_flags"] == "true" for r in group),
            "note": "Post-coding subgroup of the frozen random sample; small denominators; AI-coded, not human-validated"})
    write_csv(RESULTS / "validation_strata_summary.csv", strata)
    write_json(RESULTS / "validation_annotation_provenance.json", {
        "packet_sha256": digest((PRIVATE / "validation_packet.json").read_bytes()),
        "sample_sha256": digest((RESULTS / "validation_sample.csv").read_bytes()),
        "coder_files": [{"file": "validation_coder_"+name+".csv", "sha256": digest((PRIVATE/("validation_coder_"+name+".csv")).read_bytes())} for name in ("A","B")],
        "procedure": "Separate AI passes; exact evidence spans checked against identical blinded indexed-metadata packet; disagreements retained as unclear.",
        "human_validated": False})
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    summarize()
