"""Tests for src/validation/validator.py."""

from typing import Any
import pytest
from src.validation.validator import (
    ValidationReport,
    validate,
    validate_component_data,
)


@pytest.fixture
def valid_component_fixture() -> dict[str, Any]:
    """Fixture providing a valid synthetic component dictionary."""
    return {
        "metadata": {
            "file_name": "LM358.pdf",
            "component_name": "LM358",
            "total_pages": 4,
            "sections_found": {
                "pin_configuration": [1, 2],
                "electrical_characteristics": [3, 4],
            },
        },
        "pin_configuration": {
            "pages": [1, 2],
            "total_pins": 2,
            "pins": [
                {
                    "pin_number": "1",
                    "name": "OUT1",
                    "type": "Output",
                    "description": "Output 1",
                },
                {
                    "pin_number": "2",
                    "name": "IN1-",
                    "type": "Input",
                    "description": "Inverting Input 1",
                },
            ],
        },
        "electrical_characteristics": {
            "section": "Electrical Characteristics",
            "total_metrics": 2,
            "metrics": [
                {
                    "parameter": "Supply Voltage",
                    "symbol": "VCC",
                    "test_conditions": "TA = 25°C",
                    "min_value": 3.0,
                    "typ_value": 5.0,
                    "max_value": 32.0,
                    "unit": "V",
                    "notes": None,
                },
                {
                    "parameter": "Input Bias Current",
                    "symbol": "IB",
                    "test_conditions": "TA = 25°C",
                    "min_value": None,
                    "typ_value": 20.0,
                    "max_value": 50.0,
                    "unit": "nA",
                    "notes": None,
                },
            ],
        },
    }


def test_valid_component(valid_component_fixture: dict[str, Any]) -> None:
    """Test validation of a valid component dictionary."""
    report = validate_component_data(valid_component_fixture)

    assert isinstance(report, ValidationReport)
    assert report.valid is True
    assert len(report.errors) == 0
    assert report.statistics["component_name"] == "LM358"
    assert report.statistics["total_pins"] == 2
    assert report.statistics["total_metrics"] == 2


def test_duplicate_pins(valid_component_fixture: dict[str, Any]) -> None:
    """Test detection of duplicate pin numbers and duplicate pin names."""
    data = valid_component_fixture
    data["pin_configuration"]["pins"].append({
        "pin_number": "1",
        "name": "OUT1_DUP",
        "type": "Output",
    })
    data["pin_configuration"]["pins"].append({
        "pin_number": "3",
        "name": "OUT1",
        "type": "Output",
    })

    report = validate(data)
    assert report.valid is False
    assert any("Duplicate pin number" in err for err in report.errors)
    assert any("Duplicate pin name" in warn for warn in report.warnings)


def test_missing_component_name(valid_component_fixture: dict[str, Any]) -> None:
    """Test detection of missing or empty component file_name and name."""
    data = valid_component_fixture
    data["metadata"]["file_name"] = ""
    data["metadata"]["component_name"] = ""

    report = validate_component_data(data)
    assert report.valid is False
    assert any("file_name is missing" in err for err in report.errors)
    assert any("Component name is missing" in err for err in report.errors)


def test_invalid_metric_ranges(valid_component_fixture: dict[str, Any]) -> None:
    """Test detection of invalid metric range where min_value > max_value."""
    data = valid_component_fixture
    data["electrical_characteristics"]["metrics"][0]["min_value"] = 50.0
    data["electrical_characteristics"]["metrics"][0]["max_value"] = 10.0

    report = validate_component_data(data)
    assert report.valid is False
    assert any("invalid range" in err for err in report.errors)


def test_missing_units(valid_component_fixture: dict[str, Any]) -> None:
    """Test warning when electrical metric is missing a unit of measurement."""
    data = valid_component_fixture
    data["electrical_characteristics"]["metrics"][0]["unit"] = None

    report = validate_component_data(data)
    assert any("missing a unit" in warn for warn in report.warnings)


