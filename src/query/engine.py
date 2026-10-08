"""Query engine module for the Knowledge Graph.

Responsibilities:
- Provide the main entry point for natural language querying against the graph.
- Orchestrate parsing the query and executing the appropriate graph traversal or search.
"""

import logging
from typing import Any
import networkx as nx

from src.query.parser import parse_query, QueryIntent

logger = logging.getLogger(__name__)


def _list_pins(graph: nx.MultiDiGraph) -> list[dict[str, Any]]:
    """Retrieve all Pin nodes from the graph."""
    results = []
    for node_id, data in graph.nodes(data=True):
        if data.get("node_type") == "Pin":
            results.append({"id": node_id, **data})
    return results


def _find_pin_by_number(graph: nx.MultiDiGraph, value: str) -> list[dict[str, Any]]:
    """Find a Pin node by its pin number."""
    results = []
    for node_id, data in graph.nodes(data=True):
        if data.get("node_type") == "Pin" and str(data.get("pin_number")) == str(value):
            results.append({"id": node_id, **data})
    return results


def _find_pin_by_name(graph: nx.MultiDiGraph, value: str) -> list[dict[str, Any]]:
    """Find a Pin node by its name (case-insensitive substring match)."""
    results = []
    search_val = str(value).lower()
    for node_id, data in graph.nodes(data=True):
        if data.get("node_type") == "Pin":
            name = str(data.get("name", "")).lower()
            if search_val in name:
                results.append({"id": node_id, **data})
    return results


def _list_metrics(graph: nx.MultiDiGraph) -> list[dict[str, Any]]:
    """Retrieve all ElectricalMetric nodes from the graph."""
    results = []
    for node_id, data in graph.nodes(data=True):
        if data.get("node_type") == "ElectricalMetric":
            results.append({"id": node_id, **data})
    return results


def _find_metric(graph: nx.MultiDiGraph, value: str) -> list[dict[str, Any]]:
    """Find ElectricalMetric nodes by parameter name (case-insensitive substring match)."""
    results = []
    search_val = str(value).lower()
    for node_id, data in graph.nodes(data=True):
        if data.get("node_type") == "ElectricalMetric":
            param = str(data.get("parameter", "")).lower()
            if search_val in param:
                results.append({"id": node_id, **data})
    return results


def _list_sections(graph: nx.MultiDiGraph) -> list[dict[str, Any]]:
    """Retrieve all Section nodes from the graph."""
    results = []
    for node_id, data in graph.nodes(data=True):
        if data.get("node_type") == "Section":
            results.append({"id": node_id, **data})
    return results


def query_graph(graph: nx.MultiDiGraph, query: str) -> dict[str, Any]:
    """Execute a natural language query against the provided Knowledge Graph.

    Args:
        graph: The enriched NetworkX MultiDiGraph instance.
        query: The natural language string query provided by the user.

    Returns:
        dict[str, Any]: A structured response containing the query results and metadata.
            Expected to contain keys like 'success', 'intent', 'count', and 'results'.

    Raises:
        TypeError: If graph is not a valid NetworkX MultiDiGraph.
        ValueError: If query is empty or invalid.
    """
    if not isinstance(graph, (nx.MultiDiGraph, nx.DiGraph, nx.Graph)):
        logger.error("Invalid graph instance passed to query_graph.")
        raise TypeError("Expected a valid NetworkX Graph instance.")

    if not query or not str(query).strip():
        logger.error("Empty query provided.")
        raise ValueError("Query string cannot be empty.")

    logger.info("Received query: '%s'", query)

    intent_data: QueryIntent = parse_query(query)
    intent_type = intent_data.get("intent", "UNKNOWN")
    value = intent_data.get("value")

    results: list[dict[str, Any]] = []

    if intent_type == "list_pins":
        results = _list_pins(graph)
    elif intent_type == "find_pin_by_number" and value:
        results = _find_pin_by_number(graph, value)
    elif intent_type == "find_pin_by_name" and value:
        results = _find_pin_by_name(graph, value)
    elif intent_type == "list_metrics":
        results = _list_metrics(graph)
    elif intent_type == "find_metric" and value:
        results = _find_metric(graph, value)
    elif intent_type == "list_sections":
        results = _list_sections(graph)
    else:
        logger.warning("Unsupported or unrecognized intent: %s", intent_type)

    if not results:
        return {
            "success": False,
            "message": "No matching nodes found."
        }

    response: dict[str, Any] = {
        "success": True,
        "intent": intent_type,
        "count": len(results),
        "results": results,
    }

    logger.debug("Query execution completed with %d results for intent: %s", len(results), intent_type)
    return response
