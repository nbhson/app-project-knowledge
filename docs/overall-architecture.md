╔══════════════════════════════════════════════════════════════════════╗
║ PROJECT KNOWLEDGE HARNESS ║
║ ║
║ Transform fragmented project information into a continuously ║
║ evolving, connected, traceable, model-independent knowledge system ║
╚══════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────┐
│ DOMAIN 1 │
│ KNOWLEDGE ACQUISITION │
│ │
│ ┌──────────────────────┐ ┌──────────────────────────────┐ │
│ │ ① INGESTION ENGINE │────▶│ ② CODE INTELLIGENCE ENGINE │ │
│ └──────────────────────┘ └──────────────┬───────────────┘ │
│ │ │
│ ▼ │
│ ┌──────────────────────────────┐ │
│ │③ KNOWLEDGE EXTRACTION ENGINE │ │
│ └──────────────────────────────┘ │
└──────────────────────────────────────┬──────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────┐
│ DOMAIN 2 │
│ KNOWLEDGE CORE │
│ │
│ ┌──────────────────────────────────┐ │
│ │ PROJECT KNOWLEDGE MODEL │ │
│ └──────────────────────────────────┘ │
│ │ │
│ ┌──────────────────────┼──────────────────────┐ │
│ ▼ ▼ ▼ │
│ Semantic Knowledge Graph Knowledge Structured Knowledge │
│ │ │ │ │
│ └──────────────────────┼──────────────────────┘ │
│ ▼ │
│ ┌──────────────────────────────────┐ │
│ │ ④ KNOWLEDGE STORAGE ENGINE │ │
│ │ │ │
│ │ Vector │ Graph │ Metadata │ Source│ │
│ └──────────────────────────────────┘ │
└──────────────────────────────────────┬──────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────┐
│ DOMAIN 3 │
│ KNOWLEDGE INTELLIGENCE │
│ │
│ ┌──────────────────────────────────┐ │
│ │⑤ RETRIEVAL INTELLIGENCE ENGINE │ │
│ └────────────────┬─────────────────┘ │
│ │ │
│ ▼ │
│ ┌──────────────────────────────────┐ │
│ │⑥ CONTEXT DELIVERY ENGINE │ │
│ └──────────────────────────────────┘ │
└──────────────────────────────────────┬──────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────┐
│ DOMAIN 4 │
│ KNOWLEDGE CONSUMPTION │
│ │
│ ┌─────────────┬─────────────┬─────────────┐ │
│ ▼ ▼ ▼ ▼ │
│ Human AI Agent IDE API / Apps │
│ │
│ ▼ │
│ Claude / GPT / Gemini / Local LLM │
└─────────────────────────────────────────────────────────────────────┘

Full Domain Mapping

Mình đề xuất hệ thống gồm 4 Core Domains và 4 Cross-Cutting Domains.

DOMAIN 1 — Knowledge Acquisition

Biến raw data thành machine-understandable knowledge.

RAW PROJECT WORLD
↓
Knowledge Acquisition
↓
Normalized / Extracted Knowledge
Engine Mapping
① Ingestion Engine

Input:

Git Repository
Confluence
Jira
Documents
OpenAPI
Database Schema
CI/CD

Responsibility:

Connect
Sync
Fetch
Webhook
Change Detection
Version Tracking
Normalization
② Code Intelligence Engine

Chỉ tập trung vào:

Understanding code structurally.

Source Code
↓
Parser
↓
AST
↓
Symbols
↓
Dependencies
↓
Call Graph

Knowledge tạo ra:

Repository
Module
Package
File
Class
Interface
Function
Method
Dependency
Call Relationship
③ Knowledge Extraction Engine

Đây là nơi:

Raw information → Explicit Knowledge

Ví dụ:

Confluence Page
↓
Entity Extraction
Relationship Extraction
Decision Extraction
Constraint Extraction

Extract:

Entities
Concepts
Requirements
Business Rules
Architecture Decisions
Relationships
Constraints
DOMAIN 2 — Knowledge Core ⭐

Đây là trái tim của toàn bộ Harness.

Không phải Vector DB.

Không phải Neo4j.

Mà là:

Project Knowledge Model
KNOWLEDGE
│
┌────────────────┼────────────────┐
│ │ │
▼ ▼ ▼

    Semantic          Graph          Structured

Knowledge Categories
PROJECT KNOWLEDGE
│
├── Code Knowledge
│
├── Architecture Knowledge
│
├── Requirement Knowledge
│
├── Business Knowledge
│
├── Decision Knowledge
│
├── Document Knowledge
│
└── Operational Knowledge
④ Knowledge Storage Engine

Đây là persistence layer.

