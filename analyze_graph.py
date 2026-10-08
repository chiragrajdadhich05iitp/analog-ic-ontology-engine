"""Graph analysis script for the Knowledge Graph Builder.

Loads the master Knowledge Graph and produces a semantic breakdown of all
node types, detects structural anomalies (orphans, duplicates), and saves
a machine-readable report.
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import networkx as nx


MASTER_GRAPH = Path("data/graphs/master.graphml")
REPORT_PATH = Path("data/reports/graph_analysis.json")


def load_graph(path: Path) -> nx.MultiDiGraph:
    """Load a MultiDiGraph from a GraphML file.

    Args:
        path: Path to the .graphml file.

    Returns:
        nx.MultiDiGraph: The loaded graph.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Master graph not found at '{path}'. Run populate.py first."
        )
    graph = nx.read_graphml(path)
    # read_graphml returns a MultiDiGraph by default when multigraph=True keys exist,
    # but we coerce to MultiDiGraph just in case.
    return nx.MultiDiGraph(graph)


def count_by_type(graph: nx.MultiDiGraph) -> Counter:
    """Count nodes grouped by their node_type attribute."""
    counts: Counter = Counter()
    for _, data in graph.nodes(data=True):
        node_type = data.get("node_type", "Unknown")
        counts[node_type] += 1
    return counts


def count_relationships(graph: nx.MultiDiGraph) -> Counter:
    """Count edges grouped by their relationship attribute."""
    counts: Counter = Counter()
    for _, _, data in graph.edges(data=True):
        rel = data.get("relationship", data.get("key", "Unknown"))
        counts[rel] += 1
    return counts


def detect_duplicate_names(graph: nx.MultiDiGraph, node_type: str, attr: str) -> list[str]:
    """Find attribute values that appear more than once for a given node type.

    Args:
        graph: The loaded knowledge graph.
        node_type: The node_type to filter by (e.g. 'Component').
        attr: The attribute name to check for duplicates (e.g. 'name').

    Returns:
        list[str]: Sorted list of duplicated attribute values.
    """
    seen: Counter = Counter()
    for _, data in graph.nodes(data=True):
        if data.get("node_type") == node_type:
            val = data.get(attr)
            if val:
                seen[str(val)] += 1
    return sorted(k for k, v in seen.items() if v > 1)


def detect_orphan_nodes(graph: nx.MultiDiGraph) -> list[dict]:
    """Identify nodes with no edges (degree = 0).

    Args:
        graph: The loaded knowledge graph.

    Returns:
        list[dict]: List of dicts with node id and type for each orphan.
    """
    orphans = []
    for node_id, data in graph.nodes(data=True):
        if graph.degree(node_id) == 0:
            orphans.append({
                "id": node_id,
                "node_type": data.get("node_type", "Unknown"),
            })
    return orphans


def main() -> None:
    print("\nLoading master graph...")
    try:
        graph = load_graph(MASTER_GRAPH)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    print(f"Graph loaded: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges\n")

    # --- Node counts by type ---
    type_counts = count_by_type(graph)
    rel_counts = count_relationships(graph)

    # --- Anomaly detection ---
    duplicate_components = detect_duplicate_names(graph, "Component", "file_name")
    duplicate_parameters = detect_duplicate_names(graph, "Parameter", "name")
    orphan_nodes = detect_orphan_nodes(graph)

    # --- Print report to stdout ---
    print("=" * 50)
    print("  Knowledge Graph Semantic Breakdown")
    print("=" * 50)
    print(f"  Components         : {type_counts.get('Component', 0)}")
    print(f"  Pins               : {type_counts.get('Pin', 0)}")
    print(f"  Electrical Metrics : {type_counts.get('ElectricalMetric', 0)}")
    print(f"  Parameters         : {type_counts.get('Parameter', 0)}")
    print(f"  Units              : {type_counts.get('Unit', 0)}")
    print(f"  Conditions         : {type_counts.get('Condition', 0)}")
    print(f"  Sections           : {type_counts.get('Section', 0)}")
    print(f"  Total Nodes        : {graph.number_of_nodes()}")
    print(f"  Total Edges        : {graph.number_of_edges()}")
    print()
    print("  Relationship Counts")
    print("  -------------------")
    for rel, count in rel_counts.most_common():
        print(f"  {rel:<30}: {count}")
    print()
    print("  Anomaly Report")
    print("  --------------")
    if duplicate_components:
        print(f"  Duplicate Components     : {len(duplicate_components)}")
        for c in duplicate_components:
            print(f"    - {c}")
    else:
        print("  Duplicate Components     : None ✓")

    if duplicate_parameters:
        print(f"  Duplicate Parameters     : {len(duplicate_parameters)}")
        for p in duplicate_parameters[:10]:
            print(f"    - {p}")
        if len(duplicate_parameters) > 10:
            print(f"    ... and {len(duplicate_parameters) - 10} more")
    else:
        print("  Duplicate Parameters     : None ✓")

    if orphan_nodes:
        print(f"  Orphan Nodes (degree=0)  : {len(orphan_nodes)}")
        for o in orphan_nodes[:5]:
            print(f"    - [{o['node_type']}] {o['id']}")
        if len(orphan_nodes) > 5:
            print(f"    ... and {len(orphan_nodes) - 5} more")
    else:
        print("  Orphan Nodes (degree=0)  : None ✓")
    print("=" * 50)

    # --- Write JSON report ---
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "node_counts": dict(type_counts),
        "total_nodes": graph.number_of_nodes(),
        "total_edges": graph.number_of_edges(),
        "relationship_counts": dict(rel_counts),
        "anomalies": {
            "duplicate_components": duplicate_components,
            "duplicate_parameters": duplicate_parameters,
            "orphan_nodes": orphan_nodes,
        },
    }

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\nReport saved to: {REPORT_PATH}\n")


if __name__ == "__main__":
    main()
