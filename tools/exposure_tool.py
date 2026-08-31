"""
Sector Exposure Calculator Tool.

Deterministic calculation — no LLM involved.
Given a portfolio name, computes the weighted sector breakdown
for equity holdings only (Stocks), normalised to 100%.

Why equities only?
  Holdings table stores current_weight as share of the FULL portfolio,
  including bonds. When bonds are excluded, equity weights alone don't
  sum to 1.0, so they are re-normalised against the total equity weight.

Query path:
  portfolios → holdings → securities (asset_type='Stock') → sectors
"""

from typing import Any

from db.session import get_db
from tools.base import BaseTool
from utils.logger import logger


class ExposureCalculatorTool(BaseTool):
    """
    Calculates sector exposure percentages for a named portfolio.

    Use this tool when the user asks about:
      - Sector allocation / sector breakdown / sector weights
      - Exposure to a specific sector (e.g. "How much Technology exposure?")
      - Portfolio composition by industry

    Returns a sorted list of sectors with their exposure percentages.
    """

    name = "exposure_calculator"
    description = (
        "Calculates the sector exposure (percentage allocation) for a given portfolio. "
        "Analyses equity holdings only and shows what percentage of the equity portion "
        "is allocated to each sector (e.g. Technology 45%, Healthcare 20%). "
        "Use this for questions about sector breakdown, sector weights, or sector allocation."
    )

    # SQL: join holdings → securities (equities only) → sectors for one portfolio
    _EXPOSURE_SQL = """
        SELECT
            se.sector_name,
            SUM(h.current_weight) AS raw_weight
        FROM holdings h
        JOIN portfolios p  ON h.portfolio_id  = p.portfolio_id
        JOIN securities s  ON h.security_id   = s.security_id
        JOIN sectors se    ON s.sector_id      = se.sector_id
        WHERE
            p.portfolio_id = ?
            AND s.asset_type = 'Stock'
        GROUP BY
            se.sector_name
        ORDER BY
            raw_weight DESC;
    """

    _PORTFOLIO_CHECK_SQL = """
        SELECT portfolio_id, portfolio_name
        FROM portfolios
        WHERE LOWER(portfolio_name) = LOWER(?)
           OR LOWER(portfolio_name) LIKE LOWER(?)
           OR CAST(portfolio_id AS TEXT) = ?
        ORDER BY
            CASE WHEN LOWER(portfolio_name) = LOWER(?) THEN 0
                 WHEN LOWER(portfolio_name) LIKE LOWER(?) THEN 1
                 ELSE 2 END
        LIMIT 1;
    """

    def run(self, **kwargs: Any) -> dict[str, Any]:
        """
        Compute sector exposure for the given portfolio.

        Kwargs:
            portfolio_name (str): Name or ID of the portfolio (e.g. "Tech Innovation Fund", "international equity", or "7").

        Returns:
            On success:
                {
                    "success": True,
                    "result": {
                        "portfolio_name": str,
                        "exposures": [
                            {"sector": str, "exposure_pct": float},
                            ...  # sorted descending by exposure
                        ],
                        "total_equity_weight": float  # raw sum before normalisation
                    },
                    "error": ""
                }
            On failure:
                {"success": False, "result": None, "error": "<reason>"}
        """
        portfolio_input: str = str(
            kwargs.get("portfolio_name") or kwargs.get("portfolio_id") or ""
        ).strip()
        logger.info(f"[ExposureTool] Calculating exposure for: {portfolio_input!r}")

        if not portfolio_input:
            return {
                "success": False,
                "result": None,
                "error": "Missing required parameter: 'portfolio_name' or 'portfolio_id'.",
            }

        try:
            with get_db() as repo:
                # 1. Look up portfolio (case-insensitive and partial match support)
                portfolio = repo.fetch_one(
                    self._PORTFOLIO_CHECK_SQL,
                    (
                        portfolio_input,
                        f"%{portfolio_input}%",
                        portfolio_input,
                        portfolio_input,
                        f"%{portfolio_input}%",
                    ),
                )
                if portfolio is None:
                    return {
                        "success": False,
                        "result": None,
                        "error": (
                            f"Portfolio '{portfolio_input}' not found in database."
                        ),
                    }

                portfolio_id = portfolio["portfolio_id"]
                canonical_name = portfolio["portfolio_name"]

                # 2. Fetch raw sector weights (equity holdings only)
                rows = repo.fetch_all(self._EXPOSURE_SQL, (portfolio_id,))

            if not rows:
                return {
                    "success": False,
                    "result": None,
                    "error": (
                        f"No equity holdings found for '{canonical_name}'. "
                        "The portfolio may contain bonds only or have no holdings."
                    ),
                }

            # 3. Sum of all equity weights (< 1.0 if portfolio has bonds)
            total_equity_weight = sum(row["raw_weight"] for row in rows)

            if total_equity_weight == 0:
                return {
                    "success": False,
                    "result": None,
                    "error": f"Total equity weight is zero for '{canonical_name}'.",
                }

            # 4. Re-normalise each sector to 100% of the equity portion
            exposures = [
                {
                    "sector": row["sector_name"],
                    "exposure_pct": round(
                        (row["raw_weight"] / total_equity_weight) * 100, 2
                    ),
                }
                for row in rows
            ]

            logger.info(
                f"[ExposureTool] {len(exposures)} sectors found, "
                f"total equity weight: {total_equity_weight:.4f}"
            )

            return {
                "success": True,
                "result": {
                    "portfolio_name": canonical_name,
                    "exposures": exposures,
                    "total_equity_weight": round(total_equity_weight, 4),
                },
                "error": "",
            }

        except Exception as e:
            logger.error(f"[ExposureTool] Unexpected error: {e}")
            return {
                "success": False,
                "result": None,
                "error": f"Exposure calculation failed: {e}",
            }
