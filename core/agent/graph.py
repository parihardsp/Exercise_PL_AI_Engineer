"""
LangGraph StateGraph Agent Implementation for Portfolio Analytics.

Provides an enterprise-grade cyclical StateGraph orchestrator running alongside
the lightweight Python SDK agent, sharing the exact same tools, schema, and guardrails.
"""

import time
from typing import Any, Literal, Optional
from langchain_core.messages import BaseMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from core.agent.guard import check_conversational_guard
from core.agent.output_formatter import format_exposure_output, format_sql_output
from core.agent.router import extract_portfolio_name, route_question
from core.llm import GeminiClient
from tools.base import BaseTool
from tools.conversational_tool import ConversationalTool
from tools.exposure_tool import ExposureCalculatorTool
from tools.hybrid_tool import HybridExposureTool
from tools.sql_tool import SQLQueryTool
from utils.logger import logger, set_current_user

# Configuration Constants
MAX_MEMORY_MESSAGES: int = 6  # Retains last 3 complete Q&A turns (User + Assistant pairs)


# 1. Graph State Schema (Pydantic BaseModel - Channel & Agent Output Schema)
class PortfolioAgentGraphSchema(BaseModel):
    """Channel state & execution telemetry schema flowing through all graph nodes."""

    messages: list[dict[str, str]] = Field(default_factory=list)
    question: str = ""
    thread_id: str = "default_user"
    tool_name: Literal["sql_query", "exposure_calculator", "hybrid_exposure_tool", "conversational", ""] = ""
    parameters: dict[str, Any] = Field(default_factory=dict)
    tool_output: dict[str, Any] = Field(default_factory=dict)
    sql: str = ""
    tool_result: Any = None
    answer: str = ""
    success: bool = False
    error: str = ""
    is_blocked: bool = False
    eval_mode: bool = False
    start_time: float = 0.0
    execution_time_ms: float = 0.0


