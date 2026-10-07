"""Isolated third full-text wave; preserve all prior 45-review artifacts.

Only PDFs supplied in the recruitment root are imported. Source PDFs, page text,
and quotations remain private. Availability never supplies a study-design label.
"""
import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shutil
import threading

from common import ROOT, digest, read_csv, write_csv, write_json
from fulltext import extract
import precision_benchmark as benchmark

VERSION = "benchmark_review_wave3_2026_09_10"
PRIOR_VERSION = "benchmark_review_wave2_2026_09_10"
PRIVATE, RESULTS = ROOT / "private" / VERSION, ROOT / "results" / VERSION
_LOCK = threading.Lock()


def freeze_prior():
    existing = sorted(PRIVATE.glob("prior_stage_45_*/stage_manifest.json"))
    if existing:
        if len(existing) != 1:
            raise ValueError("Ambiguous prior-stage archive")
        manifest = json.loads(existing[0].read_text())
        for row in manifest["files"]:
            if digest((ROOT / row["archive_path"]).read_bytes()) != row["sha256"]:
                raise ValueError("Frozen prior-stage archive was changed")
        return existing[0].parent, manifest
    prior_results = ROOT / "results" / PRIOR_VERSION
    prior_private = ROOT / "private" / PRIOR_VERSION
    if json.loads((prior_results / "review_summary.json").read_text())["double_pass"] != 45:
        raise ValueError("Expected the complete 45-review prior stage")
    consensus_sha = digest((prior_results / "article_consensus.csv").read_bytes())
    archive = PRIVATE / ("prior_stage_45_" + consensus_sha[:16])
    paths = list(prior_results.glob("*")) + list((prior_private / "combined_stage").glob("*"))
    paths += [prior_private / n for n in ("reviews_coder_A.json", "reviews_coder_B.json", "reviewer_packet.json",
                                          "availability_manifest.json", "adjudications.json")]
    files = []
    for path in sorted(paths):
        if not path.is_file() or path.suffix.lower() not in (".json", ".csv", ".md", ".txt"):
            continue
        target = archive / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = path.read_bytes()
        if target.exists():
            if target.read_bytes() != data:
                raise ValueError("Existing archived bytes differ")
        else:
            with target.open("xb") as handle:
                handle.write(data)
        files.append({"source_path": str(path.relative_to(ROOT)), "archive_path": str(target.relative_to(ROOT)), "sha256": digest(data)})
    manifest = {"prior_stage": "45 double-reviewed fixed-sample articles including separate geography adjudication",
                "prior_consensus_sha256": consensus_sha, "files": files}
    write_json(archive / "stage_manifest.json", manifest)
    return archive, manifest


def import_pdf(path):
    source_sha = digest(path.read_bytes())
    target = PRIVATE / "original_downloads" / path.name
    target.parent.mkdir(parents=True, exist_ok=True)
    if path != target:
        if target.exists():
            target = target.with_name(target.stem + "__" + source_sha[:12] + target.suffix)
            if target.exists():
                raise ValueError("A duplicate download name already exists; preserve originals for explicit review")
        shutil.move(str(path), str(target))
    cache = PRIVATE / "texts" / (source_sha + ".json")
    if cache.exists():
        text = json.loads(cache.read_text())
        if text["source_sha256"] != source_sha:
            raise ValueError("Stale source extraction")
    else:
        pages, extractor = extract(target)
        text = {"source_sha256": source_sha, "extractor": extractor, "pages": pages}
        write_json(cache, text)
    return {"original_filename": path.name, "pdf_path": str(target.relative_to(ROOT)), "pdf_sha256": source_sha,
            "text_cache": str(cache.relative_to(ROOT)), "text_sha256": digest(cache.read_bytes()),
            "n_pages": len(text["pages"]), "text_characters": sum(len(p.strip()) for p in text["pages"]), "pages": text["pages"]}


def validate_reviews(path):
    with _LOCK:
        old = benchmark.PRIVATE
        try:
            benchmark.PRIVATE = PRIVATE
            return benchmark.validate_reviews(Path(path))
        finally:
            benchmark.PRIVATE = old


