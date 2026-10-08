<div align="center">

# Analog IC Ontology Engine (AIO-Engine)
### Automated Topological Knowledge Ingestion, Semantic Normalization, and Multi-Relational Property Graph Synthesis for Mixed-Signal Integrated Circuits

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.9%20%7C%203.10%20%7C%203.11-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Graph Database](https://img.shields.io/badge/Neo4j-Enterprise%205.x-008CC1.svg?style=for-the-badge&logo=neo4j&logoColor=white)](https://neo4j.com/)
[![Network Topology](https://img.shields.io/badge/NetworkX-Algorithmic%20Core-FF6F00.svg?style=for-the-badge)](https://networkx.org/)
[![Architecture](https://img.shields.io/badge/System-Heterogeneous%20Property%20Graph-4B0082.svg?style=for-the-badge)]()

<p align="center">
  <b>A deterministic extraction and schema compilation pipeline formalizing heterogeneous semiconductor datasheets into mathematically verified, query-optimized property graphs.</b>
</p>

</div>

---

## 🔬 Abstract & Problem Formalization

In electronic design automation (EDA) and mixed-signal verification architectures, electronic components have historically suffered from documentation balkanization: critical functional characteristics, Absolute Maximum Ratings ($V_{\text{max}}$, $I_{\text{max}}$, $T_J$), transfer functions, pinout topologies, and thermal operating envelopes are isolated inside unstructured PDF binaries.

**AIO-Engine** addresses this semantic disconnect. It provides a formal, deterministic ingestion pipeline that parses heterogeneous microelectronic documentation, performs topological entity-relation extraction, resolves parametric co-references, and constructs a strongly typed, directed multi-relational property graph $\mathcal{G} = (\mathcal{V}, \mathcal{E}, \mathcal{T}, \mathcal{W})$. The resulting schema projects high-dimensional electrical dependencies into Cypher-indexable Neo4j database layers and local NetworkX graph invariants for zero-shot downstream retrieval, automated parts compatibility validation, and GraphRAG pipelines.

---

## 🏛️ System Architecture

The pipeline processes raw semiconductor specifications across three isolated execution layers:


```

[ Unstructured Component Datasheet (PDF) ]
│
▼
┌────────────────────────────────────────────────────────┐
│ 1. Extraction & Lexical Disambiguation Layer           │
│    - Tabular Bounding Box Segmentation                 │
│    - Regex Heuristics for Sub-unit Normalization       │
│    - Parametric Interval Reduction (Min/Typ/Max)       │
└──────────────────────────┬─────────────────────────────┘
│ Canonical Token Stream
▼
┌────────────────────────────────────────────────────────┐
│ 2. Schema Synthesis & Topological Verification Core    │
│    - Type Verification: V = {Comp, Pin, Param, Cond}   │
│    - Edge Typing: E = {EXPOSES, CONSTRAINED_BY, MAPS}  │
│    - NetworkX Directed Graph (DiGraph) Construction    │
│    - Cycle Resolution & Connectivity Invariants        │
└──────────────────────────┬─────────────────────────────┘
│ Serialized Property Graph
▼
┌────────────────────────────────────────────────────────┐
│ 3. Persistence & Graph Execution Layer                 │
│    - Transactional Cypher Mutation Batches             │
│    - ACID Compliant Ingestion Engine (Neo4j)           │
│    - Multi-Hop Subgraph Traversals & Metric Analysis   │
└────────────────────────────────────────────────────────┘

```

---

## 📊 Ontological Schema Definition

The graph domain model enforces a mathematically rigorous, schema-bounded semantic network:

### 1. Vertex Sets ($\mathcal{V}$)
* $\mathcal{V}_{\text{Component}}$: Hardware modules identified by unified MPN (Manufacturer Part Number).
* $\mathcal{V}_{\text{Pin}}$: Hardware interconnect nodes characterized by electrical signaling classes ($\text{Input}$, $\text{Output}$, $\text{Power}$, $\text{Ground}$, $\text{High-Z}$).
* $\mathcal{V}_{\text{Parameter}}$: Scalar and vector electrical metrics ($V_{OS}$, $\text{PSRR}$, $\text{GBW}$, $I_Q$, $R_{DS(\text{on})}$).
* $\mathcal{V}_{\text{Condition}}$: Dynamic operational contexts ($V_{DD} = 5.0\text{V}$, $T_A = 25^{\circ}\text{C}$, $R_L = 10\text{k}\Omega$).
* $\mathcal{V}_{\text{Package}}$: Mechanical boundary abstractions ($\text{SOIC-8}$, $\text{SOT-23}$, $\text{TSSOP-14}$).

### 2. Directed Edge Classes ($\mathcal{E}$)
$$\begin{aligned} (\text{Component}) &\xrightarrow{\text{EXPOSES}} (\text{Pin}) \\ (\text{Component}) &\xrightarrow{\text{ENCAPSULATED\_IN}} (\text{Package}) \\ (\text{Component}) &\xrightarrow{\text{CHARACTERIZED\_BY}} (\text{Parameter}) \\ (\text{Parameter}) &\xrightarrow{\text{MEASURED\_UNDER}} (\text{Condition}) \\ (\text{Parameter}) &\xrightarrow{\text{BOUNDED\_BY}} (\text{OperatingLimit}) \end{aligned}$$

---

## ⚡ Mathematical & Algorithmic Formulation

For any analog integrated circuit parameter $p \in \mathcal{V}_{\text{Parameter}}$, the parametric attribute tuple is normalized as:

$$\mathcal{S}_p = \langle v_{\min}, v_{\text{typ}}, v_{\max}, u, \mathbf{C}_p \rangle$$

Where:
* $v \in \mathbb{R} \cup \{\emptyset\}$ designates deterministic electrical bounds.
* $u \in \mathcal{U}_{\text{SI}}$ denotes standard dimensional units (scaled via metric prefixes: $\text{pico}$, $\text{nano}$, $\text{micro}$, $\text{milli}$).
* $\mathbf{C}_p = \{c_1, c_2, \dots, c_k\} \subset \mathcal{V}_{\text{Condition}}$ represents the constraint hyperplane bounding the specified metric.

The graph density metric and topological adjacency are continuously validated prior to persistence:

$$\text{Density}(\mathcal{G}) = \frac{\vert{}\mathcal{E}\vert{}}{\vert{}\mathcal{V}\vert{}(\vert{}\mathcal{V}\vert{} - 1)}$$

---

## 🛠️ Repository Directory Structure

```ascii
analog-ic-ontology-engine/
│
├── data/
│   ├── raw/                  # Source analog datasheets (heterogeneous PDFs)
│   ├── intermediate/         # Normalized token trees, tabular extractions
│   └── output/               # Graph serializations (.graphml, .gpickle)
│
├── notebooks/
│   ├── 01_eda_distribution.ipynb      # Parametric skewness & cluster evaluations
│   └── 02_graph_topology.ipynb       # Spectral graph centrality analysis
│
├── src/
│   ├── __init__.py
│   ├── parsers/              # Deterministic PDF stream parsers
│   ├── schema/               # Formal node/relation Pydantic models
│   ├── topology/             # NetworkX topological mapping and assertion layers
│   └── connectors/           # Neo4j bolt driver integration and Cypher builders
│
├── tests/
│   ├── test_parser.py        # Token integrity unit tests
│   ├── test_schema.py        # Strict typing assertion tests
│   └── test_graph_export.py  # Graph serialization integrity suites
│
├── analyze_graph.py          # Adjacency matrix and topological metric inspector
├── load_to_neo4j.py          # Batched ACID transaction loader for Neo4j
├── populate.py               # Main deterministic execution pipeline
├── requirements.txt          # Frozen dependency manifest
├── LICENSE                   # MIT License
└── README.md                 # Technical specification document

```

---

## 🚀 Execution & Setup Protocol

### 1. Environment Isolation

Deploy within an isolated Unix or Windows virtual environment running Python 3.9+:

```bash
# Clone the repository
git clone [https://github.com/chiragrajdadhich05iitp/analog-ic-ontology-engine.git](https://github.com/chiragrajdadhich05iitp/analog-ic-ontology-engine.git)
cd analog-ic-ontology-engine

# Initialize environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1

# Install deterministic dependencies
pip install --upgrade pip
pip install -r requirements.txt

```

### 2. Graph Ingestion & Transformation Pipeline

```bash
# Phase 1: Ingest source documentation, extract entities, populate internal graph model
python populate.py

# Phase 2: Transmit graph structures into Neo4j via ACID transactional pipelines
python load_to_neo4j.py --uri bolt://localhost:7687 --user neo4j --password secret

# Phase 3: Execute topological analysis and extract semantic statistics
python analyze_graph.py --metrics centrality,clustering,diameter

```

---

## 🔍 Cypher Traversal Exemplar

Retrieve all operational amplifier variants whose typical Quiescent Current ($I_Q$) is below $500\mu\text{A}$ across ambient temperature $T_A = 25^{\circ}\text{C}$:

```cypher
MATCH (c:Component)-[:CHARACTERIZED_BY]->(p:Parameter {name: "Quiescent Current"})
MATCH (p)-[:MEASURED_UNDER]->(cond:Condition)
WHERE p.typ_value < 500 
  AND p.unit = "uA" 
  AND cond.ambient_temp = "25C"
RETURN c.mpn AS Component, p.typ_value AS Iq_Typ, p.max_value AS Iq_Max
ORDER BY p.typ_value ASC;

```

---

## 📑 Verification & Rigor

All commits, graph generation pipelines, and serialization adapters are tested under continuous assertion suites executing deterministic unit validations across the extraction parser, schema layer, and graph consistency checks.

```bash
pytest tests/ -v --cov=src --cov-report=term-missing

```

---

## 📜 Intellectual Property & Licensing

Distributed under the terms of the **MIT License**. The system is completely open for academic, industrial research, and production deployment workflows. Consult [`LICENSE`](https://www.google.com/search?q=LICENSE) for complete legal definitions.

```

```
