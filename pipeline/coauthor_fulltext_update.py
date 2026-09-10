"""Import and review a separate batch of user-supplied full texts locally.

Archiving precedes removal from the recruitment root. Original PDFs, extracted
pages and exact evidence quotes remain private. Prior review stages are inputs
only and are never rewritten. Geography review does not silently exclude papers.
"""
import argparse
import json
from pathlib import Path

from common import ROOT, digest, read_csv, write_csv, write_json
from fulltext import extract
from precision_benchmark import identity, document_kind, readiness

VERSION = "coauthor_update_2026_09_10"
PRIVATE, RESULTS = ROOT / "private" / VERSION, ROOT / "results" / VERSION
REVIEW_FIELDS = ["scopus_id", "sample_us_label", "filename", "source_sha256", "page", "evidence_quote",
                "rationale", "us_and_non_us_samples_reported", "reviewer", "reviewer_type", "review_date",
                "human_validated", "source_url", "source_kind", "pdf_path", "text_cache_path", "text_cache_sha256"]


def archive_pdf(path):
    """Remove a supplied root file only after an identical private copy exists."""
    if path.parent.resolve() != ROOT.resolve():
        raise ValueError("Only supplied recruitment-root PDFs may be imported")
    data = path.read_bytes()
    sha = digest(data)
    archive = PRIVATE / "original_downloads"
    archive.mkdir(parents=True, exist_ok=True)
    target = archive / path.name
    if target.exists() and target.read_bytes() != data:
        target = archive / (path.stem + "__" + sha[:12] + path.suffix)
    if target.exists():
        if target.read_bytes() != data:
            raise ValueError("Archive filename collision")
    else:
        with target.open("xb") as handle:
            handle.write(data)
    if digest(target.read_bytes()) != sha:
        raise ValueError("Private archive verification failed")
    if path != target:
        if path.parent.resolve() != ROOT.resolve() or digest(path.read_bytes()) != sha:
            raise ValueError("Only unchanged recruitment-root files can be removed after archiving")
        path.unlink()
    return target, sha


def write_immutable(path, value):
    if path.exists():
        if json.loads(path.read_text()) != value:
            raise ValueError("Issued packet changed; use a new review namespace")
    else:
        write_json(path, value)


def build():
    incoming = sorted(ROOT.glob("*.pdf"))
    if incoming and (PRIVATE / "fulltext_review_packet.json").exists():
        raise ValueError("A packet has already been issued; import later downloads in a new namespace")
    for path in incoming:
        archive_pdf(path)
    catalog = read_csv(ROOT / "private/query_rankings_2026_09_10/articles.csv")
    fixed = {r["scopus_id"]: r for r in read_csv(ROOT / "results/proximity_audit_2026_09_10/fulltext_sample.csv")}
    old_available = {r["scopus_id"]: r for r in read_csv(ROOT / "results/benchmark_review_wave3_2026_09_10/availability_manifest.csv")}
    inventory, packet, unmatched = [], [], []
    for path in sorted((PRIVATE / "original_downloads").glob("*.pdf")):
        sha = digest(path.read_bytes())
        cache_path = PRIVATE / "texts" / (sha + ".json")
        if cache_path.exists():
            saved = json.loads(cache_path.read_text())
            if saved["source_sha256"] != sha:
                raise ValueError("Source PDF and extraction differ")
        else:
            pages, extractor = extract(path)
            saved = {"source_sha256": sha, "extractor": extractor, "pages": pages}
            write_json(cache_path, saved)
        pages = saved["pages"]
        hits = [(a, identity(pages, a)) for a in catalog]
        hits = [(a, status) for a, status in hits if status.startswith("verified_")]
        row = {"filename": path.name, "source_sha256": sha, "pdf_path": str(path.relative_to(ROOT)),
               "text_cache_path": str(cache_path.relative_to(ROOT)), "text_cache_sha256": digest(cache_path.read_bytes()),
               "n_pages": len(pages), "text_characters": sum(len(p.strip()) for p in pages),
               "source_kind": "user_supplied_article_or_manuscript", "source_url": ""}
        if len(hits) != 1:
            unmatched.append({**row, "candidate_scopus_ids": [a["scopus_id"] for a, _ in hits]})
            continue
        article, status = hits[0]
        sid = article["scopus_id"]
        row.update({k: article.get(k, "") for k in ("scopus_id", "doi", "title", "year", "journal")})
        row.update(identity_status=status, document_kind=document_kind(path.name, pages),
                   in_fixed_benchmark=str(sid in fixed).lower(),
                   newly_available_fixed_benchmark=str(sid in fixed and old_available[sid]["fulltext_readiness"] != "ready_for_fulltext_review").lower())
        row["fulltext_readiness"] = readiness(row)
        inventory.append(row)
        packet.append({**row, "pages": [{"pdf_page": i, "text": text} for i, text in enumerate(pages, 1)]})
    if len({r["scopus_id"] for r in inventory}) != len(inventory):
        raise ValueError("Multiple supplied copies match one article; explicit deduplication is needed")
    packet.sort(key=lambda r: r["scopus_id"])
    write_immutable(PRIVATE / "fulltext_review_packet.json", packet)
    write_csv(PRIVATE / "inventory.csv", inventory)
    write_json(PRIVATE / "unmatched_downloads.json", unmatched)
    public = [{k: v for k, v in r.items() if k not in ("pdf_path", "text_cache_path", "text_characters")} for r in inventory]
    write_csv(RESULTS / "availability_manifest.csv", public)
    summary = {"download_files": len(inventory) + len(unmatched), "matched_articles": len(inventory),
               "ready_fulltexts": sum(r["fulltext_readiness"] == "ready_for_fulltext_review" for r in inventory),
               "unmatched_downloads": len(unmatched), "newly_available_fixed_benchmark_articles": sum(r["newly_available_fixed_benchmark"] == "true" for r in inventory),
               "originals_archived_before_root_removal": True, "prior_review_files_modified": False,
               "fulltext_packet_sha256": digest((PRIVATE / "fulltext_review_packet.json").read_bytes())}
    write_json(RESULTS / "inventory_summary.json", summary)
    return summary


