"""Import user PDFs into an isolated second full-text review wave.

The fixed sample and published 18-review stage are never changed by this module.
Original downloads, all page text, and review evidence remain private.
"""
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import argparse
import json
from pathlib import Path
import shutil
import threading

from common import ROOT, digest, read_csv, write_csv, write_json
from fulltext import extract
import precision_benchmark as benchmark

VERSION = "benchmark_review_wave2_2026_09_10"
PRIVATE = ROOT / "private" / VERSION
RESULTS = ROOT / "results" / VERSION
_VALIDATOR_LOCK = threading.Lock()


def validate_reviews(path):
    """Reuse the original exact-page/hash validator against only this wave's files.

    The temporary in-process namespace change is locked and always restored; it
    does not write to the original benchmark or import any previous decisions.
    """
    with _VALIDATOR_LOCK:
        prior_private = benchmark.PRIVATE
        try:
            benchmark.PRIVATE = PRIVATE
            return benchmark.validate_reviews(Path(path))
        finally:
            benchmark.PRIVATE = prior_private


def validate_adjudications(path=None):
    """Validate separate geography adjudication without changing original coders."""
    path = Path(path) if path is not None else PRIVATE / "adjudications.json"
    if not path.exists():
        return []
    rows = json.loads(path.read_text())
    if not isinstance(rows, list):
        raise ValueError("Adjudications must be a list")
    combined = PRIVATE / "combined_stage"
    packet = {r["benchmark_id"]: r for r in json.loads((combined / "reviewer_packet.json").read_text())}
    manifest = {r["benchmark_id"]: r for r in json.loads((combined / "availability_manifest.json").read_text())}
    seen = set()
    for row in rows:
        bid = row["benchmark_id"]
        if bid not in packet or bid in seen or row.get("axis") != "geography":
            raise ValueError("Unknown, repeated, or non-geography adjudication: " + bid)
        seen.add(bid)
        if row.get("decision") not in benchmark.GEOGRAPHIES:
            raise ValueError("Invalid geography adjudication decision")
        if (not row.get("rationale") or not row.get("reviewer") or row.get("reviewer_type") != "AI_assisted"
                or row.get("human_validated") not in (False, "false")):
            raise ValueError("Invalid adjudication provenance")
        date.fromisoformat(row["review_date"])
        if row.get("scopus_id") != manifest[bid]["scopus_id"]:
            raise ValueError("Adjudication Scopus identity mismatch")
        sha = row["document_sha256"]
        source = next((d for d in manifest[bid]["documents"] if d["pdf_sha256"] == sha), None)
        packet_doc = next((d for d in packet[bid]["documents"] if d["document_sha256"] == sha), None)
        if source is None or packet_doc is None or packet[bid]["readiness"] != "ready_for_fulltext_review":
            raise ValueError("Adjudication document is not ready and identity verified")
        pdf, cache = ROOT / source["pdf_path"], ROOT / source["text_cache"]
        if digest(pdf.read_bytes()) != sha or digest(cache.read_bytes()) != source["text_sha256"]:
            raise ValueError("Adjudication PDF or text-cache hash mismatch")
        saved = json.loads(cache.read_text())
        if saved["source_sha256"] != sha or packet_doc["text_sha256"] != source["text_sha256"]:
            raise ValueError("Adjudication packet source hash mismatch")
        page = int(row["pdf_page"])
        if not 1 <= page <= len(saved["pages"]):
            raise ValueError("Invalid adjudication PDF page")
        text = saved["pages"][page - 1]
        if next((p["text"] for p in packet_doc["pages"] if p["pdf_page"] == page), None) != text:
            raise ValueError("Adjudication packet page differs from extraction")
        quote = " ".join(row["evidence_quote"].split())
        if not quote or quote not in " ".join(text.split()):
            raise ValueError("Adjudication quote not found on cited page")
    return rows


