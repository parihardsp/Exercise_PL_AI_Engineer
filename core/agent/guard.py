"""
Centralized Input Guardrails — Fast deterministic pre-filter (Zero LLM calls).

Evaluates user queries against 4 centralized security & policy guardrails in < 0.1ms:
  1. Conversational Guard:   Greetings, thanks, farewells
  2. Read-Only Policy Guard: Mutation & write operations (INSERT, DROP, DELETE, UPDATE)
  3. Scope & Quality Guard:  Empty inputs, single-word placeholders, or gibberish
  4. Safety & Injection:     Jailbreaks and prompt injection attempts
"""

import re
import time
from typing import Any, Optional


# 1. Conversational Tokens
_GREETING_TOKENS: frozenset[str] = frozenset({
    "hi", "hello", "hey", "howdy", "greetings", "sup", "yo", "good morning", "good evening", "good afternoon"
})
_FAREWELL_TOKENS: frozenset[str] = frozenset({
    "bye", "goodbye", "goodnight", "see you", "ciao", "later", "farewell", "quit", "exit", "tata", "adios"
})
_THANKS_TOKENS: frozenset[str] = frozenset({
    "thanks", "thank you", "thank", "thx", "cheers", "appreciated", "well done", "great job"
})
_FILLER_TOKENS: frozenset[str] = frozenset({
    "there", "you", "ya", "mate", "man", "everyone", "all", "assistant", "bot"
})
_ALL_CONV_TOKENS: frozenset[str] = (
    _GREETING_TOKENS | _FAREWELL_TOKENS | _THANKS_TOKENS | _FILLER_TOKENS
)

# 2. Read-Only & Mutation Blocklist
_MUTATION_VERBS: frozenset[str] = frozenset({
    "insert", "delete", "drop", "update", "truncate", "alter", "create",
    "upsert", "modify", "remove", "add record", "insert into"
})

# 3. Scope / Ambiguous Single-Word Placeholders
_VAGUE_SINGLE_TOKENS: frozenset[str] = frozenset({
    "test", "asdf", "run", "query", "sql", "data", "abc", "help me", "try"
})

# Maximum allowed query length for security/safety
MAX_QUERY_LENGTH: int = 500

# 4. Prompt Injection, Embedded SQL Mutations & Meta-Prompt Patterns
_INJECTION_PATTERNS: tuple[str, ...] = (
    # Direct jailbreaks & system prompt exfiltration
    r"\bignore (all )?(previous|prior) (instructions|prompts|rules)\b",
    r"\bdisregard (all )?(previous|prior) (instructions|rules)\b",
    r"\breveal (your |the )?(system prompt|instructions|secret key)\b",
    r"\byou are now in (developer|dan|jailbreak) mode\b",
    r"\bbypass (all )?(guardrails|safety filters)\b",
    r"\bshow (me )?(the )?(hidden )?system prompt\b",
    # Meta-instructions requesting raw code generation or direct SQL writing
    r"\b(write|generate|give\s+me|create|provide)\s+(a\s+)?(sqlite|sql|python|code)\s+(query|script|select|statement|syntax)\b",
    r"\b(write|generate|give\s+me|create|provide)\s+(a\s+)?(select\s+(\*|\w+)\s+from)\b",
    r"\b(show|give|display|print)\s+(me\s+)?(the\s+)?(sql|sqlite)\s+(query|code|syntax|statement)\b",

    # Embedded SQL mutation commands (requires SQL statement structure)
    r"\bdelete\s+from\s+\w+\b",
    r"\bdelete\s+(\*|\w+)\s+(from|where)\b",
    r"\bdrop\s+(table|database|view|index)\b",
    r"\btruncate\s+(table\s+)?\w+\b",
    r"\balter\s+table\s+\w+\b",
    r"\binsert\s+into\s+\w+\b",
    r"\bupdate\s+\w+\s+set\s+\w+\b",

    # SQL injection syntax fragments
    r"--\s*$",
    r"'\s*OR\s+'1'='1",
    r"\"\s*OR\s+\"1\"=\"1",
)


