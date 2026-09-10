"""Reuse reviewed geography and expose unresolved counts for query comparisons.

No country classifier runs here. Labels come only from recorded human/AI review.
Private evidence is validated before use; public outputs omit source quotations.
"""
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
import argparse
import json
import re

from common import ROOT, digest, read_csv, write_csv, write_json
from dashboard import metadata_digest

VERSION = "query_rankings_2026_09_10"
PRIVATE = ROOT / "private" / VERSION
RESULTS = ROOT / "results" / VERSION
LABELS = {"us_explicit", "us_inferred", "non_us", "unclear", "not_applicable"}
FIELDS = ("title", "abstract", "keywords", "indexed_keywords")
VARIANTS = ("original_query", "narrower_query")


def true(value):
    return str(value).lower() == "true"


def normalize(value):
    return " ".join(str(value).split())


def doi_key(value):
    return re.sub(r"^https?://(?:dx\.)?doi\.org/", "", str(value).strip().lower())


def label(value, mixed=False):
    value = value.lower()
    if value == "mixed_includes_us":
        return "us_explicit", True
    if value not in LABELS:
        raise ValueError("Unknown geography label: " + value)
    return value, mixed


def category(value):
    return "us" if value.startswith("us_") else value


def resolve(evidence):
    """Full-text reviews outrank metadata; substantive conflicts remain visible.

    A conflict at the highest evidence tier is unresolved. An informative full-text
    decision can supersede contrary metadata, but the contradiction is retained.
    Unclear is absence of resolution, not a contradictory non-US decision.
    """
    if not evidence:
        return {"sample_us_label": "unreviewed", "source_review": "unreviewed",
                "conflict": False, "conflict_resolution": "", "mixed": False,
                "adjudicated": False, "selected_evidence": [], "rationale": "No validated geography review available."}
    tier = max(e["priority"] for e in evidence)
    selected = [e for e in evidence if e["priority"] == tier]
    informative = [e for e in selected if e["label"] != "unclear"]
    cats = {category(e["label"]) for e in informative}
    allcats = {category(e["label"]) for e in evidence if e["label"] != "unclear"}
    conflict = len(allcats) > 1 or any(e.get("review_conflict", False) for e in evidence)
    if len(cats) > 1:
        chosen = "unclear"
        resolution = "unresolved_same_evidence_tier"
    elif not informative:
        chosen = "unclear"
        resolution = "independent_fulltext_review_disagreement" if any(e.get("review_conflict", False) for e in selected) else "highest_evidence_tier_unclear" if conflict else ""
    else:
        chosen = ("us_explicit" if any(e["label"] == "us_explicit" for e in informative)
                  else informative[0]["label"])
        resolution = "validated_geography_adjudication" if tier == 3 else "fulltext_supersedes_metadata" if conflict and tier == 2 else ""
    return {"sample_us_label": chosen, "source_review": "full_text" if tier >= 2 else "metadata",
            "conflict": conflict, "conflict_resolution": resolution,
            "adjudicated": tier == 3,
            "mixed": any(e["mixed"] for e in informative) if chosen.startswith("us_") else False,
            "selected_evidence": [e["evidence_id"] for e in selected],
            "rationale": " | ".join(dict.fromkeys(e["rationale"] for e in selected))}


