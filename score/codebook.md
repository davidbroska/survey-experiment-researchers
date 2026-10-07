# SCORE validation workbook codebook

The private workbook has 620 article rows and 63 variables. Journals are alphabetical; years run from 2025 down to 2016 within each journal.

Each row is one selected article. Only year and author count are stored as Excel numbers; identifiers, categories, dates and narrative fields are stored as text.

Current assessment basis: Metadata only: 240; Full-text review: 288; Metadata only — full text awaiting review: 92.

`m_` fields preserve the original metadata assessments; `r_` fields preserve completed source reviews; `a_` fields describe current acquisition. Best-available labels use the source review when present and otherwise the original metadata assessment. Downloading a document never implies that it was reviewed.

YES = qualifying evidence; NO = ineligible under that assessment; UNCLEAR = unresolved. Missing full text is not a NO. Survey means a primary questionnaire survey, including survey experiments and diary surveys, rather than incidental scales. No country restriction applies. Human-verified best assessments: 0/620.

Allowed levels describe the field; Observed reports the actual snapshot. Free-text fields have no finite level list. Blank cells and the literal values `UNCLEAR`, `not stated`, and `Not recorded` are distinct. The historical development/holdout split is not an untouched test for the later proposed prompt.

| # | Machine field | Workbook column | Meaning | Type | Allowed levels / format | Missing means | Observed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | article_id | Article ID | Stable Scopus ID, or a Crossref-derived ID for the two World Politics records. | Identifier text | Scopus identifier, or cr_ followed by the Crossref fallback identifier. | Blank not expected; none currently missing. | 620 nonblank; 620 distinct values; blank: 0 |
| 2 | journal | Journal | SCORE journal name; rows are alphabetized by journal. | Categorical text | The 62 journal names listed below; 10 articles per journal. | Blank not expected; none currently missing. | 620 nonblank; 62 distinct values; blank: 0 |
| 3 | year | Year | Publication year; ordered 2025 down to 2016 within each journal. | Integer | 2016–2025 inclusive | Blank not expected; none currently missing. | Range 2016–2025; 10 distinct values; blank: 0 |
| 4 | title | Article title | Complete bibliographic article title. | Text | Free text; no fixed levels. | Blank not expected; none currently missing. | 620 nonblank; 620 distinct values; blank: 0 |
| 5 | doi | DOI | Article DOI; click to open its publisher landing page. | Identifier text | DOI string (10.…/…); hyperlink opens its DOI landing page. | Blank not expected; none currently missing. | 620 nonblank; 620 distinct values; blank: 0 |
| 6 | authors | Authors | Complete author list supplied by the bibliographic source. | Text | Free text; no fixed levels. | Blank not expected; none currently missing. | 620 nonblank; 620 distinct values; blank: 0 |
| 7 | available | Verified local full text | YES only if the acquisition record is verified and its local document exists with the recorded SHA-256. | Categorical text | YES / NO | Blank not expected; none currently missing. | NO: 240; YES: 380; blank: 0 |
| 8 | format | Full-text format | PDF or XML for verified local main text; blank when unavailable. | Categorical text | PDF / XML | Blank = no verified local main text. | PDF: 248; XML: 132; blank: 240 |
| 9 | a_version_note | Available source version / caveat | Explicit manuscript/version notes recorded from the available source. Version not separately recorded means no version assessment was saved; availability does not establish equivalence to the final published article. | Text | Free text; no fixed levels. | Blank = no verified local text; Version not separately recorded = no saved version assessment. | 380 nonblank; 18 distinct values; Version not separately recorded: 362; blank: 240 |
| 10 | local_file | Open local full text | Local main-document path and hyperlink; works on the research computer. | Path text | Local file path; clickable when that file exists. | Blank = no verified local main text. | 380 nonblank; 380 distinct values; blank: 240 |
| 11 | basis | Assessment basis | Full-text review; Metadata only; or Metadata only — full text awaiting review. Downloading a file never establishes review. | Categorical text | Full-text review / Metadata only / Metadata only — full text awaiting review | Blank not expected; none currently missing. | Full-text review: 288; Metadata only: 240; Metadata only — full text awaiting review: 92; blank: 0 |
| 12 | collection | Collection — best available | Completed source-review label when available; otherwise frozen original metadata label. Missing full text never becomes NO. | Categorical text | YES / NO / UNCLEAR | Blank not expected; none currently missing. | NO: 257; UNCLEAR: 67; YES: 296; blank: 0 |
| 13 | experiment | Experiment — best available | Eligible researcher-imposed variation, using the same assessment source as collection. | Categorical text | YES / NO / UNCLEAR | Blank not expected; none currently missing. | NO: 364; UNCLEAR: 48; YES: 208; blank: 0 |
| 14 | survey | Survey — best available | Eligible primary questionnaire survey, including survey experiments and diary surveys; incidental scales do not qualify. | Categorical text | YES / NO / UNCLEAR | Blank not expected; none currently missing. | NO: 388; UNCLEAR: 84; YES: 148; blank: 0 |
| 15 | human_verified | Best assessment human verified | TRUE only when the selected source review explicitly records human verification; AI assessments are FALSE. | Categorical text | TRUE / FALSE | Blank not expected; none currently missing. | FALSE: 620; blank: 0 |
| 16 | criteria | Assessment criteria | Frozen pilot rules. Later policy proposals and untested revisions have not been applied retrospectively. | Categorical text | Frozen 2026-10-07 pilot: original collection rules + primary-survey definition | Blank not expected; none currently missing. | Frozen 2026-10-07 pilot: original collection rules + primary-survey definition: 620; blank: 0 |
| 17 | m_collection | Metadata collection | Frozen original assessment using the fields recorded in Metadata input fields; retained even when source review differs. | Categorical text | YES / NO / UNCLEAR | Blank not expected; none currently missing. | NO: 248; UNCLEAR: 121; YES: 251; blank: 0 |
| 18 | m_experiment | Metadata experiment | Frozen original eligible-experiment assessment. | Categorical text | YES / NO / UNCLEAR | Blank not expected; none currently missing. | NO: 345; UNCLEAR: 93; YES: 182; blank: 0 |
| 19 | m_survey | Metadata survey | Frozen original primary-survey assessment under the user’s survey definition. | Categorical text | YES / NO / UNCLEAR | Blank not expected; none currently missing. | NO: 371; UNCLEAR: 151; YES: 98; blank: 0 |
| 20 | m_evidence | Metadata evidence | Short exact excerpts from the supplied bibliographic fields; no full-text evidence was available to this assessment. | Text | Free text; no fixed levels. | Blank = no exact excerpt saved; not proof of ineligibility. | 617 nonblank; 617 distinct values; blank: 3 |
| 21 | m_rationale | Metadata rationale | Explanation saved with the frozen metadata decision. | Text | Free text; no fixed levels. | Blank not expected; none currently missing. | 620 nonblank; 620 distinct values; blank: 0 |
| 22 | m_other_methods | Metadata other methods | Other qualifying collection methods named in the frozen metadata assessment. | Text | Free text; no fixed levels. | Blank = no other method recorded; not proof that none exists. | 56 nonblank; 47 distinct values; blank: 564 |
| 23 | m_software | Metadata software | Software names explicitly associated with the study in the supplied metadata. | Text | Free text; no fixed levels. | not stated = no explicit software name in supplied metadata. | 620 nonblank; 7 distinct values; not stated: 614; blank: 0 |
| 24 | m_recruitment_providers | Metadata recruitment providers | Recruitment or panel providers explicitly named in the supplied metadata. | Text | Free text; no fixed levels. | not stated = no explicit provider name in supplied metadata. | 620 nonblank; 2 distinct values; not stated: 619; blank: 0 |
| 25 | m_team_data_reuse | Metadata earlier team data | Original assessment of explicit reuse of the team’s earlier data; not a flag for retained local articles. | Categorical text | YES / NO / UNCLEAR | Blank not expected; none currently missing. | UNCLEAR: 620; blank: 0 |
| 26 | m_prompt_version | Metadata prompt version | Version stored in the frozen original predictions, including the primary-survey override. | Categorical text | original_with_primary_survey_definition | Blank not expected; none currently missing. | original_with_primary_survey_definition: 620; blank: 0 |
| 27 | m_reviewer | Metadata reviewer | Session reviewer identifier saved with the metadata decision. | Identifier text | Saved reviewer identifier; current identifiers are shown in Observed. | Blank not expected; none currently missing. | metadata_agent: 293; root_metadata: 327; blank: 0 |
| 28 | m_prediction_time | Metadata decision time | Timestamp saved with the frozen metadata decision; Not recorded means no timestamp was saved. | Date/time text | Recorded timestamp; metadata decision time may be Not recorded. | Not recorded = no saved timestamp; never inferred. | 620 nonblank; 311 distinct values; Not recorded: 310; blank: 0 |
| 29 | m_input_fields | Metadata input fields | Actual recorded input fields; Not recorded means the reviewer did not save this audit field. Bibliographic columns do not establish what the reviewer used. | Categorical text | title;abstract;keywords;authors / title;abstract;keywords;indexed_keywords / Not recorded | Not recorded = input fields were not logged; never inferred from available bibliography. | Not recorded: 301; title;abstract;keywords;authors: 302; title;abstract;keywords;indexed_keywords: 17; blank: 0 |
| 30 | m_authors_supplied | Metadata authors supplied | Recorded author-input flag; Not recorded means unknown, not FALSE. Availability does not imply author identity was used to infer collection. | Categorical text | true / false / Not recorded | Not recorded = unknown; false means explicitly not supplied. | Not recorded: 301; false: 17; true: 302; blank: 0 |
| 31 | r_collection | Full-text collection | Completed source-based reference label; blank means no completed review, not NO. | Categorical text | YES / NO / UNCLEAR | Blank = no completed source review; never NO. | NO: 98; UNCLEAR: 1; YES: 189; blank: 332 |
| 32 | r_experiment | Full-text experiment | Completed source-based eligible-experiment label; blank if unreviewed. | Categorical text | YES / NO / UNCLEAR | Blank = no completed source review; never NO. | NO: 151; UNCLEAR: 2; YES: 135; blank: 332 |
| 33 | r_survey | Full-text survey | Completed source-based primary-survey label; blank if unreviewed. | Categorical text | YES / NO / UNCLEAR | Blank = no completed source review; never NO. | NO: 171; UNCLEAR: 1; YES: 116; blank: 332 |
| 34 | r_evidence_excerpt | Full-text evidence | Short exact excerpt supporting the reference assessment. | Text | Free text; no fixed levels. | Blank = no completed source review; never NO. | 288 nonblank; 288 distinct values; blank: 332 |
| 35 | r_evidence_section | Evidence location | Methods section, page numbers, or other locations inspected by the source reviewer. | Text | Free text; no fixed levels. | Blank = no completed source review; never NO. | 288 nonblank; 161 distinct values; blank: 332 |
| 36 | r_rationale | Full-text rationale | Source-review explanation, including collection provenance and relevant study components. | Text | Free text; no fixed levels. | Blank = no completed source review; never NO. | 288 nonblank; 288 distinct values; blank: 332 |
| 37 | r_other_methods | Full-text other methods | Other collection methods identified through source review. | Text | Free text; no fixed levels. | Blank = no completed source review; never NO. | 288 nonblank; 74 distinct values; not stated: 24; blank: 332 |
| 38 | r_software | Full-text software | Software recorded from inspected study sources. | Text | Free text; no fixed levels. | Blank = no completed source review; never NO. | 288 nonblank; 108 distinct values; not stated: 163; blank: 332 |
| 39 | r_recruitment_providers | Full-text recruitment providers | Recruitment providers recorded from inspected study sources. | Text | Free text; no fixed levels. | Blank = no completed source review; never NO. | 288 nonblank; 53 distinct values; not stated: 220; blank: 332 |
| 40 | r_team_data_reuse | Full-text earlier team data | Whether the reviewed study uses data previously collected or commissioned by the team, with supporting detail. | Text | Free text; no fixed levels. | Blank = no completed source review; never NO. | 288 nonblank; 33 distinct values; not stated: 20; blank: 332 |
| 41 | r_confidence | Full-text reviewer confidence | Reviewer’s stated confidence; not a calibrated probability. | Categorical text | high / moderate / medium / low; stored spellings are preserved | Blank = no completed source review; never NO. | high: 284; low: 1; medium: 1; moderate: 2; blank: 332 |
| 42 | r_reviewer | Full-text reviewer | Identifier of the primary source reviewer. | Identifier text | Saved reviewer identifier; current identifiers are shown in Observed. | Blank = no completed source review; never NO. | Codex independent fulltext reviewer: 126; Codex independent fulltext reviewer social: 127; metadata_agent_after_prediction_freeze: 2; root_fulltext: 33; blank: 332 |
| 43 | r_review_date | Full-text review date | Date of the completed source assessment. | Date/time text | YYYY-MM-DD | Blank = no completed source review; never NO. | 288 nonblank; 1 distinct values; blank: 332 |
| 44 | r_review_status | Full-text review status | Stored review status; source reviews remain AI assessments until human verification. | Categorical text | primary_ai_fulltext_review / provisional_ai_review | Blank = no completed source review; never NO. | primary_ai_fulltext_review: 255; provisional_ai_review: 33; blank: 332 |
| 45 | r_human_verified | Full-text human verified | Stored human-verification flag; blank when there is no reference review. | Categorical text | true / false | Blank = no completed source review; never NO. | false: 288; blank: 332 |
| 46 | r_source_url | Reviewed source URL | Online location recorded for the reviewed main source. | URL text | Recorded source URL; supporting sources may contain several URLs. | Blank = no completed source review; never NO. | 288 nonblank; 288 distinct values; blank: 332 |
| 47 | r_source_path | Reviewed source cache | Local extracted-text or document path used for the review; click to open. | Path text | Local file path; clickable when that file exists. | Blank = no completed source review; never NO. | 288 nonblank; 288 distinct values; blank: 332 |
| 48 | r_source_sha256 | Reviewed document SHA-256 | Fingerprint of the source document, not of the extracted-text cache. | Hash text | 64 hexadecimal characters: SHA-256 of the source document. | Blank = no completed source review; never NO. | 288 nonblank; 288 distinct values; blank: 332 |
| 49 | r_supporting_resource_url | Supporting sources URL | Additional repository, supplement, or project evidence recorded by the reviewer. | URL text | Recorded source URL; supporting sources may contain several URLs. | Blank = no supporting URL recorded, or no completed review; not proof that no resource exists. | 53 nonblank; 53 distinct values; blank: 567 |
| 50 | r_supporting_resource_status | Supporting sources checked | What supporting sources were actually inspected and what remains unresolved. | Text | Free text; no fixed levels. | Blank = no completed source review; never NO. | 288 nonblank; 18 distinct values; blank: 332 |
| 51 | a_status | Retrieval status | Latest acquisition status, independent of eligibility or review completion. | Categorical text | verified_fulltext / unavailable_after_checks | Blank not expected; none currently missing. | unavailable_after_checks: 240; verified_fulltext: 380; blank: 0 |
| 52 | a_checked_at | Retrieval checked at | Timestamp of the latest saved acquisition check. | Date/time text | Recorded timestamp; metadata decision time may be Not recorded. | Blank not expected; none currently missing. | 620 nonblank; 620 distinct values; blank: 0 |
| 53 | a_identity_check | Retrieval identity check | How the acquisition process matched the document to the selected article. | Categorical text | title_match / doi_and_title_match / title_authors_journal_year_visually_verified / title_authors_and_repository_doi_independently_verified | Blank = no verified local main text. | doi_and_title_match: 26; title_authors_and_repository_doi_independently_verified: 1; title_authors_journal_year_visually_verified: 1; title_match: 352; blank: 240 |
| 54 | a_source_url | Acquired source URL | Online location of the latest verified main text or recorded acquisition result. | URL text | Recorded source URL; supporting sources may contain several URLs. | Blank = no verified local main text. | 380 nonblank; 380 distinct values; blank: 240 |
| 55 | a_source_sha256 | Acquired document SHA-256 | Fingerprint checked against the current local main document. | Hash text | 64 hexadecimal characters: SHA-256 of the source document. | Blank = no verified local main text. | 380 nonblank; 380 distinct values; blank: 240 |
| 56 | a_text_cache | Current extracted text | Local cache for searching the current main text; a cache does not mean it was reviewed. | Path text | Local file path; clickable when that file exists. | Blank = no verified local main text. | 380 nonblank; 380 distinct values; blank: 240 |
| 57 | split | Frozen evaluation split | Historical development/holdout assignment from the first pilot; not an untouched test for the later proposed prompt. New downloads do not change the assignment. | Categorical text | development / holdout | Blank not expected; none currently missing. | development: 496; holdout: 124; blank: 0 |
| 58 | metadata_source | Bibliographic source | Scopus or Crossref. Bibliographic provenance is independent of full-text retrieval. | Categorical text | Scopus / Crossref | Blank not expected; none currently missing. | Crossref: 2; Scopus: 618; blank: 0 |
| 59 | source_date | Bibliographic retrieval date | Date recorded for the bibliographic response. | Date/time text | Recorded timestamp; metadata decision time may be Not recorded. | Blank not expected; none currently missing. | 620 nonblank; 619 distinct values; blank: 0 |
| 60 | source_url | Bibliographic source URL | DOI landing page or source URL from the metadata record. | URL text | Recorded source URL; supporting sources may contain several URLs. | Blank not expected; none currently missing. | 620 nonblank; 620 distinct values; blank: 0 |
| 61 | n_authors | Author count | Number of authors supplied by the bibliographic source. | Integer | Positive author count; current range 1–26. | Blank not expected; none currently missing. | Range 1–26; 16 distinct values; blank: 0 |
| 62 | abstract | Abstract — screening input | Complete supplied abstract; blank means unavailable. Private licensed metadata. | Text | Free text; no fixed levels. | Blank = no abstract supplied by the bibliographic source. | 612 nonblank; 612 distinct values; blank: 8 |
| 63 | keywords | Keywords — screening input | Complete supplied keywords; blank means unavailable. Private licensed metadata. | Text | Free text; no fixed levels. | Blank = no keywords supplied by the bibliographic source. | 441 nonblank; 441 distinct values; blank: 179 |

