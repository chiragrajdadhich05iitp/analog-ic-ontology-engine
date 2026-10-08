"""Electrical characteristics extraction and normalization module.

Responsibilities:
- Extract electrical characteristics text/tables from datasheet pages
- Parse raw tabular data into metric records
- Normalize values (min, typ, max), units (V, A, mA, µA, °C, etc.), and parameter names
- Return structured Python dictionaries representing electrical metrics
"""

import logging
import re
from typing import Any, TypedDict
import fitz

logger = logging.getLogger(__name__)


class ElectricalMetric(TypedDict, total=False):
    """Type definition for a single normalized electrical metric record."""

    parameter: str
    symbol: str | None
    test_conditions: str | None
    min_value: float | int | None
    typ_value: float | int | None
    max_value: float | int | None
    unit: str | None
    notes: str | None


class ElectricalCharacteristicsResult(TypedDict):
    """Type definition for the complete electrical characteristics result."""

    section: str
    total_metrics: int
    metrics: list[ElectricalMetric]


# Unit normalization mapping rules
UNIT_MAP: dict[str, str] = {
    "v": "V",
    "volts": "V",
    "volt": "V",
    "mv": "mV",
    "millivolts": "mV",
    "a": "A",
    "amps": "A",
    "ampere": "A",
    "ma": "mA",
    "milliamps": "mA",
    "ua": "µA",
    "microamps": "µA",
    "na": "nA",
    "nanoamps": "nA",
    "c": "°C",
    "deg c": "°C",
    "degree c": "°C",
    "°c": "°C",
    "hz": "Hz",
    "khz": "kHz",
    "mhz": "MHz",
    "ghz": "GHz",
    "ohm": "Ω",
    "ohms": "Ω",
    "kohm": "kΩ",
    "mohm": "MΩ",
    "ns": "ns",
    "us": "µs",
    "ms": "ms",
    "s": "s",
    "%": "%",
}


def extract_electrical_text(doc: fitz.Document, page_numbers: list[int]) -> str:
    """Extract concatenated text from specified electrical characteristics pages.

    Args:
        doc: Loaded PyMuPDF Document object.
        page_numbers: List of 1-indexed page numbers containing electrical characteristics.

    Returns:
        str: Concatenated text content from specified pages.

    Raises:
        TypeError: If doc is not a valid fitz.Document.
        IndexError: If any page number is out of bounds.
    """
# Global cache to track page content for debugging/source page lookup
_PAGE_TEXTS: list[tuple[int, str]] = []


def extract_electrical_text(doc: fitz.Document, page_numbers: list[int]) -> str:
    """Extract and concatenate text content from specified PDF pages.

    Args:
        doc: Loaded PyMuPDF Document object.
        page_numbers: List of 1-indexed page numbers containing electrical characteristics.

    Returns:
        str: Concatenated text content from specified pages.

    Raises:
        TypeError: If doc is not a valid fitz.Document.
        IndexError: If any page number is out of bounds.
    """
    global _PAGE_TEXTS
    _PAGE_TEXTS = []

    if not isinstance(doc, fitz.Document):
        logger.error("Invalid document instance passed to extract_electrical_text")
        raise TypeError("Expected a valid fitz.Document instance.")

    text_blocks: list[str] = []
    for page_num in page_numbers:
        if page_num < 1 or page_num > len(doc):
            logger.error("Page number %d out of bounds (1..%d)", page_num, len(doc))
            raise IndexError(f"Page number {page_num} out of bounds.")

        page = doc.load_page(page_num - 1)
        text = page.get_text() or ""
        text_blocks.append(text)
        _PAGE_TEXTS.append((page_num, text))
        logger.debug("Extracted %d characters from page %d", len(text), page_num)

    full_text = "\n".join(text_blocks)
    logger.info(
        "Extracted electrical section text from %d pages (%d total chars)",
        len(page_numbers),
        len(full_text),
    )
    return full_text


def parse_numeric_value(raw_val: Any) -> float | int | None:
    """Clean and parse a raw value into a float, int, or None.

    Args:
        raw_val: Raw value string, number, or None.

    Returns:
        float | int | None: Parsed numeric value or None if unparseable/empty.
    """
    if raw_val is None:
        return None

    if isinstance(raw_val, (int, float)):
        return raw_val

    val_str = str(raw_val).strip()
    if not val_str or val_str in ("-", "—", "–", "N/A", "n/a", "TYP", "MIN", "MAX"):
        return None

    match = re.search(r"[-+]?\d*\.?\d+", val_str)
    if not match:
        return None

    num_str = match.group(0)
    try:
        val_float = float(num_str)
        return int(val_float) if val_float.is_integer() else val_float
    except ValueError:
        logger.debug("Failed to convert '%s' to number", num_str)
        return None


