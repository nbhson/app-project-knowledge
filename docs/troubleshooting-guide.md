# Troubleshooting Guide

> Common issues and their solutions.
> [[glossary]]

---

## Installation Issues

### Problem: `pip install` fails with Python version error

**Error:**
```
ERROR: Package requires Python 3.10 or higher
```

**Solution:**
```bash
# Check Python version
python --version

# Install Python 3.10+ using pyenv (recommended)
pyenv install 3.10.12
pyenv local 3.10.12

# Or use conda
conda create -n pkh python=3.10
conda activate pkh
```

---

### Problem: tree-sitter parser not found

**Error:**
```
ModuleNotFoundError: No module named 'tree_sitter_python'
```

**Solution:**
```bash
# Install language-specific parsers
pip install tree-sitter-python tree-sitter-typescript tree-sitter-java
```

---

### Problem: ChromaDB initialization fails

**Error:**
```
chromadb.errors.InvalidCollectionException: Collection does not exist
```

**Solution:**
```bash
# Clear ChromaDB data and reinitialize
rm -rf ./data/vectorstore
pkh init
```

---

## Ingestion Issues

### Problem: Git connector fails with authentication error

**Error:**
```
git.exc.HTTPError: 403 Forbidden
```

**Solution:**
```bash
# Verify token is set
echo $GIT_TOKEN  # Should output the token, not empty

# Update config with valid token
pkh config set sources.git.auth.token_ref secrets.GIT_TOKEN

# Test connection
pkh sources test --source git://https://github.com/org/project
```

---

### Problem: Confluence connector returns empty pages

**Error:**
```
Confluence API returned 0 pages for space PROJ
```

**Solution:**
1. Verify space key is correct (case-sensitive)
2. Check permissions — your account needs read access to the space
3. Verify OAuth2 token has `read:confluence-content` scope
4. Check Confluence base_url matches your instance

```bash
# Test Confluence connection
pkh sources test --source confluence://PROJ

# List available spaces
pkh sources list-spaces --base-url https://your-org.atlassian.net
```

---

### Problem: Jira connector fails with rate limit

**Error:**
```
RateLimitError: 429 Too Many Requests
```

**Solution:**
```yaml
# Increase rate limit in config
sources:
  jira:
    sync_interval: 15m
    rate_limit:
      requests_per_minute: 30  # Default is 60
      burst_size: 10
```

---

### Problem: Incremental sync doesn't detect changes

**Symptoms:**
- Files modified in Git but not reflected in PKH
- `pkh status` shows no updates needed

**Solution:**
```bash
# Force full re-sync
pkh ingest --sync --full

# Check content hash comparison
pkh sources debug --source git://... --verbose

# Verify FileWatcher is enabled
# Check config: sources.git.file_watcher.enabled = true
```

---

## Retrieval Issues

### Problem: Query returns no results

**Symptoms:**
```
No knowledge found for query: "How does PaymentService work?"
```

**Solution:**
1. Check if knowledge exists
```bash
# List all knowledge objects
pkh knowledge list --limit 100

# Search by entity type
pkh knowledge search --type CLASS --name "PaymentService"
```

2. Check retrieval configuration
```yaml
# Increase top_k
retrieval:
  top_k: 20  # Default is 10
  
# Lower confidence threshold
retrieval:
  min_confidence: 0.1  # Default is 0.3
```

3. Check if vector embeddings exist
```bash
# Verify vector store has data
pkh health --storage --verbose
```

---

### Problem: Low precision in results

**Symptoms:**
- Results contain irrelevant knowledge
- Top results are not useful

**Solution:**
1. Adjust fusion weights
```yaml
retrieval:
  fusion:
    method: weighted  # Try weighted instead of RRF
    weights:
      vector: 0.5
      keyword: 0.3
      graph: 0.2
```

2. Increase relevance threshold
```yaml
retrieval:
  vector:
    threshold: 0.85  # Default is 0.75
```

3. Check intent classification
```bash
# Debug query classification
pkh query "Your query" --debug --intent-only
```

---

## Storage Issues

### Problem: Graph store corruption

