"""
Pydantic Request and Response schemas for the Portfolio Analytics REST API.
"""

from typing import Any, Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Payload for submitting a natural language portfolio question."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="The natural language question to process.",
        examples=["How many portfolios do we have in total?"],
    )
    session_id: Optional[str] = Field(
        default="default_user",
        description="Optional user or session identifier for multi-user thread isolation and memory tracking.",
        examples=["user_alex_123"],
    )
    eval_mode: bool = Field(
        default=False,
        description="If True, skips the natural language synthesis formatting call.",
    )


class QueryResponse(BaseModel):
    """Structured response returned by the portfolio analytics agent."""

    question: str = Field(description="The original user query.")
    session_id: Optional[str] = Field(default="default_user", description="Active user session identifier.")
    tool_name: str = Field(description="The tool selected and executed by the agent.")
    parameters: dict[str, Any] = Field(description="Parameters passed to the executed tool.")
    tool_result: Any = Field(description="Raw structured result returned by the tool.")
    sql: str = Field(default="", description="SQL query executed (if applicable).")
    answer: str = Field(description="Human-readable response string.")
    execution_time_ms: float = Field(description="Total latency in milliseconds.")
    success: bool = Field(description="Whether the query was processed successfully.")
    error: str = Field(default="", description="Error description if processing failed.")


class HealthResponse(BaseModel):
    """Service health and database status response."""

    status: str = Field(default="healthy", description="API status (healthy/degraded).")
    database_connected: bool = Field(description="Whether database is reachable.")
    database_tables: int = Field(description="Total number of database tables found.")
    model_name: str = Field(description="Configured Gemini model identifier.")
    langsmith_tracing: bool = Field(description="Whether LangSmith auto-tracing is enabled.")


class ToolInfo(BaseModel):
    """Metadata describing an individual agent tool."""

    name: str = Field(description="Tool identifier name.")
    description: str = Field(description="Description of what the tool does.")


class ToolsListResponse(BaseModel):
    """List of all available agent tools."""

    tools: list[ToolInfo] = Field(description="Registered agent tools.")
    count: int = Field(description="Total number of tools.")


class EvaluationResponse(BaseModel):
    """Summary metrics of an evaluation run against the ground truth dataset."""

    total_questions: int
    correct_routing_pct: float
    successful_execution_pct: float
    sql_similarity_pct: float = Field(default=100.0, description="Average SQL structural similarity %")
    correct_matches_pct: float
    avg_latency_seconds: float
    results: list[dict[str, Any]]
    markdown_report: str = Field(default="", description="Auto-generated Markdown evaluation report")
