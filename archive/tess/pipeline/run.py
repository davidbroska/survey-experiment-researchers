"""Command-line pipeline. Run `python3 pipeline/run.py --help` from the package."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import re
import shutil

from common import ROOT, REPO, as_list, digest, now, read_csv, write_csv, write_json
import query
import scopus


def bootstrap():
    imports = {
        "tess_investigators.csv": "Opencall/TessVenues/tess_authors_resolved.csv",
        "legacy_investigator_journals.csv": "Opencall/TessVenues/tess_author_journals.csv",
    }
    manifest = []
    for name, relative in imports.items():
        src = REPO / relative
        dst = ROOT / "inputs" / name
        dst.parent.mkdir(exist_ok=True)
        if not dst.exists():
            shutil.copyfile(src, dst)
        manifest.append({"input": str(dst.relative_to(ROOT)), "source": relative,
            "sha256": digest(dst.read_bytes()), "imported_at": now(),
            "note": "Legacy frozen roster; profile assignments are inherited, not revalidated."})
    write_json(ROOT / "inputs" / "provenance.json", manifest)
    seed = read_csv(ROOT / "inputs" / "tess_investigators.csv")
    write_csv(ROOT / "results" / "seed_identity_review.csv", [r for r in seed if r["confidence"] != "high"])
    query.write_queries()
    build_frame(ROOT / "inputs" / "legacy_investigator_journals.csv", "legacy_2016_onward_capped")
    print(f"Imported {len(seed)} legacy seed rows ({len({r['auid'] for r in seed if r['auid']})} distinct resolved Scopus IDs).", flush=True)


def build_frame(path, origin, threshold=1):
    agg = {}
    missing = []
    for r in read_csv(path):
        if not r["source_id"]:
            missing.append(r)
            continue
        a = agg.setdefault(r["source_id"], {"source_id": r["source_id"], "journal": r["journal"],
            "issn": r.get("issn", ""), "authors": set(), "n_articles": 0})
        a["authors"].add(r["auid"])
        a["n_articles"] += int(r["n_articles"])
    rows = [{"source_id": k, "journal": a["journal"], "issn": a["issn"],
             "n_tess_investigators": len(a["authors"]), "investigator_article_links": a["n_articles"],
             "frame_origin": origin} for k, a in agg.items() if len(a["authors"]) >= threshold]
    write_csv(ROOT / "results" / "venue_frame.csv", sorted(rows, key=lambda r: int(r["source_id"])))
    write_csv(ROOT / "results" / "missing_source_ids.csv", missing, ["auid", "journal", "source_id", "n_articles"])
    write_json(ROOT / "results" / "frame_manifest.json", {"origin": origin, "threshold": threshold,
        "n_journals": len(rows), "n_investigators_with_journals": len({r['auid'] for r in read_csv(path)}),
        "input_sha256": digest(path.read_bytes()), "missing_source_rows": len(missing), "built_at": now()})
    print(f"Frame: {len(rows)} journals; origin={origin}", flush=True)


def refresh_frame(workers):
    seeds = {r["auid"]: r for r in read_csv(ROOT / "inputs" / "tess_investigators.csv") if r["auid"]}
    def fetch(item):
        aid, seed = item
        path = ROOT / "private" / "frame" / (aid + ".json")
        q = f"AU-ID({aid}) AND SRCTYPE(j) AND DOCTYPE(ar) AND PUBYEAR < {query.END_YEAR+1}"
        if path.exists():
            saved = json.loads(path.read_text())
            if saved["manifest"]["query"] == q and saved["manifest"]["complete"]:
                return saved
        entries, manifest = scopus.search(q, view="STANDARD")
        agg = {}
        for e in entries:
            sid = e.get("source-id", "")
            key = sid or e.get("prism:publicationName", "")
            rec = agg.setdefault(key, {"auid": aid, "author_name": seed["author_name"],
                "source_id": sid, "journal": e.get("prism:publicationName", ""),
                "issn": e.get("prism:issn", "") or e.get("prism:eIssn", ""), "n_articles": 0})
            rec["n_articles"] += 1
        saved = {"manifest": manifest, "rows": list(agg.values())}
        write_json(path, saved)
        return saved
    rows, manifests = [], []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, fut in enumerate(as_completed([pool.submit(fetch, item) for item in seeds.items()]), 1):
            result = fut.result()
            rows.extend(result["rows"])
            manifests.append(result["manifest"])
            if i % 25 == 0 or i == len(seeds):
                print(f"Journal histories: {i}/{len(seeds)} complete", flush=True)
    rows.sort(key=lambda r: (int(r["auid"]), r["source_id"], r["journal"]))
    out = ROOT / "inputs" / "investigator_journals.csv"
    write_csv(out, rows)
    write_json(ROOT / "results" / "frame_retrieval_manifest.json", sorted(manifests, key=lambda r: r["query"]))
    build_frame(out, f"all_publication_years_through_{query.END_YEAR}")


def counts(workers):
    core = query.build([f for f in query.FAMILIES if f["role"] != "expansion"], limits=False)
    jobs = [("baseline_user", query.baseline_query()),
            ("exact_core", core + " AND " + query.LIMITS)]
    for f in query.FAMILIES:
        jobs.append((f["id"], query.clause(f) + " AND " + query.LIMITS))
        if f["role"] == "expansion":
            jobs.append((f["id"]+"_beyond_core", "(" + query.clause(f) + " AND NOT (" + core + ")) AND " + query.LIMITS))
    rows = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(scopus.count, q): name for name, q in jobs}
        for fut in as_completed(futures):
            result = fut.result()
            result["name"] = futures[fut]
            rows.append(result)
            print(result["name"], result["count"], flush=True)
    write_csv(ROOT / "results" / "live_query_counts.csv", sorted(rows, key=lambda r: r["name"]),
              ["name", "count", "retrieved_at", "query"])


def parse_entry(e):
    authors = as_list(e.get("author"))
    seq = []
    for a in authors:
        try:
            seq.append((int(a["@seq"]), a.get("authid", "")))
        except (KeyError, ValueError, TypeError):
            pass
    declared = e.get("author-count", "")
    if isinstance(declared, dict):
        declared = declared.get("$", "")
    complete = (len(seq) == len(authors) and bool(seq)
                and len({n for n, aid in seq}) == len(seq)
                and sorted(n for n, aid in seq) == list(range(1, len(seq)+1))
                and all(aid for n, aid in seq)
                and len({aid for n, aid in seq}) == len(seq)
                and (str(declared) == str(len(authors)) or declared == ""))
    seq.sort()
    r = {"scopus_id": e["dc:identifier"].replace("SCOPUS_ID:", ""), "eid": e.get("eid", ""),
         "doi": e.get("prism:doi", ""), "year": (e.get("prism:coverDate") or "")[:4],
         "source_id": e.get("source-id", ""), "journal": e.get("prism:publicationName", ""),
         "title": e.get("dc:title", ""), "abstract": e.get("dc:description", "") or "",
         "keywords": e.get("authkeywords", "") or "", "indexed_keywords": "",
         "indexed_keywords_available": "false", "authids": "|".join(aid for n, aid in seq),
         "first_authid": seq[0][1] if complete else "", "last_authid": seq[-1][1] if complete else "",
         "byline_complete": str(complete).lower(), "n_authors": len(authors)}
    return r, [{"authid": a["authid"], "name": a.get("authname", ""), "orcid": a.get("orcid", "") or ""}
               for a in authors if a.get("authid")]


def retrieve(workers):
    # Retrieve short, overlapping query parts globally; deduplicate by Scopus ID,
    # then intersect with Source IDs locally. This preserves the exact union.
    parts = [q + f" AND PUBYEAR = {year}" for q in query.groups()
             for year in range(query.START_YEAR, query.END_YEAR+1)]
    def fetch(item):
        i, q = item
        entries, manifest = scopus.search(q)
        manifest["part"] = i
        return entries, manifest
    all_entries, manifests, membership = {}, [], defaultdict(set)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, fut in enumerate(as_completed([pool.submit(fetch, item) for item in enumerate(parts)]), 1):
            entries, manifest = fut.result()
            manifests.append(manifest)
            for e in entries:
                sid = e["dc:identifier"]
                if sid not in all_entries or json.dumps(e, sort_keys=True) < json.dumps(all_entries[sid], sort_keys=True):
                    all_entries[sid] = e
                membership[sid].add(manifest["part"])
            print(f"Query parts: {i}/{len(parts)} complete; {len(all_entries)} unique articles", flush=True)
    rows, names = [], {}
    frame = read_csv(ROOT / "results" / "venue_frame.csv")
    ids = {r["source_id"] for r in frame}
    # Names use the highest article ID encountered; task completion order must
    # not determine the exported metadata.
    for key in sorted(all_entries, key=lambda k: int(k.replace("SCOPUS_ID:", ""))):
        e = all_entries[key]
        row, authors = parse_entry(e)
        row["retrieved_by_parts"] = "|".join(str(i+1) for i in sorted(membership[e["dc:identifier"]]))
        row["in_frame"] = str(row["source_id"] in set(ids)).lower()
        rows.append(row)
        names.update({a["authid"]: a for a in authors})
    rows.sort(key=lambda r: int(r["scopus_id"]))
    write_csv(ROOT / "private" / "articles.csv", rows)
    write_csv(ROOT / "inputs" / "author_names.csv", sorted(names.values(), key=lambda r: int(r["authid"])))
    write_json(ROOT / "results" / "retrieval_manifest.json", {"query_sha256": digest(query.build()),
        "frame_sha256": digest((ROOT / "results" / "venue_frame.csv").read_bytes()), "n_articles": len(rows),
        "n_in_frame": sum(r["in_frame"] == "true" for r in rows),
        "complete": all(m["complete"] for m in manifests), "parts": sorted(manifests, key=lambda r: r["part"]),
        "missing_abstracts": sum(not r["abstract"] for r in rows),
        "incomplete_bylines": sum(r["byline_complete"] != "true" for r in rows),
        "indexed_keywords": "Not returned by Search COMPLETE; unmatched records require review"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["bootstrap", "queries", "refresh-frame", "counts", "retrieve", "analyse", "benchmark", "enrich", "dashboard", "reports", "all"])
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.workers <= 8:
        parser.error("workers must be between 1 and 8")
    if args.stage in {"bootstrap", "all"}:
        bootstrap()
    if args.stage == "queries":
        query.write_queries()
    if args.stage in {"refresh-frame", "all"}:
        refresh_frame(args.workers)
    if args.stage in {"counts", "all"}:
        counts(args.workers)
    if args.stage in {"retrieve", "all"}:
        retrieve(args.workers)
    if args.stage in {"benchmark", "all"}:
        from benchmark import benchmark
        benchmark()
    if args.stage in {"analyse", "all"}:
        from analyse import analyse
        analyse()
    if args.stage in {"reports", "all"}:
        from reports import reports
        reports()
    if args.stage in ("enrich", "dashboard"):
        if (ROOT / 'inputs/article_geography.csv').exists():
            from dashboard import build
            build()
        else:
            from enrich import enrich
            enrich()


if __name__ == "__main__":
    main()
