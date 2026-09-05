# Overall Architecture

> The complete architecture of Project Knowledge Harness (PKH): 4 Domains, 6 Engines, Knowledge Model, Cross-cutting capabilities, and Consumers.
> [[glossary]]

---

## System Structure

```mermaid
graph TD
    SRC[DATA SOURCES\nGit, Confluence, Jira, Documents, API Specs] --> DOM[4 DOMAINS\nBusiness Responsibility]
    DOM --> KM[KNOWLEDGE MODEL\nSemantic Foundation\n23 Entity Types | 15 Relationship Types | 8 Lifecycle States]
    KM --> ENG[6 EXECUTION CAPABILITIES\nEngines 1-6]
    ENG --> CC[CROSS-CUTTING CAPABILITIES\nLifecycle | Traceability | Governance & Trust | Evaluation]
    CC --> CON[CONSUMERS\nCLI | REST API | IDE Extension | Web Dashboard | Agent SDK]

    subgraph D1 [Domain 1: Knowledge Acquisition]
        D1[Collect & understand]
        E1[Engine 1: Ingestion]
        E2[Engine 2: Code Intelligence]
        E3[Engine 3: Knowledge Extraction]
    end

    subgraph D2 [Domain 2: Knowledge Core]
        D2[Store & maintain]
        E4[Engine 4: Knowledge Storage]
    end

    subgraph D3 [Domain 3: Knowledge Intelligence]
        D3[Retrieve & reason]
        E5[Engine 5: Retrieval Intelligence]
        E6[Engine 6: Context Delivery]
    end

    subgraph D4 [Domain 4: Knowledge Consumption]
        D4[Deliver to consumers]
        CONS[CLI, REST API, IDE, Web Dashboard, AI Agents]
    end

    DOM --> D1 & D2 & D3 & D4
    D1 --- E1 & E2 & E3
    D2 --- E4
    D3 --- E5 & E6
    D4 --- CONS
```

---

## 4 Domains

### Domain 1: Knowledge Acquisition
Collect raw project data and convert to normalized, structured knowledge.

**Responsibilities:**
- Connect to Git, Confluence, Jira, Documents, API specs via pluggable connectors
- Parse code structure at AST level (symbols, dependencies, call graphs)
- Extract explicit knowledge: entities, relationships, decisions, business rules
- Assign confidence scores (0.0-1.0) to all extracted knowledge
- Enforce source traceability (every KnowledgeObject MUST have SourceReference)

**Engines:**
| Engine | Role | Key Output |
|--------|------|------------|
| 1. Ingestion | Connect, sync, normalize | Normalized RawItems (lifecycle=DISCOVERED) |
| 2. Code Intelligence | Parse code structurally | CodeEntities + CodeRelationships |
| 3. Knowledge Extraction | Convert to explicit knowledge | KnowledgeObjects (EXTRACTED, scored) |

**Supported Sources:**
| Source | Connector | Sync Mode | Data Type |
|--------|-----------|-----------|-----------|
| Git Repository | `GitSourceConnector` | Push event / Schedule (5m) | Code files, commits, branches |
| Confluence | `ConfluenceSourceConnector` | Webhook / Schedule (hourly) | Pages, comments, attachments |
| Jira | `JiraSourceConnector` | Webhook / Schedule (15min) | Issues, fields, comments, transitions |
| Documents | `DocumentSourceConnector` | File watcher / On-change | Markdown, PDF, HTML, OpenAPI |
| API Specs | `ApiSpecConnector` | Schedule (daily) | OpenAPI 3.x, GraphQL, Protobuf |

**Quality Gates (before leaving domain):**
| Gate | Check | Action if Failed |
|------|-------|-----------------|
| Source reference | Every KnowledgeObject has >= 1 SourceReference | Reject; send back to Ingestion |
| Content non-empty | content field is not blank | Reject; log warning |
| Confidence assigned | confidence is set (0.0 - 1.0) | Default to 0.5 (LLM) or 1.0 (rule) |
| Lifecycle state valid | State is DISCOVERED, EXTRACTED, or VALIDATING | Reject; log error |

