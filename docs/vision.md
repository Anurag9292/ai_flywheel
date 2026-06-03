# AI Flywheel — Vision

**A Personal Venture Operating System.**

Not just an AI engineering platform. A system that answers: *What to build, for whom, why will they pay, and how to build it with agents that continuously improve.*

---

## 1. The Core Insight

Every AI-native startup needs the same building blocks — agents, tools, prompts, data pipelines, experiments. But more importantly, every venture needs to answer two questions *before* a single line of code is written:

1. **"Should this exist?"** — Is there real demand? Who has the pain? Will they pay?
2. **"What should the product experience be?"** — What does the user see, feel, do? What's the AI-native interaction model?

Existing tools (LangGraph, CrewAI, MLflow, etc.) only address the *build* phase. They assume you already know what to build. That assumption is where most ventures die.

AI Flywheel covers both sides:
- **Business Intelligence** — Customer discovery, hypothesis validation, market signals, offer design, product experience architecture.
- **Technical Execution** — Agents, ML, data pipelines, experiments, deployment, optimization.

One platform. Full lifecycle. From "I have a hunch" to "it's printing money and improving itself."

---

## 2. What This Is NOT

| It's NOT... | Why not |
|---|---|
| An AI agent framework (CrewAI, LangGraph, AutoGen) | Those are execution layers. They don't help you discover what agents to build or whether anyone wants them. |
| An ML platform (MLflow, Weights & Biases, SageMaker) | Those track models. They don't track whether the product those models serve has product-market fit. |
| A no-code builder (Bubble, Retool, FlutterFlow) | Those let you click together UIs. They don't think about positioning, pricing, or compounding intelligence. |
| A project management tool (Linear, Notion, Jira) | Those track human tasks. This orchestrates machine tasks with human judgment at critical junctures. |

**It IS:** A venture operating system that covers the full lifecycle:

```
Discover Opportunity → Validate Demand → Design Product → Build Agents →
Deploy → Learn → Compound → Launch Next Venture (faster)
```

---

## 3. The Super Founder Model

One person. Multiple startups. Shared infrastructure.

The traditional model: pick one idea, raise money, hire a team, spend years executing. The super founder model: build the engine once, then point it at different markets.

**The key differentiator from existing tools:** This covers the BUSINESS side alongside the TECHNICAL side.

| Business Side (the gap) | Technical Side (table stakes) |
|---|---|
| Customer discovery | Agent orchestration |
| Hypothesis validation | Prompt management |
| Kill signal detection | Model training |
| Offer design & positioning | Data pipelines |
| Product experience architecture | Experiment tracking |
| ICP definition & buying triggers | Deployment & scaling |
| Workflow → Agent translation | Cost optimization |

Most founders fail not because they can't build — but because they build the wrong thing, for the wrong person, with the wrong positioning. This platform makes "should I keep going?" as rigorous and measurable as "is the model accurate?"

---

## 4. The Execution Spine

Every action in the platform flows through the same spine. This is the heartbeat — the structure that makes everything traceable, measurable, and improvable.

```
Event → Task → Agent/Tool → Trace → Metric → Feedback → Experiment → Pattern
  │                                                                       │
  └───────────────────── feeds back ──────────────────────────────────────┘
```

| Stage | What Happens |
|---|---|
| **Event** | Something occurs (user action, scheduled trigger, external signal, agent output) |
| **Task** | Work unit is created with clear inputs, expected outputs, and success criteria |
| **Agent/Tool** | An agent or tool executes the task (with human review if policy requires) |
| **Trace** | Full execution trace is captured — inputs, outputs, latency, cost, decisions |
| **Metric** | Quantitative signal is emitted (accuracy, cost, latency, conversion, satisfaction) |
| **Feedback** | Human or automated judgment on quality (thumbs up/down, correction, rating) |
| **Experiment** | Metrics and feedback are aggregated into experiment results with statistical rigor |
| **Pattern** | Winning patterns are extracted, stored, and recommended for future use |

The spine is not optional. Every module, every agent, every workflow passes through it. This is how the system learns.

---

## 5. Two-Layer Architecture

### Layer 1: Shared Foundation (39 modules across 8 systems)

Venture-agnostic. Built once, used everywhere. Every module is independently testable, event-driven, and designed for composition. These are the building blocks that compound across ventures.

### Layer 2: Per-Venture Orchestrators

Domain-specific. Each venture composes Layer 1 modules with its own domain logic, domain knowledge, agent network, and workflows. A new venture is a new orchestrator — not a new codebase.

