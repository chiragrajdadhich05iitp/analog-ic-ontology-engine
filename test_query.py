from pathlib import Path

from src.graph.builder import build_graph
from src.graph.enrichment import enrich_graph
from src.query.engine import query_graph

import json

# Load extracted component
with open("data/extracted/LM358_extracted.json", "r", encoding="utf-8") as f:
    component = json.load(f)

# Build graph
graph = build_graph(component)

# Enrich graph
graph = enrich_graph(graph)

# Test queries
queries = [
    "List all pins",
    "Find pin 8",
    "Find output current",
    "List all metrics",
    "List sections",
]

for q in queries:
    print("=" * 60)
    print("QUERY:", q)
    print(query_graph(graph, q))