def write_packet_once(path, rows):
    """An issued coding packet is immutable; later copies require a later wave."""
    if path.exists():
        if json.loads(path.read_text()) != rows:
            raise ValueError("Issued review packet would change; use a subsequent wave namespace")
    else:
        write_json(path, rows)


def public_alternatives():
    """One bounded public-copy attempt for the seven still-missing fixed articles.

    New copies stay in a separate acquisition namespace; an issued coding packet
    is never expanded or replaced while independent reviewers are using it.
    """
    articles = read_csv(RESULTS / "manual_download_queue.csv")
    with _LOCK:
        old = benchmark.PRIVATE
        try:
            benchmark.PRIVATE = PRIVATE / "public_alternatives"
            client = benchmark.PublicCopies()
            discovery = client.discover(articles)
            def acquire(article):
                return article["scopus_id"], client.acquire(article, discovery[article["scopus_id"]])
            with ThreadPoolExecutor(max_workers=4) as executor:
                acquired = dict(executor.map(acquire, articles))
            write_json(benchmark.PRIVATE / "acquisition.json", acquired)
        finally:
            benchmark.PRIVATE = old
    rows = [{"scopus_id": a["scopus_id"], "doi": a["doi"], "title": a["title"],
             "open_location_found": str(acquired[a["scopus_id"]]["open_location_found"]).lower(),
             "n_urls_attempted_this_pass": acquired[a["scopus_id"]]["n_urls_this_pass"],
             "n_ready_public_copies": sum(d["fulltext_readiness"] == "ready_for_fulltext_review" for d in acquired[a["scopus_id"]]["documents"]),
             "lookup_error": acquired[a["scopus_id"]].get("lookup_error", ""),
             "attempted_urls": "|".join(r["url"] for r in acquired[a["scopus_id"]]["attempts"]),
             "publisher_access_issue_basis": a["publisher_access_issue_basis"]} for a in articles]
    write_csv(RESULTS / "public_alternative_lookup.csv", rows)
    print(json.dumps({"articles_checked": len(rows), "new_ready_public_copies": sum(r["n_ready_public_copies"] for r in rows),
                      "issued_eight_article_packet_unchanged": True}, indent=2))
    return rows


