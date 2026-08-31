"""
Pydantic data models for structured routing and schema validation.

Uses a lenient design with safe defaults so the LLM is guided with
explicit field names without failing if optional values are omitted.
"""

from typing import Any, Literal
from pydantic import BaseModel, Field


class ToolRoutingSchema(BaseModel):
    """
    Validation schema for LLM tool selection output.

    Validates that the LLM picks a valid tool and extracts the necessary
    parameters, using safe defaults to prevent validation crashes.
    """

    # 1. The selected tool (strictly enforced by Pydantic)
    tool: Literal[
        "sql_query",
        "exposure_calculator",
        "conversational",
        "hybrid_exposure_tool",
    ] = Field(
        ...,
        description=(
            "The tool to run:\n"
            "- 'sql_query': General database questions, counts, performance, dates, comparisons.\n"
            "- 'exposure_calculator': Sector exposures when the exact portfolio name is already provided.\n"
            "- 'hybrid_exposure_tool': Sector exposures for a portfolio identified by a condition/ranking (e.g. 'highest AUM', 'top performing', 'largest fund').\n"
            "- 'conversational': Greetings, farewells, thanks, off-topic."
        )
    )

    # 2. Parameters for each tool (with safe defaults)
    question: str = Field(
        default="",
        description="The question (used for 'sql_query' and 'hybrid_exposure_tool')."
    )

    portfolio_name: str = Field(
        default="",
        description="The extracted portfolio name (used when tool is 'exposure_calculator', e.g. 'Tech Innovation Fund')."
    )

    message: str = Field(
        default="",
        description="The user message (used when tool is 'conversational')."
    )

    def get_params(self, original_question: str = "") -> dict[str, Any]:
        """
        Extract a clean parameters dictionary for the selected tool.

        Falls back to original_question if the extracted parameter was empty.
        """
        if self.tool in {"sql_query", "hybrid_exposure_tool"}:
            q = self.question.strip() if self.question.strip() else original_question
            return {"question": q}

        if self.tool == "exposure_calculator":
            return {"portfolio_name": self.portfolio_name.strip()}

        if self.tool == "conversational":
            msg = self.message.strip() if self.message.strip() else original_question
            return {"message": msg}

        return {}
