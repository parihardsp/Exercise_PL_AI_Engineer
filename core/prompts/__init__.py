"""Prompts package for Portfolio Analytics Agent.

Centralizes prompt definitions into specialized modules:
  - routing:    Agent tool selection prompts
  - sql:        SQL query generation & self-correction prompts
  - formatting: Natural language response synthesis prompts
"""

from core.prompts.clarification import clarification_prompt
from core.prompts.formatting import format_sql_results_prompt
from core.prompts.routing import agent_routing_prompt
from core.prompts.sql import sql_correction_prompt, sql_system_prompt

__all__ = [
    "agent_routing_prompt",
    "sql_system_prompt",
    "sql_correction_prompt",
    "format_sql_results_prompt",
    "clarification_prompt",
]

