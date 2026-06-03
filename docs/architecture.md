# AI Flywheel — Architecture

A personal venture operating system. Python + Next.js. 39 modules across 8 systems. Two layers: shared foundation + per-venture orchestration.

---

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        LAYER 2: VENTURE ORCHESTRATORS                            │
│                                                                                 │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│   │  Venture A   │  │  Venture B   │  │  Venture C   │  │  Venture N   │      │
│   │  (HR Tech)   │  │  (Sales AI)  │  │  (FinTech)   │  │  (Future)    │      │
│   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│          │                  │                  │                  │              │
└──────────┼──────────────────┼──────────────────┼──────────────────┼──────────────┘
           │                  │                  │                  │
           ▼                  ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        LAYER 1: SHARED FOUNDATION (39 modules)                  │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │ System 8: Cross-Venture Learning          [Pattern Library, Meta-Learn] │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────┐  ┌───────────────────────────────────────────┐    │
│  │ System 7: Deployment &  │  │ System 6: Experimentation & Optimization  │    │
│  │ Reliability [2 modules] │  │ [5 modules]                               │    │
│  └─────────────────────────┘  └───────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │ System 5: Product & Market Intelligence [6 modules] ← THE KEY ADDITION │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────┐  ┌──────────────────────────────────────┐    │
│  │ System 4: ML & Evaluation   │  │ System 3: Data & Knowledge           │    │
│  │ [5 modules]                 │  │ [6 modules]                           │    │
│  └──────────────────────────────┘  └──────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │ System 2: LLM & Agent Runtime [7 modules]                              │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │ System 1: Core Kernel [6 modules]                                      │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                 │
│  ═══════════════════════════════════════════════════════════════════════════     │
│  THE EXECUTION SPINE (runs through everything):                                 │
│  Event → Task → Agent/Tool → Trace → Metric → Feedback → Experiment → Pattern  │
│  ═══════════════════════════════════════════════════════════════════════════     │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
           │                  │                  │
           ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        INTERACTION LAYER                                         │
│                                                                                 │
│   ┌──────────┐        ┌──────────────┐        ┌──────────┐                     │
│   │  Slack   │◄──────►│ Conversation │◄──────►│ Web App  │                     │
│   │ (React)  │        │    Router    │        │ (Next.js)│                     │
│   └──────────┘        └──────┬───────┘        └──────────┘                     │
│                              │                                                  │
│                       ┌──────┴───────┐                                          │
│                       │     CLI      │                                          │
│                       └──────────────┘                                          │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. The Execution Spine

The spine is the foundation everything else builds on. It is not a module — it is the *protocol* that all modules follow. Every meaningful action in the platform traverses this path:

```
┌───────┐    ┌──────┐    ┌────────────┐    ┌───────┐    ┌────────┐    ┌──────────┐    ┌────────────┐    ┌─────────┐
│ Event │───►│ Task │───►│ Agent/Tool │───►│ Trace │───►│ Metric │───►│ Feedback │───►│ Experiment │───►│ Pattern │
└───────┘    └──────┘    └────────────┘    └───────┘    └────────┘    └──────────┘    └────────────┘    └────┬────┘
     ▲                                                                                                       │
     │                                                                                                       │
     └───────────────────────────── informs future events ───────────────────────────────────────────────────┘
```

### Why This Matters

Without the spine, you have disconnected tools. With it, you have a learning system.

| Stage | Responsibility | Key Guarantees |
|---|---|---|
| **Event** | Trigger. Something happened that requires attention. | Persisted, replayable, timestamped, attributed to source |
| **Task** | Work unit. Clear inputs, expected outputs, success criteria, deadline. | Queued, retriable, dependency-aware, cancelable |
| **Agent/Tool** | Execution. The actual work happens here — LLM call, API hit, computation. | Isolated, policy-gated, resource-bounded, interruptible |
| **Trace** | Record. Full execution history captured. | Immutable, structured, queryable, cost-attributed |
| **Metric** | Signal. Quantitative measure of what happened. | Typed, comparable, aggregatable, alertable |
| **Feedback** | Judgment. Human or automated assessment of quality. | Timestamped, attributed, weighted by source reliability |
| **Experiment** | Analysis. Statistical aggregation of metrics + feedback over time. | Rigorous, versioned, reproducible, decision-ready |
| **Pattern** | Knowledge. Extracted winning strategies for reuse. | Searchable, scored, context-tagged, recommended |

