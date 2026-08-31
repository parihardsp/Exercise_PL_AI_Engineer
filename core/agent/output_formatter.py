"""
Output formatting and answer synthesis for the Portfolio Analytics Agent.

Provides multiple formatting strategies:
  1. format_exposure_output: Formats sector percentages into clean text tables (Pure Python).
  2. format_sql_output_python: Formats raw SQL rows into clean tables/lists (Pure Python, 0 LLM calls).
  3. format_sql_output_via_llm: Synthesizes SQL rows into conversational prose via Gemini.
  4. format_sql_output: Master router that selects between Python and LLM formatting.
"""

from typing import Any, Optional

from core.llm import GeminiClient
from core.prompts import format_sql_results_prompt
from utils.logger import logger


def format_exposure_output(result: Optional[dict[str, Any]]) -> str:
    """
    Format ExposureCalculatorTool or HybridExposureTool result as a clean text table.

    Args:
        result: Dictionary containing 'portfolio_name'/'exposures' or 'portfolios' list.

    Returns:
        Formatted multi-line string showing sector breakdown(s).
    """
    if not isinstance(result, dict):
        return "No exposure calculation results available."

    # Multi-portfolio case (e.g. top 3 portfolios)
    if "portfolios" in result and isinstance(result["portfolios"], list):
        port_list = result["portfolios"]
        if not port_list:
            return "No matching portfolios found."

        lines = []
        for p in port_list:
            p_name = p.get("portfolio_name", "Portfolio")
            exps = p.get("exposures", [])
            lines.append(f"**Sector Exposure for {p_name}** (Equities Only)")
            if not exps:
                lines.append(f"- *No equity sector holdings found.*")
            else:
                for item in exps:
                    sector = item.get("sector", "Unknown")
                    pct = item.get("exposure_pct", 0.0)
                    lines.append(f"- **{sector}** : {pct:.2f}%")
            lines.append("")

        return "\n".join(lines).strip()

    # Single portfolio case
    portfolio_name = result.get("portfolio_name", "Portfolio")
    exposures = result.get("exposures", [])

    if not exposures:
        return f"No equity sector exposures found for {portfolio_name}."

    logger.info(
        f"[FORMATTER] Formatting exposure table for '{portfolio_name}' "
        f"({len(exposures)} sectors) via Pure Python"
    )

    lines = [f"**Sector Exposure for {portfolio_name}** (Equities Only)\n"]
    for item in exposures:
        sector = item.get("sector", "Unknown")
        pct = item.get("exposure_pct", 0.0)
        lines.append(f"- **{sector}** : {pct:.2f}%")

    return "\n".join(lines)


def format_sql_output_python(rows: Optional[list[dict[str, Any]]]) -> str:
    """
    Format SQL query result rows into clean, human-readable text in Pure Python (0 LLM calls).

    Handles:
      - 0 rows: 'No matching records found in the database.'
      - 1 scalar value (e.g. COUNT, SUM): 'Result: <value>'
      - 1 column (e.g. list of names): Numbered list
      - Multiple columns: Structured markdown table with aligned columns

    Args:
        rows: List of row dictionaries returned by SQLite.

    Returns:
        Formatted plain-text response string.
    """
    if not isinstance(rows, list) or not rows:
        return "No matching records found in the database."

    logger.info(f"[FORMATTER] Formatting SQL output ({len(rows)} rows) via Pure Python table/list")

    # Case 1: Single scalar value (e.g. COUNT(*), SUM(total_aum), AVG(expense_ratio))
    if len(rows) == 1 and len(rows[0]) == 1:
        val = next(iter(rows[0].values()))
        if isinstance(val, float):
            return f"Result: {val:,.2f}"
        if isinstance(val, int):
            return f"Result: {val:,}"
        return f"Result: {val}"

    # Case 2: Single column list (e.g. list of portfolio names or security symbols)
    first_row = rows[0]
    if len(first_row) == 1:
        col_name = next(iter(first_row.keys()))
        output_lines = [f"Found {len(rows)} record(s):"]
        for i, row in enumerate(rows, 1):
            output_lines.append(f"  {i}. {row[col_name]}")
        return "\n".join(output_lines)

    # Case 3: Multi-column table
    output_lines = []
    for i, row in enumerate(rows, 1):
        row_str = " | ".join(f"{k}: {v}" for k, v in row.items())
        output_lines.append(f"  {i}. {row_str}")

    return "\n".join(output_lines)


def format_sql_output_via_llm(
    question: str,
    rows: Optional[list[dict[str, Any]]],
    llm: GeminiClient ) -> str:
    """
    Synthesize SQL query result rows into conversational natural language via Gemini.

    Falls back automatically to format_sql_output_python if the LLM call fails.

    Args:
        question: Original user question string.
        rows: List of row dicts from database.
        llm: GeminiClient instance.

    Returns:
        Conversational answer string.
    """
    if not isinstance(rows, list) or not rows:
        return "No matching records found in the database."

    logger.info(f"[FORMATTER] Synthesizing SQL output ({len(rows)} rows) into conversational prose via LLM...")

    try:
        prompt = format_sql_results_prompt(question, rows)
        formatted = llm.generate(prompt=prompt, temperature=0.2)
        if formatted:
            logger.info(f"[FORMATTER] LLM answer synthesized ({len(formatted)} chars)")
            return formatted
    except Exception as e:
        logger.warning(
            f"[AGENT] LLM result formatting failed: {e}. Falling back to Python formatting."
        )

    return format_sql_output_python(rows)


def format_sql_output(
    question: str,
    rows: Optional[list[dict[str, Any]]],
    llm: Optional[GeminiClient] = None,
    use_llm: bool = True,
) -> str:
    """
    Master entry point for SQL query result formatting.

    Args:
        question: Original user question.
        rows: Database row dicts.
        llm: Optional GeminiClient instance.
        use_llm: When True and LLM is provided, uses conversational LLM synthesis.
                 When False, uses fast 0-token Pure Python formatting.

    Returns:
        Formatted answer string.
    """
    if use_llm and llm is not None:
        return format_sql_output_via_llm(question, rows, llm)
    return format_sql_output_python(rows)
