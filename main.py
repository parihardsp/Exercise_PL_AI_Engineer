"""
Portfolio Analytics Agent — Interactive CLI Entry Point.

Run:
    python main.py
    python main.py --query "How many portfolios do we have in total?"
"""

import argparse
import sys
from typing import Any

from core.agent import PortfolioAgent, StateGraphPortfolioAgent
from utils.logger import logger, set_current_user


def print_banner(engine: str = "python", user_id: str = "cli_user") -> None:
    """Print welcoming CLI banner."""
    engine_badge = "LangGraph StateGraph" if engine == "langgraph" else "Python Modular SDK"
    print("=" * 64)
    print(f"  📊 Portfolio Analytics Agent (Engine: {engine_badge})")
    print(f"  Active User Session: \033[1;33m{user_id}\033[0m")
    print("  Type your question below or 'exit' / 'quit' to close.")
    print("=" * 64)
    print("  Examples:")
    print("   • How many portfolios do we have in total?")
    print("   • What are the sector exposures for the Tech Innovation Fund?")
    print("   • Show me the top 5 holdings by cost basis in Growth Equity Fund")
    print("=" * 64)
    print()


def run_interactive(agent: Any, engine: str = "python", user_id: str = "cli_user") -> None:
    """Start interactive REPL loop with user session tracking."""
    print_banner(engine, user_id)

    while True:
        try:
            print("\033[1;34mYou:\033[0m ", end="", flush=True)
            user_input = input().strip()

            if not user_input:
                continue

            if user_input.lower() in {"exit", "quit", "q", ":q"}:
                print("\nGoodbye! 👋\n")
                break

            if user_input.lower() in {"help", "?"}:
                print_banner(engine, user_id)
                continue

            if user_input.lower() == "clear":
                print("\033[H\033[J", end="")
                print_banner(engine, user_id)
                continue

            print("\n\033[1;32mAgent:\033[0m Thinking...", end="\r", flush=True)

            # Set user context for universal logging
            set_current_user(user_id)

            # Process query through Centralized Agent Pipeline with thread isolation
            response = agent.run(user_input, thread_id=user_id)

            # Clear 'Thinking...' and print answer
            print(" " * 30, end="\r")
            print(f"\033[1;32mAgent:\033[0m {response['answer']}")
            print(
                f"\033[90m[User: {user_id} | Engine: {engine} | Tool: {response['tool_name']} | Latency: {response['execution_time_ms']:.1f}ms]\033[0m\n"
            )

        except (KeyboardInterrupt, EOFError):
            print("\n\nSession interrupted. Goodbye! 👋\n")
            break
        except Exception as e:
            logger.error(f"[CLI] Unexpected error: {e}")
            print(f"\n\033[1;31mError:\033[0m An unexpected error occurred: {e}\n")


def run_single(agent: Any, query: str, user_id: str = "cli_user") -> None:
    """Execute a single query from CLI flag and exit."""
    set_current_user(user_id)
    response = agent.run(query, thread_id=user_id)
    print(response["answer"])
    if not response["success"]:
        sys.exit(1)


def main() -> None:
    """Entry point for CLI execution."""
    parser = argparse.ArgumentParser(description="Portfolio Analytics AI Agent")
    parser.add_argument(
        "--query",
        "-q",
        type=str,
        help="Single question to run and return immediately",
        default=None,
    )
    parser.add_argument(
        "--engine",
        "-e",
        choices=["python", "langgraph"],
        default="python",
        help="Orchestrator engine: 'python' (default) or 'langgraph' (StateGraph)",
    )
    parser.add_argument(
        "--user",
        "-u",
        type=str,
        default="cli_user",
        help="User / session thread identifier for memory tracking (default: 'cli_user')",
    )
    args = parser.parse_args()

    try:
        if args.engine == "langgraph":
            agent = StateGraphPortfolioAgent()
        else:
            agent = PortfolioAgent()
    except EnvironmentError as e:
        print(f"\n\033[1;31mConfiguration Error:\033[0m {e}\n", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n\033[1;31mInitialization Error:\033[0m {e}\n", file=sys.stderr)
        sys.exit(1)

    if args.query:
        run_single(agent, args.query, user_id=args.user)
    else:
        run_interactive(agent, engine=args.engine, user_id=args.user)


if __name__ == "__main__":
    main()
