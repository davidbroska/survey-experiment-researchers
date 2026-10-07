"""Versioned Scopus test of reading/manipulation proximity and shorter queries.

Retrieval membership is not study eligibility. Earlier query snapshots remain
immutable; the full-text evaluation sample is fixed before access is checked.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json

from common import ROOT, digest, now, read_csv, write_csv, write_json
import design_audit as audit
import query
import scopus
import search_strategy as previous
from run import parse_entry

VERSION = "proximity_audit_2026_09_10"
PRIVATE = ROOT / "private" / VERSION
RESULTS = ROOT / "results" / VERSION
QUERIES = ROOT / "queries" / VERSION
READ_MATERIALS = ("vignette*", "scenario*", "passage*", "message*", "article*", "news")
MANIPULATED_MATERIALS = ("vignette*", "scenario*", "message*", "information", "wording")
POPULATION = "survey* OR questionnaire* OR respondent* OR participant*"
PRIMARY_PARTS = ("named_base", "named_extra", "guarded_design", "reading_assignment")


def clause(grouped=True):
    if grouped:
        proximity = "(read W/3 (" + " OR ".join(READ_MATERIALS) + ")) OR (manipulat* W/3 (" + " OR ".join(MANIPULATED_MATERIALS) + "))"
    else:
        pairs = [("read", x) for x in READ_MATERIALS] + [("manipulat*", x) for x in MANIPULATED_MATERIALS]
        proximity = " OR ".join("(" + verb + " W/3 " + material + ")" for verb, material in pairs)
    return "TITLE-ABS-KEY(experiment*)\nAND ABS(" + proximity + ")\nAND ABS(" + POPULATION + ")"


def wrap(clauses):
    return "(\n  " + "\n  OR ".join("(" + c + ")" for c in clauses) + "\n)\nAND " + query.LIMITS


def queries():
    p = previous.clauses()
    labels = previous.field(previous.phrases(previous.BASE_LABELS + previous.EXTRA_LABELS))
    return {
        "user_clause": wrap([clause(False)]),
        "grouped_clause": wrap([clause(True)]),
        "targeted": wrap([labels, p["guarded_design"], p["reading_assignment"], clause(True)]),
        "minimal": wrap([labels, clause(True)]),
    }


def freeze():
    protocol = {"version": VERSION,
        "query_sha256": {k: digest(v) for k, v in queries().items()},
        "frame_sha256": digest((ROOT / "results/venue_frame.csv").read_bytes()),
        "prior_query_sha256": digest((previous.QUERIES / "candidate.txt").read_bytes()),
        "purpose": "Test the user-proposed clause, verify OR-group equivalence by complete Scopus ID sets, and compare prior primary routes plus the clause with a shorter named-designs-plus-clause alternative.",
        "development": "All earlier metadata/code labels, the user proposal and nominated author bibliographies are development evidence. Focal-author examples do not estimate recall.",
        "fulltext_plan": "Freeze a 60-article stratified probability sample (20 each: primary_only, proximity_only, overlap) before any open-access lookup. Exclude previously reviewed/development articles and all four nominated author bibliographies by ID/DOI/title. Do not replace unavailable articles. Record access and review completeness; use stratum weights and missing-label bounds, never convenience-subset precision.",
        "blinding": "Coding packets omit query route and previous labels. Full texts inherently contain author names, so author anonymity is not claimed.",
        "ranking_updated": False, "author_or_topic_search_terms": False,
        "limits": query.LIMITS}
    path = RESULTS / "protocol.json"
    if path.exists():
        saved = json.loads(path.read_text())
        if {k:v for k,v in saved.items() if k != "frozen_at"} != protocol:
            raise ValueError("Frozen protocol changed; create another version")
    for name, text in queries().items():
        p = QUERIES / (name + ".txt")
        if p.exists() and p.read_text() != text + "\n":
            raise ValueError("Frozen query changed")
    for name, text in queries().items():
        p = QUERIES / (name + ".txt")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text + "\n")
    if not path.exists():
        write_json(path, {"frozen_at": now(), **protocol})
    return protocol


def fetch(q, view="STANDARD"):
    path = PRIVATE / "searches" / (digest(json.dumps({"query":q,"view":view}, sort_keys=True)) + ".json")
    if path.exists():
        saved = json.loads(path.read_text())
    else:
        entries, manifest = scopus.search(q, view=view, namespace=VERSION)
        saved = {"view":view,"manifest":manifest,"entries":entries}
        write_json(path, saved)
    if saved["view"] != view or not saved["manifest"]["complete"] or saved["manifest"]["query"] != q:
        raise ValueError("Incomplete or mismatched cached query")
    return saved


def retrieve():
    freeze()
    with ThreadPoolExecutor(max_workers=2) as pool:
        for name, saved in zip(("user_clause", "grouped_clause"), pool.map(lambda k: fetch(queries()[k]), ("user_clause", "grouped_clause"))):
            print(name, saved["manifest"]["retrieved"], flush=True)
    return summarize()


def snapshots():
    frame = audit.frame_ids()
    result, manifests = {}, []
    for name in ("user_clause", "grouped_clause"):
        saved = fetch(queries()[name])
        result[name] = {e["dc:identifier"].replace("SCOPUS_ID:", ""): e for e in saved["entries"]}
        manifests.append({"route":name, **saved["manifest"]})
    same = set(result["user_clause"]) == set(result["grouped_clause"])
    write_json(RESULTS / "grouping_equivalence.json", {"global_complete_sets_equal":same,
        "literal_records":len(result["user_clause"]), "grouped_records":len(result["grouped_clause"]),
        "literal_only":sorted(set(result["user_clause"])-set(result["grouped_clause"])),
        "grouped_only":sorted(set(result["grouped_clause"])-set(result["user_clause"])),
        "interpretation":"Empirical equivalence in this Scopus snapshot; grouping does not add cross-pair combinations."})
    if not same:
        raise ValueError("Grouped query differs from literal clause")
    result = {k:{s:e for s,e in v.items() if e.get("source-id", "") in frame} for k,v in result.items()}
    old, _ = previous.memberships()
    result["previous_expanded"] = old["latest_revised"]
    result["previous_candidate"] = {s:e for k in previous.PARTS for s,e in old[k].items()}
    result["previous_primary"] = {s:e for k in PRIMARY_PARTS for s,e in old[k].items()}
    result["named_designs"] = {**old["named_base"], **old["named_extra"]}
    result, conflicts = audit.canonicalize_snapshots(result)
    write_csv(RESULTS / "doi_identity_conflicts.csv", conflicts, ["scopus_id","normalized_dois"])
    if conflicts: raise ValueError("Conflicting DOI identity across snapshots")
    result["targeted"] = {**result["previous_primary"], **result["grouped_clause"]}
    result["minimal"] = {**result["named_designs"], **result["grouped_clause"]}
    result["expanded_plus_clause"] = {**result["previous_expanded"], **result["grouped_clause"]}
    result["candidate_plus_clause"] = {**result["previous_candidate"], **result["grouped_clause"]}
    write_json(RESULTS / "retrieval_manifests.json", manifests)
    return result


def summarize():
    freeze()
    data = snapshots()
    sets = {k:{audit.identity(e) for e in v.values()} for k,v in data.items()}
    counts = [{"variant":k,"in_frame_records":len(data[k]),"unique_articles":len(v),
               "query_characters":len(queries()[k]) if k in queries() else "",
               "status":"Candidate retrieval; study eligibility unvalidated"} for k,v in sets.items()]
    write_csv(RESULTS / "retrieval_counts.csv", counts)
    comparisons = []
    for name in ("targeted","minimal","expanded_plus_clause","candidate_plus_clause"):
        for old in ("previous_expanded","previous_primary","previous_candidate"):
            comparisons.append({"candidate":name,"comparator":old,"candidate_n":len(sets[name]),"comparator_n":len(sets[old]),
                "shared":len(sets[name]&sets[old]),"added":len(sets[name]-sets[old]),"lost":len(sets[old]-sets[name])})
    write_csv(RESULTS / "retrieval_comparison.csv", comparisons)
    all_entries = {sid:e for entries in data.values() for sid,e in entries.items()}
    aliases = {}
    for sid,e in sorted(all_entries.items(), key=lambda kv:int(kv[0])):
        aliases.setdefault(audit.identity(e), []).append(sid)
    rows = []
    for identity, ids in sorted(aliases.items()):
        parsed, _ = parse_entry(all_entries[ids[0]])
        r = {k:parsed[k] for k in ("scopus_id","doi","year","journal","title","source_id")}
        r.update(identity=identity,all_scopus_ids="|".join(ids))
        r.update({k:str(identity in v).lower() for k,v in sets.items()})
        rows.append(r)
    write_csv(RESULTS / "membership.csv", rows)
    print(json.dumps(counts, indent=2), flush=True)
    return rows


def author_comparison():
    rows = read_csv(RESULTS / "membership.csv")
    by_sid = {sid:r for r in rows for sid in r["all_scopus_ids"].split("|")}
    by_doi = {audit.normalize_doi(r["doi"]):r for r in rows if r["doi"]}
    authors = read_csv(PRIVATE / "author_bibliographies/author_articles.csv")
    for r in authors:
        r["focal"] = r["focal_author_name"]
        r["first_last"] = r["first_or_last"]
    variants = ("previous_expanded","previous_primary","previous_candidate","grouped_clause","targeted","minimal","candidate_plus_clause")
    out, papers = [], []
    for person in sorted({r["focal"] for r in authors}):
        for variant in variants:
            selected = {}
            for r in authors:
                if r["focal"] != person: continue
                m = by_sid.get(r["scopus_id"], by_doi.get(audit.normalize_doi(r["doi"]),{}))
                if m.get(variant) == "true": selected.setdefault(m["identity"], []).append(r)
            out.append({"researcher":person,"variant":variant,"any_author_position":len(selected),
                "first_last_candidate_articles":sum(any(r["first_last"] == "true" and r["byline_complete"] == "true" for r in group) for group in selected.values()),
                "status":"Development-case retrieval, not confirmed study counts or population recall"})
        for r in authors:
            if r["focal"] != person: continue
            m = by_sid.get(r["scopus_id"], by_doi.get(audit.normalize_doi(r["doi"]),{}))
            papers.append({k:r.get(k,"") for k in ("focal","scopus_id","doi","title","year","source_id","first_last","byline_complete")} | {v:m.get(v,"false") for v in variants})
    write_csv(RESULTS / "author_comparison.csv", out)
    write_csv(RESULTS / "author_article_retrieval.csv", papers)
    print(json.dumps(out,indent=2))


def fulltext_sample():
    protocol = freeze()
    members = read_csv(RESULTS / "membership.csv")
    ledger = list(previous.frozen_exclusions())
    sources = [previous.RESULTS / "validation_sample.csv", previous.RESULTS / "lost_record_review.csv",
               PRIVATE / "author_bibliographies/author_articles.csv", ROOT / "inputs/fulltext_reviews.csv"]
    for path in sources:
        for r in read_csv(path):
            for sid in r.get("all_scopus_ids",r["scopus_id"]).split("|"):
                ledger.append({"scopus_id":sid,"doi":r.get("doi",""),
                    "normalized_title_sha256":audit.title_hash(r.get("title","")) if r.get("title") else "",
                    "reasons":str(path.relative_to(ROOT))})
    write_csv(RESULTS / "fulltext_development_exclusions.csv", ledger)
    indexes = audit.exclusion_indexes(ledger)
    groups = {s:[] for s in ("primary_only","proximity_only","overlap")}
    for r in members:
        if r["targeted"] != "true" or audit.excluded_by_indexes(r,indexes): continue
        p, q = r["previous_primary"] == "true", r["grouped_clause"] == "true"
        groups["overlap" if p and q else "primary_only" if p else "proximity_only"].append(r)
    seed = VERSION + ":fulltext:20260910"
    selected = []
    for name, rows in groups.items():
        if len(rows) < 20: raise ValueError("Insufficient unseen articles in " + name)
        rows.sort(key=lambda r:digest(seed+":"+r["identity"]))
        for r in rows[:20]:
            selected.append({**r,"stratum":name,"stratum_N":len(rows),"stratum_n":20,
                "inclusion_probability":20/len(rows),"selection_hash":digest(seed+":"+r["identity"]),
                "stage":"fixed_fulltext_evaluation"})
    audit.freeze_selection(RESULTS / "fulltext_sample.csv", selected, {
        "stage":"fulltext_evaluation", "selected_variant":"targeted", "query_sha256":protocol["query_sha256"]["targeted"],
        "membership_sha256":digest((RESULTS/"membership.csv").read_bytes()),"frame_sha256":protocol["frame_sha256"],
        "exclusions_sha256":digest((RESULTS/"fulltext_development_exclusions.csv").read_bytes()),
        "requested_n":60,"selection_seed":seed,
        "estimand":"Named/guarded/reading routes OR user proximity clause within the journal frame, outside prior development; stratum-weighted estimates only",
        "availability_policy":"Selection precedes access lookup; all60remain in the denominator; unavailable articles are not replaced"})
    write_csv(RESULTS / "fulltext_sampling_strata.csv", [{"stratum":k,"population_N":len(v),"sample_n":20} for k,v in groups.items()])
    print("Fixed full-text sample:60 articles; access has not determined inclusion",flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("command",choices=("freeze","retrieve","summarize","author_comparison","fulltext_sample"))
    args = p.parse_args()
    globals()[args.command]()
