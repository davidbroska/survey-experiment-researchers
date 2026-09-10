"""Build immutable-query dashboards with shared, updatable geography evidence.

This module writes only DASHBOARD_{ORIGINAL,COMPLETE,NARROWER}.html and its
own provenance directory. The historical TOP100 dashboard is never rebuilt.
Public-only builds reproduce recorded PDF availability from validated public
snapshots; they do not revalidate private source files. When the private priority
register is present, its PDF identities and hashes must match that snapshot.
"""
from collections import Counter, defaultdict
import hashlib
import html
import json
import re

from common import ROOT, read_csv, write_json

RANKINGS = ROOT / "results/query_rankings_2026_09_10"
OUTPUT = ROOT / "results/variant_dashboards_2026_09_10"
SNAPSHOT_DATE = "2026-09-10"
VARIANTS = {
    "original": dict(name="Original query", ranking="current_published",
                     membership="current_local_phrase_verified", retrieved=7302,
                     candidates=7035, unresolved_bylines=4,
                     query="queries/recommended.txt", file="DASHBOARD_ORIGINAL.html"),
    "complete": dict(name="Complete proximity query", ranking="original_query",
                     membership="original_query", retrieved=9675,
                     candidates=9675, unresolved_bylines=6,
                     query="queries/proximity_audit_2026_09_10/targeted.txt",
                     file="DASHBOARD_COMPLETE.html"),
    "narrower": dict(name="Narrower proximity query", ranking="narrower_query",
                     membership="narrower_query", retrieved=9365,
                     candidates=9365, unresolved_bylines=6,
                     query="queries/proximity_specific_2026_09_10/primary_plus_specific.txt",
                     file="DASHBOARD_NARROWER.html"),
}
FOCAL = {"50061672800": "Gordon Pennycook", "7003917566": "Jennifer A. Richeson",
         "15520639300": "Kurt Gray", "22986966200": "Jay J. Van Bavel"}


def truth(value):
    return str(value).lower() == "true"


def optional_csv(path):
    return read_csv(path) if path.exists() else []


def safe_url(value):
    return value if value and value.startswith(("https://", "http://")) else ""


def query_tokens(query):
    return re.findall(r'"[^"\\]*(?:\\.[^"\\]*)*"|\{[^}]*\}|[()]|[^\s(){}"]+', query)


def readable_query(query):
    """Reflow only whitespace outside quoted/braced phrases, preserving tokens."""
    lines, current, depth = [], "", 0

    def flush():
        nonlocal current
        if current:
            lines.append("  " * depth + current.rstrip())
            current = ""

    for token in query_tokens(query):
        if token == "(":
            current += token
            flush()
            depth += 1
        elif token == ")":
            flush()
            depth -= 1
            current = token
            flush()
        elif token in ("OR", "AND"):
            flush()
            current = token + " "
        else:
            current += (" " if current and not current.endswith(" ") else "") + token
    flush()
    result = "\n".join(lines)
    assert depth == 0 and query_tokens(result) == query_tokens(query)
    return result


def verified_priority_pdf(row):
    """Keep private document paths and quotations out of the public payload."""
    if not row.get("pdf_path") or not row.get("source_sha256"):
        return False
    path = (ROOT / row["pdf_path"]).resolve()
    if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
        return False
    raw = path.read_bytes()
    return raw.startswith(b"%PDF") and hashlib.sha256(raw).hexdigest() == row["source_sha256"]


def article_access(aliases, doi, source):
    available = any(source["availability"].get(sid, False) for sid in aliases)
    issues = {source["access_issues"].get(sid) for sid in aliases}
    if "user_unavailable" in issues:
        reason = "User could not download this article; awaiting an alternative copy."
    elif "publisher_unavailable" in issues or (source["tf_access_unavailable"] and doi.lower().startswith("10.1080/")):
        reason = ("User reports no Taylor & Francis access; awaiting an accessible manuscript or other lawful copy. "
                  "This does not imply an article-specific failed download.")
    else:
        reason = ""
    return dict(pdf_available=available, alternative_copy_pending=bool(reason) and not available,
                access_note=reason if not available else "")


