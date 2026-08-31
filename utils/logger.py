"""Structured logging system for Portfolio Analytics Agent.

Provides clean, standardized logging to both console and log files,
with lightweight helper methods for tracking agent reasoning, tool calls, and queries.
"""

from contextvars import ContextVar
import datetime
import logging
from logging.handlers import TimedRotatingFileHandler
import os
import sys
from pathlib import Path
from typing import Any, Optional

from utils.config import LOG_DIR, LOG_LEVEL_NAME

# Async & Thread-Isolated Context Variable for Active User/Session ID
current_user_context: ContextVar[str] = ContextVar("current_user_context", default="")


def set_current_user(user_id: Optional[str]) -> None:
    """Set the active user/session ID for the current coroutine or thread context."""
    clean_id = (user_id or "").strip()
    current_user_context.set(clean_id)


def get_current_user() -> str:
    """Retrieve the active user/session ID from the current context."""
    return current_user_context.get()


class UserContextFilter(logging.Filter):
    """Universal logging filter supporting user sessions, explicit System tasks, and clean defaults."""

    def filter(self, record: logging.LogRecord) -> bool:
        user_id = current_user_context.get()
        if user_id == "System":
            record.user_tag = "[User: System] "
        elif user_id:
            record.user_tag = f"[User: {user_id}] "
        else:
            record.user_tag = ""
        return True


class AgentLogger(logging.Logger):
    """Extended Logger providing clean helper methods for agent traceability."""

    def __init__(self, name: str, level: int = logging.INFO):
        super().__init__(name, level)

    def log_agent_thought(self, thought: str):
        """Log agent routing decision or reasoning step."""
        self.info(f"[AGENT] {thought}")

    def log_tool_call(self, tool_name: str, parameters: dict[str, Any]):
        """Log tool invocation and input arguments."""
        self.info(f"[TOOL: {tool_name}] Parameters: {parameters}")

    def log_sql_execution(self, query: str, execution_time_ms: Optional[float] = None):
        """Log executed SQL query and its latency."""
        time_info = f" ({execution_time_ms:.2f}ms)" if execution_time_ms is not None else ""
        self.info(f"[SQL{time_info}] {query}")

    def log_self_correction(self, error: str, retry_count: int):
        """Log self-correction retry trigger upon SQL failure."""
        self.warning(f"[RETRY #{retry_count}] Error encountered: {error} | Retrying with corrected query...")


def setup_logger(
    name: str = "portfolio_agent",
    log_level: Optional[int] = None,
    log_to_file: bool = True,
    log_dir: Optional[Path | str] = None,
) -> AgentLogger:
    """Configure and return a clean, standard AgentLogger instance with universal user tagging."""
    if log_level is None:
        log_level = getattr(logging, LOG_LEVEL_NAME, logging.INFO)

    if log_dir is None:
        log_dir = LOG_DIR

    logging.setLoggerClass(AgentLogger)
    logger: AgentLogger = logging.getLogger(name)  # type: ignore
    logger.setLevel(log_level)

    # Avoid duplicate handlers on re-initialization
    if logger.hasHandlers():
        logger.handlers.clear()

    user_filter = UserContextFilter()

    # Universal format: timestamp | LEVEL | [User: id] message
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(user_tag)s%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1. Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.addFilter(user_filter)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. Daily Rotating File Handler (Retains 7 days of history)
    if log_to_file:
        os.makedirs(str(log_dir), exist_ok=True)
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        file_path = os.path.join(str(log_dir), f"agent_{today_str}.log")

        file_handler = TimedRotatingFileHandler(
            filename=file_path,
            when="midnight",
            interval=1,
            backupCount=7,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.addFilter(user_filter)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# Default logger instance
logger = setup_logger()
