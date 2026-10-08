"""Load the master Knowledge Graph into a Neo4j database.

Reads credentials from the project .env file, loads the master GraphML,
and uploads all nodes and relationships directly into Neo4j using the
project's Neo4jLoader.

Usage:
    python load_to_neo4j.py
"""

import logging
import sys
from pathlib import Path

import networkx as nx
from dotenv import load_dotenv

from src.graph.neo4j_loader import Neo4jLoader

MASTER_GRAPH = Path("data/graphs/master.graphml")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("load_to_neo4j")


def load_graph_from_file(path: Path) -> nx.MultiDiGraph:
    """Load a NetworkX MultiDiGraph from a GraphML file.

    Args:
        path: Absolute or relative path to the ``.graphml`` file.

    Returns:
        nx.MultiDiGraph: The loaded graph.

    Raises:
        FileNotFoundError: If the file does not exist.
        RuntimeError: If the file cannot be parsed as a valid graph.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Master graph not found at '{path}'. "
            "Run populate.py first to generate it."
        )
    try:
        graph = nx.read_graphml(path)
        return nx.MultiDiGraph(graph)
    except Exception as err:
        raise RuntimeError(
            f"Failed to parse graph file '{path}': {err}"
        ) from err


def main() -> None:
    """Entry point: load the master graph into Neo4j and print a summary."""
    # Load .env credentials
    load_dotenv()

    print()
    print("=" * 41)
    print("  Loading Knowledge Graph into Neo4j")
    print("=" * 41)

    # 1. Read graph
    print(f"\nReading graph from '{MASTER_GRAPH}'...")
    try:
        graph = load_graph_from_file(MASTER_GRAPH)
    except FileNotFoundError as err:
        print(f"\nERROR: {err}")
        sys.exit(1)
    except RuntimeError as err:
        print(f"\nERROR: {err}")
        sys.exit(1)

    print(f"Nodes : {graph.number_of_nodes()}")
    print(f"Edges : {graph.number_of_edges()}")

    # 2. Connect
    print("\nConnecting to Neo4j...")
    loader: Neo4jLoader | None = None
    try:
        loader = Neo4jLoader()
    except ImportError as err:
        print(f"\nERROR: {err}")
        sys.exit(1)
    except ValueError as err:
        print(
            f"\nERROR: Missing credentials — {err}\n"
            "Ensure NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD are set "
            "in your .env file."
        )
        sys.exit(1)
    except Exception as err:
        print(f"\nERROR: Could not initialise Neo4j driver — {err}")
        sys.exit(1)

    # 3. Upload
    print("Uploading graph...")
    try:
        stats = loader.load_graph(graph)
    except Exception as err:
        # Broad catch: covers auth failures, connection drops, Cypher errors, etc.
        err_type = type(err).__name__
        print(f"\nERROR ({err_type}): {err}")
        logger.exception("Neo4j upload failed.")
        sys.exit(1)
    finally:
        # Always release the driver connection.
        if loader is not None:
            loader.close()

    # 4. Summary
    print()
    print("Upload completed successfully.")
    print()
    print(f"Nodes created         : {stats['nodes_created']}")
    print(f"Relationships created : {stats['relationships_created']}")
    print(f"Execution time        : {stats['execution_time']:.2f} s")
    print()


if __name__ == "__main__":
    main()