---

### Domain 2: Knowledge Core
Store and maintain the canonical memory of the project.

**Responsibilities:**
- Persist knowledge across 4 storage layers (Vector, Graph, Metadata, Raw)
- Maintain the semantic model (entity types, relationship types, lifecycle)
- Ensure data integrity and source traceability
- Serve as the single source of truth for all queries

**Engines:**
| Engine | Role | Storage Layers |
|--------|------|----------------|
| 4. Knowledge Storage | Persist knowledge | Vector + Graph + Metadata + Raw |

**Storage Layers:**
| Layer | Purpose | Dev Technology | Prod Technology | Key Operations |
|-------|---------|----------------|-----------------|----------------|
| Vector Store | Semantic similarity search | ChromaDB | pgvector | upsert, query, delete |
| Graph Store | Relationship traversal | NetworkX | Neo4j | neighbors, shortest_path, subgraph |
| Metadata Store | Structured filtering & traceability | SQLite + SQLAlchemy | PostgreSQL | CRUD, lifecycle filtering, source queries |
| Raw Sources | Original data preservation | Local FS | S3 / MinIO | Store, retrieve by hash |


---

### Domain 3: Knowledge Intelligence
Find and reason over knowledge intelligently.

**Responsibilities:**
- Understand user intent from natural language queries
- Execute hybrid retrieval (vector + keyword + graph) with RRF fusion
- Rerank and deduplicate results
- Assemble model-ready context packages with quality guarantees

**Engines:**
| Engine | Role | Key Output |
|--------|------|------------|
| 5. Retrieval Intelligence | Find relevant knowledge | RelevantKnowledgeSet (ranked, deduplicated) |
| 6. Context Delivery | Assemble LLM-ready context | ContextPackage (model-agnostic) |

**Retrieval Pipeline (Engine 5):**
```
Query → Intent Detection → Query Planning → Hybrid Retrieval → Reranking → Dedup → Results
```

**Intent Classification (8 types):**
| Intent | Example Query | Primary Strategy |
|--------|---------------|------------------|
| CODE_UNDERSTANDING | "How does PaymentService work?" | Vector + Graph |
| REQUIREMENT_TRACEABILITY | "Which stories implement auth?" | Graph + Keyword |
| ARCHITECTURE | "Why did we choose Kafka?" | Vector |
| IMPACT_ANALYSIS | "What breaks if I change X?" | Graph traversal |
| BUG_INVESTIGATION | "Why is checkout failing?" | Keyword + Vector |
| API_USAGE | "How do I call the payment API?" | Keyword + Graph |
| COMPARISON | "Compare Stripe vs PayPal" | Vector + Keyword |
| SUMMARY | "Summarize the payment module" | Vector |

**Context Package Schema (Engine 6):**
```python
class ContextPackage(BaseModel):
    query: str                              # Original user query
    knowledge: list[KnowledgeChunk]         # Ranked knowledge snippets
    relationships: list[RelationshipChunk]  # Entity relationships
    confidence: float                       # Overall confidence (0.0-1.0)
    sources: list[SourceReference]          # Deduplicated source references
    lifecycle_states: list[str]             # Which states are represented
    warnings: list[str] = []                # e.g., "Low confidence results included"
    intent: str = ""                        # Classified intent type
    search_stats: SearchStats = None        # How many results per strategy
    compression_ratio: float = 1.0          # Original size / final size
```

**Compression Tiers (Engine 6):**
| Tier | Strategy | When Applied |
|------|----------|--------------|
| 1 | Confidence-based pruning | Remove chunks with confidence < threshold |
| 2 | Lifecycle-based pruning | Remove UPDATED/SUPERSEDED chunks |
| 3 | Relevance-based truncation | Keep top-K by relevance_score |
| 4 | Content compression | Summarize long chunks via LLM |
| 5 | Relationship pruning | Remove low-confidence relationships |

---

### Domain 4: Knowledge Consumption
Deliver knowledge to all types of consumers.

