import json
import pytest
import networkx as nx
from pathlib import Path

from src.graph.builder import build_graph

FIXTURE_JSON = Path("data/extracted/LM358_extracted.json")


@pytest.fixture
def component_data():
    """Fixture providing the real extracted LM358 JSON data."""
    with open(FIXTURE_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def test_build_graph_success(component_data):
    """Test successful construction of graph from real extracted data."""
    graph = build_graph(component_data)
    
    assert isinstance(graph, nx.MultiDiGraph)
    assert graph.number_of_nodes() > 0
    assert graph.number_of_edges() > 0


def test_build_graph_component_node(component_data):
    """Test that the Component node is properly created with metadata."""
    graph = build_graph(component_data)
    
    # Locate component node
    component_nodes = [n for n, attr in graph.nodes(data=True) if attr.get("node_type") == "Component"]
    assert len(component_nodes) == 1
    
    comp_id = component_nodes[0]
    attrs = graph.nodes[comp_id]
    
    assert attrs["file_name"] == "LM358.pdf"
    assert "total_pages" in attrs
    assert "sections_found" in attrs


def test_build_graph_pin_nodes(component_data):
    """Test that Pin nodes and HAS_PIN edges are properly created."""
    graph = build_graph(component_data)
    
    comp_id = "Component:LM358.pdf"
    
    pin_nodes = [n for n, attr in graph.nodes(data=True) if attr.get("node_type") == "Pin"]
    assert len(pin_nodes) > 0
    
    # Check attributes of the first pin
    first_pin = pin_nodes[0]
    pin_attrs = graph.nodes[first_pin]
    assert "pin_number" in pin_attrs
    assert "name" in pin_attrs
    
    # Verify HAS_PIN relationship
    assert graph.has_edge(comp_id, first_pin)
    edges = graph.get_edge_data(comp_id, first_pin)
    assert any(edge_data.get("relationship") == "HAS_PIN" for edge_data in edges.values())


def test_build_graph_metric_nodes(component_data):
    """Test that ElectricalMetric nodes and HAS_METRIC edges are properly created."""
    graph = build_graph(component_data)
    
    comp_id = "Component:LM358.pdf"
    
    metric_nodes = [n for n, attr in graph.nodes(data=True) if attr.get("node_type") == "ElectricalMetric"]
    assert len(metric_nodes) > 0
    
    # Check attributes of the first metric
    first_metric = metric_nodes[0]
    metric_attrs = graph.nodes[first_metric]
    assert "parameter" in metric_attrs
    assert "unit" in metric_attrs
    
    # Verify HAS_METRIC relationship from Component
    assert graph.has_edge(comp_id, first_metric)
    
    # Verify HAS_METRIC relationship from Pins (builder connects pins to metrics)
    pin_nodes = [n for n, attr in graph.nodes(data=True) if attr.get("node_type") == "Pin"]
    # At least one pin should have an edge to this metric
    has_pin_edge = any(graph.has_edge(p_id, first_metric) for p_id in pin_nodes)
    assert has_pin_edge


def test_build_graph_empty_component():
    """Test building a graph from an empty or minimal dictionary."""
    graph = build_graph({})
    assert isinstance(graph, nx.MultiDiGraph)
    
    component_nodes = [n for n, attr in graph.nodes(data=True) if attr.get("node_type") == "Component"]
    assert len(component_nodes) == 1
    assert graph.nodes[component_nodes[0]]["file_name"] == "Unknown_Component"
    
    # Should have no pins or metrics
    assert graph.number_of_nodes() == 1
    assert graph.number_of_edges() == 0


def test_build_graph_invalid_input():
    """Test build_graph raises ValueError for non-dictionary inputs."""
    with pytest.raises(ValueError, match="Input component_data must be a dictionary"):
        build_graph("Not a dict")  # type: ignore


def test_build_graph_metric_pin_matching():
    """Test the specific heuristic that matches metric names to pins."""
    mock_data = {
        "metadata": {"file_name": "test.pdf"},
        "pin_configuration": {
            "pins": [{"pin_number": "1", "name": "VCC"}]
        },
        "electrical_characteristics": {
            "metrics": [{"parameter": "Supply Voltage", "symbol": "VCC"}]
        }
    }
    
    graph = build_graph(mock_data)
    
    pin_id = "Pin:1:VCC"
    metric_id = "Metric:1:VCC"
    
    assert graph.has_node(pin_id)
    assert graph.has_node(metric_id)
    assert graph.has_edge(pin_id, metric_id)
