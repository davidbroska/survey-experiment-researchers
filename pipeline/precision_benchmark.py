"""Acquire full texts for a fixed probability sample without changing its members.

Existing geography labels are never imported as design judgments. All PDFs,
extracted text and verbatim review evidence stay private. Acquisition establishes
availability and bibliographic identity, not study eligibility or data ownership.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
import json
import re
import threading
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import Request, urlopen

from common import ROOT, digest, now, read_csv, write_csv, write_json
from fulltext import extract, file_id
from open_access import PDFLinks, doi_key, is_supplement, normalize

VERSION = "precision_benchmark_2026_09_10"
PRIVATE, RESULTS = ROOT / "private" / VERSION, ROOT / "results" / VERSION
MAX_URLS, MAX_WORKERS, TIMEOUT = 8, 4, 20
UA = "SocialTunePrecisionBenchmark/1.0 (public scholarly full-text discovery)"
AXES = ("design", "new_data", "text_treatment", "parser_compatible", "geography", "data_possession")
GEOGRAPHIES = ["US_explicit", "US_inferred", "non_US", "mixed_includes_US", "unclear"]
PUBLIC_FIELDS = ["benchmark_id", "scopus_id", "doi", "title", "year", "journal", "article_url",
                 "availability_status", "identity_status", "document_kind", "fulltext_readiness",
                 "n_documents", "n_pages", "pdf_sha256", "text_sha256", "source_url",
                 "source_type", "copy_version_note", "evaluation_status", "manual_action", "suggested_filename"]


def identity(pages, article):
    """Automated identity evidence, independent of document completeness."""
    opening = normalize(" ".join(pages[:3]))
    title = normalize(article.get("title", ""))
    if len(title) >= 20 and title in opening:
        return "verified_title_in_opening_pages"
    words = {normalize(w) for w in re.findall(r"\w{4,}", article.get("title", ""))}
    coverage = sum(w in opening for w in words) / len(words) if words else 0
    doi = doi_key(article.get("doi", ""))
    if doi and normalize(doi) in opening and coverage >= .85:
        return "verified_doi_and_title_in_opening_pages"
    return "needs_identity_review"


def document_kind(filename, pages=(), source_url=""):
    if "__abstract" in filename.lower():
        return "abstract_only"
    if "__supplement" in filename.lower() or is_supplement(source_url, pages):
        return "supplement"
    return "article_or_manuscript"


def readiness(record):
    if not record["identity_status"].startswith("verified_"):
        return "needs_identity_review"
    if record["document_kind"] != "article_or_manuscript":
        return "needs_main_article"
    if not record["text_characters"]:
        return "needs_ocr_or_manual_reading"
    if record["n_pages"] < 3 or record["text_characters"] < 1500:
        return "needs_completeness_review"
    return "ready_for_fulltext_review"


def catalog():
    lookup = {}
    for name in ["results/article_metadata.csv", "results/design_audit_2026_09_10/membership.csv",
                 "results/search_strategy_2026_09_10/membership.csv", f"private/{VERSION}/fixed_sample.csv"]:
        path = ROOT / name
        if not path.exists():
            continue
        for row in read_csv(path):
            for sid in set((row.get("all_scopus_ids") or row["scopus_id"]).split("|")) | {row["scopus_id"]}:
                lookup[sid] = row
    return lookup


def text_for(path):
    sha = digest(path.read_bytes())
    cache = PRIVATE / "texts" / (sha + ".json")
    if cache.exists():
        saved = json.loads(cache.read_text())
        if saved["source_sha256"] != sha:
            raise ValueError("Text cache does not match source PDF")
    else:
        legacy = ROOT / "private/fulltext/texts" / (path.name + ".json")
        saved = json.loads(legacy.read_text()) if legacy.exists() else {}
        if saved.get("source_sha256") != sha:
            try:
                pages, extractor = extract(path)
                saved = {"source_sha256": sha, "pages": pages, "extractor": extractor}
            except Exception as error:
                saved = {"source_sha256": sha, "pages": [], "extractor": "unavailable",
                         "extraction_error": type(error).__name__}
        saved = {**saved, "source_pdf": str(path.relative_to(ROOT))}
        write_json(cache, saved)
    return saved, str(cache.relative_to(ROOT)), digest(cache.read_bytes())


def inspect_pdf(path, article, source_url="", provenance=()):
    extracted, cache, cache_sha = text_for(path)
    pages = extracted["pages"]
    record = {"scopus_id": article.get("scopus_id", ""), "doi": doi_key(article.get("doi", "")),
              "title": article.get("title", ""), "filename": path.name,
              "pdf_path": str(path.relative_to(ROOT)), "pdf_sha256": extracted["source_sha256"],
              "text_cache": cache, "text_sha256": cache_sha, "n_pages": len(pages),
              "text_characters": sum(len(p.strip()) for p in pages),
              "identity_status": identity(pages, article),
              "document_kind": document_kind(path.name, pages, source_url), "source_url": source_url,
              "source_type": next((p.get("source_type", "") for p in reversed(list(provenance)) if p.get("source_type")), ""),
              "copy_version_note": next((p.get("version_note", "") for p in reversed(list(provenance)) if p.get("version_note")), ""),
              "identity_provenance": list(provenance),
              "completeness_status": "not_manually_assessed", "evaluation_status": "unassigned"}
    record["fulltext_readiness"] = readiness(record)
    return record


def local_inventory():
    known = catalog()
    review_path = ROOT / "inputs/fulltext_reviews.csv"
    reviews = read_csv(review_path) if review_path.exists() else []
    move_path = ROOT / "private/fulltext/move_manifest.csv"
    moves = read_csv(move_path) if move_path.exists() else []
    acquired_path = PRIVATE / "acquisition.json"
    acquired = json.loads(acquired_path.read_text()) if acquired_path.exists() else {}
    acquired_documents = {d["pdf_sha256"]: d for a in acquired.values() for d in a.get("documents", [])}
    rows = []
    for folder in [ROOT / "private/fulltext/inbox", PRIVATE / "inbox"]:
        if not folder.exists():
            continue
        for path in sorted(folder.glob("*.pdf")):
            try:
                sid = file_id(path.name)
            except ValueError:
                sid = ""
            sha = digest(path.read_bytes())
            article = known.get(sid, {"scopus_id": sid, "doi": "", "title": ""})
            provenance = []
            for review in reviews:
                if review["filename"] == path.name and review["source_sha256"] == sha:
                    provenance.append({"type": "previous_geography_review_source_hash",
                                       "scopus_id": review["scopus_id"], "sha256": sha,
                                       "labels_imported": False})
            for move in moves:
                if move["destination_filename"] == path.name and move["source_sha256"] == sha:
                    provenance.append({"type": "documented_identity_at_import",
                                       "method": move["identity_method"], "sha256": sha})
            source_url = ""
            old_oa = ROOT / "private/open_access/records" / (sid + ".json")
            if old_oa.exists():
                previous = json.loads(old_oa.read_text())
                if previous.get("source_sha256") == sha:
                    source_url = previous.get("source_url", "")
                    provenance.append({"type": "previous_public_copy_acquisition",
                                       "source_url": source_url, "sha256": sha})
            if sha in acquired_documents:
                source_url = acquired_documents[sha].get("source_url", source_url)
                provenance.extend(acquired_documents[sha].get("identity_provenance", []))
            rows.append(inspect_pdf(path, {**article, "scopus_id": sid}, source_url, provenance))
    write_json(PRIVATE / "local_inventory.json", rows)
    public = [{k: r[k] for k in ["scopus_id", "doi", "title", "identity_status", "document_kind",
               "fulltext_readiness", "n_pages", "pdf_sha256", "text_sha256", "source_url", "evaluation_status"]}
              for r in rows]
    write_csv(RESULTS / "local_inventory.csv", public)
    summary = {"n_documents": len(rows), "n_main_documents": sum(r["document_kind"] == "article_or_manuscript" for r in rows),
               "n_identity_verified": sum(r["identity_status"].startswith("verified_") for r in rows),
               "n_ready_for_fulltext_review": sum(r["fulltext_readiness"] == "ready_for_fulltext_review" for r in rows),
               "previous_design_or_geography_labels_imported": False,
               "definition": "Readiness means identity-matched, readable and apparently substantial; it does not certify completeness, eligibility or parser compatibility."}
    write_json(RESULTS / "local_inventory_summary.json", summary)
    return rows


def freeze_sample(path):
    rows = read_csv(path)
    if not rows or not {"scopus_id", "doi", "title"} <= rows[0].keys():
        raise ValueError("Sample requires scopus_id, doi (may be blank), and title")
    identities, aliases = set(), set()
    for row in rows:
        if not row["scopus_id"].isdigit() or not row["title"].strip():
            raise ValueError("Invalid Scopus ID or missing title")
        ids = set((row.get("all_scopus_ids") or row["scopus_id"]).split("|")) | {row["scopus_id"]}
        if not all(s.isdigit() for s in ids) or aliases & ids:
            raise ValueError("Invalid or duplicated article aliases")
        key = "doi:" + doi_key(row["doi"]) if row["doi"] else "scopus:" + row["scopus_id"]
        if key in identities:
            raise ValueError("Fixed sample contains duplicate article identities")
        identities.add(key)
        aliases.update(ids)
    frozen = PRIVATE / "fixed_sample.csv"
    data = path.read_bytes()
    if frozen.exists() and frozen.read_bytes() != data:
        raise ValueError("The benchmark sample is frozen; use a new version for a different sample")
    if not frozen.exists():
        frozen.parent.mkdir(parents=True, exist_ok=True)
        frozen.write_bytes(data)
    manifest = {"n_selected": len(rows), "sample_sha256": digest(data),
                "selection_precedes_access_lookup": True, "inaccessible_records_replaced": False,
                "sample_is_immutable": True, "input_columns": list(rows[0]),
                "sampling_design_source": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else path.name}
    write_json(RESULTS / "sample_manifest.json", manifest)
    return rows


def match_local(article, inventory):
    ids = set((article.get("all_scopus_ids") or article["scopus_id"]).split("|")) | {article["scopus_id"]}
    doi = doi_key(article.get("doi", ""))
    matches = []
    for record in inventory:
        if record["scopus_id"] in ids or (doi and doi == record["doi"]):
            # Recheck against the sampled metadata; do not trust a filename alone.
            matches.append(inspect_pdf(ROOT / record["pdf_path"], article,
                                       record["source_url"], record["identity_provenance"]))
    return sorted(matches, key=lambda r: (r["fulltext_readiness"] != "ready_for_fulltext_review",
                                          r["document_kind"] != "article_or_manuscript", r["pdf_path"]))


class PublicCopies:
    """Public HTTP only; isolated caches and bounded publisher/repository traversal."""
    def __init__(self):
        self.lock = threading.Lock()
        self.hosts = {}

    def fetch(self, url):
        if urlsplit(url).scheme not in {"http", "https"}:
            return {"url": url, "error": "unsupported_url", "body": b""}
        key = digest(url)
        record_path, body_path = PRIVATE / "responses" / (key + ".json"), PRIVATE / "responses" / (key + ".bin")
        if record_path.exists():
            saved = json.loads(record_path.read_text())
            return {**saved, "body": body_path.read_bytes() if body_path.exists() else b""}
        with self.lock:
            gate = self.hosts.setdefault(urlsplit(url).netloc, threading.Semaphore(2))
        with gate:
            try:
                with urlopen(Request(url, headers={"User-Agent": UA,
                            "Accept": "application/pdf,application/json,text/html;q=0.8"}), timeout=TIMEOUT) as response:
                    body = response.read(40 * 1024 * 1024 + 1)
                    if len(body) > 40 * 1024 * 1024:
                        raise ValueError("response_too_large")
                    saved = {"url": url, "final_url": response.url, "checked_at": now(),
                             "http_status": response.status, "content_type": response.headers.get("Content-Type", "")}
                    body_path.parent.mkdir(parents=True, exist_ok=True)
                    body_path.write_bytes(body)
            except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
                body = b""
                saved = {"url": url, "checked_at": now(), "error": type(error).__name__,
                         "http_status": getattr(error, "code", None)}
        write_json(record_path, saved)
        return {**saved, "body": body}

    def metadata(self, url):
        response = self.fetch(url)
        try:
            body = json.loads(response.pop("body", b""))
            return {**response, "body": body}
        except (ValueError, UnicodeDecodeError):
            return {**response, "error": response.get("error", "invalid_json")}

    def discover(self, articles):
        works, errors = {}, {}
        dois = sorted({doi_key(r["doi"]) for r in articles if r["doi"]})
        for start in range(0, len(dois), 40):
            group = dois[start:start + 40]
            url = "https://api.openalex.org/works?" + urlencode({
                "filter": "doi:" + "|".join("https://doi.org/" + d for d in group),
                "per_page": 100, "select": "id,doi,title,open_access,best_oa_location,locations"})
            result = self.metadata(url)
            if result.get("error"):
                errors.update({d: result["error"] for d in group})
            else:
                works.update({doi_key(w["doi"]): w for w in result["body"].get("results", [])
                              if w.get("doi") and doi_key(w["doi"]) in group})
        out = {}
        sources_path = ROOT / "inputs/open_access_sources.csv"
        sources = read_csv(sources_path) if sources_path.exists() else []
        benchmark_sources_path = ROOT / "inputs/precision_benchmark_sources.csv"
        benchmark_sources = read_csv(benchmark_sources_path) if benchmark_sources_path.exists() else []
        if benchmark_sources and not {"scopus_id", "url", "source_type", "note"} <= benchmark_sources[0].keys():
            raise ValueError("Benchmark sources require scopus_id,url,source_type,note")
        for article in articles:
            doi = doi_key(article["doi"])
            work = works.get(doi)
            if not work and doi not in errors:
                result = self.metadata("https://api.openalex.org/works?" + urlencode({
                    "search": article["title"], "per_page": 5,
                    "select": "id,doi,title,open_access,best_oa_location,locations"}))
                matches = [w for w in result.get("body", {}).get("results", [])
                           if normalize(w.get("title", "")) == normalize(article["title"])
                           and (not doi or not w.get("doi") or doi_key(w["doi"]) == doi)]
                if len(matches) == 1:
                    work = matches[0]
            work = work or {}
            locations = [v for v in [work.get("best_oa_location"), *work.get("locations", [])]
                         if v and v.get("is_oa")]
            ids = set((article.get("all_scopus_ids") or article["scopus_id"]).split("|")) | {article["scopus_id"]}
            locations += [{"pdf_url": r["url"], "is_oa": True} for r in sources if r["scopus_id"] in ids]
            curated = [r for r in benchmark_sources if r["scopus_id"] in ids]
            # Targeted primary-source links precede old failing locations on a new pass.
            urls = list(dict.fromkeys([r["url"] for r in curated] + [location[k] for location in locations
                         for k in ("pdf_url", "landing_page_url") if location.get(k)]))
            out[article["scopus_id"]] = {"openalex_id": work.get("id", ""), "urls": urls,
                                        "lookup_error": errors.get(doi, ""), "work": work,
                                        "curated_sources": curated}
        preserve_previous(PRIVATE / "discovery.json")
        write_json(PRIVATE / "discovery.json", out)
        return out

    def acquire(self, article, discovery):
        pending, seen, attempts, documents = list(discovery["urls"]), set(), [], []
        while pending and len(seen) < MAX_URLS:
            pending.sort(key=is_supplement)
            url = pending.pop(0)
            if url in seen:
                continue
            seen.add(url)
            response = self.fetch(url)
            data = response.pop("body", b"")
            attempt = {**response, "n_bytes": len(data)}
            if data.lstrip().startswith(b"%PDF-"):
                sha = digest(data)
                candidate = PRIVATE / "candidates" / (article["scopus_id"] + "_" + sha[:12] + ".pdf")
                candidate.parent.mkdir(parents=True, exist_ok=True)
                if not candidate.exists():
                    candidate.write_bytes(data)
                record = inspect_pdf(candidate, article, response.get("final_url", url))
                attempt.update(identity_status=record["identity_status"], fulltext_readiness=record["fulltext_readiness"])
                if record["identity_status"].startswith("verified_"):
                    suffix = "__supplement_" if record["document_kind"] == "supplement" else "__copy_"
                    dest = PRIVATE / "inbox" / (article["scopus_id"] + suffix + sha[:12] + ".pdf")
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if not dest.exists():
                        with dest.open("xb") as handle:
                            handle.write(data)
                    record = inspect_pdf(dest, article, response.get("final_url", url),
                                         [{"type": "public_oa_acquisition", "source_url": url, "sha256": sha,
                                           "source_type": next((r["source_type"] for r in discovery.get("curated_sources", []) if r["url"] == url), "OpenAlex_open_location"),
                                           "version_note": next((r["note"] for r in discovery.get("curated_sources", []) if r["url"] == url), "")}])
                    documents.append(record)
                    attempts.append(attempt)
                    if record["fulltext_readiness"] == "ready_for_fulltext_review":
                        break
                    continue
            elif data and ("html" in response.get("content_type", "") or b"<html" in data[:1000].lower()):
                parser = PDFLinks()
                parser.feed(data.decode("utf-8", errors="replace"))
                for link in parser.links[:10]:
                    absolute = urljoin(response.get("final_url", url), link)
                    if absolute not in pending and absolute not in seen:
                        pending.append(absolute)
            attempts.append(attempt)
        attempt_path = PRIVATE / "attempts" / (article["scopus_id"] + ".json")
        previous_attempts = json.loads(attempt_path.read_text()) if attempt_path.exists() else []
        keys = {json.dumps(a, sort_keys=True) for a in previous_attempts}
        previous_attempts += [a for a in attempts if json.dumps(a, sort_keys=True) not in keys]
        write_json(attempt_path, previous_attempts)
        return {"documents": documents, "attempts": previous_attempts,
                "n_urls_this_pass": len(seen), "n_distinct_urls_all_passes": len({a["url"] for a in previous_attempts}),
                "lookup_error": discovery.get("lookup_error", ""), "open_location_found": bool(discovery["urls"])}


def preserve_previous(path):
    if path.exists():
        data = path.read_bytes()
        history = PRIVATE / "history" / (path.stem + "_" + digest(data) + path.suffix)
        history.parent.mkdir(parents=True, exist_ok=True)
        if not history.exists():
            history.write_bytes(data)


def reviewer_schema():
    return {"unit": "article; design=yes if at least one reported study qualifies",
            "axes": {a: GEOGRAPHIES if a == "geography" else ["yes", "no", "unclear"] for a in AXES},
            "evidence_fields_per_axis": ["decision", "document_sha256", "pdf_page", "evidence_quote", "rationale"],
            "pdf_page_convention": "1-based physical PDF page, not printed journal page",
            "unassigned_value": "", "optional_per_study_evidence": "studies array with study_id and the same evidence objects",
            "interpretation": {"design": "At least one human experiment varies communicated content or question presentation and measures respondents' judgments, attitudes, beliefs, intentions, preferences or comparable survey responses.",
                "new_data": "Original collection or fielding, separate from secondary analysis; do not infer from design=yes.",
                "text_treatment": "Written, reading, wording or vignette treatment; mixed modalities may include text.",
                "parser_compatible": "Assess actual questionnaire structure separately; conjoint/discrete-choice profile combinations and adaptive conversations are incompatible.",
                "geography": "Respondent location for eligible studies, distinguishing explicit US evidence, contextual inference, non-US and mixed samples.",
                "data_possession": "Evidence that relevant raw respondent data and materials are available to the researchers; authorship alone does not establish possession."},
            "decision_rule": "Do not require every axis to be yes to classify design=yes. Unknown eligibility stays unclear. No original review labels are prefilled.",
            "blinding": "Packets omit query routes, sampling strata, author metadata and prior annotations. Authors remain visible within original PDFs/text; author blinding is not claimed.",
            "provenance_fields": ["reviewer", "reviewer_type", "review_date", "human_validated"],
            "validation": "For each non-unclear decision cite the source PDF hash, an existing page and a short exact evidence span; unclear decisions require an explanatory rationale. AI-assisted judgments cannot be human_validated=true."}


def prepare(sample_path, acquire=False, workers=MAX_WORKERS):
    articles = freeze_sample(sample_path.resolve())
    inventory = local_inventory()
    matched = {r["scopus_id"]: match_local(r, inventory) for r in articles}
    pending = [r for r in articles if not any(d["fulltext_readiness"] == "ready_for_fulltext_review"
                                             for d in matched[r["scopus_id"]])]
    acquisition = {}
    acquisition_path = PRIVATE / "acquisition.json"
    if acquisition_path.exists():
        acquisition = json.loads(acquisition_path.read_text())
    if acquire and pending:
        preserve_previous(acquisition_path)
        client = PublicCopies()
        discoveries = client.discover(pending)
        with ThreadPoolExecutor(max_workers=min(workers, MAX_WORKERS)) as pool:
            futures = {pool.submit(client.acquire, a, discoveries[a["scopus_id"]]): a for a in pending}
            for i, future in enumerate(as_completed(futures), 1):
                article = futures[future]
                acquisition[article["scopus_id"]] = future.result()
                write_json(acquisition_path, acquisition)
                print(f"Public-copy check {i}/{len(pending)}: {article['scopus_id']}", flush=True)
                if i % 4 == 0:
                    _write_outputs(articles, matched, acquisition, verbose=False)
    return _write_outputs(articles, matched, acquisition)


def _write_outputs(articles, matched, acquisition, verbose=True):
    public, private, packet, drafts = [], [], [], []
    for article in articles:
        sid = article["scopus_id"]
        acquired = acquisition.get(sid, {})
        documents = matched[sid] + acquired.get("documents", [])
        documents = list({d["pdf_sha256"]: d for d in documents}.values())
        documents.sort(key=lambda d: (d["fulltext_readiness"] != "ready_for_fulltext_review", d["document_kind"] != "article_or_manuscript", d["pdf_path"]))
        best = documents[0] if documents else {}
        ready = any(d["fulltext_readiness"] == "ready_for_fulltext_review" for d in documents)
        bid = "PB-" + digest(VERSION + ":" + sid)[:10]
        availability = ("public_copy_downloaded" if acquired.get("documents") else
                        "local_copy_available" if matched[sid] else "manual_copy_needed")
        action = "" if ready else (best.get("fulltext_readiness", "No verified main-article copy found; download the fixed sampled article without substitution."))
        row = {"benchmark_id": bid, "scopus_id": sid, "doi": article["doi"], "title": article["title"],
               "year": article.get("year", ""), "journal": article.get("journal", ""),
               "article_url": "https://doi.org/" + doi_key(article["doi"]) if article["doi"] else "https://www.scopus.com/record/display.uri?eid=2-s2.0-" + sid,
               "availability_status": availability, "identity_status": best.get("identity_status", "unverified_no_copy"),
               "document_kind": best.get("document_kind", "missing"),
               "fulltext_readiness": "ready_for_fulltext_review" if ready else best.get("fulltext_readiness", "needs_main_article"),
               "n_documents": len(documents), "n_pages": best.get("n_pages", 0),
               "pdf_sha256": best.get("pdf_sha256", ""), "text_sha256": best.get("text_sha256", ""),
               "source_url": best.get("source_url", ""), "evaluation_status": "unassigned",
               "source_type": best.get("source_type", ""), "copy_version_note": best.get("copy_version_note", ""),
               "manual_action": action, "suggested_filename": sid + ".pdf"}
        public.append(row)
        private.append({**row, "documents": documents, "sample_metadata": article,
                        "acquisition": acquired, "fixed_sample_sha256": digest((PRIVATE / "fixed_sample.csv").read_bytes())})
        verified = [d for d in documents if d["identity_status"].startswith("verified_")]
        packet.append({"benchmark_id": bid, "readiness": row["fulltext_readiness"], "evaluation_status": "unassigned",
                       "documents": [{"document_sha256": d["pdf_sha256"], "document_kind": d["document_kind"],
                                      "n_pages": d["n_pages"], "text_sha256": d["text_sha256"],
                                      "pages": [{"pdf_page": i, "text": page} for i, page in enumerate(json.loads((ROOT / d["text_cache"]).read_text())["pages"], 1)]}
                                     for d in verified]})
        drafts.append({"benchmark_id": bid, "evaluation_status": "unassigned",
                       **{axis: {"decision": "", "document_sha256": "", "pdf_page": "", "evidence_quote": "", "rationale": ""} for axis in AXES},
                       "studies": [], "reviewer": "", "reviewer_type": "", "review_date": "", "human_validated": False})
    write_csv(RESULTS / "availability_manifest.csv", public, PUBLIC_FIELDS)
    write_csv(RESULTS / "manual_download_queue.csv", [r for r in public if r["fulltext_readiness"] != "ready_for_fulltext_review"], PUBLIC_FIELDS)
    write_json(PRIVATE / "availability_manifest.json", private)
    write_json(PRIVATE / "reviewer_packet.json", sorted(packet, key=lambda r: r["benchmark_id"]))
    # Draft templates are separate from completed annotations and are never populated from old reviews.
    write_json(PRIVATE / "review_template.json", sorted(drafts, key=lambda r: r["benchmark_id"]))
    write_json(RESULTS / "review_schema.json", reviewer_schema())
    summary = {"sample_n": len(articles), "ready_for_fulltext_review": sum(r["fulltext_readiness"] == "ready_for_fulltext_review" for r in public),
               "manual_action_needed": sum(r["fulltext_readiness"] != "ready_for_fulltext_review" for r in public),
               "evaluations_completed": 0, "evaluation_status": "unassigned", "inaccessible_records_replaced": False,
               "sample_sha256": digest((PRIVATE / "fixed_sample.csv").read_bytes()),
               "review_packet_sha256": digest((PRIVATE / "reviewer_packet.json").read_bytes()),
               "public_copies_attempted": len(acquisition), "max_urls_per_article": MAX_URLS,
               "url_budget_scope": "At most eight candidate URLs per article per acquisition pass; all distinct past attempts remain archived.",
               "workers_limit": MAX_WORKERS, "http_timeout_seconds": TIMEOUT,
               "blinding": reviewer_schema()["blinding"],
               "precision_evaluation": "Pending full-text annotation; availability is not a design label. Unavailable selected records remain in the fixed denominator."}
    write_json(RESULTS / "summary.json", summary)
    if verbose:
        print(json.dumps(summary, indent=2))
    return public


def validate_reviews(review_path):
    """Validate completed article reviews without deriving eligibility from other axes.

    Verbatim matching is case-sensitive and normalizes whitespace only, allowing
    quotes to join PDF line wraps without permitting changed words or punctuation.
    A source PDF, its extracted-text cache and the packet must all agree.
    """
    reviews = json.loads(review_path.read_text())
    if not isinstance(reviews, list):
        raise ValueError("Reviews must be a list")
    packet_path = PRIVATE / "reviewer_packet.json"
    packet = {r["benchmark_id"]: r for r in json.loads(packet_path.read_text())}
    manifest = {r["benchmark_id"]: r for r in json.loads((PRIVATE / "availability_manifest.json").read_text())}
    seen, completed = set(), []
    whitespace = lambda value: " ".join(value.split())
    for review in reviews:
        bid = review.get("benchmark_id", "")
        if bid not in packet or bid in seen:
            raise ValueError("Unknown or repeated benchmark ID: " + bid)
        seen.add(bid)
        if review.get("evaluation_status") == "unassigned":
            continue
        if review.get("evaluation_status") != "completed":
            raise ValueError("Invalid evaluation status: " + bid)
        if packet[bid]["readiness"] != "ready_for_fulltext_review":
            raise ValueError("Review completed without a ready source article: " + bid)
        if not all(review.get(k) for k in ("reviewer", "reviewer_type", "review_date")):
            raise ValueError("Missing reviewer provenance: " + bid)
        date.fromisoformat(review["review_date"])
        if review.get("human_validated") not in (True, False, "true", "false"):
            raise ValueError("Missing or invalid human validation flag: " + bid)
        if review["reviewer_type"] == "AI_assisted" and review["human_validated"] not in (False, "false"):
            raise ValueError("AI-assisted review cannot claim independent human validation: " + bid)
        docs = {d["pdf_sha256"]: d for d in manifest[bid]["documents"]}
        packet_docs = {d["document_sha256"]: d for d in packet[bid]["documents"]}

        def evidence(axis, item, allow_unassigned=False):
            allowed = GEOGRAPHIES if axis == "geography" else ["yes", "no", "unclear"]
            decision = item.get("decision", "")
            if allow_unassigned and not decision:
                return
            if decision not in allowed or not item.get("rationale", "").strip():
                raise ValueError(f"Missing decision/rationale: {bid} {axis}")
            fields = [item.get("document_sha256"), item.get("pdf_page"), item.get("evidence_quote")]
            if decision == "unclear" and not any(fields):
                return
            if not all(fields):
                raise ValueError(f"Incomplete page-cited evidence: {bid} {axis}")
            sha = item["document_sha256"]
            if sha not in docs or sha not in packet_docs:
                raise ValueError(f"Unknown source document: {bid} {axis}")
            source = docs[sha]
            pdf, cache = ROOT / source["pdf_path"], ROOT / source["text_cache"]
            if not pdf.is_file() or digest(pdf.read_bytes()) != sha:
                raise ValueError(f"Missing or changed source PDF: {bid} {axis}")
            if not cache.is_file() or digest(cache.read_bytes()) != source["text_sha256"]:
                raise ValueError(f"Missing or changed text extraction: {bid} {axis}")
            saved = json.loads(cache.read_text())
            if saved["source_sha256"] != sha or packet_docs[sha]["text_sha256"] != source["text_sha256"]:
                raise ValueError(f"Source and packet hash mismatch: {bid} {axis}")
            page = int(item["pdf_page"])
            if not 1 <= page <= len(saved["pages"]):
                raise ValueError(f"Invalid PDF page: {bid} {axis}")
            text = saved["pages"][page - 1]
            packet_page = next((p["text"] for p in packet_docs[sha]["pages"] if p["pdf_page"] == page), None)
            if packet_page != text:
                raise ValueError(f"Packet page differs from extraction: {bid} {axis}")
            if not whitespace(item["evidence_quote"]) or whitespace(item["evidence_quote"]) not in whitespace(text):
                raise ValueError(f"Evidence quote not found on cited page: {bid} {axis}")

        for axis in AXES:
            if not isinstance(review.get(axis), dict):
                raise ValueError(f"Missing axis object: {bid} {axis}")
            evidence(axis, review[axis])
        for study in review.get("studies", []):
            if not study.get("study_id"):
                raise ValueError("Per-study evidence needs a study_id: " + bid)
            for axis in AXES:
                if axis in study:
                    evidence(axis, study[axis], allow_unassigned=True)
        completed.append(review)
    return {"n_review_records": len(reviews), "n_completed": len(completed),
            "n_ready_articles": sum(r["readiness"] == "ready_for_fulltext_review" for r in packet.values()),
            "completed_benchmark_ids": sorted(r["benchmark_id"] for r in completed),
            "design_counts": dict(Counter(r["design"]["decision"] for r in completed)),
            "source_hashes_and_page_spans_validated": True,
            "reviews_sha256": digest(review_path.read_bytes()), "packet_sha256": digest(packet_path.read_bytes()),
            "design_independent_of_other_axes": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["inventory", "prepare", "acquire", "validate"])
    parser.add_argument("--sample", type=str)
    parser.add_argument("--reviews", type=str)
    parser.add_argument("--workers", type=int, default=MAX_WORKERS, choices=range(1, MAX_WORKERS + 1))
    args = parser.parse_args()
    if args.stage == "validate":
        if not args.reviews:
            parser.error("--reviews is required")
        from pathlib import Path
        print(json.dumps(validate_reviews(Path(args.reviews)), indent=2))
    elif args.stage == "inventory":
        print(json.dumps({"documents": len(local_inventory())}))
        write_json(RESULTS / "review_schema.json", reviewer_schema())
    else:
        if not args.sample:
            parser.error("--sample is required")
        from pathlib import Path
        prepare(Path(args.sample), acquire=args.stage == "acquire", workers=args.workers)
