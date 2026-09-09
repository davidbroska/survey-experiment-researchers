"""Read-only Scopus client with immutable request cache and complete pagination."""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from common import ROOT, REPO, digest, now, write_json

BASE = "https://api.elsevier.com/content/search/scopus"


def credentials():
    values = dict(os.environ)
    env = REPO / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() in {"SCOPUS_API_KEY", "SCOPUS_INSTTOKEN"}:
                values.setdefault(key.strip(), value.strip().strip("\"'"))
    if not values.get("SCOPUS_API_KEY"):
        raise RuntimeError("Set SCOPUS_API_KEY in the environment or repository .env")
    headers = {"Accept": "application/json", "X-ELS-APIKey": values["SCOPUS_API_KEY"]}
    if values.get("SCOPUS_INSTTOKEN"):
        headers["X-ELS-Insttoken"] = values["SCOPUS_INSTTOKEN"]
    return headers


def request(params, namespace="search"):
    key = digest(json.dumps(params, sort_keys=True))
    path = ROOT / "private" / "cache" / namespace / (key + ".json")
    if path.exists():
        return json.loads(path.read_text())
    url = BASE + "?" + urllib.parse.urlencode(params)
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers=credentials())
            with urllib.request.urlopen(req, timeout=45) as response:
                body = json.load(response)
                if "search-results" not in body:
                    raise RuntimeError("Scopus response lacks search-results")
                result = {"retrieved_at": now(), "params": params,
                          "quota_remaining": response.headers.get("X-RateLimit-Remaining"),
                          "body": body}
            write_json(path, result)
            return result
        except urllib.error.HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504} or attempt == 4:
                # Do not print request headers or an authentication-bearing URL.
                raise RuntimeError(f"Scopus HTTP {exc.code}: {exc.read(400).decode(errors='replace')}") from None
            time.sleep(min(2 ** (attempt + 1), 30))
        except (urllib.error.URLError, TimeoutError):
            if attempt == 4:
                raise RuntimeError("Scopus connection failed after five attempts") from None
            time.sleep(2 ** attempt)


def count(query):
    result = request({"query": query, "count": 1, "view": "STANDARD"}, "counts")
    return {"query": query, "count": int(result["body"]["search-results"]["opensearch:totalResults"]),
            "retrieved_at": result["retrieved_at"]}


def search(query, view="COMPLETE"):
    cursor, seen_cursors, records, expected, dates = "*", set(), {}, None, []
    while True:
        if cursor in seen_cursors:
            raise RuntimeError("Pagination cursor repeated before retrieval completed")
        seen_cursors.add(cursor)
        result = request({"query": query, "count": 25 if view == "COMPLETE" else 200,
                          "view": view, "cursor": cursor})
        dates.append(result["retrieved_at"])
        sr = result["body"]["search-results"]
        total = int(sr["opensearch:totalResults"])
        if expected is not None and total != expected:
            raise RuntimeError("Scopus result count changed during pagination; use a fresh cache/run")
        expected = total
        entries = sr.get("entry", [])
        if total == 0:
            return [], {"query": query, "expected": 0, "retrieved": 0, "complete": True, "dates": dates}
        for entry in entries:
            sid = entry.get("dc:identifier", "").replace("SCOPUS_ID:", "")
            if not sid:
                raise RuntimeError("Missing article identifier or Scopus entry error")
            records[sid] = entry
        if len(records) == total:
            return list(records.values()), {"query": query, "expected": total,
                "retrieved": len(records), "complete": True, "dates": dates}
        nxt = sr.get("cursor", {}).get("@next")
        if not entries or not nxt or nxt == cursor or len(records) > total:
            raise RuntimeError(f"Incomplete retrieval: {len(records)} of {total}")
        cursor = nxt

