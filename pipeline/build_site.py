"""Stage an allowlisted GitHub Pages site; never publish or copy private data."""
from html.parser import HTMLParser
from pathlib import Path
import shutil
from urllib.parse import unquote, urlsplit
import zipfile

from common import ROOT, digest, write_json

REPORTS = ('EXECUTIVE_SUMMARY', 'SUPPORTING_INFORMATION', 'QUERY_REPORT',
           'GEOGRAPHY_REPORT', 'FULLTEXT_REVIEW', 'YEAR_WINDOW_COMPARISON', 'MANUAL_DOWNLOADS', 'PRIORITY_DOWNLOADS',
           'QUERY_REVISION', 'SEARCH_STRATEGY', 'SEARCH_SUMMARY', 'SEARCH_METHODS',
           'PROXIMITY_AUDIT', 'PROXIMITY_METHODS', 'PROXIMITY_SUMMARY', 'FULLTEXT_BENCHMARK', 'RANKING_COMPARISON_REPORT',
           'METHODOLOGY', 'COAUTHOR_SUMMARY')
CSV_FILES = ('top100_enriched', 'top100_provisional', 'top100_article_annotations',
             'top100_author_article_links', 'top100_cutoff_ties', 'fulltext_download_queue',
             'year_window_author_comparison', 'year_window_tie_comparison',
             'manual_download_queue', 'downloaded_awaiting_review', 'top50_priority_downloads')


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, tag, attrs):
        self.targets.extend(v for k, v in attrs if k in ('href', 'src') and v)


def check_links(site):
    checked = 0
    for path in sorted(site.rglob('*.html')):
        links = Links()
        links.feed(path.read_text())
        for target in links.targets:
            url = urlsplit(target)
            if url.scheme or url.netloc or not url.path:
                continue
            dest = (path.parent / unquote(url.path)).resolve()
            if not dest.is_relative_to(site.resolve()) or not dest.is_file():
                raise ValueError(f'Broken or escaping site link: {path.name}: {target}')
            checked += 1
    return checked


