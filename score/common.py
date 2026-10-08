"""Private provider settings; never print credentials or save request headers."""
import os
from pathlib import Path
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parent.parent
PRIVATE_QUERY = r'^(code|state|expires|googleaccessid|view_only)$|key|token|signature|credential|authorization|email|x-amz-'


def safe_url(url):
    """Remove credentials and signed-download parameters from saved URLs."""
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not re.search(PRIVATE_QUERY, k, re.I)]
    return urlunsplit((parts.scheme, parts.netloc.rsplit('@', 1)[-1], parts.path, urlencode(query), ''))



def settings():
    """Read only the access settings used by this project; never print their values."""
    names = {'SCOPUS_API_KEY', 'SCOPUS_INSTTOKEN', 'WILEY_API_KEY', 'WILEY_TDM_TOKEN',
             'OPEN_ALEX', 'OPENALEX_API_KEY', 'UNPAYWALL_EMAIL'}
    values = dict(os.environ)
    env = ROOT.parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            key, separator, value = line.partition("=")
            if separator and key.strip() in names:
                values.setdefault(key.strip(), value.strip().strip("\"'"))
    return {key: values.get(key, '') for key in names}


def credentials():
    values = settings()
    if not values.get("SCOPUS_API_KEY"):
        raise RuntimeError("Set SCOPUS_API_KEY in the environment or project .env")
    headers = {"Accept": "application/json", "X-ELS-APIKey": values["SCOPUS_API_KEY"]}
    if values.get("SCOPUS_INSTTOKEN"):
        headers["X-ELS-Insttoken"] = values["SCOPUS_INSTTOKEN"]
    return headers