**Responsibilities:**
- Serve Human developers (CLI, web dashboard)
- Serve AI Agents (Claude, GPT, Gemini, custom agents)
- Serve Applications (IDE plugins, CI/CD, dashboards)
- Maintain model independence (any LLM via adapter layer)

**Consumer Types:**
| Type | Examples | Interface |
|------|----------|-----------|
| Human | Developers, Architects, New hires | CLI, Web Dashboard |
| AI Agent | Claude Code, Cline, Cursor, custom agents | Agent SDK, MCP |
| Application | IDE plugins, dashboards, CI/CD | REST API, LSP |
| Model | Claude, GPT, Gemini, Local LLM | Model Adapter |

---

## 6 Execution Capabilities (Engines)

| # | Engine | Domain | Input | Output |
|---|--------|--------|-------|--------|
| 1 | **Ingestion** | Acquisition | Source APIs, file systems, webhooks | Normalized RawItems (DISCOVERED) |
| 2 | **Code Intelligence** | Acquisition | Source code files | CodeEntities + CodeRelationships |
| 3 | **Knowledge Extraction** | Acquisition | RawItems + CodeEntities | KnowledgeObjects (EXTRACTED, scored) |
| 4 | **Knowledge Storage** | Core | KnowledgeObjects | Persisted across 4 layers |
| 5 | **Retrieval Intelligence** | Intelligence | User query | RelevantKnowledgeSet |
| 6 | **Context Delivery** | Intelligence | RelevantKnowledgeSet | ContextPackage |

---

## Data Flow

```
Git/Confluence/Jira/Documents/API Specs
           |
           v
+-------------------+
| 1. Ingestion      |--> Normalized RawItems (DISCOVERED)
|    Engine         |    (SourceConnector protocol)
+-------------------+
           |
           +-----> (code files) ----> +-------------------+
           |                            | 2. Code          |
           |                            |    Intelligence  |--> CodeEntities
           |                            |    Engine        |    + Relationships
           |                            +-------------------+
           |
           |  (non-code docs)
           +------------------------------------------+
                                                      v
                                           +-------------------+
                                           | 3. Knowledge     |
                                           |    Extraction    |--> KnowledgeObjects
                                           |    Engine        |     (EXTRACTED, scored)
                                           +-------------------+
                                                      |
                                                      v
                                           +-------------------+
                                           | 4. Knowledge     |--> Persisted
                                           |    Storage       |     across 4 layers
                                           |    Engine        |     (Vector + Graph +
                                           +-------------------+      Metadata + Raw)
                                                      |
                                                      v
                                           +-------------------+
                                           | 5. Retrieval     |--> RelevantKnowledgeSet
                                           |    Intelligence  |     (ranked, deduped)
                                           |    Engine        |
                                           +-------------------+
                                                      |
                                                      v
                                           +-------------------+
                                           | 6. Context       |--> ContextPackage
                                           |    Delivery      |     (model-agnostic)
                                           |    Engine        |
                                           +-------------------+
                                                      |
                                                      v
                                           Any LLM / Consumer
```

---

## Knowledge Model (Semantic Foundation)

The Knowledge Model is the semantic foundation that every engine must respect. Defined in `core/3-knowledge-model.md`.

| Component | Count | Description |
|-----------|-------|-------------|
| **Entity Types** | 23 | Complete taxonomy: 11 code + 4 project + 4 document + 4 system |
| **Relationship Types** | 15 | IMPLEMENTS, DEPENDS_ON, CALLS, USES, OWNS, DOCUMENTS, REQUIRES, SUPERSEDES, RELATED_TO, AFFECTS, PART_OF, TRACES_TO, CONTAINS, EXTENDS, IMPLEMENTS_IFACE |
| **Lifecycle States** | 8 | DISCOVERED → EXTRACTED → VALIDATING → ACTIVE → UPDATED → SUPERSEDED → DEPRECATED → ARCHIVED |
| **SourceReference** | 5 types | GIT, CONFLUENCE, JIRA, DOCUMENT, API_SPEC with type-specific fields |
| **KnowledgeObject** | — | Fundamental data structure wrapping all above |