def build():
    site = ROOT / 'site'
    site.mkdir(exist_ok=True)
    files = ['TOP100.html', 'TOP40.html', 'RANKING_COMPARISON.html', 'queries/recommended.txt',
             'DASHBOARD_ORIGINAL.html', 'DASHBOARD_COMPLETE.html', 'DASHBOARD_NARROWER.html',
             'inputs/query_dashboard_affiliations.csv']
    files += [f'results/variant_dashboards_2026_09_10/{name}.json' for name in
              ('original_provenance', 'complete_provenance', 'narrower_provenance', 'browser_check')]
    files += [f'{r}.{ext}' for r in REPORTS for ext in ('md', 'html')]
    files += [f'results/{r}.csv' for r in CSV_FILES]
    files += [f'queries/revision_2026_09_10/{name}.txt' for name in ('previous', 'revised', 'additional_embedded_variants')]
    files += [f'results/query_revision_2026_09_10/{name}.csv' for name in
              ('retrieval_comparison', 'sequential_changes', 'changed_article_metadata', 'local_verification_by_change', 'field_checks')]
    files += ['results/venue_frame.csv',
              'queries/participant_guards_2026_09_10/revised.txt',
              'results/participant_guards_2026_09_10/retrieval_comparison.csv',
              'results/participant_guards_2026_09_10/local_verification.csv',
              'results/participant_guards_2026_09_10/summary.json',
              'results/design_audit_2026_09_10/annotation_codebook.md',
              'results/design_audit_2026_09_10/counterexample_source_audit.csv',
              'results/design_audit_2026_09_10/local_guard_diagnostic_counts.json',
              'results/design_audit_2026_09_10/development_sample.csv',
              'results/design_audit_2026_09_10/development_annotations.csv',
              'results/design_audit_2026_09_10/development_strata_summary.csv',
              'results/design_audit_2026_09_10/development_sample_manifest.json',
              'results/design_audit_2026_09_10/development_annotation_provenance.json']
    files += [f'queries/search_strategy_2026_09_10/{name}.txt' for name in
              ('candidate', 'primary', 'named_base', 'named_extra', 'guarded_design', 'procedure', 'reading_assignment')]
    files += ['queries/search_strategy_2026_09_10/executed_parts.csv']
    # These are public metadata and coding rationales, without licensed abstracts
    # or the private verbatim evidence spans used to validate coding.
    files += [f'results/search_strategy_2026_09_10/{name}.csv' for name in
              ('counterexample_retrieval', 'retrieval_comparison', 'route_counts',
               'validation_sample', 'validation_coder_A', 'validation_coder_B',
               'validation_consensus', 'validation_disagreements', 'validation_unclear_queue',
               'validation_strata_summary', 'lost_record_review')]
    files += [f'results/search_strategy_2026_09_10/{name}.json' for name in
              ('protocol', 'retrieval_manifests', 'validation_sample_manifest',
               'validation_packet_provenance', 'validation_annotation_provenance',
               'validation_summary', 'report_provenance')]
    files += [f'queries/proximity_audit_2026_09_10/{name}.txt' for name in
              ('user_clause', 'grouped_clause', 'targeted', 'minimal')]
    files += [f'results/proximity_audit_2026_09_10/{name}.csv' for name in
              ('author_identity_audit', 'author_comparison', 'author_fulltext_examples',
               'author_article_retrieval', 'author_byline_discrepancies', 'retrieval_counts',
               'retrieval_comparison', 'fulltext_sample', 'fulltext_sampling_strata')]
    files += [f'results/proximity_audit_2026_09_10/{name}.json' for name in
              ('protocol', 'grouping_equivalence', 'retrieval_manifests', 'fulltext_sample_manifest', 'report_provenance')]
    files += ['results/proximity_clause_semantics_2026_09_10/live_probes.csv']
    files += [f'queries/proximity_specific_2026_09_10/{name}.txt' for name in
              ('specific_clause', 'primary_plus_specific')]
    files += [f'results/proximity_specific_2026_09_10/{name}.csv' for name in
              ('retrieval_counts', 'retrieval_comparison', 'exposed_benchmark_retention',
               'exposed_benchmark_summary', 'author_comparison', 'author_article_retrieval')]
    files += [f'results/proximity_specific_2026_09_10/{name}.json' for name in
              ('protocol', 'global_set_comparison', 'offline_reproducibility')]
    files += ['results/proximity_specific_2026_09_10/development_summary.md']
    files += [f'results/precision_benchmark_2026_09_10/{name}.csv' for name in
              ('availability_manifest', 'manual_download_queue', 'article_consensus',
               'axis_annotations', 'stratum_summary', 'missing_label_bounds')]
    files += [f'results/precision_benchmark_2026_09_10/{name}.json' for name in
              ('sample_manifest', 'review_schema', 'summary', 'review_summary', 'review_provenance')]
    files += [f'results/query_rankings_2026_09_10/{name}.csv' for name in
              ('comparison_authors', 'author_rank_comparison', 'top100_entrants_exits',
               'top100_membership_comparison', 'tie_metrics', 'focal_author_comparison',
               'byline_coverage', 'byline_completion_audit', 'current_filter_decomposition',
               'article_geography', 'geography_review_queue', 'display_membership_changes',
               'display_membership_summary', 'benchmark_retention_after_downloads')]
    files += [f'results/query_rankings_2026_09_10/{name}.json' for name in
              ('geography_summary', 'verification', 'comparison_report_provenance')]
    files += [f'results/query_rankings_2026_09_10/{name}.md' for name in
              ('methodological_assessment', 'geography_review_codebook')]
    files += ['results/proximity_specific_2026_09_10/membership.csv', 'inputs/query_ranking_name_reviews.csv']
    for variant in ('original_query', 'narrower_query', 'current_raw', 'current_published'):
        files += [f'results/query_rankings_2026_09_10/{variant}_{suffix}.csv' for suffix in
                  ('ranking', 'top100', 'top100_with_cutoff_ties', 'cutoff_ties', 'us_ranking')]
        files += [f'results/query_rankings_2026_09_10/uniform_pool_{variant}_us_ranking.csv']
    files += [f'results/benchmark_review_wave2_2026_09_10/{name}.csv' for name in
              ('availability_manifest', 'manual_download_queue', 'article_consensus',
               'axis_annotations', 'stratum_summary', 'missing_label_bounds', 'review_disagreements', 'geography_adjudications')]
    files += [f'results/benchmark_review_wave2_2026_09_10/{name}.json' for name in
              ('summary', 'review_summary', 'review_provenance', 'adjudication_provenance')]
    files += [f'results/benchmark_review_wave3_2026_09_10/{name}.csv' for name in
              ('availability_manifest', 'manual_download_queue', 'article_consensus', 'axis_annotations',
               'stratum_summary', 'missing_label_bounds', 'review_disagreements', 'geography_adjudications',
               'public_alternative_lookup', 'publisher_access_issues')]
    files += [f'results/benchmark_review_wave3_2026_09_10/{name}.json' for name in
              ('summary', 'review_summary', 'review_provenance', 'adjudication_provenance')]
    files += [f'results/us_geography_priority_2026_09_10/{name}.csv' for name in
              ('article_priority_queue', 'author_uncertainty', 'manual_download_queue', 'automatic_acquisition_queue',
               'fulltext_geography_reviews', 'metadata_review_proposals', 'round10_status', 'remaining_round10_downloads',
               'author_changes')]
    files += [f'results/us_geography_priority_2026_09_10/{name}.json' for name in
              ('priority_manifest', 'round10_manifest', 'fulltext_review_validation', 'metadata_review_validation',
               'queue_validation')]
    files += [f'results/us_geography_priority_2026_09_10/assessment.{ext}' for ext in ('md', 'html')]
    files += [f'results/coauthor_update_2026_09_10/{name}.csv' for name in
              ('availability_manifest', 'geography_reviews', 'design_parser_flags')]
    files += [f'results/coauthor_update_2026_09_10/{name}.json' for name in
              ('inventory_summary', 'review_validation', 'methodology_provenance')]
    files += [f'results/coauthor_update_wave2_2026_09_10/{name}.csv' for name in
              ('availability_manifest', 'review_assignment', 'geography_reviews', 'design_parser_flags')]
    files += [f'results/coauthor_update_wave2_2026_09_10/{name}.json' for name in
              ('inventory_summary', 'review_validation')]
    files += [f'results/coauthor_update_wave3_2026_09_10/{name}.csv' for name in
              ('availability_manifest', 'review_assignment', 'geography_reviews', 'design_parser_flags')]
    files += [f'results/coauthor_update_wave3_2026_09_10/{name}.json' for name in
              ('inventory_summary', 'review_validation')]
    for name in files:
        dest = site / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, dest)
    shutil.copy2(ROOT / 'DASHBOARD_NARROWER.html', site / 'index.html')
    (site / '.nojekyll').write_text('')
    (site / 'README.md').write_text('Survey-experiment researcher dashboard, publications 2010–2026.\n\n'
                                  'Open [the researcher ranking](index.html) or [the selection method and query](METHODOLOGY.html). '
                                  'Counts represent first/last-author candidate articles. US labels combine explicit and inferred '
                                  'evidence and await independent validation. Source PDFs, full abstracts, API credentials, and '
                                  'Scopus caches are not included.\n')
    expected = set(files) | {'index.html', '.nojekyll', 'README.md'}
    actual = {str(p.relative_to(site)) for p in site.rglob('*') if p.is_file()}
    # Unexpected files require deliberate handling rather than being silently published or deleted.
    if actual != expected:
        raise ValueError(f'Unexpected site contents: {sorted(actual ^ expected)}')
    checked = check_links(site)
    manifest = [{'path': name, 'sha256': digest((site / name).read_bytes())} for name in sorted(expected)]
    write_json(ROOT / 'results/site_manifest.json', {'entry': 'index.html', 'main_dashboard': 'DASHBOARD_NARROWER.html', 'files': manifest,
               'local_links_checked': checked, 'private_files_included': False, 'published': False})
    with zipfile.ZipFile(ROOT / 'github-pages-site.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(expected):
            info = zipfile.ZipInfo(name, (2026, 9, 9, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, (site / name).read_bytes())
    print(f'Staged {len(manifest)} files; checked {checked} local links. No publication performed.')


if __name__ == '__main__':
    build()
