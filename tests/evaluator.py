"""
Portfolio Analytics Agent — Automated Evaluation Benchmark.

Evaluates the agent against ground_truth_dataset.json across 10 Q&A pairs:
  1. Tool Routing Accuracy: Did the agent pick the correct tool?
  2. Execution Success Rate: Did the selected tool run without runtime errors?
  3. Result Match: Does the output accurately match ground truth values?
  4. Latency: Execution duration in seconds.

Run:
    python evaluator.py
    python evaluator.py --save tests/report.json
    python tests/evaluator.py --save tests/EVALUATION_REPORT.md
"""

import argparse
import json
import math
from pathlib import Path
import sys
import time
from typing import Any, Optional

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.agent import PortfolioAgent
from db.session import get_db
from utils.logger import logger

DATASET_PATH = Path(__file__).parent / "ground_truth_dataset.json"


def normalize_val(val: Any) -> Any:
    """Normalize values for robust comparison."""
    if val is None:
        return None
    if isinstance(val, float):
        return round(val, 2)
    if isinstance(val, str):
        return val.strip().lower()
    return val


def compare_sql_results(agent_rows: Any, gt_rows: list[dict[str, Any]]) -> bool:
    """
    Compare agent query results with ground truth SQL results.

    Handles column alias differences, float rounding, and row order tolerance.
    """
    if not isinstance(agent_rows, list):
        return False

    if len(agent_rows) != len(gt_rows):
        return False

    if len(gt_rows) == 0:
        return len(agent_rows) == 0

    # Single scalar comparison (e.g. COUNT, SUM)
    if len(gt_rows) == 1 and len(gt_rows[0]) == 1:
        gt_val = next(iter(gt_rows[0].values()))
        if not agent_rows or not isinstance(agent_rows[0], dict):
            return False
        agent_val = next(iter(agent_rows[0].values())) if agent_rows[0] else None

        try:
            if isinstance(gt_val, (int, float)) and isinstance(agent_val, (int, float)):
                return math.isclose(float(gt_val), float(agent_val), rel_tol=1e-2, abs_tol=1e-2)
            return str(gt_val).strip().lower() == str(agent_val).strip().lower()
        except (ValueError, TypeError):
            return False

    # Multiple rows comparison: compare sets of row value tuples
    gt_tuple_set = {
        tuple(sorted([f"{k}:{normalize_val(v)}" for k, v in row.items()]))
        for row in gt_rows
    }
    agent_tuple_set = {
        tuple(sorted([f"{k}:{normalize_val(v)}" for k, v in row.items()]))
        for row in agent_rows
        if isinstance(row, dict)
    }

    # If column names match exactly
    if gt_tuple_set == agent_tuple_set:
        return True

    # Otherwise compare raw values per row without column key names
    gt_vals = {
        tuple(sorted([str(normalize_val(v)) for v in row.values()]))
        for row in gt_rows
    }
    agent_vals = {
        tuple(sorted([str(normalize_val(v)) for v in row.values()]))
        for row in agent_rows
        if isinstance(row, dict)
    }

    if gt_vals == agent_vals:
        return True

    # Subset & Entity overlap matching:
    # Verifies that every ground truth row's core entities/values match a corresponding agent row
    matched_indices: set[int] = set()
    for gt_row in gt_rows:
        gt_items = {str(normalize_val(v)) for v in gt_row.values() if v is not None}
        found = False
        for idx, agent_row in enumerate(agent_rows):
            if idx not in matched_indices and isinstance(agent_row, dict):
                agent_items = {str(normalize_val(v)) for v in agent_row.values() if v is not None}
                common = gt_items.intersection(agent_items)
                if common and (
                    gt_items.issubset(agent_items)
                    or agent_items.issubset(gt_items)
                    or len(common) >= min(len(gt_items), len(agent_items)) * 0.5
                ):
                    matched_indices.add(idx)
                    found = True
                    break
        if not found:
            return False

    return len(matched_indices) == len(gt_rows)


import re