The ratio shifts over time:
- Venture 1: 100% new (you're building Layer 1)
- Venture 3: 30% new (domain logic + orchestration only)
- Venture 5: 15% new (mostly prompt engineering + domain config)

---

## 6. The 8 Systems

Layer 1's 39 modules are organized into 8 systems. Each system owns a coherent responsibility boundary.

### System 1: Core Kernel (6 modules)
The execution infrastructure. Config, identity, events, task queues, tracing, artifacts. Everything else builds on this.

### System 2: LLM & Agent Runtime (7 modules)
Intelligence execution. LLM routing, prompt management, agent orchestration, tools, memory, human review, and policy enforcement.

### System 3: Data & Knowledge (6 modules)
The knowledge foundation. Ingestion, quality, embeddings, knowledge graphs, labeling, and privacy controls.

### System 4: ML & Evaluation (5 modules)
Measurable learning. Features, model training, evaluation, synthetic data, and simulation.

### System 5: Product & Market Intelligence (6 modules)
**The biggest gap in existing tools — and the biggest reason ventures fail.** Market signals, customer discovery, venture thesis validation, offer design, product experience architecture, and workflow blueprinting. This is where "should this exist?" gets answered with evidence, not gut feel.

### System 6: Experimentation & Optimization (5 modules)
Flywheel acceleration. Experiment tracking, A/B testing, feedback collection, metrics registry, and cost optimization.

### System 7: Deployment & Reliability (2 modules)
Production operations. Packaging, deployment, canary releases, circuit breakers, health monitoring, incident response.

### System 8: Cross-Venture Learning (2 modules)
The compounding layer. Pattern library, meta-learning, velocity tracking, and system-level improvement. This is what makes venture 5 dramatically faster than venture 1.

*Full module breakdown in [architecture.md](./architecture.md).*

---

## 7. The Flywheel Effect

Each venture makes the platform better. Each platform improvement makes the next venture faster.

### How It Compounds

1. **Utils improve under real load** — Edge cases found in Venture 1 prevent failures in Venture 3.
2. **Patterns accumulate** — A customer discovery flow that worked for HR tech gets templated and adapted for fintech in hours.
3. **Experiments inform future ventures** — "Freemium doesn't convert for this ICP" becomes institutional knowledge, not a repeated mistake.
4. **Agent behaviors sharpen** — Agents that learned to handle objections in sales automation bring that skill to any domain.
5. **Evaluation benchmarks grow** — Each venture adds test cases and golden datasets to the shared evaluation library.

### The Math

| Venture | Validation Phase | Build Phase | Infrastructure Reuse |
|---|---|---|---|
| Venture 1 | 5 weeks | 6 weeks | 0% (building foundation) |
| Venture 2 | 3 weeks | 5 weeks | ~40% |
| Venture 3 | 2 weeks | 3 weeks | ~60% |
| Venture 4 | 1.5 weeks | 2.5 weeks | ~70% |
| Venture 5 | 1 week | 2 weeks | ~80% |

By venture 5, you're launching validated products in 3 weeks. The marginal cost of a new venture approaches the cost of writing prompts and domain configuration — which is exactly where founder judgment should concentrate.

---

## 8. Key Principles

### Everything Is Executable, Traceable, Measurable, Attributable, Replayable, Costed, and Versioned

No black boxes. Every decision has a trace. Every trace has a cost. Every cost has an attribution. Every attribution can be replayed. Every replay can be compared to alternatives.

### Cheapest Evidence First

Don't build what you haven't validated. The evidence ladder:
1. Desk research (free)
2. Customer conversations (time only)
3. Landing page + waitlist (hours)
4. Wizard-of-Oz prototype (days)
5. MVP with real agents (weeks)

Never skip a rung. The platform enforces this sequence.

### Kill Early, Kill Cheap

Explicit kill signals at every validation stage. If 8/10 discovery interviews reveal no pain, kill it. If the landing page converts at <2%, kill it. If CAC > 3x LTV projection, kill it. The system surfaces kill signals proactively — it doesn't let you fall in love with a dead idea.

### Modules Communicate via Events, Not Direct Calls

Loose coupling. Any module can react to any event. New modules can tap into existing data flows without modifying producers. Events are persisted, replayable, and form the audit trail.

### Human-in-the-Loop Is a Feature, Not a Limitation

Founder judgment on the 5% that matters. The system handles the 95% autonomously and surfaces the critical decisions — pricing strategy, brand positioning, kill/continue, ethical boundaries — to the human. Automation with oversight, not automation as replacement.

### Multi-Channel Interaction

Same brain, different interfaces:
- **Slack**: Reactive. Notifications, approvals, quick commands, status checks.
- **Web App**: Proactive. Deep work, visual tools, conversational co-pilot sidebar.
- **CLI**: Automation. Scripting, batch operations, CI/CD integration.

---

## 9. The Interaction Model

You talk to the platform through three channels. Each is optimized for different cognitive modes.

### Slack (Reactive)
- Approval requests ("Should I kill this hypothesis? Evidence score: 2/10")
- Status notifications ("Venture 3 experiment batch complete. 2 winners, 1 loser.")
- Quick commands ("/flywheel status venture:hr", "/flywheel cost last-7d")
- Alerts ("Cost spike: LLM spend 3x above budget. Auto-throttled. Review?")

### Web App (Proactive)
- Conversational co-pilot sidebar for deep exploration
- Visual dashboards: venture health, experiment results, funnel metrics
- Interactive tools: customer interview analyzer, offer positioning canvas, agent debugger
- Drag-and-drop workflow builder for agent pipelines

### CLI (Automation)
- Batch operations: run 50 experiments, process 1000 interviews, backfill embeddings
- Scripting: compose multi-step operations into repeatable scripts
- CI/CD integration: deploy agents, run eval suites, gate on quality thresholds
- Power-user shortcuts: everything the app can do, but faster for those who type

### The Conversation Router

All three channels share the same backend brain. The router decides:
- **Complexity**: Simple query → instant response. Complex analysis → async with notification on completion.
- **Urgency**: Kill signal detected → immediate Slack alert. Weekly summary → batched in app dashboard.
- **Context**: Conversation history persists across channels. Start a thought in Slack, continue it in the app.

---

## The North Star

A single founder launches a validated, revenue-generating, self-improving AI-native product every 3 weeks — with the confidence that comes from rigorous evidence, not hope. The platform doesn't just build faster. It *thinks* faster. It finds opportunities, validates them, designs products, builds agents, deploys them, and learns from the results — compounding advantage with every cycle.

That's not a framework. That's an unfair advantage.
