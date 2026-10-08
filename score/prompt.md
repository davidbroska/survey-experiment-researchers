Using only the supplied title, abstract, keywords, and journal title for one article, decide whether its research team collected or commissioned participant responses through a survey or survey experiment used in the research reported in the article.

Return YES if at least one study reported in the article meets both criteria below. Both criteria must apply to the same set of participant responses.

# (1) The research team collected or commissioned the participant responses.

The supplied text must state or clearly imply that the team collected or commissioned the responses. This includes collecting responses directly from participants or commissioning a survey firm, panel provider, or research partner to do so.

The team's role can be implied by descriptions of its study procedures, such as presenting participants with scenarios and collecting their ratings. Explicit statements about recruitment or data collection are not required.

Analyzing questionnaire responses previously collected or commissioned by the same team also qualifies.

# (2) The responses were collected through a survey or survey experiment.

A survey asks people questions about topics such as attitudes, beliefs, preferences, experiences, intentions, or reported behavior via a questionnaire. Questionnaire responses may include answers, ratings, or choices. The terms "survey" or "questionnaire" need not appear if the method is clear.

A survey experiment deliberately varies messages, questions, information, or hypothetical scenarios across conditions and collects respondents' answers to questionnaire items.

# Further clarification:

- Return YES if the text states or clearly implies that the team used Qualtrics, SurveyMonkey, LimeSurvey, Alchemer (SurveyGizmo), or similar software to to administer its own questionnaire or survey experiment.
- Return NO if the team only analyzes data collected by other researchers or organizations, such as existing General Social Survey (GSS), American National Election Studies (ANES), European Social Survey (ESS), Panel Study of Income Dynamics (PSID), or Add Health data. Adding the team's own questions to an existing survey independently conducted by another researcher or organization does not count as collecting or commissioning the responses. Downloading, purchasing, combining, or reanalyzing existing data also does not count as data collection.
- Return NO if the team only analyzes existing administrative records, company records, newspaper articles, or social media posts, without qualifying questionnaire responses.
- Return NO if the article only reports laboratory tasks, clinical procedures, physical measurements, qualitative interviews, or observations without qualifying questionnaire responses.
- Return NO if the article only reviews previous research, develops theory, conducts a meta-analysis, presents simulations, or proposes future studies without analyzing eligible questionnaire responses.
- A natural experiment or another causal analysis does not, by itself, establish eligible data collection.

# Output

Return exactly one of the following labels, with no explanation, JSON, identifier, or other text:

YES: At least one set of participant responses meets both criteria, explicitly or by clear implication.

NO: Every study described clearly fails at least one criterion.

UNCLEAR: No study clearly qualifies, but the available information leaves unresolved whether at least one study meets both criteria. Missing information is not NO. Do not return UNCLEAR merely because the platform, exact questions, or recruitment procedure is unspecified when eligible survey collection is otherwise clear.

# Input supplied by code

The input is one JSON object describing one article, never an article list. Text fields are strings; missing text is "". Keywords are an array of strings; missing keywords are [].

{
  "journal_title": "",
  "title": "",
  "abstract": "",
  "keywords": []
}
