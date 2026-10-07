"""Build a small public dashboard from bibliography and aggregate review results."""
import csv
from collections import Counter
from html import escape
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read_rows(name):
    path = ROOT / name
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def text(value):
    return escape(str(value or ""), quote=True)


def percent(value):
    return "Not estimable" if value is None else f"{100 * value:.1f}%"


def main():
    articles = read_rows("articles.csv")
    access = {r["article_id"]: r for r in read_rows("access.csv")}
    references = {r["article_id"]: r for r in read_rows("independent_review.csv")}
    original = {r["article_id"]: r for r in read_rows("predictions_original.csv")}
    revised = {r["article_id"]: r for r in read_rows("predictions_revised.csv")}
    available = sum(r.get("status") == "verified_fulltext" for r in access.values())
    evaluation_path = ROOT / "evaluation.json"
    evaluation = json.loads(evaluation_path.read_text()) if evaluation_path.exists() else {}
    reviewed = evaluation.get("fulltext_reviews", 0)
    abstract_count = sum(str(r.get("has_abstract", "")).lower() in ("true", "1", "yes")
                         for r in articles)
    groups = Counter(r.get("group", "") for r in articles)
    years = Counter(str(r.get("year", "")) for r in articles)
    available_years = Counter(r.get("year", "") for r in access.values()
                              if r.get("status") == "verified_fulltext")
    reviewed_years = Counter(r.get("year", "") for r in references.values())
    available_journals = len({r.get("journal") for r in access.values()
                              if r.get("status") == "verified_fulltext"})
    coverage = "".join(f"<tr><td>{year}</td><td>{years[str(year)]} / 62</td>"
                       f"<td>{available_years[str(year)]}</td><td>{reviewed_years[str(year)]}</td></tr>"
                       for year in range(2016, 2026))
    comparisons = []
    for report in evaluation.get("evaluations", []):
        versions = {"predictions_original.csv": "Original + survey definition",
                    "predictions_revised.csv": "Tested candidate"}
        if report.get("prediction_file") not in versions:
            continue
        for field in ("collection", "experiment", "survey"):
            result = report[field]
            comparisons.append(f"""<tr><td>{versions[report['prediction_file']]}</td>
<td>{text(report['split'])}</td><td>{field.title()}</td><td>{report['predicted']}</td>
<td>{result['paired']}</td><td>{result['resolved_reference']}</td>
<td>{percent(result.get('retention_fraction_all_predictions'))}</td>
<td>{percent(result.get('abstention_rate_all_predictions'))}</td>
<td>{percent(result['yes_precision_resolved'])} <small>(n={result.get('yes_precision_denominator',0)})</small></td>
<td>{percent(result['retention_recall'])} <small>(n={result.get('retention_recall_denominator',0)})</small></td>
<td>{percent(result['discard_specificity'])} <small>(n={result.get('discard_specificity_denominator',0)})</small></td></tr>""")
    comparison_table = "".join(comparisons) or '<tr><td colspan="11">No paired evaluation yet.</td></tr>'
    article_rows = []
    def labels(row):
        return " / ".join(text(row.get(field, "—"))
                          for field in ("collection", "experiment", "survey"))
    for row in articles:
        article_id = row["article_id"]
        title = text(row.get("title"))
        doi = row.get("doi", "")
        if doi:
            title = f'<a href="https://doi.org/{text(doi)}">{title}</a>'
        state = access.get(article_id, {}).get("status", "not checked")
        reference = references.get(article_id, {})
        detail = ""
        if reference:
            detail = (f"<details><summary>Review reasoning</summary><p>{text(reference['rationale'])}</p>"
                      f"<p><a href='{text(reference['source_url'])}'>Source</a> · "
                      f"{text(reference.get('evidence_section'))}</p></details>")
        state = "Available" if state == "verified_fulltext" else "Access unresolved"
        article_rows.append(f"""<tr><td>{text(row.get('journal'))}</td>
<td>{text(row.get('year'))}</td><td>{title}{detail}</td><td>{text(row.get('split'))}</td>
<td>{text(state)}</td><td>{labels(original.get(article_id, {}))}</td>
<td>{labels(revised.get(article_id, {}))}</td><td>{labels(reference)}</td></tr>""")
    html = f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>SCORE researcher recruitment pilot</title>
