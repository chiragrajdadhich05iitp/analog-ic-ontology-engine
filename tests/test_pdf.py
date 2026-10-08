import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import fitz
import pytest
from PIL import Image

from src.extraction.pdf import (
    get_table_of_contents,
    load_pdf,
    find_sections,
    search_section_pages,
    render_page,
    render_page_to_image,
    render_all_pages,
    render_pdf_pages,
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


def test_load_pdf_success():
    """Test successful loading of an existing PDF."""
    doc = load_pdf(FIXTURE_PDF)
    assert isinstance(doc, fitz.Document)
    assert len(doc) > 0
    doc.close()


def test_load_pdf_missing_file():
    """Test load_pdf raises FileNotFoundError for non-existent path."""
    with pytest.raises(FileNotFoundError, match="not found"):
        load_pdf("data/fixtures/non_existent.pdf")


def test_load_pdf_not_a_file(tmp_path):
    """Test load_pdf raises ValueError if the path is a directory."""
    with pytest.raises(ValueError, match="not a file"):
        load_pdf(tmp_path)


@patch("fitz.open")
def test_load_pdf_open_failure(mock_fitz_open):
    """Test load_pdf raises ValueError if fitz.open fails (e.g., corrupt file)."""
    mock_fitz_open.side_effect = Exception("Corrupt PDF")
    # We patch fitz.open, but we still need a file that exists so the pre-checks pass.
    with pytest.raises(ValueError, match="Failed to open or parse"):
        load_pdf(FIXTURE_PDF)


def test_get_table_of_contents_success(valid_pdf):
    """Test extracting TOC from a valid document."""
    toc = get_table_of_contents(valid_pdf)
    assert isinstance(toc, list)


def test_get_table_of_contents_invalid_type():
    """Test get_table_of_contents with incorrect input type."""
    with pytest.raises(TypeError, match="Expected a valid fitz.Document"):
        get_table_of_contents("Not a document")  # type: ignore


def test_get_table_of_contents_failure(mock_document):
    """Test get_table_of_contents handles underlying library errors."""
    mock_document.get_toc.side_effect = Exception("TOC extraction failed")
    with pytest.raises(RuntimeError, match="Failed to extract table of contents"):
        get_table_of_contents(mock_document)


def test_find_sections_success(valid_pdf):
    """Test finding keyword sections in a valid PDF."""
    results = find_sections(valid_pdf, keywords=["Pin Configuration"])
    assert isinstance(results, dict)
    assert "Pin Configuration" in results
    assert isinstance(results["Pin Configuration"], list)


def test_find_sections_invalid_type():
    """Test find_sections with incorrect input type."""
    with pytest.raises(TypeError, match="Expected a valid fitz.Document"):
        find_sections("Not a document")  # type: ignore


def test_find_sections_failure(mock_document):
    """Test find_sections handles extraction failures."""
    # Mocking iteration over the document pages to raise an error
    mock_document.__iter__.side_effect = Exception("Page text error")
    with pytest.raises(RuntimeError, match="Failed to search section pages"):
        find_sections(mock_document)


def test_search_section_pages_success(valid_pdf):
    """Test searching pages by keywords successfully."""
    results = search_section_pages(valid_pdf, keywords=["Electrical Characteristics"])
    assert isinstance(results, dict)


def test_search_section_pages_invalid_type():
    """Test search_section_pages with incorrect input type."""
    with pytest.raises(TypeError, match="Expected a valid fitz.Document"):
        search_section_pages(None)  # type: ignore


def test_search_section_pages_failure(mock_document):
    """Test search_section_pages handles iteration/extraction errors."""
    mock_document.__iter__.side_effect = Exception("Extraction failed")
    with pytest.raises(RuntimeError, match="Failed searching section pages"):
        search_section_pages(mock_document)


def test_render_page_success(valid_pdf):
    """Test successfully rendering a valid page to a PIL Image."""
    img = render_page(valid_pdf, 1)
    assert isinstance(img, Image.Image)


def test_render_page_invalid_type():
    """Test render_page with invalid input type."""
    with pytest.raises(TypeError, match="Expected a valid fitz.Document"):
        render_page("doc", 1)  # type: ignore


def test_render_page_out_of_bounds(valid_pdf):
    """Test render_page raises IndexError for out of bounds page numbers."""
    with pytest.raises(IndexError, match="out of valid range"):
        render_page(valid_pdf, 9999)


def test_render_page_failure(mock_document):
    """Test render_page handles loading/rendering errors."""
    mock_document.load_page.side_effect = Exception("Load error")
    with pytest.raises(RuntimeError, match="Failed to render page"):
        render_page(mock_document, 1)


def test_render_page_to_image_success(valid_pdf):
    """Test successfully rendering a fitz.Page directly to PIL Image."""
    page = valid_pdf.load_page(0)
    img = render_page_to_image(page)
    assert isinstance(img, Image.Image)


def test_render_page_to_image_invalid_type():
    """Test render_page_to_image with invalid input."""
    with pytest.raises(TypeError, match="Expected a valid fitz.Page"):
        render_page_to_image("Not a page")  # type: ignore


def test_render_page_to_image_failure():
    """Test render_page_to_image handles pixmap errors."""
    mock_page = MagicMock(spec=fitz.Page)
    mock_page.get_pixmap.side_effect = Exception("Pixmap error")
    with pytest.raises(RuntimeError, match="Failed to render page to image"):
        render_page_to_image(mock_page)


def test_render_all_pages_success(valid_pdf, tmp_path):
    """Test rendering all pages to disk as images."""
    out_dir = tmp_path / "pages_out"
    render_all_pages(valid_pdf, output_dir=out_dir)
    assert out_dir.exists()
    assert list(out_dir.glob("*.png"))  # Should have generated PNG files


def test_render_all_pages_invalid_type():
    """Test render_all_pages with invalid input type."""
    with pytest.raises(TypeError, match="Expected a valid fitz.Document"):
        render_all_pages(None)  # type: ignore


def test_render_all_pages_dir_failure(valid_pdf):
    """Test render_all_pages fails gracefully if directory creation fails."""
    # Pass a file instead of a directory path to trigger a mkdir error
    with pytest.raises(RuntimeError, match="Cannot create output directory"):
        render_all_pages(valid_pdf, output_dir=FIXTURE_PDF)


def test_render_all_pages_render_failure(mock_document, tmp_path):
    """Test render_all_pages handles page rendering errors."""
    mock_page = MagicMock()
    mock_page.get_pixmap.side_effect = Exception("Pixmap error")
    mock_document.__iter__.return_value = [mock_page]
    
    with pytest.raises(RuntimeError, match="Failed saving page"):
        render_all_pages(mock_document, output_dir=tmp_path / "pages_out")


def test_render_pdf_pages_success(valid_pdf):
    """Test rendering all pages to a list of images."""
    images = render_pdf_pages(valid_pdf)
    assert isinstance(images, list)
    if images:
        assert isinstance(images[0], Image.Image)


def test_render_pdf_pages_with_output(valid_pdf, tmp_path):
    """Test rendering all pages to images and saving to disk."""
    out_dir = tmp_path / "pdf_pages_out"
    images = render_pdf_pages(valid_pdf, output_dir=out_dir)
    assert isinstance(images, list)
    assert out_dir.exists()


def test_render_pdf_pages_invalid_type():
    """Test render_pdf_pages with invalid input type."""
    with pytest.raises(TypeError, match="Expected a valid fitz.Document"):
        render_pdf_pages(None)  # type: ignore


def test_render_pdf_pages_dir_failure(valid_pdf):
    """Test render_pdf_pages handles directory creation errors."""
    with pytest.raises(RuntimeError, match="Cannot create output directory"):
        render_pdf_pages(valid_pdf, output_dir=FIXTURE_PDF)
