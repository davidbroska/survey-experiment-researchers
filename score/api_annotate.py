"""Prepare remaining full-text reviews; make paid requests only with --run.

One independent article per request. Requests, responses and spending stay private.
Session workers must remain paused while this runner owns the pending manifest.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import fcntl
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import re
import subprocess
import threading

from annotate import PRIVATE, PROMPT, ROOT, LABELS, fulltext_prompt
from review import index_rows, read_rows, validate_evidence, validate_source_quotes, write_rows
from source_review import normalized, source_pages

RUN = PRIVATE / "api_fulltext"
MANIFEST = PRIVATE / "api_fulltext_manifest.json"
BATCHES = PRIVATE / "annotation_batches"
DESTINATION = BATCHES / "fulltext_api.csv"
ACCOUNT = PRIVATE / "api_account_verification.json"
MODEL = "gpt-6-astra"
MAX_OUTPUT = 12000
BUDGET = 100.0
EXPECTED_PENDING = 69
RATES = {"input": 10.0, "cache_write": 12.5, "cached_input": 1.0, "output": 50.0}
STATE_LOCK = threading.Lock()


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def serialized(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def save_json(path, value):
    """Replace atomically so a received response survives a later validation error."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def completed_ids():
    """Read identifiers only; never include previous labels in model inputs."""
    ids = []
    for path in sorted(BATCHES.glob("fulltext_*.csv")):
        with path.open(newline="", encoding="utf-8-sig") as handle:
            ids.extend(row["article_id"] for row in csv.DictReader(handle))
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate initial full-text reviews already exist")
    return set(ids)


def response_schema(unit):
    prefix = "PDF page" if unit == "PDF page" else "text segment"
    return {"type": "json_schema", "name": "source_review", "strict": True,
            "schema": {"type": "object", "additionalProperties": False,
                       "required": ["annotation", "evidence", "reasoning"],
                       "properties": {
                           "annotation": {"type": "string", "enum": list(LABELS)},
                           "reasoning": {"type": "string"},
                           "evidence": {"type": "array", "items": {
                               "type": "object", "additionalProperties": False,
                               "required": ["quote", "location", "source"],
                               "properties": {
                                   "quote": {"type": "string"},
                                   "location": {"type": "string",
                                                "description": f"Exactly '{prefix} N', using the supplied page_or_segment number, not printed pagination.",
                                                "pattern": f"^{prefix} [1-9][0-9]*$"},
                                   "source": {"type": "string", "enum": ["main"]}}}}}}}


def make_packet(article, access):
    if digest(Path(access["fulltext_path"]).read_bytes()) != access["source_sha256"]:
        raise ValueError("Source file changed")
    pages, unit = source_pages(access)
    pages = [normalized(page) for page in pages]
    if not pages or not any(pages):
        raise ValueError("Source has no extractable text")
    instructions, payload = fulltext_prompt(article, pages)
    body = {"model": MODEL, "instructions": instructions,
            "input": [{"role": "user", "content": payload}],
            "reasoning": {"effort": "medium"}, "service_tier": "default",
            "store": False, "max_output_tokens": MAX_OUTPUT,
            "truncation": "disabled", "text": {"format": response_schema(unit)}}
    # Reserve all input at the highest input rate, including cache writes.
    estimated_input = math.ceil(len(serialized(body)) / 3)
    return {"article_id": article["article_id"], "journal_title": article["journal"],
            "title": article["title"], "version_note": access.get("version_note", ""),
            "source_format": access["format"], "unit": unit,
            "source_sha256": access["source_sha256"],
            "text_cache_sha256": digest(Path(access["text_cache"]).read_bytes()),
            "prompt_sha256": digest(PROMPT.read_bytes()),
            "instructions_sha256": digest(instructions.encode()),
            "input_sha256": digest(payload.encode()),
            "request_sha256": digest(serialized(body).encode()),
            "pages_or_segments_supplied": list(range(1, len(pages) + 1)),
            "estimated_input_tokens": estimated_input,
            "reserved_usd": (estimated_input * max(RATES["input"], RATES["cache_write"])
                             + MAX_OUTPUT * RATES["output"]) / 1_000_000,
            "body": body}


