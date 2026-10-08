"""Knowledge Graph builder module.

Constructs a NetworkX MultiDiGraph from extracted component dictionary structures.
"""

import logging
from typing import Any
import networkx as nx

logger = logging.getLogger(__name__)


def build_graph(component_data: dict[str, Any]) -> nx.MultiDiGraph:
    """Construct a NetworkX MultiDiGraph from extracted component dictionary data.

    Creates nodes for the Component, Pins, and Electrical Metrics, connecting them with
    HAS_PIN and HAS_METRIC directed edges while preserving all metadata as node attributes.

    Args:
        component_data: Dictionary containing 'metadata', 'pin_configuration', and
            'electrical_characteristics'.

    Returns:
        nx.MultiDiGraph: Constructed knowledge graph.

    Raises:
        ValueError: If component_data is not a valid dictionary.
    """
    if not isinstance(component_data, dict):
        logger.error("Invalid input passed to build_graph: expected a dictionary.")
        raise ValueError("Input component_data must be a dictionary.")

    graph = nx.MultiDiGraph()

    # 1. Component Node
    metadata = component_data.get("metadata", {})
    file_name = metadata.get("file_name", "Unknown_Component")
    component_id = f"Component:{file_name}"

    component_attrs = {
        "node_type": "Component",
        "file_name": file_name,
        "total_pages": metadata.get("total_pages", 0),
        "sections_found": str(metadata.get("sections_found", {})),
    }
    graph.add_node(component_id, **component_attrs)
    logger.info("Added Component node: '%s'", component_id)

    # 2. Pin Nodes & Component -> Pin (HAS_PIN) Edges
    pin_config = component_data.get("pin_configuration", {})
    pins = pin_config.get("pins", [])
    pin_node_ids: list[str] = []

    for idx, pin_data in enumerate(pins, start=1):
        pin_number = str(pin_data.get("pin_number", idx))
        pin_name = str(pin_data.get("name", f"PIN_{pin_number}"))
        pin_node_id = f"Pin:{pin_number}:{pin_name}"

        pin_attrs = {
            "node_type": "Pin",
            "pin_number": pin_number,
            "name": pin_name,
            "type": pin_data.get("type"),
            "description": pin_data.get("description"),
        }

        graph.add_node(pin_node_id, **pin_attrs)
        pin_node_ids.append(pin_node_id)

        # Component -> Pin edge (HAS_PIN)
        graph.add_edge(
            component_id, pin_node_id, key="HAS_PIN", relationship="HAS_PIN"
        )
        logger.debug(
            "Added Pin node '%s' connected to '%s'", pin_node_id, component_id
        )

    logger.info("Processed %d Pin nodes with HAS_PIN edges", len(pin_node_ids))

    # 3. Metric Nodes & Pin -> Metric (HAS_METRIC) Edges
    electrical_data = component_data.get("electrical_characteristics", {})
    metrics = electrical_data.get("metrics", [])
    metric_node_ids: list[str] = []

    for idx, metric_data in enumerate(metrics, start=1):
        param = str(metric_data.get("parameter", f"Metric_{idx}"))
        symbol = metric_data.get("symbol")
        metric_node_id = (
            f"Metric:{idx}:{symbol if symbol else param.replace(' ', '_')}"
        )

        metric_attrs = {
            "node_type": "ElectricalMetric",
            "parameter": param,
            "symbol": symbol,
            "test_conditions": metric_data.get("test_conditions"),
            "min_value": metric_data.get("min_value"),
            "typ_value": metric_data.get("typ_value"),
            "max_value": metric_data.get("max_value"),
            "unit": metric_data.get("unit"),
            "notes": metric_data.get("notes"),
        }

        graph.add_node(metric_node_id, **metric_attrs)
        metric_node_ids.append(metric_node_id)

        # Connect Component -> Metric
        graph.add_edge(
            component_id, metric_node_id, key="HAS_METRIC", relationship="HAS_METRIC"
        )

        # Connect Pin -> Metric
        matched_pin = False
        for p_id in pin_node_ids:
            p_attrs = graph.nodes[p_id]
            p_name = str(p_attrs.get("name", "")).upper()

            metric_text = (
                f"{param} {symbol or ''} {metric_data.get('test_conditions') or ''}"
            ).upper()

            if p_name and (
                p_name in metric_text or (len(p_name) > 1 and p_name == symbol)
            ):
                graph.add_edge(
                    p_id, metric_node_id, key="HAS_METRIC", relationship="HAS_METRIC"
                )
                matched_pin = True
                logger.debug(
                    "Connected Pin '%s' to Metric '%s' (HAS_METRIC)",
                    p_id,
                    metric_node_id,
                )

        if not matched_pin and pin_node_ids:
            for p_id in pin_node_ids:
                graph.add_edge(
                    p_id, metric_node_id, key="HAS_METRIC", relationship="HAS_METRIC"
                )

    logger.info("Processed %d Metric nodes with HAS_METRIC edges", len(metric_node_ids))
    logger.info(
        "Graph construction complete: %d nodes, %d edges",
        graph.number_of_nodes(),
        graph.number_of_edges(),
    )

    return graph
