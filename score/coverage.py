"""Summarize metadata, retrieval and review coverage without article text."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read_rows(name):
    with (ROOT / name).open(newline='', encoding='utf-8-sig') as handle:
        return list(csv.DictReader(handle))


def main():
    articles = read_rows('articles.csv')
    access = {r['article_id']: r for r in read_rows('access.csv')}
    reviews = {r['article_id']: r for r in read_rows('independent_review.csv')}
    predictions = {r['article_id']: r for r in read_rows('predictions_original.csv')}
    groups = {('overall', 'All articles'): articles}
    for row in articles:
        for dimension in ['journal', 'year', 'group', 'split']:
            groups.setdefault((dimension, row[dimension]), []).append(row)
        label = predictions.get(row['article_id'], {}).get('collection', 'not screened')
        groups.setdefault(('metadata_collection', label), []).append(row)
    rows = []
    for (dimension, value), selected in sorted(groups.items()):
        ids = {r['article_id'] for r in selected}
        verified = sum(access.get(k, {}).get('status') == 'verified_fulltext' for k in ids)
        rows.append(dict(dimension=dimension, value=value, sampled=len(ids),
                         has_abstract=sum(r['has_abstract'].lower() == 'true' for r in selected),
                         has_keywords=sum(r['has_keywords'].lower() == 'true' for r in selected),
                         fulltext_verified=verified, fulltext_not_verified=len(ids) - verified,
                         fulltext_fraction=verified / len(ids), reviewed=len(ids & set(reviews)),
                         metadata_yes=sum(predictions.get(k, {}).get('collection') == 'YES' for k in ids),
                         metadata_no=sum(predictions.get(k, {}).get('collection') == 'NO' for k in ids),
                         metadata_unclear=sum(predictions.get(k, {}).get('collection') == 'UNCLEAR' for k in ids)))
    path = ROOT / 'coverage.csv'
    temporary = path.with_suffix('.csv.tmp')
    with temporary.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)
    print(f'Saved coverage for {len(articles)} articles across {len(rows)} grouping rows.')


if __name__ == '__main__':
    main()