def load_prior(root=ROOT):
    """Return source-level reviews, retaining failed validations in a private log."""
    evidence, invalid, provenance = [], [], []
    metadata = defaultdict(list)
    for relative in ("private/articles.csv", "private/snapshots/2016_2026_before_extension/private/articles.csv"):
        path = root / relative
        if path.exists():
            for row in read_csv(path):
                metadata[row["scopus_id"]].append(row)

    def emit(row, source, priority, validation, source_record=None, extra=None):
        value, mixed = label(row.get("sample_us_label", row.get("geography", "unclear")),
                             true(row.get("us_and_non_us_samples_reported", False)))
        record = {"scopus_id": row["scopus_id"], "doi": row.get("doi", ""), "label": value,
                  "mixed": mixed, "priority": priority, "source_file": source,
                  "source_sha256": digest((root / source).read_bytes()),
                  "validation": validation, "rationale": row.get("rationale", ""),
                  "reviewer": row.get("reviewer", ""), "reviewer_type": row.get("reviewer_type", "AI_assisted"),
                  "human_validated": true(row.get("human_validated", False)),
                  "source_record": source_record or row, **(extra or {})}
        record["evidence_id"] = digest(json.dumps(record, sort_keys=True, ensure_ascii=False))[:20]
        evidence.append(record)

    for relative in ("inputs/top40_us_annotations.csv", "inputs/article_geography.csv"):
        path = root / relative
        if not path.exists():
            continue
        for row in read_csv(path):
            matches = [a for a in metadata[row["scopus_id"]]
                       if (not row.get("metadata_sha256") or metadata_digest(a) == row["metadata_sha256"])
                       and (not row.get("abstract_sha256") or digest(a.get("abstract", "")) == row["abstract_sha256"])
                       and row.get("evidence_field") in FIELDS
                       and row.get("evidence_quote", "") in a.get(row.get("evidence_field", ""), "")
                       and (row.get("evidence_quote") or row["sample_us_label"] == "unclear")]
            if matches:
                emit({**row, "doi": matches[0].get("doi", "")}, relative, 1,
                     "metadata_hash_and_exact_span_validated")
            else:
                invalid.append({"source_file": relative, "scopus_id": row["scopus_id"], "reason": "metadata hash or span mismatch"})

    # Single development coding and two independent held-out reviews are retained
    # individually, so incompatible geography judgments cannot disappear in a join.
    for folder, packet_name, glob in (
        ("design_audit_2026_09_10", "development_packet.json", "development_coder_*.csv"),
        ("search_strategy_2026_09_10", "validation_packet.json", "validation_coder_*.csv")):
        packet_path = root / "private" / folder / packet_name
        if not packet_path.exists():
            continue
        packet = {r["scopus_id"]: r for r in json.loads(packet_path.read_text())}
        for path in sorted(packet_path.parent.glob(glob)):
            for row in read_csv(path):
                article = packet.get(row["scopus_id"], {})
                field, quote = row.get("evidence_field", ""), row.get("evidence_quote", "")
                if field in FIELDS and quote and quote in article.get(field, ""):
                    emit({**row, "doi": article.get("doi", "")}, str(path.relative_to(root)), 1,
                         "source_packet_and_exact_review_span_validated; span_may_address_design_not_geography",
                         extra={"packet_sha256": digest(packet_path.read_bytes())})
                else:
                    invalid.append({"source_file": str(path.relative_to(root)), "scopus_id": row["scopus_id"], "reason": "packet or span mismatch"})

    path = root / "inputs/fulltext_reviews.csv"
    for row in read_csv(path) if path.exists() else []:
        try:
            pdf = root / "private/fulltext/inbox" / row["filename"]
            cache = json.loads((root / "private/fulltext/texts" / (row["filename"] + ".json")).read_text())
            assert digest(pdf.read_bytes()) == row["source_sha256"] == cache["source_sha256"]
            assert normalize(row["evidence_quote"]) in normalize(cache["pages"][int(row["page"]) - 1])
            emit({**row, "doi": metadata[row["scopus_id"]][0].get("doi", "") if metadata[row["scopus_id"]] else ""},
                 "inputs/fulltext_reviews.csv", 2, "pdf_hash_cache_hash_and_exact_page_span_validated")
        except (OSError, ValueError, KeyError, IndexError, AssertionError) as error:
            invalid.append({"source_file": "inputs/fulltext_reviews.csv", "scopus_id": row["scopus_id"], "reason": type(error).__name__})

    # The benchmark validator checks PDF bytes, text-cache hashes, and page spans.
    import precision_benchmark as benchmark
    benchmark_rows = root / "results/precision_benchmark_2026_09_10/availability_manifest.csv"
    bids = {r["benchmark_id"]: r for r in read_csv(benchmark_rows)} if benchmark_rows.exists() else {}
    for path in sorted((root / "private/precision_benchmark_2026_09_10").glob("reviews_coder_*.json")):
        benchmark.validate_reviews(path)
        for review in json.loads(path.read_text()):
            if review.get("evaluation_status") != "completed":
                continue
            article = bids[review["benchmark_id"]]
            axis = review["geography"]
            emit({**article, **review, "geography": axis["decision"], "rationale": axis["rationale"]},
                 str(path.relative_to(root)), 2, "benchmark_pdf_cache_packet_and_exact_page_span_validated",
                 source_record={**{k: review[k] for k in ("benchmark_id", "reviewer", "reviewer_type", "human_validated")}, "geography": axis})

    path = root / "private/proximity_audit_2026_09_10/author_fulltext_examples.csv"
    for row in read_csv(path) if path.exists() else []:
        try:
            pdf = Path(row["private_pdf_path"])
            if not pdf.is_absolute():
                pdf = root.parent / pdf if pdf.parts[0] == root.name else root / pdf
            assert digest(pdf.read_bytes()) == row["pdf_sha256"]
            candidates = list(pdf.parent.glob(pdf.stem + "*.txt"))
            assert any(normalize(row["evidence_quote"]) in normalize(p.read_text()) for p in candidates)
            emit({**row, "geography": row["geography_fulltext"],
                  "rationale": "Existing full-text review reports " + row["geography_fulltext"] + "; " + row["evidence_location"] + "."},
                 str(path.relative_to(root)), 2, "pdf_hash_and_exact_fulltext_span_validated; span_may_address_design_not_geography")
        except (OSError, AssertionError) as error:
            invalid.append({"source_file": str(path.relative_to(root)), "scopus_id": row["scopus_id"], "reason": type(error).__name__})

    # Additional fixed-sample full texts enter geography only after both complete
    # independent passes. Original query-development labels remain untouched.
    wave_folder = root / "private/benchmark_review_wave2_2026_09_10"
    wave_summary = root / "results/benchmark_review_wave2_2026_09_10/review_summary.json"
    wave_packet = wave_folder / "reviewer_packet.json"
    if wave_summary.exists() and wave_packet.exists():
        status = json.loads(wave_summary.read_text())
        extra_ids = {r["benchmark_id"] for r in json.loads(wave_packet.read_text())}
        if status["double_pass"] == 18 + len(extra_ids):
            import benchmark_review_wave2 as wave
            reviews = {}
            for coder in ("A", "B"):
                source = wave_folder / ("reviews_coder_" + coder + ".json")
                wave.validate_reviews(source)
                reviews[coder] = {r["benchmark_id"]: r for r in json.loads(source.read_text()) if r.get("evaluation_status") == "completed"}
            source = root / "results/benchmark_review_wave2_2026_09_10/article_consensus.csv"
            adjudications = {r["benchmark_id"]: r for r in wave.validate_adjudications()}
            for row in read_csv(source):
                bid = row["benchmark_id"]
                if bid not in extra_ids:
                    continue
                a, b = reviews["A"][bid], reviews["B"][bid]
                expected = a["geography"]["decision"] if a["geography"]["decision"] == b["geography"]["decision"] else "unclear"
                adjudication = adjudications.get(bid)
                final_expected = adjudication["decision"] if adjudication else expected
                if row.get("raw_consensus_geography", row["geography"]) != expected or row["geography"] != final_expected:
                    raise ValueError("Stale additional full-text geography consensus: " + bid)
                emit({**row, "geography": expected, "rationale": " | ".join(dict.fromkeys(r["geography"]["rationale"] for r in (a, b))),
                      "reviewer": a["reviewer"] + " + " + b["reviewer"], "reviewer_type": "AI_assisted", "human_validated": False},
                     str(source.relative_to(root)), 2, "two_additional_fulltext_reviews_validated_and_consensus_checked",
                     source_record={"benchmark_id": bid, "coder_A_geography": a["geography"], "coder_B_geography": b["geography"]},
                     extra={"review_conflict": a["geography"]["decision"] != b["geography"]["decision"]})
                if adjudication:
                    emit({**adjudication, "doi": row["doi"], "geography": adjudication["decision"]},
                         str((wave_folder / "adjudications.json").relative_to(root)), 3,
                         "separate_geography_adjudication_pdf_cache_packet_and_exact_page_span_validated")

    packet_path = root / "private" / VERSION / "geography_review_packet.json"
    if packet_path.exists():
        packet = {r["scopus_id"]: r for r in json.loads(packet_path.read_text())}
        paths = list(packet_path.parent.glob("geography_reviews_*.csv")) + list(packet_path.parent.glob("new_geography_reviews_*.json"))
        for path in sorted(paths):
            seen = set()
            rows = read_csv(path) if path.suffix == ".csv" else json.loads(path.read_text())
            for row in rows:
                sid = row["scopus_id"]
                if sid in seen:
                    raise ValueError("Duplicate new geography review: " + sid)
                seen.add(sid)
                article = packet[sid]
                field, quote = row["evidence_field"], row["evidence_quote"]
                value, _ = label(row.get("sample_us_label", row.get("geography", "")))
                if (row["metadata_sha256"] != article["metadata_sha256"] or (field not in FIELDS and not (value == "unclear" and not field and not quote))
                    or quote not in article.get(field, "") or (value != "unclear" and not quote)
                    or not row.get("rationale") or not row.get("reviewer")
                    or row.get("reviewer_type") != "AI_assisted" or row.get("human_validated") not in (False, "false")):
                    raise ValueError("Invalid new geography review: " + sid)
                date.fromisoformat(row["review_date"])
                if true(row.get("us_and_non_us_samples_reported", False)) and not value.startswith("us_"):
                    raise ValueError("Mixed US/non-US flag requires a US label: " + sid)
                emit({**row, "doi": article.get("doi", "")}, str(path.relative_to(root)), 1,
                     "new_packet_metadata_hash_and_exact_geography_span_validated")
    counts = Counter(e["source_file"] for e in evidence)
    for source, count in sorted(counts.items()):
        provenance.append({"source_file": source, "sha256": digest((root / source).read_bytes()), "validated_reviews": count})
    return evidence, invalid, provenance


