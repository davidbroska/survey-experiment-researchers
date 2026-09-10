"""Second coauthor-download wave; isolate import, review shards, and publication.

Reuse the previous tested importer with a temporary in-process namespace. The
previous packet, reviews and public outputs are never rewritten. All sampled
identities remain present; separate design flags do not change article counts.
"""
import argparse
from contextlib import contextmanager
import json
import re
import threading

from common import ROOT, digest, read_csv, write_csv, write_json
import coauthor_fulltext_update as prior
from open_access import normalize, doi_key

VERSION = "coauthor_update_wave2_2026_09_10"
PRIVATE, RESULTS = ROOT / "private" / VERSION, ROOT / "results" / VERSION
REVIEW_FIELDS = prior.REVIEW_FIELDS
REVIEWERS = ("root", "strategy", "participant")
LOCK = threading.RLock()


def cached_identity():
    """Same title/DOI rules, normalizing each PDF opening only once per run."""
    pages_cache, article_cache = {}, {}
    def check(pages, article):
        key = id(pages)
        if key not in pages_cache:
            pages_cache[key] = (pages, normalize(" ".join(pages[:3])))
        opening = pages_cache[key][1]
        key = id(article)
        if key not in article_cache:
            title = normalize(article.get("title", ""))
            words = {normalize(w) for w in re.findall(r"\w{4,}", article.get("title", ""))}
            article_cache[key] = (article, title, words, normalize(doi_key(article.get("doi", ""))))
        _, title, words, doi = article_cache[key]
        if len(title) >= 20 and title in opening:
            return "verified_title_in_opening_pages"
        coverage = sum(w in opening for w in words) / len(words) if words else 0
        if doi and doi in opening and coverage >= .85:
            return "verified_doi_and_title_in_opening_pages"
        return "needs_identity_review"
    return check


@contextmanager
def namespace():
    with LOCK:
        old = prior.PRIVATE, prior.RESULTS, prior.identity
        try:
            prior.PRIVATE, prior.RESULTS, prior.identity = PRIVATE, RESULTS, cached_identity()
            yield
        finally:
            prior.PRIVATE, prior.RESULTS, prior.identity = old


def build():
    with namespace():
        summary = prior.build()
    availability = read_csv(RESULTS / "availability_manifest.csv")
    for row in availability:
        ready = row["fulltext_readiness"] == "ready_for_fulltext_review"
        row["fulltext_already_supplied"] = "true"
        row["further_pdf_download_needed"] = str(not ready).lower()
    write_csv(RESULTS / "availability_manifest.csv", availability)
    rows = json.loads((PRIVATE / "fulltext_review_packet.json").read_text())
    if summary["unmatched_downloads"]:
        raise ValueError("Some copies require identity review; do not assign or exclude them automatically")
    assignments = []
    quotient, remainder = divmod(len(rows), len(REVIEWERS))
    start = 0
    for i, reviewer in enumerate(REVIEWERS):
        size = quotient + (i < remainder)
        shard = rows[start:start + size]
        start += size
        prior.write_immutable(PRIVATE / ("packet_" + reviewer + ".json"), shard)
        assignments += [{"scopus_id": r["scopus_id"], "title": r["title"], "reviewer_shard": reviewer} for r in shard]
    write_csv(RESULTS / "review_assignment.csv", assignments)
    return summary


def validate_shard(reviewer):
    from query_ranking_geography import validate_priority_fulltext
    if reviewer not in REVIEWERS:
        raise ValueError("Unknown reviewer shard")
    packet = {r["scopus_id"]: r for r in json.loads((PRIVATE / ("packet_" + reviewer + ".json")).read_text())}
    reviews = read_csv(PRIVATE / ("reviewer_" + reviewer + ".csv"))
    flags = read_csv(PRIVATE / ("designflags_" + reviewer + ".csv"))
    for label, rows in (("geography", reviews), ("design/parser", flags)):
        if len(rows) != len(packet) or {r["scopus_id"] for r in rows} != set(packet):
            raise ValueError("Expected exactly the assigned " + label + " reviews")
    for row in reviews:
        validate_priority_fulltext(row, ROOT)
        source = packet[row["scopus_id"]]
        for key in ("filename", "source_sha256", "pdf_path", "text_cache_path", "text_cache_sha256"):
            if row[key] != source[key]:
                raise ValueError("Review differs from issued source packet")
    for row in flags:
        source = packet[row["scopus_id"]]
        text = next((p["text"] for p in source["pages"] if p["pdf_page"] == int(row["page"])), "")
        quote = " ".join(row["evidence_quote"].split())
        if row["source_sha256"] != source["source_sha256"] or not quote or quote not in " ".join(text.split()):
            raise ValueError("Design/parser source or page evidence differs")
        if row["human_validated"] != "false" or row["article_count_exclusion_applied"] != "false":
            raise ValueError("Provisional design notes cannot change counts or claim human validation")
    return {"reviewer_shard": reviewer, "validated_articles": len(reviews), "source_hashes_and_exact_page_spans_validated": True}


def aggregate():
    reviews, flags, validation = [], [], []
    for reviewer in REVIEWERS:
        validation.append(validate_shard(reviewer))
        reviews += read_csv(PRIVATE / ("reviewer_" + reviewer + ".csv"))
        flags += read_csv(PRIVATE / ("designflags_" + reviewer + ".csv"))
    write_csv(PRIVATE / "fulltext_reviews.csv", sorted(reviews, key=lambda r: r["scopus_id"]), REVIEW_FIELDS)
    write_csv(PRIVATE / "design_parser_flags.csv", sorted(flags, key=lambda r: r["scopus_id"]))
    with namespace():
        summary = prior.validate_and_export()
    public = read_csv(RESULTS / "geography_reviews.csv")
    for row in public:
        row["fulltext_already_supplied"] = "true"
        row["further_pdf_download_needed"] = "false"
        row["remaining_resolution_needed"] = ("sample-location clarification from supplement or author"
                                                if row["sample_us_label"] == "unclear" else "none")
    write_csv(RESULTS / "geography_reviews.csv", public)
    summary["reviewer_shards"] = validation
    summary["previous_coauthor_wave_unchanged"] = True
    summary["unresolved_geographies_with_pdf_already_supplied"] = sum(r["sample_us_label"] == "unclear" for r in public)
    write_json(RESULTS / "review_validation.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-shard", choices=REVIEWERS)
    parser.add_argument("--aggregate", action="store_true")
    args = parser.parse_args()
    value = validate_shard(args.validate_shard) if args.validate_shard else aggregate() if args.aggregate else build()
    print(json.dumps(value, indent=2))
