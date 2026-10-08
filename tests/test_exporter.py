import json
import pytest
import networkx as nx
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.graph.builder import build_graph
from src.graph.enrichment import enrich_graph
from src.graph.exporter import (
    export_graphml,
    export_gexf,
    export_json,
    export_cypher,
)

FIXTURE_JSON = Path("data/extracted/LM358_extracted.json")


@pytest.fixture
def base_graph():
    """Fixture providing an enriched graph built from the LM358 JSON."""
    with open(FIXTURE_JSON, "r", encoding="utf-8") as f:
        component_data = json.load(f)
    graph = build_graph(component_data)
    return enrich_graph(graph)


@pytest.fixture
def empty_graph():
    """Fixture providing an empty graph."""
    return nx.MultiDiGraph()


def test_export_graphml_success(base_graph, tmp_path):
    """Test successful GraphML export to a temporary directory."""
    out_file = tmp_path / "test.graphml"
    result_path = export_graphml(base_graph, out_file)
    
    assert result_path == out_file
    assert out_file.exists()
    assert out_file.stat().st_size > 0
    # Basic check that it's XML
    with open(out_file, "r", encoding="utf-8") as f:
        content = f.read()
        assert "<?xml" in content
        assert "graphml" in content


def test_export_graphml_invalid_type(tmp_path):
    with pytest.raises(TypeError, match="Expected a valid NetworkX Graph instance"):
        export_graphml("Not a graph", tmp_path / "test.graphml")  # type: ignore


@patch("networkx.write_graphml")
def test_export_graphml_failure(mock_write, base_graph, tmp_path):
    mock_write.side_effect = Exception("Write failed")
    with pytest.raises(RuntimeError, match="Failed exporting GraphML"):
        export_graphml(base_graph, tmp_path / "test.graphml")


def test_export_gexf_success(base_graph, tmp_path):
    """Test successful GEXF export."""
    out_file = tmp_path / "test.gexf"
    result_path = export_gexf(base_graph, out_file)
    
    assert result_path == out_file
    assert out_file.exists()
    assert out_file.stat().st_size > 0
    with open(out_file, "r", encoding="utf-8") as f:
        content = f.read()
        assert "<?xml" in content
        assert "gexf" in content


def test_export_gexf_invalid_type(tmp_path):
    with pytest.raises(TypeError, match="Expected a valid NetworkX Graph instance"):
        export_gexf("Not a graph", tmp_path / "test.gexf")  # type: ignore


@patch("networkx.write_gexf")
def test_export_gexf_failure(mock_write, base_graph, tmp_path):
    mock_write.side_effect = Exception("Write failed")
    with pytest.raises(RuntimeError, match="Failed exporting GEXF"):
        export_gexf(base_graph, tmp_path / "test.gexf")


def test_export_json_success(base_graph, tmp_path):
    """Test successful Node-Link JSON export."""
    out_file = tmp_path / "test.json"
    result_path = export_json(base_graph, out_file)
    
    assert result_path == out_file
    assert out_file.exists()
    assert out_file.stat().st_size > 0
    
    with open(out_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert "nodes" in data
        assert any(key in data for key in ("links", "edges"))

def test_export_json_invalid_type(tmp_path):
    with pytest.raises(TypeError, match="Expected a valid NetworkX Graph instance"):
        export_json("Not a graph", tmp_path / "test.json")  # type: ignore


@patch("json.dump")
def test_export_json_failure(mock_dump, base_graph, tmp_path):
    mock_dump.side_effect = Exception("Dump failed")
    with pytest.raises(RuntimeError, match="Failed exporting JSON"):
        export_json(base_graph, tmp_path / "test.json")


def test_export_cypher_success(base_graph, tmp_path):
    """Test successful Cypher script generation."""
    out_file = tmp_path / "test.cypher"
    result_path = export_cypher(base_graph, out_file)
    
    assert result_path == out_file
    assert out_file.exists()
    assert out_file.stat().st_size > 0
    
    with open(out_file, "r", encoding="utf-8") as f:
        content = f.read()
        assert "CREATE (:" in content
        assert "MATCH (a" in content


def test_export_cypher_invalid_type(tmp_path):
    with pytest.raises(TypeError, match="Expected a valid NetworkX Graph instance"):
        export_cypher("Not a graph", tmp_path / "test.cypher")  # type: ignore


@patch("builtins.open")
def test_export_cypher_failure(mock_open, base_graph, tmp_path):
    mock_open.side_effect = Exception("IO Error")
    with pytest.raises(RuntimeError, match="Failed exporting Cypher script"):
        export_cypher(base_graph, tmp_path / "test.cypher")


def test_export_empty_graph(empty_graph, tmp_path):
    """Test exporting an empty graph succeeds for all formats without errors."""
    gml = export_graphml(empty_graph, tmp_path / "empty.graphml")
    gexf = export_gexf(empty_graph, tmp_path / "empty.gexf")
    js = export_json(empty_graph, tmp_path / "empty.json")
    cypher = export_cypher(empty_graph, tmp_path / "empty.cypher")
    
    assert gml.exists()
    assert gexf.exists()
    assert js.exists()
    assert cypher.exists()


def test_export_file_overwrite(empty_graph, tmp_path):
    """Test that exporting to an existing file correctly overwrites it."""
    out_file = tmp_path / "overwrite.json"
    
    with open(out_file, "w") as f:
        f.write("existing content")
        
    export_json(empty_graph, out_file)
    
    with open(out_file, "r") as f:
        content = f.read()
        assert "existing content" not in content
        assert "nodes" in content
