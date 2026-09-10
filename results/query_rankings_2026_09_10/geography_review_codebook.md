# Geography review for query-ranking comparison

Read only the supplied title, abstract, keywords, and indexed keywords. The packet
omits authors, affiliations, journal, query route, ranking, and prior labels.
Code the country of empirical human samples, not the authors' country, language,
journal, platform, or topic alone. US_explicit requires a stated US/American sample
or named unambiguously US sampling location. US_inferred permits a specifically
US institutional/electoral setting whose recruited respondents are reasonably
inferred to be US based; studying an American topic alone is insufficient if the
sample could be foreign. non_US requires affirmative non-US sampling evidence.
mixed_includes_US means at least one US sample plus another country. unclear is
appropriate whenever the metadata cannot resolve the sample country. Do not
assign non_US merely because US is absent. not_applicable is reserved for a
clearly non-empirical article without human sample data, not an unclear design.

Save CSV private/query_rankings_2026_09_10/geography_reviews_<reviewer>.csv with:
scopus_id,geography,evidence_field,evidence_quote,rationale,metadata_sha256,
reviewer,reviewer_type,review_date,human_validated.
Allowed geography: US_explicit,US_inferred,mixed_includes_US,non_US,unclear,
not_applicable. evidence_field is title/abstract/keywords/indexed_keywords.
Use a SHORT EXACT verbatim span from that field, supporting geography where
available; unclear may use an empty field and span. Give a concise ORIGINAL rationale.
Copy metadata_sha256 from the packet; reviewer_type=AI_assisted and
human_validated=false. Read every assigned record; keyword rules are not review.
Do not inspect authors, query memberships, existing labels, or other reviewers.
