# Build Phases

## Overview

AI Flywheel is built in six phases over 12 weeks. Each phase delivers a working increment — you can use the platform after every phase, with expanding capabilities. The ordering is driven by dependency: later modules depend on earlier infrastructure.

---

## Phase 1: Kernel + 5 Core Modules (Week 1-2)

### Goal

Establish the foundation that everything else depends on. After this phase, you can define agents, run them, track experiments, and see costs — the minimum viable flywheel.

### What Gets Built

| # | Component | Purpose |
|---|-----------|---------|
| — | Core kernel | Database, config, event bus, base module class, auth, telemetry |
| 30 | LLM Gateway | Unified interface to all LLM providers. Everything needs this. |
| 16 | Prompt Studio | Create, version, and test prompt templates |
| 17 | Agent Factory | Define agents, execute them, collect results |
| 13 | Experiment Tracker | Record experiments from day 1 |
| 27 | Cost Optimizer | Track spend from the first LLM call |

### Dependencies

- PostgreSQL + pgvector (via Docker)
- At least one LLM API key (OpenAI or Anthropic)
- Python 3.12+, Node.js 20+

### Key Technical Decisions

1. **Async-first:** All module methods are `async`. The event bus, database layer, and API use asyncio throughout.
2. **Single database:** Start with one PostgreSQL instance. Partitioning and read replicas come later.
3. **LLM Gateway abstraction:** All LLM calls go through the gateway — never direct provider SDKs. This enables cost tracking, caching, fallback, and provider switching from day 1.
4. **Event bus in-process:** Start with an in-memory async event bus with database persistence. No external message broker yet.
5. **Config-driven agents:** Agents are defined as data (prompt + tools + constraints), not code. This enables experimentation without deploys.

### Testing Strategy

- Unit tests for every core module (config loading, database sessions, event pub/sub)
- Integration test for agent execution end-to-end (define → execute → record outcome → track cost)
- API endpoint tests with TestClient
- Fixture: mock LLM responses for deterministic testing

### Success Criteria

- [ ] Agent defined via config executes successfully against LLM Gateway
- [ ] Prompt versioning works (create v1, update to v2, rollback to v1)
- [ ] Experiment created and tracked with real outcome data
- [ ] Cost of every LLM call recorded and attributable to venture + module
- [ ] Event bus delivers events between modules (e.g., agent execution → cost tracker)
- [ ] Basic FastAPI endpoints operational for all five modules
- [ ] Minimal web UI showing agent execution results and costs

### Capabilities Unlocked

After Phase 1, you can:
- Create ventures and configure them
- Write and version prompts
- Define agents with specific prompts and constraints
- Execute agents and see their outputs
- Track how much each execution costs
- Run simple A/B tests (prompt v1 vs v2)
- See cost breakdowns by venture, module, and provider

---

## Phase 2: Intelligence + Data (Week 3-4)

### Goal

Build the research and data layer. The platform can now discover relevant datasets, ingest them, validate quality, generate embeddings for RAG, and construct knowledge graphs.

### What Gets Built

| # | Component | Purpose |
|---|-----------|---------|
| 1 | Dataset Scout | Discover datasets from HuggingFace, Kaggle, Papers with Code, web |
| 6 | Universal Ingestor | Ingest data from any source into normalized format |
| 7 | Data Quality Engine | Validate, profile, and score dataset quality |
| 12 | Embedding Engine | Generate and manage vector embeddings |
| 10 | Knowledge Graph Builder | Extract entities and relationships into a queryable graph |

### Dependencies

- Phase 1 complete (kernel, LLM Gateway, cost tracking)
- Object storage for raw data (S3-compatible, or local MinIO in Docker)
- pgvector extension installed (from Phase 1)

### Key Technical Decisions

1. **Dataset discovery is async:** Scout runs on a schedule or on-demand, publishing `dataset.discovered` events. Other modules react.
2. **Ingestor is pluggable:** Parser plugins for CSV, JSON, PDF, HTML, API responses. New formats added without modifying core ingestor.
3. **Quality is automated:** Data Quality Engine runs automatically on ingestion, scoring completeness, consistency, freshness, and domain relevance.
4. **Embeddings are chunked:** Documents are split into semantic chunks before embedding. Chunk strategy is configurable per venture.
5. **Knowledge graph is incremental:** New data appends edges; confidence scores update as corroborating evidence arrives.

### Testing Strategy

- Integration tests with real (small) datasets from HuggingFace
- Data Quality Engine tested against known-bad datasets (missing values, duplicates, schema drift)
- Embedding similarity tests (known-similar documents should have high cosine similarity)
- Knowledge graph extraction tested against annotated text samples

### Success Criteria

