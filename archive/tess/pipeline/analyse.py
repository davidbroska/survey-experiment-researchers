"""Evidence trace, provisional ranks, sensitivity checks and review instruments."""
from collections import Counter, defaultdict
import json
import re

from common import ROOT, digest, now, read_csv, write_csv, write_json
import query

REVIEW_FIELDS = ["scopus_id", "survey_experiment", "text_treatment", "new_data", "parser_compatible", "data_access", "panel_provider", "evidence_field",
                 "evidence_quote", "reviewer", "reviewer_type", "source_url", "notes"]


def eligibility_status(review):
    fields = ("survey_experiment", "new_data", "parser_compatible", "data_access")
    if any(review.get(k) == "no" for k in fields):
        return "excluded"
    if all(review.get(k) == "yes" for k in fields):
        return "confirmed"
    return "pending"


def deduplicate(rows):
    groups = defaultdict(list)
    for row in rows:
        doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", row.get("doi", "").strip().lower())
        groups["doi:"+doi if doi else "scopus:"+row["scopus_id"]].append(row)
    keep, duplicates = [], []
    for key, values in sorted(groups.items()):
        values.sort(key=lambda r: (r.get("byline_complete") != "true", not bool(r.get("abstract")), int(r["scopus_id"])))
        chosen = values[0]
        keep.append(chosen)
        for other in values[1:]:
            duplicates.append({"duplicate_key": key, "kept_scopus_id": chosen["scopus_id"],
                "removed_scopus_id": other["scopus_id"], "byline_conflict": chosen["authids"] != other["authids"]})
    return keep, duplicates


def rank(rows, names, seeds, credit="first_last"):
    scores = defaultdict(lambda: {"articles": set(), "text": set(), "panel": set(), "providers": set(), "first": set(), "last": set(), "fractional": 0.0})
    for row in rows:
        if row.get("byline_complete") != "true":
            continue
        all_ids = {v for v in row["authids"].split("|") if v}
        ids = {row["first_authid"], row["last_authid"]} if credit == "first_last" else all_ids
        for aid in ids - {""}:
            s = scores[aid]
            sid = row["scopus_id"]
            if sid in s["articles"]:
                continue
            s["articles"].add(sid)
            s["fractional"] += 1 / len(all_ids)
            if row.get("text_cue") == "true":
                s["text"].add(sid)
            if row.get("panel_provider_cues"):
                s["panel"].add(sid)
                s["providers"].update(row["panel_provider_cues"].split("|"))
            for kind in ("first", "last"):
                if aid == row[kind+"_authid"]:
                    s[kind].add(sid)
    ordered = sorted(scores, key=lambda aid: (-len(scores[aid]["articles"]), int(aid)))
    frequencies = Counter(len(s["articles"]) for s in scores.values())
    score_ranks, preceding = {}, 0
    for score in sorted(frequencies, reverse=True):
        score_ranks[score] = preceding + 1
        preceding += frequencies[score]
    result = []
    for position, aid in enumerate(ordered, 1):
        s = scores[aid]
        count = len(s["articles"])
        result.append({"position": position, "score_rank": score_ranks[count],
            "authid": aid, "name": names.get(aid, {}).get("name", ""), "n_articles": count,
            "n_text_cue_articles": len(s["text"]), "n_first": len(s["first"]), "n_last": len(s["last"]),
            "n_panel_cue_articles": len(s["panel"]), "panel_provider_cues": "|".join(sorted(s["providers"])),
            "fractional_credit_on_counted_articles": round(s["fractional"], 6),
            "tess_investigator_in_frozen_roster": str(aid in seeds).lower(),
            "article_ids": "|".join(sorted(s["articles"], key=int)),
            "scopus_author_url": "https://www.scopus.com/authid/detail.uri?authorId="+aid,
            "status": "provisional_query_candidates"})
    return result


