"""Prospective comparison of compact, topic-independent search routes.

Keeps search membership separate from design eligibility and the frozen ranking.
Licensed abstracts and raw responses stay in private/. No automatic gold labels.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
import html
import json
import re

from common import ROOT, digest, now, read_csv, write_csv, write_json
from run import parse_entry
import query
import query_revision
import participant_guards
import scopus

VERSION = "design_audit_2026_09_10"
PRIVATE = ROOT / "private" / VERSION
RESULTS = ROOT / "results" / VERSION
QUERIES = ROOT / "queries" / VERSION
LABELS = ["survey experiment*", "survey based experiment*", "survey embedded experiment*",
          "experimental survey*", "vignette experiment*", "experimental vignette*",
          "vignette based experiment*", "vignette based survey*", "factorial survey*",
          "randomized vignette*", "randomised vignette*", "question wording experiment*",
          "experiment* embedded in a survey", "experiment* embedded in an online survey",
          "experiment* within a survey", "experiment* within an online survey",
          "experiment* in a survey", "experiment* in an online survey"]
DESIGN = "experiment* OR random* OR manipulat*"
STIMULUS = "information OR message* OR text* OR vignette* OR scenario* OR headline* OR prompt*"
OUTCOME = "attitud* OR belief* OR opinion* OR perception* OR judgment* OR judgement* OR intention* OR preference*"
ACTION = "read* OR view* OR expos* OR present* OR receiv* OR shown"
HUMAN = "participant* OR respondent* OR survey* OR questionnaire*"


def field(text):
    return "TITLE-ABS-KEY(" + text + ")"


def routes():
    return {
        "labels": field(" OR ".join('"' + p + '"' for p in LABELS)),
        "concepts": " AND ".join(map(field, (DESIGN, STIMULUS, OUTCOME))),
        "exposure": " AND ".join([field(DESIGN), field("(" + ACTION + ") W/5 (" + STIMULUS + ")"), field(OUTCOME)]),
        "exposure_human": " AND ".join([field(DESIGN), field("(" + ACTION + ") W/5 (" + STIMULUS + ")"), field(OUTCOME), field(HUMAN)]),
    }


def full_query(variant):
    return "(\n  " + routes()["labels"] + "\n  OR (" + routes()[variant] + ")\n)\nAND " + query.LIMITS


def freeze():
    protocol = {
        "version": VERSION, "frozen_at": now(), "query_sha256": {v: digest(full_query(v)) for v in ("concepts", "exposure", "exposure_human")},
        "frame_sha256": digest((ROOT / "results/venue_frame.csv").read_bytes()),
        "comparison": "Named designs OR experimental manipulation + communicated stimulus + judgment/attitude outcome; exposure variants additionally require an exposure verb within five words of the stimulus, with or without a human-population gate.",
        "development": "User-nominated authors and papers, inherited machine-labelled corpora, deterministic stratified development sample. None is a recall benchmark.",
        "validation": "Select an unchanged variant after development; then draw a disjoint deterministic probability sample from its in-frame union. AI labels remain provisional; independent human adjudication needed before publication precision claims.",
        "scope": "At least one original empirical experiment varying communicated survey content and measuring individual responses. Mixed-study articles may qualify. Separate design relevance, self-administered format, text treatment, parser compatibility, new data, geography, and possession of data. Abstract silence is unclear, not no.",
        "no_author_or_topic_terms": True, "no_explicit_design_exclusions": True,
        "guard_policy": "Literal label punctuation checked within fields; context guards belong to the article. Eligibility must be screened separately. Local proximity is diagnostic, not a Scopus emulator.",
    }
    path = RESULTS / "protocol.json"
    if path.exists():
        saved = json.loads(path.read_text())
        if saved["query_sha256"] != protocol["query_sha256"] or saved["frame_sha256"] != protocol["frame_sha256"]:
            raise ValueError("Frozen queries or journal frame changed; create a new version")
    # Validate every existing artifact before writing any file.
    for v in ("concepts", "exposure", "exposure_human"):
        p = QUERIES / (v + ".txt")
        if p.exists() and p.read_text() != full_query(v) + "\n":
            raise ValueError("Frozen query artifact differs from its definition")
    QUERIES.mkdir(parents=True, exist_ok=True)
    for v in ("concepts", "exposure", "exposure_human"):
        p = QUERIES / (v + ".txt")
        if not p.exists():
            p.write_text(full_query(v) + "\n")
    if not path.exists():
        write_json(path, protocol)


def frame_ids():
    return {r["source_id"] for r in read_csv(ROOT / "results/venue_frame.csv")}


def fetch(q, view="STANDARD"):
    path = PRIVATE / "searches" / (digest(json.dumps({"query": q, "view": view}, sort_keys=True)) + ".json")
    if path.exists():
        saved = json.loads(path.read_text())
    else:
        entries, manifest = scopus.search(q, view=view, namespace=VERSION)
        saved = {"view": view, "manifest": manifest, "entries": entries}
        write_json(path, saved)
    if not saved["manifest"]["complete"] or saved["manifest"]["query"] != q:
        raise ValueError("Incomplete or mismatched snapshot")
    return saved


def jobs():
    # Disjoint source-ID batches make the broad sensitivity tractable and exact.
    sources = sorted(frame_ids(), key=int)
    result = []
    for i in range(0, len(sources), 45):
        frame = "(" + " OR ".join("SOURCE-ID(" + s + ")" for s in sources[i:i+45]) + ")"
        result.append(("concepts", "(" + routes()["concepts"] + ") AND " + query.LIMITS + " AND " + frame))
    for name in ("labels", "exposure", "exposure_human"):
        result.append((name, "(" + routes()[name] + ") AND " + query.LIMITS))
    return result


def retrieve(workers=4):
    freeze()
    planned = jobs()
    write_csv(QUERIES / "executed_parts.csv", [{"route": name, "query": q} for name, q in planned])
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch, q): name for name, q in planned}
        for i, fut in enumerate(as_completed(futures), 1):
            saved = fut.result()
            print(f"{i}/{len(futures)} {futures[fut]}: {saved['manifest']['retrieved']}", flush=True)
    summarize()


def memberships():
    members = {k: {} for k in routes()}
    frame = frame_ids()
    manifests = []
    for name, q in jobs():
        saved = fetch(q)
        manifests.append({"route": name, **saved["manifest"]})
        for e in saved["entries"]:
            if e.get("source-id", "") in frame:
                sid = e["dc:identifier"].replace("SCOPUS_ID:", "")
                members[name][sid] = e
    write_json(RESULTS / "retrieval_manifests.json", manifests)
    return members


def normalize_doi(value):
    return re.sub(r"^https?://(?:dx\.)?doi\.org/", "", (value or "").strip().lower())


def identity(e):
    doi = normalize_doi(e.get("prism:doi", ""))
    return "doi:" + doi if doi else e["dc:identifier"]


def canonicalize_snapshots(snapshots):
    """Reconcile DOI availability per SID before comparing article identities.

    A DOI gained between snapshots does not imply an added and removed paper.
    Conflicting nonempty DOIs require investigation, never an arbitrary choice.
    """
    values = defaultdict(set)
    for entries in snapshots.values():
        for sid, entry in entries.items():
            doi = normalize_doi(entry.get("prism:doi", ""))
            if doi:
                values[sid].add(doi)
    conflicts = [{"scopus_id": sid, "normalized_dois": "|".join(sorted(dois))}
                 for sid, dois in sorted(values.items()) if len(dois) > 1]
    canonical = {}
    for name, entries in snapshots.items():
        canonical[name] = {}
        for sid, entry in entries.items():
            copy = dict(entry)
            if len(values[sid]) == 1:
                copy["prism:doi"] = next(iter(values[sid]))
            canonical[name][sid] = copy
    return canonical, conflicts


def summarize():
    members = memberships()
    frame = frame_ids()
    old = {sid: e for sid, e in participant_guards.collect().items() if e.get("source-id", "") in frame}
    canonical, conflicts = canonicalize_snapshots({"previous": old, **members})
    write_csv(RESULTS / "doi_identity_conflicts.csv", conflicts, ["scopus_id", "normalized_dois"])
    if conflicts:
        raise ValueError("Conflicting DOIs across snapshots; see doi_identity_conflicts.csv")
    old = canonical.pop("previous")
    members = canonical
    old_keys = {identity(e) for e in old.values()}
    rows = []
    for variant in ("concepts", "exposure", "exposure_human"):
        union = {**members["labels"], **members[variant]}
        keys = {identity(e) for e in union.values()}
        rows.append({"variant": variant, "in_frame_records": len(union), "unique_articles": len(keys), "added_vs_revised": len(keys-old_keys), "lost_vs_revised": len(old_keys-keys), "shared_vs_revised": len(keys & old_keys), "status": "retrieval only; not screened eligibility"})
    write_csv(RESULTS / "retrieval_comparison.csv", rows)
    all_entries = {**old}
    for entries in members.values():
        all_entries.update(entries)
    by_key = {}
    for sid, e in sorted(all_entries.items(), key=lambda x: int(x[0])):
        by_key.setdefault(identity(e), []).append(sid)
    metadata = []
    for key, ids in sorted(by_key.items()):
        sid = ids[0]
        r, _ = parse_entry(all_entries[sid])
        public = {k: r[k] for k in ("scopus_id", "doi", "year", "source_id", "journal", "title")}
        public.update(identity=key, all_scopus_ids="|".join(ids), previous_revised=str(any(s in old for s in ids)).lower())
        for name, entries in members.items():
            public[name] = str(any(s in entries for s in ids)).lower()
        metadata.append(public)
    write_csv(RESULTS / "membership.csv", metadata)
    print(json.dumps(rows), flush=True)
    return metadata


def local_label(row):
    # Loose database phrases normalize punctuation; check an intact label here.
    # Spaces and hyphens within labels are accepted; commas/periods are not.
    for field_name in ("title", "abstract", "keywords", "indexed_keywords"):
        text = query.normalize(row.get(field_name, "") or "")
        for phrase in LABELS:
            rx = r"(?<!\w)" + re.escape(phrase).replace(r"\*", r"\w*").replace("\\ ", r"[\s-]+") + r"(?!\w)"
            if re.search(rx, text):
                return True
    return False


def corpus():
    result = {r["scopus_id"]: r for r in read_csv(ROOT / "private/articles.csv")}
    for folder in (ROOT / "private/query_revision_2026_09_10/searches", ROOT / "private/participant_guards_2026_09_10/searches", PRIVATE / "searches"):
        for path in folder.glob("*.json"):
            saved = json.loads(path.read_text())
            if saved.get("view") == "COMPLETE":
                for e in saved["entries"]:
                    r, _ = parse_entry(e)
                    result[r["scopus_id"]] = r
    for path in PRIVATE.glob("*_bibliography.json"):
        for e in json.loads(path.read_text())["entries"]:
            r, _ = parse_entry(e)
            result[r["scopus_id"]] = r
    return result


def title_hash(title):
    normalized = query.normalize(html.unescape(re.sub(r"<[^>]*>", " ", title or "")))
    normalized = " ".join(re.findall(r"\w+", normalized))
    return digest(normalized) if normalized else ""


def development_exclusions(members, available):
    """Archive already exposed development material once, then use that ledger.

    Public fields contain identifiers and a title hash, never source abstracts or
    inherited labels. Reuse does not depend on the adjacent private legacy repo.
    """
    path = RESULTS / "development_exclusions.csv"
    manifest_path = RESULTS / "development_exclusions_manifest.json"
    if path.exists():
        if not manifest_path.exists():
            raise ValueError("Exclusion ledger has no provenance manifest")
        manifest = json.loads(manifest_path.read_text())
        if manifest["ledger_sha256"] != digest(path.read_bytes()):
            raise ValueError("Frozen development exclusion ledger changed")
        return read_csv(path)
    if manifest_path.exists():
        raise ValueError("Exclusion manifest exists but its ledger is missing")
    doi_by_sid = {sid: normalize_doi(r.get("doi", "")) for sid, r in available.items()}
    for row in members:
        if normalize_doi(row.get("doi", "")):
            for sid in row["all_scopus_ids"].split("|"):
                doi_by_sid[sid] = normalize_doi(row["doi"])
    sources = [
        ("inherited_investigator_development", ROOT.parent / "Opencall/QueryV2/positives/mining_input.csv"),
        ("inherited_term_development", ROOT.parent / "Opencall/QueryV2/termeval/term_samples.csv"),
        ("focal_author_bibliographies", PRIVATE / "author_articles.csv"),
        ("user_nominated_challenge_cases", RESULTS / "counterexample_source_audit.csv"),
    ]
    rows, provenance = {}, []
    for reason, source in sources:
        if not source.exists():
            raise ValueError("Cannot bootstrap development exclusions; missing " + str(source))
        provenance.append({"reason": reason, "source": str(source.relative_to(ROOT.parent)),
                           "sha256": digest(source.read_bytes())})
        for r in read_csv(source):
            sid = r.get("scopus_id", "")
            doi = normalize_doi(r.get("doi", "")) or doi_by_sid.get(sid, "")
            thash = title_hash(r.get("title", ""))
            if not any((sid, doi, thash)):
                raise ValueError("Development record has no usable identity")
            key = (sid, doi, thash)
            rows.setdefault(key, set()).add(reason)
    ledger = [{"scopus_id": sid, "doi": doi, "normalized_title_sha256": thash,
               "reasons": "|".join(sorted(reasons))}
              for (sid, doi, thash), reasons in sorted(rows.items())]
    write_csv(path, ledger, ["scopus_id", "doi", "normalized_title_sha256", "reasons"])
    write_json(manifest_path, {"created_at": now(), "n_rows": len(ledger),
        "ledger_sha256": digest(path.read_bytes()), "sources": provenance,
        "identity_policy": "Exclude matches on any Scopus ID, normalized DOI, or normalized title hash; title fallback is deliberately conservative."})
    return ledger


def exclusion_indexes(ledger):
    used_ids = {r["scopus_id"] for r in ledger if r.get("scopus_id")}
    used_dois = {normalize_doi(r["doi"]) for r in ledger if r.get("doi")}
    used_titles = {r["normalized_title_sha256"] for r in ledger if r.get("normalized_title_sha256")}
    return used_ids, used_dois, used_titles


def excluded_by_indexes(row, indexes):
    """Return whether any article alias was exposed during development."""
    used_ids, used_dois, used_titles = indexes
    return bool(set(row["all_scopus_ids"].split("|")) & used_ids or
                normalize_doi(row.get("doi", "")) in used_dois or
                title_hash(row.get("title", "")) in used_titles)


def freeze_selection(path, selected, settings):
    """Protect the selected variant, sample frame, strata and complete sample."""
    # CSV round trips stringify integers; compare a canonical string projection.
    canonical = [{k: str(v) for k, v in r.items()} for r in selected]
    manifest_path = path.with_name(path.stem + "_manifest.json")
    manifest = {**settings, "sample_sha256": digest(json.dumps(canonical, sort_keys=True)),
                "n_selected": len(canonical)}
    if manifest_path.exists():
        if json.loads(manifest_path.read_text()) != manifest:
            raise ValueError("Frozen sample settings or selection changed; do not redraw after labels")
    elif path.exists():
        raise ValueError("Existing sample has no frozen selection manifest")
    if path.exists():
        if read_csv(path) != canonical:
            raise ValueError("Frozen sample rows or strata changed")
    if not manifest_path.exists():
        write_json(manifest_path, manifest)
    if not path.exists():
        write_csv(path, canonical)


def sample(stage="development", n=40, variant="exposure"):
    if stage not in {"development", "validation"} or variant not in {"concepts", "exposure", "exposure_human"} or n <= 0:
        raise ValueError("Invalid stage, variant or sample size")
    freeze()
    members = read_csv(RESULTS / "membership.csv")
    available = corpus()
    ledger = development_exclusions(members, available)
    exclusion_hashes = {"development_ledger": digest((RESULTS / "development_exclusions.csv").read_bytes())}
    if stage == "validation":
        prior_path = RESULTS / "development_sample.csv"
        prior_manifest = prior_path.with_name("development_sample_manifest.json")
        prior = read_csv(prior_path)
        if not prior_manifest.exists():
            raise ValueError("Development sample lacks its frozen manifest")
        if json.loads(prior_manifest.read_text())["sample_sha256"] != digest(json.dumps(prior, sort_keys=True)):
            raise ValueError("Development sample changed before validation")
        exclusion_hashes["fresh_development_sample"] = digest(prior_path.read_bytes())
        ledger += [{"scopus_id": sid, "doi": r["doi"], "normalized_title_sha256": title_hash(r["title"])}
                   for r in prior for sid in r["all_scopus_ids"].split("|")]
    # Build identity sets once rather than rescanning the ledger per candidate.
    excluded = exclusion_indexes(ledger)
    pools = {}
    for r in members:
        if excluded_by_indexes(r, excluded):
            continue
        if stage == "validation":
            if r["labels"] == "true" or r[variant] == "true":
                key = "validation_union"
            else:
                continue
        elif r["labels"] == "true":
            key = "named_design"
        elif r["exposure"] == "true":
            key = "exposure_beyond_labels"
        elif r["concepts"] == "true":
            key = "concepts_beyond_exposure"
        elif r["previous_revised"] == "true":
            key = "previous_only"
        else:
            raise ValueError("Unclassified record")
        pools.setdefault(key, []).append(r)
    selected = []
    for key, rows in sorted(pools.items()):
        rows.sort(key=lambda r: digest(VERSION + ":" + stage + ":" + r["identity"]))
        for r in rows[:n]:
            selected.append({**r, "stage": stage, "stratum": key, "stratum_N": len(rows), "stratum_n": min(n,len(rows)), "selection_hash": digest(VERSION + ":" + stage + ":" + r["identity"])})
    path = RESULTS / (stage + "_sample.csv")
    freeze_selection(path, selected, {"stage": stage, "selected_variant": variant if stage == "validation" else "all_disjoint_routes",
        "query_sha256": digest(full_query(variant)) if stage == "validation" else {v: digest(full_query(v)) for v in ("concepts", "exposure", "exposure_human")},
        "requested_n_per_stratum": n, "membership_sha256": digest((RESULTS / "membership.csv").read_bytes()),
        "frame_sha256": digest((ROOT / "results/venue_frame.csv").read_bytes()),
        "exclusion_sha256": exclusion_hashes,
        "selection_seed": VERSION + ":" + stage,
        "estimand": "Query-selected articles outside all archived development material" if stage == "validation" else "Disjoint development strata outside previously exposed material"})
    missing = [r["scopus_id"] for r in selected if r["scopus_id"] not in available]
    def batch(ids):
        saved = fetch("(" + " OR ".join("EID(2-s2.0-" + s + ")" for s in ids) + ")", "COMPLETE")
        if {e["dc:identifier"].replace("SCOPUS_ID:", "") for e in saved["entries"]} != set(ids):
            raise ValueError("Incomplete sample metadata")
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(batch, [missing[i:i+25] for i in range(0,len(missing),25)]))
    available = corpus()
    # Omit author names and route membership from coding packets.
    packet = [{k: available[r["scopus_id"]].get(k, "") for k in ("scopus_id", "doi", "year", "journal", "title", "abstract", "keywords")} for r in selected]
    packet.sort(key=lambda r: digest("blind-order:" + r["scopus_id"]))
    write_json(PRIVATE / (stage + "_packet.json"), packet)
    write_csv(PRIVATE / (stage + "_packet.csv"), packet)
    print(f"{stage}: {len(packet)} records; strata " + str({k: len(v) for k,v in pools.items()}))


def author_omission_reason(article, old_ids, frame, first_last, credited_ids, credited_dois):
    sid = article["scopus_id"]
    if sid in credited_ids or (normalize_doi(article.get("doi", "")) in credited_dois):
        return "included; first/last credit"
    if article["doctype"] != "ar":
        kind = "Review" if article["doctype"] == "re" else article["doctype"]
        return "Scopus " + kind + " classification; DOCTYPE(ar) filters out"
    if article["source_id"] not in frame:
        return "outside journal frame"
    if sid not in old_ids:
        return "query vocabulary miss"
    if not query.match(article):
        return "retrieved; local phrase/context check rejects the record"
    if not first_last:
        return "retrieved; middle author receives no credit"
    if article.get("byline_complete") != "true":
        return "retrieved; incomplete byline prevents credit"
    return "retrieved and locally verified; absent from frozen credited article set"


def author_audit():
    source_audit = read_csv(RESULTS / "counterexample_source_audit.csv")
    frame = frame_ids()
    bibliography = []
    for name, aid in (("pennycook", "50061672800"), ("richeson", "7003917566")):
        path = PRIVATE / (name + "_bibliography.json")
        if not path.exists():
            entries, manifest = scopus.search("AU-ID("+aid+") AND "+query.LIMITS, namespace=VERSION)
            write_json(path, {"entries": entries, "manifest": manifest})
        saved = json.loads(path.read_text())
        for e in saved["entries"]:
            r, _ = parse_entry(e)
            r.update(focal=name, authid=aid, doctype=e.get("subtype", ""),
                     in_frame=str(r["source_id"] in frame).lower(),
                     first_last=str(aid in (r["first_authid"], r["last_authid"])).lower())
            bibliography.append(r)
    write_csv(PRIVATE / "author_articles.csv", bibliography)
    bydoi = {normalize_doi(r["doi"]): r for r in bibliography if r["doi"]}
    for r in source_audit:
        if normalize_doi(r["doi"]) not in bydoi:
            saved = fetch("DOI("+r["doi"]+")", "COMPLETE")
            for e in saved["entries"]:
                a, _ = parse_entry(e)
                a["doctype"] = e.get("subtype", "")
                bydoi[normalize_doi(a["doi"])] = a
    old_rows = read_csv(ROOT / "private/articles.csv")
    old = {r["scopus_id"] for r in old_rows}
    latest = participant_guards.collect()
    current_rank = {r["authid"]: r for r in read_csv(ROOT / "results/ranking_provisional.csv")}
    membership_path = RESULTS / "membership.csv"
    members = {normalize_doi(r["doi"]): r for r in read_csv(membership_path) if r["doi"]} if membership_path.exists() else {}
    focal_ids = {"Gordon Pennycook": "50061672800", "Jennifer A. Richeson": "7003917566"}
    rows = []
    for r in source_audit:
        a = bydoi.get(normalize_doi(r["doi"]))
        row = {k: r[k] for k in ("focal_researcher", "year", "title", "doi", "first_last_credit", "design_judgment", "primary_source_url")}
        if a:
            row.update(scopus_id=a["scopus_id"], journal=a["journal"], doctype=a["doctype"],
                in_frame=str(a["source_id"] in frame).lower(), old_retrieved=str(a["scopus_id"] in old).lower(),
                latest_revised_retrieved=str(a["scopus_id"] in latest).lower(),
                old_local_verified=str(bool(query.match(a))).lower(),
                latest_local_verified=str(bool(query.match(a, participant_guards.revised_families()))).lower())
            m = members.get(normalize_doi(r["doi"]), {})
            for v in ("concepts", "exposure", "exposure_human"):
                row[v + "_retrieved"] = str(m.get("labels") == "true" or m.get(v) == "true").lower() if members else "pending"
            aid = focal_ids[r["focal_researcher"]]
            credited_ids = set(current_rank.get(aid, {}).get("article_ids", "").split("|")) - {""}
            credited_dois = {normalize_doi(v["doi"]) for v in old_rows if v["scopus_id"] in credited_ids and v["doi"]}
            row["primary_omission_reason"] = author_omission_reason(a, old, frame,
                r["first_last_credit"] == "true", credited_ids, credited_dois)
        else:
            row["primary_omission_reason"] = "DOI not found in Scopus"
        rows.append(row)
    write_csv(RESULTS / "counterexample_retrieval_audit.csv", rows)
    summary = []
    for name, aid in (("pennycook", "50061672800"), ("richeson", "7003917566")):
        bib = [r for r in bibliography if r["focal"] == name]
        rank = current_rank.get(aid, {})
        entry = {"researcher": name, "authid": aid, "bibliography_articles_2010_2026": len(bib),
                 "in_frame_bibliography_articles": sum(r["in_frame"] == "true" for r in bib),
                 "old_retrieved_any_position": sum(r["scopus_id"] in old for r in bib),
                 "old_credited_articles": int(rank.get("n_articles", 0)), "old_competition_rank": rank.get("score_rank", ""),
                 "old_display_position": rank.get("position", "")}
        for v in ("concepts", "exposure", "exposure_human"):
            matched = [r for r in bib if (members.get(normalize_doi(r["doi"]), {}).get("labels") == "true" or members.get(normalize_doi(r["doi"]), {}).get(v) == "true")]
            entry[v + "_any_position"] = len(matched)
            entry[v + "_first_last_candidates"] = sum(r["first_last"] == "true" for r in matched)
        summary.append(entry)
    write_csv(RESULTS / "author_retrieval_summary.csv", summary)
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["freeze", "retrieve", "summarize", "author_audit", "development", "validation"])
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--variant", choices=["concepts", "exposure", "exposure_human"], default="exposure")
    args = ap.parse_args()
    if args.command in {"development", "validation"}:
        sample(args.command, args.n, args.variant)
    else:
        globals()[args.command]()
