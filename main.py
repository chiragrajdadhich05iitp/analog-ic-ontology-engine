"""Main execution pipeline for the Knowledge Graph Builder project.

Orchestrates PDF loading, section parsing, pin configuration extraction,
and electrical characteristics processing into a unified component artifact.
"""

import argparse
import json
import logging
from pathlib import Path
import sys
from typing import Any

import fitz

from src.extraction.electrical import (
    extract_electrical_text,
    process_electrical_characteristics,
)
from src.extraction.parser import get_section_pages, locate_datasheet_sections
from src.extraction.pdf import load_pdf
from src.validation.validator import validate
from src.graph.builder import build_graph
from src.graph.enrichment import enrich_graph
from src.graph.exporter import (
    export_graphml,
    export_gexf,
    export_json,
    export_cypher,
)

# Configure logging format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("knowledge_graph.pipeline")


def extract_pin_configuration(
    doc: fitz.Document, pin_pages: list[int]
) -> list[dict[str, Any]]:
    """Extract pin configuration entries from specified PDF pages.

    Args:
        doc: Loaded PyMuPDF Document object.
        pin_pages: List of 1-indexed page numbers containing pin configuration tables.

    Returns:
        list[dict[str, Any]]: List of extracted pin record dictionaries.
    """
    pins: list[dict[str, Any]] = []
    if not pin_pages:
        logger.warning("No pin configuration pages identified in datasheet.")
        return pins

    seen_pins = set()
    seen_names = set()

    for page_num in pin_pages:
        if page_num < 1 or page_num > len(doc):
            logger.warning("Skipping out-of-bounds pin page number: %d", page_num)
            continue

        try:
            page = doc.load_page(page_num - 1)
            text = page.get_text() or ""

            # Parse lines looking for pin definitions
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            i = 0
            while i < len(lines):
                line = lines[i]
                parts = line.split(maxsplit=3)
                
                if not parts:
                    i += 1
                    continue

                pin_num_candidate = parts[0]
                
                # A valid pin number is usually a short sequence of digits or simple alphanumeric
                # For this heuristic, we strictly match purely digits to avoid false positives.
                if pin_num_candidate.isdigit() and len(pin_num_candidate) <= 3:
                    pin_num = pin_num_candidate
                    if pin_num in seen_pins:
                        i += 1
                        continue
                    
                    seen_pins.add(pin_num)
                    
                    pin_name = f"PIN_{pin_num}"
                    
                    if len(parts) > 1:
                        pin_name = parts[1]
                    elif i + 1 < len(lines):
                        # Heuristic: the next line might be the pin name if it's short
                        next_line = lines[i+1]
                        if len(next_line) <= 20 and not next_line.isdigit():
                            pin_name = next_line
                            i += 1  # Skip the next line as it was consumed
                    
                    # Prevent duplicate pin names which fail validation
                    if pin_name in seen_names:
                        pin_name = f"{pin_name}_{pin_num}"
                    seen_names.add(pin_name)

                    pins.append({
                        "pin_number": pin_num,
                        "name": pin_name,
                        "type": None,
                        "description": None,
                    })
                i += 1
                
        except Exception as err:
            logger.exception("Failed extracting pins from page %d: %s", page_num, err)

    logger.info("Extracted %d pin configuration entries", len(pins))
    return pins


