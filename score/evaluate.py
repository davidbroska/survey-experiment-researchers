"""Compare one abstract label with the independently recorded source judgment."""
import json
import numpy as np
from annotate import ROOT, PRIVATE, LABELS
from review import read_rows, index_rows, write_rows, public_text


def divide(numerator, denominator):
    return float(numerator / denominator) if denominator else None


def binary_metrics(truth, positive):
    truth = np.asarray(truth) == 'YES'
    positive = np.asarray(positive, dtype=bool)
    tp = int(np.sum(truth & positive))
    tn = int(np.sum(~truth & ~positive))
    fp = int(np.sum(~truth & positive))
    fn = int(np.sum(truth & ~positive))
    sensitivity = divide(tp, tp + fn)
    specificity = divide(tn, tn + fp)
    balanced = (sensitivity + specificity) / 2 if sensitivity is not None and specificity is not None else None
    return dict(n=len(truth), tp=tp, tn=tn, fp=fp, fn=fn,
                balanced_accuracy=balanced, precision=divide(tp, tp + fp),
                recall=sensitivity, specificity=specificity, f1=divide(2 * tp, 2 * tp + fp + fn))


def compare(predictions, references):
    paired = sorted(set(predictions) & set(references))
    truth = np.array([references[key]['annotation'] for key in paired])
    predicted = np.array([predictions[key]['annotation'] for key in paired])
    resolved = np.isin(truth, ['YES', 'NO'])
    definite = resolved & np.isin(predicted, ['YES', 'NO'])
    return {
        'paired': len(paired), 'reference_resolved': int(resolved.sum()),
        'reference_unclear': int(np.sum(truth == 'UNCLEAR')),
        'abstract_unclear': int(np.sum(predicted == 'UNCLEAR')),
        'matrix_labels': list(LABELS),
        'matrix': [[int(np.sum((truth == a) & (predicted == b))) for b in LABELS] for a in LABELS],
        'strict_yes': binary_metrics(truth[resolved], predicted[resolved] == 'YES'),
        'retain_yes_or_unclear': binary_metrics(truth[resolved], predicted[resolved] != 'NO'),
        'definite_only': binary_metrics(truth[definite], predicted[definite] == 'YES'),
        'definite_coverage': divide(int(definite.sum()), int(resolved.sum())),
    }


def percent(value):
    return f'{100 * value:.1f}%' if value is not None else 'Not estimable'


def main():
    articles = index_rows(read_rows(PRIVATE / 'articles.csv'))
    predictions = index_rows(read_rows(PRIVATE / 'predictions.csv'))
    references = index_rows(read_rows(PRIVATE / 'fulltext_reviews.csv'))
    result = compare(predictions, references)
    result.update(n_articles=len(articles), abstract_completed=len(predictions),
                  fulltext_completed=len(references), human_verified=0,
                  reference='Independent provisional AI full-text review; not human ground truth',
                  prompt='prompt.md', complete=len(predictions) == len(references) == len(articles))
    (ROOT / 'score/evaluation.json').write_text(json.dumps(result, indent=2) + '\n')
    disagreements = []
    for key in sorted(set(predictions) & set(references)):
        left, right = predictions[key]['annotation'], references[key]['annotation']
        if left == right:
            continue
        row = {field: articles[key][field] for field in ['article_id', 'doi', 'journal', 'year', 'title']}
        row.update(abstract_annotation=left, fulltext_annotation=right,
                   fulltext_reasoning=public_text(references[key]['reasoning']))
        disagreements.append(row)
    fields = ['article_id', 'doi', 'journal', 'year', 'title', 'abstract_annotation', 'fulltext_annotation', 'fulltext_reasoning']
    write_rows(ROOT / 'score/disagreements.csv', disagreements, fields)
    lines = ['# SCORE prompt evaluation', '',
             f"Abstracts annotated: {len(predictions)}/620. Full texts reviewed: {len(references)}/620. Human verification: 0.", '',
             'The reference assessments are provisional AI source reviews. These metrics describe agreement with those reviews, not human-validated accuracy. The 620 articles form an access-conditioned development collection; prior prompt development and targeted examples mean this is not an untouched holdout.', '',
             '## Metrics', '',
             f"The binary comparisons use {result['reference_resolved']} paired articles with a YES or NO full-text judgment. {result['reference_unclear']} unresolved full-text judgments are excluded from binary denominators and shown in the table below. Unreviewed articles are never assigned NO.", '',
             '| Decision being evaluated | Articles | Balanced accuracy | Precision | Recall | F1 |',
             '| --- | ---: | ---: | ---: | ---: | ---: |']
    names = [('strict_yes', 'Immediate YES: UNCLEAR is not an immediate positive'),
             ('retain_yes_or_unclear', 'Retain for review: YES and UNCLEAR are positive'),
             ('definite_only', 'Definite answers only: abstract UNCLEAR excluded')]
    for key, name in names:
        values = result[key]
        lines.append('| ' + ' | '.join([name, str(values['n'])] + [percent(values[k]) for k in ['balanced_accuracy', 'precision', 'recall', 'f1']]) + ' |')
    lines += ['', f"Definite-answer coverage among resolved references: {percent(result['definite_coverage'])}. The definite-only row can look better because it excludes difficult cases; read it alongside coverage.", '',
              '## Interpretation', '',
              '- Balanced accuracy is the average of recall for eligible articles and specificity for ineligible articles. It gives both reference classes equal weight.',
              '- Precision is the share of positive decisions supported by a full-text YES. For the retention policy, this measures how many retained cases are eligible.',
              '- Recall is the share of full-text YES articles found by the decision policy. For the retention policy, a missed positive received abstract NO.',
              '- F1 combines precision and recall, giving a low score when either is low. It does not use true negatives.',
              '- The strict-YES row measures immediate identification, not the meaning of UNCLEAR as a scientific judgment. It treats UNCLEAR as not yet selected. The retention row measures the practical queue for further review.', '',
              '## All paired labels', '',
              'Rows are full-text judgments; columns are abstract judgments.', '',
              '| Full text / Abstract | YES | NO | UNCLEAR |', '| --- | ---: | ---: | ---: |']
    for label, counts in zip(LABELS, result['matrix']):
        lines.append('| ' + ' | '.join([label] + [str(n) for n in counts]) + ' |')
    lines += ['', f"See [individual disagreements](disagreements.csv). The wording review and critically vetted examples are recorded in [the error analysis](error_analysis.md).", '',
              'The frozen supplied prompt is unchanged during this evaluation. The reported performance does not establish the benefit of a suggested revision; that requires a separate test.']
    if not result['complete']:
        lines.insert(2, '**Work in progress: these are partial counts, not the completed 620-article result.**\n')
    (ROOT / 'score/report.md').write_text('\n'.join(lines) + '\n')
    print(f"Evaluated {result['paired']} paired articles; {len(disagreements)} disagreements.")


if __name__ == '__main__':
    main()