CANNED_HELP_RESPONSE: str = (
    "**Portfolio Analytics Assistant**\n\n"
    "I can query and analyze your portfolio database in real time:\n"
    "- **Portfolios & AUM:** *'How many portfolios in total?'* or *'Top 3 by AUM'*\n"
    "- **Holdings & Risk:** *'Top 5 holdings in Growth Equity Fund'* or *'High risk portfolios'*\n"
    "- **Sector Exposure:** *'Sector exposure for Balanced Fund'* (supports follow-ups)\n"
    "- **Hybrid Queries:** *'Sector exposure for our top performing fund?'*\n\n"
    "*Try asking one of the portfolio questions above.*"
)

READ_ONLY_RESPONSE: str = (
    "**[Read-Only Mode]**\n\n"
    "Database modifications (create, update, delete) are restricted.\n"
    "Please ask a read-only analytics question (e.g. *'What is the total AUM?'*)."
)

INJECTION_BLOCKED_RESPONSE: str = (
    "**[Security Alert]**\n\n"
    "Unsafe input pattern or SQL syntax detected.\n"
    "Please ask a natural language portfolio question (e.g. *'Show top 3 portfolios by AUM'*)."
)


def _build_guard_result(
    question: str,
    answer: str,
    start_time: float,
    reason: str = "out_of_scope",
) -> dict[str, Any]:
    """Helper to construct standard Agent response dict for blocked inputs."""
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    return {
        "question": question,
        "tool_name": "conversational",
        "parameters": {"message": question},
        "tool_result": reason,
        "sql": "",
        "answer": answer,
        "execution_time_ms": elapsed_ms,
        "success": True,
        "error": "",
    }


def check_conversational_guard(
    question: str,
    start_time: float,
) -> Optional[dict[str, Any]]:
    """
    Centralized Stage 1 Input Guardrail (Zero LLM calls).

    Evaluates user input against 4 deterministic security and scope filters.
    Returns an immediate canned response if triggered, or None if the query should
    proceed to Layer 2 LLM routing.

    Args:
        question: User input string.
        start_time: Performance counter timestamp from start of request.

    Returns:
        A response dict if matched, or None if valid.
    """
    if not question or not question.strip():
        return _build_guard_result(question, CANNED_HELP_RESPONSE, start_time, reason="empty_input")

    cleaned = question.strip()
    if len(cleaned) > MAX_QUERY_LENGTH:
        return _build_guard_result(
            question,
            f"Question is too long ({len(cleaned)} chars). Maximum allowed is {MAX_QUERY_LENGTH} chars.",
            start_time,
            reason="length_exceeded",
        )

    q_lower = cleaned.lower()
    q_clean = re.sub(r"[^\w\s]", "", q_lower).strip()
    q_tokens = set(q_clean.split())

    # 1. Safety & Prompt / SQL Injection Guard
    for pattern in _INJECTION_PATTERNS:
        if re.search(pattern, cleaned, flags=re.IGNORECASE):
            return _build_guard_result(question, INJECTION_BLOCKED_RESPONSE, start_time, reason="injection_blocked")

    # 2. Read-Only Policy Guard (Catches isolated mutation verbs or mutation commands)
    # E.g. "insert", "drop table", "delete from portfolios", "create table"
    if any(q_lower == verb or q_lower.startswith(f"{verb} ") for verb in _MUTATION_VERBS):
        return _build_guard_result(question, READ_ONLY_RESPONSE, start_time, reason="mutation_blocked")

    # 3. Conversational Guard (Greetings, thanks, farewells)
    if q_tokens and q_tokens.issubset(_ALL_CONV_TOKENS):
        return _build_guard_result(question, CANNED_HELP_RESPONSE, start_time, reason="conversational")

    # 4. Scope & Quality Guard (Single-word placeholder tokens)
    if len(q_tokens) == 1 and next(iter(q_tokens)) in _VAGUE_SINGLE_TOKENS:
        return _build_guard_result(question, CANNED_HELP_RESPONSE, start_time, reason="vague_input")

    return None