def load_inputs():
    paths = [RANKINGS / name for name in
             ("articles.csv", "article_geography.csv", "author_article_links.csv")]
    profiles = {}
    for relative in ("inputs/researcher_affiliations.csv",
                     "inputs/query_dashboard_affiliations.csv"):
        path = ROOT / relative
        if path.exists():
            paths.append(path)
            for row in read_csv(path):
                profiles.setdefault(row["authid"], {}).update({k: v for k, v in row.items() if v})
    names = {aid: p.get("full_name", "") for aid, p in profiles.items()}
    path = ROOT / "inputs/query_ranking_name_reviews.csv"
    if path.exists():
        paths.append(path)
        names.update({r["authid"]: r["full_name"] for r in read_csv(path)})
    names.update(FOCAL)
    availability, access_issues = {}, {}
    tf_access_unavailable = False
    for relative in ("results/fulltext_download_queue.csv",
                     "results/benchmark_review_wave2_2026_09_10/availability_manifest.csv",
                     "results/benchmark_review_wave3_2026_09_10/availability_manifest.csv"):
        path = ROOT / relative
        if path.exists():
            paths.append(path)
            for row in read_csv(path):
                available = any(truth(row.get(k)) for k in ("local_pdf_available", "available_after_wave2", "available_after_wave3"))
                available = available or row.get("fulltext_readiness") == "ready_for_fulltext_review"
                availability[row["scopus_id"]] = availability.get(row["scopus_id"], False) or available
                if row.get("manual_retrieval_status") == "user_unavailable":
                    access_issues[row["scopus_id"]] = "user_unavailable"
                if row.get("publisher_access_issue") == "user_reported_Taylor_and_Francis_access_unavailable":
                    access_issues.setdefault(row["scopus_id"], "publisher_unavailable")
                    tf_access_unavailable = True
    path = ROOT / "inputs/manual_download_status.csv"
    if path.exists():
        paths.append(path)
        access_issues.update({r["scopus_id"]: "user_unavailable" for r in read_csv(path) if r["status"] == "user_unavailable"})
    public_priority = ROOT / "results/us_geography_priority_2026_09_10/fulltext_geography_reviews.csv"
    validation_path = ROOT / "results/us_geography_priority_2026_09_10/fulltext_review_validation.json"
    private_priority = ROOT / "private/us_geography_priority_2026_09_10/fulltext_reviews.csv"
    if public_priority.exists():
        paths.extend((public_priority, validation_path))
        rows = read_csv(public_priority)
        validation = json.loads(validation_path.read_text())
        public_rows = {r["scopus_id"]: r for r in rows}
        assert len(public_rows) == len(rows), "Priority PDF snapshot must contain unique article IDs."
        for key in ("reviewed_articles", "pdf_hashes_verified", "article_identity_verified"):
            assert validation[key] == len(rows), "The published priority snapshot is not fully source-validated."
        for row in rows:
            assert re.fullmatch(r"[0-9a-f]{64}", row["source_sha256"]) and row["source_kind"], "Priority PDF source provenance is incomplete."
            availability[row["scopus_id"]] = True
        if private_priority.exists():
            private_rows = {r["scopus_id"]: r for r in read_csv(private_priority)}
            assert private_rows.keys() == public_rows.keys(), "Private and public priority article IDs must agree."
            for sid, row in private_rows.items():
                assert all(row[k] == public_rows[sid][k] for k in ("source_sha256", "source_kind")), "Private and public priority source provenance must agree."
                assert verified_priority_pdf(row), "A priority review must cite an existing PDF with the recorded hash."
    else:
        assert not private_priority.exists(), "Publish the validated priority availability snapshot before rendering."
    credits = defaultdict(lambda: defaultdict(set))
    for r in read_csv(RANKINGS / "author_article_links.csv"):
        credits[r["variant"]][r["identity"]].add(r["authid"])
    return dict(paths=paths, profiles=profiles, names=names, availability=availability,
                access_issues=access_issues, tf_access_unavailable=tf_access_unavailable,
                articles=read_csv(RANKINGS / "articles.csv"),
                geography={r["identity"]: r for r in read_csv(RANKINGS / "article_geography.csv")},
                credits=credits)


