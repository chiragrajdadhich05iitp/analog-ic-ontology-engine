"""Prompt definitions for the Knowledge Graph query module.

Responsibilities:
- Provide reusable LLM prompt templates for parsing user queries.
- Store system instructions for guiding the LLM in structuring its output.
"""

INTENT_EXTRACTION_PROMPT = """\
You are an expert intent parser for a component Knowledge Graph.
Your task is to analyze the user's natural language query and determine their intent.

User Query: "{query}"

Analyze the query and extract the following:
1. Intent type (e.g., FIND_COMPONENT, GET_PINOUT, COMPARE_METRICS).
2. Key entities mentioned (e.g., part number, parameter name, unit).

Output the result strictly as a structured JSON object.
"""

RESPONSE_GENERATION_PROMPT = """\
You are an intelligent assistant helping an engineer query a datasheet Knowledge Graph.
Using the following data retrieved from the graph, generate a clear, concise, and 
accurate response to the user's question.

Retrieved Data:
{graph_data}

User Question:
"{query}"

Generate the final response:
"""