def normalize_unit(raw_unit: str | None) -> str | None:
    """Normalize unit string to a standardized SI unit representation.

    Args:
        raw_unit: Raw unit string (e.g., 'mV', 'volts', 'mA').

    Returns:
        str | None: Standardized unit string or None.
    """
    if not raw_unit:
        return None

    cleaned = str(raw_unit).strip().lower()
    normalized = UNIT_MAP.get(cleaned, raw_unit.strip())
    logger.debug("Normalized unit '%s' -> '%s'", raw_unit, normalized)
    return normalized


def normalize_electrical_metric(entry: dict[str, Any]) -> ElectricalMetric:
    """Sanitize and normalize a single electrical metric dictionary record.

    Args:
        entry: Dictionary containing raw metric fields (parameter, symbol, min_value, etc.).

    Returns:
        ElectricalMetric: Normalized metric record dictionary.
    """
    parameter = str(
        entry.get("parameter")
        or entry.get("param")
        or entry.get("name")
        or "Unknown Parameter"
    ).strip()
    symbol = entry.get("symbol")
    symbol_str = str(symbol).strip() if symbol else None

    test_conditions = entry.get("test_conditions") or entry.get("conditions")
    test_cond_str = str(test_conditions).strip() if test_conditions else None

    min_val = parse_numeric_value(entry.get("min_value") or entry.get("min"))
    typ_val = parse_numeric_value(entry.get("typ_value") or entry.get("typ"))
    max_val = parse_numeric_value(entry.get("max_value") or entry.get("max"))

    unit = normalize_unit(entry.get("unit"))

    notes = entry.get("notes") or entry.get("note")
    notes_str = str(notes).strip() if notes else None

    normalized: ElectricalMetric = {
        "parameter": parameter,
        "symbol": symbol_str,
        "test_conditions": test_cond_str,
        "min_value": min_val,
        "typ_value": typ_val,
        "max_value": max_val,
        "unit": unit,
        "notes": notes_str,
    }

    logger.debug("Normalized metric: %s", parameter)
    return normalized


# Keywords that unambiguously identify page-footer or boilerplate rows.
_FOOTER_KEYWORDS: frozenset[str] = frozenset(
    [
        "folder",
        "links:",
        "copyright",
        "submit",
        "feedback",
        "incorporated",
        "instruments",
        "revised",
        "revision",
    ]
)


def _is_junk_row(row: list[str]) -> bool:
    """Return True when a token row should be discarded before column-mapping.

    Filters patterns that produce invalid range errors or nonsensical metrics:

    1. **Condition assignment rows** – second token is ``=``.
       E.g. ``['VCC', '=', '5V', 'to', '30V,']``.

    2. **Footer / boilerplate rows** – tokens overlap footer keyword set.
       E.g. ``['Product', 'Folder', 'Links:', 'LM393B', …]``.

    3. **Part-number list rows** – first token ends with a comma, indicating a
       comma-separated product list rather than a table parameter.
       E.g. ``['LM224,', 'LM224K,', 'and', 'LM124...', '11']``.

    4. **TOC / dotted-leader rows** – any token contains four or more
       consecutive dots, which is a strong indicator of a table-of-contents
       entry or separator line rather than an electrical table row.
       E.g. ``['5.1', 'Absolute', 'Maximum', 'Ratings........', '4']``.

    5. **Narrative prose: Low measurement-like token ratio** - if a row has
       6 or more tokens and less than 25% of the tokens are "measurement-like"
       (containing digits, units, or placeholders), skip it.

    6. **Narrative prose: Sentence endings** - if a row has 5 or more tokens
       and ends with a period on the last word (and is not a standard unit or
       abbreviation), skip it.

    Args:
        row: A list of whitespace-split string tokens representing one text line.

    Returns:
        bool: True if the row should be skipped.
    """
    if len(row) >= 2 and str(row[1]).strip() == "=":
        logger.debug("Skipping condition assignment row: %s", row)
        return True

    lower_tokens = {t.lower() for t in row}
    if lower_tokens & _FOOTER_KEYWORDS:
        logger.debug("Skipping footer/boilerplate row: %s", row)
        return True

    # Part-number list: first token ends with a comma (e.g. 'LM224,')
    if str(row[0]).strip().endswith(","):
        logger.debug("Skipping part-number list row: %s", row)
        return True

    # TOC dotted-leader rows: any token contains 4+ consecutive dots
    if any("...." in t for t in row):
        logger.debug("Skipping TOC dotted-leader row: %s", row)
        return True

    # 5. Ratio of measurement-like tokens
    if len(row) >= 6:
        num_measurement_like = 0
        for token in row:
            token_clean = token.strip()
            # Contains a digit (e.g. '85°C', '30')
            if any(c.isdigit() for c in token_clean):
                num_measurement_like += 1
                continue
            # Known unit or placeholder or common symbols
            token_lower = token_clean.lower().rstrip(".,;:()")
            if token_lower in UNIT_MAP or token_lower in (
                "v", "mv", "a", "ma", "ua", "na", "pa", "c", "hz", "khz", "mhz", "db", "ohm", "kohm", "mohm",
                "n/a", "-", "—", "–", "typ", "min", "max", "typ.", "min.", "max."
            ):
                num_measurement_like += 1

        ratio = num_measurement_like / len(row)
        if ratio < 0.25:
            logger.debug("Skipping narrative/prose row (ratio=%.2f): %s", ratio, row)
            return True

    # 6. Sentence ending check
    if len(row) >= 5:
        last_token = str(row[-1]).strip()
        if last_token.endswith(".") and not last_token[:-1].replace(".", "", 1).isdigit():
            # Check if last token is not a known unit abbreviation with period
            if last_token.lower() not in ("typ.", "min.", "max.", "v.", "a.", "c.", "db."):
                logger.debug("Skipping prose row ending with period: %s", row)
                return True

    return False