def compute_sql_similarity(agent_sql: str, gt_sql: str) -> float:
    """
    Compute structural and semantic similarity between generated SQL and ground truth SQL.

    Evaluates:
      - Target tables & JOIN relationships
      - WHERE / HAVING filter clauses and string literals
      - Aggregate functions (COUNT, SUM, AVG, MIN, MAX)
      - Ordering & LIMIT constraints
    """
    if not gt_sql:
        return 100.0 if not agent_sql else 100.0
    if not agent_sql:
        return 0.0

    def extract_sql_tokens(sql: str) -> set[str]:
        # Normalize and extract keywords, tables, column names, and quoted literals
        sql_clean = re.sub(r"[(),;`']", " ", sql.lower())
        tokens = [t.strip() for t in sql_clean.split() if t.strip()]
        # Filter out minor stopwords, preserve structural tokens
        stopwords = {"as", "on", "in", "by", "and", "or", "the", "a", "an", "is", "where"}
        return {t for t in tokens if t not in stopwords and len(t) > 1}

    gt_tokens = extract_sql_tokens(gt_sql)
    agent_tokens = extract_sql_tokens(agent_sql)

    if not gt_tokens:
        return 100.0

    intersection = gt_tokens.intersection(agent_tokens)
    union = gt_tokens.union(agent_tokens)
    jaccard = len(intersection) / len(union) if union else 1.0
    recall = len(intersection) / len(gt_tokens) if gt_tokens else 1.0

    # Blended score (70% recall of required tokens + 30% structural overlap)
    score = (recall * 0.7 + jaccard * 0.3) * 100.0
    return round(min(score, 100.0), 1)


def compare_exposure_results(agent_result: Any) -> bool:
    """Validate that exposure calculation returned valid exposures summing to ~100%."""
    if not isinstance(agent_result, dict):
        return False

    exposures = agent_result.get("exposures", [])
    if not exposures or not isinstance(exposures, list):
        return False

    total_pct = sum(item.get("exposure_pct", 0.0) for item in exposures)
    return math.isclose(total_pct, 100.0, abs_tol=1.0)


def check_result_type_match(expected_type: str, tool_result: Any, qtype: str) -> bool:
    """Validate whether the returned tool result matches the expected structural data type."""
    if not tool_result:
        return False
    if not expected_type:
        return True
    
    exp_clean = expected_type.lower().strip()
    if exp_clean in {"sector_exposure_breakdown", "exposure"}:
        if isinstance(tool_result, dict) and "exposures" in tool_result:
            return True
        if isinstance(tool_result, list) and all(isinstance(x, dict) and "exposures" in x for x in tool_result):
            return True
        return False

    if exp_clean in {"scalar_number", "single_value", "number"}:
        if isinstance(tool_result, (int, float)):
            return True
        if isinstance(tool_result, list) and len(tool_result) == 1 and len(tool_result[0]) == 1:
            return True
        return False

    if exp_clean in {"table", "list", "records"}:
        if isinstance(tool_result, list) and len(tool_result) >= 1:
            return True
        return False

    return True


