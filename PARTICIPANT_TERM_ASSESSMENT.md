# Assessing `participant*` as a search expansion

Assessment date: 10 September 2026. This is a supplementary query assessment; the published ranking and Methodology tab continue to describe the archived production retrieval.

`participant*` covers both “participant” and “participants” and can recover relevant experiments whose abstracts omit “survey,” “questionnaire,” and “respondent.” It does not, by itself, identify a survey setting. The proposed [candidate query](queries/participant_assessment/candidate_text_and_wording.txt) adds it to the context requirement for **text assignments and question-wording experiments**. The broader framing/scenario and information-treatment branches retain their existing context requirement. Exact survey- and vignette-experiment branches already operate without that requirement. No design exclusions are added.

Four Scopus diagnostic searches combined each existing phrase family with `TITLE-ABS-KEY(participant*)`, the 2010–2026 journal-article limits, and absence of the three existing context terms. That absence condition isolates the term's contribution for this diagnostic; it is absent from the candidate production query. Each search retrieved only its first 25 records, or all records when fewer were available. Returned records were matched to the frozen journal frame and archived corpus by source and article IDs.

| Phrase family | Global diagnostic hits | Records retrieved | Retrieved in frame and absent from archive |
|---|---:|---:|---:|
| Framing/scenario designs | 193 | 25 | 10 |
| Text assignments | 395 | 25 | 20 |
| Information treatments | 50 | 25 | 16 |
| Question wording | 1 | 1 | 1 |

The four pages contain 75 distinct records; 47 are in the journal frame and absent from the archived corpus. These are convenience samples, not estimates of precision or recall. The global totals overlap and include journals outside the frame. Absence from an earlier archive can also reflect indexing changes. The full incremental yield has not been retrieved or screened.

Illustrative records explain the proposed restriction:

- **Relevant wording experiment:** [Bearing the burden of peace](https://doi.org/10.1111/pops.13008) reports wording experiments with more than 1,650 Azerbaijani participants. Its [publisher full text](https://onlinelibrary.wiley.com/doi/10.1111/pops.13008) confirms random assignment within an online survey. This is a concrete omission that the added term can recover.
- **Relevant text assignment:** [Syllabus Tone but not Faculty Gender Influences Student Perceptions](https://doi.org/10.1177/00986283251397625) describes random assignment to hypothetical syllabi followed by perception measures in its Scopus abstract.
- **Broader branch needing additional screening:** [Evaluating user performance with RAG-based generative AI](https://doi.org/10.1016/j.chb.2026.108952) describes participants performing interactive search tasks, rather than establishing a survey experiment in the abstract.
- **Broader branch needing design review:** [Selective exposure reduces voluntary contributions](https://doi.org/10.1016/j.jebo.2025.107081) describes an incentivized public-good experiment with information-source choices. Online recruitment alone does not establish compatibility with the survey parser.

The candidate remains a proposed retrieval revision. Applying it requires a separate archived search, deduplication, eligibility review, and reranking; the dashboard's existing counts must not be attributed to it. Saved [diagnostic counts and provenance](results/participant_term_probe.csv) identify the exact executed query files, retrieval times, and private response hashes. The original request parameters were `count=25`, `view=COMPLETE`, and `start=0`, using `pipeline/scopus.py` with cache namespace `participant_probe_2026_09_10`.
