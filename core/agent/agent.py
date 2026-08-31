"""
Portfolio Analytics Agent — Pipeline Orchestrator.

Coordinates the entire question-answering workflow:
  1. Layer 1 Guardrail check (fast zero-LLM keyword filter)
  2. Router: determines appropriate tool (SQL query vs Exposure calculator vs Hybrid vs Conversational)
  3. Tool execution
  4. Output formatting & answer synthesis
  5. Latency & structured logging
"""

import time
from typing import Any, Optional, Sequence

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


class PortfolioAgent:
    """
    Main orchestrator for answering natural language portfolio questions.

    Maintains a registry of BaseTool instances. Adding new tools requires
    only registering them in `tools` list at initialization.
    """

    def __init__(
        self,
        llm: Optional[GeminiClient] = None,
        tools: Optional[Sequence[BaseTool]] = None,
    ) -> None:
        """
        Initialize the agent with an LLM client and tool suite.

        Args:
            llm: GeminiClient instance. If None, creates a default instance.
            tools: Optional custom list of BaseTools.
        """
        self.llm = llm if llm is not None else GeminiClient()

        if tools is not None:
            tool_list = list(tools)
        else:
            sql_t = SQLQueryTool(self.llm)
            exp_t = ExposureCalculatorTool()
            tool_list = [
                sql_t,
                exp_t,
                HybridExposureTool(sql_tool=sql_t, exposure_tool=exp_t),
                ConversationalTool(),
            ]

        self.tools: dict[str, BaseTool] = {tool.name: tool for tool in tool_list}
        logger.info(f"[AGENT] Initialized with tools: {list(self.tools.keys())}")

    def run(
        self,
        question: str,
        eval_mode: bool = False,
        thread_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Process a user question through the complete agent pipeline.

        Args:
            question: Natural language question.
            eval_mode: When True, skips the LLM NL-formatting step (saves 1 API
                       call per question). Useful for automated evaluation runs.
            thread_id: Optional thread/user identifier for interface parity.

        Returns:
            Dict containing execution results and answer string.
        """
        start_time = time.perf_counter()
        set_current_user(thread_id)
        question = question.strip()

        if not question:
            return {
                "question": question,
                "tool_name": "",
                "parameters": {},
                "tool_result": None,
                "sql": "",
                "answer": "Please provide a valid question.",
                "execution_time_ms": 0.0,
                "success": False,
                "error": "Empty question provided.",
            }

        # 1. Layer 1 — Fast keyword pre-filter (0 LLM calls)
        guard_response = check_conversational_guard(question, start_time)
        if guard_response is not None:
            return guard_response

        # 2. Tool Routing (1 LLM call)
        tool_name, params = route_question(question, self.tools, self.llm)
        logger.log_tool_call(tool_name, params)

        tool = self.tools.get(tool_name)
        if not tool:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return {
                "question": question,
                "tool_name": tool_name,
                "parameters": params,
                "tool_result": None,
                "sql": "",
                "answer": f"Error: Tool '{tool_name}' is not registered.",
                "execution_time_ms": elapsed_ms,
                "success": False,
                "error": f"Tool '{tool_name}' not found.",
            }

        # Ensure parameters are well-formed for the target tool
        if tool_name in {"sql_query", "hybrid_exposure_tool"}:
            params.pop("query", None)
            params.pop("sql", None)
            params.pop("prebuilt_sql", None)
            if "question" not in params or not params["question"]:
                params["question"] = question
        elif tool_name == "exposure_calculator":
            p_val = str(params.get("portfolio_name") or params.get("portfolio_id") or "").strip()
            resolved = extract_portfolio_name(p_val) if p_val else ""
            if not resolved or resolved == p_val:
                resolved_from_q = extract_portfolio_name(question)
                if resolved_from_q and resolved_from_q != question:
                    resolved = resolved_from_q
            params["portfolio_name"] = resolved if resolved else (p_val or question)

        # 3. Execute Tool
        tool_output = tool.run(**params)
        success = tool_output.get("success", False)
        raw_result = tool_output.get("result")
        error = tool_output.get("error", "")

        # 4. Format Answer
        if not success:
            answer = error if error else "An error occurred while processing your request."
        else:
            if tool_name == "conversational":
                answer = tool_output.get("answer", "I can only help with portfolio data questions.")
            elif tool_name in {"exposure_calculator", "hybrid_exposure_tool"}:
                answer = format_exposure_output(raw_result)
            elif tool_name == "sql_query":
                if eval_mode:
                    rows = raw_result or []
                    answer = f"{len(rows)} row(s) returned." if rows else "No results."
                else:
                    answer = format_sql_output(question, raw_result, self.llm, use_llm = True)
            else:
                answer = str(raw_result)

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(f"[AGENT:ANSWER] {answer.strip()}")
        logger.info(f"[AGENT] Completed question in {elapsed_ms:.2f}ms (Success={success})")

        return {
            "question": question,
            "tool_name": tool_name,
            "parameters": params,
            "tool_result": raw_result,
            "sql": tool_output.get("sql", ""),
            "answer": answer,
            "execution_time_ms": elapsed_ms,
            "success": success,
            "error": error,
        }

    def answer(self, question: str) -> str:
        """
        Convenience method for CLI and simple callers.

        Args:
            question: Natural language question.

        Returns:
            Human-readable response string.
        """
        response = self.run(question)
        return response["answer"]

    def answer_question(self, question: str) -> str:
        """Alias for answer() to match specification requirements."""
        return self.answer(question)