def prepare(articles, sources):
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text())
    assigned = []
    for path in sorted(BATCHES.glob("fulltext_*.json")):
        assigned.extend(json.loads(path.read_text()))
    if len(assigned) != len(set(assigned)):
        raise ValueError("Duplicate full-text assignments")
    ids = [key for key in assigned if key not in completed_ids()]
    if len(ids) != EXPECTED_PENDING:
        raise ValueError(f"Expected {EXPECTED_PENDING} pending articles; found {len(ids)}")
    entries = []
    for key in ids:
        packet = make_packet(articles[key], sources[key])
        save_json(RUN / "requests" / (key + ".json"), packet)
        entries.append({name: value for name, value in packet.items() if name != "body"})
    manifest = {"created_at": now(), "model": MODEL, "reasoning_effort": "medium",
                "service_tier": "default", "max_output_tokens": MAX_OUTPUT,
                "budget_usd": BUDGET, "rates_per_million_usd": RATES,
                "token_estimate": "ceil(serialized request characters / 3); all input reserved at cache-write rate",
                "prompt_sha256": digest(PROMPT.read_bytes()), "articles": entries}
    save_json(MANIFEST, manifest)
    return manifest


def load_packet(entry, article, source):
    packet = json.loads((RUN / "requests" / (entry["article_id"] + ".json")).read_text())
    current = make_packet(article, source)
    if current != packet or {k: v for k, v in packet.items() if k != "body"} != entry:
        raise ValueError("Prepared request, prompt, metadata or source changed; refusing to send")
    return packet


def usage_cost(response):
    usage = response.get("usage")
    if not usage or not all(isinstance(usage.get(k), int) for k in ["input_tokens", "output_tokens"]):
        return None
    incoming, outgoing = usage["input_tokens"], usage["output_tokens"]
    details = usage.get("input_tokens_details") or {}
    cached = details.get("cached_tokens", 0)
    written = details.get("cache_write_tokens", 0)
    if (not isinstance(cached, int) or not isinstance(written, int)
            or min(cached, written, incoming, outgoing) < 0 or cached + written > incoming):
        raise ValueError("Invalid token usage in response")
    return ((incoming - cached - written) * RATES["input"] + cached * RATES["cached_input"]
            + written * RATES["cache_write"]
            + outgoing * RATES["output"]) / 1_000_000


def refresh_prices():
    """Migrate accounting only; preserve every prepared request and raw response."""
    manifest = json.loads(MANIFEST.read_text())
    changes = {"refreshed_at": now(), "previous_rates": manifest["rates_per_million_usd"],
               "rates_per_million_usd": RATES, "attempts": []}
    reservations = {}
    for entry in manifest["articles"]:
        path = RUN / "requests" / (entry["article_id"] + ".json")
        packet = json.loads(path.read_text())
        if digest(serialized(packet["body"]).encode()) != packet["request_sha256"]:
            raise ValueError("Prepared request hash changed; accounting refresh refused")
        reserve = (packet["estimated_input_tokens"] * max(RATES["input"], RATES["cache_write"])
                   + packet["body"]["max_output_tokens"] * RATES["output"]) / 1_000_000
        packet["reserved_usd"] = entry["reserved_usd"] = reserve
        reservations[entry["article_id"]] = reserve
        save_json(path, packet)
    for path in sorted((RUN / "attempts").glob("*.json")):
        attempt = json.loads(path.read_text())
        changes["attempts"].append({"file": path.name, "previous_reserved_usd": attempt["reserved_usd"],
                                    "previous_actual_usd": attempt.get("actual_usd")})
        attempt["reserved_usd"] = reservations[attempt["article_id"]]
        cost = usage_cost(attempt.get("response", {}))
        if cost is not None:
            attempt["actual_usd"] = cost
        save_json(path, attempt)
    history_path = RUN / "pricing_migrations.json"
    history = json.loads(history_path.read_text()) if history_path.exists() else []
    save_json(history_path, history + [changes])
    manifest.update(rates_per_million_usd=RATES, pricing_refreshed_at=changes["refreshed_at"],
                    token_estimate="ceil(serialized request characters / 3); all input reserved at cache-write rate")
    save_json(MANIFEST, manifest)
    actual, uncertain = spending()
    print(f"Accounting refreshed without API calls: ${actual:.4f} known usage; ${uncertain:.4f} uncertain reservations.")


def spending():
    actual, reserved = 0.0, 0.0
    for path in (RUN / "attempts").glob("*.json"):
        attempt = json.loads(path.read_text())
        cost = usage_cost(attempt.get("response", {}))
        if cost is None:
            reserved += attempt["reserved_usd"]
        else:
            actual += cost
    return actual, reserved


