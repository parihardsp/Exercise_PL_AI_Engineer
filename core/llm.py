"""
Gemini API Client Wrapper — Powered by LangChain Google GenAI.

This module provides a unified interface to Google Gemini models.

Key Capabilities:
  1. Plain-Text Generation:
     - Free-form natural language and SQL text generation via generate().
  2. Native Structured Output:
     - Constrained decoding via generate_structured() enforcing Pydantic schemas.
  3. Automatic Observability:
     - Automatically streams traces to LangSmith when configured in .env.
"""

import time
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq


from utils.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GROQ_API_KEY,
    GROQ_MODEL,
    LLM_PROVIDER,
)
from utils.logger import logger


def _invoke_with_retry(llm_callable: Any, max_retries: int = 4, base_delay: float = 3.0) -> Any:
    """Execute LLM call with automated rate-limit backoff."""
    for attempt in range(1, max_retries + 1):
        try:
            return llm_callable()
        except Exception as e:
            err_str = str(e).lower()
            if (
                "429" in err_str
                or "resource_exhausted" in err_str
                or "quota" in err_str
                or "rate" in err_str
            ) and attempt < max_retries:
                sleep_time = base_delay * (1.8 ** (attempt - 1))
                logger.warning(
                    f"[LLM Rate Limit] Quota pause on attempt {attempt}/{max_retries}. "
                    f"Backing off for {sleep_time:.1f}s..."
                )
                time.sleep(sleep_time)
            else:
                raise


class GeminiClient:
    """
    Unified client wrapper around LangChain's ChatGoogleGenerativeAI / ChatGroq.

    Provides a clean interface for text generation and Pydantic structured outputs.
    """

    def __init__(
        self,
        api_key: str = "",
        model: str = "",
    ) -> None:
        """Initialize LLM client based directly on LLM_PROVIDER ('gemini' or 'groq')."""
        if LLM_PROVIDER == "groq":
            self._model = model or GROQ_MODEL
            self._llm = ChatGroq(
                model=self._model,
                groq_api_key=GROQ_API_KEY,
                temperature=0.0,
            )
            logger.info(f"[LLM] Groq client initialized — model: {self._model}")
        else:
            self._model = model or GEMINI_MODEL
            self._llm = ChatGoogleGenerativeAI(
                model=self._model,
                google_api_key=api_key or GEMINI_API_KEY,
                temperature=0.0,
            )
            logger.info(f"[LLM] Gemini client initialized — model: {self._model}")

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.0,
    ) -> str:
        """
        Send a prompt to the LLM and return the model's text response.

        Args:
            prompt: The question or instruction for the LLM.
            system_prompt: Optional background instruction (e.g. database schema).
            temperature: 0.0 for deterministic output.

        Returns:
            The plain text string returned by the LLM.
        """
        try:
            messages: list[BaseMessage] = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            messages.append(HumanMessage(content=prompt))

            llm_to_use = self._llm if temperature == 0.0 else self._llm.bind(temperature=temperature)
            response = _invoke_with_retry(lambda: llm_to_use.invoke(messages))

            # Extract clean string from response
            content = response.content
            if isinstance(content, str):
                text = content.strip()
            elif isinstance(content, list):
                text = "".join(
                    block.get("text", str(block)) if isinstance(block, dict) else getattr(block, "text", str(block))
                    for block in content
                ).strip()
            else:
                text = str(content).strip()

            if not text:
                raise RuntimeError("LLM returned an empty response.")

            logger.debug(f"[LLM] Response ({len(text)} chars): {text[:120]}...")
            return text

        except Exception as e:
            logger.error(f"[LLM] Generation failed: {e}")
            raise RuntimeError(f"LLM generation failed: {e}") from e

    def generate_structured(
        self,
        schema: Any,
        prompt: str,
        system_prompt: str = "",
    ) -> Any:
        """
        Send a prompt and enforce a Pydantic schema on the output.

        Args:
            schema: The Pydantic model class to enforce (e.g. ToolRoutingSchema).
            prompt: The question or routing instruction prompt.
            system_prompt: Optional background system instruction.

        Returns:
            A validated instance of the requested Pydantic schema.
        """
        try:
            messages: list[BaseMessage] = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            messages.append(HumanMessage(content=prompt))

            # Use json_mode for Groq so it parses the JSON content without 400 errors
            if LLM_PROVIDER == "groq":
                structured_model = self._llm.with_structured_output(schema, method="json_mode")
            else:
                # Gemini enforces output structure matching the Pydantic schema
                structured_model = self._llm.with_structured_output(schema)
            
            return _invoke_with_retry(lambda: structured_model.invoke(messages))

        except Exception as e:
            logger.error(f"[LLM] Structured generation failed: {e}")
            raise RuntimeError(f"Structured LLM call failed: {e}") from e