**Symptoms:**
```
NetworkXError: Graph drawn from inconsistent node set
```

**Solution:**
```bash
# Rebuild graph from metadata store
pkh storage rebuild --layer graph

# Verify consistency
pkh health --storage --check-consistency
```

---

### Problem: Vector store running out of memory

**Symptoms:**
```
MemoryError: Unable to allocate array
```

**Solution:**
1. Switch to pgvector for production
```yaml
storage:
  vector:
    provider: pgvector  # Instead of chroma
```

2. Reduce chunk size
```yaml
retrieval:
  vector:
    chunk_size: 256  # Default is 512
```

3. Enable compression
```yaml
storage:
  vector:
    compression: sq  # Sub-quantization
```

---

## Governance Issues

### Problem: Access denied for user

**Error:**
```
PermissionError: User lacks access to this knowledge
```

**Solution:**
1. Check user role
```bash
pkh auth whoami
```

2. Verify source permissions match
```bash
# Check if user has access to source
pkh sources check-permissions --user <user_id>
```

3. Admin can grant access
```bash
pkh auth grant --user <user_id> --role developer --project PROJ
```

---

### Problem: Audit log not capturing events

**Symptoms:**
- Audit log is empty
- `pkh audit` returns no entries

**Solution:**
1. Check audit is enabled
```yaml
governance:
  audit:
    enabled: true
```

2. Verify log storage
```bash
# Check audit log location
pkh config get governance.audit.log_path

# Test logging
pkh audit --test
```

---

## Performance Issues

### Problem: Slow query response

**Symptoms:**
- Queries take > 2 seconds
- P99 latency exceeds target

**Solution:**
1. Enable query caching
```yaml
retrieval:
  cache:
    enabled: true
    ttl: 3600
```

2. Reduce graph traversal depth
```yaml
retrieval:
  graph:
    max_hops: 2  # Default is 3
```

3. Add database indexes
```sql
-- For PostgreSQL metadata store
CREATE INDEX idx_knowledge_lifecycle ON knowledge_objects(lifecycle_state);
CREATE INDEX idx_knowledge_type ON knowledge_objects(entity_type);
CREATE INDEX idx_knowledge_tags ON knowledge_objects USING GIN(tags);
```

---

### Problem: High ingestion latency

**Symptoms:**
- Full sync takes hours
- Engine 1 CPU/memory usage high

**Solution:**
1. Increase concurrency
```yaml
ingestion:
  max_concurrent: 8  # Default is 3
```

2. Exclude large files
```yaml
sources:
  git:
    exclude_paths:
      - "**/*.bin"
      - "**/*.zip"
      - "**/node_modules/**"
```

3. Enable incremental parsing
```yaml
sources:
  git:
    incremental_parsing: true
```

---

## LLM Adapter Issues

### Problem: Claude adapter fails with rate limit

**Error:**
```
RateLimitError: 429 Too Many Requests
```

**Solution:**
```yaml
adapters:
  claude:
    rate_limit:
      requests_per_minute: 10
      tokens_per_minute: 100000
    retry:
      max_attempts: 5
      backoff: exponential
```

---

### Problem: Context exceeds token limit

**Error:**
```
ContextTooLargeError: Context exceeds model token limit
```

**Solution:**
1. Reduce top_k
```yaml
retrieval:
  top_k: 5  # Default is 10
```

2. Enable compression
```yaml
retrieval:
  compression:
    enabled: true
    max_tokens: 4096
```

3. Use smaller model
```yaml
adapters:
  default: claude
  models:
    claude:
      model: claude-haiku-3-20240307  # 200K context, faster
```

---

## Debug Mode

Enable debug logging for detailed diagnostics:

```bash
# Verbose output
pkh ingest --verbose
pkh query "question" --verbose

# Debug specific engine
pkh query "question" --debug --engine=5

# Export diagnostics
pkh diagnostics --output debug-report.json
```

---

## Getting Help

1. Check logs: `/var/log/pkh/pkh.log`
2. Run diagnostics: `pkh diagnostics`
3. Check GitHub Issues: https://github.com/org/project-knowledge-harness/issues
4. Join Discord: https://discord.gg/pkh
