"""Data Population Script.

Scans the data/datasheets/ directory, runs the extraction and graph building
pipeline on every PDF, merges all graphs into a single master knowledge graph,
and exports the master graph in multiple formats.
"""

import json
import logging
import re
from pathlib import Path
import sys

import networkx as nx

from src.extraction.pdf import load_pdf
from src.extraction.parser import locate_datasheet_sections, get_section_pages
from main import extract_pin_configuration
from src.extraction.electrical import (
    extract_electrical_text,
    process_electrical_characteristics,
)
from src.validation.validator import validate
from src.graph.builder import build_graph
from src.graph.enrichment import enrich_graph
from src.graph.exporter import (
    export_graphml,
    export_gexf,
    export_json,
    export_cypher,
)

VALID_PIN_RE = re.compile(r"^[A-Za-z0-9_+\-()/±]+$")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("populate")


def process_pdf_to_graph(pdf_path: Path) -> nx.MultiDiGraph | None:
    """Run the extraction pipeline on a single PDF and return its enriched graph."""
    logger.info("Processing '%s'", pdf_path.name)

    try:
        doc = load_pdf(pdf_path)
    except Exception as e:
        logger.error("Failed to load %s: %s", pdf_path, e)
        return None

    try:
        sections = locate_datasheet_sections(doc)
    except Exception as e:
        logger.error("Failed to parse sections for %s: %s", pdf_path, e)
        return None

    pin_pages = get_section_pages(sections, "pin_configuration")
    pins = extract_pin_configuration(doc, pin_pages)

    # ------------------------------------------------------------------
    # Filter obviously invalid pin entries before graph construction
    # ------------------------------------------------------------------
    filtered_pins = []

    for pin in pins:
        try:
            pin_number = int(str(pin.get("pin_number", "")).strip())
        except (ValueError, TypeError):
            logger.warning("Skipping pin with invalid pin number: %s", pin)
            continue

        pin_name = str(pin.get("name", "")).strip()

        # Reject impossible pin numbers
        if not (1 <= pin_number <= 64):
            logger.warning("Skipping invalid pin number %s (%s)", pin_number, pin_name)
            continue

        # Reject empty names
        if not pin_name:
            logger.warning("Skipping empty pin name: %s", pin)
            continue

        # Reject OCR/control-character garbage
        if not VALID_PIN_RE.fullmatch(pin_name):
            logger.warning("Skipping invalid pin name '%s'", pin_name)
            continue

        filtered_pins.append(
            {
                **pin,
                "pin_number": str(pin_number),
                "name": pin_name,
            }
        )

    pins = filtered_pins

    logger.info("Retained %d valid pins after filtering", len(pins))

    elec_pages = get_section_pages(sections, "electrical_characteristics")
    elec_text = ""
    if elec_pages:
        try:
            elec_text = extract_electrical_text(doc, elec_pages)
        except Exception as e:
            logger.warning("Failed extracting electrical text for %s: %s", pdf_path, e)

    raw_electrical_rows = []
    if elec_text:
        for line in elec_text.splitlines():
            tokens = [t.strip() for t in line.split() if t.strip()]
            if len(tokens) >= 2:
                raw_electrical_rows.append(tokens)

    electrical_result = process_electrical_characteristics(raw_electrical_rows)

    component_data = {
        "metadata": {
            "file_name": pdf_path.name,
            "total_pages": len(doc),
            "sections_found": {k: list(v) for k, v in sections.items() if v},
        },
        "pin_configuration": {
            "pages": pin_pages,
            "total_pins": len(pins),
            "pins": pins,
        },
        "electrical_characteristics": electrical_result,
    }

    validation_report = validate(component_data)
    if not validation_report.valid:
        logger.error("Validation failed for %s. Skipping.", pdf_path.name)
        for err in validation_report.errors:
            logger.error(" - %s", err)
        return None

    try:
        graph = build_graph(component_data)
        enriched_graph = enrich_graph(graph)
        return enriched_graph
    except Exception as e:
        logger.error("Failed to build/enrich graph for %s: %s", pdf_path, e)
        return None


def main() -> None:
    datasheets_dir = Path("data/datasheets")
    if not datasheets_dir.exists() or not datasheets_dir.is_dir():
        logger.error("Directory '%s' does not exist.", datasheets_dir)
        sys.exit(1)

    pdf_files = list(datasheets_dir.glob("*.pdf"))
    if not pdf_files:
        logger.error("No PDFs found in '%s'.", datasheets_dir)
        sys.exit(1)

    master_graph = nx.MultiDiGraph()
    processed_files: list[str] = []
    failed_files: list[str] = []

    print("\nStarting Knowledge Graph Population...")
    print("-" * 40)

    for pdf_path in pdf_files:
        comp_graph = process_pdf_to_graph(pdf_path)
        if comp_graph:
            master_graph = nx.compose(master_graph, comp_graph)
            processed_files.append(pdf_path.name)
            print(f"✓ {pdf_path.name}")
        else:
            failed_files.append(pdf_path.name)
            print(f"✗ {pdf_path.name} (failed)")

    print("\nBuilding and exporting Master Graph...")

    if master_graph.number_of_nodes() == 0:
        logger.error("Master graph is empty. Exiting without export.")
        sys.exit(1)

    output_dir = Path("data/graphs")
    output_dir.mkdir(parents=True, exist_ok=True)

    export_paths = {}
    try:
        gml_path = export_graphml(master_graph, output_dir / "master.graphml")
        export_paths["graphml"] = str(gml_path)

        gexf_path = export_gexf(master_graph, output_dir / "master.gexf")
        export_paths["gexf"] = str(gexf_path)

        json_path = export_json(master_graph, output_dir / "master.json")
        export_paths["json"] = str(json_path)

        cypher_path = export_cypher(master_graph, output_dir / "master.cypher")
        export_paths["cypher"] = str(cypher_path)
    except Exception as e:
        logger.exception("Failed to export master graph: %s", e)
        sys.exit(1)

    # Generate population report
    reports_dir = Path("data/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / "population_report.json"

    report_data = {
        "datasheets_processed": processed_files,
        "datasheets_failed": failed_files,
        "total_components": len(processed_files),
        "total_nodes": master_graph.number_of_nodes(),
        "total_edges": master_graph.number_of_edges(),
        "export_paths": export_paths
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    print("\nPopulation Summary")
    print("-" * 18)
    print(f"Processed: {len(processed_files)}")
    print(f"Failed: {len(failed_files)}")
    print(f"Nodes: {master_graph.number_of_nodes()}")
    print(f"Edges: {master_graph.number_of_edges()}")
    print(f"Report: {report_path}\n")


if __name__ == "__main__":
    main()