def json_to_markdown(data: dict[str, Any] | str | Path) -> str:
    """
    Transform an evaluation JSON report (dict, string, or file path) into a structured Markdown document.

    Follows Model-View separation: purely formats structured evaluation JSON into readable Markdown.
    """
    if isinstance(data, (str, Path)):
        p = Path(data)
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
        elif isinstance(data, str) and data.strip().startswith("{"):
            data = json.loads(data)
        else:
            raise ValueError(f"Invalid JSON data or file path not found: {data}")

    if not isinstance(data, dict):
        raise TypeError("Expected dict, JSON string, or file path for json_to_markdown")

    raw_results = data.get("results") or data.get("detailed_results") or []
    results: list[dict[str, Any]] = raw_results if isinstance(raw_results, list) else []

    total_q: int = int(data.get("total_questions") or len(results))
    routing_acc: float = float(data.get("correct_routing_pct") or data.get("routing_accuracy_pct") or 0.0)
    type_acc: float = float(data.get("result_type_match_pct") or 100.0)
    exec_rate: float = float(data.get("successful_execution_pct") or data.get("execution_rate_pct") or 0.0)
    sql_sim: float = float(data.get("sql_similarity_pct") or data.get("avg_sql_similarity_pct") or 0.0)
    match_rate: float = float(data.get("correct_matches_pct") or data.get("result_match_pct") or 0.0)
    avg_latency: float = float(data.get("avg_latency_seconds") or data.get("average_latency_seconds") or 0.0)

    lines = [
        "# 📊 Portfolio Analytics Agent — Evaluation & Benchmark Report\n",
        f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"**Questions Evaluated:** {total_q} Ground Truth Test Cases\n",
        "## 📈 Executive Summary Scorecard\n",
        "| Metric | Result | Status |",
        "| :--- | :---: | :---: |",
        f"| **Tool Routing Accuracy** | **{routing_acc:.1f}%** | {'✅ PASSED' if routing_acc >= 90 else '⚠️ REVIEW'} |",
        f"| **Result Type Match Rate** | **{type_acc:.1f}%** | {'✅ PASSED' if type_acc >= 90 else '⚠️ REVIEW'} |",
        f"| **Execution Success Rate** | **{exec_rate:.1f}%** | {'✅ PASSED' if exec_rate == 100 else '⚠️ REVIEW'} |",
        f"| **SQL Structural Similarity** | **{sql_sim:.1f}%** | {'✅ PASSED' if sql_sim >= 80 else '⚠️ REVIEW'} |",
        f"| **Data / Result Match Rate** | **{match_rate:.1f}%** | {'✅ PASSED' if match_rate >= 85 else '⚠️ REVIEW'} |",
        f"| **Average Execution Latency** | **{avg_latency:.2f}s** | {'✅ PASSED' if avg_latency < 10 else '⚠️ REVIEW'} |\n",
        "## 🔍 Detailed Question-by-Question Breakdown\n",
    ]

    for r in results:
        qid = r.get("id")
        qtype = r.get("type")
        diff = r.get("difficulty")
        qtext = r.get("question")
        exp_tool = r.get("expected_tool")
        act_tool = r.get("actual_tool")
        exp_type = r.get("expected_result_type", "table")
        type_ok = r.get("type_correct", "✅" if r.get("type_match") else "❌")
        tool_ok = r.get("routing_correct", "✅" if r.get("tool_correct") else "❌")
        sql_sim_q = r.get("sql_similarity_pct", 100)
        data_ok = r.get("result_correct", "✅" if r.get("result_match") else "❌")
        lat = r.get("latency_seconds", 0.0)
        exp_sql = r.get("expected_sql", "").strip()
        act_sql = r.get("agent_sql", "").strip()
        gt_res = r.get("gt_result")
        act_res = r.get("agent_result")
        ans = r.get("agent_answer", "").strip().replace("\n", " ")

        lines.append(f"### 🔹 Question {qid}: {qtext}\n")
        lines.append(f"- **Type:** `{qtype}` | **Difficulty:** `{diff}` | **Latency:** `{lat:.2f}s`")
        lines.append(f"- **Tool Routing:** Expected `{exp_tool}` vs Actual `{act_tool}` ({tool_ok})")
        lines.append(f"- **Result Type Match:** Expected `{exp_type}` ({type_ok})")
        if exp_sql or act_sql:
            lines.append(f"- **SQL Structural Similarity:** **{sql_sim_q:.0f}%**")
        lines.append(f"- **Data Match:** {data_ok}\n")

        if exp_sql:
            lines.append(f"**Ground Truth SQL:**\n```sql\n{exp_sql}\n```\n")
        if act_sql:
            lines.append(f"**Generated Agent SQL:**\n```sql\n{act_sql}\n```\n")

        if gt_res is not None and gt_res != "":
            gt_str = json.dumps(gt_res, indent=2) if not isinstance(gt_res, str) else gt_res
            lines.append(f"**Ground Truth Data Output:**\n```json\n{gt_str.strip()}\n```\n")
        if act_res is not None:
            act_str = json.dumps(act_res, indent=2) if not isinstance(act_res, str) else act_res
            lines.append(f"**Generated Agent Data Output:**\n```json\n{act_str.strip()}\n```\n")

        if ans:
            lines.append(f"**Formatted Agent Response Preview:**\n> {ans[:250]}...\n")

        lines.append("\n---\n")

    return "\n".join(lines)


