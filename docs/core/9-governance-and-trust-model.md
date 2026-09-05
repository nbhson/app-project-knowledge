# Governance & Trust Model

> How the Harness ensures security, access control, and data governance.
> [[glossary]]

---

## Security Model

| Layer | Mechanism | Description | Implementation |
|-------|-----------|-------------|----------------|
| **Authentication** | OAuth2 / API Key / Token | Verify identity of the requester | Middleware on API; CLI credential store |
| **Authorization** | RBAC (Role-Based Access Control) | Control what authenticated users can do | Permission checks in engine pipelines |
| **Data Classification** | Tag-based | Classify knowledge by sensitivity | Tags on KnowledgeObjects: PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED |
| **Audit Logging** | Immutable log | Record every access and operation | Append-only log table; cryptographic hash chain |
| **Encryption** | At rest + in transit | Protect data confidentiality | TLS for transit; AES-256 for stored secrets |

---

## Access Control Principle

> The Harness cannot give access to knowledge the user cannot access in the original system.

```
User has access to Source X
    |  (Git repo, Confluence space, Jira project)
    v
User can see knowledge derived from Source X
    |  (in the Knowledge Core)
    v
User can use that knowledge in retrievals
    |
    v
[ENFORCED: If user lacks Source X access, knowledge from X is filtered out]
```

**Implementation:** Each SourceReference carries the original access level. During retrieval, the engine filters results by the user''s permitted access levels.

---

## RBAC Model

| Role | Permissions | Typical User |
|------|------------|--------------|
| `ADMIN` | Full access to all knowledge; manage sources; configure engines | DevOps / Platform team |
| `ARCHITECT` | Read all knowledge; trigger re-extraction; view audit logs | Lead architect |
| `DEVELOPER` | Read knowledge from assigned projects; run ingestion for own repos | Software engineer |
| `VIEWER` | Read-only; limited to public knowledge | External contributor / stakeholder |
| `SERVICE` | Programmatic access for CI/CD; no human identity | Bot / automation |

### Permission Matrix

| Action | ADMIN | ARCHITECT | DEVELOPER | VIEWER | SERVICE |
|--------|-------|-----------|-----------|--------|---------|
| Read public knowledge | Y | Y | Y | Y | Y |
| Read internal knowledge | Y | Y | Y (own proj) | N | Y (scoped) |
| Read confidential knowledge | Y | Y | N | N | N |
| Read restricted knowledge | Y | N | N | N | N |
| Ingest sources | Y | Y | Y (own) | N | Y (scoped) |
| Configure engines | Y | N | N | N | N |
| View audit logs | Y | Y | N | N | N |
| Delete knowledge | Y | Y | N | N | N |

---

## Data Classification

| Level | Sources | Treatment | Retention |
|-------|---------|-----------|-----------|
| **PUBLIC** | Public repos, public docs | Full access to all users | Indefinite |
| **INTERNAL** | Private repos (team), team Confluence | Team members only | 2 years after project close |
| **CONFIDENTIAL** | Restricted Confluence, proprietary code | Permission-group only | Project lifetime + 1 year |
| **RESTRICTED** | HR/Finance docs, security configs | Admin only, encrypted | Compliance-driven (7+ years) |

Classification is inherited from the source:
- Git repo visibility (public/private) -> PUBLIC/INTERNAL
- Confluence space permission -> maps to INTERNAL/CONFIDENTIAL
- Jira project permission -> maps to INTERNAL/CONFIDENTIAL

---

## Audit Log Model

Every knowledge operation is logged immutably:

```python
class AuditEntry(BaseModel):
    """Immutable record of every operation."""
    
    timestamp: datetime
    actor_id: str                      # user or service ID
    action: AuditAction                # READ | WRITE | DELETE | CONFIGURE | INGEST
    resource_type: str                 # KNOWLEDGE_OBJECT | SOURCE | CONFIG | USER
    resource_id: str                   # ID of the resource acted upon
    source_ip: str = ""                # IP address of requester
    user_agent: str = ""               # Client identifier
    result: str                        # SUCCESS | FAILED | DENIED
    details: dict[str, Any] = {}       # Operation-specific details
    hash: str = ""                     # SHA-256 of all preceding entries (chain)
```

**Logged events:**
- User reads knowledge (what was read, from which source)
- Knowledge is ingested (which source, how many objects)
- Knowledge lifecycle state changes
- Configuration changes (new source added, engine tuned)
- Access denied attempts (for security monitoring)

**Retention:** Audit logs retained for minimum 1 year; restricted operations logged for 7 years.

---

## Trust Boundaries

```mermaid
graph TD
    EXT[EXTERNAL TRUST\nGit / Confluence / Jira authenticated APIs]
    EXT -->|ingestion with source credentials| INT[PKH INTERNAL ZONE\nKnowledge Core structured traced scored\nLifecycle enforced | Confidence tracked]
    INT -->|retrieval with user permissions| CON[CONSUMER ZONE\nLLM / IDE / Human receives ContextPackage\nSources included | Confidence flagged]
```

**Key trust rules:**
1. PKH never modifies source data. Sources are read-only.
2. PKH never exposes knowledge beyond the user''s source-level permissions.
3. PKH never claims extracted knowledge is 100% accurate (confidence scores prevent this).
4. PKH logs every access for accountability.