def parse_electrical_table_rows(
    table_rows: list[list[str]],
) -> list[ElectricalMetric]:
    """Parse tabular row data into structured normalized metric records.

    Expects row formats such as:
    [Parameter, Symbol, Test Conditions, Min, Typ, Max, Unit] or similar 4-7 column layouts.

    Rows that match condition-assignment patterns (``token = …``) or
    page-footer boilerplate are silently skipped.

    Args:
        table_rows: List of string rows extracted from an electrical table.

    Returns:
        list[ElectricalMetric]: List of parsed and normalized metric records.
    """
    metrics: list[ElectricalMetric] = []

    for row in table_rows:
        if not row or len(row) < 2:
            continue

        # Guard 1: discard condition assignments and footer boilerplate
        if _is_junk_row(row):
            continue

        first_col = str(row[0]).strip().lower()
        if first_col in (
            "parameter",
            "description",
            "symbol",
            "test conditions",
            "name",
        ):
            logger.debug("Skipping table header row: %s", row)
            continue

        if len(row) >= 7:
            raw_entry = {
                "parameter": row[0],
                "symbol": row[1],
                "test_conditions": row[2],
                "min_value": row[3],
                "typ_value": row[4],
                "max_value": row[5],
                "unit": row[6],
            }
        elif len(row) == 6:
            raw_entry = {
                "parameter": row[0],
                "symbol": row[1],
                "min_value": row[2],
                "typ_value": row[3],
                "max_value": row[4],
                "unit": row[5],
            }
        elif len(row) == 5:
            raw_entry = {
                "parameter": row[0],
                "min_value": row[1],
                "typ_value": row[2],
                "max_value": row[3],
                "unit": row[4],
            }
        elif len(row) == 4:
            raw_entry = {
                "parameter": row[0],
                "typ_value": row[1],
                "max_value": row[2],
                "unit": row[3],
            }
        else:
            raw_entry = {
                "parameter": row[0],
                "typ_value": row[1],
            }

        normalized = normalize_electrical_metric(raw_entry)
        metrics.append(normalized)

    logger.info("Parsed %d metrics from %d table rows", len(metrics), len(table_rows))
    return metrics


def process_electrical_characteristics(
    raw_entries: list[dict[str, Any]] | list[list[str]],
) -> ElectricalCharacteristicsResult:
    """Process raw metric dictionaries or table rows into a structured result.

    Args:
        raw_entries: List of raw metric dictionaries or raw string table rows.

    Returns:
        ElectricalCharacteristicsResult: Dictionary containing structured metric records.
    """
    normalized_metrics: list[ElectricalMetric] = []

    if not raw_entries:
        logger.warning("Empty raw_entries passed to process_electrical_characteristics")
        return {
            "section": "Electrical Characteristics",
            "total_metrics": 0,
            "metrics": [],
        }

    first_item = raw_entries[0]
    if isinstance(first_item, list):
        table_rows = [item for item in raw_entries if isinstance(item, list)]
        normalized_metrics = parse_electrical_table_rows(table_rows)
    else:
        for item in raw_entries:
            if isinstance(item, dict):
                normalized = normalize_electrical_metric(item)
                normalized_metrics.append(normalized)

    result: ElectricalCharacteristicsResult = {
        "section": "Electrical Characteristics",
        "total_metrics": len(normalized_metrics),
        "metrics": normalized_metrics,
    }

    logger.info(
        "Processed electrical characteristics: %d total normalized metrics",
        len(normalized_metrics),
    )
    return result