- [ ] Dataset Scout discovers relevant datasets given a domain description
- [ ] Universal Ingestor successfully ingests CSV, JSON, and PDF formats
- [ ] Data Quality Engine produces a quality report with actionable findings
- [ ] Embedding Engine generates vectors and similarity search returns relevant results
- [ ] Knowledge Graph Builder extracts entities and relationships from text
- [ ] All modules publish events and track costs
- [ ] End-to-end: discover → ingest → quality check → embed → graph build

### Capabilities Unlocked

After Phase 2, you can:
- Tell the platform "I'm building an HR tech product" and it finds relevant datasets
- Ingest CSVs, PDFs, and API data into a unified format
- Get automatic quality reports on ingested data
- Ask RAG-style questions against your ingested data (via embeddings)
- Explore a knowledge graph of entities and relationships in your domain
- Agents can now access domain knowledge in their executions

---

## Phase 3: ML Pipeline (Week 5-6)

### Goal

Enable real model training within the platform. From raw data to deployed model with proper evaluation and reproducible pipelines.

### What Gets Built

| # | Component | Purpose |
|---|-----------|---------|
| 8 | Feature Factory | Transform raw data into ML-ready features |
| 11 | Model Forge | Train, tune, and manage ML models |
| 14 | Evaluation Framework | Comprehensive model evaluation with multiple metrics |
| 15 | Pipeline Orchestrator | Define and execute reproducible ML pipelines |
| 9 | Synthetic Data Generator | Generate training data when real data is scarce |

### Dependencies

- Phase 2 complete (data ingestion, quality, embeddings)
- Compute resources for training (GPU optional, CPU for small models)
- Model artifact storage (S3-compatible)

### Key Technical Decisions

1. **Feature Factory is declarative:** Feature transformations are defined as config (like dbt for ML features). This enables versioning and reproducibility.
2. **Model Forge wraps multiple frameworks:** scikit-learn, PyTorch, and Hugging Face Transformers behind a unified interface. Model type determines which backend runs.
3. **Evaluation is multi-dimensional:** Never a single metric. Every model evaluation produces accuracy, fairness, robustness, latency, and cost metrics.
4. **Pipelines are DAGs:** Pipeline Orchestrator defines steps as a directed acyclic graph. Steps can be retried independently.
5. **Synthetic data is validated:** Generated data passes through the same Data Quality Engine as real data. Quality score must meet threshold.

### Testing Strategy

- Feature Factory tested with known input/output pairs
- Model Forge tested with toy datasets (iris, MNIST subset) for fast iteration
- Evaluation Framework tested against models with known characteristics
- Pipeline execution tested with mock steps for speed, real steps in nightly CI
- Synthetic data validated against statistical properties of source data

### Success Criteria

- [ ] Feature Factory transforms raw ingested data into ML-ready features
- [ ] Model Forge trains a classifier on ingested data with >80% accuracy
- [ ] Evaluation Framework produces multi-dimensional report
- [ ] Pipeline Orchestrator runs a complete ingest → feature → train → evaluate pipeline
- [ ] Synthetic Data Generator produces statistically similar data to source
- [ ] All training costs tracked and attributed

### Capabilities Unlocked

After Phase 3, you can:
- Define feature engineering pipelines declaratively
- Train classification, regression, and embedding models
- Get comprehensive evaluation reports (not just accuracy)
- Run reproducible ML pipelines end-to-end
- Generate synthetic training data to augment scarce real data
- Compare model versions with proper evaluation methodology
- Agents can now use custom-trained models in their workflows

---

## Phase 4: Multi-Agent + Optimization (Week 7-8)

### Goal

Move from single agents to coordinated multi-agent systems. Add tools, memory, and continuous optimization through experimentation.

### What Gets Built

| # | Component | Purpose |
|---|-----------|---------|
| 20 | Orchestration Patterns | Coordinate multiple agents (chain, fan-out, debate, hierarchy) |
| 18 | Tool Forge | Create, register, and manage tools for agents |
| 19 | Memory Engine | Short-term and long-term memory for agent continuity |
| 21 | A/B Test Engine | Statistical A/B testing for any module configuration |
| 22 | Bandit Optimizer | Multi-armed bandit for continuous optimization |
| 23 | Feedback Collector | Collect human and automated feedback systematically |

### Dependencies

- Phase 1 complete (agents, prompts, experiments)
- Phase 2 complete (embeddings for memory retrieval)
- Phase 3 optional but beneficial (trained models as agent tools)

### Key Technical Decisions

