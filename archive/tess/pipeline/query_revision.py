"""Retrieve and compare the requested query revision in a separate dated snapshot.

The reviewed dashboard remains reproducible from its original query and corpus.
This module executes the revised search; it never assigns geography or replaces
the dashboard's annotations with labels from a different retrieval.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
import json
import re

from common import ROOT, digest, read_csv, write_csv, write_json
import query
import scopus
from run import parse_entry

VERSION = "2026_09_10"
QDIR = ROOT / "queries" / ("revision_" + VERSION)
RDIR = ROOT / "results" / ("query_revision_" + VERSION)
PRIVATE = ROOT / "private" / ("query_revision_" + VERSION)
NAMESPACE = "query_revision_" + VERSION
REMOVED = {
    "experiment embedded in a national survey",
    "experiments embedded in national surveys",
    "experiment embedded in a nationally representative survey",
    "experiments embedded in nationally representative surveys",
}
ADDED = [
    "randomly presented with information", "randomly exposed to information",
    "randomly assigned to receive a message", "randomly assigned to receive messages",
    "randomly presented with a message", "randomly presented with messages",
    "randomly exposed to a message", "randomly exposed to messages",
]
EXPLICIT_ADDED = ["experimental survey", "experimental surveys",
    "experimental survey study", "experimental survey studies"] + query.number(
    "survey-based randomized experiment", "survey based randomized experiment",
    "survey-based randomised experiment", "survey based randomised experiment")
# The plural belongs to 'experiment', not 'survey'. Enumerate these explicitly.
EMBEDDED_ADDED = [
    "experiment in an online survey", "experiments in an online survey",
    "experiment within an online survey", "experiments within an online survey",
    "experiment in a survey", "experiments in a survey",
    "experiment within a survey", "experiments within a survey",
]
TEXT_FURTHER = ["randomly shown information", "randomly assigned information",
    "randomly assigned a message", "randomly assigned messages",
    "randomly shown a message", "randomly shown messages"]
INFORMATION_ADDED = query.number("information experiment", "randomized information experiment",
                                 "randomised information experiment")
EMBEDDED_GAPS = [
    "experiment embedded within a survey", "experiments embedded within a survey",
    "experiment embedded within an online survey", "experiments embedded within an online survey",
    "experiments embedded in surveys", "experiments embedded in online surveys",
    "experiment was embedded in a survey", "experiments were embedded in a survey",
    "experiments were embedded in surveys", "experiment was embedded in an online survey",
    "experiments were embedded in an online survey", "experiments were embedded in online surveys",
]


def previous_families():
    return json.loads((QDIR / "previous_families.json").read_text())


def initial_families(participants=True, messages=True, remove_national=True):
    families = deepcopy(previous_families())
    for family in families:
        if participants and family["id"] in {"text_assignment", "survey_wording"}:
            family["participant_context"] = True
        if messages and family["id"] == "text_assignment":
            family["phrases"] += [p for p in ADDED if p not in family["phrases"]]
        if remove_national and family["id"] == "embedded_design":
            if not REMOVED <= set(family["phrases"]):
                raise ValueError("Previous embedded family does not contain the four requested removals")
            family["phrases"] = [p for p in family["phrases"] if p not in REMOVED]
    return families


def revised_families(explicit=True, embedded=True, text=True, information=True):
    families = initial_families()
    additions = {"survey_design": EXPLICIT_ADDED if explicit else [],
                 "embedded_design": EMBEDDED_ADDED if embedded else [],
                 "text_assignment": TEXT_FURTHER if text else [],
                 "survey_information": INFORMATION_ADDED if information else []}
    for family in families:
        family["phrases"] += [p for p in additions.get(family["id"], []) if p not in family["phrases"]]
        if information and family["id"] == "survey_information":
            family["participant_context"] = True
    return families


def versions():
    return {
        "previous": previous_families(),
        "participants": initial_families(messages=False, remove_national=False),
        "participants_messages": initial_families(remove_national=False),
        "initial_request": initial_families(),
        "explicit_designs": revised_families(embedded=False, text=False, information=False),
        "embedded_variants": revised_families(text=False, information=False),
        "expanded_text_assignments": revised_families(information=False),
        "revised": revised_families(),
    }


def gap_family():
    return {"id": "additional_embedded_variants", "phrases": EMBEDDED_GAPS,
            "context": True, "role": "diagnostic_only"}


def family_query(family):
    return query.clause(family) + " AND " + query.LIMITS


def write_queries():
    QDIR.mkdir(exist_ok=True)
    old = (QDIR / "previous.txt").read_text().strip()
    if old != query.build(previous_families()).strip():
        raise ValueError("Frozen previous query does not match its family definitions")
    revised = revised_families()
    (QDIR / "revised.txt").write_text(query.build(revised) + "\n")
    write_json(QDIR / "revised_families.json", revised)
    rows = [{"version": name, "family": f["id"], "query": family_query(f)}
            for name, families in versions().items() for f in families]
    rows.append({"version": "diagnostic_only", "family": gap_family()["id"],
                 "query": family_query(gap_family())})
    write_csv(QDIR / "executed_family_queries.csv", rows)
    (QDIR / "additional_embedded_variants.txt").write_text(family_query(gap_family()) + "\n")


def snapshot_path(q, view):
    return PRIVATE / "searches" / (digest(json.dumps({"query": q, "view": view}, sort_keys=True)) + ".json")


def fetch(q, view="STANDARD"):
    path = snapshot_path(q, view)
    if path.exists():
        saved = json.loads(path.read_text())
    else:
        entries, manifest = scopus.search(q, view=view, namespace=NAMESPACE)
        saved = {"view": view, "manifest": manifest, "entries": entries}
        write_json(path, saved)
    if saved["manifest"]["query"] != q or not saved["manifest"]["complete"]:
        raise ValueError("Incomplete or mismatched query snapshot")
    return saved


def load(q, view="STANDARD"):
    path = snapshot_path(q, view)
    if not path.exists():
        raise ValueError("Missing snapshot; run query_revision.py retrieve first")
    saved = json.loads(path.read_text())
    if not saved["manifest"]["complete"]:
        raise ValueError("Incomplete query snapshot")
    return saved


def collect(families, view="STANDARD"):
    entries = {}
    for f in families:
        for e in load(family_query(f), view)["entries"]:
            sid = e["dc:identifier"].replace("SCOPUS_ID:", "")
            # A stable choice avoids dependence on worker completion order.
            if sid not in entries or json.dumps(e, sort_keys=True) < json.dumps(entries[sid], sort_keys=True):
                entries[sid] = e
    return entries


def check_fields():
    probes = [("84924585051", "experimental survey"), ("84979503153", "information experiment"),
              ("84961190121", "information experiment"), ("84961190121", "information treatment"),
              ("85062297171", "information treatment")]
    def probe(job):
        sid, phrase, field = job
        q = "EID(2-s2.0-"+sid+") AND "+field+"({"+phrase+"})"
        saved = scopus.request({"query": q, "count": 1, "view": "STANDARD"},
                              "query_revision_field_checks_2026_09_10")
        return {"scopus_id": sid, "phrase": phrase, "field": field,
                "count": int(saved["body"]["search-results"]["opensearch:totalResults"]),
                "query": q, "retrieved_at": saved["retrieved_at"]}
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(probe, [(sid, phrase, field) for sid, phrase in probes
                                    for field in ["TITLE", "ABS", "KEY"]]))
    write_json(PRIVATE / "field_checks.json", rows)


def retrieve(workers=4):
    write_queries()
    jobs = {family_query(f) for families in versions().values() for f in families}
    jobs.add(family_query(gap_family()))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch, q): q for q in sorted(jobs)}
        for i, fut in enumerate(as_completed(futures), 1):
            saved = fut.result()
            print(f"Search membership {i}/{len(jobs)}: {saved['manifest']['retrieved']} records", flush=True)
    # Fetch full metadata only for changed IDs, reusing previously acquired pages.
    old, new = collect(previous_families()), collect(revised_families())
    gaps = collect([gap_family()])
    targets = (set(new)-set(old)) | (set(old)-set(new)) | (set(gaps)-set(new))
    available = set()
    for path in (PRIVATE / "searches").glob("*.json"):
        saved = json.loads(path.read_text())
        if saved["view"] == "COMPLETE":
            available.update(e["dc:identifier"].replace("SCOPUS_ID:", "") for e in saved["entries"])
    missing = sorted(targets-available, key=int)
    batches = [missing[i:i+25] for i in range(0, len(missing), 25)]
    def detail_batch(ids):
        if not all(s.isdigit() for s in ids):
            raise ValueError("Invalid Scopus identifier")
        q = "(" + " OR ".join("EID(2-s2.0-"+s+")" for s in ids) + ")"
        saved = fetch(q, "COMPLETE")
        found = {e["dc:identifier"].replace("SCOPUS_ID:", "") for e in saved["entries"]}
        if found != set(ids):
            raise ValueError("Full-metadata lookup did not return exactly the requested IDs")
        return saved
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(detail_batch, ids) for ids in batches]
        for i, fut in enumerate(as_completed(futures), 1):
            saved = fut.result()
            print(f"Review metadata {i}/{len(futures)}: {saved['manifest']['retrieved']} records", flush=True)
    check_fields()


def identity(e):
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", (e.get("prism:doi") or "").strip().lower())
    return "doi:" + doi if doi else "scopus:" + e["dc:identifier"].replace("SCOPUS_ID:", "")


def restrict(entries, frame=None):
    return {sid: e for sid, e in entries.items() if frame is None or e.get("source-id", "") in frame}


def contrast(old, new, scope):
    a, b = set(old), set(new)
    ak, bk = {identity(e) for e in old.values()}, {identity(e) for e in new.values()}
    return {"scope": scope, "previous_records": len(a), "revised_records": len(b),
            "shared_records": len(a & b), "added_records": len(b-a), "removed_records": len(a-b),
            "net_records": len(b)-len(a), "previous_unique_articles": len(ak),
            "revised_unique_articles": len(bk), "added_unique_articles": len(bk-ak),
            "removed_unique_articles": len(ak-bk), "net_unique_articles": len(bk)-len(ak)}


def report():
    field_checks = json.loads((PRIVATE / "field_checks.json").read_text())
    for check in field_checks:
        expected = int(check["field"] == "ABS" and
                       (check["scopus_id"], check["phrase"]) != ("84961190121", "information experiment"))
        if check["count"] != expected:
            raise ValueError("Field-check results differ from the documented observations; review the interpretation")
    write_csv(RDIR / "field_checks.csv", field_checks)
    frame = {r["source_id"] for r in read_csv(ROOT / "results/venue_frame.csv")}
    sets = {name: collect(families) for name, families in versions().items()}
    old, new = sets["previous"], sets["revised"]
    comparisons = [contrast(restrict(old, f), restrict(new, f), label)
                   for label, f in [("global", None), ("journal_frame", frame)]]
    write_csv(RDIR / "retrieval_comparison.csv", comparisons)
    stages = list(sets)
    changes = []
    for before, after in zip(stages, stages[1:]):
        if after == "initial_request":
            if not set(sets[after]) <= set(sets[before]):
                raise ValueError("Removing phrases unexpectedly added IDs; inspect index changes")
        elif not set(sets[before]) <= set(sets[after]):
            raise ValueError("Adding phrases unexpectedly removed IDs; inspect index changes")
        for scope, f in [("global", None), ("journal_frame", frame)]:
            changes.append({"change": after, **contrast(restrict(sets[before], f), restrict(sets[after], f), scope)})
    write_csv(RDIR / "sequential_changes.csv", changes)
    details = {}
    manifests = []
    for path in sorted((PRIVATE / "searches").glob("*.json")):
        saved = json.loads(path.read_text())
        manifests.append({"view": saved["view"], **saved["manifest"],
                          "private_snapshot": str(path.relative_to(ROOT)), "sha256": digest(path.read_bytes())})
        if saved["view"] == "COMPLETE":
            for e in saved["entries"]:
                details[e["dc:identifier"].replace("SCOPUS_ID:", "")] = e
    added, removed = set(new)-set(old), set(old)-set(new)
    if not (added | removed) <= set(details):
        raise ValueError("Changed result IDs lack full metadata, or the index changed between searches")
    gaps = collect([gap_family()])
    gap_extra = set(gaps)-set(new)
    if not gap_extra <= set(details):
        raise ValueError("Additional embedded-variant IDs lack full metadata")
    public, private, names = [], [], {}
    for label, ids in [("added", added), ("removed", removed), ("additional_embedded_variant", gap_extra)]:
        for sid in sorted(ids, key=int):
            row, authors = parse_entry(details[sid])
            in_frame = row["source_id"] in frame
            hits = query.match(row, revised_families()) if label != "additional_embedded_variant" else query.match(row, [gap_family()])
            row.update(change=label, in_frame=str(in_frame).lower(),
                       local_phrase_verified=str(bool(hits)).lower(),
                       matched_families="|".join(sorted({h["family"] for h in hits})))
            private.append(row)
            names.update({a["authid"]: a for a in authors})
            public.append({k: row[k] for k in ["change", "scopus_id", "doi", "title", "year", "journal", "source_id", "in_frame", "first_authid", "last_authid", "byline_complete", "local_phrase_verified", "matched_families"]})
    write_csv(RDIR / "changed_article_metadata.csv", public)
    write_csv(PRIVATE / "changed_articles_with_abstracts.csv", private)
    write_csv(RDIR / "changed_article_author_names.csv", sorted(names.values(), key=lambda r: int(r["authid"])))
    archived = read_csv(ROOT / "private/articles.csv")
    archive_entries = {r["scopus_id"]: {"dc:identifier": "SCOPUS_ID:"+r["scopus_id"], "prism:doi": r["doi"], "source-id": r["source_id"]} for r in archived}
    drift = [contrast(restrict(archive_entries, f), restrict(old, f), label)
             for label, f in [("global", None), ("journal_frame", frame)]]
    write_csv(RDIR / "archived_to_fresh_previous.csv", drift)
    dates = sorted({d for m in manifests for d in m["dates"]})
    added_in_frame = [r for r in private if r["change"] == "added" and r["in_frame"] == "true"]
    local_count = sum(r["local_phrase_verified"] == "true" for r in added_in_frame)
    verification = []
    definitions = versions()
    for before, after in zip(stages, stages[1:]):
        ids = set(sets[after])-set(sets[before])
        pool = [r for r in added_in_frame if r["scopus_id"] in ids]
        checked = sum(bool(query.match(r, definitions[after])) for r in pool)
        verification.append({"change": after, "added_in_frame_records": len(pool),
                             "locally_verified_records": checked,
                             "not_locally_verified_records": len(pool)-checked})
    write_csv(RDIR / "local_verification_by_change.csv", verification)
    summary = {"status": "complete retrieval comparison; added records require eligibility and geography review",
               "retrieval_start": dates[0], "retrieval_end": dates[-1], "publication_years": [query.START_YEAR, query.END_YEAR],
               "journal_frame_n": len(frame), "frame_sha256": digest((ROOT / "results/venue_frame.csv").read_bytes()),
               "previous_query_sha256": digest(query.build(previous_families())),
               "revised_query_sha256": digest(query.build(revised_families())),
               "comparison": comparisons, "sequential_changes": changes, "archived_to_fresh_previous": drift,
               "additional_embedded_variants": {"global_beyond_revised": len(gap_extra),
                   "in_frame_beyond_revised": sum(gaps[s].get("source-id") in frame for s in gap_extra),
                   "incorporated_in_requested_revision": False},
               "added_in_frame_local_verification": {"records": len(added_in_frame), "verified": local_count,
                   "not_verified": len(added_in_frame)-local_count,
                   "interpretation": "Phrase and same-sentence context verification only; not eligibility or precision validation."},
               "dashboard_updated_with_revision": False,
               "interpretation": "Set overlap measures retrieval change, not precision or recall. Sequential contributions depend on order; individual phrase hits overlap."}
    write_json(RDIR / "summary.json", summary)
    write_json(RDIR / "retrieval_manifests.json", manifests)
    render_report(summary)
    print(json.dumps(summary, indent=2))


def render_report(summary):
    from render import render
    s = next(r for r in summary["comparison"] if r["scope"] == "journal_frame")
    g = next(r for r in summary["comparison"] if r["scope"] == "global")
    archived = next(r for r in summary["archived_to_fresh_previous"] if r["scope"] == "journal_frame")
    labels = {
        "participants": "Add participant* to text assignment and question wording",
        "participants_messages": "Add the initial eight information/message assignment phrases",
        "initial_request": "Remove the four national-survey embedded-experiment phrases",
        "explicit_designs": "Add the 12 explicit survey-design phrases",
        "embedded_variants": "Add the eight generic in/within-survey phrases",
        "expanded_text_assignments": "Add the remaining six information/message assignment phrases",
        "revised": "Expand information experiments and add its participant* context",
    }
    steps = [r for r in summary["sequential_changes"] if r["scope"] == "journal_frame"]
    table = "\n".join(f"| {labels[r['change']]} | {r['net_unique_articles']:+,} | {r['revised_unique_articles']:,} |" for r in steps)
    literal = re.sub(r" OR (?=\{)", "\n      OR ", query.build(revised_families()))
    extra = summary["additional_embedded_variants"]
    local = summary["added_in_frame_local_verification"]
    verification = read_csv(RDIR / "local_verification_by_change.csv")
    info_check = next(r for r in verification if r["change"] == "revised")
    md = f"""The revised query retrieves **{s['revised_unique_articles']:,} distinct articles** within the same {summary['journal_frame_n']:,}-journal frame and 2010–2026 publication window. Relative to a fresh run of the previous query, it adds {s['added_unique_articles']:,} articles and loses {s['removed_unique_articles']:,}, a net change of **{s['net_unique_articles']:+,}** ({100*s['net_unique_articles']/s['previous_unique_articles']:.1f}%). These are candidate articles for screening, not confirmed eligible datasets or donors.