def verified_client():
    """Read only the named workspace key and verify it without printing it."""
    receipt = json.loads(ACCOUNT.read_text())
    if (receipt.get("key_variable") != "OPEN_AI_API_KEY"
            or receipt.get("organization_title") != "Politics and Social Change Lab"
            or receipt.get("model_listed") != MODEL or not receipt.get("organization_id")):
        raise ValueError("Lab account verification receipt does not match this run")
    values = []
    for line in (ROOT.parent / ".env").read_text().splitlines():
        match = re.match(r"^\s*(?:export\s+)?OPEN_AI_API_KEY\s*=\s*(.*?)\s*$", line)
        if match:
            values.append(match.group(1).strip().strip("\"'"))
    if len(values) != 1 or not hmac.compare_digest(digest(values[0].encode()), receipt["key_sha256"]):
        raise ValueError("Workspace lab key does not match verified fingerprint")
    from openai import OpenAI
    import httpx
    # Explicit base URL/project prevents inherited environment routing overrides.
    client = OpenAI(api_key=values[0], organization=receipt["organization_id"], project="",
                    base_url="https://api.openai.com/v1", max_retries=0, timeout=900,
                    http_client=httpx.Client(trust_env=False, follow_redirects=False))
    client.project = None  # Omit the project header; retain the key's verified organization.
    return client, receipt


def apply_evidence_corrections(review, packet):
    """Apply explicit source-checked formatting edits, never labels or reasoning."""
    path = RUN / "evidence_corrections.json"
    if not path.exists():
        return {}
    corrections = json.loads(path.read_text())
    if not isinstance(corrections, list):
        raise ValueError("Evidence corrections must be a list")
    applied = {}
    for correction in corrections:
        if correction.get("article_id") != packet["article_id"]:
            continue
        index = correction["evidence_index"]
        if (type(index) is not int or not 0 <= index < len(review["evidence"]) or index in applied
                or correction["source_sha256"] != packet["source_sha256"]
                or any(not isinstance(correction.get(key), str) or not correction[key].strip()
                       for key in ["original_quote", "quote", "reviewer", "reviewed_at", "reason"])):
            raise ValueError("Invalid or duplicate evidence correction")
        datetime.fromisoformat(correction["reviewed_at"])
        original, replacement = correction["original_quote"], correction["quote"]
        if (review["evidence"][index]["quote"] != original
                or (replacement not in original and replacement.replace("-", "") != original.replace("-", ""))):
            raise ValueError("Correction must match the original and only shorten it or change hyphens")
        review["evidence"][index]["quote"] = replacement
        applied[index] = {"record": correction, "corrections_file_sha256": digest(path.read_bytes())}
    return applied


def parse_review(response, packet, source, evidence_checks=None):
    if response.get("status") != "completed":
        raise ValueError("API response is incomplete or failed")
    texts = []
    for item in response.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "refusal":
                raise ValueError("API refused the request")
            if content.get("type") == "output_text":
                texts.append(content["text"])
    review = json.loads("".join(texts))
    if (not isinstance(review, dict) or set(review) != {"annotation", "evidence", "reasoning"}
            or review["annotation"] not in LABELS
            or not isinstance(review["reasoning"], str) or not review["reasoning"].strip()):
        raise ValueError("Invalid review shape")
    validate_evidence(review["evidence"])
    corrections = apply_evidence_corrections(review, packet)
    evidence = validate_evidence(review["evidence"])
    supplied = json.loads(packet["body"]["input"][0]["content"])["pages"]
    prefix = "PDF page" if packet["unit"] == "PDF page" else "text segment"
    for index, item in enumerate(evidence):
        location = re.fullmatch(prefix + r" ([1-9][0-9]*)", item["location"])
        if item["source"] != "main" or not location:
            raise ValueError("Evidence must cite a numbered supplied main-source page")
        number = int(location.group(1))
        if number > len(supplied):
            raise ValueError("Evidence cites a page outside the supplied source")
        page_text = supplied[number - 1]["text"]
        method = "supplied_page"
        if normalized(item["quote"]) not in page_text:
            # PDF layout extraction can interleave two columns. Check the same
            # numbered source page in reading order, without changing the quote.
            if source["format"].lower() != "pdf":
                raise ValueError("Evidence quote does not match its cited supplied page")
            try:
                page_text = normalized(subprocess.check_output(
                    ["pdftotext", "-f", str(number), "-l", str(number), source["fulltext_path"], "-"],
                    text=True, stderr=subprocess.PIPE))
            except (OSError, subprocess.CalledProcessError) as error:
                raise ValueError("Could not extract cited PDF page in reading order") from error
            if normalized(item["quote"]) not in page_text:
                raise ValueError("Evidence quote does not match its cited PDF page in either extraction order")
            method = "same_pdf_page_reading_order"
        if evidence_checks is not None:
            evidence_checks.append({"evidence_index": index, "location": item["location"],
                                    "method": method, "page_text_sha256": digest(page_text.encode()),
                                    "correction": corrections.get(index)})
    validate_source_quotes(evidence, source)
    return review


