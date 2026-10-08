"""LLM prompt templates and constants for datasheet extraction.

Responsibilities:
- Store reusable prompt templates for Electrical Characteristics extraction
- Store reusable prompt templates for Pin Configuration and Pin Functions extraction
- Provide helper prompt formatting functions without performing API calls or model execution
"""

# Common System Instruction for Datasheet Parsing LLM Tasks
SYSTEM_PROMPT: str = """You are an expert electronic hardware engineer and datasheet extraction specialist.
Your task is to analyze datasheet content (text and images) and extract precise, structured specifications.
Always adhere to the provided JSON schema. Do not make up or infer values that are not explicitly present in the source document.
If a value is not specified or is represented as a dash/blank, output null.
"""

# Prompt constant for Electrical Characteristics extraction
ELECTRICAL_CHARACTERISTICS_PROMPT: str = """Analyze the provided datasheet page(s) and extract the Electrical Characteristics table into valid JSON format.

Extract every electrical metric row with the following fields:
- parameter: The full descriptive name of the parameter (e.g., "Supply Voltage", "Quiescent Current", "Output High Voltage").
- symbol: The technical abbreviation or symbol (e.g., "VCC", "IQ", "VOH"). Output null if not specified.
- test_conditions: Operating conditions under which the metric was measured (e.g., "TA = 25°C, VCC = 5V"). Output null if not specified.
- min_value: Minimum value specified (numeric or string if complex range). Output null if not specified.
- typ_value: Typical value specified (numeric or string). Output null if not specified.
- max_value: Maximum value specified (numeric or string). Output null if not specified.
- unit: Standard unit of measurement (e.g., "V", "mV", "mA", "µA", "°C", "Hz", "Ω"). Output null if not specified.
- notes: Any footnotes or extra notes associated with the row. Output null if none.

JSON Output Schema:
{
  "section": "Electrical Characteristics",
  "metrics": [
    {
      "parameter": "string",
      "symbol": "string or null",
      "test_conditions": "string or null",
      "min_value": "number/string or null",
      "typ_value": "number/string or null",
      "max_value": "number/string or null",
      "unit": "string or null",
      "notes": "string or null"
    }
  ]
}

Respond ONLY with valid JSON inside a ```json ``` block.
"""

# Prompt constant for Pin Configuration and Pin Functions extraction
PIN_CONFIGURATION_PROMPT: str = """Analyze the provided datasheet page(s) and extract the Pin Configuration and Pin Functions into valid JSON format.

For each pin in the package or pinout diagram/table, extract:
- pin_number: Pin number or designation (e.g., "1", "A1", "P0.1").
- name: Pin name/label (e.g., "VCC", "GND", "SDA", "RESET").
- type: Pin type/direction (e.g., "Input", "Output", "I/O", "Power", "Ground", "No Connect"). Output null if not specified.
- description: Detailed function or pin usage description. Output null if not specified.

JSON Output Schema:
{
  "section": "Pin Configuration",
  "pins": [
    {
      "pin_number": "string",
      "name": "string",
      "type": "string or null",
      "description": "string or null"
    }
  ]
}

Respond ONLY with valid JSON inside a ```json ``` block.
"""

# Supplementary prompt constant for Absolute Maximum Ratings
ABSOLUTE_MAXIMUM_RATINGS_PROMPT: str = """Analyze the provided datasheet page(s) and extract the Absolute Maximum Ratings table into valid JSON format.

For each parameter in the Absolute Maximum Ratings table, extract:
- parameter: Descriptive parameter name (e.g., "Supply Voltage", "Storage Temperature Range").
- symbol: Symbol abbreviation (e.g., "VCC", "TSTG"). Output null if omitted.
- min_value: Minimum rating limit. Output null if omitted.
- max_value: Maximum rating limit. Output null if omitted.
- unit: Unit of measurement (e.g., "V", "°C"). Output null if omitted.

JSON Output Schema:
{
  "section": "Absolute Maximum Ratings",
  "ratings": [
    {
      "parameter": "string",
      "symbol": "string or null",
      "min_value": "number/string or null",
      "max_value": "number/string or null",
      "unit": "string or null"
    }
  ]
}

Respond ONLY with valid JSON inside a ```json ``` block.
"""

# Supplementary prompt constant for Recommended Operating Conditions
RECOMMENDED_OPERATING_CONDITIONS_PROMPT: str = """Analyze the provided datasheet page(s) and extract the Recommended Operating Conditions table into valid JSON format.

For each operating condition parameter, extract:
- parameter: Parameter description (e.g., "Operating Junction Temperature", "Supply Voltage").
- symbol: Symbol abbreviation. Output null if omitted.
- min_value: Minimum recommended value. Output null if omitted.
- typ_value: Typical recommended value. Output null if omitted.
- max_value: Maximum recommended value. Output null if omitted.
- unit: Unit of measurement. Output null if omitted.

JSON Output Schema:
{
  "section": "Recommended Operating Conditions",
  "conditions": [
    {
      "parameter": "string",
      "symbol": "string or null",
      "min_value": "number/string or null",
      "typ_value": "number/string or null",
      "max_value": "number/string or null",
      "unit": "string or null"
    }
  ]
}

Respond ONLY with valid JSON inside a ```json ``` block.
"""


def get_electrical_prompt(context_text: str | None = None) -> str:
    """Get the prompt template for Electrical Characteristics extraction.

    Args:
        context_text: Optional supplementary text context to append to the prompt.

    Returns:
        str: Complete prompt string.
    """
    if context_text:
        return f"{ELECTRICAL_CHARACTERISTICS_PROMPT}\n\nAdditional Text Context:\n{context_text}"
    return ELECTRICAL_CHARACTERISTICS_PROMPT


def get_pin_configuration_prompt(context_text: str | None = None) -> str:
    """Get the prompt template for Pin Configuration extraction.

    Args:
        context_text: Optional supplementary text context to append to the prompt.

    Returns:
        str: Complete prompt string.
    """
    if context_text:
        return f"{PIN_CONFIGURATION_PROMPT}\n\nAdditional Text Context:\n{context_text}"
    return PIN_CONFIGURATION_PROMPT
