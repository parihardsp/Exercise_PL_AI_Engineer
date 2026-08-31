"""Clarification prompt templates for ambiguous user queries."""

from typing import Optional


def clarification_prompt(question: str, candidate_options: list[str]) -> str:
    """
    Generate prompt for Gemini to craft a polite clarification question with candidate options.

    Args:
        question:          The ambiguous user question.
        candidate_options: List of portfolio names or options found in the database.
    """
    options_list = "\n".join([f"- {opt}" for opt in candidate_options])
    return f"""The user asked a portfolio analytics question that is ambiguous or missing the specific portfolio name.

User Question:
"{question}"

Available Portfolio Options in Database:
{options_list}

Instructions:
1. Explain politely that multiple portfolios exist or a specific portfolio name is needed.
2. Clearly list the available options as bullet points.
3. Ask the user which portfolio they would like to analyze.
4. Keep the response friendly, concise, and helpful.
"""