def harmonize(articles, evidence):
    aliases, dois = {}, {}
    for article in articles:
        identity = article["identity"]
        for sid in (article.get("all_scopus_ids", "") + "|" + article["scopus_id"]).split("|"):
            if sid:
                if sid in aliases and aliases[sid] != identity:
                    raise ValueError("Conflicting Scopus identity alias: " + sid)
                aliases[sid] = identity
        if article.get("doi"):
            key = doi_key(article["doi"])
            if key in dois and dois[key] != identity:
                raise ValueError("Duplicate canonical DOI: " + key)
            dois[key] = identity
    grouped, unmatched = defaultdict(list), []
    for review in evidence:
        a = aliases.get(review["scopus_id"])
        b = dois.get(doi_key(review.get("doi", "")))
        if a and b and a != b:
            raise ValueError("Annotation DOI/Scopus identity conflict")
        identity = a or b
        if identity:
            grouped[identity].append(review)
        else:
            unmatched.append(review)
    rows = []
    for article in articles:
        reviews = grouped[article["identity"]]
        result = resolve(reviews)
        rows.append({**{k: article.get(k, "") for k in ("identity", "scopus_id", "doi", "title", "year", "journal", *VARIANTS)},
                     **{k: v for k, v in result.items() if k != "selected_evidence"},
                     "conflict": str(result["conflict"]).lower(), "mixed": str(result["mixed"]).lower(),
                     "adjudicated": str(result["adjudicated"]).lower(),
                     "n_validated_reviews": len(reviews), "evidence_ids": "|".join(result["selected_evidence"]),
                     "human_validated": "true" if reviews and all(e["human_validated"] for e in reviews) else "false"})
    return rows, grouped, unmatched


