"""Frozen refined survey-experiment candidate query and independent sample.

This is a retrieval and validation instrument, not a confirmed-eligibility rank.
The refinement follows the initial development audit; no held-out labels inform
its terms. Licensed metadata and coding packets remain under private/.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

from common import ROOT, digest, now, read_csv, write_csv, write_json
import design_audit as audit
import participant_guards
import query
import scopus
from run import parse_entry

VERSION = "search_strategy_2026_09_10"
PRIVATE = ROOT / "private" / VERSION
RESULTS = ROOT / "results" / VERSION
QUERIES = ROOT / "queries" / VERSION
BASE_LABELS = tuple(audit.LABELS)
EXTRA_LABELS = ("survey based random* experiment*",)
GUARDED_LABELS = ("framing experiment*", "information provision experiment*",
    "scenario based experiment*", "information treatment*", "informational treatment*",
    "information experiment*", "wording experiment*", "embedded experiment*")
READING_LABELS = ("random* assign* to read", "random* allocat* to read",
                  "random* select* to read", "random* to read")
DESIGN = 'experiment* OR random* OR manipulat* OR "control condition*" OR "control group*"'
OUTCOME = "attitud* OR belief* OR opinion* OR intention* OR judgment* OR judgement*"
STIMULUS = "message* OR text OR textual OR written OR vignette* OR scenario* OR headline* OR prompt*"
ACTION = "read* OR view* OR expos* OR present* OR receiv* OR shown"
SURVEY = "survey* OR questionnaire* OR respondent* OR participant*"
HUMAN = "participant* OR respondent* OR survey* OR questionnaire* OR human*"
PARTS = ("named_base", "named_extra", "guarded_design", "procedure", "reading_assignment")


def phrases(values):
    return " OR ".join('"' + p + '"' for p in values)


def field(value, name="TITLE-ABS-KEY"):
    return name + "(" + value + ")"


def clauses():
    return {
        "named_base": field(phrases(BASE_LABELS)),
        "named_extra": field(phrases(EXTRA_LABELS)),
        "guarded_design": " AND ".join((field(phrases(GUARDED_LABELS)), field(SURVEY), field("random* OR experiment*"))),
        "procedure": " AND ".join((field(DESIGN, "TITLE-ABS"), field(OUTCOME, "TITLE-ABS"), field(HUMAN),
            "(" + field(STIMULUS, "TITLE-ABS") + " OR " + field("(" + ACTION + ") W/5 information", "TITLE-ABS") + ")")),
        "reading_assignment": field(phrases(READING_LABELS)) + " AND " + field(SURVEY),
    }


def part_query(name):
    return "(" + clauses()[name] + ") AND " + query.LIMITS


def full_query():
    labels = "\n      OR ".join('"' + p + '"' for p in BASE_LABELS + EXTRA_LABELS)
    guarded = "\n        OR ".join('"' + p + '"' for p in GUARDED_LABELS)
    reading = "\n        OR ".join('"' + p + '"' for p in READING_LABELS)
    return (
        "(\n  TITLE-ABS-KEY(\n      " + labels + "\n  )"
        + "\n  OR (\n    TITLE-ABS-KEY(\n        " + guarded + "\n    )"
        + "\n    AND " + field(SURVEY) + "\n    AND " + field("random* OR experiment*") + "\n  )"
        + "\n  OR (\n    " + field(DESIGN, "TITLE-ABS")
        + "\n    AND " + field(OUTCOME, "TITLE-ABS")
        + "\n    AND " + field(HUMAN)
        + "\n    AND (\n      " + field(STIMULUS, "TITLE-ABS")
        + "\n      OR " + field("(" + ACTION + ") W/5 information", "TITLE-ABS") + "\n    )\n  )"
        + "\n  OR (\n    TITLE-ABS-KEY(\n        " + reading + "\n    )"
        + "\n    AND " + field(SURVEY) + "\n  )\n)"
        + "\nAND SRCTYPE(j)\nAND DOCTYPE(ar)\nAND PUBYEAR > 2009\nAND PUBYEAR < 2027"
    )


def freeze():
    protocol = {
        "version": VERSION, "query_sha256": digest(full_query()),
        "part_sha256": {name: digest(part_query(name)) for name in PARTS},
        "frame_sha256": digest((ROOT / "results/venue_frame.csv").read_bytes()),
        "comparator_query_sha256": digest(query.build(participant_guards.revised_families())),
        "development_exclusion_sha256": digest((audit.RESULTS / "development_exclusions.csv").read_bytes()),
        "development_sample_sha256": digest((audit.RESULTS / "development_sample.csv").read_bytes()),
        "rationale": "Initial development exposed substantial irrelevant retrieval from broad information/perception/texture matches. The refined candidate preserves named designs and randomized reading assignments, restores guarded design expressions, restricts broad procedural evidence to title/abstract, adds a human-context gate, and removes perception/preference/text-prefix terms from that route. No claim of validated precision follows from this refinement.",
        "validation_plan": "One fixed simple random hash sample of 100 DOI-deduplicated candidate articles, excluding all archived inherited/focal development material and the 160 fresh development records by Scopus aliases, DOI or normalized title hash. Two independent AI coders; human adjudication needed before manuscript precision claims.",
        "sample_estimand": "Candidate-query articles outside archived development material, not all social-science experiments or all records in the candidate union.",
        "positive_terms_only": True, "author_or_topic_terms": False,
        "punctuation_policy": "Database loose phrases retrieve candidates; punctuation-sensitive evidence checking and study-level screening remain separate. Database matches do not automatically establish eligibility.",
        "indexed_keywords_policy": "Design/stimulus/outcome procedural evidence is sought in TITLE-ABS; named designs and human context also search keywords. Complete API metadata lacks indexed keywords, so missing local evidence is unresolved.",
        "freeze_boundary": "Terms fixed after initial development and before this held-out sample is annotated.",
    }
    outputs = {QUERIES / "candidate.txt": full_query() + "\n"}
    outputs.update({QUERIES / (name + ".txt"): part_query(name) + "\n" for name in PARTS})
    protocol_path = RESULTS / "protocol.json"
    if protocol_path.exists():
        saved = json.loads(protocol_path.read_text())
        if {k: v for k, v in saved.items() if k != "frozen_at"} != protocol:
            raise ValueError("Frozen strategy, source frame or development material changed; create a new version")
    for path, value in outputs.items():
        if path.exists() and path.read_text() != value:
            raise ValueError("Frozen query artifact changed: " + path.name)
    for path, value in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(value)
    if not protocol_path.exists():
        write_json(protocol_path, {"frozen_at": now(), **protocol})
    return protocol


def fetch(q, view="STANDARD"):
    path = PRIVATE / "searches" / (digest(json.dumps({"query": q, "view": view}, sort_keys=True)) + ".json")
    if path.exists():
        saved = json.loads(path.read_text())
    else:
        entries, manifest = scopus.search(q, view=view, namespace=VERSION)
        saved = {"view": view, "manifest": manifest, "entries": entries}
        write_json(path, saved)
    if saved["view"] != view or not saved["manifest"]["complete"] or saved["manifest"]["query"] != q:
        raise ValueError("Incomplete or mismatched strategy snapshot")
    return saved


def fetch_part(name):
    q = part_query(name)
    if name == "named_base":
        if q != "(" + audit.routes()["labels"] + ") AND " + query.LIMITS:
            raise ValueError("The reused named-label route changed")
        return audit.fetch(q)
    return fetch(q)


def retrieve(workers=4):
    freeze()
    write_csv(QUERIES / "executed_parts.csv", [{"part": name, "query": part_query(name),
        "snapshot_namespace": audit.VERSION if name == "named_base" else VERSION} for name in PARTS])
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch_part, name): name for name in PARTS}
        for i, future in enumerate(as_completed(futures), 1):
            saved = future.result()
            print(f"{i}/{len(PARTS)} {futures[future]}: {saved['manifest']['retrieved']} records", flush=True)
    summarize()


def initial_comparators():
    result = {"initial_" + v: {} for v in ("concepts", "exposure", "exposure_human")}
    for row in read_csv(audit.RESULTS / "membership.csv"):
        for name in result:
            if row["labels"] != "true" and row[name.removeprefix("initial_")] != "true":
                continue
            for sid in row["all_scopus_ids"].split("|"):
                result[name][sid] = {"dc:identifier": "SCOPUS_ID:" + sid, "prism:doi": row["doi"]}
    return result


def memberships():
    frame = audit.frame_ids()
    snapshots, manifests = {}, []
    for name in PARTS:
        saved = fetch_part(name)
        snapshots[name] = {e["dc:identifier"].replace("SCOPUS_ID:", ""): e
                           for e in saved["entries"] if e.get("source-id", "") in frame}
        manifests.append({"part": name, "snapshot_namespace": audit.VERSION if name == "named_base" else VERSION,
                          **saved["manifest"]})
    snapshots["latest_revised"] = {sid: e for sid, e in participant_guards.collect().items()
                                    if e.get("source-id", "") in frame}
    snapshots.update(initial_comparators())
    canonical, conflicts = audit.canonicalize_snapshots(snapshots)
    write_csv(RESULTS / "doi_identity_conflicts.csv", conflicts, ["scopus_id", "normalized_dois"])
    if conflicts:
        raise ValueError("DOI conflicts across strategy snapshots")
    write_json(RESULTS / "retrieval_manifests.json", manifests)
    return canonical, manifests


def summarize():
    freeze()
    snapshots, manifests = memberships()
    candidate = {}
    for part in PARTS:
        candidate.update(snapshots[part])
    candidate_keys = {audit.identity(e) for e in candidate.values()}
    sets = {name: {audit.identity(e) for e in entries.values()} for name, entries in snapshots.items()}
    comparison = []
    for name in ("latest_revised", "initial_concepts", "initial_exposure", "initial_exposure_human"):
        before = sets[name]
        comparison.append({"comparator": name, "comparator_unique_articles": len(before),
            "candidate_unique_articles": len(candidate_keys), "shared": len(candidate_keys & before),
            "added": len(candidate_keys - before), "lost": len(before - candidate_keys),
            "net": len(candidate_keys) - len(before), "status": "Candidate retrieval; eligibility unvalidated"})
    write_csv(RESULTS / "retrieval_comparison.csv", comparison)
    route_rows, preceding = [], set()
    manifest_map = {r["part"]: r for r in manifests}
    for part in PARTS:
        keys = sets[part]
        route_rows.append({"part": part, "global_records": manifest_map[part]["retrieved"],
            "in_frame_records": len(snapshots[part]), "in_frame_unique_articles": len(keys),
            "added_in_route_order": len(keys - preceding),
            "unique_to_route_within_candidate": len(keys - set().union(*(sets[p] for p in PARTS if p != part))),
            "beyond_latest_revised": len(keys - sets["latest_revised"]),
            "status": "Routes overlap; marginal yield depends on route order"})
        preceding |= keys
    write_csv(RESULTS / "route_counts.csv", route_rows)
    # Compare all old and new records but retain article membership on DOI aliases.
    entries = {**snapshots["latest_revised"], **candidate}
    by_identity = {}
    for sid, entry in sorted(entries.items(), key=lambda kv: int(kv[0])):
        by_identity.setdefault(audit.identity(entry), []).append(sid)
    metadata = []
    for identity, ids in sorted(by_identity.items()):
        selected_sid = next((sid for sid in ids if sid in candidate), ids[0])
        parsed, _ = parse_entry(entries[selected_sid])
        row = {k: parsed[k] for k in ("scopus_id", "doi", "year", "source_id", "journal", "title")}
        row.update(identity=identity, all_scopus_ids="|".join(ids), candidate=str(identity in candidate_keys).lower())
        for name, keys in sets.items():
            row[name] = str(identity in keys).lower()
        metadata.append(row)
    write_csv(RESULTS / "membership.csv", metadata)
    print(json.dumps(comparison, indent=2), flush=True)
    return metadata


def frozen_exclusions():
    ledger = audit.development_exclusions([], {})
    sample_path = audit.RESULTS / "development_sample.csv"
    sample = read_csv(sample_path)
    manifest = json.loads((audit.RESULTS / "development_sample_manifest.json").read_text())
    if manifest["sample_sha256"] != digest(json.dumps(sample, sort_keys=True)):
        raise ValueError("Initial development sample changed")
    fresh = [{"scopus_id": sid, "doi": r["doi"], "normalized_title_sha256": audit.title_hash(r["title"]),
              "reasons": "initial_fresh_development"}
             for r in sample for sid in r["all_scopus_ids"].split("|")]
    return ledger + fresh


def available_metadata():
    available = audit.corpus()
    for path in sorted((PRIVATE / "searches").glob("*.json")):
        saved = json.loads(path.read_text())
        if saved["view"] == "COMPLETE":
            for entry in saved["entries"]:
                row, _ = parse_entry(entry)
                available[row["scopus_id"]] = row
    return available


def sample(n=100):
    if n != 100:
        raise ValueError("This frozen protocol specifies 100 held-out articles")
    protocol = freeze()
    members = read_csv(RESULTS / "membership.csv")
    ledger = frozen_exclusions()
    indexes = audit.exclusion_indexes(ledger)
    eligible = [r for r in members if r["candidate"] == "true" and not audit.excluded_by_indexes(r, indexes)]
    if len(eligible) < n:
        raise ValueError("Insufficient disjoint candidate articles")
    seed = VERSION + ":validation"
    eligible.sort(key=lambda r: digest(seed + ":" + r["identity"]))
    selected = [{**r, "stage": "validation", "stratum": "heldout_candidate_union", "stratum_N": len(eligible),
                 "stratum_n": n, "inclusion_probability": n / len(eligible),
                 "selection_hash": digest(seed + ":" + r["identity"])} for r in eligible[:n]]
    audit.freeze_selection(RESULTS / "validation_sample.csv", selected, {
        "stage": "validation", "selected_variant": VERSION, "query_sha256": protocol["query_sha256"],
        "membership_sha256": digest((RESULTS / "membership.csv").read_bytes()), "frame_sha256": protocol["frame_sha256"],
        "development_exclusion_sha256": protocol["development_exclusion_sha256"],
        "development_sample_sha256": protocol["development_sample_sha256"],
        "requested_n": n, "selection_seed": seed, "estimand": protocol["sample_estimand"]})
    available = available_metadata()
    missing = [r["scopus_id"] for r in selected if r["scopus_id"] not in available]
    def batch(ids):
        saved = fetch("(" + " OR ".join("EID(2-s2.0-" + sid + ")" for sid in ids) + ")", "COMPLETE")
        if {e["dc:identifier"].replace("SCOPUS_ID:", "") for e in saved["entries"]} != set(ids):
            raise ValueError("Held-out detail lookup is incomplete")
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(batch, [missing[i:i+25] for i in range(0, len(missing), 25)]))
    available = available_metadata()
    fields = ("scopus_id", "doi", "year", "journal", "title", "abstract", "keywords")
    packet = [{key: available[r["scopus_id"]].get(key, "") for key in fields} for r in selected]
    packet.sort(key=lambda row: digest(VERSION + ":blind:" + row["scopus_id"]))
    packet_path = PRIVATE / "validation_packet.json"
    if packet_path.exists() and json.loads(packet_path.read_text()) != packet:
        raise ValueError("Frozen blinded packet changed")
    if not packet_path.exists():
        write_json(packet_path, packet)
        write_csv(PRIVATE / "validation_packet.csv", packet)
    write_json(RESULTS / "validation_packet_provenance.json", {
        "n_records": len(packet), "packet_sha256": digest(packet_path.read_bytes()),
        "public_sample_sha256": digest((RESULTS / "validation_sample.csv").read_bytes()),
        "fields": list(fields), "authors_and_routes_omitted": True,
        "n_candidate_articles": sum(r["candidate"] == "true" for r in members),
        "n_after_development_exclusions": len(eligible),
        "n_excluded_from_sampling": sum(r["candidate"] == "true" for r in members) - len(eligible),
        "annotation_status": "Awaiting independent coding; no gold-standard precision claim"})
    print(f"Held-out packet ready: {len(packet)} articles from {len(eligible)} eligible candidate articles", flush=True)


def author_comparison():
    """Describe nominated-author coverage only as an exposed development check."""
    membership = read_csv(RESULTS / "membership.csv")
    by_sid = {sid: row for row in membership for sid in row["all_scopus_ids"].split("|")}
    by_doi = {audit.normalize_doi(r["doi"]): r for r in membership if r["doi"]}
    initial_rows = read_csv(audit.RESULTS / "membership.csv")
    initial_by_sid = {sid: row for row in initial_rows for sid in row["all_scopus_ids"].split("|")}
    initial_by_doi = {audit.normalize_doi(r["doi"]): r for r in initial_rows if r["doi"]}
    articles = read_csv(audit.PRIVATE / "author_articles.csv")
    fields = ("latest_revised", "initial_concepts", "initial_exposure", "initial_exposure_human", "candidate")
    output = []
    for focal in ("pennycook", "richeson"):
        corpus = [r for r in articles if r["focal"] == focal]
        for variant in fields:
            selected = {}
            for row in corpus:
                if variant.startswith("initial_"):
                    m = initial_by_sid.get(row["scopus_id"], initial_by_doi.get(audit.normalize_doi(row["doi"]), {}))
                    hit = m.get("labels") == "true" or m.get(variant.removeprefix("initial_")) == "true"
                else:
                    m = by_sid.get(row["scopus_id"], by_doi.get(audit.normalize_doi(row["doi"]), {}))
                    hit = m.get(variant) == "true"
                if hit:
                    selected.setdefault(m["identity"], []).append(row)
            output.append({"researcher": focal, "variant": variant, "articles_any_position": len(selected),
                "first_last_candidate_articles": sum(any(v["first_last"].lower() == "true" and v.get("byline_complete") == "true"
                                                          for v in values) for values in selected.values()),
                "status": "Exposed development examples; retrieval only, not eligible counts or recall"})
    write_csv(RESULTS / "author_development_comparison.csv", output)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("freeze", "retrieve", "summarize", "sample", "author_comparison", "all"))
    args = parser.parse_args()
    if args.command == "all":
        retrieve()
        author_comparison()
        sample()
    else:
        globals()[args.command]()