| Retrieval measure | Previous query, rerun | Revised query | Net change |
|---|---:|---:|---:|
| Global Scopus records | {g['previous_records']:,} | {g['revised_records']:,} | {g['net_records']:+,} |
| Records in the journal frame | {s['previous_records']:,} | {s['revised_records']:,} | {s['net_records']:+,} |
| Distinct in-frame articles after DOI deduplication | {s['previous_unique_articles']:,} | {s['revised_unique_articles']:,} | {s['net_unique_articles']:+,} |

The earlier archived search contained {archived['previous_unique_articles']:,} distinct in-frame articles. Rerunning that unchanged query now produces {archived['revised_unique_articles']:,}; this {archived['net_unique_articles']:+,} difference is database change, separate from the query revision. The dashboard's existing reviewed cohort remains attached to its archived query; the new retrieval has not yet been incorporated into its geography annotations or rankings.

The following changes are cumulative in the displayed order. Overlapping matches are credited once, so these contributions sum to the net change; they are not independent estimates of each phrase's value.

| Query change | Change in distinct in-frame articles | Cumulative articles |
|---|---:|---:|
{table}

“Survey-based experiments” was already present, together with its singular and unhyphenated forms. The revision adds 40 exact phrases, removes the four requested national-survey phrases, and permits `participant*` in the text-assignment, question-wording, and information-treatment context requirements. It introduces no design, country, provider, or representativeness exclusions. An article describing a national sample can still match another retained term. Longer phrases such as “experimental survey study” overlap with “experimental survey”; their presence does not imply an independent retrieval gain.

