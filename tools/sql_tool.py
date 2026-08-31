"""
SQL Query Tool — Text-to-SQL with self-correction.

Flow:
  1. On first call, load the DB schema into the system prompt (injected once)
  2. Gemini generates a SQL SELECT query from the natural language question
  3. Pre-execution validation: AST syntax tree check (sqlglot) + regex fallback
  4. Execute via Repository.fetch_all()
  5. On failure: feed the error back to Gemini, retry (max MAX_RETRIES times)
  6. Cache successful results so repeated questions skip the LLM entirely

The LLM only generates SQL here — it never executes it directly.
All execution goes through the Repository (parameterised, safe, read-only).
"""

import re
import time
from typing import Any

from core.llm import GeminiClient
from core.prompts import sql_correction_prompt, sql_system_prompt
from db.session import get_db
from tools.base import BaseTool
from utils.logger import logger

# Maximum number of self-correction retries before giving up
MAX_RETRIES = 2

# SQL keywords that must never appear in a generated query (fallback check)
_BLOCKED_KEYWORDS = {"DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE"}

try:
    import sqlglot
    import sqlglot.expressions as exp
    _HAS_SQLGLOT = True
except ImportError:
    _HAS_SQLGLOT = False


class SQLQueryTool(BaseTool):
    """
    Converts a natural language question into a SQL SELECT query and executes it.

    Use this tool when the user asks about:
      - Portfolio data: counts, totals, averages, comparisons
      - Holdings, transactions, securities, performance metrics
      - Risk metrics, historical prices, benchmark data
      - Any question answerable by querying the database tables

    Do NOT use this tool for sector exposure / sector breakdown questions
    — use the exposure_calculator tool for those.
    """

    name = "sql_query"
    description = (
        "Translates a natural language question into a SQL query and returns results "
        "from the portfolio database. Use for questions about portfolio data, holdings, "
        "transactions, securities, performance metrics, risk metrics, and any structured "
        "data lookups. Do not use for sector exposure calculations."
    )

    def __init__(self, llm: GeminiClient) -> None:
        """
        Args:
            llm: Shared GeminiClient instance. Injected so the agent
                 controls the client lifecycle (one client, multiple tools).
        """
        self._llm = llm
        self._cache: dict[str, list[dict[str, Any]]] = {}
        self._system_prompt: str = ""  # loaded lazily on first call

    def _load_schema(self) -> None:
        """Load schema from DB and build the system prompt (called once)."""
        with get_db() as repo:
            schema = repo.get_schema_string()
        self._system_prompt = sql_system_prompt(schema)
        logger.info("[SQLTool] Schema loaded into system prompt")

    def _validate_sql(self, sql: str) -> tuple[bool, str]:
        """
        Pre-execution safety check using AST Syntax Tree Compilation (sqlglot) + Regex.

        Returns:
            (True, "") if the query is safe to run.
            (False, reason) if the query is blocked.
        """
        if _HAS_SQLGLOT:
            try:
                # 1. Compile into formal SQLite AST
                ast = sqlglot.parse_one(sql, read="sqlite")
                if ast is None:
                    return False, "Failed to parse SQL into Abstract Syntax Tree."

                # 2. Root node must be a SELECT or UNION expression
                if not isinstance(ast, (exp.Select, exp.Union)) and not ast.find(exp.Select):
                    return False, f"SQL root node '{type(ast).__name__}' is not a read-only SELECT expression."

                # 3. Walk entire AST to ensure zero mutation sub-expressions
                forbidden_nodes = (
                    exp.Delete,
                    exp.Drop,
                    exp.Update,
                    exp.Insert,
                    exp.Alter,
                    exp.Command,
                    exp.Pragma,
                )
                for node_type in forbidden_nodes:
                    matched = ast.find(node_type)
                    if matched:
                        return False, f"Prohibited AST node '{node_type.__name__}' detected in query syntax tree."

                return True, ""
            except Exception as e:
                logger.warning(f"[SQLTool] AST parse warning ({e}). Falling back to strict regex verification.")

        # Fallback to strict regex validation
        upper = sql.upper()
        for keyword in _BLOCKED_KEYWORDS:
            # Word-boundary check so SELECT isn't blocked by ELECT etc.
            if re.search(rf"\b{keyword}\b", upper):
                return False, f"Blocked keyword '{keyword}' found in generated SQL."

        # Must start with SELECT or WITH (for CTE queries)
        stripped = sql.strip().upper()
        if not (stripped.startswith("SELECT") or stripped.startswith("WITH")):
            return False, "Generated SQL does not start with SELECT or WITH."

        return True, ""

    def _clean_sql(self, raw: str) -> str:
        """Strip markdown fences, preamble text, and normalize trailing semicolon."""
        # Remove ```sql ... ``` fences
        cleaned = re.sub(r"```(?:sql)?", "", raw, flags=re.IGNORECASE).strip()
        # Find query starting at SELECT or WITH (for CTE queries)
        match = re.search(r"((?:WITH|SELECT)\b.+?)(?:;|\Z)", cleaned, re.IGNORECASE | re.DOTALL)
        if match:
            cleaned = match.group(1).strip()
        return cleaned.rstrip(";").strip() + ";"

    
    def run(self, **kwargs: Any) -> dict[str, Any]:
        """
        Generate and execute a SQL query for the given question.

        Kwargs:
            question (str): The natural language question to answer.

        Returns:
            On success:
                {
                    "success": True,
                    "result": list[dict],   # rows returned by the query
                    "sql":    str,          # the SQL that was executed
                    "cached": bool,         # True if result came from cache
                    "error":  ""
                }
            On failure:
                {"success": False, "result": None, "sql": str, "cached": False, "error": str}
        """
        question: str = kwargs.get("question", "").strip()
        if not question:
            return {
                "success": False,
                "result": None,
                "sql": "",
                "cached": False,
                "error": "Missing required parameter: 'question'.",
            }

        # Return cached result for repeated questions
        if question in self._cache:
            logger.info(f"[SQLTool] Cache hit for: {question!r}")
            return {
                "success": True,
                "result": self._cache[question],
                "sql": "(cached)",
                "cached": True,
                "error": "",
            }

        # Lazy schema load on first call
        if not self._system_prompt:
            self._load_schema()

        logger.info(f"[SQLTool] Generating SQL for: {question!r}")

        sql = ""
        last_error = ""

        for attempt in range(1, MAX_RETRIES + 2):  # attempts: 1, 2, 3
            try:
                # Generate SQL with full schema context
                if attempt == 1:
                    raw_sql = self._llm.generate(
                        prompt=question,
                        system_prompt=self._system_prompt,
                        temperature=0.0,
                    )
                else:
                    # Self-correction: feed the previous failure back to Gemini
                    logger.log_self_correction(last_error, attempt - 1)
                    correction_prompt = sql_correction_prompt(question, sql, last_error)
                    raw_sql = self._llm.generate(
                        prompt=correction_prompt,
                        system_prompt=self._system_prompt,
                        temperature=0.0,
                    )

                sql = self._clean_sql(raw_sql)
                logger.info(f"[SQLTool] Generated SQL (attempt {attempt}): {sql}")

                # Validate query safety
                valid, reason = self._validate_sql(sql)
                if not valid:
                    last_error = reason
                    logger.warning(f"[SQLTool] Validation failed: {reason}")
                    continue  # retry with self-correction

                # Execute query against database
                t_exec_start = time.perf_counter()
                with get_db() as repo:
                    rows = repo.fetch_all(sql)
                exec_ms = (time.perf_counter() - t_exec_start) * 1000

                logger.log_sql_execution(sql, exec_ms)

                # Success — cache and return
                self._cache[question] = rows
                logger.info(f"[SQLTool] Query returned {len(rows)} rows in {exec_ms:.2f}ms")
                return {
                    "success": True,
                    "result": rows,
                    "sql": sql,
                    "cached": False,
                    "error": "",
                }

            except (RuntimeError, Exception) as e:
                last_error = str(e)
                logger.warning(f"[SQLTool] Execution failed (attempt {attempt}): {last_error}")
                # Loop continues → self-correction on next iteration

        # All retries exhausted
        logger.error(f"[SQLTool] Failed after {MAX_RETRIES + 1} attempts. Last error: {last_error}")
        return {
            "success": False,
            "result": None,
            "sql": sql,
            "cached": False,
            "error": f"Query failed after {MAX_RETRIES + 1} attempts. Last error: {last_error}",
        }
