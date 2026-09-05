# Day 18 — Graph Store (NetworkX)

> **Phase:** 4 — Knowledge Storage Engine | **Date:** Day 18 of 30 | **Goal:** Implement GraphStore with NetworkX backend for knowledge graph

---

## 🎯 Daily Target

**Deliverable:** Graph store interface with NetworkX implementation for relationship storage and traversal

---

## ✅ Tasks

### 1. GraphStore Interface
- [ ] Abstract base class with methods:
  - `add_node(entity_id, entity_type, properties)`
  - `add_edge(from_id, to_id, relationship_type, confidence)`
  - `get_neighbors(entity_id, relationship_types, max_depth)`
  - `shortest_path(from_id, to_id)`
  - `subgraph(entity_ids)`
  - `detect_communities()`

### 2. NetworkXBackend Implementation
- [ ] Initialize directed graph `DiGraph()` 
- [ ] Store nodes with properties: entity_type, lifecycle_state, source_type, confidence
- [ ] Add edges with type and confidence
- [ ] Get neighbors with configurable relationship types and depth
- [ ] Shortest path finding (Dijkstra/BFS)
- [ ] Subgraph extraction for entity IDs
- [ ] Community detection (Louvain or greedy)

### 3. Build Full Graph
- [ ] Nodes = knowledge objects from storage
- [ ] Edges = relationships from knowledge_objects
- [ ] Cross-store sync: metadata changes → graph updates
- [ ] Lifecycle-aware: exclude SUPERSEDED/DEPRECATED from traversal
- [ ] Graph persistence (save/load to JSON/JSONL)

### 4. Operations
- [ ] neighbors(entity_id, types=None, depth=1)
- [ ] shortest_path(from_id, to_id) with path reconstruction
- [ ] subgraph(entity_ids) induced subgraph
- [ ] detect_communities() community partitions
- [ ] node_degree(entity_id)
- [ ] community_members(community_id) → list of nodes

### 5. Unit Tests (`tests/unit/test_graph_store.py`)
- [ ] Test add_node and add_edge
- [ ] Test get_neighbors with depth filtering
- [ ] Test shortest_path computation
- [ ] Test subgraph extraction
- [ ] Test community detection
- [ ] Test lifecycle filtering

---

## 📋 Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| Graph initialized with NetworkX | ☐ |
| Add node/edge with properties works | ☐ |
| Get neighbors respects relationship types | ☐ |
| Shortest path finds correct path | ☐ |
| Subgraph extraction works | ☐ |
| Community detection runs | ☐ |
| Unit tests pass | ☐ |

---

## 🔗 Dependencies

- **Blocks:** Day 19 (Storage integration), Phase 5 (Retrieval traversal)
- **Blocked by:** Day 17 (Vector store), Day 16 (Metadata store)

---

## 📝 Notes

- Use `networkx.DiGraph()` for directed knowledge graph
- Persist graph to JSON for recovery
- GraphML or GEXF for visualization later
- Commit: `feat: graph store with networkx and traversal operations`