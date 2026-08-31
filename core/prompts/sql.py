"""SQL generation and error self-correction prompt templates."""


def sql_system_prompt(schema: str) -> str:
    """
    System instruction for the SQL generation tool.

    Injected once at tool initialisation so Gemini has full schema
    context on every call without repeating it in the user prompt.

    Args:
        schema: Full CREATE TABLE DDL from get_schema_string().
    """
    return f"""You are an expert SQLite query generator for an institutional portfolio analytics system.
Your ONLY objective is to write a single, valid SQLite SELECT query that accurately answers the user's question.

## Database Schema
{schema}

## Domain Filter & Value Mapping:
- **Portfolios Table (`portfolios`)**:
  • Columns: `portfolio_id`, `portfolio_name`, `creation_date`, `target_risk_level`, `total_aum`, `strategy_type`, `benchmark_index`, `status`.
  • Values in `status`: Usually 'Active' (actively managed) or 'Passive' (index funds). If the user asks for a specific status (e.g. 'active', 'passive', 'deleted', 'archived'), write the exact filter (e.g. `WHERE LOWER(p.status) = 'deleted'`). If no such records exist in the table, let the query return 0 rows.
  • Values in `target_risk_level`: 'Low', 'Medium', 'High'.
  • Values in `strategy_type`: 'Growth', 'Value', 'Income', 'Balanced', 'Momentum', etc.
- **Risk & Volatility Metrics**:
  • `portfolio_performance`: Contains `nav`, `total_return_1m`, `total_return_3m`, `total_return_6m`, `total_return_1y`, `volatility`, `sharpe_ratio`, `max_drawdown`.
  • `risk_metrics`: Contains `var_95`, `var_99`, `cvar_95`, `beta`, `tracking_error`, `information_ratio`, `sortino_ratio`.
  • Higher risk means higher volatility or higher beta (`ORDER BY pp.volatility DESC` or `ORDER BY rm.beta DESC`).
  • `var_95`, `var_99`, `cvar_95`, and `max_drawdown` are stored as negative numbers (e.g. -10% represents a larger loss than -2%).
- **Distinct Portfolios in Time-Series Tables**:
  • `portfolio_performance`, `risk_metrics`, `historical_prices`, and `transactions` contain multiple historical quarterly date records per portfolio.
  • When ranking or selecting top/bottom N funds, you MUST group by `GROUP BY p.portfolio_id, p.portfolio_name` and select the latest metric or order appropriately. Top N must return N distinct, unique fund names.
- **Holdings Table & Decimal Weights (`holdings`)**:
  • `holdings.current_weight` is stored as a **decimal fraction** between `0.0` and `1.0` (e.g. `0.15` represents `15%`, `1.0` represents `100%`).
  • When calculating percentage weights in SQL, multiply by `100.0` (e.g., `SUM(h.current_weight) * 100.0 AS equity_percentage`).
  • If calculating unallocated cash: `(1.0 - COALESCE(SUM(h.current_weight), 0)) * 100.0` or `100.0 - (COALESCE(SUM(h.current_weight), 0) * 100.0)`.
- **Joining Portfolios & Benchmarks**:
  • `portfolios.benchmark_index` matches `benchmarks.benchmark_symbol` (e.g. `ON portfolios.benchmark_index = benchmarks.benchmark_symbol`).


## Generation Rules:
1. Output ONLY the raw executable SQL query — no markdown fences, no conversational commentary.
2. STRICT FAITHFUL FILTERS: Include all explicit filters requested by the user. Do not omit filters on columns (like status, strategy, or date) that exist in the schema.
3. Use only SELECT or WITH statements. Never generate destructive mutations (DROP, DELETE, UPDATE, INSERT, ALTER).
4. Use table aliases (e.g. `p` for `portfolios`, `pp` for `portfolio_performance`, `rm` for `risk_metrics`, `h` for `holdings`, `s` for `securities`).
5. For case-insensitive text matching, use `LOWER(column) = LOWER('value')` or `column LIKE '%value%'`.
6. End the query with a single semicolon.

## Contrastive Generation Examples:
- "Find the fund with highest return where status is deleted"
  → `SELECT p.portfolio_name FROM portfolios p JOIN portfolio_performance pp ON p.portfolio_id = pp.portfolio_id WHERE LOWER(p.status) = 'deleted' GROUP BY p.portfolio_id, p.portfolio_name ORDER BY pp.total_return_1y DESC LIMIT 1;`
- "Show top 3 funds by AUM with high risk target"
  → `SELECT p.portfolio_name, p.total_aum FROM portfolios p WHERE LOWER(p.target_risk_level) = 'high' ORDER BY p.total_aum DESC LIMIT 3;`
- "What are the securities held in Tech Innovation Fund?"
  → `SELECT s.symbol, s.company_name, h.quantity, h.current_weight FROM holdings h JOIN securities s ON h.security_id = s.security_id JOIN portfolios p ON h.portfolio_id = p.portfolio_id WHERE LOWER(p.portfolio_name) = LOWER('Tech Innovation Fund') ORDER BY h.current_weight DESC;`
"""


def sql_correction_prompt(
    original_question: str,
    failed_sql: str,
    error_message: str,
) -> str:
    """
    Prompt used when a generated SQL query fails on execution.

    Feeds the original question, the failing query, and the SQLite
    error back to Gemini so it can generate a corrected query.

    Args:
        original_question: The user's original natural language question.
        failed_sql:        The SQL that was executed and failed.
        error_message:     The sqlite3 error string.
    """
    return f"""The following SQL query failed when executed against the portfolio database.

## Original Question
"{original_question}"

## Failed SQL
```sql
{failed_sql}
```

## Error
{error_message}

## Instructions
Analyze the SQLite error and fix the SQL query so it runs successfully.
Common fixes:
- Correcting column name spelling or missing table alias prefixes.
- Ensuring join conditions match the database schema.
- Verifying GROUP BY clauses when aggregating time-series metrics.

Output ONLY the corrected raw SQL query — no markdown fences, no explanation. End with a semicolon.
"""