def make_payload(key, source):
    config = VARIANTS[key]
    variant = config["ranking"]
    rank_path = RANKINGS / (variant + "_ranking.csv")
    us_path = RANKINGS / (variant + "_us_ranking.csv")
    pool_path = RANKINGS / ("uniform_pool_" + variant + "_us_ranking.csv")
    paths = source["paths"] + [rank_path, us_path, pool_path, ROOT / config["query"]]
    ranks = {r["authid"]: r for r in read_csv(rank_path)}
    us = {r["authid"]: r for r in read_csv(us_path)}
    pool = {r["authid"]: r for r in read_csv(pool_path)}
    authors = []
    for aid in sorted(set(ranks) | set(pool) | set(FOCAL), key=int):
        r, g = ranks.get(aid, {}), us.get(aid, {})
        n, first, last = (int(r.get(k, 0)) for k in ("n_articles", "n_first", "n_last"))
        p = source["profiles"].get(aid, {})
        authors.append(dict(
            authid=aid, name=source["names"].get(aid) or r.get("name") or g.get("name") or aid,
            n_articles=n, n_first=first, n_last=last, n_sole=first + last - n,
            rank=int(r["competition_rank"]) if r else None,
            position=int(r["display_position"]) if r else None,
            us_count=int(g.get("n_us_articles", 0)),
            us_explicit=int(g.get("n_us_explicit", 0)), us_inferred=int(g.get("n_us_inferred", 0)),
            unclear=int(g.get("n_unclear", 0)), unreviewed=int(g.get("n_unreviewed", 0)),
            us_upper=int(g.get("n_us_upper", 0)),
            us_rank=int(g["us_competition_rank"]) if g else None,
            us_position=int(g["us_display_position"]) if g else None,
            pool_rank=int(pool[aid]["us_competition_rank"]) if aid in pool else None,
            pool_position=int(pool[aid]["us_display_position"]) if aid in pool else None,
            in_pool=aid in pool,
            institution=p.get("institution", ""), department=p.get("department", ""),
            country=p.get("country", ""), role=p.get("role", ""),
            profile_url=safe_url(p.get("source_url", "")), profile_date=p.get("verified_on", ""),
            profile_notes=p.get("notes", ""),
        ))
    aid_map = {r["authid"]: r for r in authors}
    article_rows = []
    credits = source["credits"][variant]
    for a in source["articles"]:
        if not truth(a[config["membership"]]):
            continue
        g = source["geography"][a["identity"]]
        aids = sorted(credits.get(a["identity"], ()), key=int)
        in_pool = [aid for aid in aids if aid in pool]
        aliases = a["all_scopus_ids"].split("|")
        access = article_access(aliases, a["doi"], source)
        url = ("https://doi.org/" + a["doi"]) if a["doi"] else (
            "https://www.scopus.com/record/display.uri?eid=2-s2.0-" + a["scopus_id"])
        article_rows.append(dict(
            sid=a["scopus_id"], title=a["title"], year=a["year"], journal=a["journal"],
            doi=a["doi"], url=url, authors=aids, in_pool=bool(in_pool),
            geography=g["sample_us_label"], rationale=g["rationale"],
            evidence=g["source_review"], mixed=truth(g["mixed"]),
            **access, filename=a["scopus_id"] + ".pdf",
            priority=sum(aid_map[aid]["pool_rank"] <= 50 or
                         (aid_map[aid]["rank"] or 10**9) <= 50 for aid in in_pool),
        ))
    article_rows.sort(key=lambda a: (-a["priority"], -len(a["authors"]), int(a["sid"])))
    pool_articles = [a for a in article_rows if a["in_pool"]]
    labels = Counter(a["geography"] for a in pool_articles)
    query = (ROOT / config["query"]).read_text().strip()
    assert len(pool) == 120, "The frozen comparison pool must remain the same 120 researchers."
    assert len(article_rows) == config["candidates"], (key, len(article_rows))
    for author in authors:
        assert author["n_articles"] == author["n_first"] + author["n_last"] - author["n_sole"]
    counts = Counter(aid for a in article_rows for aid in a["authors"])
    assert all(counts[a["authid"]] == a["n_articles"] for a in authors), "Author–article credits must reconcile."
    geography_counts = defaultdict(Counter)
    for article in article_rows:
        for aid in article["authors"]:
            geography_counts[aid][article["geography"]] += 1
    for author in authors:
        c = geography_counts[author["authid"]]
        assert author["us_count"] == c["us_explicit"] + c["us_inferred"], "Rebuild geography rankings before dashboards."
        assert author["unclear"] == c["unclear"] and author["unreviewed"] == c["unreviewed"], "Stale geography coverage."
    assert labels["unreviewed"] == 0, "Do not claim complete review of the common pool before annotation."
    result = dict(key=key, name=config["name"], query=query, query_path=config["query"],
                  retrieved=config["retrieved"], candidates=config["candidates"],
                  unresolved_bylines=config["unresolved_bylines"], authors=authors, articles=article_rows,
                  pool_size=len(pool), pool_articles=len(pool_articles), pool_labels=dict(labels),
                  ranking_csv=str(rank_path.relative_to(ROOT)),
                  geography_csv=str((RANKINGS / "article_geography.csv").relative_to(ROOT)),
                  snapshot_date=SNAPSHOT_DATE)
    return result, paths