def decisions(rows):
    path = ROOT / "inputs" / "article_decisions.csv"
    if not path.exists():
        write_csv(path, [], REVIEW_FIELDS)
    elif not read_csv(path):
        write_csv(path, [], REVIEW_FIELDS)
    byid = {r["scopus_id"]: r for r in rows}
    accepted, errors = {}, []
    for d in read_csv(path):
        sid = d["scopus_id"]
        reason = ""
        if sid not in byid:
            reason = "unknown_scopus_id"
        elif sid in accepted:
            reason = "duplicate_decision"
        elif any(d.get(k) not in {"yes", "no", "unclear"} for k in ("survey_experiment", "text_treatment", "new_data", "parser_compatible", "data_access")):
            reason = "invalid_label"
        elif not d.get("reviewer") or d.get("reviewer_type") not in {"human", "AI_assisted"}:
            reason = "missing_reviewer_provenance"
        elif d["survey_experiment"] == "yes":
            field = d.get("evidence_field", "")
            source = byid[sid].get(field, "") if field in {"title", "abstract", "keywords", "indexed_keywords"} else ""
            if field == "fulltext":
                p = ROOT / "private" / "fulltext" / (sid+".txt")
                source = p.read_text() if p.exists() else ""
            if not d.get("evidence_quote") or query.normalize(d["evidence_quote"]) not in query.normalize(source):
                reason = "evidence_not_verifiable"
        if reason:
            errors.append({"scopus_id": sid, "error": reason})
        else:
            accepted[sid] = d
    write_csv(ROOT / "results" / "decision_errors.csv", errors, ["scopus_id", "error"])
    if errors:
        raise RuntimeError("Invalid review decisions; see results/decision_errors.csv")
    return accepted