def build():
    archive, prior_manifest = freeze_prior()
    prior_private = archive / "private" / PRIOR_VERSION
    prior_results = archive / "results" / PRIOR_VERSION
    sample = read_csv(prior_private / "combined_stage/fixed_sample.csv")
    prior = {r["scopus_id"]: r for r in read_csv(prior_results / "availability_manifest.csv")}
    prior_consensus = {r["scopus_id"]: r for r in read_csv(prior_results / "article_consensus.csv")}
    candidates = sorted(ROOT.glob("*.pdf")) + sorted((PRIVATE / "original_downloads").glob("*.pdf"))
    with ThreadPoolExecutor(max_workers=4) as executor:
        downloads = list(executor.map(import_pdf, candidates))
    catalog = list(sample)
    current_articles = ROOT / "private/query_rankings_2026_09_10/articles.csv"
    if current_articles.exists():
        sampled_ids = {r["scopus_id"] for r in sample}
        catalog += [r for r in read_csv(current_articles) if r["scopus_id"] not in sampled_ids]
    matches, unmatched, inventory = defaultdict(list), [], []
    for download in downloads:
        hits = [(article, benchmark.identity(download["pages"], article)) for article in sample]
        hits = [(a, status) for a, status in hits if status.startswith("verified_")]
        if not hits:
            hits = [(article, benchmark.identity(download["pages"], article)) for article in catalog[len(sample):]]
            hits = [(a, status) for a, status in hits if status.startswith("verified_")]
        if len(hits) != 1:
            unmatched.append({**download, "candidate_scopus_ids": [a["scopus_id"] for a, _ in hits]})
            continue
        article, status = hits[0]
        record = {**{k: v for k, v in download.items() if k != "pages"},
                  **{k: article.get(k, "") for k in ("scopus_id", "doi", "title", "year", "journal")},
                  "identity_status": status, "document_kind": benchmark.document_kind(download["original_filename"], download["pages"]),
                  "source_type": "user_supplied_download", "source_url": ""}
        record["fulltext_readiness"] = benchmark.readiness(record)
        matches[article["scopus_id"]].append(record)
        inventory.append(record)
    packet, new_private, public, supplementary = [], [], [], []
    for article in sample:
        sid = article["scopus_id"]
        copies = sorted(matches.get(sid, []), key=lambda r: (-r["n_pages"], -r["text_characters"], r["pdf_sha256"]))
        ready = [r for r in copies if r["fulltext_readiness"] == "ready_for_fulltext_review"]
        old_ready = prior[sid]["fulltext_readiness"] == "ready_for_fulltext_review"
        available = old_ready or bool(ready)
        tf = article["doi"].lower().startswith("10.1080/")
        row = {**{k: article.get(k, "") for k in ("scopus_id", "doi", "title", "year", "journal")},
               "benchmark_id": prior[sid]["benchmark_id"], "previously_ready": str(old_ready).lower(),
               "new_verified_ready_copy": str(bool(ready)).lower(), "available_after_wave3": str(available).lower(),
               "new_download_copies": len(copies), "fulltext_readiness": "ready_for_fulltext_review" if available else prior[sid]["fulltext_readiness"],
               "prior_review_coverage": prior_consensus[sid]["review_coverage"],
               "new_review_status": "unassigned" if ready and not old_ready else "no_new_review",
               "article_url": "https://doi.org/" + article["doi"] if article["doi"] else "https://www.scopus.com/record/display.uri?eid=2-s2.0-" + sid,
               "suggested_filename": sid + ".pdf", "selected_pdf_sha256": ready[0]["pdf_sha256"] if ready else "",
               "publisher_access_issue": "user_reported_Taylor_and_Francis_access_unavailable" if tf and not available else "",
               "publisher_access_issue_basis": "User reported inability to access Taylor & Francis generally; no article-specific failed attempt is inferred." if tf and not available else ""}
        public.append(row)
        if not ready or old_ready:
            continue
        selected = ready[0]
        new_private.append({**row, "documents": [selected], "all_download_copies": copies})
        pages = json.loads((ROOT / selected["text_cache"]).read_text())["pages"]
        packet.append({"benchmark_id": row["benchmark_id"], "scopus_id": sid, "title": row["title"], "doi": row["doi"],
                       "readiness": "ready_for_fulltext_review", "evaluation_status": "unassigned", "documents": [
                           {"document_sha256": selected["pdf_sha256"], "document_kind": selected["document_kind"], "n_pages": selected["n_pages"],
                            "text_sha256": selected["text_sha256"], "pages": [{"pdf_page": n, "text": text} for n, text in enumerate(pages, 1)]}]})
    sample_ids = {r["scopus_id"] for r in sample}
    for sid, records in matches.items():
        if sid not in sample_ids:
            supplementary.append({"scopus_id": sid, "documents": records, "status": "matched_geography_article_outside_fixed_benchmark"})
    packet.sort(key=lambda r: r["benchmark_id"])
    write_packet_once(PRIVATE / "reviewer_packet.json", packet)
    write_json(PRIVATE / "availability_manifest.json", new_private)
    write_json(PRIVATE / "geography_matches.json", supplementary)
    write_json(PRIVATE / "unmatched_downloads.json", unmatched)
    write_csv(PRIVATE / "download_inventory.csv", inventory)
    write_csv(RESULTS / "availability_manifest.csv", public)
    missing = [r for r in public if r["available_after_wave3"] == "false"]
    write_csv(RESULTS / "manual_download_queue.csv", missing)
    write_csv(RESULTS / "publisher_access_issues.csv", [r for r in missing if r["publisher_access_issue"]], list(public[0]))
    write_json(RESULTS / "review_schema.json", benchmark.reviewer_schema())
    write_packet_once(PRIVATE / "review_template.json", [{"benchmark_id": r["benchmark_id"], "evaluation_status": "unassigned",
        **{axis: {"decision": "", "document_sha256": "", "pdf_page": "", "evidence_quote": "", "rationale": ""} for axis in benchmark.AXES},
        "studies": [], "reviewer": "", "reviewer_type": "", "review_date": "", "human_validated": False} for r in packet])
    summary = {"fixed_sample_n": len(sample), "download_files": len(downloads), "unique_download_hashes": len({r["pdf_sha256"] for r in downloads}),
               "unique_verified_download_articles": len(matches), "new_benchmark_articles_ready": len(packet),
               "matched_geography_articles_outside_benchmark": len(supplementary), "unmatched_downloads": len(unmatched),
               "previously_ready_articles": 45, "articles_available_after_wave3": len(public) - len(missing), "articles_still_missing": len(missing),
               "missing_articles_with_user_reported_TF_access_issue": sum(bool(r["publisher_access_issue"]) for r in missing),
               "prior_stage_archive": str(archive.relative_to(ROOT)), "prior_consensus_sha256": prior_manifest["prior_consensus_sha256"],
               "packet_sha256": digest((PRIVATE / "reviewer_packet.json").read_bytes()),
               "previous_packets_and_reviews_modified": False, "inaccessible_records_replaced": False}
    write_json(RESULTS / "summary.json", summary)
    print(json.dumps(summary, indent=2))
    return summary