def methodology(key, data):
    if key == "original":
        retrieval = ("The original query retrieved 7,302 distinct articles. Its historical local phrase check retained "
                     "7,035 candidates; four had unresolved bylines, leaving 7,031 articles with author credits. "
                     "This page preserves the published author–article credits and counts. Sample-geography evidence "
                     "is updated from the shared review register, so US counts may differ from the frozen historical dashboard.")
    else:
        retrieval = (f"This query retrieves {data['retrieved']:,} distinct candidate articles. Six have unresolved "
                     "bylines and receive no author credits. These are retrieval-only candidate counts: the older local "
                     "phrase filter is not applied to the new searches. Two bylines capped at 100 authors were repaired "
                     "using complete ordered author lists.")
    description = ("The complete query adds a guarded abstract clause describing reading or information manipulation to "
                   "the named-design and procedure core." if key == "complete" else
                   "The narrower query removes only the reading–passage and manipulation–information proximity pairs "
                   "from the complete clause. It retains 9,365 of the complete query’s 9,675 candidates. This is a "
                   "sensitivity and screening-priority view, not an independently validated precision improvement." if key == "narrower" else
                   "The original query combines exact survey/vignette phrases with guarded embedded-experiment, "
                   "text-assignment, information-treatment and question-wording descriptions. The local text check "
                   "preserves punctuation to reduce accidental phrase matches.")
    return f"""<h2>Methodology · {html.escape(data['name'])}</h2>
<ol class="selection-steps"><li>Define the journal frame using the 3,401 journals in the frozen TESS-investigator publication list. Candidate donors need not have participated in TESS. Search journal articles published in 2010–2026. The literal query below is applied to Scopus; retrieved records are then restricted to the frozen <a href="results/venue_frame.csv">journal frame</a>.</li>
<li>{description} This page always uses this query; the other query versions have their own URLs.</li>
<li>{retrieval} Count each distinct canonical article once for each distinct first or last author, and count a sole author once. Equal scores share competition ranks; a fixed numeric author-ID order determines the first 100 displayed researchers. First/last authorship is a proxy for possible PI involvement, not verified seniority.</li>
<li>Join current institutions, departments, countries and roles only from sourced profiles. Missing fields are shown as unknown. Sample geography concerns participants and is coded separately: explicit US evidence and justified contextual inference are combined; unclear or unreviewed cases do not count as non-US.</li>
<li>For the main US comparison, use the same 120 researchers: the historical 100 plus all new total-count leaders including cutoff ties. In this query, their {data['pool_articles']:,} distinct credited articles all have a geography judgment, of which {data['pool_labels'].get('unclear', 0):,} remain unclear. US sorting within this pool is conditional, not a global US top 100. The separate all-author US view is partially reviewed and can favor better-reviewed authors.</li>
<li>Screen article design, parser compatibility and access to respondent-level data before invitations. Counts describe publications, not independent datasets. Geography and design judgments remain AI-assisted and await human validation. The 28 legacy-only candidates absent from both new queries remain archived for screening.</li></ol>
<div class="summary-actions"><button id="copy-query">Copy Scopus query</button><a href="{html.escape(data['query_path'])}" download>Download literal query</a><a href="RANKING_COMPARISON_REPORT.html">Comparison and recommendation ↗</a></div>
<p id="query-copy-status" class="status" aria-live="polite"></p><textarea id="query-copy-fallback" readonly rows="8" hidden aria-label="Literal query to copy"></textarea><p class="compact-note">The display adds line breaks and indentation only. Copy and download use the literal executed query.</p><pre class="scopus-query"><code id="literal-query">{html.escape(readable_query(data['query']))}</code></pre>"""


