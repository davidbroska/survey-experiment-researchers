"""Isolated retrieval comparison for participant* in two remaining population gates.

This snapshot extends the executed 2026-09-10 revision without changing it or the
reviewed dashboard. Unchanged family memberships reuse that revision's archived
responses; the two changed positive family queries are retrieved separately.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json

from common import ROOT, digest, read_csv, write_csv, write_json
import query
import query_revision as previous
import scopus
from run import parse_entry

VERSION = "participant_guards_2026_09_10"
QDIR, RDIR, PRIVATE = (ROOT / part / VERSION for part in ("queries", "results", "private"))
CHANGED_FAMILIES = {"embedded_design", "contextual_design"}
FIELDS = ("title", "abstract", "keywords", "indexed_keywords")


def revised_families():
    families = deepcopy(previous.revised_families())
    for family in families:
        if family["id"] in CHANGED_FAMILIES:
            family["participant_context"] = True
    return families


def write_queries():
    QDIR.mkdir(parents=True, exist_ok=True)
    (QDIR / "previous.txt").write_text(query.build(previous.revised_families()) + "\n")
    (QDIR / "revised.txt").write_text(query.build(revised_families()) + "\n")
    write_json(QDIR / "families.json", revised_families())
    write_csv(QDIR / "executed_family_queries.csv", [
        {"family": f["id"], "query": previous.family_query(f),
         "membership_source": VERSION if f["id"] in CHANGED_FAMILIES else previous.NAMESPACE}
        for f in revised_families()])


def snapshot_path(q, view):
    return PRIVATE / "searches" / (digest(json.dumps({"query": q, "view": view}, sort_keys=True)) + ".json")


def load(q, view="STANDARD"):
    saved = json.loads(snapshot_path(q, view).read_text())
    if saved["manifest"]["query"] != q or not saved["manifest"]["complete"]:
        raise ValueError("Incomplete or mismatched snapshot")
    return saved


def fetch(q, view="STANDARD"):
    path = snapshot_path(q, view)
    if not path.exists():
        entries, manifest = scopus.search(q, view=view, namespace=VERSION)
        write_json(path, {"view": view, "manifest": manifest, "entries": entries})
    return load(q, view)


def collect():
    entries = {}
    for f in revised_families():
        loader = load if f["id"] in CHANGED_FAMILIES else previous.load
        for entry in loader(previous.family_query(f))["entries"]:
            sid = entry["dc:identifier"].replace("SCOPUS_ID:", "")
            if sid not in entries or json.dumps(entry, sort_keys=True) < json.dumps(entries[sid], sort_keys=True):
                entries[sid] = entry
    return entries


def article_context_match(row, families):
    """Require literal phrases within units, but permit guards anywhere in metadata.

    This separates the database's article-level Boolean semantics from the stricter
    same-sentence local rule. Neither check is an eligibility annotation, and the
    absent Scopus indexed-keyword field prevents exact database emulation.
    """
    texts = [query.normalize(row.get(field, "") or "") for field in FIELDS]
    units = list(query.units(row))
    hits = []
    for family in families:
        context_rx = query.PARTICIPANT_CONTEXT_RX if family.get("participant_context") else query.CONTEXT_RX
        if family.get("context") and not any(context_rx.search(t) for t in texts):
            continue
        if family.get("random") and not any(query.RANDOM_RX.search(t) for t in texts):
            continue
        for field, normalized, original in units:
            for phrase in family["phrases"]:
                if query.phrase_rx(phrase).search(normalized):
                    hits.append({"family": family["id"], "field": field,
                                 "phrase": phrase, "evidence": original})
                    break
    return hits


def retrieve(workers=3):
    write_queries()
    jobs = [previous.family_query(f) for f in revised_families() if f["id"] in CHANGED_FAMILIES]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for saved in pool.map(fetch, jobs):
            print("Changed family membership:", saved["manifest"]["retrieved"], flush=True)
    old, new = previous.collect(previous.revised_families()), collect()
    targets = sorted(set(old) ^ set(new), key=int)
    batches = [targets[i:i + 25] for i in range(0, len(targets), 25)]
    def detail(ids):
        if not all(s.isdigit() for s in ids):
            raise ValueError("Invalid Scopus identifier")
        q = "(" + " OR ".join("EID(2-s2.0-" + sid + ")" for sid in ids) + ")"
        saved = fetch(q, "COMPLETE")
        actual = {e["dc:identifier"].replace("SCOPUS_ID:", "") for e in saved["entries"]}
        if actual != set(ids):
            raise ValueError("Detail lookup did not return exactly the requested IDs")
        return saved
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, saved in enumerate(pool.map(detail, batches), 1):
            print(f"Changed metadata {i}/{len(batches)}: {saved['manifest']['retrieved']}", flush=True)


def report():
    frame = {r["source_id"] for r in read_csv(ROOT / "results/venue_frame.csv")}
    old, new = previous.collect(previous.revised_families()), collect()
    scopes = [("global", None), ("journal_frame", frame)]
    comparisons = [previous.contrast(previous.restrict(old, f), previous.restrict(new, f), label)
                   for label, f in scopes]
    by_family = []
    for revised in revised_families():
        if revised["id"] not in CHANGED_FAMILIES:
            continue
        before = next(f for f in previous.revised_families() if f["id"] == revised["id"])
        a = {e["dc:identifier"].replace("SCOPUS_ID:", ""): e for e in previous.load(previous.family_query(before))["entries"]}
        b = {e["dc:identifier"].replace("SCOPUS_ID:", ""): e for e in load(previous.family_query(revised))["entries"]}
        by_family.extend({"family": revised["id"], **previous.contrast(previous.restrict(a, f), previous.restrict(b, f), label)}
                         for label, f in scopes)
    details, manifests = {}, []
    for path in sorted((PRIVATE / "searches").glob("*.json")):
        saved = json.loads(path.read_text())
        manifests.append({"view": saved["view"], **saved["manifest"],
                          "private_snapshot": str(path.relative_to(ROOT)), "sha256": digest(path.read_bytes())})
        if saved["view"] == "COMPLETE":
            details.update({e["dc:identifier"].replace("SCOPUS_ID:", ""): e for e in saved["entries"]})
    if not (set(old) ^ set(new)) <= details.keys():
        raise ValueError("Changed records lack full metadata")
    rows, names, evidence = [], {}, []
    for change, ids in [("added", set(new) - set(old)), ("removed", set(old) - set(new))]:
        for sid in sorted(ids, key=int):
            row, authors = parse_entry(details[sid])
            strict = query.match(row, revised_families())
            loose = article_context_match(row, revised_families())
            row.update(change=change, in_frame=str(row["source_id"] in frame).lower(),
                       same_sentence_verified=str(bool(strict)).lower(),
                       article_context_verified=str(bool(loose)).lower(),
                       same_sentence_families="|".join(sorted({h["family"] for h in strict})),
                       article_context_families="|".join(sorted({h["family"] for h in loose})))
            rows.append(row)
            names.update({a["authid"]: a for a in authors})
            evidence.extend({"scopus_id": sid, "guard_scope": scope, **hit}
                            for scope, hits in [("same_sentence", strict), ("article", loose)] for hit in hits)
    fields = ["change", "scopus_id", "doi", "title", "year", "journal", "source_id", "in_frame",
              "first_authid", "last_authid", "byline_complete", "same_sentence_verified", "article_context_verified",
              "same_sentence_families", "article_context_families"]
    write_csv(RDIR / "retrieval_comparison.csv", comparisons)
    write_csv(RDIR / "family_comparison.csv", by_family)
    write_csv(RDIR / "changed_article_metadata.csv", rows, fields)
    write_csv(RDIR / "changed_article_author_names.csv", sorted(names.values(), key=lambda r: int(r["authid"])))
    write_csv(PRIVATE / "changed_articles_with_abstracts.csv", rows)
    write_csv(PRIVATE / "local_evidence.csv", evidence)
    checks = []
    for label, frame_filter in scopes:
        added = [r for r in rows if r["change"] == "added" and (frame_filter is None or r["source_id"] in frame_filter)]
        checks.append({"scope": label, "added_records": len(added),
                       "same_sentence_verified": sum(r["same_sentence_verified"] == "true" for r in added),
                       "article_context_verified": sum(r["article_context_verified"] == "true" for r in added)})
    write_csv(RDIR / "local_verification.csv", checks)
    dates = sorted({date for m in manifests for date in m["dates"]})
    summary = {"status": "retrieval comparison complete; eligibility and geography review pending",
               "comparison_baseline": "queries/revision_2026_09_10/revised.txt",
               "previous_query_sha256": digest(query.build(previous.revised_families())),
               "revised_query_sha256": digest(query.build(revised_families())),
               "changed_families": sorted(CHANGED_FAMILIES), "comparison": comparisons,
               "family_comparison": by_family, "local_verification": checks,
               "retrieval_start": dates[0], "retrieval_end": dates[-1],
               "unchanged_memberships_reused_from": previous.NAMESPACE,
               "previous_membership_records_missing_after_expansion": len(set(old) - set(new)),
               "journal_frame_n": len(frame), "frame_sha256": digest((ROOT / "results/venue_frame.csv").read_bytes()),
               "dashboard_updated": False,
               "interpretation": "Positive clause set differences measure retrieval change, not precision or recall. Literal phrase verification and population guards are reported separately from study eligibility. Article-level context allows population/randomization words in other metadata sentences; same-sentence verification reproduces the existing strict local rule. Indexed keywords may be absent from downloaded metadata."}
    write_json(RDIR / "summary.json", summary)
    write_json(RDIR / "retrieval_manifests.json", manifests)
    in_frame = next(c for c in comparisons if c["scope"] == "journal_frame")
    local = next(c for c in checks if c["scope"] == "journal_frame")
    (RDIR / "README.md").write_text(f"""Adding `participant*` to the contextual-design and embedded-design population gates increases the executed revised search from **{in_frame['previous_unique_articles']:,} to {in_frame['revised_unique_articles']:,} distinct in-frame articles** ({in_frame['added_unique_articles']:+,}; {in_frame['removed_unique_articles']} lost). The publication window is 2010–2026 and the journal frame remains {len(frame):,} journals.

