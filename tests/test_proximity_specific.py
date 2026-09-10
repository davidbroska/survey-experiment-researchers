"""The post-hoc ablation changes two pairs, not gates or old snapshots."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import proximity_specific as specific
import proximity_audit as prior


def test_only_two_positive_pairs_removed():
    expected = (
        'TITLE-ABS-KEY(experiment*)\n'
        'AND ABS((read W/3 (vignette* OR scenario* OR message* OR article* OR news)) '
        'OR (manipulat* W/3 (vignette* OR scenario* OR message* OR wording)))\n'
        'AND ABS(survey* OR questionnaire* OR respondent* OR participant*)'
    )
    assert specific.clause() == expected
    assert 'passage*' in prior.clause()
    assert ' OR information OR ' in prior.clause()
    assert ' AND NOT ' not in specific.clause()


def test_new_queries_preserve_old_primary_content():
    q = specific.queries()
    assert q['specific_clause'] == prior.wrap([specific.clause()])
    original = (prior.QUERIES/'targeted.txt').read_text().rstrip('\n')
    assert q['primary_plus_specific'].replace(specific.clause(), prior.clause()) == original
    assert specific.VERSION != prior.VERSION
