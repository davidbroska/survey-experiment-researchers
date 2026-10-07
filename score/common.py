"""Small file helpers and read-only Scopus credentials; never save request headers."""
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://api.elsevier.com/content/search/scopus"
csv.field_size_limit(sys.maxsize)


def now():
    return datetime.now(timezone.utc).isoformat()


def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fields=None):
    rows = list(rows)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or list(rows[0]), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def credentials():
    values = dict(os.environ)
    env = ROOT.parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            key, separator, value = line.partition("=")
            if separator and key.strip() in {"SCOPUS_API_KEY", "SCOPUS_INSTTOKEN"}:
                values.setdefault(key.strip(), value.strip().strip("\"'"))
    if not values.get("SCOPUS_API_KEY"):
        raise RuntimeError("Set SCOPUS_API_KEY in the environment or project .env")
    headers = {"Accept": "application/json", "X-ELS-APIKey": values["SCOPUS_API_KEY"]}
    if values.get("SCOPUS_INSTTOKEN"):
        headers["X-ELS-Insttoken"] = values["SCOPUS_INSTTOKEN"]
    return headers
