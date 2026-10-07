# Independent review of the proximity clause

The user’s eleven alternatives can be compressed into two action–stimulus groups without changing their logical pairs:

```
TITLE-ABS-KEY(experiment*)
AND ABS(
  (read W/3 (vignette* OR scenario* OR passage* OR message* OR article* OR news))
  OR (manipulat* W/3 (vignette* OR scenario* OR message* OR information OR wording))
)
AND ABS(survey* OR questionnaire* OR respondent* OR participant*)
```

On 10 September 2026, both forms returned 1,791 Scopus journal articles dated 2010–2026 globally. Both set differences returned zero. These checks establish empirical equivalence in this snapshot; the counts precede the frozen journal-frame filter. Combining both action terms with all eleven objects would introduce unintended pairs. Scopus officially permits OR groups as proximity arguments; parentheses avoid precedence ambiguity. [Scopus API search syntax](https://dev.elsevier.com/sc_search_tips.html); [Scopus advanced-search guidance](https://www.elsevier.support/scopus/answer/how-can-i-best-use-the-advanced-search).

Focused EID probes show that bare `read` did not retrieve an abstract containing `reading`, whereas `read*` did. The wildcard also retrieved an abstract containing `readiness`, demonstrating an unwanted expansion. Similarly, `experiment*` retrieved an abstract containing `experimental` when bare `experiment` did not. These are measured examples, not a comprehensive account of stemming. Retaining the user’s literal `read` is the most conservative equivalent compression. Proximity is unordered and does not establish that the treatment and outcome belong to the same study; it should not be described as a sentence-boundary or eligibility guarantee.

## Exposed-development comparison

`development_proxy.csv` compares local lexical approximations on the earlier 160-article development set and the former 100-article validation set. Both are now exposed development data. Proximity uses at most three intervening local tokens, not an exact reimplementation of Scopus indexing, stemming or stop-word treatment; indexed keywords are unavailable. Existing judgments are AI assisted and not a human-validated gold standard. These selected samples do not support population precision or recall estimates.

The literal-read proximity approximation matched eight articles in the 160 set, all previously coded design=yes, and four in the former 100 set (three yes, one no). Beyond the preceding named/guarded/read-assignment core it added two matches in each set: respectively two yes; and one yes plus one no. A minimal nine-label-plus-proximity replacement lost 30 previously positive articles in the 160 set and three in the former 100 set relative to that core. Consequently, brevity alone does not justify discarding the guarded design and reading-assignment families. Preserve productive logical families, compress equivalent alternatives, and evaluate the new route separately before recommending replacement.

The negative literal-read example was a ten-week mobile intervention promoting sustainable seafood choices (Scopus EID 85185598922). Its repeated messages and longitudinal behavior outcomes illustrate how human exposure to messages can satisfy the clause without an embedded survey experiment. A controlled expansion from `read` to reading inflections additionally matched a learning and retrieval-practice experiment (85125954072), where text messages accompanied a learning task and later recall. These original rationales describe scope ambiguity without reproducing abstracts.

`live_probes.csv` retains the actual Scopus counts and query hashes; `development_proxy_provenance.json` records input hashes and the reproducible local script. The subsequent full-text probability benchmark is independent of these exposed records and must not be used to tune this query after inspection.
