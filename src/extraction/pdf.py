"""PDF processing module for the Knowledge Graph Builder.

Responsibilities:
- Load and validate PDF documents
- Extract table of contents (TOC)
- Find pages containing specified sections or keywords
- Render individual or all PDF pages into high-resolution PIL Images
"""

import logging
from pathlib import Path
from typing import Any
import fitz
from PIL import Image

logger = logging.getLogger(__name__)

DEFAULT_KEYWORDS: list[str] = [
    "Pin Configuration",
    "Pin Functions",
    "Absolute Maximum Ratings",
    "Recommended Operating Conditions",
    "Electrical Characteristics",
    "Package Information",
]


def load_pdf(pdf_path: str | Path) -> fitz.Document:
    """Open a PDF document and return the PyMuPDF Document object.

    Args:
        pdf_path: Absolute or relative file path to the target PDF document.

    Returns:
        fitz.Document: Opened PyMuPDF Document instance.

    Raises:
        FileNotFoundError: If the specified pdf_path does not exist on disk.
        ValueError: If the file is not a valid PDF document or cannot be parsed.
    """
    path = Path(pdf_path)
    if not path.exists():
        logger.error("PDF file not found at path: %s", pdf_path)
        raise FileNotFoundError(f"PDF file not found at path: {pdf_path}")

    if not path.is_file():
        logger.error("Path is not a regular file: %s", pdf_path)
        raise ValueError(f"Path is not a file: {pdf_path}")

    try:
        doc = fitz.open(path)
        logger.info("Successfully loaded PDF '%s' (%d pages)", path.name, len(doc))
        return doc
    except Exception as err:
        logger.exception("Failed to open PDF document '%s': %s", pdf_path, err)
        raise ValueError(
            f"Failed to open or parse PDF document '{pdf_path}': {err}"
        ) from err


def get_table_of_contents(doc: fitz.Document) -> list[list[Any]]:
    """Return the PDF table of contents (TOC).

    Args:
        doc: Loaded PyMuPDF Document object.

    Returns:
        list[list[Any]]: List of TOC entries, where each entry is [level, title, page_number].

    Raises:
        TypeError: If doc is not a valid PyMuPDF Document instance.
        RuntimeError: If TOC extraction fails.
    """
    if not isinstance(doc, fitz.Document):
        logger.error("Invalid document instance passed to get_table_of_contents")
        raise TypeError("Expected a valid fitz.Document instance.")

    try:
        toc = doc.get_toc()
        logger.debug("Extracted %d table of contents entries from document", len(toc))
        return toc
    except Exception as err:
        logger.exception("Error extracting table of contents: %s", err)
        raise RuntimeError(f"Failed to extract table of contents: {err}") from err


def find_sections(
    doc: fitz.Document, keywords: list[str] | None = None
) -> dict[str, list[int]]:
    """Find 1-indexed page numbers containing the requested keywords.

    Args:
        doc: Loaded PyMuPDF Document object.
        keywords: List of section titles or keywords to search for. Defaults to DEFAULT_KEYWORDS.

    Returns:
        dict[str, list[int]]: Mapping of keyword string to a list of 1-indexed page numbers
            where the keyword was matched.

    Raises:
        TypeError: If doc is not a valid fitz.Document instance.
        RuntimeError: If page text extraction fails.
    """
    if not isinstance(doc, fitz.Document):
        logger.error("Invalid document instance passed to find_sections")
        raise TypeError("Expected a valid fitz.Document instance.")

    if keywords is None:
        keywords = DEFAULT_KEYWORDS

    results: dict[str, list[int]] = {keyword: [] for keyword in keywords}

    try:
        for page_number, page in enumerate(doc, start=1):
            text = page.get_text() or ""
            text_lower = text.lower()

            for keyword in keywords:
                if keyword.lower() in text_lower:
                    results[keyword].append(page_number)
                    logger.debug("Found keyword '%s' on page %d", keyword, page_number)

        logger.info("Completed section search across %d pages", len(doc))
        return results
    except Exception as err:
        logger.exception("Error during section page search: %s", err)
        raise RuntimeError(f"Failed to search section pages in PDF: {err}") from err


def search_section_pages(
    doc: fitz.Document, keywords: list[str] | None = None
) -> dict[int, list[str]]:
    """Search for pages in the document that contain specified section keywords.

    Args:
        doc: Loaded PyMuPDF Document.
        keywords: List of section keywords to search for. Defaults to DEFAULT_KEYWORDS.

    Returns:
        dict[int, list[str]]: Mapping from 1-indexed page number to list of matching
            keywords found on that page.

    Raises:
        TypeError: If doc is not a valid fitz.Document instance.
        RuntimeError: If page text search fails.
    """
    if not isinstance(doc, fitz.Document):
        logger.error("Invalid document instance passed to search_section_pages")
        raise TypeError("Expected a valid fitz.Document instance.")

    if keywords is None:
        keywords = DEFAULT_KEYWORDS

    results: dict[int, list[str]] = {}
    try:
        for page_index, page in enumerate(doc):
            page_number = page_index + 1
            text = page.get_text() or ""
            matched = [kw for kw in keywords if kw.lower() in text.lower()]
            if matched:
                results[page_number] = matched

        return results
    except Exception as err:
        logger.exception("Error searching section pages: %s", err)
        raise RuntimeError(f"Failed searching section pages: {err}") from err