### Spine Guarantees

1. **Nothing executes without a trace** — If it ran, there's a record.
2. **Nothing is unmeasured** — Every execution emits at least one metric.
3. **Nothing is unopinionated** — Every metric eventually receives feedback (human or automated).
4. **Nothing is wasted** — Every experiment produces a pattern (even "this doesn't work" is a pattern).
5. **Nothing is siloed** — Patterns from one venture are discoverable by all ventures.

---

## 3. The 8 Systems (39 Modules)

---

### System 1: Core Kernel (6 modules)

The execution infrastructure. Everything else depends on this layer being rock-solid.

| # | Module | Responsibility |
|---|---|---|
| 1 | **Platform Core** | Configuration management, secrets handling, settings registry, service discovery, health endpoints. The boot sequence. |
| 2 | **Identity & Tenancy** | Users, ventures, permissions, API keys, data isolation between ventures, role-based access, session management. |
| 3 | **Event Bus** | Publish/subscribe messaging, event persistence, replay capabilities, wildcard subscriptions, dead letter queues, ordering guarantees. |
| 4 | **Task Runtime** | Work queues, task status tracking, automatic retries with backoff, dependency graphs, bulk execution, priority scheduling, timeout enforcement. |
| 5 | **Trace & Observability** | Distributed tracing across all modules, error classification and analysis, execution replay for debugging, performance profiling, cost attribution per trace. |
| 6 | **Artifact Manager** | Versioned storage of outputs (reports, model cards, datasets, configs), reproducibility links (artifact → trace → experiment), lifecycle management. |

---

### System 2: LLM & Agent Runtime (7 modules)

The intelligence execution layer. Where AI actually does work.

| # | Module | Responsibility |
|---|---|---|
| 7 | **LLM Gateway** | Multi-provider interface (OpenAI, Anthropic, Google, open-source), smart routing based on task type/cost/latency, response caching, automatic fallback on failure, per-call cost tracking, rate limit management. |
| 8 | **Prompt Studio** | Prompt versioning with diff tracking, composition (template + variables + few-shot), automated optimization (DSPy-style), analytics (which prompts perform best), template library with search, regression detection on prompt changes. |
| 9 | **Agent Factory & Orchestration** | Agent blueprints (define once, instantiate many), archetype library (researcher, writer, analyst, coder), execution modes (single-shot, ReAct, plan-and-execute), multi-agent coordination patterns (delegation, debate, consensus, pipeline, supervisor). |
| 10 | **Tool Forge** | Tool definitions with typed schemas, API integration framework, tool testing harness, composition (chain tools into workflows), discovery (agents find relevant tools), credential management per tool per venture. |
| 11 | **Memory Engine** | Working memory (current task context), episodic memory (past interactions, retrievable), semantic memory (facts, knowledge, searchable), procedural memory (learned skills, reusable), cross-agent shared memory (venture-scoped context accessible to all agents). |
| 12 | **Human Review Engine** | Review queues with priority and routing, approval workflows (single/multi-step), correction capture (human fixes → training signal), escalation rules (confidence < threshold → human), feedback capture integrated with the spine. |
| 13 | **Policy Engine** | Active constraints on agent behavior, rule definitions (what agents can/cannot do), safety boundaries (token limits, action restrictions, PII handling), compliance enforcement, audit logging of policy decisions. |

---

### System 3: Data & Knowledge (6 modules)

The knowledge foundation. Data in, structured knowledge out.

| # | Module | Responsibility |
|---|---|---|
| 14 | **Universal Ingestor** | Any format → structured data (PDF, CSV, JSON, HTML, audio, video, images), OCR pipeline, streaming + batch modes, schema detection, deduplication at ingest, source tracking. |
| 15 | **Data Quality Engine** | Validation rules (schema, range, format, custom), anomaly detection (statistical, ML-based), deduplication (fuzzy matching, entity resolution), data lineage tracking (where did this data come from, what touched it). |
| 16 | **Embedding Engine** | Multi-modal embeddings (text, image, code, audio), vector store management (create, update, query, delete), domain-adapted models (fine-tuned embeddings for specific domains), retrieval pipelines (hybrid search: dense + sparse + reranking). |
| 17 | **Knowledge Graph Builder** | Entity extraction and resolution, relationship detection and typing, ontology management (domain schemas), graph queries and traversal, reasoning over graph structure, incremental updates. |
| 18 | **Labeling & Ground Truth** | Annotation task creation and management, gold dataset curation and versioning, quality scoring (inter-annotator agreement, confidence), active learning (prioritize most informative examples for labeling). |
| 19 | **Privacy & PII Engine** | PII detection across text/images/structured data, configurable redaction strategies, retention policy enforcement, consent management, data residency rules, audit trail for all PII access. |

