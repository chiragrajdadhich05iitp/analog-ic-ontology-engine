"""Knowledge Graph enrichment module.

Enriches NetworkX MultiDiGraph instances by extracting shared entity nodes
(Units, Parameters, Conditions, Sections) and establishing semantic relationships:
- USES_UNIT
- MEASURES_PARAMETER
- TESTED_UNDER
- BELONGS_TO_SECTION
"""

import logging
import re
from typing import Any
import networkx as nx

logger = logging.getLogger(__name__)


def _slugify(text: str) -> str:
    """Clean and format a string into a safe node identifier slug."""
    cleaned = re.sub(r"[^\w\s\-\.\°\%\=]", "", str(text).strip())
    return re.sub(r"[\s\-]+", "_", cleaned)


def enrich_graph(graph: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Enrich a NetworkX MultiDiGraph with shared semantic nodes and relationships.

    Adds nodes for shared Units, Parameters, Conditions, and Datasheet Sections,
    and establishes relationships (USES_UNIT, MEASURES_PARAMETER, TESTED_UNDER,
    BELONGS_TO_SECTION) while preserving all existing graph entities.

    Args:
        graph: Input NetworkX MultiDiGraph instance produced by builder.py.

    Returns:
        nx.MultiDiGraph: Enriched graph containing original and new semantic entities.

    Raises:
        TypeError: If input is not a valid NetworkX MultiDiGraph.
    """
    if not isinstance(graph, (nx.MultiDiGraph, nx.DiGraph, nx.Graph)):
        logger.error("Invalid graph instance passed to enrich_graph")
        raise TypeError("Expected a valid NetworkX Graph instance.")

    enriched_g = graph.copy()

    units_created = 0
    params_created = 0
    conditions_created = 0

    sec_pin_id = "Section:Pin_Configuration"
    sec_elec_id = "Section:Electrical_Characteristics"

    enriched_g.add_node(sec_pin_id, node_type="Section", name="Pin Configuration")
    enriched_g.add_node(
        sec_elec_id, node_type="Section", name="Electrical Characteristics"
    )

    node_list = list(enriched_g.nodes(data=True))

    for node_id, data in node_list:
        node_type = data.get("node_type")

        if node_type == "Component":
            enriched_g.add_edge(
                node_id, sec_pin_id, key="HAS_SECTION", relationship="HAS_SECTION"
            )
            enriched_g.add_edge(
                node_id, sec_elec_id, key="HAS_SECTION", relationship="HAS_SECTION"
            )

        elif node_type == "Pin":
            enriched_g.add_edge(
                node_id,
                sec_pin_id,
                key="BELONGS_TO_SECTION",
                relationship="BELONGS_TO_SECTION",
            )

        elif node_type == "ElectricalMetric":
            enriched_g.add_edge(
                node_id,
                sec_elec_id,
                key="BELONGS_TO_SECTION",
                relationship="BELONGS_TO_SECTION",
            )

            # 1. Shared Unit entity (USES_UNIT)
            unit_val = data.get("unit")
            if unit_val and str(unit_val).strip():
                unit_str = str(unit_val).strip()
                unit_node_id = f"Unit:{unit_str}"

                if not enriched_g.has_node(unit_node_id):
                    enriched_g.add_node(unit_node_id, node_type="Unit", name=unit_str)
                    units_created += 1

                enriched_g.add_edge(
                    node_id,
                    unit_node_id,
                    key="USES_UNIT",
                    relationship="USES_UNIT",
                )

            # 2. Shared Parameter entity (MEASURES_PARAMETER)
            param_val = data.get("parameter")
            if param_val and str(param_val).strip():
                param_str = str(param_val).strip()
                param_slug = _slugify(param_str)
                param_node_id = f"Parameter:{param_slug}"

                if not enriched_g.has_node(param_node_id):
                    enriched_g.add_node(
                        param_node_id, node_type="Parameter", name=param_str
                    )
                    params_created += 1

                enriched_g.add_edge(
                    node_id,
                    param_node_id,
                    key="MEASURES_PARAMETER",
                    relationship="MEASURES_PARAMETER",
                )

            # 3. Shared Test Condition entity (TESTED_UNDER)
            cond_val = data.get("test_conditions")
            if cond_val and str(cond_val).strip():
                cond_str = str(cond_val).strip()
                cond_slug = _slugify(cond_str)
                cond_node_id = f"Condition:{cond_slug}"

                if not enriched_g.has_node(cond_node_id):
                    enriched_g.add_node(
                        cond_node_id, node_type="Condition", description=cond_str
                    )
                    conditions_created += 1

                enriched_g.add_edge(
                    node_id,
                    cond_node_id,
                    key="TESTED_UNDER",
                    relationship="TESTED_UNDER",
                )

    logger.info(
        "Graph enrichment complete: created %d Units, %d Parameters, %d Conditions, 2 Sections",
        units_created,
        params_created,
        conditions_created,
    )
    logger.info(
        "Enriched Graph summary: %d total nodes, %d total edges",
        enriched_g.number_of_nodes(),
        enriched_g.number_of_edges(),
    )

    return enriched_g
