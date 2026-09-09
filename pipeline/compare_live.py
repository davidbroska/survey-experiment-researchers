"""Measure actual Scopus result-set overlap, rather than approximating it by regex."""
from concurrent.futures import ThreadPoolExecutor
import json
from common import ROOT, read_csv, write_csv, write_json
import query
import scopus


def compare():
    def fetch(year):
        return scopus.search(query.baseline_query()+f" AND PUBYEAR = {year}", view="STANDARD")
    baseline, manifests = {}, []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for entries, manifest in pool.map(fetch, range(query.START_YEAR, query.END_YEAR+1)):
            manifests.append(manifest)
            for e in entries:
                sid = e["dc:identifier"].replace("SCOPUS_ID:", "")
                baseline[sid] = {"scopus_id": sid, "source_id": e.get("source-id", ""),
                    "title": e.get("dc:title", ""), "doi": e.get("prism:doi", "")}
    frame = {r["source_id"] for r in read_csv(ROOT / "results" / "venue_frame.csv")}
    recommended = {r["scopus_id"]: r for r in read_csv(ROOT / "private" / "articles.csv")}
    results = []
    for label, sources in [("global", None), ("tess_journals", frame)]:
        b = {sid for sid, r in baseline.items() if sources is None or r["source_id"] in sources}
        n = {sid for sid, r in recommended.items() if sources is None or r["source_id"] in sources}
        results.append({"scope": label, "baseline": len(b), "recommended": len(n), "shared": len(b & n),
            "added_by_recommended": len(n-b), "baseline_only": len(b-n),
            "note": "Retrieval overlap, not recall or precision; the population of all relevant articles is unknown."})
        if sources is not None:
            write_csv(ROOT / "results" / "added_article_metadata.csv", [recommended[sid] for sid in sorted(n-b, key=int)],
                ["scopus_id", "doi", "title", "journal", "year"])
    write_csv(ROOT / "results" / "live_set_comparison.csv", results)
    write_json(ROOT / "results" / "baseline_retrieval_manifest.json", manifests)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    compare()

