"""Query parsing module.

Responsibilities:
- Parse user natural language queries into structured intents using rule-based heuristics.
- Extract recognized entities or filtering parameters from the query.
"""

import logging
import re
from typing import TypedDict

logger = logging.getLogger(__name__)


class QueryIntent(TypedDict):
    """Structured representation of a parsed user query."""
    intent: str
    entity: str | None
    value: str | None
    confidence: float


def parse_query(query: str) -> QueryIntent:
    """Parse a natural language query into a structured QueryIntent dictionary.

    Uses keyword and regex-based rules to determine the user's intent from the query.
    Supported intents:
        - list_pins: E.g., "list all pins", "show me the pins"
        - find_pin_by_number: E.g., "what is pin 5", "pin number 8"
        - find_pin_by_name: E.g., "find pin VCC", "details for GND pin"
        - list_metrics: E.g., "list electrical metrics", "show characteristics"
        - find_metric: E.g., "what is the supply voltage", "metric for input offset"
        - list_sections: E.g., "what sections are in the datasheet", "list sections"

    Args:
        query: The raw natural language query string.

    Returns:
        QueryIntent: A dictionary describing the recognized intent, extracted
            entities/values, and a confidence score.

    Raises:
        ValueError: If the query string is empty or invalid.
    """
    if not query or not str(query).strip():
        logger.error("Attempted to parse an empty query.")
        raise ValueError("Query string cannot be empty.")

    cleaned_query = str(query).strip().lower()
    logger.debug("Parsing query: '%s'", cleaned_query)

    # list_sections
    if re.search(r"list\s+sections|what\s+sections|show\s+sections", cleaned_query):
        return {"intent": "list_sections", "entity": None, "value": None, "confidence": 0.8}

    # list_pins
    if re.search(r"list\s+(all\s+)?pins|show(\s+me)?\s+the\s+pins", cleaned_query):
        return {"intent": "list_pins", "entity": None, "value": None, "confidence": 0.8}

    # find_pin_by_number (e.g., "pin 5", "pin number 8")
    pin_num_match = re.search(r"pin\s+(number\s+)?(\d+)", cleaned_query)
    if pin_num_match:
        return {
            "intent": "find_pin_by_number",
            "entity": "pin_number",
            "value": pin_num_match.group(2),
            "confidence": 0.9
        }

    # find_pin_by_name (e.g., "pin VCC", "VCC pin")
    pin_name_match = re.search(r"pin\s+([a-z0-9_+-]+)", cleaned_query)
    if pin_name_match and not pin_name_match.group(1).isdigit():
        return {
            "intent": "find_pin_by_name",
            "entity": "pin_name",
            "value": pin_name_match.group(1),
            "confidence": 0.8
        }
    
    pin_name_prefix_match = re.search(r"([a-z0-9_+-]+)\s+pin", cleaned_query)
    if pin_name_prefix_match and not pin_name_prefix_match.group(1).isdigit():
        return {
            "intent": "find_pin_by_name",
            "entity": "pin_name",
            "value": pin_name_prefix_match.group(1),
            "confidence": 0.8
        }

    # list_metrics
    if re.search(r"list\s+(all\s+)?(electrical\s+)?metrics|show\s+characteristics", cleaned_query):
        return {"intent": "list_metrics", "entity": None, "value": None, "confidence": 0.8}

    # find_metric (fallback for metric queries, e.g., "what is the supply voltage")
    metric_match = re.search(r"what is (the )?(.*?)( metric)?\s*\??$", cleaned_query)
    if metric_match:
        # Avoid matching generic phrases as metric queries if possible
        value = metric_match.group(2).strip()
        if value and "pin" not in value and "section" not in value:
            return {
                "intent": "find_metric",
                "entity": "metric_name",
                "value": value,
                "confidence": 0.6
            }

    metric_keyword_match = re.search(r"metric for (.*?)\s*\??$", cleaned_query)
    if metric_keyword_match:
        return {
            "intent": "find_metric",
            "entity": "metric_name",
            "value": metric_keyword_match.group(1).strip(),
            "confidence": 0.8
        }

    # Fallback UNKNOWN intent
    return {
        "intent": "UNKNOWN",
        "entity": None,
        "value": None,
        "confidence": 0.0,
    }
