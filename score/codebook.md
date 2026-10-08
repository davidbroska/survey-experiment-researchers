# Spreadsheet codebook

The workbook has two 620-row assessment sheets, each with one annotation column, sorted by journal and descending year. Abstract screening and full-text review remain separate. No article ID is displayed; code joins records internally.

Labels: YES = qualifies; NO = clearly fails; UNCLEAR = unresolved. Blank means not yet assessed. Full-text availability does not imply review. Evidence and reasoning accompany only the full-text assessment. Full-text AI judgments remain provisional pending human verification.

| Sheet | Variable | Meaning |
| --- | --- | --- |
| Abstract screening | Journal | SCORE journal title. |
| Abstract screening | Year | Indexed publication year; descending within journal. |
| Abstract screening | Article title | Full article title. |
| Abstract screening | DOI | Persistent article DOI. |
| Abstract screening | Authors | Bibliographic author list; not supplied for abstract screening. |
| Abstract screening | Full text available locally | YES only for a source file with a matching recorded checksum. |
| Abstract screening | Local full text | Path to the locally available source. |
| Abstract screening | Source version note | Known manuscript differences or missing supporting assets. |
| Abstract screening | Annotation | YES / NO / UNCLEAR using only journal, title, abstract and keywords. Blank means not yet assessed. |
| Abstract screening | Abstract | Original screening input; private licensed metadata. |
| Abstract screening | Keywords | Original screening input; private licensed metadata. |
| Full-text review | Journal | SCORE journal title. |
| Full-text review | Year | Indexed publication year; descending within journal. |
| Full-text review | Article title | Full article title. |
| Full-text review | DOI | Persistent article DOI. |
| Full-text review | Authors | Bibliographic author list; not supplied for abstract screening. |
| Full-text review | Full text available locally | YES only for a source file with a matching recorded checksum. |
| Full-text review | Local full text | Path to the locally available source. |
| Full-text review | Source version note | Known manuscript differences or missing supporting assets. |
| Full-text review | Annotation | YES / NO / UNCLEAR based on substantive source review. Blank means not yet reviewed. |
| Full-text review | Evidence | Short source excerpts with page or section references; links identify supporting sources. |
| Full-text review | Reasoning | Why the same participant responses do or do not satisfy both eligibility criteria, and any unresolved source issues. |
