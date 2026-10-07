"""Freeze one Scopus article per SCORE journal/year (2016–2025).

Keep matching local articles, then draw a seeded random rank in each empty
stratum. No topic, geography, or full-text availability filter is applied.
Raw responses and licensed abstracts stay in private/score.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "private/score"
PUBLIC = ROOT / "score"
from common import BASE, credentials, now, read_csv, write_csv, write_json

SEED = 20261007
YEARS = list(range(2016, 2026))
REVIEWED = set("85118939204 85042721612 85079670115 85101177545 85175473443 "
               "105005626231 85030544249 85056907668 85131596715 85046645518 "
               "85066605513 85122139505 85174000856 85208237881 85062262291 "
               "84931077293 85175738454".split())
PUBLIC_FIELDS = ["article_id", "journal_id", "journal", "group", "year", "doi",
                 "title", "scopus_id", "source_url", "metadata_source", "source_date",
                 "stratum_n", "sample_rank", "selection_seed", "split",
                 "has_abstract", "has_keywords", "n_authors"]
PRIVATE_FIELDS = PUBLIC_FIELDS + ["fulltext_status", "abstract", "keywords", "authors", "author_ids",
    "source_id", "indexed_journal", "cover_date", "openaccess", "pdf_url",
    "fulltext_path", "text_cache", "query", "response_cache"]


def normal(text):
    aliases = {
        "health psychology official journal of the division of health psychology american psychological association": "health psychology",
        "social science medicine 1982": "social science and medicine",
    }
    text = aliases.get(text.lower(), text.lower())
    return re.sub(r"[^a-z0-9]", "", text.removeprefix("the ").replace("&", "and"))


def rng(label):
    value = int(hashlib.sha256(f"{SEED}:{label}".encode()).hexdigest()[:16], 16)
    return np.random.default_rng(value)


def request(params):
    """Cache each successful request; headers containing keys are never saved."""
    key = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
    path = PRIVATE / "responses" / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text()), str(path.relative_to(ROOT))
    url = BASE + "?" + urllib.parse.urlencode(params)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=credentials()), timeout=45) as reply:
                body = json.load(reply)
                result = {"retrieved_at": now(), "params": params, "body": body,
                          "quota_remaining": reply.headers.get("X-RateLimit-Remaining")}
            if "search-results" not in body:
                raise ValueError("Scopus response has no search-results")
            write_json(path, result)
            return result, str(path.relative_to(ROOT))
        except urllib.error.HTTPError as error:
            if error.code not in {429, 500, 502, 503, 504} or attempt == 4:
                raise RuntimeError(f"Scopus HTTP {error.code}") from None
        except (urllib.error.URLError, TimeoutError):
            if attempt == 4:
                raise RuntimeError("Scopus connection failed") from None
        time.sleep(min(2 ** attempt, 16))


def journals():
    attached = read_csv(ROOT / "inputs/score_journal_frame.csv")
    path = PRIVATE / "score_original_journals.csv"
    if not path.exists():
        with urllib.request.urlopen("https://osf.io/download/tcb8q/", timeout=45) as reply:
            data = reply.read()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    original = read_csv(path)
    lookup = {normal(r["publication_standard"]): r for r in original}
    corrections = {
        "Journal of Applied Psychology": ("1939-1854", "https://www.apa.org/pubs/journals/apl"),
        "Journal of Public Administration Research and Theory":
            ("1477-9803", "https://academic.oup.com/jpart/issue-archive"),
        "Learning and Instruction": ("1873-3263", "https://portal.issn.org/resource/ISSN/1873-3263"),
    }
    rows = []
    for row in attached:
        if row["in_score_62"] != "TRUE":
            continue
        source = lookup[normal(row["journal"])]
        eis, correction_url = corrections.get(row["journal"], (source["eISSN"], ""))
        rows.append({"journal_id": f"J{len(rows) + 1:02d}", "journal": row["journal"],
            "group": row["group"], "issn": source["ISSN"], "eissn": eis,
            "score_eissn": source["eISSN"], "score_title": source["publication_standard"],
            "source_url": "https://osf.io/download/tcb8q/", "correction_url": correction_url})
    assert len(rows) == 62 and len({r["journal"] for r in rows}) == 62
    write_csv(PUBLIC / "journals.csv", rows)
    return rows


def parse(entry):
    authors = entry.get("author", [])
    if isinstance(authors, dict):
        authors = [authors]
    names = [(a.get("given-name") or "") + " " + (a.get("surname") or "") for a in authors]
    doi = (entry.get("prism:doi") or "").lower()
    return {"scopus_id": entry.get("dc:identifier", "").replace("SCOPUS_ID:", ""),
        "doi": doi, "title": entry.get("dc:title", ""),
        "year": entry.get("prism:coverDate", "")[:4],
        "indexed_journal": entry.get("prism:publicationName", ""),
        "journal": entry.get("prism:publicationName", ""),
        "abstract": entry.get("dc:description") or "", "keywords": entry.get("authkeywords") or "",
        "authors": "; ".join(n.strip() or a.get("authname", "") for n, a in zip(names, authors)),
        "author_ids": "; ".join(a.get("authid", "") for a in authors), "n_authors": len(authors),
        "source_id": entry.get("source-id", ""), "cover_date": entry.get("prism:coverDate", ""),
        "openaccess": entry.get("openaccess", ""), "subtype": entry.get("subtype", ""),
        "source_url": "https://doi.org/" + doi if doi else entry.get("prism:url", "")}


def inventory(frame):
    """Match PDFs by existing identity manifests or an article DOI/title match."""
    metadata = {}
    for path in (ROOT / "private/cache").rglob("*.json"):
        content = json.loads(path.read_text())
        for entry in content.get("body", {}).get("search-results", {}).get("entry", []):
            row = parse(entry)
            old = metadata.get(row["scopus_id"], {})
            if row["scopus_id"] and len(row["abstract"]) >= len(old.get("abstract", "")):
                metadata[row["scopus_id"]] = row
    legacy = ROOT / "private/articles.csv"
    for row in read_csv(legacy) if legacy.exists() else []:
        if row["scopus_id"] not in metadata:
            metadata[row["scopus_id"]] = row
    identities = {}
    legacy_results = ROOT / "archive/tess/results"
    if not legacy_results.exists():
        legacy_results = ROOT / "results"
    for path in legacy_results.rglob("availability_manifest.csv"):
        for row in read_csv(path):
            sha = row.get("source_sha256") or row.get("selected_pdf_sha256")
            if sha and row.get("scopus_id"):
                identities[sha] = row["scopus_id"]
    texts = {}
    for path in (ROOT / "private").rglob("*.json"):
        if path.parent.name != "texts":
            continue
        value = json.loads(path.read_text())
        if value.get("source_sha256") and value.get("pages"):
            texts[value["source_sha256"]] = (str(path.resolve()), " ".join(value["pages"][:2]))
    frame_by_name = {normal(r["journal"]): r for r in frame}
    by_doi = {r.get("doi", "").lower(): r for r in metadata.values() if r.get("doi")}
    candidates = {}
    for path in sorted((ROOT / "private").rglob("*.pdf")):
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        cache, opening = texts.get(sha, ("", ""))
        sid = identities.get(sha, path.stem if path.stem.isdigit() else "")
        row = metadata.get(sid)
        if not row:
            if not opening:
                result = subprocess.run(["pdftotext", "-f", "1", "-l", "2", str(path), "-"],
                    capture_output=True, text=True, timeout=30)
                opening = result.stdout
            for doi in re.findall(r"10\.\d{4,9}/[^\s<>\"\]]+", opening[:8000], re.I):
                match = by_doi.get(doi.rstrip(".,;)").lower())
                if match and normal(match["title"])[:60] in normal(opening):
                    row = match
                    break
        if not row or normal(row.get("journal", "")) not in frame_by_name:
            continue
        if row.get("year", "") not in [str(y) for y in YEARS]:
            continue
        if "supplement" in path.name.lower() or "supporting" in path.name.lower():
            continue
        journal = frame_by_name[normal(row["journal"])]
        candidate = {**row, **journal, "fulltext_path": str(path.resolve()),
                     "text_cache": cache, "source_sha256": sha}
        old = candidates.get(row["scopus_id"])
        if old is None or (cache and not old["text_cache"]):
            candidates[row["scopus_id"]] = candidate
    rows = sorted(candidates.values(), key=lambda r: (r["journal_id"], r["year"], r["scopus_id"]))
    write_json(PRIVATE / "local_candidates.json", rows)
    print(f"Found {len(rows)} local articles in {len({(r['journal_id'], r['year']) for r in rows})} journal-year cells.", flush=True)
    return rows


def audit(journal):
    """Check every title in an ISSN query, not just the selected article."""
    issns = {journal["issn"], journal["eissn"]}
    query = "(" + " OR ".join(f"ISSN({s.replace('-', '')})" for s in sorted(issns)) + ")"
    query += " AND PUBYEAR > 2015 AND PUBYEAR < 2026 AND SRCTYPE(j) AND DOCTYPE(ar)"
    result, cache = request({"query": query, "count": 1, "view": "STANDARD",
                             "facets": "exactsrctitle(count=100)"})
    body = result["body"]["search-results"]
    categories = body.get("facet", {}).get("category", [])
    if isinstance(categories, dict):
        categories = [categories]
    titles = [r["name"] for r in categories]
    matched = bool(titles) and all(normal(title) == normal(journal["journal"]) for title in titles)
    return {"journal_id": journal["journal_id"], "journal": journal["journal"],
        "indexed_titles": "; ".join(titles), "count_2016_2025": body["opensearch:totalResults"],
        "all_titles_match": matched, "retrieved_at": result["retrieved_at"], "response_cache": cache}


def crossref(journal, year):
    """World Politics moved publisher and Scopus has no 2024–2025 records."""
    path = PRIVATE / "world_politics_crossref_online.json"
    if not path.exists():
        params = {"filter": "from-pub-date:2024-01-01,until-pub-date:2025-12-31,type:journal-article", "rows": 1000}
        url = "https://api.crossref.org/journals/1086-3338/works?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=45) as reply:
            body = json.load(reply)
        write_json(path, {"retrieved_at": now(), "url": url, "body": body})
    result = json.loads(path.read_text())
    message = result["body"]["message"]
    assert len(message["items"]) == message["total-results"]
    # Issue-assigned records prevent early-online versions counting in both years.
    # The sole front-matter record in these two volumes is the referee list.
    items = [r for r in message["items"] if r.get("volume") == {2024: "76", 2025: "77"}[year]
             and r.get("title") != ["Referees"]]
    items.sort(key=lambda r: r["DOI"])
    assert len({r["DOI"] for r in items}) == len(items)
    rank = int(rng(f"draw:{journal['journal_id']}:{year}").integers(len(items)))
    item = items[rank]
    assert item["published-print"]["date-parts"][0][0] == year
    doi = item["DOI"].lower()
    abstract = html.unescape(re.sub(r"<[^>]+>", "", item.get("abstract", ""))).strip()
    authors = item.get("author", [])
    row = {"article_id": "cr_" + hashlib.sha256(doi.encode()).hexdigest()[:12], "scopus_id": "",
        "journal_id": journal["journal_id"], "journal": journal["journal"], "group": journal["group"],
        "year": str(year), "doi": doi, "title": " ".join(item["title"]), "abstract": abstract,
        "keywords": "", "authors": "; ".join((a.get("given", "") + " " + a.get("family", "")).strip() for a in authors),
        "n_authors": len(authors), "metadata_source": "Crossref", "source_date": result["retrieved_at"],
        "source_url": "https://doi.org/" + doi, "stratum_n": len(items), "sample_rank": rank,
        "selection_seed": SEED, "has_abstract": bool(abstract), "has_keywords": False,
        "fulltext_status": "pending", "response_cache": str(path.relative_to(ROOT)),
        "query": result["url"], "cover_date": str(year), "indexed_journal": "World Politics"}
    write_json(PRIVATE / "selected" / f"{journal['journal_id']}_{year}.json", row)
    return row


def select(journal, year, local):
    jid = journal["journal_id"]
    path = PRIVATE / "selected" / f"{jid}_{year}.json"
    if path.exists():
        return json.loads(path.read_text())
    issns = {journal["issn"], journal["eissn"]}
    query = "(" + " OR ".join(f"ISSN({s.replace('-', '')})" for s in sorted(issns)) + ")"
    query += f" AND PUBYEAR = {year} AND SRCTYPE(j) AND DOCTYPE(ar)"
    result, _ = request({"query": query, "count": 1, "view": "STANDARD"})
    count = int(result["body"]["search-results"]["opensearch:totalResults"])
    if not count:
        if jid == "J52" and year in {2024, 2025}:
            return crossref(journal, year)
        raise ValueError(f"Empty stratum: {jid} {year}")
    matches = [r for r in local if r["journal_id"] == jid and r["year"] == str(year)]
    # Existing full texts are retained as requested. Break ties before reading their labels.
    matches.sort(key=lambda r: hashlib.sha256(f"{SEED}:{r['scopus_id']}".encode()).hexdigest())
    record = None
    for existing in matches:
        found, response_cache = request({"query": query + f" AND EID(2-s2.0-{existing['scopus_id']})",
                                         "count": 1, "view": "COMPLETE"})
        if int(found["body"]["search-results"]["opensearch:totalResults"]) == 1:
            record = parse(found["body"]["search-results"]["entry"][0])
            record.update(fulltext_path=existing["fulltext_path"], text_cache=existing["text_cache"])
            rank = ""
            break
    if record is None:
        rank = int(rng(f"draw:{jid}:{year}").integers(count))
        found, response_cache = request({"query": query, "count": 1, "view": "COMPLETE",
                                         "start": rank, "sort": "+coverDate,+title"})
        if int(found["body"]["search-results"]["opensearch:totalResults"]) != count:
            raise ValueError(f"Stratum changed during draw: {jid} {year}")
        record = parse(found["body"]["search-results"]["entry"][0])
    if record["year"] != str(year) or normal(record["journal"]) != normal(journal["journal"]):
        raise ValueError(f"Wrong journal/year returned: {jid} {year}: {record['journal']} {record['year']}")
    record.update(article_id=record["scopus_id"], journal_id=jid, journal=journal["journal"],
        group=journal["group"], stratum_n=count, sample_rank=rank, selection_seed=SEED,
        metadata_source="Scopus", source_date=found["retrieved_at"], query=query,
        response_cache=response_cache, fulltext_status="local_file" if record.get("fulltext_path") else "pending",
        has_abstract=bool(record.get("abstract")), has_keywords=bool(record.get("keywords")))
    write_json(path, record)
    return record


def export():
    rows = [json.loads(p.read_text()) for p in sorted((PRIVATE / "selected").glob("*.json"))]
    for row in rows:
        row["article_id"] = row.get("scopus_id") or row["article_id"]
        row["split"] = "pending"
    for journal_id in {r["journal_id"] for r in rows}:
        journal_rows = [r for r in rows if r["journal_id"] == journal_id]
        if len(journal_rows) != len(YEARS):
            continue
        eligible = [r["year"] for r in journal_rows if r["scopus_id"] not in REVIEWED]
        holdout = set(rng(f"split:{journal_id}").choice(sorted(eligible), 2, replace=False))
        for row in journal_rows:
            row["split"] = "holdout" if row["year"] in holdout else "development"
    for folder, fields in [(PRIVATE, PRIVATE_FIELDS), (PUBLIC, PUBLIC_FIELDS)]:
        temp = folder / "articles.csv.tmp"
        write_csv(temp, rows, fields)
        temp.replace(folder / "articles.csv")
    write_json(PRIVATE / "sample_status.json", {"updated_at": now(), "expected": 620,
        "selected": len(rows), "journals": len({r['journal_id'] for r in rows}),
        "with_abstract": sum(bool(r.get("abstract")) for r in rows),
        "with_keywords": sum(bool(r.get("keywords")) for r in rows),
        "local_fulltexts": sum(bool(r.get("fulltext_path")) for r in rows)})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["inventory", "audit", "sample", "export"])
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.command == "export":
        export()
        return
    frame = journals()
    if args.command == "audit":
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            rows = list(pool.map(audit, frame))
        write_csv(PUBLIC / "journal_audit.csv", rows)
        for row in rows:
            if not row["all_titles_match"]:
                print("IDENTIFIER MISMATCH", row, flush=True)
        print(f"Audited {len(rows)} journals: {sum(r['all_titles_match'] for r in rows)} matched.", flush=True)
        return
    if args.command == "inventory":
        inventory(frame)
        return
    path = PRIVATE / "local_candidates.json"
    local = json.loads(path.read_text()) if path.exists() else inventory(frame)
    errors = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        jobs = {pool.submit(select, journal, year, local): (journal["journal_id"], year)
                for journal in frame for year in YEARS}
        for i, job in enumerate(as_completed(jobs), 1):
            try:
                row = job.result()
            except Exception as error:
                errors.append({"stratum": jobs[job], "error": str(error)})
                print("ERROR", jobs[job], error, flush=True)
            if i % 20 == 0:
                export()
                print(f"Processed {i}/620 strata; {len(errors)} errors.", flush=True)
    rows = export()
    write_json(PRIVATE / "errors.json", errors)
    print(f"Selected {len(rows)} articles; {len(errors)} errors.", flush=True)
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
