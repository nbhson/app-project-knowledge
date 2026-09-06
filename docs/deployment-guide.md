# Deployment Guide

> How to deploy PKH in development and production environments.
> [[glossary]]

---

## Development Deployment

> ✅ **`src/` exists (scaffold 06/09).** Các lệnh `pkh ingest/query` đã scaffold trong `src/pkh/cli` + `src/pkh/api`; MVP 10 ngày (Git local + SQLite/Chroma/NetworkX) chạy được với `PYTHONPATH=src pytest`. Xem `docs/plan/plan.md#mvp-scope` và `docs/plan/fix-plan.md` cho gaps còn lại.

### Prerequisites

- Python 3.10+
- Git
- Optional: Docker (for database services — chỉ cần cho prod Neo4j/pgvector, MVP không cần)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/org/project-knowledge-harness.git
cd project-knowledge-harness

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Initialize configuration
pkh init

# Run with development databases (SQLite, ChromaDB, NetworkX)
pkh ingest --source git://https://github.com/org/project

# Query knowledge
pkh query "How does the payment flow work?"
```

### Development Docker Compose

For local development with real database services:

```yaml
# docker-compose.dev.yml
version: '3.8'
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: pkh
      POSTGRES_USER: pkh
      POSTGRES_PASSWORD: pkh_dev
    ports:
      - "5432:5432"
    volumes:
      - postgres_dev_data:/var/lib/postgresql/data

  pgvector:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: pkh_vector
      POSTGRES_USER: pkh
      POSTGRES_PASSWORD: pkh_dev
    ports:
      - "5433:5432"

  neo4j:
    image: neo4j:5
    environment:
      NEO4J_AUTH: neo4j/pkh_dev
    ports:
      - "7474:7474"
      - "7687:7687"

volumes:
  postgres_dev_data:
```

```bash
# Start development databases
docker-compose -f docker-compose.dev.yml up -d

# Update config/settings.yaml for dev databases
pkh init --env dev

# Run tests
pytest

# Run with local databases
pkh ingest --source git://https://github.com/org/project
```

---

## Production Deployment

### Architecture

```
                    ┌─────────────┐
                    │  Load Balancer │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐ ┌───▼────┐ ┌────▼─────┐
        │  API Node 1│ │API Node│ │ API Node  │
        │  (PKH)     │ │  2     │ │   3      │
        └─────┬─────┘ └───┬────┘ └────┬─────┘
              │            │            │
              └────────────┼────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐ ┌───▼────┐ ┌────▼─────┐
        │ Postgres   │ │Neo4j   │ │S3/MinIO  │
        │ (Metadata) │ │(Graph)  │ │ (Raw)   │
        └───────────┘ └────────┘ └──────────┘
```

### Prerequisites (Full — Post-MVP)

> MVP chỉ cần **SQLite + Chroma + NetworkX + Local FS** (không cần Postgres/Neo4j/S3/Redis). Các infra dưới là cho Full prod sau Day 19.

- PostgreSQL 16+ with pgvector extension
- Neo4j 5+ (or compatible graph database)
- Object storage (S3, GCS, or MinIO for local)
- Python 3.10+ runtime
- Redis (optional, for caching)

### Configuration

```yaml
# config/settings.prod.yaml
storage:
  vector:
    provider: pgvector
    connection: postgresql://user:pass@pgvector-host:5432/pkh_vector
  graph:
    provider: neo4j
    connection: bolt://neo4j-host:7687
    auth:
      username: neo4j
      password: ${NEO4J_PASSWORD}
  metadata:
    provider: postgresql
    connection: postgresql://user:pass@postgres-host:5432/pkh
  raw:
    provider: s3
    bucket: pkh-raw-sources
    region: us-east-1
    auth:
      access_key: ${AWS_ACCESS_KEY}
      secret_key: ${AWS_SECRET_KEY}

retrieval:
  top_k: 20
  min_confidence: 0.3
  cache:
    enabled: true
    provider: redis
    connection: redis://redis-host:6379/0
    ttl: 3600  # 1 hour

governance:
  audit:
    enabled: true
    retention_years: 7
  encryption:
    at_rest: true
    key_ref: secrets.KMS_KEY
```

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir .

COPY . .

EXPOSE 8000

CMD ["pkh", "serve", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  pkh-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - PKH_CONFIG_PATH=/app/config/settings.prod.yaml
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - AWS_ACCESS_KEY=${AWS_ACCESS_KEY}
      - AWS_SECRET_KEY=${AWS_SECRET_KEY}
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
    volumes:
      - ./config:/app/config
    depends_on:
      - postgres
      - neo4j
      - redis

  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: pkh
      POSTGRES_USER: pkh
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  pgvector:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: pkh_vector
      POSTGRES_USER: pkh
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - pgvector_data:/var/lib/postgresql/data

  neo4j:
    image: neo4j:5
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}
    volumes:
      - neo4j_data:/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  pgvector_data:
  neo4j_data:
  redis_data:
```

### Kubernetes Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pkh-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: pkh
  template:
    metadata:
      labels:
        app: pkh
    spec:
      containers:
      - name: pkh
        image: registry.example.com/pkh:latest
        ports:
        - containerPort: 8000
        env:
        - name: PKH_CONFIG_PATH
          value: "/app/config/settings.yaml"
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: pkh-secrets
              key: anthropic-api-key
        volumeMounts:
        - name: config
          mountPath: /app/config
      volumes:
      - name: config
        configMap:
          name: pkh-config
---
apiVersion: v1
kind: Service
metadata:
  name: pkh-api
spec:
  selector:
    app: pkh
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

---

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/pkh-sync.yml
name: PKH Daily Sync

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      
      - name: Install PKH
        run: pip install project-knowledge-harness
      
      - name: Run sync
        run: pkh ingest --sync --incremental
        env:
          GIT_TOKEN: ${{ secrets.GIT_TOKEN }}
          CONFLUENCE_TOKEN: ${{ secrets.CONFLUENCE_TOKEN }}
          JIRA_TOKEN: ${{ secrets.JIRA_TOKEN }}
      
      - name: Check health
        run: pkh status
```

---

## Health Checks

### API Endpoints

| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| `GET /health` | Service health | `{"status": "healthy", "uptime": "Xh"}` |
| `GET /health/storage` | Storage layer health | `{"vector": "ok", "graph": "ok", "metadata": "ok"}` |
| `GET /health/sources` | Source connectivity | `{"git": "ok", "confluence": "ok", "jira": "ok"}` |

### CLI Commands

```bash
# Check overall health
pkh status

# Check specific source
pkh sources status --source git://github.com/org/project

# Check ingestion pipeline
pkh health --pipeline

# Check storage layers
pkh health --storage
```

---

## Monitoring

### Metrics to Track

| Metric | Source | Alert Threshold |
|--------|--------|-----------------|
| Ingestion rate | Engine 1 | < 10 doc/min |
| Sync success rate | SyncManager | < 95% |
| Error rate | All engines | > 1% |
| Query latency P99 | Engine 5 | > 1000ms |
| Storage growth | Metadata Store | Monitor trend |
| LLM API costs | Adapter layer | Track per query |

### Logging

PKH uses structured JSON logging:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "logger": "pkh.engines.ingestion",
  "message": "Sync completed",
  "source": "git",
  "items_processed": 150,
  "duration_ms": 2340
}
```

Configure logging in `settings.yaml`:

```yaml
logging:
  level: INFO
  format: json
  output: stdout
  file: /var/log/pkh/pkh.log
  max_size_mb: 100
  backup_count: 5
```
