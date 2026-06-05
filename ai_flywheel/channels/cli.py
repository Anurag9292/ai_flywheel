"""AI Flywheel CLI — command-line interface to the platform."""

import argparse
import asyncio
import json
import sys


def main():
    parser = argparse.ArgumentParser(description="AI Flywheel — Personal Venture OS")
    subparsers = parser.add_subparsers(dest="command")

    # venture commands
    venture_parser = subparsers.add_parser("venture", help="Manage ventures")
    venture_sub = venture_parser.add_subparsers(dest="action")

    create_p = venture_sub.add_parser("create", help="Create a venture")
    create_p.add_argument("--name", required=True)
    create_p.add_argument("--domain", required=True)

    venture_sub.add_parser("list", help="List ventures")

    get_p = venture_sub.add_parser("get", help="Get venture details")
    get_p.add_argument("id")

    # health command
    subparsers.add_parser("health", help="Check platform health")

    # agent commands
    agent_parser = subparsers.add_parser("agent", help="Manage agents")
    agent_sub = agent_parser.add_subparsers(dest="action")

    agent_sub.add_parser("list", help="List agents")

    exec_p = agent_sub.add_parser("execute", help="Execute an agent")
    exec_p.add_argument("--agent-id", required=True)
    exec_p.add_argument("--task", required=True)
    exec_p.add_argument("--venture-id", required=True)

    # cost command
    cost_parser = subparsers.add_parser("cost", help="Cost reports")
    cost_sub = cost_parser.add_subparsers(dest="action")
    cost_report_p = cost_sub.add_parser("report", help="Get cost report")
    cost_report_p.add_argument("--venture-id", required=True)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Dispatch
    asyncio.run(_dispatch(args))


async def _dispatch(args):
    """Route CLI commands to service calls."""
    if args.command == "health":
        print(json.dumps({"status": "healthy", "message": "AI Flywheel is running"}, indent=2))

    elif args.command == "venture":
        if args.action == "create":
            msg = f"Would create venture: {args.name} ({args.domain})"
            print(json.dumps({"status": "ok", "message": msg}))
        elif args.action == "list":
            print(
                json.dumps({"status": "ok", "message": "Would list ventures (needs DB connection)"})
            )
        elif args.action == "get":
            print(json.dumps({"status": "ok", "message": f"Would get venture: {args.id}"}))
        else:
            print("Usage: ai-flywheel venture {create|list|get}")

    elif args.command == "agent":
        if args.action == "execute":
            print(
                json.dumps(
                    {
                        "status": "ok",
                        "message": f"Would execute agent {args.agent_id} with task: {args.task}",
                    }
                )
            )
        elif args.action == "list":
            print(
                json.dumps({"status": "ok", "message": "Would list agents (needs DB connection)"})
            )
        else:
            print("Usage: ai-flywheel agent {list|execute}")

    elif args.command == "cost":
        if args.action == "report":
            print(
                json.dumps(
                    {
                        "status": "ok",
                        "message": f"Would get cost report for venture: {args.venture_id}",
                    }
                )
            )
        else:
            print("Usage: ai-flywheel cost {report}")

    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
