"""
Hybrid Exposure Tool — Chained Tool for Multi-Step Portfolio Queries.

Solves hybrid questions that require both database querying and sector
math normalization in sequence:
  Step 1 (SQL): Find the portfolio matching a condition (e.g. 'highest AUM', 'best performance').
  Step 2 (Exposure): Calculate 100% normalized sector weights for the discovered portfolio.
"""

from typing import Any, Optional

from db.session import get_db
from tools.base import BaseTool
from tools.exposure_tool import ExposureCalculatorTool
from tools.sql_tool import SQLQueryTool
from utils.logger import logger


class HybridExposureTool(BaseTool):
    """
    Composite tool that chains SQL query lookup with normalized sector exposure calculation.

    Use when the user asks for sector exposures of a portfolio identified by a condition
    (e.g., 'fund with highest AUM', 'largest tech fund', 'portfolio with highest return').
    """

    name = "hybrid_exposure_tool"
    description = (
        "Use when the user asks for the sector exposure, breakdown, or allocation "
        "of a portfolio that must first be identified by a condition, ranking, or filter "
        "(e.g. 'sector exposure of the fund with highest AUM', 'breakdown of the top performing fund'). "
        "Chains database lookup to find the portfolio, then calculates exact normalized sector exposures."
    )

    def __init__(
        self,
        sql_tool: Optional[SQLQueryTool] = None,
        exposure_tool: Optional[ExposureCalculatorTool] = None,
    ) -> None:
        if sql_tool is None:
            from core.llm import GeminiClient
            sql_tool = SQLQueryTool(GeminiClient())
        self.sql_tool = sql_tool
        self.exposure_tool = exposure_tool if exposure_tool is not None else ExposureCalculatorTool()

    def run(self, **kwargs: Any) -> dict[str, Any]:
        """
        Execute the 2-step hybrid query chain.

        Args:
            question: The user's hybrid natural language question.

        Returns:
            Dict containing:
              - success: bool
              - result: dict with portfolio_name, sql, and normalized exposures
              - sql: SQL query executed in Step 1
              - error: str if failed
        """
        question = str(kwargs.get("question") or "").strip()
        logger.info(f"[HybridTool] Processing hybrid question: {question!r}")

        if not question:
            return {
                "success": False,
                "result": None,
                "sql": "",
                "error": "Missing required question parameter for hybrid tool.",
            }

        # Step 1: Resolve the target portfolio name(s) via SQL
        portfolio_lookup_prompt = (
            f"Identify the target portfolio(s) from the user's question: '{question}'.\n"
            f"Write a SQLite SELECT query that returns ONLY the 'portfolio_name' column of the matching portfolio(s).\n"
            f"Requirements:\n"
            f"1. Focus solely on finding the portfolio(s) based on the filter, ranking, or limit in the question.\n"
            f"2. Unless another metric is specified (like return or risk), 'top N portfolios' or 'largest portfolio' defaults to ranking by total AUM (ORDER BY total_aum DESC LIMIT N).\n"
            f"3. Do NOT compute sector exposures or join sector tables in this step; sector exposure is computed separately in Step 2."
        )
        sql_result = self.sql_tool.run(question=portfolio_lookup_prompt)

        if not sql_result.get("success") or not sql_result.get("result"):
            error_msg = sql_result.get("error") or "No matching portfolio found for the specified criteria."
            return {
                "success": False,
                "result": None,
                "sql": sql_result.get("sql", ""),
                "error": f"Failed to identify target portfolio: {error_msg}",
            }
        else:

            rows = sql_result["result"]
            executed_sql = sql_result.get("sql", "")
            target_portfolio_names = []
            if isinstance(rows, list):
                for row in rows:
                    if isinstance(row, dict):
                        name = (
                            row.get("portfolio_name")
                            or row.get("name")
                            or next(iter(row.values()), None)
                        )
                        if name:
                            target_portfolio_names.append(str(name))
                    elif isinstance(row, (str, int)):
                        target_portfolio_names.append(str(row))
            elif isinstance(rows, dict):
                name = rows.get("portfolio_name") or next(iter(rows.values()), None)
                if name:
                    target_portfolio_names.append(str(name))

        if not target_portfolio_names:
            return {
                "success": False,
                "result": None,
                "sql": executed_sql,
                "error": "No matching portfolios found from SQL resolution.",
            }

        logger.info(f"[HybridTool] Step 1 resolved {len(target_portfolio_names)} portfolio(s): {target_portfolio_names}")

        # Step 2: Calculate normalized sector exposure for all resolved portfolios
        if len(target_portfolio_names) == 1:
            target_name = target_portfolio_names[0]
            exposure_result = self.exposure_tool.run(portfolio_name=target_name)

            if not exposure_result.get("success"):
                return {
                    "success": False,
                    "result": None,
                    "sql": executed_sql,
                    "error": f"Exposure calculation failed for '{target_name}': {exposure_result.get('error')}",
                }

            calc_data = exposure_result.get("result", {})
            composite_result = {
                "portfolio_name": calc_data.get("portfolio_name", target_name),
                "exposures": calc_data.get("exposures", []),
                "total_equity_weight": calc_data.get("total_equity_weight", 1.0),
                "lookup_sql": executed_sql,
            }
        else:
            portfolio_results = []
            for name in target_portfolio_names:
                exp_res = self.exposure_tool.run(portfolio_name=name)
                if exp_res.get("success"):
                    c_data = exp_res.get("result", {})
                    portfolio_results.append({
                        "portfolio_name": c_data.get("portfolio_name", name),
                        "exposures": c_data.get("exposures", []),
                        "total_equity_weight": c_data.get("total_equity_weight", 1.0),
                    })
                else:
                    portfolio_results.append({
                        "portfolio_name": name,
                        "exposures": [],
                        "total_equity_weight": 0.0,
                        "error": exp_res.get("error", "No equity holdings found"),
                    })

            composite_result = {
                "portfolios": portfolio_results,
                "lookup_sql": executed_sql,
            }

        logger.info(
            f"[HybridTool] Successfully completed hybrid calculation for {len(target_portfolio_names)} portfolio(s)"
        )

        return {
            "success": True,
            "result": composite_result,
            "sql": executed_sql,
            "error": "",
        }