def validate_and_export():
    from query_ranking_geography import validate_priority_fulltext
    path = PRIVATE / "fulltext_reviews.csv"
    rows = read_csv(path)
    packet = {r["scopus_id"]: r for r in json.loads((PRIVATE / "fulltext_review_packet.json").read_text())}
    if len(rows) != len(packet) or {r["scopus_id"] for r in rows} != set(packet):
        raise ValueError("Every supplied article needs exactly one review")
    public = []
    for row in rows:
        validate_priority_fulltext(row, ROOT)
        source = packet[row["scopus_id"]]
        for key in ("filename", "source_sha256", "pdf_path", "text_cache_path", "text_cache_sha256"):
            if row[key] != source[key]:
                raise ValueError("Review differs from issued packet: " + key)
        if source["fulltext_readiness"] != "ready_for_fulltext_review":
            raise ValueError("Review source was not identity-verified and ready")
        public.append({**{k: v for k, v in row.items() if k not in ("evidence_quote", "pdf_path", "text_cache_path")},
                       **{k: source[k] for k in ("doi", "title", "year", "journal", "identity_status", "fulltext_readiness", "n_pages")}})
    write_csv(RESULTS / "geography_reviews.csv", public)
    flags = read_csv(PRIVATE / "design_parser_flags.csv")
    if len(flags) != len(packet) or {r["scopus_id"] for r in flags} != set(packet):
        raise ValueError("Every reviewed article needs a separate design/parser note")
    public_flags = []
    for row in flags:
        source = packet[row["scopus_id"]]
        if row["source_sha256"] != source["source_sha256"] or row["human_validated"] != "false":
            raise ValueError("Invalid design/parser provenance")
        page = int(row["page"])
        text = next((p["text"] for p in source["pages"] if p["pdf_page"] == page), "")
        quote = " ".join(row["evidence_quote"].split())
        if not quote or quote not in " ".join(text.split()):
            raise ValueError("Design/parser evidence does not occur on cited page")
        public_flags.append({k: v for k, v in row.items() if k != "evidence_quote"})
    write_csv(RESULTS / "design_parser_flags.csv", public_flags)
    summary = {"reviewed_articles": len(rows), "labels": {label: sum(r["sample_us_label"] == label for r in rows)
               for label in ("us_explicit", "us_inferred", "non_us", "unclear", "not_applicable")},
               "source_pdf_cache_and_exact_page_spans_validated": True,
               "reviews_sha256": digest(path.read_bytes()), "packet_sha256": digest((PRIVATE / "fulltext_review_packet.json").read_bytes()),
               "human_validated": False, "no_source_text_or_quotes_published": True,
               "article_counts_modified_by_design_parser_notes": False}
    write_json(RESULTS / "review_validation.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    print(json.dumps(validate_and_export() if args.validate else build(), indent=2))