We also tested generic variants involving “embedded within,” plural “surveys,” and intervening verbs, such as “experiment was embedded in a survey.” That [separate diagnostic](queries/revision_2026_09_10/additional_embedded_variants.txt) identifies {extra['in_frame_beyond_revised']:,} further in-frame records beyond the revised query ({extra['global_beyond_revised']:,} globally). These variants are recorded separately from the requested query below.

**Retrieval and review.** The previous, revised, and intermediate versions were executed as unions of positive Scopus phrase-family searches. Identical clauses share the same archived responses. Every result page was retrieved and checked against the reported total; Source IDs determine journal-frame membership. We compare Scopus IDs locally and then compare normalized DOI identities, falling back to Scopus ID when DOI is absent. Full metadata for all added and removed records is retained privately for screening. Retrieval ran from {summary['retrieval_start']} to {summary['retrieval_end']}. [Counts](results/query_revision_2026_09_10/retrieval_comparison.csv), [cumulative contributions](results/query_revision_2026_09_10/sequential_changes.csv), and [added/removed article metadata](results/query_revision_2026_09_10/changed_article_metadata.csv) accompany the complete manifests in the repository.

Of the {local['records']:,} added in-frame records, **{local['verified']:,} pass the strict local phrase/context check** and {local['not_verified']:,} do not. The latter remain in a review queue: missing indexed keywords, context in another sentence, and punctuation-crossing database matches are possible reasons. Passing this check does not establish study eligibility. [Local verification by change](results/query_revision_2026_09_10/local_verification_by_change.csv).

