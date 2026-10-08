import json
import pytest
import networkx as nx
from pathlib import Path

from src.graph.builder import build_graph
from src.graph.enrichment import enrich_graph

FIXTURE_JSON = Path("data/extracted/LM358_extracted.json")


@pytest.fixture
def base_graph():
    """Fixture providing a baseline graph built from the LM358 JSON."""
    with open(FIXTURE_JSON, "r", encoding="utf-8") as f:
        component_data = json.load(f)
    return build_graph(component_data)


def test_enrich_graph_success(base_graph):
    """Test successful enrichment of a valid base graph."""
    enriched = enrich_graph(base_graph)
    
    assert isinstance(enriched, nx.MultiDiGraph)
    # The enriched graph should have more nodes and edges than the base graph
    assert enriched.number_of_nodes() > base_graph.number_of_nodes()
    assert enriched.number_of_edges() > base_graph.number_of_edges()


def test_enrich_graph_original_unmodified(base_graph):
    """Test that the original graph object is not mutated by enrichment."""
    original_nodes = set(base_graph.nodes())
    original_edges = set(base_graph.edges(keys=True))
    
    enrich_graph(base_graph)
    
    assert set(base_graph.nodes()) == original_nodes
    assert set(base_graph.edges(keys=True)) == original_edges


def test_enrich_graph_section_nodes(base_graph):
    """Test that Section nodes and HAS_SECTION edges are properly created."""
    enriched = enrich_graph(base_graph)
    
    sec_pin_id = "Section:Pin_Configuration"
    sec_elec_id = "Section:Electrical_Characteristics"
    
    assert enriched.has_node(sec_pin_id)
    assert enriched.nodes[sec_pin_id]["node_type"] == "Section"
    
    assert enriched.has_node(sec_elec_id)
    assert enriched.nodes[sec_elec_id]["node_type"] == "Section"
    
    comp_id = "Component:LM358.pdf"
    
    # HAS_SECTION relationships
    assert enriched.has_edge(comp_id, sec_pin_id)
    assert enriched.has_edge(comp_id, sec_elec_id)


def test_enrich_graph_unit_nodes(base_graph):
    """Test that Unit nodes and USES_UNIT edges are correctly created."""
    enriched = enrich_graph(base_graph)
    
    unit_nodes = [n for n, attr in enriched.nodes(data=True) if attr.get("node_type") == "Unit"]
    assert len(unit_nodes) > 0
    
    # Check edges
    uses_unit_edges = [
        (u, v) for u, v, k, attr in enriched.edges(keys=True, data=True) 
        if attr.get("relationship") == "USES_UNIT"
    ]
    assert len(uses_unit_edges) > 0


def test_enrich_graph_parameter_nodes(base_graph):
    """Test that Parameter nodes and MEASURES_PARAMETER edges are correctly created."""
    enriched = enrich_graph(base_graph)
    
    param_nodes = [n for n, attr in enriched.nodes(data=True) if attr.get("node_type") == "Parameter"]
    assert len(param_nodes) > 0
    
    # Check edges
    measures_param_edges = [
        (u, v) for u, v, k, attr in enriched.edges(keys=True, data=True) 
        if attr.get("relationship") == "MEASURES_PARAMETER"
    ]
    assert len(measures_param_edges) > 0


def test_enrich_graph_condition_nodes(base_graph):
    """Test that Condition nodes and TESTED_UNDER edges are correctly created."""
    enriched = enrich_graph(base_graph)
    
    cond_nodes = [n for n, attr in enriched.nodes(data=True) if attr.get("node_type") == "Condition"]
    assert len(cond_nodes) > 0
    
    # Check edges
    tested_under_edges = [
        (u, v) for u, v, k, attr in enriched.edges(keys=True, data=True) 
        if attr.get("relationship") == "TESTED_UNDER"
    ]
    assert len(tested_under_edges) > 0


def test_enrich_graph_belongs_to_section_edges(base_graph):
    """Test that BELONGS_TO_SECTION edges are assigned for Pins and Metrics."""
    enriched = enrich_graph(base_graph)
    
    belongs_edges = [
        (u, v) for u, v, k, attr in enriched.edges(keys=True, data=True) 
        if attr.get("relationship") == "BELONGS_TO_SECTION"
    ]
    assert len(belongs_edges) > 0


def test_enrich_graph_empty_graph():
    """Test that enrich_graph safely handles an empty graph."""
    empty_graph = nx.MultiDiGraph()
    enriched = enrich_graph(empty_graph)
    
    # It should still create the 2 default Section nodes
    assert enriched.number_of_nodes() == 2
    assert enriched.number_of_edges() == 0


def test_enrich_graph_invalid_input():
    """Test that enrich_graph raises TypeError for non-NetworkX inputs."""
    with pytest.raises(TypeError, match="Expected a valid NetworkX Graph instance"):
        enrich_graph("Not a graph")  # type: ignore