def run_pipeline(
    pdf_path: str | Path, output_dir: str | Path = "data/extracted"
) -> Path:
    """Run the end-to-end extraction pipeline on a datasheet PDF.

    Args:
        pdf_path: Absolute or relative path to the input PDF datasheet.
        output_dir: Destination directory for the extracted JSON artifact.

    Returns:
        Path: Path to the generated JSON output file.

    Raises:
        FileNotFoundError: If pdf_path does not exist.
        RuntimeError: If pipeline execution encounters a critical failure.
    """
    input_path = Path(pdf_path)
    if not input_path.exists():
        logger.error("Input PDF not found at path: %s", input_path)
        raise FileNotFoundError(f"Input PDF not found at path: {input_path}")

    logger.info("Starting Knowledge Graph pipeline for '%s'", input_path.name)

    # 1. Load PDF using pdf.py module
    try:
        doc = load_pdf(input_path)
    except Exception as err:
        logger.exception("Pipeline failed during PDF loading: %s", err)
        raise RuntimeError(f"PDF loading failed: {err}") from err

    # 2. Locate important datasheet sections using parser.py module
    try:
        sections = locate_datasheet_sections(doc)
        logger.info("Discovered sections: %s", list(sections.keys()))
    except Exception as err:
        logger.exception("Pipeline failed during section location: %s", err)
        raise RuntimeError(f"Section parsing failed: {err}") from err

    # 3. Extract Pin Configuration
    pin_pages = get_section_pages(sections, "pin_configuration")
    pins = extract_pin_configuration(doc, pin_pages)

    # 4. Extract Electrical Characteristics using electrical.py module
    elec_pages = get_section_pages(sections, "electrical_characteristics")
    elec_text = ""
    if elec_pages:
        try:
            elec_text = extract_electrical_text(doc, elec_pages)
        except Exception as err:
            logger.warning("Failed extracting electrical text: %s", err)

    raw_electrical_rows: list[list[str]] = []
    if elec_text:
        for line in elec_text.splitlines():
            tokens = [t.strip() for t in line.split() if t.strip()]
            if len(tokens) >= 2:
                raw_electrical_rows.append(tokens)

    electrical_result = process_electrical_characteristics(raw_electrical_rows)

    # 5. Combine everything into one component dictionary
    component_data: dict[str, Any] = {
        "metadata": {
            "file_name": input_path.name,
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


    # Validate extracted component
    validation_report = validate(component_data)

    if not validation_report.valid:
        logger.error("Validation failed.")

        for error in validation_report.errors:
            logger.error(error)

        raise RuntimeError("Pipeline stopped due to validation errors.")

    if validation_report.warnings:
        logger.warning("Validation completed with warnings.")

        for warning in validation_report.warnings:
            logger.warning(warning)
    logger.info("Building knowledge graph...")

    graph = build_graph(component_data)

    logger.info(
        "Graph built successfully (%d nodes, %d edges)",
        graph.number_of_nodes(),
        graph.number_of_edges(),
    )

    # ------------------------------------------------------------------
    # Enrich graph
    # ------------------------------------------------------------------
    logger.info("Enriching graph...")

    graph = enrich_graph(graph)

    logger.info(
        "Graph enriched (%d nodes, %d edges)",
        graph.number_of_nodes(),
        graph.number_of_edges(),
    )
    # 6. Save the result as JSON in data/ extracted directory
    out_dir_path = Path(output_dir)
    try:
        out_dir_path.mkdir(parents=True, exist_ok=True)
    except Exception as err:
        logger.exception("Failed creating output directory '%s': %s", output_dir, err)
        raise RuntimeError(f"Cannot create output directory '{output_dir}': {err}") from err

    output_file = out_dir_path / f"{input_path.stem}_extracted.json"
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(component_data, f, indent=2, ensure_ascii=False)

        logger.info("Pipeline completed successfully. Output saved to: %s", output_file)

        # ---------------------------------------------------------
        # Export Knowledge Graph
        # ---------------------------------------------------------
        graph_dir = Path("data/graphs")
        graph_dir.mkdir(parents=True, exist_ok=True)

        stem = input_path.stem

        export_graphml(graph, graph_dir / f"{stem}.graphml")
        export_gexf(graph, graph_dir / f"{stem}.gexf")
        export_json(graph, graph_dir / f"{stem}.json")
        export_cypher(graph, graph_dir / f"{stem}.cypher")

        logger.info("Knowledge graph exported successfully to %s", graph_dir)

    except Exception as err:
        logger.exception(
            "Failed saving JSON output artifact to '%s': %s",
            output_file,
            err,
        )
        raise RuntimeError(f"Failed writing output JSON: {err}") from err

    return output_file


def main() -> None:
    """CLI entry point for executing the Knowledge Graph Builder pipeline."""
    parser = argparse.ArgumentParser(
        description="Knowledge Graph Builder - Datasheet Extraction Pipeline"
    )
    parser.add_argument(
        "pdf_path",
        nargs="?",
        help="Path to the datasheet PDF file to process",
    )
    parser.add_argument(
        "--output-dir",
        default="data/extracted",
        help="Directory to save extracted JSON artifacts (default: data/extracted)",
    )

    args = parser.parse_args()

    if not args.pdf_path:
        # Check if any PDFs exist in data/datasheets/ or data/fixtures/
        datasheet_dir = Path("data/datasheets")
        pdf_files = list(datasheet_dir.glob("*.pdf")) + list(
            Path("data/fixtures").glob("*.pdf")
        )

        if pdf_files:
            target_pdf = pdf_files[0]
            logger.info(
                "No PDF argument provided. Defaulting to found datasheet: %s",
                target_pdf,
            )
            run_pipeline(target_pdf, output_dir=args.output_dir)
        else:
            logger.info("Usage: python main.py <path_to_datasheet.pdf>")
            logger.info("No PDF files found in data/datasheets/ or data/fixtures/.")
            sys.exit(0)
    else:
        run_pipeline(args.pdf_path, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