def analyse():
    manifest = json.loads((ROOT / "results" / "retrieval_manifest.json").read_text())
    if manifest["query_sha256"] != digest(query.build()):
        raise RuntimeError("Query changed since retrieval; rerun retrieve before analysing")
    if not manifest["complete"]:
        raise RuntimeError("Cannot analyse an incomplete retrieval")
    raw = read_csv(ROOT / "private" / "articles.csv")
    frame = {r["source_id"]: r for r in read_csv(ROOT / "results" / "venue_frame.csv")}
    inframe = [r for r in raw if r["source_id"] in frame and query.START_YEAR <= int(r["year"]) <= query.END_YEAR]
    rows, duplicates = deduplicate(inframe)
    write_csv(ROOT / "results" / "duplicate_log.csv", duplicates,
              ["duplicate_key", "kept_scopus_id", "removed_scopus_id", "byline_conflict"])
    names = {r["authid"]: r for r in read_csv(ROOT / "inputs" / "author_names.csv")}
    seeds = {r["auid"] for r in read_csv(ROOT / "inputs" / "tess_investigators.csv") if r["auid"]}
    reviewed = decisions(rows)
    evidence, summaries, candidates, strata = [], [], [], defaultdict(list)
    for row in rows:
        hits = query.match(row)
        families = {h["family"] for h in hits}
        row["text_cue"] = str(any(query.TEXT_RX.search(unit) for field, unit, original in query.units(row))).lower()
        row["panel_provider_cues"] = "|".join(query.panel_cues(row))
        row["design_review_cue"] = str(query.design_review_cue(row)).lower()
        core = any(f["id"] in families and f["role"] != "expansion" for f in query.FAMILIES)
        stratum = "core" if core else next((f["id"] for f in query.FAMILIES if f["id"] in families), "unverified_match")
        strata[stratum].append(row)
        review = reviewed.get(row["scopus_id"], {})
        row["screening_status"] = eligibility_status(review)
        row["matched_families"] = "|".join(sorted(families))
        row["stratum"] = stratum
        row["local_phrase_verified"] = str(bool(hits)).lower()
        for hit in hits:
            evidence.append({"scopus_id": row["scopus_id"], **hit})
        summaries.append({k: v for k, v in row.items() if k not in {"abstract", "keywords", "indexed_keywords"}})
        if hits and row["screening_status"] != "excluded":
            candidates.append(row)
    write_csv(ROOT / "results" / "punctuation_audit.csv", [
        {"scopus_id": r["scopus_id"], "title": r["title"],
         "contains_survey_punctuation_experimental": "true", "valid_local_match_elsewhere": r["local_phrase_verified"],
         "action": "retain independent valid evidence; otherwise review"}
        for r in rows if re.search(r"\bsurvey[,.;:]\s+experiment\w*", r["abstract"], re.I)],
        ["scopus_id", "title", "contains_survey_punctuation_experimental", "valid_local_match_elsewhere", "action"])
    write_csv(ROOT / "private" / "match_evidence.csv", evidence,
        ["scopus_id", "family", "field", "phrase", "evidence"])
    write_csv(ROOT / "results" / "article_metadata.csv", summaries)
    ranks = rank(candidates, names, seeds)
    write_csv(ROOT / "results" / "ranking_provisional.csv", ranks)
    write_csv(ROOT / "results" / "top40_provisional.csv", ranks[:40])
    # No file named final/top40_confirmed is emitted while eligibility remains
    # unresolved. Missing indexing fields cannot be treated as negative evidence.
    confirmed = [r for r in rows if r["screening_status"] == "confirmed"]
    confirmed_ranks = rank(confirmed, names, seeds)
    for r in confirmed_ranks:
        r["status"] = "ranking_of_reviewed_subset_only"
    write_csv(ROOT / "results" / "ranking_reviewed_subset.csv", confirmed_ranks, list(ranks[0]) if ranks else [])
    top40 = {r["authid"] for r in ranks[:40]}
    sensitivity = []
    variants = [("venue_threshold_1", candidates, "first_last"),
        ("venue_threshold_3", [r for r in candidates if int(frame[r["source_id"]]["n_tess_investigators"]) >= 3], "first_last"),
        ("venue_threshold_5", [r for r in candidates if int(frame[r["source_id"]]["n_tess_investigators"]) >= 5], "first_last"),
        ("all_authors", candidates, "all"),
        ("text_cue_only", [r for r in candidates if r["text_cue"] == "true"], "first_last"),
        ("core_only", [r for r in candidates if r["stratum"] == "core"], "first_last")]
    for label, subset, credit in variants:
        ranking = rank(subset, names, seeds, credit)
        write_csv(ROOT / "results" / "sensitivity" / (label+"_top40.csv"), ranking[:40])
        sensitivity.append({"variant": label, "n_articles": len(subset), "n_authors": len(ranking),
            "overlap_with_primary_top40": len(top40 & {r["authid"] for r in ranking[:40]})})
    write_csv(ROOT / "results" / "sensitivity_summary.csv", sensitivity)
    tess_only = [r.copy() for r in ranks if r["authid"] in seeds]
    for i, r in enumerate(tess_only, 1):
        r["position"] = i
    write_csv(ROOT / "results" / "sensitivity" / "tess_only_top40.csv", tess_only[:40])
    # Disjoint strata and deterministic pseudo-random order permit valid weighted
    # precision estimation after annotation. Preserve the full sampling frame.
    sample = []
    for stratum, pool in sorted(strata.items()):
        ordered = sorted(pool, key=lambda r: digest("validation-v1-20260908:"+r["scopus_id"]))
        n = min(40 if stratum == "core" else 25, len(pool))
        for row in ordered[:n]:
            sample.append({"scopus_id": row["scopus_id"], "stratum": stratum,
                "population_n": len(pool), "sample_n": n, "inclusion_probability": n/len(pool),
                "title": row["title"], "abstract": row["abstract"], "keywords": row["keywords"],
                "survey_experiment": "", "text_treatment": "", "new_data": "", "parser_compatible": "", "data_access": "", "panel_provider": "", "evidence_quote": "",
                "reviewer": "", "notes": ""})
    write_csv(ROOT / "private" / "validation_sample.csv", sample)
    write_csv(ROOT / "results" / "validation_sample_ids.csv", sample,
        ["scopus_id", "stratum", "population_n", "sample_n", "inclusion_probability"])
    shortlist_ids = set().union(*(set(r["article_ids"].split("|")) for r in ranks[:60])) if ranks else set()
    write_csv(ROOT / "private" / "shortlist_article_review.csv",
        [{**r, **{k: "" for k in REVIEW_FIELDS if k != "scopus_id"}} for r in rows if r["scopus_id"] in shortlist_ids])
    cutoff = int(ranks[39]["n_articles"]) if len(ranks) >= 40 else None
    tied = [r for r in ranks if r["n_articles"] == cutoff] if cutoff is not None else []
    write_csv(ROOT / "results" / "cutoff_ties.csv", tied, list(ranks[0]) if ranks else [])
    flow = {"generated_at": now(), "global_retrieved": len(raw), "in_frame": len(inframe),
        "unique_articles": len(rows), "doi_duplicates_removed": len(duplicates),
        "locally_verified_candidates": len(candidates), "unverified_match_needs_review": len(strata["unverified_match"]),
        "incomplete_bylines_in_candidates": sum(r["byline_complete"] != "true" for r in candidates),
        "ranked_authors": len(ranks), "reviewed_articles": len(reviewed), "confirmed_new_survey_experiments": len(confirmed),
        "top40_cutoff_article_count": cutoff, "authors_tied_at_cutoff": len(tied),
        "strata": {k: len(v) for k, v in sorted(strata.items())},
        "publication_status": "provisional: identity, experimental eligibility, parser compatibility and data access pending",
        "query_sha256": digest(query.build()), "article_sha256": digest((ROOT / "private" / "articles.csv").read_bytes()),
        "frame_sha256": digest((ROOT / "results" / "venue_frame.csv").read_bytes())}
    write_json(ROOT / "results" / "flow_counts.json", flow)
    print(json.dumps({k: v for k, v in flow.items() if not k.endswith('sha256')}, indent=2))
