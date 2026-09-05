# Philosophy Layer

> Answers: Why are we building this?

---

## Vision

Transform fragmented project information into a continuously evolving, connected, traceable, model-independent knowledge system.

Projects accumulate knowledge in many places: code in Git, decisions in Confluence, requirements in Jira, specs in docs. This knowledge is siloed, stale, and hard to query. PKH unifies it into a single queryable knowledge graph.

---

## Core Beliefs

| Belief | Implication |
|--------|-------------|
| Knowledge outlives models | LLMs come and go; project knowledge is permanent |
| Source is always trustworthy | We never modify source data; we only interpret it |
| Interpretation is uncertain | Every piece of knowledge has a confidence score |
| One size does not fit all | Any LLM should work; no vendor lock-in |
| Stale knowledge is worse than no knowledge | Lifecycle management prevents outdated answers |

---

## What We Are Building

A **knowledge infrastructure layer** that sits alongside existing tools (Git, Confluence, Jira) and provides:

1. **Structured knowledge** -- Not raw text, but entities, relationships, and lifecycle states
2. **Traceability** -- Every fact links back to its source
3. **Intelligent retrieval** -- Semantic + relational + keyword search combined
4. **Model independence** -- Works with any LLM via adapters
5. **Continuous freshness** -- Automatic sync and staleness detection

---

## What We Are NOT Building

| NOT This | Why |
|----------|-----|
| Chatbot | We provide knowledge TO chatbots, we aren't one |
| Documentation generator | We consume docs, we don't create them |
| Code linter/formatter | Existing tools solve this |
| CI/CD tool | We integrate with CI/CD, don't replace it |
| Project management tool | We read from Jira, don't manage tickets |
| Replacement for Git/Confluence/Jira | We sit alongside these tools |

---

## Target Users

| User | Problem | How PKH Helps |
|------|---------|---------------|
| **Developer** | "I joined a new project, where do I start?" | Natural language queries about code and architecture |
| **Architect** | "What decision led us to use Kafka?" | Traceable ADRs with context |
| **Tech Lead** | "What breaks if I change this API?" | Impact analysis via knowledge graph |
| **AI Agent** | "I need project context to answer this question" | Structured ContextPackage with sources |
| **New Hire** | "How does the payment flow work?" | Summarized knowledge with source links |

---

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| User adoption | >50% of team uses weekly | CLI/API usage logs |
| Knowledge coverage | >80% of project entities indexed | Source item count vs. indexed count |
| Answer relevance | >80% of queries return useful results | Human evaluation |
| Model swap time | <5 min to switch LLM | Config change + restart |
| Sync freshness | <24h for all sources | last_synced timestamps |