1. **Orchestration is pattern-based:** Pre-built patterns (chain, fan-out, map-reduce, debate, supervisor) that users compose visually. Not free-form.
2. **Tools are self-describing:** Every tool has a JSON Schema definition that LLMs use for function calling. Tools can be auto-generated from API specs.
3. **Memory is tiered:** Working memory (current conversation), episodic memory (recent interactions), semantic memory (embedded knowledge). Different retrieval strategies per tier.
4. **A/B tests are statistically rigorous:** Sequential testing with proper stopping rules. No peeking without correction.
5. **Bandits are contextual:** Thompson Sampling with contextual features. The optimizer learns which variant works best in which context.
6. **Feedback is multi-signal:** Explicit (thumbs up/down), implicit (task completion, retry rate), and automated (output quality metrics).

### Testing Strategy

- Orchestration patterns tested with mock agents (deterministic responses)
- Tool execution tested with sandboxed tools (filesystem, network isolation)
- Memory retrieval tested with known query/document pairs
- A/B test engine tested with simulated data (verify statistical correctness)
- Bandit tested against known reward distributions (verify convergence)

### Success Criteria

- [ ] Multi-agent chain executes with proper context passing between agents
- [ ] Fan-out pattern distributes work and aggregates results
- [ ] Tools created from OpenAPI spec and usable by agents
- [ ] Agent remembers context from previous interactions
- [ ] A/B test reaches statistical significance and declares winner
- [ ] Bandit converges on best variant faster than uniform A/B test
- [ ] Feedback collector captures signals from multiple sources

### Capabilities Unlocked

After Phase 4, you can:
- Build multi-agent systems (research agent → analysis agent → writing agent)
- Create custom tools that agents can use (API calls, database queries, calculations)
- Agents maintain memory across interactions (remember user preferences, past decisions)
- Run proper A/B tests on any system component (prompts, models, tool selection)
- Use bandit optimization for continuous improvement without waiting for test completion
- Collect and aggregate feedback from users and automated systems
- The flywheel is now fully operational: execute → measure → experiment → improve → repeat

---

## Phase 5: Full Platform (Week 9-10)

### Goal

Complete all 30 modules. Fill remaining gaps in intelligence, advanced optimization, deployment, and governance.

### What Gets Built

| # | Component | Purpose |
|---|-----------|---------|
| 2 | Market Scanner | Monitor market trends, competitors, opportunities |
| 3 | Academic Radar | Track relevant papers, breakthroughs, techniques |
| 4 | Signal Aggregator | Combine signals from multiple sources into actionable intelligence |
| 5 | Domain Knowledge Extractor | Extract structured knowledge from unstructured domain content |
| 24 | Reward Modeler | Learn reward functions from feedback data |
| 25 | Error Analyzer | Categorize, cluster, and diagnose system errors |
| 26 | Deployment Engine | Package and deploy models/agents to production |
| 28 | Reliability Engine | Monitor health, detect anomalies, auto-heal |
| 29 | Governance & Audit | Compliance, access control audit, data lineage |

### Dependencies

- Phase 1-4 complete
- External monitoring infrastructure (for Reliability Engine)
- Container registry (for Deployment Engine)

### Key Technical Decisions

1. **Market Scanner is event-driven:** Monitors RSS, Twitter/X, Product Hunt, Crunchbase on schedules. Publishes `signal.detected` events.
2. **Academic Radar uses Semantic Scholar API:** Tracks papers by topic, citation velocity, and author networks.
3. **Signal Aggregator is a fusion engine:** Combines weak signals from multiple sources into confidence-weighted intelligence.
4. **Reward Modeler uses inverse RL:** Learns what "good" looks like from human feedback data collected by the Feedback Collector.
5. **Error Analyzer clusters errors:** Uses embedding similarity to group related errors and identify root causes.
6. **Deployment is container-based:** Models and agents are packaged as containers with standardized health checks and scaling policies.
7. **Governance is non-blocking:** Audit logging is async. Compliance checks are advisory by default, blocking only for configured policies.

### Testing Strategy

- Market Scanner tested with mock RSS feeds and API responses
- Academic Radar tested with known paper datasets
- Signal Aggregator tested with synthetic signals of known ground truth
- Reward Modeler tested with simulated preference data
- Error Analyzer tested with known error clusters
- Deployment Engine tested with dummy containers in local Docker
- Governance tested with known compliance scenarios (GDPR data requests, access audit)

### Success Criteria

- [ ] Market Scanner identifies relevant trends for a given venture domain
- [ ] Academic Radar surfaces papers relevant to venture's AI approach
- [ ] Signal Aggregator combines market + academic + data signals into ranked opportunities
- [ ] Reward Modeler learns preferences from feedback history
- [ ] Error Analyzer automatically categorizes and diagnoses failures
- [ ] Deployment Engine packages and deploys an agent as a standalone service
- [ ] Reliability Engine detects and recovers from simulated failures
- [ ] Governance audit produces complete data lineage for any output

### Capabilities Unlocked