def build():
    source = load_inputs()
    template = (ROOT / "pipeline/variant_dashboard_template.html").read_text()
    css = (ROOT / "pipeline/dashboard.css").read_text()
    script = (ROOT / "pipeline/variant_dashboard.js").read_text()
    artifacts = {}
    for key, config in VARIANTS.items():
        data, paths = make_payload(key, source)
        navigation = " · ".join(
            ("<strong aria-current=\"page\">" + html.escape(v["name"]) + "</strong>") if k == key else
            f'<a href="{v["file"]}">{html.escape(v["name"])}</a>' for k, v in VARIANTS.items())
        serialized = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c").replace("&", "\\u0026")
        out = template.replace("__CSS__", css).replace("__NAME__", html.escape(config["name"]))
        out = out.replace("__NAVIGATION__", navigation).replace("__METHODS__", methodology(key, data))
        out = out.replace("__SCRIPT__", script).replace("__DATA__", serialized)
        output = ROOT / config["file"]
        output.write_text(out)
        inputs = paths + [ROOT / "pipeline/variant_dashboards.py", ROOT / "pipeline/variant_dashboard_template.html",
                          ROOT / "pipeline/variant_dashboard.js", ROOT / "pipeline/dashboard.css"]
        provenance = dict(query_variant=key, query_sha256=hashlib.sha256(data["query"].encode()).hexdigest(),
                          researchers=len(data["authors"]), articles=len(data["articles"]),
                          pool_size=data["pool_size"], pool_articles=data["pool_articles"],
                          pool_geography=data["pool_labels"], human_validated=False,
                          frozen_dashboard_modified=False,
                          priority_availability_basis="Published source-validated snapshot; private PDF bytes additionally checked when the private register is present.",
                          input_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
                          output_sha256=hashlib.sha256(out.encode()).hexdigest())
        write_json(OUTPUT / (key + "_provenance.json"), provenance)
        artifacts[key] = {"path": config["file"], "bytes": len(out.encode()), "authors": len(data["authors"])}
    print(json.dumps(artifacts, indent=2))


if __name__ == "__main__":
    build()