---

## Cross-Cutting Capabilities

These run across ALL engines:

| Capability | Description | Applied In |
|------------|-------------|------------|
| **Lifecycle** | 8-state state machine, 14 valid transitions, staleness detection | All engines |
| **Traceability** | Every knowledge traces back to source via SourceReference | Engine 1, 3, 4, 5, 6 |
| **Governance & Trust** | RBAC (5 roles), audit logging, data classification (4 levels) | Engine 4, 5, 6, CLI, API |
| **Evaluation** | 4 quality dimensions, test protocols, feedback loop | All engines |

---

## Governance & Trust Model

> Full details in `core/9-governance-and-trust-model.md`

**Security Model:**
| Layer | Mechanism | Implementation |
|-------|-----------|----------------|
| Authentication | OAuth2 / API Key / Token | Middleware on API; CLI credential store |
| Authorization | RBAC (5 roles) | Permission checks in engine pipelines |
| Data Classification | Tag-based (4 levels) | Tags on KnowledgeObjects |
| Audit Logging | Immutable hash chain | Append-only log table |
| Encryption | At rest + in transit | TLS for transit; AES-256 for secrets |

**RBAC Roles:**
| Role | Permissions | Typical User |
|------|------------|--------------|
| ADMIN | Full access; manage sources; configure engines | DevOps / Platform team |
| ARCHITECT | Read all; trigger re-extraction; view audit | Lead architect |
| DEVELOPER | Read assigned projects; run ingestion for own repos | Software engineer |
| VIEWER | Read-only; limited to public knowledge | External contributor |
| SERVICE | Programmatic access for CI/CD | Bot / automation |

**Data Classification:**
| Level | Sources | Retention |
|-------|---------|-----------|
| PUBLIC | Public repos, public docs | Indefinite |
| INTERNAL | Private repos (team), team Confluence | 2 years after project close |
| CONFIDENTIAL | Restricted Confluence, proprietary code | Project lifetime + 1 year |
| RESTRICTED | HR/Finance docs, security configs | Compliance-driven (7+ years) |

**Trust Boundaries:**
```
EXTERNAL TRUST (Git/Confluence/Jira authenticated APIs)
        |
        | (ingestion with source credentials)
        v
PKH INTERNAL ZONE (Knowledge Core: structured, traced, scored)
        |
        | (retrieval with user permissions)
        v
CONSUMER ZONE (LLM/IDE/Human receives ContextPackage)
```

**Key trust rules:**
1. PKH never modifies source data. Sources are read-only.
2. PKH never exposes knowledge beyond the user's source-level permissions.
3. PKH never claims extracted knowledge is 100% accurate (confidence scores prevent this).
4. PKH logs every access for accountability.

---

## Evaluation Framework

> Full details in `core/8-evaluation-framework.md`

**4 Quality Dimensions:**
| Dimension | Metrics | Target | Measurement |
|-----------|---------|--------|-------------|
| Knowledge Quality | Coverage %, entity accuracy | > 80% | Source count vs indexed count |
| Retrieval Quality | Precision@k, Recall@k, NDCG | P@5 > 0.85 | Test set evaluation |
| Context Quality | Token efficiency, source coverage | > 95% fit rate | ContextPackage validation |
| System Quality | Latency, availability, error rate | P99 < 1000ms | Production metrics |

**Feedback Loop:**
```
User Query → ContextPackage → LLM Answer → User Rating → Feedback
                                                              |
                                                              v
                                                    Retrain/Retune
                                                    Extraction Rules
                                                    Retrieval Weights
```

---

## Design Principles (Recap)

1. **Knowledge First** -- Model is replaceable, knowledge is permanent
2. **Source Traceability** -- Every knowledge answers "where did this come from?"
3. **Never Trust Extracted Knowledge Completely** -- Confidence scores always attached
4. **Model Independence** -- Any LLM can be swapped via adapters

See `core/1-vision-and-design-principles.md` for full details.