## Journal levels

These are all 62 allowed journal values; each has 10 rows.

| Journal | Rows |
| --- | --- |
| Academy of Management Journal | 10 |
| American Economic Journal: Applied Economics | 10 |
| American Economic Review | 10 |
| American Educational Research Journal | 10 |
| American Journal of Political Science | 10 |
| American Journal of Sociology | 10 |
| American Political Science Review | 10 |
| American Sociological Review | 10 |
| British Journal of Political Science | 10 |
| Child Development | 10 |
| Clinical Psychological Science | 10 |
| Cognition | 10 |
| Comparative Political Studies | 10 |
| Computers and Education | 10 |
| Contemporary Educational Psychology | 10 |
| Criminology | 10 |
| Demography | 10 |
| Econometrica | 10 |
| Educational Researcher | 10 |
| European Journal of Personality | 10 |
| European Sociological Review | 10 |
| Evolution and Human Behavior | 10 |
| Exceptional Children | 10 |
| Experimental Economics | 10 |
| Health Psychology | 10 |
| Journal of Applied Psychology | 10 |
| Journal of Business Research | 10 |
| Journal of Conflict Resolution | 10 |
| Journal of Consulting and Clinical Psychology | 10 |
| Journal of Consumer Research | 10 |
| Journal of Educational Psychology | 10 |
| Journal of Environmental Psychology | 10 |
| Journal of Experimental Political Science | 10 |
| Journal of Experimental Psychology: General | 10 |
| Journal of Experimental Social Psychology | 10 |
| Journal of Finance | 10 |
| Journal of Financial Economics | 10 |
| Journal of Labor Economics | 10 |
| Journal of Management | 10 |
| Journal of Marketing | 10 |
| Journal of Marketing Research | 10 |
| Journal of Marriage and Family | 10 |
| Journal of Organizational Behavior | 10 |
| Journal of Personality and Social Psychology | 10 |
| Journal of Political Economy | 10 |
| Journal of Public Administration Research and Theory | 10 |
| Journal of the Academy of Marketing Science | 10 |
| Law and Human Behavior | 10 |
| Leadership Quarterly | 10 |
| Learning and Instruction | 10 |
| Management Science | 10 |
| Organization Science | 10 |
| Organizational Behavior and Human Decision Processes | 10 |
| Psychological Medicine | 10 |
| Psychological Science | 10 |
| Public Administration Review | 10 |
| Quarterly Journal of Economics | 10 |
| Review of Financial Studies | 10 |
| Social Forces | 10 |
| Social Science and Medicine | 10 |
| World Development | 10 |
| World Politics | 10 |

The workbook contains licensed abstracts, author lists, exact evidence, and local paths and remains private. This codebook contains definitions and aggregate counts only.

Regenerate the workbook and this codebook together with `python3 score/workbook.py`.
