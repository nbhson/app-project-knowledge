# Day 14 — Decision & Rule Detection (Phase 3)

> **Phase:** 3 — Knowledge Extraction Engine | **Date:** Day 14 of 30 | **Goal:** Detect Architecture Decision Records (ADRs), business rules, and constraints

---

## 🎯 Daily Target

**Deliverable:** Detectors for ADRs, business rules, and technical constraints that output KnowledgeObjects with object_type=DECISION or RULE

---

## ✅ Tasks

### 1. ADRDetector (`adr_detector.py`)
- [ ] Pattern matching for Architecture Decision Records:
  - Filename pattern: `ADR-*`, `architecture-decision-*`
  - Title pattern: `ADR: *`, `Architecture Decision Record: *`
  - Content structure: Context/Decision/Consequences sections
  - Labels/tags: `adr`, `architecture-decision`
- [ ] Extract:
  - Decision ID (from filename or content)
  - Status (proposed, accepted, superseded)
  - Context, decision, consequences
  - Related requirements/issues
- [ ] Output: KnowledgeObject with:
  - object_type=DECISION
  - entity_type=ADR (or create new EntityType.ADR)
  - content: structured decision record
  - relationships: TRACES_TO (related requirements), DOCUMENTS (related code)

### 2. BusinessRuleDetector (`business_rule_detector.py`)
- [ ] Detect "must", "should", "cannot", "required" patterns:
  - Regex patterns for obligation language
  - Context-aware detection (in requirements, policies, contracts)
  - Negation handling (must not, cannot)
- [ ] Extract:
  - Rule statement
  - Condition/action
  - Scope (system-wide, module-specific)
  - Enforcement mechanism (if specified)
- [ ] Output: KnowledgeObject with:
  - object_type=RULE
  - entity_type=BUSINESS_RULE
  - content: rule statement
  - relationships: GOVERNS (entities it applies to)

### 3. ConstraintDetector (`constraint_detector.py`)
- [ ] Detect technical constraints, NFRs, security requirements:
  - Performance: response time < Xms, throughput > Y req/sec
  - Scalability: handle Z concurrent users
  - Availability: 99.9% uptime
  - Security: encryption, authentication, authorization
  - Compliance: GDPR, HIPAA, SOC2
- [ ] Extract from:
  - Requirements documents
  - Architecture decisions
  - Design specifications
  - Code comments (TODO, FIXME, SECURITY)
- [ ] Output: KnowledgeObject with:
  - object_type=RULE
  - entity_type=TECHNICAL_CONSTRAINT or SECURITY_REQUIREMENT
  - content: constraint statement
  - relationships: CONSTRAINS (entities it applies to)

### 4. Confidence Scoring for Detectors
- [ ] High confidence (0.9): explicit labels/patterns (ADR-*, must/shall)
- [ ] Medium confidence (0.7): inferred from context/keywords
- [ ] Low confidence (0.5): heuristic-based detection

### 5. Integration with Extraction Pipeline
- [ ] Feed into Day 15 pipeline after rule-based and LLM extraction
- [ ] Merge with other extracted entities
- [ ] Resolve conflicts (e.g., duplicate ADR detection)

### 6. Unit Tests
- [ ] Test ADR detection on sample ADR files
- [ ] Test business rule detection on requirement text
- [ ] Test constraint detection on NFR documents
- [ ] Validate output KnowledgeObject structure
- [ ] Test conflict resolution with other extractors

---

## 📋 Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| Detects ADRs by filename, title, structure | ☐ |
| Extracts business rules with obligation language | ☐ |
| Detects technical constraints and NFRs | ☐ |
| Outputs correct KnowledgeObject types (DECISION, RULE) | ☐ |
| Integrates with extraction pipeline | ☐ |
| Unit tests pass | ☐ |

---

## 🔗 Dependencies

- **Blocks:** Day 15 (Extraction pipeline)
- **Blocked by:** Day 13 (LLM extractor provides enrichment)

---

## 📝 Notes

- Consider creating new EntityTypes for ADR, BUSINESS_RULE, etc. or use properties
- Use regex patterns + NLP techniques for detection
- Store detected decisions/rules in knowledge graph for traceability
- Commit: `feat: adr, business rule, and constraint detectors`