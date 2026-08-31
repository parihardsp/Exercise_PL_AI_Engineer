"""
Asynchronous HTTP API Client for Portfolio Analytics Streamlit Dashboard.
"""

import asyncio
from typing import Any
import httpx


def run_async(coro: Any) -> Any:
    """Execute an async coroutine within Streamlit's execution lifecycle."""
    return asyncio.run(coro)


class AsyncAPIClient:
    """Asynchronous HTTP Client for Portfolio Analytics REST API."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def check_health(self) -> dict[str, Any]:
        """Check status of the backend API and database."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/v1/health")
                if res.status_code == 200:
                    return res.json()
        except Exception:
            pass
        return {"status": "offline", "database_connected": False}

    async def fetch_tools(self) -> list[dict[str, str]]:
        """Fetch list of registered agent tools."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/v1/tools")
                if res.status_code == 200:
                    return res.json().get("tools", [])
        except Exception:
            pass
        return []

    async def query(
        self,
        text: str,
        eval_mode: bool = False,
        session_id: str = "default_user",
    ) -> dict[str, Any]:
        """Dispatch natural language query to the backend agent."""
        try:
            async with httpx.AsyncClient(timeout=150.0) as client:
                res = await client.post(
                    f"{self.base_url}/api/v1/query",
                    json={"query": text, "eval_mode": eval_mode, "session_id": session_id},
                )
                if res.status_code == 200:
                    return res.json()
                return {
                    "success": False,
                    "answer": f"API Error ({res.status_code}): {res.text}",
                    "tool_name": "error",
                    "sql": "",
                    "execution_time_ms": 0.0,
                }
        except Exception as e:
            return {
                "success": False,
                "answer": f"Connection Error: {str(e)}",
                "tool_name": "error",
                "sql": "",
                "execution_time_ms": 0.0,
            }

    async def fetch_both_exposures(
        self, port_a: str, port_b: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Fetch exposure analytics for two portfolios concurrently in parallel."""
        return await asyncio.gather(
            self.query(f"What are the sector exposures for {port_a}?"),
            self.query(f"What are the sector exposures for {port_b}?"),
        )

    async def run_benchmark(self) -> dict[str, Any]:
        """Execute automated ground-truth benchmark suite."""
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                res = await client.post(f"{self.base_url}/api/v1/eval")
                if res.status_code == 200:
                    return res.json()
                return {"error": f"Benchmark failed ({res.status_code}): {res.text}"}
        except Exception as e:
            return {"error": f"Benchmark connection error: {str(e)}"}