The embedded-design gate adds no records: all of its phrases already contain “survey.” The contextual-design family adds 69 in-frame records, of which one already matched another family, leaving 68 additional articles in the full union. It covers framing, information-provision and scenario-based experiments. The complete [query](../../queries/{VERSION}/revised.txt) retains all previously requested additions and removals and adds no explicit design exclusions.

All **{local['article_context_verified']}** added in-frame records contain a literal design phrase and population context somewhere in the available article metadata. Only **{local['same_sentence_verified']}** have the two in the same local sentence. This difference measures sensitivity to the local context rule; neither count establishes study eligibility, precision or recall. A contextual word in another sentence can correctly describe the sample, or it can refer to an unrelated or previous study. Indexed keywords are not included in the downloaded COMPLETE metadata.

The two modified positive family queries were retrieved on {dates[0][:10]}. Unchanged families reuse the immediately preceding revision's immutable memberships. Comparisons use Scopus IDs and normalized DOI identities, with Scopus IDs as the fallback when DOI is absent. Full metadata for every changed record is archived privately. No reviewed dashboard rankings or annotations were replaced.

Reproduce this comparison offline with `python3 pipeline/participant_guards.py report`; `all` resumes the archived retrieval and regenerates the outputs. [Comparison counts](retrieval_comparison.csv), [family counts](family_comparison.csv), [article metadata](changed_article_metadata.csv), and [local checks](local_verification.csv) provide the audit trail. Selected [screening examples](screening_examples.csv) illustrate interpretation and are not a representative precision sample.
""")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["queries", "retrieve", "report", "all"])
    parser.add_argument("--workers", type=int, default=3, choices=range(1, 5))
    args = parser.parse_args()
    if args.stage == "queries":
        write_queries()
    if args.stage in {"retrieve", "all"}:
        retrieve(args.workers)
    if args.stage in {"report", "all"}:
        report()
