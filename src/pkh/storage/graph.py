"""Graph store - NetworkX with persistence."""

from __future__ import annotations

import json
from pathlib import Path

import networkx as nx

from pkh.models.knowledge import KnowledgeObject
from pkh.utils.logging import get_logger

logger = get_logger(__name__)


class GraphStore:
    def __init__(self, persist_path: str = "./data/graph.json"):
        self.persist_path = Path(persist_path)
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        self.graph = nx.DiGraph()
        self._load()

    def _load(self) -> None:
        if self.persist_path.exists():
            try:
                data = json.loads(self.persist_path.read_text())
                self.graph = nx.node_link_graph(data, directed=True, multigraph=False)
            except Exception as e:
                logger.warning(f"Failed to load graph: {e}")

    def _persist(self) -> None:
        try:
            data = nx.node_link_data(self.graph)
            self.persist_path.write_text(json.dumps(data))
        except Exception as e:
            logger.warning(f"Failed to persist graph: {e}")

    async def add_node(self, ko: KnowledgeObject) -> None:
        self.graph.add_node(
            ko.id,
            label=ko.entity_type.value if ko.entity_type else ko.object_type.value,
            title=ko.title,
            lifecycle_state=ko.lifecycle_state.value,
            confidence=ko.confidence,
            properties=ko.properties,
        )
        self._persist()

    async def upsert(self, ko: KnowledgeObject, idempotency_key: str | None = None) -> None:
        # if relationship type, add edge; else add node
        if ko.object_type.value == "RELATIONSHIP":
            from_id = ko.properties.get("from") or ko.properties.get("from_id")
            to_id = ko.properties.get("to") or ko.properties.get("to_id")
            rel_type = (
                ko.properties.get("rel_type")
                or ko.properties.get("relationship_type")
                or "RELATED_TO"
            )
            if from_id and to_id:
                # ensure nodes exist
                if from_id not in self.graph:
                    self.graph.add_node(from_id, label="UNKNOWN")
                if to_id not in self.graph:
                    self.graph.add_node(to_id, label="UNKNOWN")
                self.graph.add_edge(
                    from_id, to_id, relation=rel_type, confidence=ko.confidence, id=ko.id
                )
        else:
            await self.add_node(ko)
        self._persist()

    async def upsert_many(self, kos: list[KnowledgeObject]) -> None:
        for ko in kos:
            await self.upsert(ko)

    async def add_edge(
        self, from_id: str, to_id: str, relation: str, confidence: float = 1.0
    ) -> None:
        self.graph.add_edge(from_id, to_id, relation=relation, confidence=confidence)
        self._persist()

    def get_neighbors(
        self, entity_id: str, relationship_types: list[str] | None = None, max_depth: int = 1
    ) -> list[str]:
        if entity_id not in self.graph:
            return []
        # BFS
        visited = set()
        frontier = {entity_id}
        result = set()
        for _ in range(max_depth):
            next_frontier = set()
            for node in frontier:
                if node in visited:
                    continue
                visited.add(node)
                for succ in self.graph.successors(node):
                    edge_data = self.graph.get_edge_data(node, succ) or {}
                    rel = edge_data.get("relation")
                    if relationship_types and rel not in relationship_types:
                        continue
                    result.add(succ)
                    next_frontier.add(succ)
                for pred in self.graph.predecessors(node):
                    edge_data = self.graph.get_edge_data(pred, node) or {}
                    rel = edge_data.get("relation")
                    if relationship_types and rel not in relationship_types:
                        continue
                    result.add(pred)
                    next_frontier.add(pred)
            frontier = next_frontier
        return list(result)

    def shortest_path(self, from_id: str, to_id: str) -> list[str] | None:
        try:
            return nx.shortest_path(self.graph, from_id, to_id)
        except Exception:
            return None

    def subgraph(self, entity_ids: list[str]) -> nx.DiGraph:
        return self.graph.subgraph(entity_ids).copy()

    async def delete_node(self, node_id: str) -> None:
        if node_id in self.graph:
            self.graph.remove_node(node_id)
            self._persist()

    async def count_nodes(self) -> int:
        return self.graph.number_of_nodes()

    async def count_edges(self) -> int:
        return self.graph.number_of_edges()

    def detect_communities(self) -> list[list[str]]:
        try:
            import networkx.algorithms.community as comm

            undirected = self.graph.to_undirected()
            communities = list(comm.greedy_modularity_communities(undirected))
            return [list(c) for c in communities]
        except Exception:
            return []
