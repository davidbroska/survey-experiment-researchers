"""Exact phrase families and a punctuation-aware local verification layer.

The local matcher is deliberately stricter than database retrieval. It is not
an emulator of Scopus stemming, indexed keywords, or proximity semantics.
"""
import re
import unicodedata
from common import ROOT, write_csv, write_json

START_YEAR, END_YEAR = 2010, 2026
LIMITS = f"SRCTYPE(j) AND DOCTYPE(ar) AND PUBYEAR > {START_YEAR-1} AND PUBYEAR < {END_YEAR+1}"
CONTEXT = "survey* OR questionnaire* OR respondent*"
RANDOM = "random* OR experiment*"
BASELINE = ["survey experiment*", "survey-based experiment*", "survey-embedded experiment*",
            "vignette experiment*", "experimental vignette*", "vignette-based experiment*",
            "framing experiment*", "information provision experiment*", "survey-experimental",
            "vignette-based survey*", "scenario-based experiment*"]


def number(*phrases):
    return [v for p in phrases for v in (p, p + "s")]


FAMILIES = [
    {"id": "survey_design", "phrases": number("survey experiment", "survey-based experiment",
        "survey based experiment", "survey-embedded experiment", "survey embedded experiment")
        + ["survey-experimental", "survey experimental"], "role": "core"},
    {"id": "vignette_design", "phrases": number("vignette experiment", "experimental vignette",
        "vignette-based experiment", "vignette based experiment"), "role": "core"},
    {"id": "contextual_design", "phrases": number("framing experiment", "information provision experiment",
        "information-provision experiment", "scenario-based experiment", "scenario based experiment"),
        "context": True, "role": "guarded_original"},
    {"id": "vignette_survey", "phrases": number("vignette-based survey", "vignette based survey"),
        "random": True, "role": "guarded_original"},
    {"id": "embedded_design", "phrases": [
        "experiment embedded in a survey", "experiments embedded in a survey",
        "experiment embedded in an online survey", "experiments embedded in an online survey",
        "experiment embedded in a national survey", "experiments embedded in national surveys",
        "experiment embedded in a nationally representative survey",
        "experiments embedded in nationally representative surveys",
        "embedded survey experiment", "embedded survey experiments",
        "survey with an embedded experiment", "survey with embedded experiments",
        "surveys with embedded experiments"],
        "context": True, "role": "expansion"},
    {"id": "factorial_randomized_vignette", "phrases": number("factorial survey", "factorial vignette experiment",
        "randomized vignette experiment", "randomised vignette experiment")
        + ["randomized vignette", "randomized vignettes", "randomised vignette", "randomised vignettes"],
        "role": "expansion"},
    {"id": "text_assignment", "phrases": ["randomly assigned to read", "randomly allocated to read",
        "randomly selected to read", "randomized to read", "randomised to read",
        "randomly assigned to a vignette", "randomly assigned a vignette",
        "randomly assigned to one of two vignettes", "randomly assigned to one of three vignettes",
        "randomly assigned to receive information", "randomly provided with information",
        "randomly presented with a vignette", "randomly presented with vignettes",
        "randomly presented with a scenario", "randomly shown a vignette"],
        "context": True, "role": "expansion"},
    {"id": "survey_information", "phrases": number("information treatment", "informational treatment"),
        "context": True, "random": True, "role": "expansion"},
    {"id": "survey_wording", "phrases": number("question wording experiment", "question-wording experiment",
        "wording experiment"),
        "context": True, "role": "expansion"},
]


def clause(family):
    parts = ["TITLE-ABS-KEY(" + " OR ".join("{" + p + "}" for p in family["phrases"]) + ")"]
    if family.get("context"):
        context = CONTEXT + (" OR participant*" if family.get("participant_context") else "")
        parts.append("TITLE-ABS-KEY(" + context + ")")
    if family.get("random"):
        parts.append("TITLE-ABS-KEY(" + RANDOM + ")")
    return "(" + " AND ".join(parts) + ")"


def build(families=None, limits=True):
    body = "(\n  " + "\n  OR ".join(clause(f) for f in (FAMILIES if families is None else families)) + "\n)"
    return body + ("\nAND " + LIMITS if limits else "")


def baseline_query():
    return "TITLE-ABS-KEY(" + " OR ".join('"'+p+'"' for p in BASELINE) + ") AND " + LIMITS


def groups():
    """Equivalent union of short queries, avoiding the API gateway URL limit."""
    result, current = [], []
    for family in FAMILIES:
        if current and len(build(current + [family])) > 1800:
            result.append(build(current))
            current = []
        current.append(family)
    if current:
        result.append(build(current))
    return result


def normalize(text):
    text = unicodedata.normalize("NFKC", text).casefold()
    text = re.sub("[‐‑‒–—−]", "-", text)
    return re.sub(r"\s+", " ", text)