After Phase 5, you can:
- Monitor your market continuously and get alerted to opportunities/threats
- Stay current on relevant academic research without manual paper reading
- Get fused intelligence from multiple signal sources
- System learns what "good" means from accumulated feedback (reward modeling)
- Errors are automatically analyzed and root-caused
- Deploy trained models and agents to production endpoints
- System self-heals from common failure modes
- Produce compliance reports and data lineage for audit
- Run a complete venture end-to-end: discover → build → deploy → monitor → improve

---

## Phase 6: Visual Builder + Venture Layer (Week 11-12)

### Goal

Polish the user experience. Build the visual graph editor for designing multi-agent systems, create venture templates for common use cases, and deliver the cross-venture dashboard.

### What Gets Built

| Component | Purpose |
|-----------|---------|
| Visual Graph Editor | React Flow-based drag-and-drop agent network designer |
| Venture Templates | Pre-built configurations for HR, Sales, Knowledge Management |
| Cross-Venture Dashboard | Unified view across all ventures with comparative metrics |
| Pattern Library | Reusable agent/pipeline patterns shared across ventures |
| Flywheel Metrics | Visualization of improvement over time (the flywheel effect) |

### Dependencies

- All 30 modules complete (Phase 1-5)
- Frontend foundation from Phase 1 (basic web UI)
- Real usage data from earlier phases (for flywheel metrics)

### Key Technical Decisions

1. **React Flow for graph editor:** Mature library, handles complex node graphs, supports custom nodes/edges, good mobile support.
2. **Templates are composable:** Venture templates are not monolithic — they compose module configurations. Users can mix elements from different templates.
3. **Dashboard is real-time:** WebSocket updates for live metrics. No polling.
4. **Pattern library is versioned:** Patterns are stored as versioned configs. Users can fork and customize.
5. **Flywheel metrics show improvement slopes:** Not just current performance, but rate of improvement over time — the key differentiator.

### Testing Strategy

- Visual editor tested with Playwright (E2E browser tests)
- Venture templates tested by instantiation and validation
- Dashboard tested with simulated metrics data
- Pattern library tested with apply/validate cycle
- Performance testing for real-time WebSocket updates at scale

### Success Criteria

- [ ] User can design a multi-agent system visually by dragging nodes and connecting edges
- [ ] Graph editor generates valid agent orchestration config
- [ ] HR startup template creates a working venture in under 5 minutes
- [ ] Cross-venture dashboard shows comparative metrics across all ventures
- [ ] Pattern library allows saving and reusing agent configurations
- [ ] Flywheel metrics clearly show improvement over time for each venture
- [ ] The platform is usable by a non-technical user for basic venture creation

### Capabilities Unlocked

After Phase 6, you can:
- Design multi-agent systems visually without writing code
- Launch a new venture from a template in minutes
- Compare performance across ventures on a unified dashboard
- Share and reuse proven agent patterns across ventures
- See the flywheel effect visualized: how each venture improves over time
- Onboard new users who can create ventures through the visual builder
- The platform is complete and ready for production use

---

## Phase Summary

| Phase | Weeks | Modules Built | Cumulative | Key Unlock |
|-------|-------|---------------|------------|------------|
| 1 | 1-2 | 5 + kernel | 5/30 | Agents run, costs tracked, experiments started |
| 2 | 3-4 | 5 | 10/30 | Data discovered, ingested, embedded, graphed |
| 3 | 5-6 | 5 | 15/30 | Models trained, evaluated, pipelines running |
| 4 | 7-8 | 6 | 21/30 | Multi-agent, memory, tools, optimization |
| 5 | 9-10 | 9 | 30/30 | Full platform, deploy, monitor, govern |
| 6 | 11-12 | UI + templates | Complete | Visual builder, templates, polish |

### Dependency Graph

```
Phase 1 (Kernel)
    │
    ├── Phase 2 (Data) ──── Phase 3 (ML)
    │                              │
    └── Phase 4 (Multi-Agent + Optimization)
                │
                └── Phase 5 (Full Platform)
                        │
                        └── Phase 6 (Visual Builder)
```

Phase 2 and Phase 4 can partially overlap since Phase 4 depends primarily on Phase 1 (agents) and only optionally on Phase 2 (embeddings for memory). In practice, running them sequentially allows the data layer to inform agent design decisions.

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| LLM API instability | LLM Gateway with fallback providers from day 1 |
| Cost overrun during development | Cost Optimizer active from Phase 1 |
| Module coupling | Event bus enforces loose coupling; no direct module imports |
| Scope creep per module | Each module has a clear BaseModule contract; extras become separate modules |
| Database performance at scale | Partitioning planned from schema design; implemented when growth requires it |
| Frontend complexity | Component library and design system established in Phase 1 minimal UI |
