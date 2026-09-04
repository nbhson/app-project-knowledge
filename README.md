# PKH - Project Knowledge Harness

> Transform fragmented project information into a continuously evolving, connected, model-independent knowledge system.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA SOURCES                             │
│  Git Repo   │   Confluence   │   Jira   │   Documents      │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ ① INGESTION ENGINE                                         │
│    Connectors │ Sync │ Webhooks │ Change Detection          │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ ② CODE INTELLIGENCE ENGINE                                 │
│    AST │ Symbols │ Dependencies │ Call Graph                │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ ③ KNOWLEDGE EXTRACTION ENGINE                              │
│    Entity │ Relationship │ Concept │ Decision Extraction    │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ ④ KNOWLEDGE STORAGE ENGINE                                 │
│    Vector Store │ Graph Store │ Metadata Store             │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ ⑤ RETRIEVAL INTELLIGENCE ENGINE                            │
│    Intent │ Query Plan │ Hybrid Retrieval │ Reranking       │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ ⑥ CONTEXT DELIVERY ENGINE                                  │
│    Assembly │ Compression │ Model Adapters                 │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
              Claude │ GPT │ Gemini │ Local LLM
```

## Design Principles

1. **Knowledge First** — Model is replaceable, knowledge is permanent
2. **Source Traceability** — Every knowledge traces back to its source
3. **Never Trust Extracted Knowledge Completely** — Confidence scores always attached
4. **Model Independence** — Any LLM can be swapped without changing knowledge core

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Initialize config
pkh init

# Ingest a project
pkh ingest --source /path/to/repo --source confluence://my-space --source jira://MYPROJECT

# Query knowledge
pkh query "How does payment flow work?"

# Get context for AI agent
pkh context --query "Explain the authentication module"
```

## Configuration

Edit `config/settings.yaml`:

```yaml
sources:
  git:
    paths:
      - ./my-project
  confluence:
    base_url: https://your-company.atlassian.net
    space_keys:
      - PROJ
    api_token: ${CONFLUENCE_API_TOKEN}
  jira:
    base_url: https://your-company.atlassian.net
    project_keys:
      - PROJ
    api_token: ${JIRA_API_TOKEN}

storage:
  vector:
    provider: chroma
    path: ./data/vectorstore
  graph:
    provider: networkx
    path: ./data/graph
  metadata:
    provider: sqlite
    path: ./data/metadata.db

retrieval:
  top_k: 10
  hybrid: true
  rerank: true

adapters:
  default: openai
  models:
    openai:
      model: gpt-4o
      api_key: ${OPENAI_API_KEY}
```

## Core Concepts

### Knowledge Types
- **Code Knowledge** — Classes, functions, dependencies, call graphs
- **Architecture Knowledge** — ADRs, design decisions, patterns
- **Requirement Knowledge** — Jira stories, epics, acceptance criteria
- **Business Knowledge** — Rules, constraints, domain concepts
- **Document Knowledge** — Confluence pages, specs, docs

### Knowledge Lifecycle
```
DISCOVER → EXTRACT → VALIDATE → ACTIVATE → UPDATE → SUPERSEDE → DEPRECATE → ARCHIVE
```

### Source of Truth
| Knowledge | Source of Truth |
|-----------|----------------|
| Code implementation | Git Repository |
| Requirement | Jira |
| Architecture decision | Confluence / ADR |
| API Contract | OpenAPI |
| Deployment | Infrastructure Config |

