import pytest
import fitz
from pathlib import Path
from unittest.mock import MagicMock

from src.extraction.pdf import load_pdf
from src.extraction.parser import (
    DEFAULT_SECTION_KEYWORDS,
    find_sections_from_toc,
    find_sections_from_text,
    locate_datasheet_sections,
    get_section_pages,
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
    return doc


def test_find_sections_from_toc_success(valid_pdf):
    """Test find_sections_from_toc successfully identifies sections from a real TOC."""
    toc = valid_pdf.get_toc()
    sections = find_sections_from_toc(toc)
    
    assert isinstance(sections, dict)
    # Depending on the exact datasheet, some sections should be found.
    # LM358 TOC has 'Pin Configuration', 'Electrical Characteristics', etc.
    assert "pin_configuration" in sections
    assert isinstance(sections["pin_configuration"], list)
    assert len(sections["pin_configuration"]) > 0


def test_find_sections_from_toc_empty():
    """Test find_sections_from_toc with an empty TOC returns empty lists for all categories."""
    sections = find_sections_from_toc([])
    assert isinstance(sections, dict)
    assert len(sections) == 0  # Function filters out empty keys


def test_find_sections_from_toc_malformed():
    """Test find_sections_from_toc gracefully ignores malformed TOC entries."""
    malformed_toc = [
        [1, "Valid Entry", 10],
        [1, "Too Short"],
        [],
    ]
    sections = find_sections_from_toc(malformed_toc, section_keywords={"test": ["Valid"]})
    assert "test" in sections
    assert sections["test"] == [10]


def test_find_sections_from_text_success(valid_pdf):
    """Test find_sections_from_text successfully identifies sections by scanning page text."""
    sections = find_sections_from_text(valid_pdf)
    assert isinstance(sections, dict)
    assert "pin_configuration" in sections
    assert isinstance(sections["pin_configuration"], list)
    assert len(sections["pin_configuration"]) > 0


def test_find_sections_from_text_invalid_type():
    """Test find_sections_from_text with invalid input type."""
    with pytest.raises(TypeError, match="Expected a valid fitz.Document"):
        find_sections_from_text("Not a document")  # type: ignore


def test_find_sections_from_text_failure(mock_document):
    """Test find_sections_from_text handles underlying text extraction errors."""
    mock_document.__iter__.side_effect = Exception("Page text error")
    with pytest.raises(RuntimeError, match="Failed searching section pages"):
        find_sections_from_text(mock_document)


def test_locate_datasheet_sections_success(valid_pdf):
    """Test locate_datasheet_sections combines TOC and text search effectively."""
    sections = locate_datasheet_sections(valid_pdf)
    assert isinstance(sections, dict)
    # Since it combines both, it should find pin_configuration and others
    assert "pin_configuration" in sections
    assert len(sections["pin_configuration"]) > 0


def test_locate_datasheet_sections_invalid_type():
    """Test locate_datasheet_sections with invalid input type."""
    with pytest.raises(TypeError, match="Expected a valid fitz.Document"):
        locate_datasheet_sections(None)  # type: ignore


def test_locate_datasheet_sections_with_custom_keywords(valid_pdf):
    """Test locate_datasheet_sections uses custom keywords if provided."""
    custom_keywords = {"custom_section": ["LM358"]}
    sections = locate_datasheet_sections(valid_pdf, section_keywords=custom_keywords)
    assert "custom_section" in sections
    assert len(sections["custom_section"]) > 0


def test_get_section_pages_success():
    """Test get_section_pages successfully retrieves existing keys."""
    mock_map = {"pin_configuration": [1, 2, 3]}
    pages = get_section_pages(mock_map, "pin_configuration")
    assert pages == [1, 2, 3]


def test_get_section_pages_missing():
    """Test get_section_pages returns empty list for missing keys."""
    mock_map = {"pin_configuration": [1, 2, 3]}
    pages = get_section_pages(mock_map, "non_existent")
    assert pages == []
    assert isinstance(pages, list)