The final information-family expansion adds {info_check['added_in_frame_records']} in-frame records, but only **{info_check['locally_verified_records']}** pass the local check for that stage. The returned records include clinical-treatment and visual-memory studies. “Experimental survey” also retrieves useful manipulated-scenario studies, survey-recruitment experiments, and a paper recommending an experimental survey as future research. These broad additions therefore require screening before researcher counts change; their additional hits should not be described as confirmed survey experiments.

Field-specific Scopus API checks found `ABS({{experimental survey}})` matching “experimental, survey” and `ABS({{information experiment}})` matching “information. Experiment.” `ABS({{information treatment}})` also matched “information: Treatment” in clinical-trial registration text. For these examples, the same phrase returned zero title and keyword matches. Thus braces alone did not prevent the punctuation errors in the tested endpoint. The local matcher rejects these strings. [Queries and observed field counts](results/query_revision_2026_09_10/field_checks.csv) document the tests; the underlying responses and full abstracts remain private.

Retrieval gains do not establish precision or recall. Eligibility requires inspection of the treatment, response structure, original fielding, and access to respondent data and survey materials. These additions have not received geography annotation or independent eligibility validation.

**Complete revised query.** The query searches titles, abstracts, and keywords. Curly braces request exact phrases, with singular/plural and spelling variants enumerated explicitly. [Elsevier's documented syntax](https://dev.elsevier.com/sc_search_tips.html) describes punctuation-sensitive matching; the observed exceptions above make a separate local check necessary. The pipeline applies the journal frame using Source IDs. [Download revised query](queries/revision_2026_09_10/revised.txt) · [Previous query](queries/revision_2026_09_10/previous.txt).

```text
{literal}
```

Reproduce the archived comparison with `python3 pipeline/query_revision.py report`; `retrieve` resumes the dated API snapshot, and `all` retrieves and reports. A subsequent live comparison requires a new dated namespace to preserve this snapshot.
"""
    examples_path = ROOT / "inputs/query_revision_screening_examples.csv"
    if examples_path.exists():
        examples = read_csv(examples_path)
        paragraphs = [f"| [{r['title']}](https://doi.org/{r['doi']}) | {r['assessment']} |" for r in examples]
        if paragraphs:
            md += ("\n**Illustrative abstract checks.** These selected examples describe eligibility concerns and useful additions; they are not a precision estimate.\n\n"
                   "| Article | Abstract-based assessment |\n|---|---|\n" + "\n".join(paragraphs) + "\n")
    md += "\n[Open the reviewed researcher dashboard](TOP100.html#summary).\n"
    (ROOT / "QUERY_REVISION.md").write_text(md)
    (ROOT / "QUERY_REVISION.html").write_text(render(md, "Revised query and retrieval comparison"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["queries", "retrieve", "report", "all"])
    parser.add_argument("--workers", type=int, default=4, choices=range(1, 9))
    args = parser.parse_args()
    if args.stage == "queries":
        write_queries()
    if args.stage in {"retrieve", "all"}:
        retrieve(args.workers)
    if args.stage in {"report", "all"}:
        report()
