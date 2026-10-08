"""Knowledge Graph export utilities for NetworkX MultiDiGraph instances.

Responsibilities:
- Export graph as GraphML (.graphml)
- Export graph as GEXF (.gexf)
- Export graph as Node-Link JSON (.json)
- Export graph as Neo4j Cypher DDL/DML script (.cypher)
"""

import json
import logging
from pathlib import Path
from typing import Any
import networkx as nx

logger = logging.getLogger(__name__)


def _prepare_export_graph(graph: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Create a sanitized copy of the graph suitable for GraphML and GEXF serialization.

    Converts None values, dicts, and lists into string representations to satisfy XML schema constraints.

    Args:
        graph: Original NetworkX MultiDiGraph instance.

    Returns:
        nx.MultiDiGraph: Sanitized copy of the input graph.
    """
    export_g = nx.MultiDiGraph()

    for node_id, data in graph.nodes(data=True):
        sanitized_attrs: dict[str, Any] = {}
        for k, v in data.items():
            if v is None:
                sanitized_attrs[k] = ""
            elif isinstance(v, (dict, list)):
                sanitized_attrs[k] = json.dumps(v)
            else:
                sanitized_attrs[k] = v
        export_g.add_node(node_id, **sanitized_attrs)

    for u, v, key, data in graph.edges(keys=True, data=True):
        sanitized_edge_attrs: dict[str, Any] = {}
        for k, val in data.items():
            if val is None:
                sanitized_edge_attrs[k] = ""
            elif isinstance(val, (dict, list)):
                sanitized_edge_attrs[k] = json.dumps(val)
            else:
                sanitized_edge_attrs[k] = val
        export_g.add_edge(u, v, key=key, **sanitized_edge_attrs)

    return export_g


def _format_cypher_value(val: Any) -> str:
    """Format a Python value into a valid Cypher literal expression."""
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return str(val)
    escaped = str(val).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def export_graphml(graph: nx.MultiDiGraph, output_path: str | Path) -> Path:
    """Export NetworkX MultiDiGraph as a GraphML file.

    Args:
        graph: Input NetworkX MultiDiGraph instance.
        output_path: Target path for the .graphml file.

    Returns:
        Path: Path to the saved GraphML file.

    Raises:
        TypeError: If input graph is not a valid NetworkX graph.
        RuntimeError: If writing GraphML fails.
    """
    if not isinstance(graph, (nx.MultiDiGraph, nx.DiGraph, nx.Graph)):
        logger.error("Invalid graph instance passed to export_graphml")
        raise TypeError("Expected a valid NetworkX Graph instance.")

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        prep_g = _prepare_export_graph(graph)
        nx.write_graphml(prep_g, out_path)
        logger.info("Successfully exported GraphML to '%s'", out_path)
        return out_path
    except Exception as err:
        logger.exception("Failed exporting GraphML to '%s': %s", out_path, err)
        raise RuntimeError(f"Failed exporting GraphML: {err}") from err


def export_gexf(graph: nx.MultiDiGraph, output_path: str | Path) -> Path:
    """Export NetworkX MultiDiGraph as a GEXF file.

    Args:
        graph: Input NetworkX MultiDiGraph instance.
        output_path: Target path for the .gexf file.

    Returns:
        Path: Path to the saved GEXF file.

    Raises:
        TypeError: If input graph is not a valid NetworkX graph.
        RuntimeError: If writing GEXF fails.
    """
    if not isinstance(graph, (nx.MultiDiGraph, nx.DiGraph, nx.Graph)):
        logger.error("Invalid graph instance passed to export_gexf")
        raise TypeError("Expected a valid NetworkX Graph instance.")

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        prep_g = _prepare_export_graph(graph)
        nx.write_gexf(prep_g, out_path)
        logger.info("Successfully exported GEXF to '%s'", out_path)
        return out_path
    except Exception as err:
        logger.exception("Failed exporting GEXF to '%s': %s", out_path, err)
        raise RuntimeError(f"Failed exporting GEXF: {err}") from err


def export_json(graph: nx.MultiDiGraph, output_path: str | Path) -> Path:
    """Export NetworkX MultiDiGraph as Node-Link format JSON.

    Args:
        graph: Input NetworkX MultiDiGraph instance.
        output_path: Target path for the .json file.

    Returns:
        Path: Path to the saved JSON file.

    Raises:
        TypeError: If input graph is not a valid NetworkX graph.
        RuntimeError: If writing JSON fails.
    """
    if not isinstance(graph, (nx.MultiDiGraph, nx.DiGraph, nx.Graph)):
        logger.error("Invalid graph instance passed to export_json")
        raise TypeError("Expected a valid NetworkX Graph instance.")

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        data = nx.node_link_data(graph)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("Successfully exported Node-Link JSON to '%s'", out_path)
        return out_path
    except Exception as err:
        logger.exception("Failed exporting Node-Link JSON to '%s': %s", out_path, err)
        raise RuntimeError(f"Failed exporting JSON: {err}") from err


def export_cypher(graph: nx.MultiDiGraph, output_path: str | Path) -> Path:
    """Export NetworkX MultiDiGraph as executable Neo4j Cypher DDL/DML statements.

    Args:
        graph: Input NetworkX MultiDiGraph instance.
        output_path: Target path for the .cypher file.

    Returns:
        Path: Path to the saved Cypher script file.

    Raises:
        TypeError: If input graph is not a valid NetworkX graph.
        RuntimeError: If writing Cypher script fails.
    """
    if not isinstance(graph, (nx.MultiDiGraph, nx.DiGraph, nx.Graph)):
        logger.error("Invalid graph instance passed to export_cypher")
        raise TypeError("Expected a valid NetworkX Graph instance.")

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    statements: list[str] = [
        "// Knowledge Graph Neo4j Cypher DDL/DML Script",
        "// Generated automatically by Knowledge Graph Builder",
        "",
        "// --- NODES ---",
    ]

    for node_id, data in graph.nodes(data=True):
        label = str(data.get("node_type", "Entity"))
        props: dict[str, Any] = {"id": str(node_id)}
        for k, v in data.items():
            if v is not None and v != "":
                props[k] = v

        prop_pairs = [f"{k}: {_format_cypher_value(v)}" for k, v in props.items()]
        prop_str = "{" + ", ".join(prop_pairs) + "}"
        statements.append(f"CREATE (:{label} {prop_str});")

    statements.append("")
    statements.append("// --- RELATIONSHIPS ---")

    for u, v, key, data in graph.edges(keys=True, data=True):
        rel_type = str(data.get("relationship", key or "RELATED_TO")).upper()
        u_escaped = _format_cypher_value(u)
        v_escaped = _format_cypher_value(v)
        statements.append(
            f"MATCH (a {{id: {u_escaped}}}), (b {{id: {v_escaped}}}) CREATE (a)-[:{rel_type}]->(b);"
        )

    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(statements) + "\n")
        logger.info("Successfully exported Cypher script to '%s'", out_path)
        return out_path
    except Exception as err:
        logger.exception("Failed exporting Cypher script to '%s': %s", out_path, err)
        raise RuntimeError(f"Failed exporting Cypher script: {err}") from err
