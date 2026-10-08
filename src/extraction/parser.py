"""Datasheet section parsing and page location module.

Responsibilities:
- Define standard datasheet section keywords and categories
- Parse PDF Table of Contents (TOC) for target sections
- Perform full-text search across document pages to identify section locations
- Map section names to 1-indexed page numbers for downstream processing
"""

import logging
from typing import Any
import fitz

logger = logging.getLogger(__name__)

# Standard default keywords mapping section categories to search terms
DEFAULT_SECTION_KEYWORDS: dict[str, list[str]] = {
    "pin_configuration": [
        "Pin Configuration",
        "Pin Functions",
        "Pinout",
        "Terminal Functions",
    ],
    "absolute_maximum_ratings": [
        "Absolute Maximum Ratings",
        "Maximum Ratings",
        "Limiting Values",
    ],
    "recommended_operating_conditions": [
        "Recommended Operating Conditions",
        "Operating Conditions",
        "Recommended Operating State",
    ],
    "electrical_characteristics": [
        "Electrical Characteristics",
        "Electrical Specs",
        "Static Characteristics",
        "Dynamic Characteristics",
    ],
    "package_information": [
        "Package Information",
        "Package Option Addendum",
        "Mechanical Data",
        "Packaging Information",
        "Outline Dimensions",
    ],
}


def find_sections_from_toc(
    toc: list[list[Any]],
    section_keywords: dict[str, list[str]] | None = None,
) -> dict[str, list[int]]:
    """Parse a PDF Table of Contents (TOC) to locate page numbers for target sections.

    Args:
        toc: PyMuPDF Table of Contents list, where each item is [level, title, page_number].
        section_keywords: Dictionary mapping section canonical names to lists of search keywords.
            Defaults to DEFAULT_SECTION_KEYWORDS.

    Returns:
        dict[str, list[int]]: Mapping of canonical section names to sorted list of
            1-indexed page numbers found in the TOC.
    """
    if section_keywords is None:
        section_keywords = DEFAULT_SECTION_KEYWORDS

    found_sections: dict[str, set[int]] = {
        section: set() for section in section_keywords
    }

    for entry in toc:
        if len(entry) < 3:
            continue
        title = str(entry[1])
        page_num = int(entry[2])

        title_lower = title.lower()
        for section_name, keywords in section_keywords.items():
            for kw in keywords:
                if kw.lower() in title_lower:
                    found_sections[section_name].add(page_num)
                    logger.debug(
                        "TOC match: '%s' -> section '%s' on page %d",
                        title,
                        section_name,
                        page_num,
                    )

    result = {
        section: sorted(list(pages))
        for section, pages in found_sections.items()
        if pages
    }
    logger.info("TOC section search completed: found %d sections", len(result))
    return result


def find_sections_from_text(
    doc: fitz.Document,
    section_keywords: dict[str, list[str]] | None = None,
) -> dict[str, list[int]]:
    """Search PDF page text to locate page numbers for target sections.

    Args:
        doc: Loaded PyMuPDF Document object.
        section_keywords: Dictionary mapping section canonical names to lists of search keywords.
            Defaults to DEFAULT_SECTION_KEYWORDS.

    Returns:
        dict[str, list[int]]: Mapping of canonical section names to sorted list of
            1-indexed page numbers containing matched section headings/keywords.

    Raises:
        TypeError: If doc is not a valid fitz.Document instance.
        RuntimeError: If page text extraction fails.
    """
    if not isinstance(doc, fitz.Document):
        logger.error("Invalid document instance passed to find_sections_from_text")
        raise TypeError("Expected a valid fitz.Document instance.")

    if section_keywords is None:
        section_keywords = DEFAULT_SECTION_KEYWORDS

    found_sections: dict[str, set[int]] = {
        section: set() for section in section_keywords
    }

    try:
        for page_index, page in enumerate(doc):
            page_number = page_index + 1
            text = page.get_text() or ""
            text_lower = text.lower()

            for section_name, keywords in section_keywords.items():
                for kw in keywords:
                    if kw.lower() in text_lower:
                        found_sections[section_name].add(page_number)
                        logger.debug(
                            "Text match: keyword '%s' -> section '%s' on page %d",
                            kw,
                            section_name,
                            page_number,
                        )

        result = {
            section: sorted(list(pages))
            for section, pages in found_sections.items()
            if pages
        }
        logger.info(
            "Text section search completed: located %d sections across %d pages",
            len(result),
            len(doc),
        )
        return result
    except Exception as err:
        logger.exception("Error searching text for section pages: %s", err)
        raise RuntimeError(f"Failed searching section pages in PDF: {err}") from err


def locate_datasheet_sections(
    doc: fitz.Document,
    section_keywords: dict[str, list[str]] | None = None,
) -> dict[str, list[int]]:
    """Locate all key datasheet sections by combining TOC parsing and full-text search.

    Combines results from Table of Contents extraction and full-text page search to produce
    a consolidated map of section locations.

    Args:
        doc: Loaded PyMuPDF Document object.
        section_keywords: Dictionary mapping section canonical names to search keywords.
            Defaults to DEFAULT_SECTION_KEYWORDS.

    Returns:
        dict[str, list[int]]: Consolidated mapping of canonical section names to
            sorted 1-indexed page numbers.

    Raises:
        TypeError: If doc is not a valid fitz.Document instance.
    """
    if not isinstance(doc, fitz.Document):
        logger.error("Invalid document instance passed to locate_datasheet_sections")
        raise TypeError("Expected a valid fitz.Document instance.")

    if section_keywords is None:
        section_keywords = DEFAULT_SECTION_KEYWORDS

    # 1. Try TOC parsing
    toc = doc.get_toc()
    toc_sections = find_sections_from_toc(toc, section_keywords)

    # 2. Perform text page search
    text_sections = find_sections_from_text(doc, section_keywords)

    # 3. Merge TOC and Text search results
    consolidated: dict[str, set[int]] = {
        section: set() for section in section_keywords
    }

    for section, pages in toc_sections.items():
        consolidated[section].update(pages)

    for section, pages in text_sections.items():
        consolidated[section].update(pages)

    result = {
        section: sorted(list(pages))
        for section, pages in consolidated.items()
        if pages
    }

    logger.info(
        "Datasheet section location completed: identified %d total sections",
        len(result),
    )
    return result


def get_section_pages(
    section_map: dict[str, list[int]], section_name: str
) -> list[int]:
    """Retrieve 1-indexed page numbers for a specific section from a section map.

    Args:
        section_map: Output dictionary from locate_datasheet_sections or find_sections.
        section_name: Canonical section name to query.

    Returns:
        list[int]: List of page numbers, or empty list if the section is not found.
    """
    pages = section_map.get(section_name, [])
    logger.debug("Queried section '%s': found pages %s", section_name, pages)
    return pages