---

### System 4: ML & Evaluation (5 modules)

Measurable learning. Where the system gets objectively better over time.

| # | Module | Responsibility |
|---|---|---|
| 20 | **Feature Factory** | Automated feature engineering (from raw data → useful signals), feature store (compute once, serve everywhere), importance analysis (which features actually matter), cross-venture sharing (a feature useful in HR might be useful in sales). |
| 21 | **Model Forge** | Training pipelines (classical ML + deep learning + LLM fine-tuning), model registry (versioned, tagged, searchable), drift detection (model performance degrading over time), AutoML for rapid prototyping. |
| 22 | **Evaluation Framework** | Multi-dimensional scoring (accuracy, latency, cost, safety, user satisfaction), LLM-as-judge evaluations, benchmark management, regression testing (did this change make things worse?), human eval integration. |
| 23 | **Synthetic Data Generator** | LLM-powered data generation (from schema + constraints → realistic data), augmentation strategies (expand limited datasets), privacy-preserving synthesis (train on real patterns, generate non-PII data), calibration (synthetic data quality scoring). |
| 24 | **Simulation Engine** | Workflow stress testing (what happens under load, with failures, with edge cases), cost estimation (how much will this workflow cost at scale), multi-agent failure testing (what if one agent goes rogue, times out, hallucinates). |

---

### System 5: Product & Market Intelligence (6 modules)

**THE BIGGEST ADDITION. The gap that kills most AI ventures.**

This system answers: "Should this exist? For whom? At what price? With what experience?" — before you burn weeks building the wrong thing.