<style>
body{{font:16px/1.5 system-ui,sans-serif;color:#192b35;background:#f6f8f8;margin:0}}
main{{max-width:1200px;margin:auto;padding:32px}}h1{{font-size:30px}}h2{{font-size:21px;margin-top:32px}}
a{{color:#12666a}}.cards{{display:flex;gap:16px;flex-wrap:wrap}}.card{{background:white;padding:18px;min-width:150px;border:1px solid #d6e0e0;border-radius:8px}}
.card strong{{display:block;font-size:28px}}.note{{background:#e9f0f1;padding:16px;border-left:4px solid #36787c}}
table{{border-collapse:collapse;width:100%;background:white}}td,th{{padding:10px;border-bottom:1px solid #d9e1e1;text-align:left;vertical-align:top}}
th{{background:#e4eeee}}.scroll{{overflow:auto}}input{{font:inherit;padding:10px;width:min(95%,600px);margin-bottom:14px}}
small{{color:#465c65}}nav{{display:flex;gap:20px;flex-wrap:wrap}}#papers td:first-child{{min-width:170px}}
</style><main>
<h1>SCORE researcher recruitment pilot</h1>
<p>62 journals · One article per journal and year, 2016–2025 · No geographic restriction</p>
<nav><a href="articles.csv">Article list</a><a href="journals.csv">Journal frame</a>
<a href="coverage.csv">Coverage data</a>
<a href="prompt_current.md">Current prompt</a><a href="prompt_original.md">Verbatim original</a>
<a href="prompt_revised.md">Tested candidate</a>
<a href="protocol.md">Review protocol</a><a href="report.md">Findings</a>
<a href="prompt_proposed_redline.md">Proposed prompt edits (untested)</a>
<a href="access_report.md">Access report</a>
<a href="independent_review.csv">AI source reviews</a><a href="access.csv">Retrieval status</a>
<a href="manual_downloads.csv">Download queue</a><a href="evaluation.json">Evaluation data</a>
<a href="../archive/tess/DASHBOARD_NARROWER.html">TESS archive</a></nav>
<div class="cards" style="margin-top:24px">
<div class="card"><strong>{len(articles)} / 620</strong>Articles selected</div>
<div class="card"><strong>{abstract_count}</strong>Abstracts available</div>
<div class="card"><strong>{available}</strong>Main articles available</div>
<div class="card"><strong>{reviewed}</strong>Substantive full-text reviews</div>
<div class="card"><strong>{evaluation.get('human_verified',0)}</strong>Human verifications</div></div>
<p class="note">This pilot evaluates whether metadata identifies research-team collection of quantitative human participant data.
Experiments and surveys receive separate labels. Substantive AI source review supplies the primary, provisional reference assessment;
missing access remains unresolved. Surveys include studies primarily designed as surveys and survey experiments;
incidental questionnaires and clinical assessment scales are excluded. Human RAs will verify a sample of the AI reviews.</p>
<p><strong>Provisional recommendation:</strong> Use the <a href="prompt_current.md">original prompt with the primary-survey definition</a>,
retaining collection YES and UNCLEAR. The tested candidate is preserved as a research record and has not been adopted.
Audit metadata NO decisions before using them as final exclusions. See the <a href="report.md">findings</a>.</p>
<p>The broader study window is 2016–2026. The pilot uses ten completed publication years.
Matching existing articles are retained; remaining journal–year slots are sampled from bibliographic records.
Scopus supplies 618 records; Crossref supplies the two World Politics years absent from Scopus.
The pilot is therefore not a fully random sample. TESS journals and United States restrictions do not define this frame.</p>
<p>Main text is available for {available} of {len(articles)} articles, covering {available_journals} of 62 journals.
Performance among reviewed papers cannot establish performance for the {len(articles) - reviewed} papers without source reviews.
The <a href="coverage.csv">coverage table</a> separates availability by journal, year and metadata decision.</p>
<h2>Prompt evaluation</h2>
<p>Retain both YES and UNCLEAR metadata decisions. Retention recall measures how many eligible reviewed articles survive that rule.
Discard specificity measures how many ineligible reviewed articles receive NO. Unresolved full-text labels are excluded from binary denominators.
Retained and UNCLEAR percentages use all predictions in that row, including articles without a reference review.
Each performance percentage shows its actual denominator. Development results guided revision.
The candidate was frozen before holdout source review; its metadata reviewer remained blind to those findings.
Different session reviewers and contexts contributed to the two versions, so their comparison cannot isolate the effect of prompt wording
or validate a future model configuration. Both versions use the user's primary-survey definition.</p>
<div class="scroll"><table><thead><tr><th>Prompt</th><th>Split</th><th>Decision</th><th>Predicted</th><th>Paired</th><th>Resolved</th><th>Retained</th><th>UNCLEAR</th><th>YES precision</th><th>Retention recall</th><th>Discard specificity</th></tr></thead>
<tbody>{comparison_table}</tbody></table></div>
<p><small>{text(evaluation.get('interpretation','No performance estimate is available until predictions and sourced full-text reviews are paired.'))}</small></p>
<details><summary>Coverage by publication year and field</summary>
<table><tr><th>Year</th><th>Journal slots</th><th>Main text available</th><th>Source reviewed</th></tr>{coverage}</table>
<p>{' · '.join(text(k)+': '+str(v) for k,v in sorted(groups.items()))}</p></details>
<h2>Selected articles</h2><label for="filter">Filter by journal, year, title, split, or retrieval status</label><br>
<p>Decision order: <strong>collection / experiment / survey</strong>. Reference labels come from provisional AI source review;
a dash means unreviewed or not run. The tested candidate covers the 124 held-out articles. Open “Review reasoning” for the source assessment.</p>
<input id="filter" type="search" placeholder="Search articles" autocomplete="off">
<p id="count" aria-live="polite">{len(articles)} articles</p>
<div class="scroll"><table id="papers"><thead><tr><th>Journal</th><th>Year</th><th>Article</th><th>Split</th><th>Full text</th><th>Original + survey definition</th><th>Tested candidate</th><th>AI reference</th></tr></thead>
<tbody>{''.join(article_rows)}</tbody></table></div>
<p><small>Full articles, complete abstracts, and private correspondence remain in the local research workspace.</small></p>
</main><script>
const input=document.querySelector('#filter');
const rows=[...document.querySelectorAll('#papers tbody tr')];
input.addEventListener('input',()=>{{
  const query=input.value.toLocaleLowerCase().trim();
  let count=0;
  for(const row of rows){{
    row.hidden=!row.textContent.toLocaleLowerCase().includes(query);
    if(!row.hidden)count++;
  }}
  document.querySelector('#count').textContent=count+' articles';
}});
</script></html>"""
    (ROOT / "index.html").write_text(html)
    print(f"Built SCORE dashboard with {len(articles)} articles.")


if __name__ == "__main__":
    main()