def merge_new_records(previous, additional, *, require_unready=False):
    """Require stable sample IDs and prevent replacement of previously reviewed PDFs."""
    old = {r["benchmark_id"]: r for r in previous}
    new = {r["benchmark_id"]: r for r in additional}
    if len(old) != len(previous) or len(new) != len(additional) or not set(new) <= set(old):
        raise ValueError("Repeated or non-sampled benchmark identity")
    if require_unready and any(old[bid]["readiness"] == "ready_for_fulltext_review" for bid in new):
        raise ValueError("New wave would replace a previously reviewed document")
    return sorted({**old, **new}.values(), key=lambda r: r["benchmark_id"])


def aggregate():
    """Add this wave to the immutable 45-review stage, retaining all 60 sampled rows."""
    import benchmark_review_wave2 as previous_wave
    import precision_benchmark_review as review

    archive, frozen_manifest = freeze_prior()
    frozen = archive / "private" / PRIOR_VERSION
    prior = frozen / "combined_stage"
    combined = PRIVATE / "combined_stage"
    combined.mkdir(parents=True, exist_ok=True)
    (combined / "fixed_sample.csv").write_bytes((prior / "fixed_sample.csv").read_bytes())
    old_packet = json.loads((prior / "reviewer_packet.json").read_text())
    new_packet = json.loads((PRIVATE / "reviewer_packet.json").read_text())
    packets = merge_new_records(old_packet, new_packet, require_unready=True)
    write_json(combined / "reviewer_packet.json", packets)
    manifests = merge_new_records(json.loads((prior / "availability_manifest.json").read_text()),
                                  json.loads((PRIVATE / "availability_manifest.json").read_text()))
    write_json(combined / "availability_manifest.json", manifests)
    for coder in ("A", "B"):
        old_reviews = json.loads((prior / ("reviews_coder_" + coder + ".json")).read_text())
        path = PRIVATE / ("reviews_coder_" + coder + ".json")
        new_reviews = []
        if path.exists():
            validate_reviews(path)
            new_reviews = [r for r in json.loads(path.read_text()) if r.get("evaluation_status") == "completed"]
        if {r["benchmark_id"] for r in old_reviews} & {r["benchmark_id"] for r in new_reviews}:
            raise ValueError("A prior review would be replaced")
        write_json(combined / ("reviews_coder_" + coder + ".json"), sorted(old_reviews + new_reviews, key=lambda r: r["benchmark_id"]))
    with _LOCK:
        old_private, old_results, old_wave_private = benchmark.PRIVATE, benchmark.RESULTS, previous_wave.PRIVATE
        try:
            benchmark.PRIVATE, benchmark.RESULTS = combined, RESULTS
            summary = review.build()
            previous_wave.PRIVATE = PRIVATE
            adjudication_path = frozen / "adjudications.json"
            adjudications = previous_wave.validate_adjudications(adjudication_path)
        finally:
            benchmark.PRIVATE, benchmark.RESULTS, previous_wave.PRIVATE = old_private, old_results, old_wave_private
    consensus = previous_wave.apply_geography_adjudications(read_csv(RESULTS / "article_consensus.csv"), adjudications)
    write_csv(RESULTS / "article_consensus.csv", consensus)
    write_csv(RESULTS / "geography_adjudications.csv",
              [{k: str(v).lower() if isinstance(v, bool) else v for k, v in row.items() if k != "evidence_quote"} for row in adjudications],
              ["benchmark_id", "scopus_id", "axis", "decision", "document_sha256", "pdf_page", "rationale", "reviewer", "reviewer_type", "review_date", "human_validated"])
    write_json(RESULTS / "adjudication_provenance.json", {
        "adjudications": len(adjudications), "source_file": str(adjudication_path.relative_to(ROOT)),
        "source_sha256": digest(adjudication_path.read_bytes()) if adjudication_path.exists() else "",
        "packet_sha256": digest((combined / "reviewer_packet.json").read_bytes()),
        "pdf_cache_packet_and_exact_page_spans_validated": True,
        "original_coder_files_unchanged": True, "other_axes_unchanged": True, "human_validated": False})
    new_ids = {r["benchmark_id"] for r in new_packet}
    sources = {c: {r["benchmark_id"]: r for r in json.loads((combined / ("reviews_coder_" + c + ".json")).read_text())} for c in ("A", "B")}
    packet_lookup = {r["benchmark_id"]: r for r in packets}
    public_disagreements, private_disagreements = [], []
    for row in consensus:
        if row["review_coverage"] != "double_pass":
            continue
        bid = row["benchmark_id"]
        for axis in benchmark.AXES:
            a, b = sources["A"][bid][axis], sources["B"][bid][axis]
            if a["decision"] == b["decision"]:
                continue
            item = {"benchmark_id": bid, "scopus_id": row["scopus_id"], "title": row["title"],
                    "review_stage": "additional_8" if bid in new_ids else "previous_45",
                    "axis": axis, "coder_A_decision": a["decision"], "coder_B_decision": b["decision"],
                    "coder_A_rationale": a["rationale"], "coder_B_rationale": b["rationale"],
                    "consensus": "unclear", "human_validated": "false",
                    "adjudicated_decision": row["geography"] if axis == "geography" and row["geography_adjudicated"] == "true" else ""}
            public_disagreements.append(item)
            private_disagreements.append({**item, "coder_A_evidence": a, "coder_B_evidence": b,
                                          "documents": packet_lookup[bid]["documents"]})
    write_csv(RESULTS / "review_disagreements.csv", public_disagreements)
    write_json(PRIVATE / "adjudication_packet.json", private_disagreements)
    summary.update({"review_stage": "previous 45 plus eight additional user-supplied fixed-sample full texts",
                    "additional_articles_available": len(new_packet), "geography_adjudications": len(adjudications),
                    "prior_stage_preserved": True, "prior_consensus_sha256": frozen_manifest["prior_consensus_sha256"],
                    "query_development_exposure": "Only the original 18 reviews were available at initial query development; the subsequent 27 and eight are later reviews of the same fixed sample, not independent samples.",
                    "original_coder_decisions_and_disagreements_preserved": True})
    write_json(RESULTS / "review_summary.json", summary)
    # Revalidate the archived bytes after every aggregation; this also verifies
    # that later stages have not accidentally modified their input archive.
    freeze_prior()
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", type=Path)
    parser.add_argument("--public-alternatives", action="store_true")
    parser.add_argument("--aggregate", action="store_true")
    args = parser.parse_args()
    if args.validate:
        print(json.dumps(validate_reviews(args.validate), indent=2))
    elif args.public_alternatives:
        public_alternatives()
    elif args.aggregate:
        aggregate()
    else:
        build()