| # | Module | Responsibility |
|---|---|---|
| 25 | **Market & Signal Intelligence** | Competitor monitoring (products, pricing, positioning, funding), trend detection (what's growing, what's dying), dataset discovery for new domains, funding signal tracking, opportunity scoring (market size × gap × timing × founder fit). |
| 26 | **Customer Discovery Engine** | Interview script design (JTBD-based, pain-extraction focused), automated interview analysis (pain extraction, frequency counting, emotional intensity scoring), persona synthesis (from N interviews → actionable ICPs), buying trigger identification, pattern detection across interviews ("8/10 mentioned X as their #1 pain"). |
| 27 | **Venture Thesis Engine** | Hypothesis formulation (structured: "We believe [ICP] will pay [price] for [solution] because [pain]"), assumption decomposition (what must be true for this to work?), validation tracking (evidence ladder per assumption), kill signal detection (automatic alerts when evidence contradicts thesis), decision framework (kill/pivot/proceed with evidence scores). |
| 28 | **Offer Design Engine** | Positioning canvas (category, differentiator, proof), pricing strategy (value-based, competitive, penetration), messaging hierarchy (headline, subhead, proof points, objection handling), landing page copy generation, ICP definition refinement, channel strategy (where does the ICP hang out?). |
| 29 | **Product Experience Engine** | UX flow mapping (user journey from awareness → activation → retention), screen architecture (what screens exist, what's on them, how they connect), interaction pattern selection (which AI patterns work for this use case: chat, copilot, autonomous, ambient), feature prioritization (MoSCoW with evidence weighting), AI-native UX patterns library. |
| 30 | **Workflow Blueprint Engine** | Process mapping (current state: how does the user solve this today?), human/AI step identification (which steps can AI handle, which need humans?), workflow → agent translation (process map → agent network design), automation opportunity scoring, handoff point design (where does AI pass to human and back?). |

---

### System 6: Experimentation & Optimization (5 modules)

Flywheel acceleration. The system that turns data into decisions and decisions into improvements.

| # | Module | Responsibility |
|---|---|---|
| 31 | **Experiment Tracker** | Unified tracking across all experiment types (prompt, model, workflow, product, market), meta-learning (which experiment designs yield fastest learning), scheduling (run experiments without conflicts), cross-venture insights (an experiment in Venture A informs Venture B). |
| 32 | **A/B Test & Optimization Engine** | Statistical testing with proper power analysis, multi-armed bandits for real-time optimization, continuous optimization (auto-allocate traffic to winners), multi-variant testing, guardrail metrics (don't optimize conversion at the cost of satisfaction). |
| 33 | **Feedback Collector** | Human signals (explicit ratings, corrections, preferences), automated signals (latency, errors, costs, conversion), implicit signals (usage patterns, abandonment, time-on-task), routing (feedback → correct experiment → correct metric), quality scoring (weight feedback by source reliability). |
| 34 | **Metrics & Reward Registry** | Metric definitions (typed, with computation logic), north star metrics per venture, guardrail metrics (never cross these boundaries), reward modeling (for RLHF-style optimization), metric lineage (which inputs feed this metric). |
| 35 | **Cost Optimizer** | Per-token cost tracking across all LLM calls, smart routing (cheaper model when quality is sufficient), response caching (don't pay twice for the same answer), budget alerts and automatic throttling, Pareto optimization (cost vs. quality frontier). |

---

### System 7: Deployment & Reliability (2 modules)

Production operations. Get it live. Keep it live.

| # | Module | Responsibility |
|---|---|---|
| 36 | **Deployment Engine** | Packaging (containerization, dependency management), multi-environment promotion (dev → staging → prod), canary releases (gradual rollout with automatic rollback), blue/green deployments, auto-scaling based on load, rollback (instant revert to last known good). |
| 37 | **Reliability & Incident Engine** | Circuit breakers (stop calling failing services), intelligent retries (exponential backoff, jitter), health checks (liveness, readiness, deep health), SLA monitoring and alerting, incident detection and response, audit trail (what happened, when, why, who was notified). |

---

### System 8: Cross-Venture Learning (2 modules)

The compounding layer. This is what makes the platform more than the sum of its parts.

| # | Module | Responsibility |
|---|---|---|
| 38 | **Pattern & Template Library** | Reusable patterns across ventures (agent architectures, workflow templates, prompt strategies, evaluation suites), success/failure tracking per pattern (this pattern worked in 3/4 ventures), contextual recommendations (given your domain + stage, try these patterns), contribution (new winning patterns auto-extracted from experiments). |
| 39 | **Meta-Learning & Flywheel Engine** | Cross-venture analytics (which ventures are healthiest, which are stalling), velocity tracking (are we getting faster with each venture?), system-level improvement identification (which shared modules are bottlenecks?), compounding metrics (quantify the flywheel effect over time). |

---

## 4. Layer 2: Venture Orchestrators

Each venture is a self-contained unit that composes Layer 1 modules with domain-specific logic. A venture orchestrator is NOT a fork — it's a configuration + domain layer.

### Components of a Venture Orchestrator

#### Venture Definition
- **Domain**: Industry/problem space (e.g., HR tech, sales intelligence, fintech)
- **Thesis**: Structured hypothesis with validation criteria and kill signals
- **ICP**: Ideal customer profile with buying triggers and pain hierarchy
- **Success Metrics**: North star + guardrails + leading indicators
- **Stage**: Discovery → Validation → Build → Launch → Scale (determines which modules are active)

#### Agent Network
- **Manager Agent**: Top-level coordinator, understands venture goals, delegates work
- **Specialist Agents**: Domain-specific (resume parser, deal scorer, risk assessor)
- **Support Agents**: Cross-domain (researcher, writer, data analyst, evaluator)
- **Coordination Protocol**: How agents communicate, share context, resolve conflicts
- **Shared Memory**: Venture-scoped context accessible to all agents in the network

#### Domain Workflows
- Built by composing Layer 1 modules into domain-specific sequences
- Examples: candidate screening pipeline, customer interview analysis flow, pricing test workflow
- Each workflow is versioned, traced through the spine, and improvable via experiments

#### Domain Knowledge Base
- **Industry Data**: Regulations, terminology, benchmarks, competitive landscape
- **Customer Data**: Profiles, interactions, preferences, feedback history
- **Learning Repository**: What this venture has learned — successful strategies, failed experiments, edge cases
- **Domain Embeddings**: Venture-specific vector indices for retrieval

#### Venture Flywheel
- The venture-specific feedback loop:
  1. Every interaction generates data (spine captures it)
  2. Data improves agent/model performance (experiments prove it)
  3. Improved performance drives more usage (metrics show it)
  4. More usage generates more data (events record it)
  5. Patterns extracted feed back into Layer 1 (cross-venture learning)

---

## 5. How a Venture Activates Layer 1

The day-by-day sequence from idea to production. Each phase activates specific Layer 1 systems.

### Week 1–2: Discovery & Validation (Systems 1, 5, 3)

| Day | Activity | Modules Used |
|---|---|---|
| 1 | Define venture thesis | **Venture Thesis Engine** (27): Formulate hypotheses, list assumptions |
| 2 | Market scan | **Market & Signal Intelligence** (25): Competitors, trends, gaps, timing |
| 3 | Data landscape | **Universal Ingestor** (14) + **Knowledge Graph Builder** (17): Ingest domain docs, build initial knowledge |
| 4–5 | Customer discovery | **Customer Discovery Engine** (26): Design interviews, analyze pain, extract patterns |
| 6–7 | Validate or kill | **Venture Thesis Engine** (27): Score evidence, check kill signals, decide go/no-go |
| 8–9 | Design offer | **Offer Design Engine** (28): Positioning, pricing, messaging, ICP refinement |
| 10 | Design product | **Product Experience Engine** (29) + **Workflow Blueprint Engine** (30): UX flows, screen architecture, AI pattern selection |

**Gate**: Kill signal check. If evidence score < threshold → kill venture, save learnings, move to next idea.

### Week 3–4: Build (Systems 1, 2, 3, 4)

| Day | Activity | Modules Used |
|---|---|---|
| 11–12 | Data foundation | **Universal Ingestor** (14) + **Data Quality Engine** (15) + **Embedding Engine** (16): Ingest, clean, embed |
| 13–14 | Agent design | **Agent Factory** (9) + **Prompt Studio** (8) + **Tool Forge** (10): Design agents, craft prompts, build tools |
| 15–16 | Memory & knowledge | **Memory Engine** (11) + **Knowledge Graph Builder** (17): Configure memory, enrich knowledge graph |
| 17–18 | Initial training | **Model Forge** (21) + **Feature Factory** (20): Train domain models, compute features |
| 19–20 | Evaluation baseline | **Evaluation Framework** (22) + **Labeling & Ground Truth** (18): Build test suites, create gold datasets |

### Week 5: Optimize & Ship (Systems 6, 7)

| Day | Activity | Modules Used |
|---|---|---|
| 21–22 | Experiment setup | **Experiment Tracker** (31) + **A/B Test Engine** (32): Launch experiments on key decisions |
| 23–24 | Feedback wiring | **Feedback Collector** (33) + **Human Review Engine** (12): Wire up all feedback channels |
| 25 | Cost optimization | **Cost Optimizer** (35): Optimize LLM routing, enable caching, set budgets |
| 26–27 | Deploy | **Deployment Engine** (36) + **Reliability Engine** (37): Canary release, circuit breakers, monitoring |
| 28 | Flywheel activation | All feedback loops closed. Spine is capturing → measuring → learning → improving. |

### Week 6+: Compound (System 8)

- **Pattern & Template Library** (38): Extract winning patterns, share across ventures
- **Meta-Learning Engine** (39): Track velocity, identify bottlenecks, quantify improvement
- Patterns from this venture make the NEXT venture faster

---

## 6. Design Principles

### Principle 1: The Execution Spine Is Non-Negotiable

Every module, every agent, every workflow passes through: Event → Task → Agent/Tool → Trace → Metric → Feedback → Experiment → Pattern. No exceptions. No shortcuts. This is how the system learns.

### Principle 2: Cheapest Evidence First

The evidence ladder is enforced:
1. Desk research (System 5: Market Intelligence)
2. Customer conversations (System 5: Customer Discovery)
3. Landing page + waitlist (System 5: Offer Design)
4. Wizard-of-Oz prototype (System 2: Human Review + Agent Factory)
5. Full agent deployment (System 7: Deployment)

Never skip a rung. Each rung has explicit go/no-go criteria.

### Principle 3: Kill Early, Kill Cheap

Every validation stage has explicit kill signals:
- Discovery: <3/10 interviews show pain → kill
- Offer validation: <2% landing page conversion → kill
- Build: Agent accuracy <70% after tuning → pivot approach
- Launch: CAC >3x LTV projection → kill or pivot channel

The **Venture Thesis Engine** (module 27) surfaces these proactively. The platform does not let you ignore disconfirming evidence.

### Principle 4: Event-Driven Communication

Modules emit events and subscribe to events. Never direct calls between modules. Benefits:
- Modules can be swapped without cascading changes
- New modules can tap into existing flows without modifying producers
- Events are persisted → full audit trail
- Events are replayable → debugging and testing
- Cross-venture learning happens through event patterns

### Principle 5: Human-in-the-Loop Is a Feature

The system handles 95% autonomously. It surfaces the 5% that requires founder judgment:
- Kill/continue decisions on venture thesis
- Pricing strategy choices
- Brand positioning and messaging tone
- Ethical boundary decisions
- High-stakes customer communications

The **Human Review Engine** (module 12) + **Policy Engine** (module 13) manage the boundary between autonomy and oversight.

### Principle 6: Multi-Channel, Single Brain

Slack, Web App, and CLI are interfaces to the same system. Context persists across channels. The router picks the right channel for each interaction type:
- Urgent → Slack push notification
- Complex → App deep-dive with visual tools
- Bulk → CLI batch processing
- Ambient → App dashboard (check when you want)

### Principle 7: Everything Is Versioned and Reproducible

Prompts, agent configs, workflows, datasets, models, experiments, and patterns are all versioned. Any past state can be reproduced. Any result can be attributed to its exact configuration. Rollback to any previous version is instant.

### Principle 8: Cost Is a First-Class Metric

Every LLM call, every API hit, every compute cycle has a cost attached. Cost is tracked per-task, per-agent, per-venture, per-experiment. The **Cost Optimizer** (module 35) continuously finds cheaper ways to achieve the same quality. Budget overruns trigger automatic alerts and throttling before they become problems.

---

## Critical Complexity Pipelines

Not every module is a single agent wrapping an API call. Some components determine the quality of an entire venture and need deep decomposition into multi-agent pipelines with independent evaluation and experimentation at each step.

### The Principle

For any venture, certain components are **quality-determining** — if they work well, the whole product works. If they're shallow ("just call GPT and hope"), the product is unreliable slop.

The platform's job is to:
1. **Identify** which components are critical (from error analysis, metric bottlenecks, or founder flagging)
2. **Decompose** into a pipeline of specialized sub-agents (not one monolithic agent)
3. **Evaluate** each step independently with its own metrics
4. **Experiment** at each step to find the best approach (prompts, models, strategies)
5. **Research** — when a sub-problem is hard, actively search for papers, techniques, and sample implementations rather than just throwing a prompt at it
6. **Compound** — improvements at each step multiply together

### When to Use Deep Pipelines vs. Single Agents

| Situation | Approach |
|-----------|----------|
| Simple, well-defined task (send email, format data) | Single agent, single shot |
| Complex but doesn't determine product quality (logging, notifications) | Single agent, good enough |
| Quality-determining component where errors are visible to users | **Deep pipeline with eval + experimentation** |
| Component where "just use GPT" produces unreliable results | **Deep pipeline — the problem needs research, not wrappers** |

### The Research Imperative

For critical complexity points, the system should NOT just "try a prompt and see." It should:
- Search academic papers for proven approaches (via Market & Signal Intelligence)
- Understand what methods work for this specific sub-problem
- When it doesn't know how to solve something: ask the founder, suggest papers, request sample implementations
- Build on research, not on hope

This prevents the platform from becoming "GPT wrapper + database" and pushes it toward genuine intelligence.

### Examples of Critical Complexity Pipelines

**Knowledge Graph Construction (RAG ventures):**
- 8+ specialized sub-agents (structure analysis → ontology → entity extraction → resolution → relationships → graph assembly → schema export)
- Each step has independent eval metrics
- Each step is experimentable
- The exported schema constrains query-time generation (prevents hallucination)

**Candidate Screening (HR ventures):**
- Multi-dimensional scoring (skills match + experience relevance + culture fit + growth potential)
- Bias detection as a parallel evaluation pipeline
- Each scoring dimension independently tunable and experimentable

**Lead Qualification (Sales ventures):**
- Signal aggregation from multiple sources (company data + buyer intent + tech stack + hiring patterns)
- Scoring model that weights signals differently per ICP
- Each signal source independently evaluatable

### Visual Pipeline Builder

Critical complexity pipelines are built and managed through a visual pipeline builder UI:
- Drag specialized agents onto a canvas
- Wire them together (outputs → inputs)
- See results in real-time (graph view for KG, metrics for eval)
- Run experiments comparing pipeline variants
- Each agent in the pipeline is independently configurable

This is a core UI component of the platform — it works for KG construction, retrieval pipelines, evaluation pipelines, scoring pipelines, or any multi-step process where quality matters.

### How Experimentation Integrates

Each step in a critical pipeline connects to the Experiment Tracker:
- Define variants for any step (different prompt, different model, different strategy)
- Run traffic through the pipeline with different step configurations
- Measure impact on downstream quality (not just the step's own metric, but the END metric)
- Identify which steps have the most leverage (where improvement matters most)
- Prioritize research/effort on the highest-leverage steps

---

## 7. Interaction Architecture

### The Conversation Router

The router sits between all interaction channels and the module system. It receives intent from any channel and routes to the appropriate module(s).

```
┌──────────────────────────────────────────────────────────────────────┐
│                         CHANNELS                                      │
│                                                                      │
│  ┌─────────┐         ┌──────────────┐         ┌─────────┐          │
│  │  Slack  │         │   Web App    │         │   CLI   │          │
│  │         │         │  (Next.js)   │         │         │          │
│  │ • Notif │         │ • Dashboard  │         │ • Batch │          │
│  │ • Approv│         │ • Co-pilot   │         │ • Script│          │
│  │ • Quick │         │ • Visual     │         │ • CI/CD │          │
│  │   cmds  │         │ • Deep work  │         │ • Power │          │
│  └────┬────┘         └──────┬───────┘         └────┬────┘          │
│       │                     │                      │                │
└───────┼─────────────────────┼──────────────────────┼────────────────┘
        │                     │                      │
        ▼                     ▼                      ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    CONVERSATION ROUTER                                │
│                                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────────┐ │
│  │   Intent    │  │   Context    │  │      Routing Logic         │ │
│  │  Classifier │  │   Manager    │  │                            │ │
│  │             │  │              │  │  • Complexity → sync/async │ │
│  │  • Command  │  │  • Session   │  │  • Urgency → channel pick │ │
│  │  • Query    │  │  • History   │  │  • Context → module select │ │
│  │  • Action   │  │  • Venture   │  │  • Capability → agent pick │ │
│  │  • Approval │  │  • Stage     │  │  • Cost → budget check     │ │
│  └─────────────┘  └──────────────┘  └────────────────────────────┘ │
│                                                                      │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    MODULE SYSTEM (Layer 1 + Layer 2)                  │
│                                                                      │
│  Routed to appropriate system/module based on:                       │
│  • Intent type (discovery, build, deploy, monitor, optimize)         │
│  • Venture context (which venture is active)                         │
│  • Stage context (are we in validation or production)                │
│  • Complexity (simple lookup vs. multi-step workflow)                 │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Routing Logic

| Signal | Low | High |
|---|---|---|
| **Complexity** | Instant response (lookup, status check) | Async execution with progress updates |
| **Urgency** | Batched in dashboard, weekly summary | Immediate Slack push or app alert |
| **Context depth** | Stateless command (no history needed) | Full conversation with memory retrieval |
| **Cost** | Free tier (cached, no LLM call) | Budget-gated (requires confirmation above threshold) |

### Channel Strengths

| Channel | Best For | Interaction Style |
|---|---|---|
| **Slack** | Approvals, alerts, quick status, time-sensitive decisions | Reactive — system initiates |
| **Web App** | Deep exploration, visual analysis, co-pilot conversations, workflow design | Proactive — founder initiates |
| **CLI** | Batch operations, scripting, CI/CD, power-user workflows | Programmatic — automation initiates |

### Context Continuity

All channels share:
- **Session state**: Current venture, current stage, recent actions
- **Conversation memory**: Start in Slack, continue in app, reference in CLI
- **Pending decisions**: Approval requested in app, answered in Slack, recorded everywhere
- **Active experiments**: Results visible in app dashboard, alerts via Slack, queryable via CLI

---

## Summary: The System at a Glance

| Layer | Systems | Modules | Purpose |
|---|---|---|---|
| Layer 1 | 8 | 39 | Shared, venture-agnostic foundation |
| Layer 2 | — | Per-venture | Domain logic + orchestration |
| Spine | — | — | Learning protocol (Event → Pattern) |
| Interaction | — | — | Multi-channel access (Slack, App, CLI) |

The architecture exists to serve one goal: **make each venture faster, cheaper, and more evidence-based than the last — compounding advantage with every cycle of the flywheel.**
