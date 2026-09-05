"""Intent classifier - rule-based + keyword matching."""

from __future__ import annotations

import re
from enum import Enum


class IntentType(str, Enum):
    CODE_UNDERSTANDING = "CODE_UNDERSTANDING"
    REQUIREMENT_TRACEABILITY = "REQUIREMENT_TRACEABILITY"
    ARCHITECTURE = "ARCHITECTURE"
    IMPACT_ANALYSIS = "IMPACT_ANALYSIS"
    BUG_INVESTIGATION = "BUG_INVESTIGATION"
    API_USAGE = "API_USAGE"
    COMPARISON = "COMPARISON"
    SUMMARY = "SUMMARY"


KEYWORDS = {
    IntentType.CODE_UNDERSTANDING: [
        "how does",
        "what is",
        "explain",
        "how to",
        "work",
        "function",
        "class",
        "method",
    ],
    IntentType.REQUIREMENT_TRACEABILITY: [
        "which",
        "implement",
        "trace",
        "story",
        "requirement",
        "jira",
        "epic",
    ],
    IntentType.ARCHITECTURE: [
        "why",
        "decision",
        "architecture",
        "adr",
        "choice",
        "chose",
        "design",
    ],
    IntentType.IMPACT_ANALYSIS: [
        "what breaks",
        "affect",
        "depend",
        "change",
        "impact",
        "if i change",
    ],
    IntentType.BUG_INVESTIGATION: [
        "why failing",
        "error",
        "bug",
        "failing",
        "issue",
        "exception",
        "fail",
    ],
    IntentType.API_USAGE: [
        "how to call",
        "endpoint",
        "api",
        "request",
        "response",
        "curl",
        "use api",
    ],
    IntentType.COMPARISON: ["compare", "vs", "difference", "between", "versus"],
    IntentType.SUMMARY: ["summarize", "overview", "summary", "tell me about", "describe"],
}


def classify_intent(query: str) -> IntentType:
    q = query.lower()
    scores: dict[IntentType, int] = dict.fromkeys(IntentType, 0)
    for intent, keywords in KEYWORDS.items():
        for kw in keywords:
            if kw in q:
                scores[intent] += 1
    # pick max, default to CODE_UNDERSTANDING
    best = max(scores, key=lambda k: scores[k])
    if scores[best] == 0:
        return IntentType.CODE_UNDERSTANDING
    return best


class QueryPlanner:
    """Decompose complex queries into sub-queries."""

    def plan(self, query: str, intent: IntentType) -> list[str]:
        # simple decomposition for IMPACT_ANALYSIS
        if intent == IntentType.IMPACT_ANALYSIS:
            # extract entity name
            m = re.search(r"(?:change|affect|depend.*?)\s+(\w+)", query, re.I)
            if m:
                ent = m.group(1)
                return [
                    f"What is {ent}?",
                    f"What depends on {ent}?",
                    f"What does {ent} depend on?",
                ]
        if " and " in query.lower():
            parts = [p.strip() for p in query.split(" and ") if p.strip()]
            if len(parts) > 1:
                return parts
        return [query]
