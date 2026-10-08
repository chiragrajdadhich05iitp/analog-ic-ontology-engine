"""Neo4j graph loading module.

Responsibilities:
- Connect to a Neo4j database using environment variables.
- Create uniqueness constraints and indexes for key node labels.
- Upload a NetworkX MultiDiGraph directly into Neo4j using batched MERGE statements.
- Return population statistics.
"""

import logging
import os
import time
from typing import Any, TypedDict
import networkx as nx

try:
    from neo4j import GraphDatabase, Driver
    from neo4j.exceptions import ClientError as Neo4jClientError
except ImportError:
    GraphDatabase = None
    Driver = Any
    Neo4jClientError = Exception

logger = logging.getLogger(__name__)

# Labels for which we create uniqueness constraints and indexes.
_INDEXED_LABELS: list[tuple[str, str]] = [
    ("Component", "id"),
    ("Pin", "id"),
    ("ElectricalMetric", "id"),
    ("Parameter", "id"),
    ("Unit", "id"),
    ("Condition", "id"),
    ("Section", "id"),
]


class LoadStatistics(TypedDict):
    """Statistics detailing the results of the Neo4j load operation."""
    nodes_created: int
    relationships_created: int
    execution_time: float


class Neo4jLoader:
    """Manages the connection and data upload to a Neo4j database.

    Example:
        >>> loader = Neo4jLoader()
        >>> stats = loader.load_graph(graph)
        >>> loader.close()
        >>> print(stats["nodes_created"])
    """

    def __init__(
        self,
        uri: str | None = None,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        """Initialize the Neo4j loader using explicit credentials or environment variables.

        Args:
            uri: Neo4j connection URI (e.g., ``'bolt://localhost:7687'``).
                Defaults to the ``NEO4J_URI`` environment variable.
            username: Neo4j username. Defaults to ``NEO4J_USERNAME``.
            password: Neo4j password. Defaults to ``NEO4J_PASSWORD``.

        Raises:
            ImportError: If the ``neo4j`` Python package is not installed.
            ValueError: If any credential is missing from both arguments and environment.
        """
        if GraphDatabase is None:
            raise ImportError(
                "The 'neo4j' package is required. Install it with: pip install neo4j"
            )

        self.uri = uri or os.environ.get("NEO4J_URI")
        self.username = username or os.environ.get("NEO4J_USERNAME")
        self.password = password or os.environ.get("NEO4J_PASSWORD")

        if not all([self.uri, self.username, self.password]):
            raise ValueError(
                "Missing Neo4j credentials. Set NEO4J_URI, NEO4J_USERNAME, and "
                "NEO4J_PASSWORD as environment variables, or pass them explicitly."
            )

        self._driver: Driver = GraphDatabase.driver(
            self.uri, auth=(self.username, self.password)
        )
        logger.info("Neo4j driver initialised for '%s'.", self.uri)

    def close(self) -> None:
        """Close the Neo4j driver connection and release all resources."""
        if self._driver:
            self._driver.close()
            logger.info("Neo4j driver closed.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_indexes(self) -> None:
        """Create uniqueness constraints and range indexes for all indexed labels.

        Uses ``CREATE CONSTRAINT IF NOT EXISTS`` so the operation is idempotent.
        Falls back to a plain ``CREATE INDEX`` when constraints are unsupported
        (e.g., on Neo4j Community Edition).
        """
        with self._driver.session() as session:
            for label, prop in _INDEXED_LABELS:
                constraint_name = f"unique_{label.lower()}_{prop}"
                try:
                    session.run(
                        f"CREATE CONSTRAINT {constraint_name} IF NOT EXISTS "
                        f"FOR (n:{label}) REQUIRE n.{prop} IS UNIQUE"
                    )
                    logger.debug("Constraint ensured: %s.%s", label, prop)
                except Neo4jClientError as err:
                    # Community Edition does not support all constraint syntax;
                    # fall back to a plain index.
                    logger.warning(
                        "Could not create constraint for %s.%s (%s); "
                        "falling back to index.",
                        label,
                        prop,
                        err,
                    )
                    try:
                        index_name = f"idx_{label.lower()}_{prop}"
                        session.run(
                            f"CREATE INDEX {index_name} IF NOT EXISTS "
                            f"FOR (n:{label}) ON (n.{prop})"
                        )
                    except Neo4jClientError as idx_err:
                        logger.warning(
                            "Could not create index for %s.%s: %s",
                            label,
                            prop,
                            idx_err,
                        )

        logger.info("Indexes/constraints setup complete.")

    def load_graph(
        self, graph: nx.MultiDiGraph, batch_size: int = 500
    ) -> LoadStatistics:
        """Load a NetworkX MultiDiGraph into Neo4j using batched MERGE queries.

        Steps:
            1. Create indexes / constraints.
            2. Batch-MERGE all nodes, grouped by label.
            3. Batch-MERGE all relationships, grouped by type.

        Args:
            graph: The enriched Knowledge Graph to upload.
            batch_size: Number of items processed in a single transaction.

        Returns:
            LoadStatistics: Dict with ``nodes_created``, ``relationships_created``,
                and ``execution_time`` (seconds).
        """
        start_time = time.time()
        nodes_created = 0
        relationships_created = 0

        logger.info(
            "Starting Neo4j load: %d nodes, %d edges (batch_size=%d).",
            graph.number_of_nodes(),
            graph.number_of_edges(),
            batch_size,
        )

        self.create_indexes()

        with self._driver.session() as session:
            # ---- 1. Nodes -----------------------------------------------
            node_buffer: list[dict[str, Any]] = []
            for node_id, data in graph.nodes(data=True):
                props: dict[str, Any] = {
                    k: v for k, v in data.items() if v is not None and v != ""
                }
                props["id"] = str(node_id)
                label = str(props.get("node_type", "Entity"))
                node_buffer.append({"label": label, "props": props})

                if len(node_buffer) >= batch_size:
                    nodes_created += self._flush_nodes(session, node_buffer)
                    node_buffer = []

            if node_buffer:
                nodes_created += self._flush_nodes(session, node_buffer)

            # ---- 2. Relationships ----------------------------------------
            edge_buffer: list[dict[str, Any]] = []
            for u, v, key, data in graph.edges(keys=True, data=True):
                rel_type = str(
                    data.get("relationship", key or "RELATED_TO")
                ).upper()
                props = {k: val for k, val in data.items() if val is not None}
                edge_buffer.append(
                    {
                        "source_id": str(u),
                        "target_id": str(v),
                        "rel_type": rel_type,
                        "props": props,
                    }
                )

                if len(edge_buffer) >= batch_size:
                    relationships_created += self._flush_edges(session, edge_buffer)
                    edge_buffer = []

            if edge_buffer:
                relationships_created += self._flush_edges(session, edge_buffer)

        elapsed = round(time.time() - start_time, 3)
        logger.info(
            "Neo4j load complete: %d nodes created, %d relationships created "
            "in %.3f seconds.",
            nodes_created,
            relationships_created,
            elapsed,
        )

        return {
            "nodes_created": nodes_created,
            "relationships_created": relationships_created,
            "execution_time": elapsed,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _flush_nodes(
        self, session: Any, buffer: list[dict[str, Any]]
    ) -> int:
        """Flush a node buffer to Neo4j using MERGE grouped by label.

        Args:
            session: Active Neo4j session.
            buffer: List of ``{"label": str, "props": dict}`` items.

        Returns:
            int: Total number of nodes created (per Neo4j counters).
        """
        created = 0
        # Group by label so every Cypher statement references a static label.
        by_label: dict[str, list[dict[str, Any]]] = {}
        for item in buffer:
            by_label.setdefault(item["label"], []).append(item["props"])

        for label, batch in by_label.items():
            cypher = (
                f"UNWIND $batch AS props "
                f"MERGE (n:{label} {{id: props.id}}) "
                f"SET n += props"
            )
            result = session.run(cypher, batch=batch)
            created += result.consume().counters.nodes_created

        return created

    def _flush_edges(
        self, session: Any, buffer: list[dict[str, Any]]
    ) -> int:
        """Flush a relationship buffer to Neo4j using MERGE grouped by type.

        Args:
            session: Active Neo4j session.
            buffer: List of ``{"source_id", "target_id", "rel_type", "props"}`` items.

        Returns:
            int: Total number of relationships created (per Neo4j counters).
        """
        created = 0
        # Group by relationship type so Cypher references a static label.
        by_type: dict[str, list[dict[str, Any]]] = {}
        for item in buffer:
            by_type.setdefault(item["rel_type"], []).append(item)

        for rel_type, batch in by_type.items():
            cypher = (
                f"UNWIND $batch AS edge "
                f"MATCH (src {{id: edge.source_id}}) "
                f"MATCH (tgt {{id: edge.target_id}}) "
                f"MERGE (src)-[r:{rel_type}]->(tgt) "
                f"SET r += edge.props"
            )
            result = session.run(cypher, batch=batch)
            created += result.consume().counters.relationships_created

        return created
