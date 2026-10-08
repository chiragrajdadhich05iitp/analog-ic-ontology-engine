import pytest
import fitz
from pathlib import Path
from unittest.mock import MagicMock

from src.extraction.pdf import load_pdf
from src.extraction.electrical import (
    extract_electrical_text,
    parse_numeric_value,
    normalize_unit,
    normalize_electrical_metric,
    parse_electrical_table_rows,
    process_electrical_characteristics,
)

FIXTURE_PDF = Path("data/datasheets/lm358.pdf")


@pytest.fixture
def valid_pdf():
    """Fixture providing a valid PyMuPDF Document using the real LM358 datasheet."""
    doc = load_pdf(FIXTURE_PDF)
    yield doc
    doc.close()


@pytest.fixture
def mock_document():
    """Fixture providing a mocked fitz.Document for error simulation."""
    doc = MagicMock()
    doc.__class__ = fitz.Document
    doc.__len__.return_value = 5
    return doc


def test_extract_electrical_text_success(valid_pdf):
    """Test successful text extraction from specified electrical pages."""
    # Based on earlier LM358 parser output, electrical chars are on pages like 6, 7, 8
    # We just need to extract from one page to verify it works
    text = extract_electrical_text(valid_pdf, [6, 7])
    assert isinstance(text, str)
    assert len(text) > 0
    # Electrical Characteristics table headers typically have words like "Parameter", "Test Conditions"
    assert "Parameter" in text or "PARAMETER" in text or "Test Conditions" in text or "TEST CONDITIONS" in text or "LM" in text


def test_extract_electrical_text_invalid_type():
    """Test extract_electrical_text with invalid input type."""
    with pytest.raises(TypeError, match="Expected a valid fitz.Document"):
        extract_electrical_text(None, [1])  # type: ignore


def test_extract_electrical_text_out_of_bounds(valid_pdf):
    """Test extract_electrical_text with invalid page numbers."""
    with pytest.raises(IndexError, match="out of bounds"):
        extract_electrical_text(valid_pdf, [9999])


def test_parse_numeric_value():
    """Test parse_numeric_value handles various number formats correctly."""
    assert parse_numeric_value(10) == 10
    assert parse_numeric_value(10.5) == 10.5
    assert parse_numeric_value(" 25.0 ") == 25
    assert parse_numeric_value("-5.5") == -5.5
    assert parse_numeric_value("+3.3") == 3.3
    
    # Non-numeric or empty
    assert parse_numeric_value(None) is None
    assert parse_numeric_value("") is None
    assert parse_numeric_value("-") is None
    assert parse_numeric_value("N/A") is None
    assert parse_numeric_value("TYP") is None
    assert parse_numeric_value("Some string without numbers") is None

    # Mixed strings
    assert parse_numeric_value("100 mV") == 100
    assert parse_numeric_value("approx 42") == 42


def test_normalize_unit():
    """Test normalize_unit maps common variations to standard SI units."""
    assert normalize_unit(None) is None
    assert normalize_unit("v") == "V"
    assert normalize_unit("volts") == "V"
    assert normalize_unit("mA") == "mA"
    assert normalize_unit("milliamps") == "mA"
    assert normalize_unit("deg c") == "°C"
    assert normalize_unit("Hz") == "Hz"
    # Unmapped units should return stripped original
    assert normalize_unit("unknown_unit") == "unknown_unit"


def test_normalize_electrical_metric():
    """Test normalize_electrical_metric formats raw dicts into ElectricalMetric."""
    raw = {
        "parameter": "Input Offset Voltage",
        "symbol": "Vos",
        "min": "2",
        "typ": "3.5",
        "max": "N/A",
        "unit": "mv",
        "test_conditions": "TA = 25C",
    }
    norm = normalize_electrical_metric(raw)
    
    assert norm["parameter"] == "Input Offset Voltage"
    assert norm["symbol"] == "Vos"
    assert norm["min_value"] == 2
    assert norm["typ_value"] == 3.5
    assert norm["max_value"] is None
    assert norm["unit"] == "mV"
    assert norm["test_conditions"] == "TA = 25C"


def test_parse_electrical_table_rows():
    """Test parse_electrical_table_rows accurately maps column counts."""
    # Test skipping headers
    headers = [["Parameter", "Symbol", "Min", "Typ", "Max", "Unit"]]
    assert len(parse_electrical_table_rows(headers)) == 0

    # Test 7 cols
    row_7 = [["Offset Voltage", "Vos", "TA=25", "1", "2", "3", "mV"]]
    res_7 = parse_electrical_table_rows(row_7)
    assert len(res_7) == 1
    assert res_7[0]["parameter"] == "Offset Voltage"
    assert res_7[0]["test_conditions"] == "TA=25"
    assert res_7[0]["unit"] == "mV"

    # Test 6 cols
    row_6 = [["Offset Voltage", "Vos", "1", "2", "3", "mV"]]
    res_6 = parse_electrical_table_rows(row_6)
    assert res_6[0]["symbol"] == "Vos"
    assert res_6[0]["test_conditions"] is None

    # Test 5 cols
    row_5 = [["Offset Voltage", "1", "2", "3", "mV"]]
    res_5 = parse_electrical_table_rows(row_5)
    assert res_5[0]["symbol"] is None

    # Test 4 cols
    row_4 = [["Quiescent Current", "1.5", "2", "mA"]]
    res_4 = parse_electrical_table_rows(row_4)
    assert res_4[0]["typ_value"] == 1.5
    assert res_4[0]["max_value"] == 2

    # Test fewer cols
    row_2 = [["Some Param", "50"]]
    res_2 = parse_electrical_table_rows(row_2)
    assert res_2[0]["typ_value"] == 50
    
    # Test empty or too short row
    assert len(parse_electrical_table_rows([[]])) == 0
    assert len(parse_electrical_table_rows([["Param Only"]])) == 0


def test_process_electrical_characteristics_empty():
    """Test process_electrical_characteristics handles empty inputs."""
    res = process_electrical_characteristics([])
    assert res["total_metrics"] == 0
    assert res["metrics"] == []


def test_process_electrical_characteristics_with_rows():
    """Test process_electrical_characteristics delegates row parsing."""
    rows = [
        ["Parameter", "Min", "Max", "Unit"],  # header
        ["Offset", "1", "5", "mV"],
    ]
    res = process_electrical_characteristics(rows)
    assert res["total_metrics"] == 1
    assert res["metrics"][0]["parameter"] == "Offset"
    assert res["metrics"][0]["unit"] == "mV"


def test_process_electrical_characteristics_with_dicts():
    """Test process_electrical_characteristics delegates dict normalization."""
    dicts = [
        {"parameter": "Offset", "min": "1", "unit": "mv"}
    ]
    res = process_electrical_characteristics(dicts)
    assert res["total_metrics"] == 1
    assert res["metrics"][0]["parameter"] == "Offset"
    assert res["metrics"][0]["min_value"] == 1
    assert res["metrics"][0]["unit"] == "mV"
