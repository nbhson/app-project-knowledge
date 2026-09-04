# Architecture

                         DATA SOURCES
                              │
        ┌─────────────────────┼─────────────────────┐
        ↓                     ↓                     ↓

      CODE              DOCUMENTS               PROJECT

    Git Repo            Confluence               Jira
       │                    │                      │
       ↓                    ↓                      ↓

┌────────────────────────────────────────────────────┐
│ INGESTION LAYER │
│ │
│ Code Parser │ Document Parser │ Connector │
└───────────────────────┬────────────────────────────┘
↓
┌────────────────────────────────────────────────────┐
│ KNOWLEDGE EXTRACTION │
│ │
│ Entity Extraction │
│ Relationship Extraction │
│ Semantic Analysis │
│ Metadata Extraction │
└───────────────────────┬────────────────────────────┘
↓
┌────────────────────────────────────────────────────┐
│ KNOWLEDGE MODEL │
│ │
│ Semantic Graph Structured │
│ Knowledge Knowledge Knowledge │
└──────────────┬────────────┬──────────────┬────────┘
↓ ↓ ↓

           Vector DB      Graph DB       Metadata DB
                │            │              │
                └────────────┼──────────────┘
                             ↓

┌────────────────────────────────────────────────────┐
│ RETRIEVAL HARNESS │
│ │
│ Intent Detection │
│ Query Planning │
│ Hybrid Retrieval │
│ Graph Traversal │
│ Reranking │
│ Context Assembly │
└───────────────────────┬────────────────────────────┘
↓
┌────────────────────────────────────────────────────┐
│ MODEL ADAPTER │
│ │
│ Claude │ GPT │ Gemini │ DeepSeek │ Local LLM │
└────────────────────────────────────────────────────┘

# Mapping to 6 engines

┌───────────────────────────────────────────────────────┐
│ DATA SOURCES │
│ │
│ Git │ Code │ Confluence │ Jira │ Documents │ APIs │
└───────────────────────────┬───────────────────────────┘
│
▼
┌───────────────────────────────────────────────────────┐
│ ① INGESTION ENGINE │
│ │
│ Connectors │
│ Sync │
│ Webhooks │
│ Change Detection │
│ Version Tracking │
└───────────────────────────┬───────────────────────────┘
│
▼
┌───────────────────────────────────────────────────────┐
│ ② CODE INTELLIGENCE ENGINE │
│ │
│ AST │
│ Symbols │
│ Dependencies │
│ Call Graph │
│ Module Analysis │
└───────────────────────────┬───────────────────────────┘
│
▼
┌───────────────────────────────────────────────────────┐
│ ③ KNOWLEDGE EXTRACTION ENGINE │
│ │
│ Entity Extraction │
│ Relationship Extraction │
│ Concept Detection │
│ Decision Detection │
│ Business Rule Extraction │
└───────────────────────────┬───────────────────────────┘
│
▼
╔═══════════════════════════════════════════════════════╗
║ KNOWLEDGE CORE ║
║ ║
║ ④ KNOWLEDGE STORAGE ENGINE ║
║ ║
║ Vector Store │ Graph Store │ Metadata │ Raw Sources ║
╚═══════════════════════════╤═══════════════════════════╝
│
▼
┌───────────────────────────────────────────────────────┐
│ ⑤ RETRIEVAL INTELLIGENCE ENGINE │
│ │
│ Intent Detection │
│ Query Planning │
│ Hybrid Retrieval │
│ Graph Traversal │
│ Reranking │
└───────────────────────────┬───────────────────────────┘
│
▼
┌───────────────────────────────────────────────────────┐
│ ⑥ CONTEXT DELIVERY ENGINE │
│ │
│ Context Assembly │
│ Context Compression │
│ Context Contract │
│ Model Adapters │
└───────────────────────────┬───────────────────────────┘
│
┌─────────────┼─────────────┐
▼ ▼ ▼
Claude GPT Local LLM
