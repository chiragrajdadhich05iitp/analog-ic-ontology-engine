"""Validation layer for Knowledge Graph extracted component data.

Responsibilities:
- Validate Component metadata (name, file_name, page counts)
- Validate Pin configurations (duplicates, invalid numbers, missing names)
- Validate Electrical Metrics (missing parameters, units, invalid numeric values/ranges)
- Validate References (page number positivity, source document presence)
- Check Graph Readiness (pin count, metric count)
- Generate structured ValidationReport objects containing errors, warnings, and statistics
"""

from dataclasses import dataclass, field
import logging
import math
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ValidationReport:
    """Structured validation report for component extraction data.

    Attributes:
        valid: True if no validation errors were found; False otherwise.
        errors: List of error messages indicating invalid data.
        warnings: List of warning messages indicating non-critical data quality issues.
        statistics: Dictionary containing component data metrics and execution stats.
    """

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    statistics: dict[str, Any] = field(default_factory=dict)


def validate_component_data(
    component_data: dict[str, Any], check_file_exists: bool = False
) -> ValidationReport:
    """Validate a normalized component data dictionary produced by the extraction pipeline.

    Args:
        component_data: Input dictionary containing 'metadata', 'pin_configuration',
            and 'electrical_characteristics'.
        check_file_exists: If True, verifies that the source PDF file exists on disk.

    Returns:
        ValidationReport: Detailed report containing validity flag, errors, warnings, and stats.

    Raises:
        TypeError: If component_data is not a dictionary.
    """
    if not isinstance(component_data, dict):
        logger.error(
            "Invalid input to validate_component_data: expected dict, got %s",
            type(component_data),
        )
        raise TypeError("Expected component_data to be a dictionary.")

    errors: list[str] = []
    warnings: list[str] = []

    # --- 1. COMPONENT VALIDATION ---
    metadata = component_data.get("metadata", {})
    if not isinstance(metadata, dict):
        errors.append("Metadata section must be a dictionary.")
        metadata = {}

    file_name = metadata.get("file_name")
    if not file_name or not str(file_name).strip():
        errors.append("Component file_name is missing or empty.")
    else:
        file_name = str(file_name).strip()

    comp_name = metadata.get("component_name") or Path(file_name or "").stem
    if not comp_name or not str(comp_name).strip():
        errors.append("Component name is missing or empty.")

    # --- 2. PINS VALIDATION ---
    pin_config = component_data.get("pin_configuration", {})
    if not isinstance(pin_config, dict):
        errors.append("Pin configuration section must be a dictionary.")
        pin_config = {}

    pins = pin_config.get("pins", [])
    if not isinstance(pins, list):
        errors.append("Pin configuration 'pins' must be a list.")
        pins = []

    seen_pin_numbers: set[str] = set()
    seen_pin_names: set[str] = set()

    for idx, pin in enumerate(pins, start=1):
        if not isinstance(pin, dict):
            errors.append(f"Pin entry at index {idx} is not a dictionary.")
            continue

        raw_pin_num = pin.get("pin_number")
        pin_num_str = str(raw_pin_num).strip() if raw_pin_num is not None else ""

        if not pin_num_str:
            errors.append(f"Pin entry at index {idx} has an empty pin number.")
        elif not pin_num_str.isalnum():
            warnings.append(
                f"Pin entry '{pin_num_str}' at index {idx} contains non-alphanumeric characters."
            )

        if pin_num_str:
            if pin_num_str in seen_pin_numbers:
                errors.append(f"Duplicate pin number found: '{pin_num_str}'.")
            else:
                seen_pin_numbers.add(pin_num_str)

        pin_name = pin.get("name")
        pin_name_str = str(pin_name).strip() if pin_name is not None else ""
        if not pin_name_str:
            errors.append(f"Pin '{pin_num_str or idx}' is missing a pin name.")
        else:
            if pin_name_str in seen_pin_names:
                warnings.append(f"Duplicate pin name found: '{pin_name_str}'.")
            else:
                seen_pin_names.add(pin_name_str)

    # --- 3. ELECTRICAL METRICS VALIDATION ---
    elec_config = component_data.get("electrical_characteristics", {})
    if not isinstance(elec_config, dict):
        errors.append("Electrical characteristics section must be a dictionary.")
        elec_config = {}

    metrics = elec_config.get("metrics", [])
    if not isinstance(metrics, list):
        errors.append("Electrical characteristics 'metrics' must be a list.")
        metrics = []

    seen_metric_signatures: set[tuple[str, str, str]] = set()

    for idx, metric in enumerate(metrics, start=1):
        if not isinstance(metric, dict):
            errors.append(f"Metric entry at index {idx} is not a dictionary.")
            continue

        param = metric.get("parameter")
        param_str = str(param).strip() if param is not None else ""
        if not param_str:
            errors.append(
                f"Electrical metric entry at index {idx} is missing a parameter name."
            )

        unit = metric.get("unit")
        unit_str = str(unit).strip() if unit is not None else ""
        if not unit_str:
            warnings.append(
                f"Metric '{param_str or idx}' is missing a unit of measurement."
            )

        cond = metric.get("test_conditions")
        cond_str = str(cond).strip() if cond is not None else ""
        if not cond_str:
            warnings.append(f"Metric '{param_str or idx}' has empty test conditions.")

        min_val = metric.get("min_value")
        typ_val = metric.get("typ_value")
        max_val = metric.get("max_value")

        def _check_numeric(val: Any, val_name: str) -> float | int | None:
            if val is None or val == "":
                return None
            if isinstance(val, (int, float)):
                if math.isnan(val) or math.isinf(val):
                    errors.append(
                        f"Metric '{param_str or idx}' has invalid {val_name}: {val}."
                    )
                    return None
                return val
            try:
                f = float(val)
                if math.isnan(f) or math.isinf(f):
                    errors.append(
                        f"Metric '{param_str or idx}' has invalid {val_name}: {val}."
                    )
                    return None
                return f
            except (ValueError, TypeError):
                errors.append(
                    f"Metric '{param_str or idx}' has non-numeric {val_name}: '{val}'."
                )
                return None

        parsed_min = _check_numeric(min_val, "min_value")
        _check_numeric(typ_val, "typ_value")
        parsed_max = _check_numeric(max_val, "max_value")

        if parsed_min is not None and parsed_max is not None:
            if parsed_min > parsed_max:
                errors.append(
                    f"Metric '{param_str or idx}' has invalid range: min_value ({parsed_min}) > max_value ({parsed_max})."
                )

        symbol = str(metric.get("symbol") or "").strip()
        sig = (param_str.lower(), symbol.lower(), cond_str.lower())
        if sig in seen_metric_signatures:
            warnings.append(f"Duplicate electrical metric entry found: '{param_str}'.")
        else:
            seen_metric_signatures.add(sig)

    # --- 4. REFERENCES VALIDATION ---
    if check_file_exists and file_name:
        file_path = Path(file_name)
        if not file_path.exists():
            errors.append(f"Source document file does not exist: '{file_name}'.")

    total_pages = metadata.get("total_pages")
    if total_pages is not None:
        if not isinstance(total_pages, int) or total_pages <= 0:
            errors.append(f"Invalid total_pages count: {total_pages}. Must be > 0.")

    sections_found = metadata.get("sections_found", {})
    if isinstance(sections_found, dict):
        for sec_name, pages in sections_found.items():
            if isinstance(pages, list):
                for p in pages:
                    if not isinstance(p, int) or p <= 0:
                        errors.append(
                            f"Section '{sec_name}' contains non-positive page number: {p}."
                        )

    pin_pages = pin_config.get("pages", [])
    if isinstance(pin_pages, list):
        for p in pin_pages:
            if not isinstance(p, int) or p <= 0:
                errors.append(
                    f"Pin configuration contains non-positive page number: {p}."
                )

    # --- 5. GRAPH READINESS ---
    if len(pins) == 0:
        errors.append(
            "Graph readiness failure: Component contains 0 pins (at least 1 required)."
        )

    if len(metrics) == 0:
        errors.append(
            "Graph readiness failure: Component contains 0 electrical metrics (at least 1 required)."
        )

    is_valid = len(errors) == 0

    statistics: dict[str, Any] = {
        "component_name": comp_name,
        "file_name": file_name,
        "total_pages": total_pages,
        "total_pins": len(pins),
        "total_metrics": len(metrics),
        "total_errors": len(errors),
        "total_warnings": len(warnings),
        "sections_found_count": len(sections_found)
        if isinstance(sections_found, dict)
        else 0,
    }

    logger.info(
        "Validation complete for '%s': valid=%s, %d errors, %d warnings",
        comp_name,
        is_valid,
        len(errors),
        len(warnings),
    )

    return ValidationReport(
        valid=is_valid,
        errors=errors,
        warnings=warnings,
        statistics=statistics,
    )


def validate(
    component_data: dict[str, Any], check_file_exists: bool = False
) -> ValidationReport:
    """Alias for validate_component_data."""
    return validate_component_data(component_data, check_file_exists=check_file_exists)