def commit(review, response, packet):
    rows = read_rows(DESTINATION)
    existing = index_rows(rows)
    key = packet["article_id"]
    if key in existing:
        return
    if key in completed_ids():
        raise ValueError("Article was completed by another reviewer during the API run")
    row = {"article_id": key, "annotation": review["annotation"],
           "evidence": json.dumps(review["evidence"], ensure_ascii=False),
           "reasoning": review["reasoning"], "reviewer": "fulltext_api",
           "model": response["model"], "reviewed_at": now(),
           "prompt_sha256": packet["prompt_sha256"],
           "instructions_sha256": packet["instructions_sha256"],
           "source_sha256": packet["source_sha256"], "source_format": packet["source_format"],
           "pages_or_segments_read": "", "human_verified": "false",
           "pages_or_segments_supplied": ",".join(map(str, packet["pages_or_segments_supplied"])),
           "input_sha256": packet["input_sha256"], "request_sha256": packet["request_sha256"],
           "response_id": response["id"], "review_method": "api_main_text"}
    if rows and list(rows[0]) != list(row):
        raise ValueError("Unexpected API CSV schema")
    write_rows(DESTINATION, rows + [row], list(row))


def process(entry, article, source, client_info, retry_failed, cached_only=False):
    packet = load_packet(entry, article, source)
    paths = sorted((RUN / "attempts").glob(packet["article_id"] + "__*.json"))
    previous = json.loads(paths[-1].read_text()) if paths else None
    if previous and previous["request_sha256"] != packet["request_sha256"]:
        raise ValueError("Attempt belongs to a different request")
    if cached_only and (not previous or "response" not in previous):
        print(f"No saved response to revalidate: {packet['article_id']}")
        return client_info, False
    cached = previous and "response" in previous and (previous.get("validation") != "failed" or cached_only)
    if previous and not cached and not retry_failed:
        print(f"Pending failed/uncertain attempt: {packet['article_id']} (no automatic retry)")
        return client_info, False
    if cached:
        attempt, path = previous, paths[-1]
    else:
        if client_info is None:
            client_info = verified_client()
        client, account = client_info
        with STATE_LOCK:
            actual, uncertain = spending()
            if actual + uncertain + packet["reserved_usd"] > BUDGET:
                raise ValueError("$100 run budget would be exceeded by the next reservation")
            path = RUN / "attempts" / f"{packet['article_id']}__{len(paths) + 1:03d}.json"
            if path.exists():
                raise ValueError("An attempt for this article was reserved concurrently")
            attempt = {"article_id": packet["article_id"], "started_at": now(),
                       "request_sha256": packet["request_sha256"], "reserved_usd": packet["reserved_usd"],
                       "status": "submitted", "organization_id": account["organization_id"],
                       "account_verification_sha256": digest(ACCOUNT.read_bytes())}
            save_json(path, attempt)
        try:
            response = client.responses.create(**packet["body"])
            attempt.update(response=response.model_dump(mode="json"), received_at=now(),
                           request_id=getattr(response, "_request_id", None), status="received")
            save_json(path, attempt)  # Persist usage even when output fails validation.
        except Exception as error:
            attempt.update(status="request_failed", failed_at=now(), error_type=type(error).__name__,
                           http_status=getattr(error, "status_code", None),
                           request_id=getattr(error, "request_id", None))
            save_json(path, attempt)
            print(f"Request failed: {packet['article_id']} ({type(error).__name__}); reservation retained")
            return client_info, True
    # Keep the original failure alongside subsequent validation decisions.
    history = attempt.setdefault("validation_history", [])
    if attempt.get("validation") and not history:
        history.append({"result": attempt["validation"], "error": attempt.get("validation_error"),
                        "validator": "original_supplied_page_check"})
    evidence_checks = []
    try:
        response = attempt["response"]
        review = parse_review(response, packet, source, evidence_checks)
        if not response.get("model") or not response.get("id") or usage_cost(response) is None:
            raise ValueError("Response lacks model, identifier or token usage")
        load_packet(entry, article, source)  # Reject source changes while the request was running.
        with STATE_LOCK:
            commit(review, response, packet)
        attempt.update(validation="passed", status="committed", committed_at=now(),
                       actual_usd=usage_cost(response), needs_support_review=review["annotation"] == "UNCLEAR")
        attempt.pop("validation_error", None)
        print(f"Saved {packet['article_id']}; response cost ${attempt['actual_usd']:.4f}")
    except (ValueError, KeyError, TypeError) as error:
        attempt.update(validation="failed", status="needs_review", validation_error=str(error),
                       actual_usd=usage_cost(attempt["response"]))
        print(f"Validation pending: {packet['article_id']} ({type(error).__name__}); raw response retained")
    history.append({"checked_at": now(), "result": attempt["validation"],
                    "error": attempt.get("validation_error"), "validator": "same_page_reading_order_v1",
                    "response_sha256": digest(serialized(attempt["response"]).encode()),
                    "source_sha256": packet["source_sha256"], "evidence_checks": evidence_checks})
    save_json(path, attempt)
    return client_info, True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--prepare", action="store_true", help="Freeze requests and estimate costs; default, no API calls")
    modes.add_argument("--run", action="store_true", help="Send prepared requests using the verified lab key")
    modes.add_argument("--refresh-prices", action="store_true", help="Update accounting from stored usage without changing requests or making API calls")
    modes.add_argument("--revalidate", action="store_true", help="Recheck saved responses only; no key access or API calls")
    parser.add_argument("--limit", type=int, help="Maximum pending articles selected before processing")
    parser.add_argument("--workers", type=int, default=1, help="Concurrent independent requests; default 1")
    parser.add_argument("--retry-failed", action="store_true", help="Explicitly allow new paid attempts for failed/uncertain prior requests")
    parser.add_argument("--allow-standard-paid", action="store_true", help="Override the Flex preference only with explicit user authorization for standard-tier spending")
    args = parser.parse_args()
    if args.run and not args.allow_standard_paid:
        parser.error("New paid work uses Flex. Use api_recheck.py; standard requests require --allow-standard-paid and explicit user authorization.")
    if args.allow_standard_paid and not args.run:
        parser.error("--allow-standard-paid requires --run")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if args.workers < 1:
        parser.error("--workers must be positive")
    if args.retry_failed and not args.run:
        parser.error("--retry-failed requires --run")
    RUN.mkdir(parents=True, exist_ok=True)
    with (RUN / "runner.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.refresh_prices:
            refresh_prices()
            return
        articles = index_rows(read_rows(PRIVATE / "articles.csv"))
        sources = index_rows(read_rows(PRIVATE / "fulltext.csv"))
        if (args.run or args.revalidate) and not MANIFEST.exists():
            raise ValueError("Run --prepare before authorizing requests with --run")
        manifest = prepare(articles, sources)
        if (manifest["prompt_sha256"] != digest(PROMPT.read_bytes()) or manifest["model"] != MODEL
                or manifest["budget_usd"] != BUDGET or manifest["rates_per_million_usd"] != RATES):
            raise ValueError("Frozen manifest settings differ")
        ids = [entry["article_id"] for entry in manifest["articles"]]
        if len(ids) != EXPECTED_PENDING or len(ids) != len(set(ids)) or not set(ids) <= articles.keys():
            raise ValueError("Frozen manifest must contain exactly the original 69 distinct articles")
        done = completed_ids()
        pending = [entry for entry in manifest["articles"] if entry["article_id"] not in done]
        if not args.run and not args.revalidate:
            for entry in pending:
                load_packet(entry, articles[entry["article_id"]], sources[entry["article_id"]])
            reserve = sum(entry["reserved_usd"] for entry in pending)
            incoming = sum(entry["estimated_input_tokens"] for entry in pending)
            print(f"Prepared {len(manifest['articles'])} articles; {len(pending)} pending.")
            print(f"Estimated input: {incoming:,} tokens; cache-write input + maximum output reservation: ${reserve:.2f}.")
            print("No API calls made. Paid execution requires --run; cumulative hard stop is $100.")
            return
        selected = pending[:args.limit] if args.limit else pending
        client_info = None
        try:
            if selected and args.run:
                client_info = verified_client()
            errors = []
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                futures = {pool.submit(process, entry, articles[entry["article_id"]],
                                       sources[entry["article_id"]], client_info, args.retry_failed,
                                       args.revalidate): entry["article_id"]
                           for entry in selected}
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as error:
                        errors.append(futures[future])
                        print(f"Article stopped: {futures[future]} ({type(error).__name__})")
            if errors:
                raise ValueError(f"{len(errors)} articles stopped; inspect the ledger before resuming")
        finally:
            if client_info is not None:
                client_info[0].close()
            actual, uncertain = spending()
            print(f"Run ledger: ${actual:.4f} known usage; ${uncertain:.4f} reserved for uncertain attempts.")


if __name__ == "__main__":
    main()
