"""Local lexical diagnostics on now-exposed development data, not Scopus recall."""
from collections import Counter
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
from common import read_csv, write_csv, write_json, digest
import query
import search_strategy as previous

MINIMAL_LABELS = ("survey experiment*", "survey based experiment*", "survey embedded experiment*",
    "survey based random* experiment*", "experimental survey*", "vignette experiment*",
    "vignette based experiment*", "experimental vignette*", "factorial survey*")
READ_STIM = re.compile(r"^(?:vignette\w*|scenario\w*|passage\w*|message\w*|article\w*|news)$")
MANIP_STIM = re.compile(r"^(?:vignette\w*|scenario\w*|message\w*|information|wording)$")
POP = re.compile(r"\b(?:survey\w*|questionnaire\w*|respondent\w*|participant\w*)\b")
EXP = re.compile(r"\bexperiment\w*\b")
RAND = re.compile(r"\b(?:experiment\w*|random\w*)\b")


def normalized(text):
    return query.normalize(re.sub(r"<[^>]*>", " ", text or ""))


def named_match(row, labels):
    fields = [normalized(row.get(k, "")) for k in ("title", "abstract", "keywords")]
    return any(re.search(r"(?<!\w)" + re.escape(p).replace(r"\*", r"\w*").replace(r"\ ", r"[\s-]+") + r"(?!\w)", text)
               for p in labels for text in fields)


def nearby(abstract, read_mode="literal", same_sentence=False):
    units = re.split(r"[.!?;]+", abstract) if same_sentence else [abstract]
    for unit in units:
        tokens = re.findall(r"\b\w+\b", unit)
        for i, token in enumerate(tokens):
            read = token == "read" if read_mode == "literal" else token in {"read", "reads", "reading"} if read_mode == "inflections" else token.startswith("read")
            pattern = READ_STIM if read else MANIP_STIM if token.startswith("manipulat") else None
            if pattern is not None and any(i != j and pattern.fullmatch(tokens[j]) for j in range(max(0, i-4), min(len(tokens), i+5))):
                return True
    return False


def check(row):
    abstract = normalized(row.get("abstract", ""))
    texts = " ".join(normalized(row.get(k, "")) for k in ("title", "abstract", "keywords"))
    gate = bool(EXP.search(texts) and POP.search(abstract))
    proximal = gate and nearby(abstract)
    minimal = named_match(row, MINIMAL_LABELS)
    full_named = named_match(row, previous.BASE_LABELS + previous.EXTRA_LABELS)
    previous_core = full_named or (bool(POP.search(texts) and RAND.search(texts)) and named_match(row, previous.GUARDED_LABELS)) or (bool(POP.search(texts)) and named_match(row, previous.READING_LABELS))
    return {"proximity_literal_read": proximal,
            "proximity_read_inflections": gate and nearby(abstract, "inflections"),
            "proximity_read_prefix": gate and nearby(abstract, "prefix"),
            "proximity_literal_read_same_sentence": gate and nearby(abstract, same_sentence=True),
            "minimal_nine_named_labels": minimal,
            "all_nineteen_named_labels": full_named,
            "minimal_named_or_proximity": minimal or proximal,
            "all_named_or_proximity": full_named or proximal,
            "previous_core_without_broad_procedure": previous_core,
            "previous_core_or_proximity": previous_core or proximal,
            "proximity_beyond_previous_core": proximal and not previous_core,
            "lost_by_minimal_compared_with_previous_core": previous_core and not (minimal or proximal)}


def run():
    summary, details, provenance = [], [], []
    sources = [("initial_stratified_development", ROOT / "private/design_audit_2026_09_10/development_packet.json",
                ROOT / "results/design_audit_2026_09_10/development_annotations.csv"),
               ("former_holdout_now_development", ROOT / "private/search_strategy_2026_09_10/validation_packet.json",
                ROOT / "results/search_strategy_2026_09_10/validation_consensus.csv")]
    for name, packet_path, label_path in sources:
        records = json.loads(packet_path.read_text())
        labels = {r["scopus_id"]: r["design"] for r in read_csv(label_path)}
        checks = {r["scopus_id"]: check(r) for r in records}
        for variant in next(iter(checks.values())):
            ids = [sid for sid, matched in checks.items() if matched[variant]]
            counts = Counter(labels[sid] for sid in ids)
            summary.append({"corpus": name, "variant": variant, "n_available": len(records), "n_local_matches": len(ids),
                "design_yes": counts["yes"], "design_no": counts["no"], "design_unclear": counts["unclear"],
                "status": "Exposed development metadata and AI labels; local lexical proxy, not measured Scopus retrieval or precision"})
        for row in records:
            details.append({"corpus": name, "scopus_id": row["scopus_id"], "title": row["title"],
                "existing_design_label": labels[row["scopus_id"]], **{k:str(v).lower() for k,v in checks[row["scopus_id"]].items()}})
        provenance.extend({"file": str(path.relative_to(ROOT)), "sha256": digest(path.read_bytes())} for path in (packet_path,label_path))
    target = ROOT / "results/proximity_clause_semantics_2026_09_10"
    write_csv(target / "development_local_proxy.csv", summary)
    write_csv(ROOT / "private/proximity_clause_semantics_2026_09_10/development_local_matches.csv", details)
    write_json(target / "development_proxy_provenance.json", {"sources": provenance, "script_sha256": digest(Path(__file__).read_bytes()),
        "proximal_distance": "At most three intervening tokens; unordered; a local approximation, not Scopus emulation",
        "limitations": "Only available title/abstract/author keywords; no indexed keywords, stopword handling or database stemming emulation. Both datasets are now exposed development material."})
    for row in summary:
        print(row["corpus"],row["variant"],row["n_local_matches"],row["design_yes"],row["design_no"],row["design_unclear"])


if __name__ == "__main__":
    run()
