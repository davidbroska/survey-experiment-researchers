"""Validate audit annotations and summarize probability samples without gold claims."""
import argparse
from collections import Counter
import json
import math

from common import ROOT, digest, read_csv, write_csv, write_json
import design_audit as audit

PUBLIC_FIELDS = ["scopus_id", "design", "new_data", "text_treatment", "parser_compatible",
                 "geography", "rationale", "reviewer", "reviewer_type", "human_validated"]
GEO = {"US_explicit", "US_inferred", "non_US", "mixed_includes_US", "unclear"}


def collate(stage, pattern=None):
    sample = read_csv(audit.RESULTS / (stage + "_sample.csv"))
    wanted = {r["scopus_id"] for r in sample}
    packet = {r["scopus_id"]: r for r in json.loads((audit.PRIVATE / (stage + "_packet.json")).read_text())}
    paths = sorted(audit.PRIVATE.glob(pattern or (stage + "_coder_*.csv")))
    labels = {}
    for path in paths:
        for row in read_csv(path):
            sid = row["scopus_id"]
            if sid not in wanted or sid in labels:
                raise ValueError("Unknown or duplicate annotation " + sid)
            if any(row.get(k) not in {"yes", "no", "unclear"} for k in ("design", "new_data", "text_treatment", "parser_compatible")):
                raise ValueError("Invalid design label " + sid)
            if row.get("geography") not in GEO or not row.get("rationale") or not row.get("reviewer"):
                raise ValueError("Missing classification/provenance " + sid)
            if row.get("reviewer_type") != "AI_assisted" or row.get("human_validated") != "false":
                raise ValueError("Audit requires explicit AI provenance " + sid)
            field = row.get("evidence_field", "")
            quote = row.get("evidence_quote", "")
            normalize = lambda s: " ".join(s.split())
            if field not in {"title", "abstract", "keywords"} or not quote or normalize(quote) not in normalize(packet[sid].get(field, "")):
                raise ValueError("Evidence span missing from packet " + sid)
            labels[sid] = row
    if set(labels) != wanted:
        raise ValueError("Incomplete coding: " + str(len(labels)) + "/" + str(len(wanted)))
    ordered = [labels[r["scopus_id"]] for r in sample]
    write_csv(audit.RESULTS / (stage + "_annotations.csv"), ordered, PUBLIC_FIELDS)
    write_json(audit.RESULTS / (stage + "_annotation_provenance.json"), {
        "packet_sha256": digest((audit.PRIVATE / (stage + "_packet.json")).read_bytes()),
        "sample_sha256": digest((audit.RESULTS / (stage + "_sample.csv")).read_bytes()),
        "coding_files": [{"file": p.name, "sha256": digest(p.read_bytes())} for p in paths],
        "human_validated": False, "n": len(labels), "abstract_only": True})
    return labels


def wilson(yes, n):
    if not n:
        return [None, None]
    z = 1.959963984540054
    p = yes / n
    den = 1 + z*z/n
    c = (p + z*z/(2*n))/den
    d = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n))/den
    return [max(0,c-d), min(1,c+d)]


def summarize(stage):
    labels = {r["scopus_id"]: r for r in read_csv(audit.RESULTS / (stage + "_annotations.csv"))}
    sample = read_csv(audit.RESULTS / (stage + "_sample.csv"))
    strata = []
    for stratum in sorted({r["stratum"] for r in sample}):
        rows = [r for r in sample if r["stratum"] == stratum]
        c = Counter(labels[r["scopus_id"]]["design"] for r in rows)
        strata.append({"stratum": stratum, "population_N": rows[0]["stratum_N"], "sample_n": len(rows),
                       "design_yes": c["yes"], "design_no": c["no"], "design_unclear": c["unclear"],
                       "affirmative_share": c["yes"]/len(rows),
                       "affirmative_or_unclear_share": (c["yes"]+c["unclear"])/len(rows),
                       "status": "AI-coded indexed-metadata evidence; not validated precision"})
    write_csv(audit.RESULTS / (stage + "_strata_summary.csv"), strata)
    if stage == "development":
        # Horvitz-Thompson estimates within the sampled (development-excluded) universe.
        # Report the weighted mix; a pooled 160-record proportion is inappropriate.
        weighted = []
        for variant in ("concepts", "exposure", "exposure_human"):
            totals = Counter()
            for r in sample:
                if r["labels"] == "true" or r[variant] == "true":
                    totals[labels[r["scopus_id"]]["design"]] += int(r["stratum_N"])/int(r["stratum_n"])
            denom = sum(totals.values())
            weighted.append({"variant": variant, "weighted_yes_share": totals["yes"]/denom if denom else "",
                             "weighted_no_share": totals["no"]/denom if denom else "",
                             "weighted_unclear_share": totals["unclear"]/denom if denom else "",
                             "note": "Stratum-weighted descriptive ratio estimate from development sample; excludes prior development records; no precision validation"})
        write_csv(audit.RESULTS / "development_variant_summary.csv", weighted)
    else:
        c = Counter(r["design"] for r in labels.values())
        yes = c["yes"]
        n = len(labels)
        write_json(audit.RESULTS / "validation_summary.json", {
            "n": n, "yes": yes, "no": c["no"], "unclear": c["unclear"],
            "affirmative_share": yes/n, "affirmative_share_wilson_95": wilson(yes,n),
            "affirmative_or_unclear_share": (yes+c["unclear"])/n,
            "geography": dict(Counter(r["geography"] for r in labels.values())),
            "text_treatment": dict(Counter(r["text_treatment"] for r in labels.values())),
            "human_validated": False,
            "interpretation": "Disjoint probability sample, AI-coded abstracts. Interval covers sampling uncertainty, not label error. Unknowns remain unknown; this is not validated eligibility precision or recall."})
    queue = []
    byid = {r["scopus_id"]: r for r in sample}
    for sid, r in labels.items():
        if r["design"] == "unclear":
            m = byid[sid]
            queue.append({"scopus_id": sid, "title": m["title"], "doi": m["doi"],
                          "url": "https://doi.org/"+m["doi"] if m["doi"] else "https://www.scopus.com/record/display.uri?eid=2-s2.0-"+sid,
                          "reason": r["rationale"], "stage": stage})
    write_csv(audit.RESULTS / (stage + "_unclear_queue.csv"), queue,
              ["scopus_id", "title", "doi", "url", "reason", "stage"])
    return strata


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["development", "validation"])
    ap.add_argument("--pattern")
    args = ap.parse_args()
    collate(args.stage, args.pattern)
    print(json.dumps(summarize(args.stage), indent=2))
