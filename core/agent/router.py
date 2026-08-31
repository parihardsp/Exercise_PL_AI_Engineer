"""
Tool routing and dispatch logic for the Portfolio Analytics Agent.

Uses ToolRoutingSchema (Pydantic) for structured output validation,
with rule-based heuristic fallback if the LLM call fails.
"""

import re
from typing import Any

from core.agent.schemas import ToolRoutingSchema
from core.llm import GeminiClient
from core.prompts import agent_routing_prompt
from db.session import get_db
from tools.base import BaseTool
from utils.logger import logger


def build_tools_description(tools: dict[str, BaseTool]) -> str:
    """Build a formatted description of all available tools for the prompt."""
    descriptions = []
    for name, tool in tools.items():
        descriptions.append(f"Tool: {name}\nDescription: {tool.description.strip()}")
    return "\n\n".join(descriptions)


def extract_portfolio_name(question: str) -> str:
    """Find and return matching canonical portfolio name with strict suffix interchangeability."""
    if not question:
        return ""
    try:
        with get_db() as repo:
            portfolios = repo.fetch_all("SELECT portfolio_id, portfolio_name FROM portfolios")

        q = question.strip()
        suffixes = r"(?:fund|portfolio|etf|strategy|trust|index)"

        for p in portfolios:
            p_id, p_name = str(p["portfolio_id"]), p["portfolio_name"]
            if q == p_id or q.lower() == p_name.lower():
                return p_name

            core = re.sub(rf"\s+{suffixes}$", "", p_name, flags=re.I).strip()
            # Strict full match for entity phrases (e.g. 'Balanced Fund', 'Balanced')
            if re.fullmatch(rf"{re.escape(core)}(?:\s+{suffixes})?", q, flags=re.I):
                return p_name
            # Sentence match for full portfolio phrases
            if re.search(rf"\b{re.escape(core)}\s+{suffixes}\b", q, flags=re.I):
                return p_name
    except Exception as e:
        logger.warning(f"Error in extract_portfolio_name: {e}")

    return question


def route_question(
    question: str,
    tools: dict[str, BaseTool],
    llm: GeminiClient,
) -> tuple[str, dict[str, Any]]:
    """
    Decide which tool should handle the user's question.

    Validates LLM output against ToolRoutingSchema, and falls back to
    simple keyword matching if there is an error.
    """
    logger.log_agent_thought(f"Routing question: {question!r}")
    tools_desc = build_tools_description(tools)
    prompt = agent_routing_prompt(question, tools_desc)

    try:
        # Validate LLM output against the Pydantic schema
        routing_result = llm.generate_structured(ToolRoutingSchema, prompt)

        tool_name = routing_result.tool
        params = routing_result.get_params(original_question=question)

        if tool_name in tools:
            logger.log_agent_thought(f"Selected tool: {tool_name!r} with params: {params}")
            return tool_name, params
        else:
            logger.warning(f"[AGENT] Tool '{tool_name}' not found in registered tools. Using fallback.")

    except Exception as error:
        logger.warning(f"[AGENT] Schema validation routing failed ({error}). Using heuristic fallback.")

    # Fallback: Simple keyword check if LLM routing fails
    q_lower = question.lower()
    if "exposure" in q_lower or (
        "sector" in q_lower
        and ("breakdown" in q_lower or "allocation" in q_lower or "weight" in q_lower)
    ):
        matched_name = extract_portfolio_name(question)
        return "exposure_calculator", {"portfolio_name": matched_name}

    return "sql_query", {"question": question}