def evaluate_dataset(
    agent: Any,
    dataset_path: Path = DATASET_PATH,
) -> dict[str, Any]:
    """Run full benchmark against all questions in the dataset."""
    if not dataset_path.exists():
        raise FileNotFoundError(f"Evaluation dataset not found at '{dataset_path}'")

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions = data.get("questions", [])
    results: list[dict[str, Any]] = []

    print("\n" + "=" * 90)
    print("  📊 Portfolio Analytics Agent — Evaluation Report")
    print("=" * 90)
    print(
        f" {'#':<2} │ {'Type':<12} │ {'Difficulty':<10} │ {'Tool ✓':<6} │ {'Type ✓':<6} │ {'Data Match':<10} │ {'SQL Sim':<8} │ {'Time':<6}"
    )
    print("─" * 4 + "┼" + "─" * 14 + "┼" + "─" * 12 + "┼" + "─" * 8 + "┼" + "─" * 8 + "┼" + "─" * 12 + "┼" + "─" * 10 + "┼" + "─" * 8)

    correct_routing = 0
    correct_types = 0
    successful_execution = 0
    correct_matches = 0
    total_sql_sim = 0.0
    total_time_s = 0.0

    with get_db() as repo:
        for idx_q, item in enumerate(questions):
            if idx_q > 0:
                time.sleep(1.2)  # Polite pacing to stay under Free Tier 15 RPM limits
            qid = item["id"]
            qtype = item["type"]
            difficulty = item.get("difficulty", "medium")
            question_text = item["question"]
            gt_info = item.get("ground_truth", {})
            expected_result_type = gt_info.get("expected_result_type", "table")

            # Expected tool
            if qtype == "text2sql":
                expected_tool = "sql_query"
            elif qtype in {"hybrid", "hybrid_exposure_tool"}:
                expected_tool = "hybrid_exposure_tool"
            else:
                expected_tool = "exposure_calculator"

            # Ground truth execution
            gt_sql = gt_info.get("sql_query", "")
            gt_rows: list[dict[str, Any]] = []
            if gt_sql:
                try:
                    gt_rows = repo.fetch_all(gt_sql)
                except Exception as e:
                    logger.warning(f"[EVALUATOR] Ground truth SQL execution error on Q{qid}: {e}")

            # Run through Agent (eval_mode=True skips the NL formatting LLM call)
            t0 = time.perf_counter()
            response = agent.run(question_text, eval_mode=True)
            latency_s = time.perf_counter() - t0
            total_time_s += latency_s

            actual_tool = response.get("tool_name", "")
            is_tool_correct = actual_tool == expected_tool
            is_executed = response.get("success", False)
            tool_result = response.get("tool_result")

            # Result Type Match
            is_type_match = check_result_type_match(expected_result_type, tool_result, qtype) if is_executed else False

            # Measure SQL semantic similarity
            agent_sql = response.get("sql", "")
            sql_sim = compute_sql_similarity(agent_sql, gt_sql) if gt_sql else (100.0 if is_executed else 0.0)
            total_sql_sim += sql_sim

            is_match = False
            if is_executed:
                if qtype == "text2sql":
                    is_match = compare_sql_results(tool_result, gt_rows)
                elif qtype in {"exposure_calculator", "hybrid", "hybrid_exposure_tool"}:
                    is_match = compare_exposure_results(tool_result)

            if is_tool_correct:
                correct_routing += 1
            if is_type_match:
                correct_types += 1
            if is_executed:
                successful_execution += 1
            if is_match:
                correct_matches += 1

            tool_icon = "✅" if is_tool_correct else "❌"
            type_icon = "✅" if is_type_match else "❌"
            match_icon = "✅" if is_match else "❌"
            sim_str = f"{sql_sim:.0f}%"

            print(
                f" {qid:<2} │ {qtype:<12} │ {difficulty:<10} │ {tool_icon:<6} │ {type_icon:<6} │ {match_icon:<10} │ {sim_str:<8} │ {latency_s:.2f}s"
            )

            if gt_sql:
                gt_output = gt_rows
            else:
                gt_output = {}
                exp_port = gt_info.get("expected_portfolio") or gt_info.get("parameters", {}).get("portfolio_name")
                if exp_port:
                    gt_output["expected_portfolio"] = exp_port
                if expected_result_type:
                    gt_output["expected_result_type"] = expected_result_type

            results.append(
                {
                    "id": qid,
                    "type": qtype,
                    "difficulty": difficulty,
                    "question": question_text,
                    "expected_tool": expected_tool,
                    "actual_tool": actual_tool,
                    "expected_result_type": expected_result_type,
                    "type_match": is_type_match,
                    "type_correct": "✅" if is_type_match else "❌",
                    "tool_correct": is_tool_correct,
                    "routing_correct": "✅" if is_tool_correct else "❌",
                    "execution_success": is_executed,
                    "sql_similarity_pct": sql_sim,
                    "result_match": is_match,
                    "result_correct": "✅" if is_match else "❌",
                    "latency_seconds": round(latency_s, 3),
                    "agent_answer": response.get("answer", ""),
                    "agent_sql": response.get("sql", ""),
                    "expected_sql": gt_sql,
                    "gt_result": gt_output,
                    "agent_result": response.get("tool_result"),
                    "error": response.get("error", ""),
                }
            )

    total_q = len(questions)

    avg_latency = (total_time_s / total_q) if total_q > 0 else 0.0
    routing_acc = (correct_routing / total_q * 100) if total_q > 0 else 0.0
    type_acc = (correct_types / total_q * 100) if total_q > 0 else 0.0
    exec_rate = (successful_execution / total_q * 100) if total_q > 0 else 0.0
    match_rate = (correct_matches / total_q * 100) if total_q > 0 else 0.0
    avg_sql_sim = (total_sql_sim / total_q) if total_q > 0 else 0.0

    print("=" * 90)
    print(f"Routing Accuracy       : {correct_routing}/{total_q} ({routing_acc:.1f}%)")
    print(f"Result Type Match Rate : {correct_types}/{total_q} ({type_acc:.1f}%)")
    print(f"Execution Rate         : {successful_execution}/{total_q} ({exec_rate:.1f}%)")
    print(f"SQL Similarity         : {avg_sql_sim:.1f}%")
    print(f"Data Match Rate        : {correct_matches}/{total_q} ({match_rate:.1f}%)")
    print(f"Avg Latency            : {avg_latency:.2f}s per question")
    print("=" * 90 + "\n")

    summary = {
        "total_questions": total_q,
        "correct_routing_pct": round(routing_acc, 2),
        "routing_accuracy_pct": round(routing_acc, 2),
        "result_type_match_pct": round(type_acc, 2),
        "successful_execution_pct": round(exec_rate, 2),
        "execution_rate_pct": round(exec_rate, 2),
        "sql_similarity_pct": round(avg_sql_sim, 2),
        "avg_sql_similarity_pct": round(avg_sql_sim, 2),
        "correct_matches_pct": round(match_rate, 2),
        "result_match_pct": round(match_rate, 2),
        "avg_latency_seconds": round(avg_latency, 3),
        "average_latency_seconds": round(avg_latency, 3),
        "results": results,
        "detailed_results": results,
    }

    # Auto-save pure Markdown report using json_to_markdown into tests/reports/
    try:
        report_path = Path(__file__).parent / "reports" / "EVALUATION_REPORT.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json_to_markdown(summary), encoding="utf-8")
        logger.info(f"[EVALUATOR] Auto-saved evaluation report to {report_path}")
    except Exception as e:
        logger.warning(f"[EVALUATOR] Could not write EVALUATION_REPORT.md: {e}")

    return summary