def apply_geography_adjudications(rows, adjudications):
    """Keep raw geography consensus and every other axis, applying only reviewed geography."""
    lookup = {r["benchmark_id"]: r for r in adjudications}
    if not set(lookup) <= {r["benchmark_id"] for r in rows}:
        raise ValueError("Adjudication article is outside combined fixed sample")
    out = []
    for row in rows:
        result = {**row, "raw_consensus_geography": row["geography"], "geography_adjudicated": "false",
                  "geography_adjudication_reviewer": ""}
        if row["benchmark_id"] in lookup:
            item = lookup[row["benchmark_id"]]
            if item["axis"] != "geography" or row["review_coverage"] != "double_pass":
                raise ValueError("Adjudication must follow two completed geography reviews")
            result.update(geography=item["decision"], geography_adjudicated="true",
                          geography_adjudication_reviewer=item["reviewer"])
        out.append(result)
    return out


def archive_previous():
    existing = sorted(PRIVATE.glob("prior_stage_18_*/stage_manifest.json"))
    if existing:
        if len(existing) != 1:
            raise ValueError("Ambiguous frozen prior-stage archive")
        saved = json.loads(existing[0].read_text())
        for item in saved["files"]:
            if digest((ROOT / item["archive_path"]).read_bytes()) != item["sha256"]:
                raise ValueError("Frozen prior-stage archive has changed: " + item["archive_path"])
        return existing[0].parent, saved
    prior = ROOT / "results/precision_benchmark_2026_09_10/article_consensus.csv"
    archive = PRIVATE / ("prior_stage_18_" + digest(prior.read_bytes())[:16])
    paths = list((ROOT / "results/precision_benchmark_2026_09_10").glob("*"))
    paths += [ROOT / "private/precision_benchmark_2026_09_10" / name for name in (
        "fixed_sample.csv", "reviewer_packet.json", "review_template.json", "availability_manifest.json",
        "reviews_coder_A.json", "reviews_coder_B.json", "acquisition.json", "local_inventory.json")]
    manifest = []
    for path in paths:
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        target = archive / relative
        data = path.read_bytes()
        if target.exists():
            if target.read_bytes() != data:
                raise ValueError("Frozen prior-stage artifact has changed: " + str(relative))
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as handle:
                handle.write(data)
        manifest.append({"source_path": str(relative), "archive_path": str(target.relative_to(ROOT)), "sha256": digest(data)})
    output = archive / "stage_manifest.json"
    data = {"stage": "18 independently double-coded full texts before additional user downloads",
            "article_consensus_sha256": digest(prior.read_bytes()), "files": sorted(manifest, key=lambda r: r["source_path"])}
    if output.exists() and json.loads(output.read_text()) != data:
        raise ValueError("Frozen prior-stage manifest differs")
    if not output.exists():
        write_json(output, data)
    return archive, data


def import_download(path):
    sha = digest(path.read_bytes())
    target = PRIVATE / "original_downloads" / path.name
    if target.exists() and digest(target.read_bytes()) != sha:
        target = target.with_name(target.stem + "__" + sha[:12] + ".pdf")
    target.parent.mkdir(parents=True, exist_ok=True)
    if path != target:
        if target.exists():
            # Preserve each download even when its bytes duplicate a prior import.
            target = target.with_name(target.stem + "__duplicate_" + digest(str(path))[:8] + ".pdf")
        shutil.move(str(path), str(target))
    cache = PRIVATE / "texts" / (sha + ".json")
    if cache.exists():
        text = json.loads(cache.read_text())
        if text["source_sha256"] != sha:
            raise ValueError("Stale wave-2 extraction")
    else:
        pages, extractor = extract(target)
        text = {"source_sha256": sha, "extractor": extractor, "pages": pages}
        write_json(cache, text)
    return {"original_filename": path.name, "pdf_path": str(target.relative_to(ROOT)),
            "pdf_sha256": sha, "text_cache": str(cache.relative_to(ROOT)),
            "text_sha256": digest(cache.read_bytes()), "n_pages": len(text["pages"]),
            "text_characters": sum(len(p.strip()) for p in text["pages"]), "pages": text["pages"]}