def render_page(
    doc: fitz.Document, page_number: int, zoom: float = 2.0
) -> Image.Image:
    """Render a single 1-indexed page of a PDF document as a PIL Image.

    Args:
        doc: Loaded PyMuPDF Document object.
        page_number: 1-indexed page number to render.
        zoom: Resolution scaling multiplier (default 2.0).

    Returns:
        PIL.Image.Image: Rendered page as an RGB PIL Image object.

    Raises:
        TypeError: If doc is not a valid fitz.Document.
        IndexError: If page_number is out of bounds (1 to len(doc)).
        RuntimeError: If page rendering fails.
    """
    if not isinstance(doc, fitz.Document):
        logger.error("Invalid document instance passed to render_page")
        raise TypeError("Expected a valid fitz.Document instance.")

    if page_number < 1 or page_number > len(doc):
        logger.error(
            "Requested page_number %d out of bounds (1..%d)", page_number, len(doc)
        )
        raise IndexError(
            f"Page number {page_number} out of valid range (1 to {len(doc)})."
        )

    try:
        page = doc.load_page(page_number - 1)
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix)

        mode = "RGBA" if pix.alpha else "RGB"
        img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
        if mode == "RGBA":
            img = img.convert("RGB")

        logger.debug(
            "Rendered page %d as PIL Image (%dx%d)",
            page_number,
            pix.width,
            pix.height,
        )
        return img
    except Exception as err:
        logger.exception("Failed to render page %d: %s", page_number, err)
        raise RuntimeError(f"Failed to render page {page_number}: {err}") from err


def render_page_to_image(page: fitz.Page, zoom: float = 2.0) -> Image.Image:
    """Render a single PyMuPDF Page instance into a PIL Image.

    Args:
        page: PyMuPDF Page object.
        zoom: Resolution scaling multiplier (default 2.0).

    Returns:
        PIL.Image.Image: Rendered page as an RGB PIL Image object.

    Raises:
        TypeError: If page is not a valid fitz.Page instance.
        RuntimeError: If rendering fails.
    """
    if not isinstance(page, fitz.Page):
        logger.error("Invalid page instance passed to render_page_to_image")
        raise TypeError("Expected a valid fitz.Page instance.")

    try:
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix)
        mode = "RGBA" if pix.alpha else "RGB"
        img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
        if mode == "RGBA":
            img = img.convert("RGB")
        return img
    except Exception as err:
        logger.exception("Failed to render fitz.Page instance: %s", err)
        raise RuntimeError(f"Failed to render page to image: {err}") from err


def render_all_pages(
    doc: fitz.Document,
    output_dir: str | Path = "pages",
    zoom: float = 2.0,
) -> None:
    """Render every page of a PDF document as PNG images to disk.

    Args:
        doc: Loaded PyMuPDF Document object.
        output_dir: Destination folder path for rendered images (default 'pages').
        zoom: Resolution scaling multiplier (default 2.0).

    Raises:
        TypeError: If doc is not a valid fitz.Document.
        RuntimeError: If output folder creation or image saving fails.
    """
    if not isinstance(doc, fitz.Document):
        logger.error("Invalid document instance passed to render_all_pages")
        raise TypeError("Expected a valid fitz.Document instance.")

    output_path = Path(output_dir)
    try:
        output_path.mkdir(parents=True, exist_ok=True)
    except Exception as err:
        logger.exception(
            "Failed to create output directory '%s': %s", output_dir, err
        )
        raise RuntimeError(
            f"Cannot create output directory '{output_dir}': {err}"
        ) from err

    matrix = fitz.Matrix(zoom, zoom)
    logger.info(
        "Rendering all %d pages to '%s' (zoom=%.1f)",
        len(doc),
        output_path,
        zoom,
    )

    for i, page in enumerate(doc):
        try:
            pix = page.get_pixmap(matrix=matrix)
            pix.save(output_path / f"page_{i + 1}.png")
        except Exception as err:
            logger.exception("Error rendering page %d to disk: %s", i + 1, err)
            raise RuntimeError(
                f"Failed saving page {i + 1} image to disk: {err}"
            ) from err

    logger.info("Successfully rendered %d pages to '%s'", len(doc), output_path)


def render_pdf_pages(
    doc: fitz.Document,
    output_dir: str | Path | None = None,
    zoom: float = 2.0,
) -> list[Image.Image]:
    """Render all pages of a PDF document as a list of PIL Images.

    Optionally saves rendered PNG images to output_dir if provided.

    Args:
        doc: Loaded PyMuPDF Document object.
        output_dir: Optional directory path to save page images.
        zoom: Resolution scaling multiplier (default 2.0).

    Returns:
        list[PIL.Image.Image]: List of rendered PIL Image objects.

    Raises:
        TypeError: If doc is not a valid fitz.Document.
        RuntimeError: If directory creation fails.
    """
    if not isinstance(doc, fitz.Document):
        logger.error("Invalid document instance passed to render_pdf_pages")
        raise TypeError("Expected a valid fitz.Document instance.")

    images: list[Image.Image] = []
    out_path = Path(output_dir) if output_dir else None

    if out_path:
        try:
            out_path.mkdir(parents=True, exist_ok=True)
        except Exception as err:
            logger.exception(
                "Failed to create output directory '%s': %s", output_dir, err
            )
            raise RuntimeError(
                f"Cannot create output directory '{output_dir}': {err}"
            ) from err

    for i, page in enumerate(doc, start=1):
        img = render_page(doc, i, zoom=zoom)
        images.append(img)
        if out_path:
            try:
                img.save(out_path / f"page_{i}.png")
            except Exception as err:
                logger.exception("Failed saving page image %d: %s", i, err)

    return images
