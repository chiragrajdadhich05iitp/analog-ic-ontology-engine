"""LLM query generation module for the Knowledge Graph.

Responsibilities:
- Synthesize human-readable query responses using LLMs.
- Retrieve data using the rule-based query engine.
- Combine raw data with user queries via prompt templates.
"""

import logging
import networkx as nx

from src.query.engine import query_graph
from src.query.responder import format_response
from src.query.prompts import RESPONSE_GENERATION_PROMPT

logger = logging.getLogger(__name__)


def generate_llm_response(prompt: str) -> str:
    """Generate a response using a configured Large Language Model.

    Args:
        prompt: The fully constructed prompt string containing the user query
            and the formatted context data.

    Returns:
        str: The generated response from the LLM.

    Raises:
        NotImplementedError: As LLM integration is not yet configured.
    """
    logger.error("LLM generation is not yet implemented.")
    raise NotImplementedError(
        "generate_llm_response is a placeholder. LLM integration is not yet configured."
    )


def answer_query(graph: nx.MultiDiGraph, query: str, use_llm: bool = False) -> str:
    """Answer a user query by querying the graph and (optionally) using an LLM.

    Executes the query against the graph, formats the results into text, and 
    either returns the text directly or uses it as context to generate a 
    conversational response via an LLM.

    Args:
        graph: The enriched NetworkX MultiDiGraph instance.
        query: The natural language string query provided by the user.
        use_llm: If True, attempts to pass the context to the LLM. Defaults to False.

    Returns:
        str: The final text response answering the user's query.
    """
    logger.info("Answering query: '%s' (use_llm=%s)", query, use_llm)

    # 1. Query the graph
    structured_result = query_graph(graph, query)
    
    # 2. Format the response context
    formatted_context = format_response(structured_result)

    # 3. If LLM is not requested or configured, return the formatted context directly.
    if not use_llm:
        logger.debug("Bypassing LLM generation, returning formatted context.")
        return formatted_context

    # 4. Build the prompt using the context and query
    prompt = RESPONSE_GENERATION_PROMPT.format(
        graph_data=formatted_context,
        query=query
    )

    # 5. Call the LLM
    try:
        llm_response = generate_llm_response(prompt)
        return llm_response
    except NotImplementedError:
        logger.warning(
            "LLM integration not available. Falling back to structured response."
        )
        return formatted_context