def rank_authors(articles, labels, variant, names=None, pool=None, frozen_credits=None):
    codes = {r["identity"]: r for r in labels}
    groups = defaultdict(list)
    for article in articles:
        if not true(article[variant]) or (frozen_credits is None and not true(article["byline_complete"])):
            continue
        credited = (frozen_credits.get(article["identity"], set()) if frozen_credits is not None
                    else {article["first_authid"], article["last_authid"]} - {""})
        for aid in credited:
            if pool is None or aid in pool:
                groups[aid].append(article)
    rows = []
    for aid, group in groups.items():
        counts = Counter(codes[a["identity"]]["sample_us_label"] for a in group)
        us = counts["us_explicit"] + counts["us_inferred"]
        n = len(group)
        rows.append({"authid": aid, "name": (names or {}).get(aid, ""), "n_articles": n,
                     "n_us_articles": us, "n_us_explicit": counts["us_explicit"], "n_us_inferred": counts["us_inferred"],
                     "n_non_us": counts["non_us"], "n_unclear": counts["unclear"], "n_unreviewed": counts["unreviewed"],
                     "n_not_applicable": counts["not_applicable"],
                     "n_us_upper": us + counts["unclear"] + counts["unreviewed"],
                     "n_reviewed": n - counts["unreviewed"], "annotation_coverage": round((n - counts["unreviewed"]) / n, 6),
                     "resolved_geography_coverage": round((n - counts["unreviewed"] - counts["unclear"]) / n, 6),
                     "n_geography_conflicts": sum(true(codes[a["identity"]]["conflict"]) for a in group),
                     "n_mixed_country_us_articles": sum(true(codes[a["identity"]]["mixed"]) for a in group),
                     "article_ids": "|".join(sorted(a["scopus_id"] for a in group)),
                     "scope": "fixed_author_comparison_pool_" + str(len(pool)) if pool is not None else "all_first_last_authors",
                     "count_interpretation": "query-candidate articles with reviewed US sample evidence; unresolved upper counts are scenarios, not confidence intervals"})
    rows.sort(key=lambda r: (-r["n_us_articles"], -r["n_articles"], int(r["authid"])))
    uscounts = Counter(r["n_us_articles"] for r in rows)
    allcounts = Counter(r["n_articles"] for r in rows)
    us_rank = {v: 1 + sum(n for k, n in uscounts.items() if k > v) for v in uscounts}
    all_rank = {v: 1 + sum(n for k, n in allcounts.items() if k > v) for v in allcounts}
    for position, row in enumerate(rows, 1):
        row.update(us_competition_rank=us_rank[row["n_us_articles"]], us_display_position=position,
                   all_competition_rank=all_rank[row["n_articles"]])
    return rows


