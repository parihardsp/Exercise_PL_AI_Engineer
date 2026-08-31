"""
Conversational Tool — Layer 2 guardrail for off-topic inputs.

When the routing LLM determines a question is NOT about portfolio data,
it selects this tool. Returns a single fixed out-of-scope response with
zero additional LLM calls.

Layer 1 (keyword pre-filter in agent.py) catches the obvious cases first.
This tool only fires when something slips past Layer 1 and the routing
LLM correctly identifies it as non-portfolio.
"""

from typing import Any

from tools.base import BaseTool



class ConversationalTool(BaseTool):
    """
    Zero-LLM-call handler for non-portfolio conversational inputs.

    Selected by the routing LLM when the user's message is not about
    portfolio data. Returns a fixed informative response immediately
    without triggering SQL generation or NL formatting calls.
    """

    name = "conversational"
    description = (
        "Use ONLY when the user's message is NOT a portfolio data question. "
        "Examples: farewells, greetings, thanks, off-topic questions like "
        "'what is the weather?' or 'tell me a joke'. "
        "Do NOT use this for any question about portfolios, holdings, sectors, "
        "performance, or any financial data."
    )

    def run(self, **kwargs: Any) -> dict[str, Any]:
        """
        Return a fixed out-of-scope guidance response. No LLM calls made.

        Returns:
            {"success": True, "result": "out_of_scope", "answer": str, "error": ""}
        """
        from core.agent.guard import CANNED_HELP_RESPONSE
        return {
            "success": True,
            "result": "out_of_scope",
            "answer": CANNED_HELP_RESPONSE,
            "error": "",
        }

