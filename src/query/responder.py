"""Responder module for the Knowledge Graph query system.

Responsibilities:
- Convert structured query results into clean, human-readable text responses.
- Provide informative fallback messages when queries return no results.
"""

from typing import Any


def format_response(result: dict[str, Any]) -> str:
    """Format structured query results into a human-readable text response.

    Args:
        result: A dictionary containing the 'success' flag, the 'intent', and 
            the list of matched 'results' from the query engine.

    Returns:
        str: A clean, human-readable response string summarizing the data.
    """
    if not result.get("success"):
        return result.get("message", "No matching data was found for your query.")

    intent = result.get("intent", "UNKNOWN")
    nodes = result.get("results", [])

    if not nodes:
        return "The query was successful, but no matching items were found."

    if intent == "list_pins":
        lines = ["Here are the pins found in the component:"]
        for node in nodes:
            num = node.get("pin_number", "?")
            name = node.get("name", "Unknown")
            desc = node.get("description", "")
            line = f"  - Pin {num}: {name}"
            if desc:
                line += f" ({desc})"
            lines.append(line)
        return "\n".join(lines)

    elif intent in ("find_pin_by_number", "find_pin_by_name"):
        if len(nodes) == 1:
            node = nodes[0]
            num = node.get("pin_number", "?")
            name = node.get("name", "Unknown")
            desc = node.get("description", "No description available.")
            return f"Pin {num} is '{name}'. Description: {desc}"
        else:
            lines = [f"Found {len(nodes)} matching pins:"]
            for node in nodes:
                num = node.get("pin_number", "?")
                name = node.get("name", "Unknown")
                lines.append(f"  - Pin {num}: {name}")
            return "\n".join(lines)

    elif intent == "list_metrics":
        lines = [f"Found {len(nodes)} electrical metrics:"]
        for node in nodes:
            param = node.get("parameter", "Unknown Parameter")
            typ = node.get("typ_value")
            unit = node.get("unit", "")
            
            val_str = f"Typical: {typ} {unit}".strip() if typ is not None else "No typical value"
            lines.append(f"  - {param} ({val_str})")
        return "\n".join(lines)

    elif intent == "find_metric":
        lines = [f"Here are the details for the requested metric(s):"]
        for node in nodes:
            param = node.get("parameter", "Unknown Parameter")
            cond = node.get("test_conditions", "N/A")
            min_val = node.get("min_value", "-")
            typ_val = node.get("typ_value", "-")
            max_val = node.get("max_value", "-")
            unit = node.get("unit", "")
            
            lines.append(f"  - Parameter: {param}")
            lines.append(f"    Conditions: {cond}")
            lines.append(f"    Min/Typ/Max: {min_val} / {typ_val} / {max_val} {unit}".strip())
        return "\n".join(lines)

    elif intent == "list_sections":
        lines = ["The datasheet contains the following sections:"]
        for node in nodes:
            name = node.get("name", "Unknown Section")
            lines.append(f"  - {name}")
        return "\n".join(lines)

    else:
        # Fallback for unknown intent with valid results
        return f"Found {len(nodes)} result(s), but no formatter is defined for intent '{intent}'."
