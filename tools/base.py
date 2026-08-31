"""
Abstract base class for all agent tools.

Every tool the agent can call must inherit from BaseTool and implement:
  - name        : unique identifier Gemini uses to select this tool
  - description : natural language description Gemini reads for routing decisions
  - run()       : the actual execution logic

Adding a new tool = create a subclass, implement these three things,
register it in agent.py. Zero changes to the agent dispatcher required.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """
    Contract that all tools must satisfy.

    The agent builds a routing prompt by iterating over registered tools
    and reading each tool's name + description. Gemini then returns the
    chosen tool name and any parameters — the agent dispatches to run().

    Subclasses must define class-level attributes, not instance attributes,
    so the agent can inspect them before instantiating a tool.
    """

    #: Unique tool identifier. Gemini uses this exact string to select the tool.
    name: str

    #: Routing description. Tell Gemini *when* to use this tool, not *how* it works.
    #: Be specific: mention the kinds of questions it handles and what it returns.
    description: str

    @abstractmethod
    def run(self, **kwargs: Any) -> dict[str, Any]:
        """
        Execute the tool with the given parameters.

        Args:
            **kwargs: Tool-specific parameters. Each subclass documents
                      what parameters it expects.

        Returns:
            A dict with at minimum:
              - "success" (bool): whether execution completed without error
              - "result"  (Any):  the tool's output on success
              - "error"   (str):  error description on failure, empty string on success

        Raises:
            Never raises to the agent — all exceptions must be caught internally
            and returned as {"success": False, "error": "...", "result": None}.
        """
        ...

    def __repr__(self) -> str:
        return f"<Tool name={self.name!r}>"