def select_review_pool(rankings, size=100):
    """Coverage is based on both variants, with all count ties included."""
    selected, detail = set(), {}
    for variant, rows in rankings.items():
        if not rows:
            continue
        n = min(size, len(rows))
        allcut = sorted((r["n_articles"] for r in rows), reverse=True)[n - 1]
        uscut = sorted((r["n_us_articles"] for r in rows), reverse=True)[n - 1]
        allpool = {r["authid"] for r in rows if r["n_articles"] >= allcut}
        uspool = {r["authid"] for r in rows if r["n_us_upper"] >= uscut}
        selected |= allpool | uspool
        detail[variant] = {"total_count_cutoff": allcut, "known_us_count_cutoff": uscut,
                           "total_top100_including_ties": len(allpool), "possible_us_top100_including_ties": len(uspool)}
    return selected, detail


def build():
    articles = read_csv(PRIVATE / "articles.csv")
    evidence, invalid, provenance = load_prior()
    labels, grouped, unmatched = harmonize(articles, evidence)
    names = {}
    for variant in VARIANTS:
        for r in read_csv(RESULTS / (variant + "_ranking.csv")):
            names[r["authid"]] = r.get("name", "")
    common = {r["authid"] for r in read_csv(ROOT / "results/top100_enriched.csv")}
    rankings = {}
    for variant in VARIANTS:
        rankings[variant] = rank_authors(articles, labels, variant, names)
        write_csv(RESULTS / (variant + "_us_ranking.csv"), rankings[variant])
        write_csv(RESULTS / ("common_pool_" + variant + "_us_ranking.csv"), rank_authors(articles, labels, variant, names, common))
    leaders = set(common)
    for rows in rankings.values():
        leaders.update(r["authid"] for r in rows if r["all_competition_rank"] <= 100)
    for variant in VARIANTS:
        uniform = rank_authors(articles, labels, variant, names, leaders)
        write_csv(RESULTS / ("leader_pool_" + variant + "_us_ranking.csv"), uniform)
        write_csv(RESULTS / ("uniform_pool_" + variant + "_us_ranking.csv"), uniform)
    for output_name, membership in (("current_raw", "current_raw"), ("current_published", "current_published_credited")):
        if membership not in articles[0]:
            continue
        source = RESULTS / (output_name + "_ranking.csv")
        if source.exists():
            names.update({r["authid"]: r.get("name", "") for r in read_csv(source)})
        credits = None
        if output_name == "current_published":
            credits = defaultdict(set)
            for row in read_csv(RESULTS / "author_article_links.csv"):
                if row["variant"] == "current_published":
                    credits[row["identity"]].add(row["authid"])
        write_csv(RESULTS / (output_name + "_us_ranking.csv"), rank_authors(articles, labels, membership, names, frozen_credits=credits))
        write_csv(RESULTS / ("common_pool_" + output_name + "_us_ranking.csv"), rank_authors(articles, labels, membership, names, common, credits))
        uniform = rank_authors(articles, labels, membership, names, leaders, credits)
        write_csv(RESULTS / ("leader_pool_" + output_name + "_us_ranking.csv"), uniform)
        write_csv(RESULTS / ("uniform_pool_" + output_name + "_us_ranking.csv"), uniform)
    pool, criteria = select_review_pool(rankings)
    codes = {r["identity"]: r for r in labels}
    required = [a for a in articles if any(true(a[v]) for v in VARIANTS)
                and {a["first_authid"], a["last_authid"]} & pool]
    pending = [a for a in required if codes[a["identity"]]["sample_us_label"] == "unreviewed"]
    leader_articles = [a for a in articles if {a["first_authid"], a["last_authid"]} & leaders]
    leader_pending = [a for a in leader_articles if codes[a["identity"]]["sample_us_label"] == "unreviewed"]
    pending.sort(key=lambda a: digest(VERSION + ":geography:" + a["identity"]))
    upper_by_author = defaultdict(int)
    for rows in rankings.values():
        for row in rows:
            upper_by_author[row["authid"]] = max(upper_by_author[row["authid"]], row["n_us_upper"])
    packet_path = PRIVATE / "geography_review_packet.json"
    packet = {r["scopus_id"]: r for r in json.loads(packet_path.read_text())} if packet_path.exists() else {}
    for article in pending + leader_pending:
        packet.setdefault(article["scopus_id"], {"scopus_id": article["scopus_id"],
            "doi": article.get("doi", ""), **{k: article.get(k, "") for k in FIELDS},
            "metadata_sha256": metadata_digest(article),
            "review_id": "GEO-" + digest(VERSION + ":geography:" + article["identity"])[:12]})
    packet_rows = sorted(packet.values(), key=lambda r: r["review_id"])
    write_json(packet_path, packet_rows)
    wave_path = PRIVATE / "geography_wave1_packet.json"
    if not wave_path.exists():
        write_json(wave_path, sorted([packet[a["scopus_id"]] for a in leader_pending], key=lambda r: r["review_id"]))
    public_queue = [{**{k: a.get(k, "") for k in ("identity", "scopus_id", "doi", "title", "year", "journal")},
                     "review_id": packet[a["scopus_id"]]["review_id"], "status": "unreviewed",
                     "in_uniform_leader_pool": str(bool({a["first_authid"], a["last_authid"]} & leaders)).lower(),
                     "maximum_author_us_upper_count": max(upper_by_author[a["first_authid"]], upper_by_author[a["last_authid"]]),
                     "selection": "article of an author reaching total top100 or possible US top100 in either variant; all cutoff ties included"}
                    for a in pending]
    public_queue.sort(key=lambda r: (not true(r["in_uniform_leader_pool"]), -r["maximum_author_us_upper_count"], r["review_id"]))
    write_csv(RESULTS / "geography_review_queue.csv", public_queue)
    write_csv(RESULTS / "article_geography.csv", labels)
    write_json(PRIVATE / "geography_evidence.json", evidence)
    write_json(PRIVATE / "geography_invalid_evidence.json", invalid)
    write_json(RESULTS / "geography_annotation_provenance.json", provenance)
    variant_coverage = {}
    for variant in (*VARIANTS, "current_raw", "current_published_credited"):
        subset = [codes[a["identity"]] for a in articles if true(a.get(variant, False))]
        variant_coverage[variant] = {"articles": len(subset), "labels": dict(Counter(r["sample_us_label"] for r in subset)),
                                     "reviewed": sum(r["sample_us_label"] != "unreviewed" for r in subset)}
    summary = {"canonical_articles": len(articles), "valid_source_reviews": len(evidence),
               "distinct_previously_reviewed_scopus_ids": len({e["scopus_id"] for e in evidence}),
               "invalid_source_reviews": len(invalid), "unmatched_prior_reviews": len(unmatched),
               "article_labels": dict(Counter(r["sample_us_label"] for r in labels)),
               "articles_with_conflicting_evidence": sum(true(r["conflict"]) for r in labels),
               "articles_with_unresolved_geography_conflicts": sum(true(r["conflict"]) and r["sample_us_label"] == "unclear" for r in labels),
               "geography_adjudicated_articles": sum(true(r["adjudicated"]) for r in labels),
               "review_selection": criteria, "review_pool_authors": len(pool),
               "review_pool_articles": len(required), "new_articles_requiring_review": len(pending),
               "common_pool_authors": len(common), "human_validated": False,
               "union_current_and_new_total_leaders_authors": len(leaders),
               "union_leader_pool_articles": len(leader_articles),
               "union_leader_pool_articles_unreviewed": len(leader_pending),
               "union_leader_pool_article_labels": dict(Counter(codes[a["identity"]]["sample_us_label"] for a in leader_articles)),
               "wave1_fixed_packet_articles": len(json.loads(wave_path.read_text())),
               "variant_coverage": variant_coverage,
               "packet_order": "deterministic hash of canonical article identity, independent of author name and rank",
               "precedence": "Separately validated geography adjudications take precedence over raw reviews, and full-text reviews over metadata. Same-tier US/non-US contradictions remain unclear; original disagreements remain flagged after adjudication.",
               "interpretation": "Geography evidence does not certify survey-experiment design. Known US counts are observed lower counts, and unclear/unreviewed counts define a resolution scenario only."}
    write_json(RESULTS / "geography_summary.json", summary)
    codebook = """# Geography review for query-ranking comparison

Read only the supplied title, abstract, keywords, and indexed keywords. The packet
omits authors, affiliations, journal, query route, ranking, and prior labels.
Code the country of empirical human samples, not the authors' country, language,
journal, platform, or topic alone. US_explicit requires a stated US/American sample
or named unambiguously US sampling location. US_inferred permits a specifically
US institutional/electoral setting whose recruited respondents are reasonably
inferred to be US based; studying an American topic alone is insufficient if the
sample could be foreign. non_US requires affirmative non-US sampling evidence.
mixed_includes_US means at least one US sample plus another country. unclear is
appropriate whenever the metadata cannot resolve the sample country. Do not
assign non_US merely because US is absent. not_applicable is reserved for a
clearly non-empirical article without human sample data, not an unclear design.

Save CSV private/query_rankings_2026_09_10/geography_reviews_<reviewer>.csv with:
scopus_id,geography,evidence_field,evidence_quote,rationale,metadata_sha256,
reviewer,reviewer_type,review_date,human_validated.
Allowed geography: US_explicit,US_inferred,mixed_includes_US,non_US,unclear,
not_applicable. evidence_field is title/abstract/keywords/indexed_keywords.
Use a SHORT EXACT verbatim span from that field, supporting geography where
available; unclear may use an empty field and span. Give a concise ORIGINAL rationale.
Copy metadata_sha256 from the packet; reviewer_type=AI_assisted and
human_validated=false. Read every assigned record; keyword rules are not review.
Do not inspect authors, query memberships, existing labels, or other reviewers.
"""
    (RESULTS / "geography_review_codebook.md").write_text(codebook)
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", action="store_true")
    args = parser.parse_args()
    if args.inventory:
        ev, bad, sources = load_prior()
        write_json(PRIVATE / "geography_evidence.json", ev)
        write_json(PRIVATE / "geography_invalid_evidence.json", bad)
        write_json(RESULTS / "geography_annotation_provenance.json", sources)
        print(json.dumps({"reviews": len(ev), "unique_scopus_ids": len({e["scopus_id"] for e in ev}),
                          "invalid": bad, "sources": sources}, indent=2))
    else:
        build()