def build():
    archive, frozen = archive_previous()
    candidates = sorted(ROOT.glob("*.pdf")) + sorted((PRIVATE / "original_downloads").glob("*.pdf"))
    with ThreadPoolExecutor(max_workers=4) as executor:
        downloads = list(executor.map(import_download, candidates))
    sample = read_csv(archive / "private/precision_benchmark_2026_09_10/fixed_sample.csv")
    old = {r["scopus_id"]: r for r in read_csv(archive / "results/precision_benchmark_2026_09_10/availability_manifest.csv")}
    matches, unmatched, inventory = defaultdict(list), [], []
    for download in downloads:
        found = [(a, benchmark.identity(download["pages"], a)) for a in sample]
        found = [(a, status) for a, status in found if status.startswith("verified_")]
        public = {k: v for k, v in download.items() if k not in ("pages", "pdf_path", "text_cache")}
        if len(found) != 1:
            unmatched.append({**download, "candidate_scopus_ids": [a["scopus_id"] for a, _ in found]})
            inventory.append({**public, "scopus_id": "", "doi": "", "title": "", "identity_status": "needs_identity_review", "fulltext_readiness": "needs_identity_review"})
            continue
        article, status = found[0]
        kind = benchmark.document_kind(download["original_filename"], download["pages"])
        record = {**{k: v for k, v in download.items() if k != "pages"},
                  "scopus_id": article["scopus_id"], "doi": article["doi"], "title": article["title"],
                  "identity_status": status, "document_kind": kind, "source_type": "user_supplied_download",
                  "source_url": "", "source_note": "User downloaded and supplied this copy; no availability/eligibility inference from access method."}
        record["fulltext_readiness"] = benchmark.readiness(record)
        matches[article["scopus_id"]].append(record)
        inventory.append({**public, **{k: record[k] for k in ("scopus_id", "doi", "title", "identity_status", "fulltext_readiness")}})
    packet, manifest, all_available = [], [], []
    for article in sample:
        sid = article["scopus_id"]
        copies = sorted(matches.get(sid, []), key=lambda d: (-d["n_pages"], -d["text_characters"], d["pdf_sha256"]))
        ready = [d for d in copies if d["fulltext_readiness"] == "ready_for_fulltext_review"]
        previously_ready = old[sid]["fulltext_readiness"] == "ready_for_fulltext_review"
        row = {**{k: article.get(k, "") for k in ("scopus_id", "doi", "title", "year", "journal")},
               "benchmark_id": old[sid]["benchmark_id"], "previously_ready": previously_ready,
               "article_url": "https://doi.org/" + article["doi"] if article["doi"] else "https://www.scopus.com/record/display.uri?eid=2-s2.0-" + sid,
               "suggested_filename": sid + ".pdf",
               "new_download_copies": len(copies), "new_verified_ready_copy": bool(ready),
               "available_after_wave2": previously_ready or bool(ready),
               "fulltext_readiness": "ready_for_fulltext_review" if previously_ready or ready else old[sid]["fulltext_readiness"],
               "evaluation_status": "previous_18_review_stage_preserved" if previously_ready else "unassigned",
               "selected_pdf_sha256": ready[0]["pdf_sha256"] if ready else ""}
        all_available.append(row)
        if not ready or previously_ready:
            continue
        selected = ready[0]
        manifest.append({**row, "documents": [selected], "all_download_copies": copies})
        text = json.loads((ROOT / selected["text_cache"]).read_text())
        packet.append({"benchmark_id": old[sid]["benchmark_id"], "scopus_id": sid,
                       "title": article["title"], "doi": article["doi"],
                       "readiness": "ready_for_fulltext_review", "evaluation_status": "unassigned",
                       "documents": [{"document_sha256": selected["pdf_sha256"], "document_kind": selected["document_kind"],
                                      "n_pages": selected["n_pages"], "text_sha256": selected["text_sha256"],
                                      "pages": [{"pdf_page": i, "text": text} for i, text in enumerate(text["pages"], 1)]}]})
    packet.sort(key=lambda r: r["benchmark_id"])
    write_json(PRIVATE / "reviewer_packet.json", packet)
    write_json(PRIVATE / "review_template.json", [{"benchmark_id": row["benchmark_id"], "evaluation_status": "unassigned",
        **{axis: {"decision": "", "document_sha256": "", "pdf_page": "", "evidence_quote": "", "rationale": ""} for axis in benchmark.AXES},
        "studies": [], "reviewer": "", "reviewer_type": "", "review_date": "", "human_validated": False} for row in packet])
    write_json(PRIVATE / "availability_manifest.json", manifest)
    write_json(PRIVATE / "unmatched_downloads.json", unmatched)
    write_csv(PRIVATE / "download_inventory.csv", inventory)
    public_available = [{k: str(v).lower() if isinstance(v, bool) else v for k, v in row.items()} for row in all_available]
    write_csv(RESULTS / "availability_manifest.csv", public_available)
    write_csv(RESULTS / "manual_download_queue.csv", [r for r in public_available if r["available_after_wave2"] == "false"])
    schema = benchmark.reviewer_schema()
    write_json(RESULTS / "review_schema.json", schema)
    summary = {"fixed_sample_n": len(sample), "download_files": len(downloads),
               "unique_download_hashes": len({d["pdf_sha256"] for d in downloads}),
               "unique_verified_download_articles": len(matches), "unmatched_downloads": len(unmatched),
               "new_articles_ready_for_review": len(packet), "previously_ready_articles": sum(r["previously_ready"] for r in all_available),
               "articles_available_after_wave2": sum(r["available_after_wave2"] for r in all_available),
               "articles_still_missing": sum(not r["available_after_wave2"] for r in all_available),
               "prior_stage_archive": str(archive.relative_to(ROOT)),
               "prior_consensus_sha256": frozen["article_consensus_sha256"],
               "packet_sha256": digest((PRIVATE / "reviewer_packet.json").read_bytes()),
               "prior_labels_modified": False, "inaccessible_records_replaced": False}
    write_json(RESULTS / "summary.json", summary)
    print(json.dumps(summary, indent=2))
    return summary