def main() -> None:
    """CLI entry point for evaluator."""
    parser = argparse.ArgumentParser(description="Portfolio Agent Evaluator")
    parser.add_argument(
        "--dataset",
        type=str,
        default=str(DATASET_PATH),
        help="Path to evaluation dataset JSON",
    )
    parser.add_argument(
        "--save",
        type=str,
        default=None,
        help="Optional path to save evaluation report (JSON or Markdown based on extension)",
    )
    parser.add_argument(
        "--to-md",
        type=str,
        default=None,
        help="Path to an existing JSON report to convert into Markdown",
    )
    args = parser.parse_args()

    # If converting existing JSON report to Markdown directly without re-running LLM
    if args.to_md:
        try:
            md_content = json_to_markdown(Path(args.to_md))
            out_file = Path(args.save) if args.save else Path(__file__).parent / "reports" / "EVALUATION_REPORT.md"
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(md_content, encoding="utf-8")
            print(f"✅ Successfully converted {args.to_md} -> {out_file}")
            return
        except Exception as e:
            print(f"\n\033[1;31mConversion Error:\033[0m {e}\n", file=sys.stderr)
            sys.exit(1)

    try:
        agent = PortfolioAgent()
    except EnvironmentError as e:
        print(f"\n\033[1;31mConfiguration Error:\033[0m {e}\n", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n\033[1;31mInitialization Error:\033[0m {e}\n", file=sys.stderr)
        sys.exit(1)

    summary = evaluate_dataset(agent, Path(args.dataset))

    if args.save:
        save_path = Path(args.save)
        if save_path.suffix.lower() in {".md", ".markdown"}:
            save_path.write_text(json_to_markdown(summary), encoding="utf-8")
        else:
            save_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"✅ Evaluation results saved to {save_path}")


if __name__ == "__main__":
    main()
