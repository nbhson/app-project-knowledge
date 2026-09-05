# Project Structure

> Overview of the repository organization for Project Knowledge Harness (PKH).

## Repository Layout

```
project-knowledge-harness/
│
├── README.md                          # Project overview, quick start, tech stack summary
├── LICENSE                            # MIT License
├── .gitignore                         # Git ignore rules (.DS_Store, etc.)
│
├── docs/                              # All documentation files
│   ├── core/                          # Core architecture and knowledge model
│   │   ├── 1-vision-and-design-principles.md
│   │   ├── 2-architecture.md
│   │   ├── 3-knowledge-model.md
│   │   ├── 4-knowledge-lifecycle.md
│   │   ├── 5-source-of-truth-model.md
│   │   ├── 6-retrieval-strategy.md
│   │   ├── 7-context-contract.md
│   │   ├── 8-evaluation-framework.md
│   │   └── 9-governance-and-trust-model.md
│   │
│   ├── domains/                       # Domain-specific documentation
│   │   ├── knowledge-acquisition.md
│   │   ├── knowledge-core.md
│   │   ├── knowledge-intelligence.md
│   │   ├── knowledge-consumption.md
│   │   └── knowledge-update-loop.md
│   │
│   ├── engines/                       # Engine-specific documentation
│   │   ├── ingestion-engine.md
│   │   ├── code-intelligence-engine.md
│   │   ├── knowledge-extraction-engine.md
│   │   ├── knowledge-storage-engine.md
│   │   ├── retrieval-intelligence-engine.md
│   │   └── context-delivery-engine.md
│   │
│   ├── layers/                        # Layer-level architecture documents
│   │   ├── philosophy.md
│   │   ├── system-design.md
│   │   ├── knowledge-design.md
│   │   └── quality-and-trust.md
│   │
│   ├── tech-stack.md                  # Detailed technology stack documentation
│   ├── overall-architecture.md        # Complete system architecture overview
│   ├── deployment-guide.md            # Development and production deployment instructions
│   ├── troubleshooting-guide.md       # Common issues and solutions
│   ├── glossary.md                    # Key terminology and definitions
│   │
│   └── plan/                          # Planning documents
│       └── plan.md
│
└── (source code)                      # Python source code (to be added)
    ├── pkh/                           # Main package
    │   ├── __init__.py
    │   ├── models/                    # Pydantic models (KnowledgeObject, etc.)
    │   ├── engines/                   # Engine implementations
    │   ├── storage/                   # Storage layer implementations
    │   ├── retrieval/                 # Retrieval and query logic
    │   ├── ingestion/                 # Source connectors and ingestion pipeline
    │   ├── adapters/                  # LLM adapters
    │   ├── cli/                       # CLI commands (Typer)
    │   ├── api/                       # FastAPI routes and middleware
    │   ├── config/                    # Configuration management
    │   └── utils/                     # Utility functions
    │
    ├── pyproject.toml                 # Poetry/project configuration
    ├── requirements.txt               # Python dependencies
    ├── config/                        # Configuration files
    │   ├── settings.yaml              # Default settings
    │   ├── settings.dev.yaml          # Development settings
    │   └── settings.prod.yaml         # Production settings
    │
    ├── tests/                         # Test suite
    │   ├── conftest.py                # pytest fixtures
    │   ├── test_models.py
    │   ├── test_engines/
    │   ├── test_storage/
    │   └── test_api/
    │
    └── docker-compose.yml             # Development orchestration
```

## Documentation Index

### Core Documents (`docs/core/`)
- **1-vision-and-design-principles.md**: Project vision, design philosophy
- **2-architecture.md**: High-level system architecture
- **3-knowledge-model.md**: Semantic model, entity types, relationship types
- **4-knowledge-lifecycle.md**: 8-state lifecycle machine, transitions
- **5-source-of-truth-model.md**: Source reference system
- **6-retrieval-strategy.md**: Retrieval strategies and hybrid search
- **7-context-contract.md**: ContextPackage specification
- **8-evaluation-framework.md**: Quality measurement and metrics
- **9-governance-and-trust-model.md**: RBAC, audit, security

### Domain Documents (`docs/domains/`)
- **knowledge-acquisition.md**: Domain 1 - Collecting and processing sources
- **knowledge-core.md**: Domain 2 - Storage and persistence
- **knowledge-intelligence.md**: Domain 3 - Retrieval and reasoning
- **knowledge-consumption.md**: Domain 4 - Delivery to consumers
- **knowledge-update-loop.md**: Incremental sync and update mechanisms

### Engine Documents (`docs/engines/`)
- **ingestion-engine.md**: Engine 1 - Source connector and sync pipeline
- **code-intelligence-engine.md**: Engine 2 - AST parsing and code analysis
- **knowledge-extraction-engine.md**: Engine 3 - Knowledge extraction and scoring
- **knowledge-storage-engine.md**: Engine 4 - Multi-layer storage management
- **retrieval-intelligence-engine.md**: Engine 5 - Hybrid retrieval and ranking
- **context-delivery-engine.md**: Engine 6 - ContextPackage assembly and compression

### Other Documentation
- **overall-architecture.md**: Complete architecture diagram and data flows
- **tech-stack.md**: Detailed technology breakdown by category
- **deployment-guide.md**: Dev/prod setup, Docker, Kubernetes, CI/CD
- **troubleshooting-guide.md**: Common issues and solutions
- **glossary.md**: Key terminology definitions

## Getting Started

1. **Read**: Start with `docs/core/1-vision-and-design-principles.md`
2. **Architecture**: Then `docs/overall-architecture.md`
3. **Tech Details**: Check `docs/tech-stack.md`
4. **Deployment**: Follow `docs/deployment-guide.md`
5. **Implementation**: Explore `docs/engines/` for each component

## Key Design Documents by Topic

| Topic | Primary Document | Supporting |
|-------|-----------------|------------|
| Vision & Principles | `docs/core/1-vision-and-design-principles.md` | `docs/layers/philosophy.md` |
| Architecture | `docs/core/2-architecture.md` | `docs/overall-architecture.md` |
| Data Model | `docs/core/3-knowledge-model.md` | `docs/core/5-source-of-truth-model.md` |
| Storage | `docs/engines/knowledge-storage-engine.md` | `docs/domains/knowledge-core.md` |
| Retrieval | `docs/core/6-retrieval-strategy.md` | `docs/engines/retrieval-intelligence-engine.md` |
| Deployment | `docs/deployment-guide.md` | `docs/tech-stack.md` |
| Governance | `docs/core/9-governance-and-trust-model.md` | `docs/layers/quality-and-trust.md` |

---

> This structure organizes documentation by abstraction level (core → domain → engine → layer) for progressive understanding.