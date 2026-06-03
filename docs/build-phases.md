# Build Phases

## Overview

AI Flywheel is built in seven phases (Phase 0–6) over 13+ weeks. Each phase delivers a working increment — you can use the platform after every phase, with expanding capabilities. The ordering is driven by a single principle: **the Execution Spine comes first**. Phase 0 proves the bare metal works (Temporal workflows survive restarts, traces capture everything, cost is tracked). Phase 1 proves a real agent can run through that spine. Nothing else proceeds until these foundations are proven solid.

---

## Phase 0: Bare Metal (Week 1-2)

### Goal

Prove the execution spine works. A dummy workflow can execute across multiple steps, survive a restart, trace every action, and record cost.

### What Gets Built (5 modules)

| Source System | Module | Purpose |
|---------------|--------|---------|
| System 1: Platform Core | **Platform Core (#1)** | Config, secrets, settings |
| System 1: Platform Core | **Event Bus (#3)** | Pub/sub with persistence |
| System 1: Platform Core | **Task Runtime (#4)** | Temporal-based workflow engine |
| System 1: Platform Core | **Trace & Observability (#5)** | Distributed tracing, error analysis |
| System 2: Agent Intelligence | **LLM Gateway (#7)** | Multi-provider with cost tracking |

### Dependencies

- PostgreSQL + pgvector (via Docker)
- Temporal (local dev server via Docker)
- At least one LLM API key (OpenAI or Anthropic)
- Python 3.12+

### Key Technical Decisions

1. **Temporal.io as the workflow engine:** Not a custom Postgres state machine. Workflows survive container restarts via event history replay. This is the foundation everything else builds on.
2. **Row-Level Security (RLS) on PostgreSQL from the first table creation:** Every query requires `venture_id` context at the DB session level. Security is structural, not application-level.
3. **In-process event bus with DB persistence:** No external broker yet. Events publish in-process and persist to Postgres for replay and audit.
4. **All module methods are async:** The event bus, database layer, and API use asyncio throughout. No blocking calls.
5. **Every query requires venture_id context:** At the DB session level. Cross-venture data access is impossible by construction.

### Testing Strategy

- Unit tests for every core module (config loading, database sessions, event pub/sub)
- Temporal workflow execution tested with container restart simulation
- Trace completeness validation (every task produces a trace, every trace has cost attribution)
- RLS enforcement tested (queries without venture_id context fail)
- LLM Gateway tested with mock providers for deterministic cost tracking

### Success Criteria

- [ ] A multi-step workflow executes via Temporal
- [ ] Workflow survives container restart (state hydration works)
- [ ] Every step is traced with timing, cost, and inputs/outputs
- [ ] LLM call goes through gateway, cost is recorded
- [ ] RLS prevents cross-venture data access at the DB level

### Deliverable

The execution spine is proven solid. Nothing else until this works.

---

## Phase 1: First Agent (Week 3-4)

### Goal

A real agent runs a real task through the spine.

### What Gets Built (5 modules)

| Source System | Module | Purpose |
|---------------|--------|---------|
| System 1: Platform Core | **Identity & Tenancy (#2)** | Venture scoping, RLS enforcement |
| System 2: Agent Intelligence | **Agent Factory & Orchestration (#9)** | Config-driven agents, multi-agent patterns as Temporal workflows |
| System 2: Agent Intelligence | **Prompt Studio (#8)** | Template management, versioning, no UI |
| System 5: Venture Validation | **Customer Discovery Engine (#26)** | First real use case |
| System 6: Learning & Optimization | **Cost Optimizer (#35)** | Budget tracking and alerts |

### Dependencies

- Phase 0 complete (execution spine proven)
- PostgreSQL with RLS configured (from Phase 0)
- Temporal running (from Phase 0)
- At least one LLM API key (OpenAI or Anthropic)
- Python 3.12+, Node.js 20+

### Key Technical Decisions

1. **Agents defined as data (YAML/JSON), not code:** Agent behavior is configuration. This enables experimentation without deploys.
2. **Agent execution = Temporal activity:** Retryable, timeout-able, and independently cost-tracked.
3. **Multi-agent orchestration = Temporal child workflows:** Fan-out, sequential chains, and coordination all expressed as workflow primitives.
4. **Human review = Temporal signals:** Workflow pauses, emits a review request event, and resumes only when a signal arrives (approved/rejected/edited). No polling, no timers.
5. **Memory access control:** Agent blueprints declare which memory tiers they can access. Enforced at runtime.

### Testing Strategy

- Agent definition and execution end-to-end (define via config → execute → trace → cost)
- Multi-step workflow with approval pause tested (signal sent, workflow resumes)
- Customer Discovery Engine tested with mock interview transcripts
- Cost tracking validated across multiple agent executions
- Prompt versioning lifecycle (create v1, update to v2, rollback to v1)

### Success Criteria

- [ ] Create an agent via config, execute it against a task
- [ ] Agent execution traces through the full spine (event → task → trace → metric → cost)
- [ ] Customer Discovery Engine generates interview guide from domain input
- [ ] Multi-step workflow pauses for approval, resumes when approved
- [ ] Cost tracked per agent per execution

### Deliverable

A real agent does real work, fully traced and costed.

### Capabilities Unlocked

After Phase 0 + Phase 1, you can:
- Run customer discovery interviews with AI-assisted analysis
- Create and test agents with versioned prompts
- Execute agents as Temporal workflows with full observability
- Multi-agent orchestration with parallel fan-out and sequential chains
- Human-in-the-loop approval flows that survive indefinite waits
- See full cost breakdown by venture, module, task, and provider
- Debug any action through its complete trace
- All data isolated per venture via RLS at the database level

---

## Phase 2: Data Foundation + Market Intelligence (Week 5-6)

### Goal

Build the research and data layer. The platform can discover markets, ingest data, validate quality, generate embeddings for RAG, and construct knowledge graphs. You can now research whether a market is worth entering.

### What Gets Built (7 modules)

| Source System | Module | Purpose |
|---------------|--------|---------|
| System 1: Platform Core | **Identity & Tenancy** | Multi-tenant isolation, user management |
| System 3: Data & Knowledge | **Universal Ingestor** | Ingest data from any source into normalized format |
| System 3: Data & Knowledge | **Data Quality Engine** | Validate, profile, and score dataset quality |
| System 3: Data & Knowledge | **Embedding Engine** | Generate and manage vector embeddings |
| System 3: Data & Knowledge | **Knowledge Graph Builder** | Extract entities and relationships |
| System 5: Venture Validation | **Market & Signal Intelligence** | Monitor markets, competitors, opportunities |
| System 5: Venture Validation | **Venture Thesis Engine** | Formalize and track hypotheses |

### Dependencies

- Phase 0 + Phase 1 complete (Execution Spine + First Agent)
- Object storage for raw data (S3-compatible or local MinIO)
- pgvector extension installed (from Phase 0)

### Key Technical Decisions

1. **Market Intelligence is event-driven:** Monitors signals on schedule or on-demand, publishing `signal.detected` events.
2. **Ingestor is pluggable:** Parser plugins for CSV, JSON, PDF, HTML, API responses. New formats added without modifying core.
3. **Quality is automated:** Data Quality Engine runs automatically on ingestion. Scores completeness, consistency, freshness, domain relevance.
4. **Embeddings are chunked:** Documents split into semantic chunks before embedding. Chunk strategy configurable per venture.
5. **Knowledge graph is incremental:** New data appends edges; confidence scores update as corroborating evidence arrives.
6. **Thesis Engine integrates with Evidence Ladder:** Each hypothesis has explicit rungs and validation criteria.

### Testing Strategy

- Market Intelligence tested with mock signal sources (RSS, API responses)
- Universal Ingestor tested with real (small) datasets in multiple formats
- Data Quality Engine tested against known-bad datasets (missing values, duplicates, schema drift)
- Embedding similarity tests (known-similar documents should have high cosine similarity)
- Knowledge Graph tested against annotated text samples
- Venture Thesis Engine tested with hypothesis lifecycle (create → evidence → validate/invalidate)

### Success Criteria

- [ ] Market & Signal Intelligence identifies relevant trends for a given venture domain
- [ ] Venture Thesis Engine tracks hypotheses through evidence ladder rungs
- [ ] Universal Ingestor successfully ingests CSV, JSON, and PDF formats
- [ ] Data Quality Engine produces quality report with actionable findings
- [ ] Embedding Engine generates vectors and similarity search returns relevant results
- [ ] Knowledge Graph Builder extracts entities and relationships from text
- [ ] Identity & Tenancy isolates data between ventures
- [ ] All modules publish events and track costs through Task Runtime
- [ ] End-to-end: market signal → hypothesis → data ingestion → quality check → embed → graph

### Capabilities Unlocked

After Phase 2, you can:
- Research markets with AI-assisted signal aggregation
- Formalize and track venture hypotheses through evidence stages
- Ingest CSVs, PDFs, and API data into a unified format
- Get automatic quality reports on ingested data
- Ask RAG-style questions against ingested data (via embeddings)
- Explore knowledge graphs of entities and relationships
- Isolate data between ventures with proper tenancy
- Full research and data pipeline operational

---

## Phase 3: Product Design + Offer (Week 7-8)

### Goal

Complete the validation pipeline. Design offers, create landing pages, run campaigns, collect behavioral signals, test pricing. The Evidence Ladder is fully operational.

### What Gets Built (6 modules)

| Source System | Module | Purpose |
|---------------|--------|---------|
| System 5: Venture Validation | **Offer Design Engine** | ICP, positioning, pricing, landing copy |
| System 5: Venture Validation | **Product Experience Engine** | Screen architecture, AI interaction patterns |
| System 5: Venture Validation | **Workflow Blueprint Engine** | Map user flows and agent handoffs |
| System 2: Agent Intelligence | **Tool Forge** | Create and manage tools for agents (initial integrations) |
| System 6: Learning & Optimization | **A/B Test & Optimization Engine** | Statistical A/B testing for any configuration |
| System 6: Learning & Optimization | **Feedback Collector** | Collect human and automated feedback systematically |

### Dependencies

- Phase 0-1 complete (agents, tasks, traces, Temporal workflows)
- Phase 2 complete (market intelligence, data, embeddings)
- External integration accounts (ad platforms, Stripe, email provider, hosting)

### Key Technical Decisions

1. **Offer Design is LLM-powered but structured:** Outputs are structured data (ICP profile, positioning statement, pricing table), not free-form text.
2. **Product Experience Engine generates interaction specifications:** Defines which AI decisions are autonomous, which need explanation, which need approval.
3. **Workflow Blueprint is executable:** Blueprints aren't just documentation — they compile into actual agent orchestration configs.
4. **Tool Forge initial integrations:** Ad platforms (Meta, Google), Stripe (billing), Vercel (landing pages), email (SendGrid). More in later phases.
5. **A/B tests are statistically rigorous:** Sequential testing with proper stopping rules. No peeking without correction.
6. **Feedback is multi-signal:** Explicit (forms), implicit (behavior), and automated (output quality metrics).

### Testing Strategy

- Offer Design Engine tested with known market inputs → validated output structure
- Product Experience Engine tested with various AI function types (autonomous, explanatory, approval)
- Workflow Blueprint Engine tested by compiling blueprints and validating executable output
- Tool Forge tested with sandboxed external API calls
- A/B Test Engine tested with simulated data (verify statistical correctness)
- Feedback Collector tested with multiple signal types

### Success Criteria

- [ ] Offer Design Engine produces complete offer package (ICP, positioning, pricing, copy) from market research input
- [ ] Product Experience Engine generates interaction specifications for AI agent behaviors
- [ ] Workflow Blueprint Engine compiles user flows into executable agent orchestration
- [ ] Tool Forge connects to at least 4 external integrations (ad platform, payment, hosting, email)
- [ ] A/B Test Engine reaches statistical significance and declares winner
- [ ] Feedback Collector captures explicit, implicit, and automated signals
- [ ] Evidence Ladder is fully operational: can validate a venture from market research through behavioral signal collection
- [ ] End-to-end: offer designed → landing page created → campaign run → signals collected → hypothesis validated/invalidated

### Capabilities Unlocked

After Phase 3, you can:
- Design complete product offers with AI assistance
- Map user workflows that compile into agent orchestration
- Define AI interaction patterns (autonomous vs. supervised vs. approval)
- Connect agents to external tools (ad platforms, payment, email, hosting)
- Run proper A/B tests on any system component
- Collect multi-signal feedback from users
- Validate a venture end-to-end through the Evidence Ladder
- Full validation pipeline: discover → research → hypothesize → design → test → validate

---

## Phase 4: ML + Advanced Agents (Week 9-10)

### Goal

Move beyond LLM prompts to real ML models, human review workflows, safety/compliance, and labeled datasets for rigorous evaluation.

### What Gets Built (8 modules)

| Source System | Module | Purpose |
|---------------|--------|---------|
| System 2: Agent Intelligence | **Memory Engine** | Short-term and long-term memory for agent continuity |
| System 2: Agent Intelligence | **Human Review Engine** | Configurable human-in-the-loop workflows |
| System 2: Agent Intelligence | **Policy Engine** | Safety, compliance, and governance rules |
| System 4: Model & ML | **Feature Factory** | Transform raw data into ML-ready features |
| System 4: Model & ML | **Model Forge** | Train, tune, and manage ML models |
| System 4: Model & ML | **Evaluation Framework** | Comprehensive model evaluation with multiple metrics |
| System 3: Data & Knowledge | **Labeling & Ground Truth** | Create and manage labeled datasets |
| System 3: Data & Knowledge | **Privacy & PII Engine** | Detect, mask, and manage PII |

### Dependencies

- Phase 0-3 complete (spine, data, validation)
- Compute resources for training (GPU optional for small models)
- Model artifact storage (S3-compatible)

### Key Technical Decisions

1. **Memory is tiered:** Working memory (current task), episodic memory (recent interactions), semantic memory (embedded knowledge). Different retrieval strategies per tier.
2. **Human Review is policy-driven:** Approval rules defined as data, not code. Thresholds, escalation paths, and timeout behaviors are configurable per venture.
3. **Policy Engine is non-blocking by default:** Compliance checks are advisory unless explicitly configured as blocking.
4. **Feature Factory is declarative:** Feature transformations defined as config (like dbt for ML features). Enables versioning and reproducibility.
5. **Model Forge wraps multiple frameworks:** scikit-learn, PyTorch, and Hugging Face behind unified interface.
6. **Evaluation is multi-dimensional:** Never a single metric. Every evaluation produces accuracy, fairness, robustness, latency, and cost metrics.
7. **Labeling integrates with Human Review:** Human review decisions become training labels automatically.
8. **PII detection runs on ingest:** Privacy Engine hooks into Universal Ingestor pipeline.

### Testing Strategy

- Memory retrieval tested with known query/document pairs across all tiers
- Human Review tested with simulated approval flows (auto-approve, queue, escalate, timeout)
- Policy Engine tested with known compliance scenarios
- Feature Factory tested with known input/output pairs
- Model Forge tested with toy datasets for fast iteration
- Evaluation Framework tested against models with known characteristics
- Labeling tested with inter-annotator agreement metrics
- Privacy Engine tested with known PII patterns

### Success Criteria

- [ ] Agent remembers context from previous interactions (working + episodic + semantic memory)
- [ ] Human Review routes decisions correctly (auto-approve, queue, escalate) based on confidence thresholds
- [ ] Policy Engine enforces safety rules and produces audit trail
- [ ] Feature Factory transforms raw data into ML-ready features declaratively
- [ ] Model Forge trains a classifier on venture data with proper evaluation
- [ ] Evaluation Framework produces multi-dimensional report (accuracy, fairness, cost, latency)
- [ ] Labeling Engine manages gold datasets with inter-annotator agreement tracking
- [ ] Privacy Engine detects and masks PII in ingested documents
- [ ] End-to-end: data → features → train → evaluate → review → approve → deploy

### Capabilities Unlocked

After Phase 4, you can:
- Build agents with persistent memory across interactions
- Configure human-in-the-loop workflows with policy-driven routing
- Enforce safety and compliance policies with full audit trails
- Train real ML models (not just LLM prompts) on venture-specific data
- Evaluate models rigorously across multiple dimensions
- Create and manage labeled datasets for training and evaluation
- Detect and handle PII automatically
- Human review decisions automatically become training data (the loop closes)

---

## Phase 5: Production + Scale (Week 11-12)

### Goal

Production-grade deployment, reliability, simulation testing. Can ship real ventures to real customers with confidence.

### What Gets Built (4 modules)

| Source System | Module | Purpose |
|---------------|--------|---------|
| System 4: Model & ML | **Synthetic Data Generator** | Generate training data when real data is scarce |
| System 4: Model & ML | **Simulation Engine** | Test agent networks against synthetic scenarios |
| System 7: Production & Reliability | **Deployment Engine** | Package and deploy agents to production |
| System 7: Production & Reliability | **Reliability & Incident Engine** | Monitor health, detect anomalies, auto-heal |

### Dependencies

- Phase 0-4 complete
- Container registry (for Deployment Engine)
- Monitoring infrastructure (for Reliability Engine)
- Production hosting environment

### Key Technical Decisions

1. **Synthetic Data is validated:** Generated data passes through Data Quality Engine. Quality score must meet threshold before use in training.
2. **Simulation runs before every deploy:** Agent networks are tested against synthetic scenarios that cover edge cases before production promotion.
3. **Deployment is container-based:** Agents packaged as containers with standardized health checks and scaling policies.
4. **Canary deployments by default:** New versions receive 10% traffic, promote to 100% only if metrics hold.
5. **Reliability Engine is proactive:** Anomaly detection triggers before incidents. Auto-scaling, circuit breaking, and fallback routing are automatic.
6. **Incident Engine learns:** Each incident's resolution is captured and used to auto-resolve similar future incidents.

### Testing Strategy

- Synthetic Data validated against statistical properties of source data
- Simulation Engine tested with known scenarios (expected outcomes defined)
- Deployment Engine tested with dummy containers in staging environment
- Reliability Engine tested with chaos engineering (simulated failures, load spikes)
- End-to-end deployment pipeline tested with rollback scenarios

### Success Criteria

- [ ] Synthetic Data Generator produces statistically valid data for augmenting small datasets
- [ ] Simulation Engine tests agent network against 100+ synthetic scenarios before deploy
- [ ] Deployment Engine packages and deploys agent network as production service
- [ ] Canary deployment detects regression and auto-rolls back
- [ ] Reliability Engine detects anomalies and auto-scales or circuit-breaks
- [ ] Incident Engine captures resolution and applies it to similar future incidents
- [ ] End-to-end: simulate → deploy canary → monitor → promote or rollback

### Capabilities Unlocked

After Phase 5, you can:
- Generate synthetic data to bootstrap new ventures or augment sparse datasets
- Simulate agent behavior against edge cases before shipping
- Deploy ventures to production with canary rollouts
- Auto-detect and recover from failures
- Ship real ventures to real customers with confidence
- Full production lifecycle: build → simulate → deploy → monitor → heal

---

## Phase 6: Flywheel + Visual Builder (Week 13+)

### Goal

Complete platform with cross-venture learning, visual tools, multi-channel interaction, and the meta-learning layer that makes each venture cheaper and faster than the last.

### What Gets Built

| Source System | Component | Purpose |
|---------------|-----------|---------|
| System 8: Meta-Learning | **Pattern & Template Library** | Reusable patterns shared across ventures |
| System 8: Meta-Learning | **Meta-Learning & Flywheel Engine** | System-wide intelligence and cross-venture optimization |
| Platform UI | **Visual Graph Editor** | React Flow-based drag-and-drop agent network designer |
| Platform UI | **Venture Templates** | Pre-built configurations for common venture types |
| Platform UI | **Cross-Venture Dashboard** | Unified view with comparative metrics and flywheel velocity |
| Integration | **Slack Integration** | Bot, notifications, approval workflows via Slack |
| Integration | **CLI Tool** | Command-line interface for power users |

### Dependencies

- Phase 0-5 complete (all 39 modules operational)
- Real usage data from earlier phases (for flywheel metrics and pattern extraction)
- Frontend foundation (React, React Flow)

### Key Technical Decisions

1. **React Flow for graph editor:** Mature library for complex node graphs. Custom nodes per agent type. Edges represent data flow and coordination.
2. **Templates are composable:** Venture templates compose module configurations, not monolithic blueprints. Mix elements from different templates.
3. **Pattern Library is versioned and scored:** Each pattern has confidence score, applicability metadata, and transfer success history.
4. **Meta-Learning uses all venture data:** Observes experiments, identifies what accelerates learning, recommends next actions across the entire platform.
5. **Dashboard is real-time:** WebSocket updates for live metrics. Flywheel velocity shown as rate-of-improvement, not just current performance.
6. **Slack integration is bidirectional:** Receive notifications, approve human review items, trigger commands, view dashboards — all from Slack.
7. **CLI mirrors full platform capability:** Everything possible in UI is possible via CLI. Designed for scripting and automation.

### Testing Strategy

- Visual editor tested with Playwright (E2E browser tests)
- Venture templates tested by instantiation and validation
- Pattern Library tested with apply/validate cycle across ventures
- Meta-Learning tested with historical venture data (does it correctly identify patterns?)
- Dashboard tested with simulated real-time metrics data
- Slack integration tested with mock Slack API
- CLI tested with full command coverage

### Success Criteria

- [ ] User can design multi-agent system visually by dragging nodes and connecting edges
- [ ] Graph editor generates valid agent orchestration config that executes
- [ ] Venture template creates working venture in under 5 minutes
- [ ] Pattern Library correctly identifies and suggests applicable cross-venture patterns
- [ ] Meta-Learning Engine measures flywheel velocity and identifies bottlenecks
- [ ] Cross-venture dashboard shows comparative metrics with improvement trends
- [ ] Slack bot handles notifications, approvals, and basic commands
- [ ] CLI provides full platform access for power users
- [ ] Flywheel metrics clearly show each successive venture getting faster/cheaper

### Capabilities Unlocked

After Phase 6, you can:
- Design multi-agent systems visually without writing code
- Launch new ventures from templates in minutes
- See cross-venture patterns automatically identified and suggested
- Measure flywheel velocity (is each venture accelerating?)
- Compare all ventures on a unified dashboard
- Interact with the platform via Slack (approvals, notifications, commands)
- Use the CLI for scripting and automation
- The meta-learning layer actively makes each new venture faster and cheaper
- Platform is complete and production-ready

---

## Phase Summary

| Phase | Weeks | Modules Built | Cumulative | Key Unlock |
|-------|-------|---------------|------------|------------|
| 0 | 1-2 | 5 | 5/39 | Execution spine proven (Temporal + tracing + cost) |
| 1 | 3-4 | 5 | 10/39 | First agent runs real work through spine |
| 2 | 5-6 | 7 | 17/39 | Market research + data pipeline |
| 3 | 7-8 | 6 | 23/39 | Full validation pipeline + Evidence Ladder |
| 4 | 9-10 | 8 | 31/39 | ML models + human review + safety |
| 5 | 11-12 | 4 | 35/39 | Production deployment + reliability |
| 6 | 13+ | 4 + UI + integrations | 39/39 | Flywheel + visual builder + meta-learning |

### Dependency Graph

```
Phase 0 (Bare Metal — Execution Spine)
    │
    └── Phase 1 (First Agent)
            │
            ├── Phase 2 (Data + Market Intelligence)
            │       │
            │       └── Phase 3 (Product Design + Offer)
            │               │
            │               └── Phase 4 (ML + Advanced Agents)
            │                       │
            │                       └── Phase 5 (Production + Scale)
            │                               │
            │                               └── Phase 6 (Flywheel + Visual Builder)
            │
            └── [Each phase depends on all previous phases]
```

Phases are strictly sequential. Each phase builds on capabilities from all previous phases. This is intentional — Phase 0 proves the execution spine is solid (Temporal, tracing, cost tracking) before any real work runs on it. Phase 1 proves a real agent can execute through the spine. Nothing else proceeds until these foundations are proven.

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| LLM API instability | LLM Gateway with fallback providers from Phase 0 |
| Cost overrun during development | Cost tracking active from Phase 0; Cost Optimizer in Phase 1; every LLM call tracked |
| Workflow state loss | Temporal.io guarantees durable execution from Phase 0; workflows survive container restarts |
| Module coupling | Event bus enforces loose coupling; no direct module imports |
| Scope creep per module | Each module has clear contract; extras become separate modules |
| Database performance at scale | Single DB in Phase 0, partitioning planned from schema design |
| "We'll add observability later" | Trace & Observability in Phase 0; non-negotiable |
| Validation takes too long | Customer Discovery in Phase 1; can validate ideas before building |
| Over-engineering early | Config-driven agents mean you can change behavior without code changes |
| Integration fragility | Tool Forge abstracts external APIs; failures isolated to tool layer |