def aggregate():
    """Combine old and additional reviews without rewriting the old study stage."""
    archive, _ = archive_previous()
    frozen = archive / "private/precision_benchmark_2026_09_10"
    combined = PRIVATE / "combined_stage"
    combined.mkdir(parents=True, exist_ok=True)
    (combined / "fixed_sample.csv").write_bytes((frozen / "fixed_sample.csv").read_bytes())
    old_packet = {r["benchmark_id"]: r for r in json.loads((frozen / "reviewer_packet.json").read_text())}
    new_packet = {r["benchmark_id"]: r for r in json.loads((PRIVATE / "reviewer_packet.json").read_text())}
    if any(old_packet[k]["readiness"] == "ready_for_fulltext_review" for k in new_packet):
        raise ValueError("A wave-2 article overlaps the original ready stage")
    write_json(combined / "reviewer_packet.json", sorted({**old_packet, **new_packet}.values(), key=lambda r: r["benchmark_id"]))
    old_manifest = {r["benchmark_id"]: r for r in json.loads((frozen / "availability_manifest.json").read_text())}
    for row in json.loads((PRIVATE / "availability_manifest.json").read_text()):
        old_manifest[row["benchmark_id"]] = row
    write_json(combined / "availability_manifest.json", sorted(old_manifest.values(), key=lambda r: r["benchmark_id"]))
    for coder in ("A", "B"):
        old_reviews = json.loads((frozen / ("reviews_coder_" + coder + ".json")).read_text())
        new_path = PRIVATE / ("reviews_coder_" + coder + ".json")
        new_reviews = []
        if new_path.exists():
            validate_reviews(new_path)
            new_reviews = [r for r in json.loads(new_path.read_text()) if r.get("evaluation_status") == "completed"]
        old_ids = {r["benchmark_id"] for r in old_reviews}
        if old_ids & {r["benchmark_id"] for r in new_reviews}:
            raise ValueError("Old and additional reviews overlap")
        write_json(combined / ("reviews_coder_" + coder + ".json"), sorted(old_reviews + new_reviews, key=lambda r: r["benchmark_id"]))
    import precision_benchmark_review as review
    with _VALIDATOR_LOCK:
        old_private, old_results = benchmark.PRIVATE, benchmark.RESULTS
        try:
            benchmark.PRIVATE, benchmark.RESULTS = combined, RESULTS
            summary = review.build()
        finally:
            benchmark.PRIVATE, benchmark.RESULTS = old_private, old_results
    adjudications = validate_adjudications()
    summary.update({"review_stage": "original 18 plus additional user-supplied fixed-sample full texts",
                    "additional_articles_available": len(new_packet),
                    "query_development_exposure": "Only the archived original 18 reviews were available at query development. Later reviews are additional validation of the same fixed sample, not a new independent sample.",
                    "prior_stage_preserved": True, "geography_adjudications": len(adjudications),
                    "original_coder_decisions_and_disagreements_preserved": True})
    write_json(RESULTS / "review_summary.json", summary)
    consensus = apply_geography_adjudications(read_csv(RESULTS / "article_consensus.csv"), adjudications)
    write_csv(RESULTS / "article_consensus.csv", consensus)
    public_adjudications = [{k: str(v).lower() if isinstance(v, bool) else v for k, v in r.items() if k != "evidence_quote"} for r in adjudications]
    write_csv(RESULTS / "geography_adjudications.csv", public_adjudications,
              ["benchmark_id", "scopus_id", "axis", "decision", "document_sha256", "pdf_page", "rationale", "reviewer", "reviewer_type", "review_date", "human_validated"])
    source_path = PRIVATE / "adjudications.json"
    write_json(RESULTS / "adjudication_provenance.json", {
        "adjudications": len(adjudications), "source_file": str(source_path.relative_to(ROOT)),
        "source_sha256": digest(source_path.read_bytes()) if source_path.exists() else "",
        "packet_sha256": digest((combined / "reviewer_packet.json").read_bytes()),
        "pdf_cache_packet_and_exact_page_spans_validated": True,
        "original_coder_files_unchanged": True, "other_axes_unchanged": True, "human_validated": False})
    sources = {c: {r["benchmark_id"]: r for r in json.loads((combined / ("reviews_coder_" + c + ".json")).read_text())} for c in ("A", "B")}
    packets = {**old_packet, **new_packet}
    disagreements, private_disagreements = [], []
    for row in consensus:
        if row["review_coverage"] != "double_pass":
            continue
        bid = row["benchmark_id"]
        for axis in benchmark.AXES:
            if row["coder_A_" + axis] == row["coder_B_" + axis]:
                continue
            a, b = sources["A"][bid][axis], sources["B"][bid][axis]
            public = {"benchmark_id": bid, "scopus_id": row["scopus_id"], "title": row["title"],
                      "review_stage": "additional_27" if bid in new_packet else "original_18",
                      "axis": axis, "coder_A_decision": a["decision"], "coder_B_decision": b["decision"],
                      "coder_A_rationale": a["rationale"], "coder_B_rationale": b["rationale"],
                      "consensus": "unclear", "human_validated": "false",
                      "adjudicated_decision": row["geography"] if axis == "geography" and row["geography_adjudicated"] == "true" else ""}
            disagreements.append(public)
            private_disagreements.append({**public, "coder_A_evidence": a, "coder_B_evidence": b,
                                          "documents": packets[bid]["documents"]})
    write_csv(RESULTS / "review_disagreements.csv", disagreements)
    write_json(PRIVATE / "adjudication_packet.json", private_disagreements)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", type=Path)
    parser.add_argument("--aggregate", action="store_true")
    args = parser.parse_args()
    if args.validate:
        print(json.dumps(validate_reviews(args.validate), indent=2))
    elif args.aggregate:
        aggregate()
    else:
        build()
