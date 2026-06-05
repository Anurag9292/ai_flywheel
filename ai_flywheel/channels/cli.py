"""AI Flywheel CLI — command-line interface to the platform.

Every action that's possible in the web UI is possible via CLI.
Designed for scripting, batch operations, and CI/CD integration.
"""

import argparse
import asyncio
import json
import sys

from ai_flywheel.ventures.service import VentureService


def main():
    parser = argparse.ArgumentParser(
        description="AI Flywheel — Personal Venture Operating System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ai-flywheel venture create --name "Sales AI" --domain "sales-automation"
  ai-flywheel venture list
  ai-flywheel agent execute --agent-id abc123 --task "Research competitors" --venture-id xyz
  ai-flywheel thesis create --venture-id xyz --title "AI Sales Coach" --hypothesis "..."
  ai-flywheel cost report --venture-id xyz
        """,
    )
    subparsers = parser.add_subparsers(dest="command")

    # --- Venture commands ---
    venture_parser = subparsers.add_parser("venture", help="Manage ventures")
    venture_sub = venture_parser.add_subparsers(dest="action")

    create_p = venture_sub.add_parser("create", help="Create a venture")
    create_p.add_argument("--name", required=True)
    create_p.add_argument("--domain", required=True)

    venture_sub.add_parser("list", help="List ventures")

    get_p = venture_sub.add_parser("get", help="Get venture details")
    get_p.add_argument("id")

    archive_p = venture_sub.add_parser("archive", help="Archive a venture")
    archive_p.add_argument("id")

    # --- Health command ---
    subparsers.add_parser("health", help="Check platform health")

    # --- Agent commands ---
    agent_parser = subparsers.add_parser("agent", help="Manage agents")
    agent_sub = agent_parser.add_subparsers(dest="action")

    agent_list_p = agent_sub.add_parser("list", help="List agents")
    agent_list_p.add_argument("--venture-id", required=True)

    agent_create_p = agent_sub.add_parser("create", help="Create an agent")
    agent_create_p.add_argument("--venture-id", required=True)
    agent_create_p.add_argument("--name", required=True)
    agent_create_p.add_argument("--archetype", default="researcher")
    agent_create_p.add_argument("--model", default="gpt-4o-mini")
    agent_create_p.add_argument("--system-prompt", required=True)

    exec_p = agent_sub.add_parser("execute", help="Execute an agent")
    exec_p.add_argument("--agent-id", required=True)
    exec_p.add_argument("--task", required=True)
    exec_p.add_argument("--venture-id", required=True)

    # --- Thesis commands ---
    thesis_parser = subparsers.add_parser("thesis", help="Venture thesis management")
    thesis_sub = thesis_parser.add_subparsers(dest="action")

    thesis_list_p = thesis_sub.add_parser("list", help="List theses")
    thesis_list_p.add_argument("--venture-id", required=True)

    thesis_create_p = thesis_sub.add_parser("create", help="Create a thesis")
    thesis_create_p.add_argument("--venture-id", required=True)
    thesis_create_p.add_argument("--title", required=True)
    thesis_create_p.add_argument("--hypothesis", required=True)
    thesis_create_p.add_argument("--assumptions", nargs="*", default=[])
    thesis_create_p.add_argument("--kill-signals", nargs="*", default=[])

    thesis_evidence_p = thesis_sub.add_parser("evidence", help="Add evidence")
    thesis_evidence_p.add_argument("--venture-id", required=True)
    thesis_evidence_p.add_argument("--thesis-id", required=True)
    thesis_evidence_p.add_argument("--content", required=True)
    thesis_evidence_p.add_argument("--direction", choices=["supports", "contradicts", "neutral"], default="supports")
    thesis_evidence_p.add_argument("--strength", type=float, default=0.5)

    # --- Discovery commands ---
    disc_parser = subparsers.add_parser("discovery", help="Customer discovery")
    disc_sub = disc_parser.add_subparsers(dest="action")

    disc_list_p = disc_sub.add_parser("list", help="List discovery projects")
    disc_list_p.add_argument("--venture-id", required=True)

    disc_analyze_p = disc_sub.add_parser("analyze", help="Analyze interview transcript")
    disc_analyze_p.add_argument("--venture-id", required=True)
    disc_analyze_p.add_argument("--project-id", required=True)
    disc_analyze_p.add_argument("--transcript", required=True, help="Path to transcript file or text")

    # --- Cost commands ---
    cost_parser = subparsers.add_parser("cost", help="Cost tracking and optimization")
    cost_sub = cost_parser.add_subparsers(dest="action")

    cost_report_p = cost_sub.add_parser("report", help="Get cost report")
    cost_report_p.add_argument("--venture-id", required=True)

    cost_budget_p = cost_sub.add_parser("set-budget", help="Set monthly budget")
    cost_budget_p.add_argument("--venture-id", required=True)
    cost_budget_p.add_argument("--amount", type=float, required=True)

    # --- Market commands ---
    market_parser = subparsers.add_parser("market", help="Market intelligence")
    market_sub = market_parser.add_subparsers(dest="action")

    market_analyze_p = market_sub.add_parser("analyze", help="Analyze market signals")
    market_analyze_p.add_argument("--venture-id", required=True)
    market_analyze_p.add_argument("--domain", required=True)
    market_analyze_p.add_argument("--text", required=True, help="Text to analyze or file path")

    market_signals_p = market_sub.add_parser("signals", help="List detected signals")
    market_signals_p.add_argument("--venture-id", required=True)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    asyncio.run(_dispatch(args))


async def _dispatch(args):
    """Route CLI commands to actual service calls."""
    if args.command == "health":
        await _cmd_health()

    elif args.command == "venture":
        await _cmd_venture(args)

    elif args.command == "agent":
        await _cmd_agent(args)

    elif args.command == "thesis":
        await _cmd_thesis(args)

    elif args.command == "discovery":
        await _cmd_discovery(args)

    elif args.command == "cost":
        await _cmd_cost(args)

    elif args.command == "market":
        await _cmd_market(args)

    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        sys.exit(1)


async def _cmd_health():
    """Check platform connectivity."""
    from ai_flywheel.core.config import settings

    checks = {}
    # DB check
    try:
        from sqlalchemy import text
        async with get_global_session() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "connected"
    except Exception as e:
        checks["database"] = f"error: {e}"

    # Temporal check
    try:
        from temporalio.client import Client
        await Client.connect(settings.temporal_host, namespace=settings.temporal_namespace)
        checks["temporal"] = "connected"
    except Exception as e:
        checks["temporal"] = f"error: {type(e).__name__}"

    all_ok = all(v == "connected" for v in checks.values())
    _output({"status": "healthy" if all_ok else "degraded", **checks})


async def _cmd_venture(args):
    """Venture CRUD operations."""
    service = VentureService()

    if args.action == "create":
        result = await service.create_venture(name=args.name, domain=args.domain)
        _output({"id": result.id, "name": result.name, "domain": result.domain, "status": result.status})

    elif args.action == "list":
        ventures = await service.list_ventures()
        _output([{"id": v.id, "name": v.name, "domain": v.domain, "status": v.status} for v in ventures])

    elif args.action == "get":
        try:
            venture = await service.get_venture(args.id)
            _output({"id": venture.id, "name": venture.name, "domain": venture.domain, "status": venture.status})
        except ValueError as e:
            _error(str(e))

    elif args.action == "archive":
        await service.archive_venture(args.id)
        _output({"message": f"Venture {args.id} archived"})

    else:
        print("Usage: ai-flywheel venture {create|list|get|archive}", file=sys.stderr)


async def _cmd_agent(args):
    """Agent management operations."""
    from ai_flywheel.modules.agent_runtime.agent_factory.service import AgentFactory

    service = AgentFactory()

    if args.action == "list":
        agents = await service.list_agents(args.venture_id)
        _output([{"id": a.id, "name": a.name, "archetype": a.archetype, "model": a.model} for a in agents])

    elif args.action == "create":
        result = await service.create_agent(
            args.venture_id,
            {
                "name": args.name,
                "archetype": args.archetype,
                "model": args.model,
                "system_prompt": args.system_prompt,
            },
        )
        _output({"id": result.id, "name": result.name, "archetype": result.archetype})

    elif args.action == "execute":
        result = await service.execute(
            args.venture_id,
            {"agent_id": args.agent_id, "task": args.task},
        )
        _output(result)

    else:
        print("Usage: ai-flywheel agent {list|create|execute}", file=sys.stderr)


async def _cmd_thesis(args):
    """Venture thesis operations."""
    from ai_flywheel.modules.product_intelligence.venture_thesis.schemas import (
        AddEvidenceRequest,
        ThesisCreate,
    )
    from ai_flywheel.modules.product_intelligence.venture_thesis.service import VentureThesisEngine

    service = VentureThesisEngine()

    if args.action == "list":
        theses = await service.list_theses(args.venture_id)
        _output([
            {"id": t.id, "title": t.title, "status": t.status, "confidence": t.confidence}
            for t in theses
        ])

    elif args.action == "create":
        assumptions = [{"statement": a, "risk_level": "medium"} for a in args.assumptions]
        result = await service.create_thesis(
            args.venture_id,
            ThesisCreate(
                title=args.title,
                hypothesis=args.hypothesis,
                assumptions=assumptions,
                kill_signals=args.kill_signals,
            ),
        )
        _output({"id": result.id, "title": result.title, "confidence": result.confidence})

    elif args.action == "evidence":
        result = await service.add_evidence(
            args.venture_id,
            AddEvidenceRequest(
                thesis_id=args.thesis_id,
                source_type="observation",
                content=args.content,
                direction=args.direction,
                strength=args.strength,
            ),
        )
        _output({"id": result.id, "direction": result.direction, "strength": result.strength})

    else:
        print("Usage: ai-flywheel thesis {list|create|evidence}", file=sys.stderr)


async def _cmd_discovery(args):
    """Customer discovery operations."""
    from ai_flywheel.modules.product_intelligence.customer_discovery.schemas import TranscriptAnalysisRequest
    from ai_flywheel.modules.product_intelligence.customer_discovery.service import CustomerDiscoveryEngine

    service = CustomerDiscoveryEngine()

    if args.action == "list":
        projects = await service.list_projects(args.venture_id)
        _output([{"id": p.id, "name": p.name, "confidence_score": p.confidence_score} for p in projects])

    elif args.action == "analyze":
        # Read transcript from file or use as text
        import os
        text = args.transcript
        if os.path.isfile(text):
            with open(text) as f:
                text = f.read()

        request = TranscriptAnalysisRequest(
            project_id=args.project_id,
            interviewee_role="customer",
            transcript=text,
        )
        result = await service.analyze_transcript(args.venture_id, request)
        _output({
            "interview_id": result.interview_id,
            "sentiment": result.sentiment,
            "insights": [{"category": i.category, "finding": i.finding} for i in result.insights],
        })

    else:
        print("Usage: ai-flywheel discovery {list|analyze}", file=sys.stderr)


async def _cmd_cost(args):
    """Cost tracking operations."""
    from ai_flywheel.modules.experimentation.cost_optimizer.schemas import BudgetCreate
    from ai_flywheel.modules.experimentation.cost_optimizer.service import CostOptimizer

    service = CostOptimizer()

    if args.action == "report":
        report = await service.get_report(args.venture_id)
        _output(report)

    elif args.action == "set-budget":
        result = await service.set_budget(
            BudgetCreate(
                venture_id=args.venture_id,
                period_type="monthly",
                limit_usd=args.amount,
                alert_threshold_pct=0.8,
            )
        )
        _output(result)

    else:
        print("Usage: ai-flywheel cost {report|set-budget}", file=sys.stderr)


async def _cmd_market(args):
    """Market intelligence operations."""
    from ai_flywheel.modules.product_intelligence.market_intelligence.schemas import AnalyzeSignalsRequest
    from ai_flywheel.modules.product_intelligence.market_intelligence.service import MarketIntelligence

    service = MarketIntelligence()

    if args.action == "analyze":
        import os
        text = args.text
        if os.path.isfile(text):
            with open(text) as f:
                text = f.read()

        result = await service.analyze_signals(
            args.venture_id,
            AnalyzeSignalsRequest(
                venture_id=args.venture_id,
                domain=args.domain,
                signals_text=text,
            ),
        )
        _output({"signals": len(result.signals), "summary": result.summary, "patterns": result.patterns})

    elif args.action == "signals":
        signals = await service.get_signals(args.venture_id)
        _output([{"id": s.id, "type": s.signal_type, "title": s.title, "relevance": s.relevance_score} for s in signals])

    else:
        print("Usage: ai-flywheel market {analyze|signals}", file=sys.stderr)


def _output(data):
    """Print JSON output."""
    print(json.dumps(data, indent=2, default=str))


def _error(message: str):
    """Print error and exit."""
    print(json.dumps({"error": message}), file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
