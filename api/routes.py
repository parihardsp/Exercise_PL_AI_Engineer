"""
API route handlers for Portfolio Analytics Agent.
"""

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, status

from api.models import (
    EvaluationResponse,
    HealthResponse,
    QueryRequest,
    QueryResponse,
    ToolInfo,
    ToolsListResponse,
)
from core.agent import PortfolioAgent, StateGraphPortfolioAgent
from db.session import get_db
from tests.evaluator import evaluate_dataset
from utils.config import GEMINI_MODEL, LANGSMITH_TRACING, LLM_PROVIDER, GROQ_MODEL
from utils.logger import logger, set_current_user

router_tools = APIRouter(prefix="/api/v1", tags=["Tools-Query"])
router_health = APIRouter(prefix="/api/v1", tags=["Health"])

# Global shared stateful LangGraph agent instance with multi-user session memory
_agent = StateGraphPortfolioAgent()



@router_health.get(

    "/health",
    response_model=HealthResponse,
    summary="Health check & system status",
    description="Returns the status of the database connection, table counts, and model configuration.",

)
async def health_check() -> HealthResponse:
    """Perform health and connectivity diagnostics."""
    set_current_user("System")
    db_connected = False
    table_count = 0

    try:
        with get_db() as repo:
            rows = repo.fetch_all(
                "SELECT COUNT(*) as count FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
            )
            table_count = rows[0]["count"] if rows else 0
            db_connected = True
    except Exception as e:
        logger.error(f"[HEALTH] Database health check failed: {e}")

    active_model = GROQ_MODEL if LLM_PROVIDER == "groq" else GEMINI_MODEL
    return HealthResponse(
        status="healthy" if db_connected else "degraded",
        database_connected=db_connected,
        database_tables=table_count,
        model_name=active_model,
        langsmith_tracing=LANGSMITH_TRACING,
    )




@router_tools.post(
    "/query",
    response_model=QueryResponse,
    summary="Ask a portfolio question",
    description="Processes a natural language question through the portfolio agent (concurrently non-blocking).",
)
async def query_portfolio_agent(payload: QueryRequest) -> QueryResponse:
    """Execute a query through the agent with non-blocking asynchronous thread dispatch."""
    query_text = payload.query.strip()
    session_id = payload.session_id or "default_user"

    if not query_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query string cannot be empty.",
        )

    set_current_user(session_id)
    logger.info(f"[API] Received query: {query_text!r}")

    try:
        # Run agent in async threadpool with user session isolation
        def _dispatch():
            set_current_user(session_id)
            return _agent.run(query_text, eval_mode=payload.eval_mode, thread_id=session_id)

        response_dict: dict[str, Any] = await asyncio.to_thread(_dispatch)

        if "session_id" not in response_dict:
            response_dict["session_id"] = session_id

        return QueryResponse(**response_dict)

    except Exception as e:
        logger.error(f"[API] Query processing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal agent processing error: {str(e)}",
        )


@router_tools.get(
    "/tools",
    response_model=ToolsListResponse,
    summary="List available agent tools",
    description="Returns metadata and descriptions for all registered agent tools.",
)
async def list_tools() -> ToolsListResponse:
    """List all registered tools."""
    tool_items = [
        ToolInfo(name=tool.name, description=tool.description)
        for tool in _agent.tools.values()
    ]
    return ToolsListResponse(tools=tool_items, count=len(tool_items))


@router_tools.post(
    "/eval",
    response_model=EvaluationResponse,
    summary="Run benchmark evaluation",
    description="Executes the full 12-question ground truth dataset evaluation benchmark.",
)
async def run_evaluation() -> EvaluationResponse:
    """Run automated evaluation against ground truth dataset asynchronously."""
    try:
        eval_metrics = await asyncio.to_thread(evaluate_dataset, _agent)
        return EvaluationResponse(**eval_metrics)
    except Exception as e:
        logger.error(f"[API] Evaluation run failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {str(e)}",
        )
