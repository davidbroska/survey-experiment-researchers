"""Prepare selected source rechecks; --run uses Flex, --revalidate uses saved responses.

Input: private/score/api_rechecks/sources.json, a list of article_id/supports records.
Each support has source (public URL), fulltext_path, format, text_cache and
source_sha256; optional title/coverage describe the supplied document or excerpt.
Notes and prior judgments are never sent. Results await separate adjudication.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import fcntl
import json
import math
from pathlib import Path
import re
import threading

import api_annotate as base
from review import index_rows, public_text, read_rows, validate_evidence, validate_source_quotes
from source_review import normalized, source_pages

RUN = base.PRIVATE / "api_rechecks"
MANIFEST = RUN / "manifest.json"
BASELINE = base.PRIVATE / "unclear_recheck_run.json"
BASELINE_COUNT = 13
FLEX_RATES = {key: value / 2 for key, value in base.RATES.items()}
STATE_LOCK = threading.Lock()


def document(record, source):
    """Verify source/cache identity and retain all supplied pages or segments."""
    if base.digest(Path(record["fulltext_path"]).read_bytes()) != record["source_sha256"]:
        raise ValueError("Source file changed")
    pages, unit = source_pages(record)
    if not pages or not any(normalized(page) for page in pages):
        raise ValueError("Source has no extractable text")
    unit = "PDF page" if unit == "PDF page" else "text segment"
    provenance = {key: record[key] for key in ["fulltext_path", "format", "text_cache", "source_sha256"]}
    provenance.update(source=source, unit=unit,
                      text_cache_sha256=base.digest(Path(record["text_cache"]).read_bytes()),
                      title=record.get("title", ""), coverage=record.get("coverage", "full document"))
    supplied = {key: provenance[key] for key in ["source", "title", "coverage", "unit"]}
    supplied["pages"] = [{"page_or_segment": i + 1, "text": normalized(page)} for i, page in enumerate(pages)]
    provenance["pages_or_segments_supplied"] = list(range(1, len(pages) + 1))
    return provenance, supplied


def make_packet(entry, article, main):
    packet = base.make_packet(article, main)
    payload = json.loads(packet["body"]["input"][0]["content"])
    metadata, supplied = document(main, "main")
    documents = {"main": metadata}
    payload["page_unit"] = supplied["unit"]
    payload["supporting_sources"] = []
    for record in entry.get("supports", []):
        url = record["source"]
        if (not url.startswith(("https://", "http://")) or public_text(url) != url or url in documents):
            raise ValueError("Support needs a distinct public URL without private credentials")
        metadata, supplied = document(record, url)
        documents[url] = metadata
        payload["supporting_sources"].append(supplied)
    body = packet["body"]
    body["service_tier"] = "flex"
    body["input"][0]["content"] = json.dumps(payload, ensure_ascii=False)
    properties = body["text"]["format"]["schema"]["properties"]["evidence"]["items"]["properties"]
    properties["source"]["enum"] = list(documents)
    properties["location"].update(pattern=r"^(PDF page|text segment) [1-9][0-9]*$",
                                   description="Use the cited source's unit and numbered supplied page_or_segment: 'PDF page N' or 'text segment N'.")
    estimated = math.ceil(len(base.serialized(body)) / 3)
    long_input = estimated > 272000
    estimate = (estimated * FLEX_RATES["cache_write"] * (2 if long_input else 1)
                + base.MAX_OUTPUT * FLEX_RATES["output"] * (1.5 if long_input else 1)) / 1_000_000
    # Reserve the highest standard context rates as a safeguard against an
    # unexpected returned tier. Such a response stops further paid requests.
    reserve = (estimated * base.RATES["cache_write"] * 2
               + base.MAX_OUTPUT * base.RATES["output"] * 1.5) / 1_000_000
    packet.update(documents=documents, estimated_input_tokens=estimated,
                  estimated_flex_max_usd=estimate, reserved_usd=reserve,
                  input_sha256=base.digest(body["input"][0]["content"].encode()),
                  request_sha256=base.digest(base.serialized(body).encode()))
    return packet


def prepare(path, articles, sources, require_existing=False):
    raw = path.read_bytes()
    entries = json.loads(raw)
    allowed = json.loads(BASELINE.read_text())["article_ids"]
    if (not isinstance(allowed, list) or len(allowed) != BASELINE_COUNT
            or len(set(allowed)) != BASELINE_COUNT or not all(isinstance(key, str) for key in allowed)):
        raise ValueError("Recheck baseline must identify the original 13 distinct articles")
    if not isinstance(entries, list) or not 1 <= len(entries) <= BASELINE_COUNT:
        raise ValueError("Input manifest must select between 1 and 13 baseline articles")
    ids = [entry["article_id"] for entry in entries]
    if len(set(ids)) != len(ids) or not set(ids) <= articles.keys() or not set(ids) <= set(allowed):
        raise ValueError("Input manifest has duplicate, unknown or non-baseline article identifiers")
    manifest = {"sources_manifest_sha256": base.digest(raw), "model": base.MODEL,
                "baseline_article_ids_sha256": base.digest(base.serialized(sorted(allowed)).encode()),
                "reasoning_effort": "medium", "service_tier": "flex", "budget_usd": base.BUDGET,
                "rates_per_million_usd": FLEX_RATES, "prompt_sha256": base.digest(base.PROMPT.read_bytes()),
                "articles": []}
    packets = []
    for entry in entries:
        key = entry["article_id"]
        packet = make_packet(entry, articles[key], sources[key])
        packets.append(packet)
        manifest["articles"].append({"article_id": key, "request_sha256": packet["request_sha256"],
                                     "estimated_flex_max_usd": packet["estimated_flex_max_usd"],
                                     "reserved_usd": packet["reserved_usd"]})
    if MANIFEST.exists():
        if json.loads(MANIFEST.read_text()) != manifest:
            raise ValueError("Frozen recheck manifest changed")
        for packet in packets:
            saved = json.loads((RUN / "requests" / (packet["article_id"] + ".json")).read_text())
            if saved != packet:
                raise ValueError("Frozen recheck source or request changed")
    elif require_existing:
        raise ValueError("Run --prepare before paid execution or revalidation")
    else:
        for packet in packets:
            base.save_json(RUN / "requests" / (packet["article_id"] + ".json"), packet)
        base.save_json(MANIFEST, manifest)
    return packets


def usage_cost(response):
    standard = base.usage_cost(response)
    if standard is None:
        return None
    tier = response.get("service_tier")
    if tier not in ["flex", "default", "standard", "priority", "fast"]:
        return None
    if response["usage"]["input_tokens"] > 272000:
        output = response["usage"]["output_tokens"] * base.RATES["output"] / 1_000_000
        standard = (standard - output) * 2 + output * 1.5
    return standard * (0.5 if tier == "flex" else 2 if tier in ["priority", "fast"] else 1)


def spending():
    actual, uncertain = base.spending()  # Original 69 standard requests remain intact.
    for path in (RUN / "attempts").glob("*.json"):
        attempt = json.loads(path.read_text())
        cost = usage_cost(attempt.get("response", {}))
        if cost is None:
            uncertain += attempt["reserved_usd"]
        else:
            actual += cost
    return actual, uncertain


def validate_review(response, packet):
    if response.get("status") != "completed":
        raise ValueError("Response incomplete or failed")
    parts = [part for item in response.get("output", []) if item.get("type") == "message"
             for part in item.get("content", [])]
    if any(part.get("type") == "refusal" for part in parts):
        raise ValueError("Response refused")
    review = json.loads("".join(part["text"] for part in parts if part.get("type") == "output_text"))
    if (set(review) != {"annotation", "evidence", "reasoning"} or review["annotation"] not in base.LABELS
            or not isinstance(review["reasoning"], str) or not review["reasoning"].strip()):
        raise ValueError("Invalid review shape")
    evidence = validate_evidence(review["evidence"])
    payload = json.loads(packet["body"]["input"][0]["content"])
    supplied = {"main": payload["pages"], **{doc["source"]: doc["pages"] for doc in payload["supporting_sources"]}}
    for item in evidence:
        document = packet["documents"].get(item["source"])
        if document is None:
            raise ValueError("Evidence cites a source not supplied")
        location = re.fullmatch(document["unit"] + r" ([1-9][0-9]*)", item["location"])
        number = int(location.group(1)) if location else 0
        if not 1 <= number <= len(supplied[item["source"]]):
            raise ValueError("Evidence location does not identify a supplied source page/segment")
        if normalized(item["quote"]) not in supplied[item["source"]][number - 1]["text"]:
            raise ValueError("Evidence quote does not match its exact supplied source page/segment")
        validate_source_quotes([dict(item, source="main")], document)
    return review


def process(packet, client_info, retry_failed=False, cached_only=False):
    key = packet["article_id"]
    paths = sorted((RUN / "attempts").glob(key + "__*.json"))
    previous = json.loads(paths[-1].read_text()) if paths else None
    if previous and previous["request_sha256"] != packet["request_sha256"]:
        raise ValueError("Previous attempt has different input")
    if previous and "response" in previous and not retry_failed:
        attempt, path = previous, paths[-1]
    elif cached_only or (previous and not retry_failed):
        print(f"No response to revalidate or retry not authorized: {key}")
        return
    else:
        with STATE_LOCK:
            for saved in (RUN / "attempts").glob("*.json"):
                response = json.loads(saved.read_text()).get("response")
                if response and response.get("service_tier") != "flex":
                    raise ValueError("Unexpected returned service tier requires review before more requests")
            actual, uncertain = spending()
            if actual + uncertain + packet["reserved_usd"] > base.BUDGET:
                raise ValueError("Cumulative $100 budget would be exceeded")
            path = RUN / "attempts" / f"{key}__{len(paths) + 1:03d}.json"
            if path.exists():
                raise ValueError("Article already reserved")
            attempt = {"article_id": key, "request_sha256": packet["request_sha256"],
                       "started_at": base.now(), "status": "submitted", "reserved_usd": packet["reserved_usd"],
                       "requested_service_tier": "flex", "organization_id": client_info[1]["organization_id"],
                       "account_verification_sha256": base.digest(base.ACCOUNT.read_bytes())}
            base.save_json(path, attempt)
        try:
            response = client_info[0].responses.create(**packet["body"])
            attempt.update(response=response.model_dump(mode="json"), received_at=base.now(),
                           request_id=getattr(response, "_request_id", None), status="received")
            base.save_json(path, attempt)  # Preserve billed usage before validation.
        except Exception as error:
            attempt.update(status="request_failed", error_type=type(error).__name__,
                           http_status=getattr(error, "status_code", None), request_id=getattr(error, "request_id", None))
            base.save_json(path, attempt)
            print(f"Request failed: {key}; no automatic retry or standard fallback")
            return
    try:
        response = attempt["response"]
        if response.get("service_tier") != "flex":
            raise ValueError("Returned service tier is not flex")
        if not response.get("model") or not response.get("id") or usage_cost(response) is None:
            raise ValueError("Response lacks model, identifier or usage")
        for document in packet["documents"].values():
            if (base.digest(Path(document["fulltext_path"]).read_bytes()) != document["source_sha256"]
                    or base.digest(Path(document["text_cache"]).read_bytes()) != document["text_cache_sha256"]):
                raise ValueError("Source changed during request")
        review = validate_review(response, packet)
        result = {"article_id": key, **review, "reviewed_at": base.now(), "reviewer": "api_flex_recheck",
                  "model": response["model"], "service_tier": response["service_tier"],
                  "response_id": response["id"], "request_sha256": packet["request_sha256"],
                  "prompt_sha256": packet["prompt_sha256"], "input_sha256": packet["input_sha256"],
                  "sources": packet["documents"], "status": "pending_adjudication", "human_verified": False}
        base.save_json(RUN / "results" / (key + ".json"), result)
        attempt.update(status="validated", validation="passed")
        attempt.pop("validation_error", None)
        print(f"Saved recheck for adjudication: {key}")
    except (ValueError, KeyError, TypeError) as error:
        attempt.update(status="needs_review", validation="failed", validation_error=str(error))
        print(f"Validation pending: {key}; raw response retained")
    attempt.update(actual_usd=usage_cost(attempt["response"]),
                   returned_service_tier=attempt["response"].get("service_tier"))
    base.save_json(path, attempt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--prepare", action="store_true", help="Default: freeze inputs and estimate only")
    modes.add_argument("--run", action="store_true", help="Make authorized Flex requests; never fall back to standard")
    modes.add_argument("--revalidate", action="store_true", help="Validate saved responses without paid or network calls")
    parser.add_argument("--sources", type=Path, default=RUN / "sources.json")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--retry-failed", action="store_true", help="Explicitly authorize new Flex attempts for unsuccessful prior requests")
    args = parser.parse_args()
    if args.workers < 1 or (args.limit is not None and args.limit < 1):
        parser.error("workers and limit must be positive")
    if args.retry_failed and not args.run:
        parser.error("--retry-failed requires --run")
    RUN.mkdir(parents=True, exist_ok=True)
    # Share the historical runner lock so both cannot reserve the same budget.
    with (base.RUN / "runner.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        articles = index_rows(read_rows(base.PRIVATE / "articles.csv"))
        sources = index_rows(read_rows(base.PRIVATE / "fulltext.csv"))
        packets = prepare(args.sources, articles, sources, args.run or args.revalidate)
        pending = [packet for packet in packets if not (RUN / "results" / (packet["article_id"] + ".json")).exists()]
        actual, uncertain = spending()
        if not args.run and not args.revalidate:
            print(f"Prepared {len(packets)} rechecks; {len(pending)} pending. No API calls.")
            print(f"Pending Flex estimate with maximum output: ${sum(p['estimated_flex_max_usd'] for p in pending):.2f}.")
            print(f"Cumulative ledger: ${actual:.4f} known; ${uncertain:.4f} uncertain; limit $100.")
            return
        selected = pending[:args.limit] if args.limit else pending
        client_info = base.verified_client() if args.run and selected else None
        try:
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                futures = [pool.submit(process, packet, client_info, args.retry_failed, args.revalidate) for packet in selected]
                for future in as_completed(futures):
                    future.result()
        finally:
            if client_info:
                client_info[0].close()
            actual, uncertain = spending()
            print(f"Cumulative ledger: ${actual:.4f} known; ${uncertain:.4f} uncertain; limit $100.")


if __name__ == "__main__":
    main()