def test_duplicate_metrics(valid_component_fixture: dict[str, Any]) -> None:
    """Test warning for duplicate electrical metric entries."""
    data = valid_component_fixture
    metric = data["electrical_characteristics"]["metrics"][0]
    data["electrical_characteristics"]["metrics"].append(dict(metric))

    report = validate_component_data(data)
    assert any("Duplicate electrical metric" in warn for warn in report.warnings)


def test_empty_graph(valid_component_fixture: dict[str, Any]) -> None:
    """Test graph readiness errors when pins or metrics lists are empty."""
    data = valid_component_fixture
    data["pin_configuration"]["pins"] = []
    data["electrical_characteristics"]["metrics"] = []

    report = validate_component_data(data)
    assert report.valid is False
    assert any("contains 0 pins" in err for err in report.errors)
    assert any("contains 0 electrical metrics" in err for err in report.errors)


def test_malformed_references(valid_component_fixture: dict[str, Any]) -> None:
    """Test detection of non-positive page numbers in references and metadata."""
    data = valid_component_fixture
    data["metadata"]["total_pages"] = -1
    data["metadata"]["sections_found"]["pin_configuration"] = [0]
    data["pin_configuration"]["pages"] = [-2]

    report = validate_component_data(data)
    assert report.valid is False
    assert any("Invalid total_pages count" in err for err in report.errors)
    assert any("non-positive page number" in err for err in report.errors)


def test_invalid_input_type() -> None:
    """Test TypeError when passing non-dictionary input to validate_component_data."""
    with pytest.raises(TypeError):
        validate_component_data("not a dictionary")  # type: ignore


def test_check_file_exists_flag(valid_component_fixture: dict[str, Any]) -> None:
    """Test check_file_exists option when file does not exist on disk."""
    data = valid_component_fixture
    data["metadata"]["file_name"] = "non_existent_file_12345.pdf"

    report = validate_component_data(data, check_file_exists=True)
    assert report.valid is False
    assert any("file does not exist" in err for err in report.errors)


def test_non_dict_sections_and_invalid_types(valid_component_fixture: dict[str, Any]) -> None:
    """Test non-dict metadata/pin_config/elec_config and non-list pins/metrics."""
    data = valid_component_fixture
    data["metadata"] = "not_a_dict"
    data["pin_configuration"] = "not_a_dict"
    data["electrical_characteristics"] = "not_a_dict"

    report = validate_component_data(data)
    assert report.valid is False
    assert any("Metadata section must be a dictionary" in err for err in report.errors)
    assert any("Pin configuration section must be a dictionary" in err for err in report.errors)
    assert any("Electrical characteristics section must be a dictionary" in err for err in report.errors)


def test_invalid_pin_entries_and_metrics(valid_component_fixture: dict[str, Any]) -> None:
    """Test invalid entries in pins and metrics lists."""
    data = valid_component_fixture
    data["pin_configuration"]["pins"] = [
        "not_a_pin_dict",
        {"pin_number": "", "name": ""},
        {"pin_number": "1!", "name": "VCC"},
    ]
    data["electrical_characteristics"]["metrics"] = [
        "not_a_metric_dict",
        {
            "parameter": "",
            "unit": "V",
            "test_conditions": "",
            "min_value": "abc",
            "typ_value": float("nan"),
            "max_value": float("inf"),
        },
    ]

    report = validate_component_data(data)
    assert report.valid is False
    assert any("Pin entry at index 1 is not a dictionary" in err for err in report.errors)
    assert any("has an empty pin number" in err for err in report.errors)
    assert any("contains non-alphanumeric" in warn for warn in report.warnings)
    assert any("Metric entry at index 1 is not a dictionary" in err for err in report.errors)
    assert any("missing a parameter name" in err for err in report.errors)
    assert any("non-numeric min_value" in err for err in report.errors)
    assert any("invalid typ_value: nan" in err for err in report.errors)
    assert any("invalid max_value: inf" in err for err in report.errors)