def phrase_rx(phrase):
    return re.compile(r"(?<!\w)" + re.escape(normalize(phrase)).replace(r"\ ", r"\s+") + r"(?!\w)")


PATTERNS = {f["id"]: [(p, phrase_rx(p)) for p in f["phrases"]] for f in FAMILIES}
CONTEXT_RX = re.compile(r"\b(?:surveys?|surveyed|questionnaires?|respondents?)\b")
PARTICIPANT_CONTEXT_RX = re.compile(r"\b(?:surveys?|surveyed|questionnaires?|respondents?|participants?)\b")
RANDOM_RX = re.compile(r"\b(?:random\w*|experiment\w*)\b")
TEXT_RX = re.compile(r"\b(?:vignettes?|read|reading|text(?:ual)?|written|wording|information(?:al)? treatments?|messages?)\b")
DESIGN_REVIEW_RX = re.compile(r"\bconjoint\b|\bsplit[\W_]+ballots?\b")
PANEL_PATTERNS = {
    "Prolific": re.compile(r"\bprolific(?:\s+(?:academic|participants|panel|platform|sample|respondents))?\b"),
    "Bovitz": re.compile(r"\b(?:bovitz|forthright)\b"),
    "Amazon Mechanical Turk": re.compile(r"\b(?:mturk|mechanical turk)\b"),
    "Lucid": re.compile(r"\blucid\b"), "Cint": re.compile(r"\bcint\b"),
    "Dynata": re.compile(r"\bdynata\b"), "YouGov": re.compile(r"\byougov\b"),
    "Qualtrics panel": re.compile(r"\bqualtrics\s+(?:panel|panels|research services)\b"),
}


def design_review_cue(row):
    return any(DESIGN_REVIEW_RX.search(normalize(row.get(field, "") or ""))
               for field in ("title", "abstract", "keywords", "indexed_keywords"))


def panel_cues(row):
    """Provider mentions are review cues, not proof of recruitment or data access."""
    text = normalize((row.get("title", "") or "") + " " + (row.get("abstract", "") or ""))
    return sorted(name for name, pattern in PANEL_PATTERNS.items() if pattern.search(text))


def units(row):
    # Never concatenate a title with an abstract or separate keyword entries.
    for field in ("title", "abstract", "keywords", "indexed_keywords"):
        for unit in re.split(r"[.!?;|\n]+", row.get(field, "") or ""):
            if unit.strip():
                yield field, normalize(unit), unit.strip()


def match(row, families=None):
    selected = FAMILIES if families is None else families
    patterns = PATTERNS if families is None else {
        f["id"]: [(p, phrase_rx(p)) for p in f["phrases"]] for f in selected}
    hits = []
    for field, unit, original in units(row):
        for family in selected:
            context_rx = PARTICIPANT_CONTEXT_RX if family.get("participant_context") else CONTEXT_RX
            if family.get("context") and not context_rx.search(unit):
                continue
            if family.get("random") and not RANDOM_RX.search(unit):
                continue
            for phrase, rx in patterns[family["id"]]:
                if rx.search(unit):
                    hits.append({"family": family["id"], "field": field,
                                 "phrase": phrase, "evidence": original})
                    break
    return hits


def baseline_match(row, punctuation_blind=False):
    for field in ("title", "abstract", "keywords", "indexed_keywords"):
        text = normalize(row.get(field, ""))
        text = re.sub(r"[^\w\s]", " ", text) if punctuation_blind else text.replace("-", " ")
        for p in BASELINE:
            pattern = r"\b" + re.escape(p.replace("-", " ")).replace(r"\ ", r"\s+").replace(r"\*", r"\w*") + r"\b"
            if re.search(pattern, text):
                return True
    return False


def write_queries():
    target = ROOT / "queries"
    target.mkdir(exist_ok=True)
    (target / "recommended.txt").write_text(build() + "\n")
    (target / "baseline_user.txt").write_text(baseline_query() + "\n")
    (target / "core.txt").write_text(build([f for f in FAMILIES if f["role"] != "expansion"]) + "\n")
    # Remove only generated files whose definitions no longer exist.
    (target / "supplementary_split_ballot.txt").unlink(missing_ok=True)
    for old in target.glob("api_part_*.txt"):
        old.unlink()
    write_json(target / "families.json", FAMILIES)
    for i, q in enumerate(groups(), 1):
        (target / f"api_part_{i:02d}.txt").write_text(q + "\n")
    write_csv(target / "clause_register.csv", [{"family": f["id"], "role": f["role"],
        "query": clause(f), "status": "candidate; requires prospective validation"} for f in FAMILIES])


if __name__ == "__main__":
    write_queries()
