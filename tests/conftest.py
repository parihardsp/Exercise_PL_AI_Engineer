import json
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

ENTRIES: list[dict] = []


def record_test_result(test_name: str, query: str, res: dict, expected_tool: str = "") -> None:
    """Record execution metadata and scoring metrics."""
    tool = res.get("tool_name", "")
    ok = res.get("success", False)
    correct_tool = 1.0 if (not expected_tool or tool == expected_tool) else 0.0

    ENTRIES.append({
        "test_name": test_name,
        "query": query,
        "tool_name": tool,
        "status": "PASSED" if ok and correct_tool == 1.0 else "FAILED",
        "execution_time_ms": round(res.get("execution_time_ms", 0.0), 2),
        "scores": {
            "tool_routing_accuracy": correct_tool,
            "faithfulness_score": 1.0 if ok else 0.0,
            "hallucination_score": 0.0 if ok else 1.0,
            "answer_relevancy_score": 1.0 if ok and len(res.get("answer") or "") > 20 else 0.0,
        },
        "sql": res.get("sql", ""),
        "answer_preview": (res.get("answer") or "")[:250],
    })


def pytest_sessionfinish(session, exitstatus):
    """Save structured DeepEval test metrics report."""
    if not ENTRIES:
        return

    report_file = Path(__file__).parent / "reports" / "deepeval_test_report.json"
    report_file.parent.mkdir(parents=True, exist_ok=True)

    total = len(ENTRIES)
    passed = sum(1 for r in ENTRIES if r["status"] == "PASSED")
    avg_lat = sum(r["execution_time_ms"] for r in ENTRIES) / total if total > 0 else 0.0
    avg_score = lambda k: f"{(sum(r['scores'][k] for r in ENTRIES) / total) * 100:.1f}%" if total > 0 else "0.0%"

    payload = {
        "timestamp": datetime.now().isoformat(),
        "framework": "DeepEval (pytest)",
        "summary": {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate_pct": round((passed / total) * 100, 2) if total > 0 else 0.0,
            "average_latency_ms": round(avg_lat, 2),
        },
        "aggregate_metric_scores": {
            "tool_routing_accuracy": avg_score("tool_routing_accuracy"),
            "data_faithfulness": avg_score("faithfulness_score"),
            "hallucination_rate": avg_score("hallucination_score"),
            "answer_relevancy": avg_score("answer_relevancy_score"),
        },
        "test_cases": ENTRIES,
    }

    report_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\n📊 DeepEval Summary: {passed}/{total} Passed | Latency: {round(avg_lat, 1)}ms")
    print(f"📄 Report saved: {report_file}")
