# Knowledge Consumption Domain

> Domain 4: Deliver knowledge to all types of consumers.

---

## Responsibility

The Knowledge Consumption domain is responsible for serving knowledge to all consumer types -- humans, AI agents, applications, and models -- through appropriate delivery channels while maintaining model independence.

### Core Responsibilities

1. **Serve Human developers** -- search, ask questions, understand project context
2. **Serve AI Agents** -- provide structured knowledge for reasoning and action
3. **Serve Applications** -- power IDE plugins, dashboards, CI/CD integration
4. **Maintain model independence** -- any LLM works via the adapter layer
5. **Provide consistent interfaces** -- CLI, API, IDE extension, agent SDK

---

## Consumer Types

### Human Consumers

| Persona | Use Case | Interface | Expected Output |
|---------|----------|-----------|-----------------|
| **Developer** | Search code, ask questions about project | CLI, Web Dashboard | Natural language answers with source links |
| **Architect** | Review decisions, trace requirements | Web Dashboard, CLI | Decision summaries, traceability reports |
| **New Hire** | Understand project structure and history | Web Dashboard, CLI | Onboarding overview, module map |

### AI Agent Consumers

| Consumer | Use Case | Interface | Expected Output |
|----------|----------|-----------|-----------------|
| **Claude Code / Cline** | AI coding assistant | Agent SDK / MCP | ContextPackage for tool calls |
| **Custom Agents** | Domain-specific automation | Agent SDK | ContextPackage + structured tools |
| **Multi-Agent Systems** | Collaborative problem solving | Agent SDK | Shared ContextPackage, tool registry |

### Application Consumers

| Consumer | Use Case | Interface | Expected Output |
|----------|----------|-----------|-----------------|
| **IDE Plugin** | Intelligent code navigation | LSP / Extension API | Code hints, related knowledge on hover |
| **Dashboard** | Architecture review | Web HTTP API | Knowledge visualizations, charts |
| **CI/CD** | Impact analysis, code review | REST API / Webhook | PR comments with knowledge context |

### Model Consumers

| Consumer | Use Case | Interface | Expected Output |
|----------|----------|-----------|-----------------|
| **Claude / GPT / Gemini** | Reasoning over project knowledge | Model Adapter | Formatted prompt with knowledge |
| **Local LLM** | Offline reasoning | Local Adapter | Plain text context |
| **Any LLM** | Custom integrations | Custom Adapter | Configurable format |

---

## Delivery Channels

| Channel | Protocol | Use Case | Auth | Rate Limit |
|---------|----------|----------|------|------------|
| **CLI** | stdin/stdout, TTY | Developer local usage | Local user | N/A |
| **REST API** | HTTP/HTTPS, JSON | Programmatic access | API Key / OAuth2 | Configurable |
| **IDE Extension** | LSP / native protocol | Code navigation | User session | N/A |
| **Web Dashboard** | HTTP/HTTPS | Architecture review | SSO / OAuth2 | Per-user |
| **Agent SDK** | LangChain / CrewAI / MCP | AI coding assistant | API Key | Per-key |
| **Webhook** | HTTP POST | CI/CD integration | Token | Per-event |

---

## Model Independence

```
                    ContextPackage (canonical, model-agnostic)
                    /         |         \         \
                   v          v          v          v
            ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
            │Claude    │ │GPT       │ │Gemini    │ │Local LLM │
            │Adapter    │ │Adapter    │ │Adapter    │ │Adapter    │
            └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

Switching models = changing config only. No code changes.

### Config Example
```yaml
consumption:
  model:
    provider: anthropic
    model_id: claude-sonnet-4-20250514
    temperature: 0.1
    max_tokens: 4096
  
  # To switch to GPT:
  # model:
  #   provider: openai
  #   model_id: gpt-4o
  # (zero code changes required)
```

---

## API Specification (REST)

| Endpoint | Method | Description | Input | Output |
|----------|--------|-------------|-------|--------|
| `/query` | POST | Natural language query | `{query, model?, top_k?}` | `{answer, sources[], context}` |
| `/context` | POST | Raw context package | `{query, model?, top_k?}` | `ContextPackage` |
| `/knowledge/{id}` | GET | Get single knowledge object | path: id | `KnowledgeObject` |
| `/knowledge` | GET | Search knowledge | query params | `list[KnowledgeObject]` |
| `/graph/explore` | POST | Explore knowledge graph | `{seed, depth}` | `{nodes, edges}` |
| `/sources/status` | GET | Source sync status | none | `list[SourceStatus]` |
| `/health` | GET | Health check | none | `{status, uptime}` |

---

## CLI Interface

```bash
# Query the knowledge base
pkh query "How does authentication work?"
pkh query "What breaks if I change PaymentService?" --depth 3

# Get raw context for AI agents
pkh context --query "Explain the payment flow" --model claude

# Explore the knowledge graph
pkh graph --entity "PaymentService" --depth 2

# Check ingestion status
pkh status

# Run a full sync
pkh ingest --sync
```