Knowledge Object
│
├───────────────┐
▼ ▼
Vector Store Graph Store
│ │
└──────┬────────┘
▼
Metadata Store
│
▼
Source Store
Storage Mapping
Knowledge Storage
Text / Meaning Vector
Relationships Graph
Entities / Metadata Relational
Original content Source/Object Storage
DOMAIN 3 — Knowledge Intelligence

Biết cách tìm, reasoning và tổ chức knowledge.

Đây là điểm khác biệt giữa:

Database

và:

Knowledge System
⑤ Retrieval Intelligence Engine

Input:

Question
Task
Agent Request

Flow:

Query
↓
Intent Understanding
↓
Query Planning
↓
Hybrid Retrieval
↓
Graph Traversal
↓
Filtering
↓
Reranking

Retrieval Sources:

Vector Search
Graph Query
Metadata Filter
Keyword Search
Source Lookup

Output:

Ranked Knowledge Set
⑥ Context Delivery Engine

Retrieval xong chưa phải là output cuối cùng.

Cần:

Retrieved Knowledge
↓
Context Assembly
↓
Deduplication
↓
Prioritization
↓
Compression
↓
Universal Context Contract

Output:

CONTEXT PACKAGE
│
├── Task
├── Relevant Knowledge
├── Relationships
├── Constraints
├── Decisions
├── Source References
└── Confidence

Sau đó:

Universal Context
↓
Model Adapter
↓
Claude / GPT / Gemini / Local
DOMAIN 4 — Knowledge Consumption

Knowledge không chỉ phục vụ chatbot.

                KNOWLEDGE CORE
                       │
       ┌───────────────┼────────────────┐
       │               │                │
       ▼               ▼                ▼

      Human          AI Agent          System

Consumers
Developer
Search
Ask Question
Understand Project
AI Coding Agent
Claude Code
Cline
Cursor
Custom Agent
Internal Application
Architecture Dashboard
Project Explorer
Knowledge Search
Automation
CI/CD
Code Review
Impact Analysis
Test Planning
🔄 Cross-Cutting Domain 1 — Knowledge Lifecycle

Cái này chạy xuyên suốt tất cả Engines.

DISCOVER
↓
INGEST
↓
EXTRACT
↓
VALIDATE
↓
ACTIVATE
↓
UPDATE
↓
SUPERSEDE
↓
DEPRECATE
↓
ARCHIVE

Applies to:

Code
Documents
Requirements
Architecture
Decisions
🔗 Cross-Cutting Domain 2 — Traceability

Mọi knowledge phải trace ngược được.

AI Answer
↓
Context
↓
Knowledge
↓
Extraction
↓
Original Source

Ví dụ:

PaymentService
↓ IMPLEMENTS
JIRA-123
↓ DOCUMENTED_BY
Confluence Page
🛡️ Cross-Cutting Domain 3 — Governance & Trust
Authentication
Authorization
Access Control
Permission Awareness
Data Classification
Audit Log
Confidence
Source Provenance

Nguyên tắc:

Harness cannot give access to knowledge that the user cannot access in the original system.

📊 Cross-Cutting Domain 4 — Evaluation & Observability
HARNESS
│
┌──────────┼──────────┐
▼ ▼ ▼

     Quality     Performance   Cost

Metrics:

Knowledge Quality
Extraction Accuracy
Relationship Accuracy
Stale Knowledge Rate
Retrieval Quality
Precision
Recall
Relevance
Source Coverage
Context Quality
Context Relevance
Context Size
Redundancy
System
Latency
Storage
Embedding Cost
LLM Cost
🔥 Complete Mapping: Layer → Domain → Engine
Layer Domain Engine / Component Responsibility
Source Project World Git / Jira / Confluence Source of Truth
Acquisition Knowledge Acquisition ① Ingestion Collect & Sync
Acquisition Knowledge Acquisition ② Code Intelligence Understand Code
Acquisition Knowledge Acquisition ③ Knowledge Extraction Convert information → knowledge
Core Knowledge Core Knowledge Model Define entities & relationships
Core Knowledge Core ④ Storage Persist knowledge
Intelligence Knowledge Intelligence ⑤ Retrieval Find relevant knowledge
Intelligence Knowledge Intelligence ⑥ Context Delivery Build model-ready context
Consumption Knowledge Consumption Human Consume knowledge
Consumption Knowledge Consumption AI Agent Reason / Execute
Consumption Knowledge Consumption API / Apps Integrate knowledge
Cross-cutting Lifecycle Lifecycle System Keep knowledge current
Cross-cutting Trust Governance Permission & provenance
Cross-cutting Quality Evaluation Measure quality
Cross-cutting System Observability Monitor system
