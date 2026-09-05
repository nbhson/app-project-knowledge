# Knowledge Lifecycle

> Knowledge is not just CREATED - it has a full lifecycle. This prevents stale knowledge from poisoning queries.
> [[glossary]]

---

## State Machine

```
                          +-----------------+
                          |                 |
    DISCOVERED  -->  EXTRACTED  -->  VALIDATING
       ^                  |              |
       |                  v              v
       |            EXTRACTED       ACTIVE <-- UPDATED
       |                  |         /    \
       |                  |        v      v
       |                  |    SUPERSEDED  |
       |                  |         \      /
       |                  |          v    v
       |                  |       DEPRECATED
       |                  |            |
       |                  |            v
       +------------------+       ARCHIVED
```

**Final states:** `DEPRECATED` and `ARCHIVED` are terminal -- no outgoing transitions.

---

## State Definitions

| State | Description | Who Sets It | Can Be Queried? |
|-------|-------------|-------------|-----------------|
| `DISCOVERED` | Raw data found, not yet processed | Ingestion Engine | No |
| `EXTRACTED` | Knowledge extracted but not yet validated | Extraction Engine | Yes (flagged) |
| `VALIDATING` | Under validation checks (rule + LLM) | Validation subsystem | No |
| `ACTIVE` | Validated and live -- the default operational state | Validation subsystem | Yes |
| `UPDATED` | Source changed, re-validation pending | Update Loop | Yes (flagged) |
| `SUPERSEDED` | Replaced by newer knowledge | Update Loop / Human | No |
| `DEPRECATED` | No longer in use (retired) | Governance / Human | No |
| `ARCHIVED` | Preserved for history (read-only) | Governance / Human | No (read-only access) |

---

## Transition Rules

| From | To | Trigger | Conditions |
|------|-----|---------|------------|
| `DISCOVERED` | `EXTRACTED` | Extraction Engine completes | SourceReference present, content non-empty |
| `DISCOVERED` | `ARCHIVED` | Source permanently removed | No active dependents, after 30-day hold |
| `EXTRACTED` | `VALIDATING` | Validation starts | Confidence >= 0.3, all required fields present |
| `EXTRACTED` | `DISCOVERED` | Re-ingestion needed | Missing SourceReference, corrupt content |
| `VALIDATING` | `ACTIVE` | Validation passes | Confidence >= 0.7, no conflicting knowledge |
| `VALIDATING` | `EXTRACTED` | Validation fails | Confidence < 0.7, needs re-extraction |
| `ACTIVE` | `UPDATED` | Source change detected | Source last_synced < now, content hash differs |
| `ACTIVE` | `SUPERSEDED` | New knowledge replaces this | New ACTIVE knowledge with same topic, higher confidence |
| `ACTIVE` | `DEPRECATED` | Knowledge retired | Manual override or staleness > 90 days |
| `UPDATED` | `VALIDATING` | Re-validation triggered | New content validated against rules |
| `UPDATED` | `ACTIVE` | Re-validation passes | Updated content valid, no conflicts |
| `SUPERSEDED` | `DEPRECATED` | Time-based retirement | 90 days since supersession |
| `DEPRECATED` | `ARCHIVED` | Historical preservation | Compliance requirement or manual action |
| `DEPRECATED` | `SUPERSEDED` | Re-activated by human | Human override with justification |

---

## Example: ADR Lifecycle

```
Day 1:  Confluence ADR page created
           |
           v
        DISCOVERED          (Ingestion Engine finds new page)
           |
           v
        EXTRACTED           (Extraction Engine identifies ADR structure)
           |
           v
        VALIDATING          (Validation: is this a real ADR? confidence check)
           |
           v
        ACTIVE              (Validated -- this ADR is now queryable)
           |
           |  Day 30: New ADR updates the decision
           v
        UPDATED             (Source changed -- re-validation needed)
           |
           v
        VALIDATING          (Re-validate against updated content)
           |
           v
        ACTIVE              (New version is now active)
           |
           v
        SUPERSEDED          (Old ADR marked as replaced)
           |
           |  Day 120
           v
        DEPRECATED          (Retired after 90-day grace period)
           |
           v
        ARCHIVED            (Preserved for compliance/history)
```

---

## Example: Code Entity Lifecycle

```
Day 1:  Developer pushes `PaymentService.java` to Git
           |
           v
        DISCOVERED          (FileWatcher detects new file)
           |
           v
        EXTRACTED           (Code Intelligence Engine parses AST)
           |
           v
        VALIDATING          (Validate: class exists, methods have signatures)
           |
           v
        ACTIVE              (Code is live and documented)
           |
           |  Day 14: Developer refactors PaymentService
           v
        UPDATED             (Git diff shows changes)
           |
           v
        VALIDATING          (Re-parse AST, compare old vs new)
           |
           v
        ACTIVE              (Updated code is now the source of truth)
           |
           |  (Old KnowledgeObject for PaymentService marked SUPERSEDED)
```

---

## Lifecycle in Each Engine

| Engine | Lifecycle Responsibility |
|--------|-------------------------|
| **1. Ingestion** | Sets initial state to `DISCOVERED` when data is found |
| **3. Extraction** | Transitions `DISCOVERED` -> `EXTRACTED` after parsing |
| **Validation** | Transitions `EXTRACTED` -> `VALIDATING` -> `ACTIVE` or back to `EXTRACTED` |
| **4. Storage** | Persists state changes; indexes by state for efficient filtering |
| **5. Retrieval** | Filters out `SUPERSEDED`, `DEPRECATED`, `ARCHIVED` by default; includes `UPDATED` with warnings |
| **6. Context Delivery** | Includes lifecycle state in every KnowledgeChunk for consumer awareness |

---

## Staleness Rules

| Signal | Action |
|--------|--------|
| Source not synced > 7 days | Warning flag on KnowledgeObject |
| Source not synced > 30 days | Warning + prompt user to re-sync |
| Source deleted without notice | Mark associated knowledge `SUPERSEDED` |
| New version of source detected | Trigger re-extraction -> `UPDATED` state |
| Knowledge not queried > 180 days | Suggest archiving (does not auto-archive) |