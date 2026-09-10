"""Reproduce a geography-review priority queue from the local ranking snapshot.

No country is assigned by this script. Inputs retain their recorded decisions.
Public outputs contain bibliographic metadata and original methodological notes;
the full metadata packet and local PDF paths remain private.
"""
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
from common import read_csv, write_csv, write_json
from dashboard import metadata_digest

VERSION = "us_geography_priority_2026_09_10"
OUT = ROOT / "results" / VERSION
PRIVATE = ROOT / "private" / VERSION
RANKS = ROOT / "results/query_rankings_2026_09_10"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    sources = [ROOT / "private/query_rankings_2026_09_10/articles.csv",
               RANKS / "article_geography.csv",
               RANKS / "uniform_pool_original_query_us_ranking.csv",
               RANKS / "original_query_ranking.csv",
               RANKS / "original_query_top100_with_cutoff_ties.csv",
               ROOT / "inputs/manual_download_status.csv",
               ROOT / "inputs/fulltext_followups.csv",
               ROOT / "results/open_access_acquisition.csv"]
    articles = read_csv(sources[0])
    labels = {r["identity"]: r for r in read_csv(sources[1])}
    rows = read_csv(sources[2])
    authors = {r["authid"]: r for r in rows}
    pool = set(authors)
    leaders = {r["authid"] for r in read_csv(sources[4])}
    statuses = {r["scopus_id"]: r for r in read_csv(sources[5])}
    followups = {r["scopus_id"]: r for r in read_csv(sources[6])}
    acquisition = {r["scopus_id"]: r for r in read_csv(sources[7])}
    latest_path = OUT / "round10_status.csv"
    latest = {r["scopus_id"]: r for r in read_csv(latest_path)} if latest_path.exists() else {}
    if latest_path.exists():
        sources.append(latest_path)
    counts = {aid: int(r["n_us_articles"]) for aid, r in authors.items()}
    total_ranks = {aid: int(r["all_competition_rank"]) for aid, r in authors.items()}
    us_ranks = {aid: int(r["us_competition_rank"]) for aid, r in authors.items()}
    important = {aid for aid in pool if total_ranks[aid] <= 50 or us_ranks[aid] <= 50}
    allpairs = list(combinations(sorted(pool), 2))
    toppairs = [(a, b) for a, b in allpairs if a in important or b in important]
    leaderpairs = [(a, b) for a, b in allpairs if a in leaders and b in leaders]
    selected = [a for a in articles if {a["first_authid"], a["last_authid"]} & pool]
    unresolved = [a for a in selected if labels[a["identity"]]["sample_us_label"] in {"unclear", "unreviewed"}]

    # Same article can credit two researchers. Both move together: their mutual
    # tie is not broken by resolving this shared paper as US based.
    def effects(credited, pairs):
        broken, formed = set(), set()
        for a, b in pairs:
            before = counts[a] - counts[b]
            after = before + int(a in credited) - int(b in credited)
            if before == 0 and after != 0:
                broken.add((a, b))
            elif before != 0 and after == 0:
                formed.add((a, b))
        return broken, formed

    queue, packet, private_sources = [], [], []
    effectsets = {}
    for article in unresolved:
        sid = article["scopus_id"]
        credited = ({article["first_authid"], article["last_authid"]} & pool
                    if article["original_query"] == "true" else set())
        broken, formed = effects(credited, toppairs)
        lb, lf = effects(credited, leaderpairs)
        ab, af = effects(credited, allpairs)
        effectsets[sid] = broken
        local_pdf = ROOT / "private/fulltext/inbox" / (sid + ".pdf")
        local_text = ROOT / "private/fulltext/texts" / (sid + ".pdf.json")
        available = local_pdf.exists() and local_text.exists()
        verified = False
        if available:
            cache = json.loads(local_text.read_text())
            verified = cache["source_sha256"] == sha(local_pdf)
            private_sources.append({"scopus_id": sid, "pdf_path": str(local_pdf.relative_to(ROOT)),
                                    "text_cache_path": str(local_text.relative_to(ROOT)),
                                    "pdf_sha256": sha(local_pdf), "cache_sha256": sha(local_text),
                                    "cache_matches_pdf": verified, "pages": len(cache["pages"])})
        priority = {
            "scopus_id": sid, "identity": article["identity"], "doi": article["doi"],
            "title": article["title"], "year": article["year"], "journal": article["journal"],
            "article_url": "https://doi.org/" + article["doi"] if article["doi"] else "https://www.scopus.com/record/display.uri?eid=2-s2.0-" + sid,
            "current_geography": labels[article["identity"]]["sample_us_label"],
            "credited_author_ids": "|".join(sorted(credited)),
            "credited_researchers": "; ".join(authors[x]["name"] for x in sorted(credited)),
            "n_credited_pool_authors": len(credited),
            "n_top50_total_authors": sum(total_ranks[x] <= 50 for x in credited),
            "n_top50_us_authors": sum(us_ranks[x] <= 50 for x in credited),
            "n_total_leaders_including_cutoff_ties": len(credited & leaders),
            "top50_tied_pairs_broken_if_us": len(broken),
            "top50_new_ties_if_us": len(formed),
            "leader114_tied_pairs_broken_if_us": len(lb),
            "leader114_new_ties_if_us": len(lf),
            "pool120_tied_pairs_broken_if_us": len(ab),
            "pool120_new_ties_if_us": len(af),
            "maximum_current_us_count": max((counts[x] for x in credited), default=0),
            "minimum_current_total_rank": min((total_ranks[x] for x in credited), default=0),
            "available_historical_inbox_pdf": str(verified).lower(),
            "user_download_status": statuses.get(sid, {}).get("status", ""),
            "existing_followup": followups.get(sid, {}).get("needed_material", ""),
            "prior_automatic_acquisition_status": acquisition.get(sid, {}).get("acquisition_status", "not_previously_checked"),
            "latest_priority_round_status": latest.get(sid, {}).get("status", ""),
            "prior_open_location_url": acquisition.get(sid, {}).get("open_location_url", ""),
            "review_action": ("Inspect available PDF and seek sampling appendix if country remains absent" if verified else
                              "Await an alternative manuscript or lawful copy; user cannot obtain Taylor & Francis papers, so do not repeat the publisher download request"
                              if latest.get(sid, {}).get("status") == "awaiting_alternative_copy" else
                              "Obtain methods/sampling pages or a source-verified country statement"),
            "interpretation": "Hypothetical US-positive resolution of this one article; no estimated probability and no change to total article counts",
        }
        queue.append(priority)
        packet.append({"scopus_id": sid, "doi": article["doi"],
                       **{k: article.get(k, "") for k in ("title", "abstract", "keywords", "indexed_keywords")},
                       "metadata_sha256": metadata_digest(article)})

    # Greedy coverage gives priority to previously unaddressed tied pairs, with
    # no names, vendors, countries, or inferred likelihood in the score.
    remaining, ordered, covered = list(queue), [], set()
    while remaining:
        chosen = min(remaining, key=lambda r: (
            -len(effectsets[r["scopus_id"]] - covered),
            -r["n_top50_total_authors"], -r["n_top50_us_authors"],
            -r["top50_tied_pairs_broken_if_us"],
            -r["leader114_tied_pairs_broken_if_us"],
            -r["top50_new_ties_if_us"], -r["maximum_current_us_count"], r["scopus_id"]))
        chosen["new_top50_tied_pairs_covered_at_selection"] = len(effectsets[chosen["scopus_id"]] - covered)
        covered |= effectsets[chosen["scopus_id"]]
        chosen["queue_position"] = len(ordered) + 1
        chosen["download_batch"] = len(ordered) // 10 + 1
        ordered.append(chosen)
        remaining.remove(chosen)
    order = {r["scopus_id"]: r["queue_position"] for r in ordered}
    packet.sort(key=lambda r: order[r["scopus_id"]])
    author_rows = []
    for aid, r in authors.items():
        aa = [q for q in ordered if aid in q["credited_author_ids"].split("|")]
        author_rows.append({"authid": aid, "name": r["name"], "total_article_count": r["n_articles"],
                            "total_competition_rank": total_ranks[aid], "current_us_count": counts[aid],
                            "current_us_competition_rank": us_ranks[aid], "unresolved_articles": len(aa),
                            "us_upper_resolution_scenario": counts[aid] + len(aa),
                            "total_leader_with_cutoff_ties": str(aid in leaders).lower(),
                            "local_inbox_pdfs": sum(q["available_historical_inbox_pdf"] == "true" for q in aa),
                            "queue_scopus_ids": "|".join(q["scopus_id"] for q in aa)})
    author_rows.sort(key=lambda r: (-r["unresolved_articles"], -r["current_us_count"], int(r["authid"])))
    write_csv(OUT / "article_priority_queue.csv", ordered)
    downloads, unchecked = [], []
    for r in ordered:
        if r["available_historical_inbox_pdf"] == "true" or r["user_download_status"] == "user_unavailable":
            continue
        target = unchecked if r["prior_automatic_acquisition_status"] == "not_previously_checked" and not r["latest_priority_round_status"] else downloads
        target.append({**r, "download_position": len(target) + 1,
                       "download_batch": len(target) // 10 + 1,
                       "suggested_filename": r["scopus_id"] + ".pdf"})
    write_csv(OUT / "manual_download_queue.csv", downloads)
    write_csv(OUT / "automatic_acquisition_queue.csv", unchecked)
    write_csv(OUT / "author_uncertainty.csv", author_rows)
    write_json(PRIVATE / "prioritized_metadata_packet.json", packet)
    write_json(PRIVATE / "available_historical_fulltext.json", private_sources)
    manifest = {
        "version": VERSION, "reference_variant": "original_query", "author_pool": len(pool),
        "total_leaders_including_cutoff_ties": len(leaders), "distinct_pool_articles": len(selected),
        "article_denominator_scope": "Cross-variant union for the same 120 authors; author-count impacts use original_query membership only",
        "distinct_pool_original_query_articles": sum(a["original_query"] == "true" for a in selected),
        "pool_original_query_us_articles": sum(a["original_query"] == "true" and labels[a["identity"]]["sample_us_label"] in {"us_explicit", "us_inferred"} for a in selected),
        "unresolved_pool_articles": len(unresolved),
        "unresolved_articles_of_total_top50": sum(r["n_top50_total_authors"] > 0 for r in ordered),
        "unresolved_articles_of_us_top50": sum(r["n_top50_us_authors"] > 0 for r in ordered),
        "unresolved_articles_of_total_leader114": sum(r["n_total_leaders_including_cutoff_ties"] > 0 for r in ordered),
        "unresolved_authors": sum(r["unresolved_articles"] > 0 for r in author_rows),
        "available_verified_historical_inbox_pdfs": sum(r["available_historical_inbox_pdf"] == "true" for r in ordered),
        "user_unavailable_not_requested_again": sum(r["user_download_status"] == "user_unavailable" for r in ordered),
        "manual_download_queue_articles": len(downloads),
        "automatic_acquisition_not_previously_checked": len(unchecked),
        "distinct_top50_tied_pairs_covered": len(covered),
        "annotation_assignment": "Queue generation assigns no geography label. Every unresolved article in the fixed pool is included; names and country-likelihood do not set priority.",
        "tie_interpretation": "Within the same 120-author pool, a pair matters for top50 if either researcher currently has total or US competition rank <=50. Shared-paper coauthors move together. One US resolution may break old ties and create new ones; separate scenarios are not additive.",
        "sources": [{"path": str(p.relative_to(ROOT)), "sha256": sha(p)} for p in sources],
        "outputs": {str(p.relative_to(ROOT)): sha(p) for p in [OUT / "article_priority_queue.csv", OUT / "manual_download_queue.csv", OUT / "automatic_acquisition_queue.csv", OUT / "author_uncertainty.csv", PRIVATE / "prioritized_metadata_packet.json", PRIVATE / "available_historical_fulltext.json"]},
    }
    write_json(OUT / "priority_manifest.json", manifest)
    print(json.dumps({k: v for k, v in manifest.items() if k not in {"sources", "outputs"}}, indent=2))


if __name__ == "__main__":
    main()