# 2. StateGraph Agent Wrapper
class StateGraphPortfolioAgent:
    """Enterprise LangGraph StateGraph Agent with multi-user isolation & sliding memory."""

    def __init__(self, llm: Optional[GeminiClient] = None):
        self.llm = llm or GeminiClient()
        sql_tool = SQLQueryTool(self.llm)
        exposure_tool = ExposureCalculatorTool()
        hybrid_tool = HybridExposureTool(sql_tool=sql_tool, exposure_tool=exposure_tool)
        conversational_tool = ConversationalTool()

        self.tools: dict[str, BaseTool] = {
            "sql_query": sql_tool,
            "exposure_calculator": exposure_tool,
            "hybrid_exposure_tool": hybrid_tool,
            "conversational": conversational_tool,
        }

        # Build StateGraph
        workflow = StateGraph(PortfolioAgentGraphSchema)

        workflow.add_node("guardrail", self._guardrail_step)
        workflow.add_node("router", self._router_step)
        workflow.add_node("executor", self._executor_step)
        workflow.add_node("formatter", self._formatter_step)

        # Define Transitions
        workflow.add_edge(START, "guardrail")
        workflow.add_conditional_edges(
            "guardrail",
            self._guardrail_condition,
            {"END": END, "router": "router"},
        )
        workflow.add_edge("router", "executor")
        workflow.add_edge("executor", "formatter")
        workflow.add_edge("formatter", END)

        # In-memory checkpointer for multi-turn thread memory
        self.checkpointer = MemorySaver()
        self.graph = workflow.compile(checkpointer=self.checkpointer)
        logger.info(f"[LANGGRAPH] StateGraph compiled with {len(self.tools)} tools & multi-user memory checkpointer")

    def _guardrail_step(self, state: PortfolioAgentGraphSchema) -> dict[str, Any]:
        """Stage 1: Centralized Input Guardrail Gateway (0ms / 0 LLM calls)."""
        question = state.question
        start_time = state.start_time or time.perf_counter()

        guard_res = check_conversational_guard(question, start_time)
        if guard_res is not None:
            elapsed = (time.perf_counter() - start_time) * 1000
            answer = guard_res["answer"]

            # Maintain sliding window
            updated_messages = list(state.messages)
            updated_messages.append({"role": "user", "content": question})
            updated_messages.append({"role": "assistant", "content": answer})

            logger.info(f"[LANGGRAPH] Guardrail intercepted '{question}' in {elapsed:.2f}ms")
            return {
                "messages": updated_messages[-MAX_MEMORY_MESSAGES:],
                "answer": answer,
                "tool_name": "conversational",
                "parameters": guard_res.get("parameters", {}),
                "tool_result": guard_res.get("tool_result"),
                "sql": "",
                "success": True,
                "error": "",
                "is_blocked": True,
                "execution_time_ms": elapsed,
            }

        return {"is_blocked": False}

    def _guardrail_condition(self, state: PortfolioAgentGraphSchema) -> str:
        """Route conditionally based on whether guardrail blocked input."""
        return "END" if state.is_blocked else "router"

    def _router_step(self, state: PortfolioAgentGraphSchema) -> dict[str, Any]:
        """Stage 2: Pydantic Structured Output LLM Routing with contextual history."""
        question = state.question

        # In eval mode, evaluate question statelessly without cross-question memory bleed
        if state.eval_mode or not state.messages:
            contextual_query = question
        else:
            recent_history = state.messages[-MAX_MEMORY_MESSAGES:]
            history_context = "\n".join([
                f"{m['role'].capitalize()}: {m['content'].strip()}"
                for m in recent_history
            ])
            contextual_query = f"Previous Conversation Context:\n{history_context}\n\nCurrent User Question: {question}"

        tool_name, params = route_question(contextual_query, self.tools, self.llm)
        logger.info(f"[LANGGRAPH] Selected tool: '{tool_name}' with params: {params}")

        # Sanitize parameter keys for target tools and pass contextual query
        if tool_name in {"sql_query", "hybrid_exposure_tool"}:

            # Strip any hallucinated SQL or query aliases
            params.pop("query", None)
            params.pop("sql", None)
            params.pop("prebuilt_sql", None)

            # Bind to the validated contextual question
            params["question"] = contextual_query

        elif tool_name == "exposure_calculator":

            # Ensure portfolio name is resolved from parameters OR from context
            p_val = str(params.get("portfolio_name") or params.get("portfolio_id") or "").strip()
            resolved = extract_portfolio_name(p_val) if p_val else ""
            if not resolved or resolved == p_val:
                resolved_from_q = extract_portfolio_name(question)
                if resolved_from_q and resolved_from_q != question:
                    resolved = resolved_from_q
            params["portfolio_name"] = resolved if resolved else (p_val or question)

        return {
            "tool_name": tool_name,
            "parameters": params,
        }

    def _executor_step(self, state: PortfolioAgentGraphSchema) -> dict[str, Any]:
        """Execute the selected tool deterministically."""
        tool_name = state.tool_name
        params = state.parameters
        tool = self.tools.get(tool_name)

        if not tool:
            logger.error(f"[LANGGRAPH] Tool '{tool_name}' not found.")
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found.",
                "tool_result": None,
                "sql": "",
            }

        logger.info(f"[LANGGRAPH] Executing tool '{tool_name}'...")
        tool_output = tool.run(**params)
        return {
            "tool_output": tool_output,
            "success": tool_output.get("success", False),
            "tool_result": tool_output.get("result"),
            "sql": tool_output.get("sql", ""),
            "error": tool_output.get("error", ""),
        }

    def _formatter_step(self, state: PortfolioAgentGraphSchema) -> dict[str, Any]:
        """Stage 3: Output formatting and conversational synthesis with sliding memory retention."""
        if state.is_blocked:
            return {}

        question = state.question
        tool_name = state.tool_name
        raw_result = state.tool_result
        success = state.success
        error = state.error
        eval_mode = state.eval_mode

        if not success:
            answer = error if error else "An error occurred while processing your request."
        else:
            if tool_name == "conversational":
                answer = state.tool_output.get("answer", "I can only help with portfolio data questions.")
            elif tool_name in {"exposure_calculator", "hybrid_exposure_tool"}:
                answer = format_exposure_output(raw_result)
            elif tool_name == "sql_query":
                if eval_mode:
                    rows = raw_result or []
                    answer = f"{len(rows)} row(s) returned." if rows else "No results."
                else:
                    answer = format_sql_output(question, raw_result, self.llm, use_llm=True)
            else:
                answer = str(raw_result)

        start_time = state.start_time or time.perf_counter()
        elapsed = (time.perf_counter() - start_time) * 1000

        # Update sliding window (retains last MAX_MEMORY_MESSAGES)
        updated_messages = list(state.messages)
        updated_messages.append({"role": "user", "content": question})
        updated_messages.append({"role": "assistant", "content": answer})
        trimmed_messages = updated_messages[-MAX_MEMORY_MESSAGES:]

        logger.info(f"[AGENT:ANSWER] {answer.strip()}")
        logger.info(f"[LANGGRAPH] Completed in {elapsed:.2f}ms (Success={success}, MemoryWindow={len(trimmed_messages)} msgs)")

        return {
            "messages": trimmed_messages,
            "answer": answer,
            "execution_time_ms": elapsed,
        }

    def run(
        self,
        question: str,
        eval_mode: bool = False,
        thread_id: Optional[str] = "default_user",
    ) -> dict[str, Any]:
        """Execute state graph for user question with session persistence and sliding memory."""
        start_time = time.perf_counter()
        effective_thread_id = (thread_id or "default_user").strip() or "default_user"

        # Set user context for universal logging across all modules (DB, SQLTool, Formatter)
        set_current_user(effective_thread_id)

        config = {"configurable": {"thread_id": effective_thread_id}}

        # Load existing conversation history from checkpointer if present (bypassed in eval_mode)
        if eval_mode:
            existing_messages = []
        else:
            current_state = self.graph.get_state(config)
            existing_messages = current_state.values.get("messages", []) if current_state and current_state.values else []

        initial_state = PortfolioAgentGraphSchema(
            messages=existing_messages,
            question=question,
            thread_id=effective_thread_id,
            eval_mode=eval_mode,
            start_time=start_time,
        )

        final_state: dict[str, Any] = self.graph.invoke(initial_state, config=config)

        elapsed = (time.perf_counter() - start_time) * 1000
        return {
            "question": question,
            "thread_id": effective_thread_id,
            "tool_name": final_state.get("tool_name", ""),
            "parameters": final_state.get("parameters", {}),
            "tool_result": final_state.get("tool_result"),
            "sql": final_state.get("sql", ""),
            "answer": final_state.get("answer", ""),
            "execution_time_ms": final_state.get("execution_time_ms", elapsed),
            "success": final_state.get("success", False),
            "error": final_state.get("error", ""),
            "memory_messages_count": len(final_state.get("messages", [])),
        }
