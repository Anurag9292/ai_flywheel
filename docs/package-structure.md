# Package Structure

## Overview

AI Flywheel is organized as a single Python monorepo package (`ai_flywheel`) with a Next.js frontend (`web/`). The architecture follows an **8-system design** where each system encapsulates a domain of capabilities, connected through a shared Core Kernel and served via multiple interaction channels (Slack bot, Web App, CLI).

```
ai_flywheel/
├── pyproject.toml                    # Single monorepo package
├── docker-compose.yml                # Full local dev environment
├── alembic/                          # Database migrations
│
├── core/                             # System 1: Core Kernel
│   ├── config.py                     # Platform Core (config, secrets)
│   ├── identity.py                   # Identity & Tenancy
│   ├── events.py                     # Event Bus
│   ├── tasks.py                      # Task Runtime
│   ├── traces.py                     # Trace & Observability
│   ├── artifacts.py                  # Artifact Manager
│   ├── database.py                   # DB connection
│   ├── models/                       # SQLAlchemy models
│   └── schemas/                      # Pydantic schemas
│
├── modules/
│   ├── base.py                       # Base module class
│   ├── agent_runtime/                # System 2
│   │   ├── llm_gateway.py
│   │   ├── prompt_studio.py
│   │   ├── agent_factory.py
│   │   ├── tool_forge.py
│   │   ├── memory_engine.py
│   │   ├── human_review.py
│   │   └── policy_engine.py
│   ├── data_knowledge/               # System 3
│   │   ├── universal_ingestor.py
│   │   ├── data_quality.py
│   │   ├── embedding_engine.py
│   │   ├── knowledge_graph.py
│   │   ├── labeling.py
│   │   └── privacy_pii.py
│   ├── ml_evaluation/                # System 4
│   │   ├── feature_factory.py
│   │   ├── model_forge.py
│   │   ├── evaluation.py
│   │   ├── synthetic_data.py
│   │   └── simulation.py
│   ├── product_intelligence/         # System 5
│   │   ├── market_intelligence.py
│   │   ├── customer_discovery.py
│   │   ├── venture_thesis.py
│   │   ├── offer_design.py
│   │   ├── product_experience.py
│   │   └── workflow_blueprint.py
│   ├── experimentation/              # System 6
│   │   ├── experiment_tracker.py
│   │   ├── ab_testing.py
│   │   ├── feedback_collector.py
│   │   ├── metrics_registry.py
│   │   └── cost_optimizer.py
│   ├── deployment/                   # System 7
│   │   ├── deploy_engine.py
│   │   └── reliability.py
│   └── cross_venture/                # System 8
│       ├── pattern_library.py
│       └── meta_learning.py
│
├── ventures/                         # Layer 2
│   ├── base.py
│   ├── registry.py
│   └── templates/
│
├── channels/                         # Multi-channel interaction
│   ├── router.py                     # Conversation Router (brain)
│   ├── slack_bot.py                  # Slack Bolt integration
│   ├── cli.py                        # CLI interface
│   └── websocket.py                  # WebSocket for web app
│
├── api/                              # FastAPI
│   ├── main.py
│   ├── routers/
│   └── middleware/
│
├── web/                              # Next.js frontend
│   ├── app/                          # App Router
│   ├── components/
│   ├── lib/
│   └── stores/
│
└── tests/
    ├── unit/
    ├── integration/
    └── fixtures/
```

---

## Directory Reference

### `core/` — System 1: Core Kernel

**Purpose:** The shared foundation that every system depends on. Provides identity, configuration, task execution, event routing, tracing, and artifact management. No module operates without the kernel.

**Key Files:**

| File | Responsibility |
|------|---------------|
| `config.py` | Platform Core — loads environment variables, manages secrets (via environment or vault), exposes typed `Settings` object using Pydantic BaseSettings. Supports per-venture config overrides, feature flags, and environment-specific behavior. |
| `identity.py` | Identity & Tenancy — user authentication (JWT), role-based authorization (admin, developer, viewer), venture-scoped permissions, API key management, and multi-tenant isolation enforcement. |
| `events.py` | Event Bus — publish/subscribe infrastructure backed by Redis Streams. Events are persisted to the `events` table for replay and audit. Supports wildcard subscriptions, venture-scoped routing, correlation IDs, and consumer groups. |
| `tasks.py` | Task Runtime — manages asynchronous task execution via Celery. Handles task creation, priority queuing, retries with backoff, parent-child task relationships, and status tracking. Provides `@task` decorator for module methods. |
| `traces.py` | Trace & Observability — distributed tracing with span management. Records every operation with input/output, duration, cost, and token usage. Provides `@traced` decorator and context managers for automatic span creation. |
| `artifacts.py` | Artifact Manager — versioned storage for binary outputs (models, datasets, reports). Handles upload to S3/MinIO, version tracking, metadata association, and retrieval by module/venture/type. |
| `database.py` | DB connection — creates the async SQLAlchemy engine, manages session lifecycle with async context managers, provides `get_db()` dependency for FastAPI. Connection pooling via asyncpg. |
| `models/` | SQLAlchemy model definitions. Base model with `id` (UUID), `created_at`, `updated_at`, `deleted_at` (soft delete) audit fields. Venture-scoped mixin. |
| `schemas/` | Pydantic v2 schemas for all API request/response contracts. Shared across routers, modules, and channels. |

**Interactions:**
- Every module imports from `core` — it never imports from `modules`
- `api/` depends on `core.schemas` and `core.database`
- `channels/` uses `core.identity` for auth and `core.events` for real-time updates
- `ventures/` extends `core.models`

**Design Patterns:**
- Dependency Injection (FastAPI `Depends()`)
- Repository Pattern (database access abstracted behind session management)
- Observer Pattern (event bus)
- Decorator Pattern (traces, tasks)
- Configuration as Code (Pydantic BaseSettings)

---

### `modules/` — Systems 2-8

**Purpose:** Contains the business logic organized into seven systems. Each system encapsulates a cohesive domain of capabilities. Every module within a system inherits from `BaseModule`, which provides Task Runtime integration and Trace integration out of the box.

**Key Files:**

| File | Responsibility |
|------|---------------|
| `base.py` | The `BaseModule` abstract class. Defines the contract every module must fulfill. Provides built-in task execution, tracing, event publishing, feedback loops, cost tracking, and venture scoping. |

**System Breakdown:**

| System | Directory | Focus | Modules |
|--------|-----------|-------|---------|
| 2 | `agent_runtime/` | LLM orchestration, agents, tools, memory, safety | LLM Gateway, Prompt Studio, Agent Factory, Tool Forge, Memory Engine, Human Review, Policy Engine |
| 3 | `data_knowledge/` | Data ingestion, quality, embeddings, knowledge, privacy | Universal Ingestor, Data Quality, Embedding Engine, Knowledge Graph, Labeling, Privacy/PII |
| 4 | `ml_evaluation/` | Feature engineering, model training, evaluation, simulation | Feature Factory, Model Forge, Evaluation, Synthetic Data, Simulation |
| 5 | `product_intelligence/` | Market research, customer discovery, offers, product design | Market Intelligence, Customer Discovery, Venture Thesis, Offer Design, Product Experience, Workflow Blueprint |
| 6 | `experimentation/` | A/B testing, metrics, feedback, cost optimization | Experiment Tracker, A/B Testing, Feedback Collector, Metrics Registry, Cost Optimizer |
| 7 | `deployment/` | Deployment pipelines, reliability, rollback | Deploy Engine, Reliability |
| 8 | `cross_venture/` | Pattern reuse, meta-learning across ventures | Pattern Library, Meta-Learning |

---

#### System 2: `agent_runtime/`

**Purpose:** The AI execution layer. Manages LLM access, prompt engineering, agent creation and execution, tool management, memory, and safety guardrails.

| File | Responsibility |
|------|---------------|
| `llm_gateway.py` | Unified interface to LLM providers via litellm. Model routing, fallback chains, cost-aware selection, response caching, rate limiting. |
| `prompt_studio.py` | Versioned prompt management. Template rendering, variable injection, performance tracking, automated improvement suggestions. |
| `agent_factory.py` | Creates and configures agents from archetypes. Manages agent lifecycle, version control, and performance scoring. |
| `tool_forge.py` | Tool registry and execution. Manages external integrations (Google Ads, LinkedIn, Stripe, etc.), credential rotation, schema validation, and usage analytics. |
| `memory_engine.py` | Agent memory — short-term (conversation), long-term (vector store), and episodic (past executions). Retrieval and relevance ranking. |
| `human_review.py` | Human-in-the-loop review queue. Routes low-confidence AI decisions to humans, collects feedback, and uses it to improve future decisions. |
| `policy_engine.py` | Safety guardrails and governance rules. Content filtering, budget enforcement, action constraints, and compliance policies. |

**Key Interactions:**
- LLM Gateway is called by every module that needs LLM access
- Tool Forge integrates with external ad platforms, data APIs, payment systems
- Human Review publishes to Slack bot for real-time approval workflows
- Policy Engine is consulted before any agent action is executed

---

#### System 3: `data_knowledge/`

**Purpose:** Data lifecycle management — from raw ingestion through quality assessment, embedding generation, knowledge structuring, and privacy compliance.

| File | Responsibility |
|------|---------------|
| `universal_ingestor.py` | Ingests data from any source (APIs, files, web scraping, databases). Normalizes formats, handles pagination, and manages incremental updates. |
| `data_quality.py` | Assesses and improves data quality. Schema validation, completeness checks, anomaly detection, deduplication, and quality scoring. |
| `embedding_engine.py` | Generates and manages vector embeddings. Supports multiple models, batch processing, incremental updates, and dimension tracking. |
| `knowledge_graph.py` | Builds and queries knowledge graphs from unstructured data. Entity extraction, relationship detection, confidence scoring, and graph traversal. |
| `labeling.py` | Data labeling pipeline. Supports human annotation, LLM-assisted labeling, active learning selection, and inter-annotator agreement tracking. |
| `privacy_pii.py` | PII detection and handling. Identifies sensitive data, applies masking/anonymization, manages consent, and ensures regulatory compliance. |

---

#### System 4: `ml_evaluation/`

**Purpose:** Machine learning lifecycle — feature engineering, model training, evaluation, synthetic data generation, and simulation.

| File | Responsibility |
|------|---------------|
| `feature_factory.py` | Feature engineering pipeline. Computes, stores, and serves features for ML models. Handles feature versioning and lineage tracking. |
| `model_forge.py` | Model training orchestration. Hyperparameter tuning, distributed training, checkpoint management, and model registry. |
| `evaluation.py` | Model evaluation framework. Automated benchmarking, regression detection, A/B comparison, and holdout testing. |
| `synthetic_data.py` | Generates synthetic training data. LLM-based generation, statistical augmentation, and quality validation of generated data. |
| `simulation.py` | Simulates system behavior before deployment. Backtesting strategies, load simulation, and scenario modeling. |

---

#### System 5: `product_intelligence/`

**Purpose:** Market and product intelligence — understanding markets, customers, and designing offers and product experiences.

| File | Responsibility |
|------|---------------|
| `market_intelligence.py` | Market research automation. Competitor analysis, trend detection, TAM/SAM estimation, and opportunity scoring. |
| `customer_discovery.py` | Customer interview analysis. Transcription processing, pain extraction, severity scoring, willingness-to-pay analysis, and emotional intensity measurement. |
| `venture_thesis.py` | Hypothesis generation and validation. Formulates testable business hypotheses, tracks validation status, and computes confidence. |
| `offer_design.py` | Offer construction. ICP definition, positioning, pricing strategy, messaging, objection handling, and landing copy generation. |
| `product_experience.py` | Product experience design. User journey mapping, feature prioritization, and UX recommendation. |
| `workflow_blueprint.py` | Workflow design. Maps business processes, identifies automation opportunities, and generates implementation specs. |

---

#### System 6: `experimentation/`

**Purpose:** The scientific method applied to the platform. A/B testing, metrics tracking, feedback collection, and cost optimization.

| File | Responsibility |
|------|---------------|
| `experiment_tracker.py` | Experiment lifecycle management. Create, configure, run, analyze, and conclude experiments. Statistical significance calculation. |
| `ab_testing.py` | A/B test infrastructure. Traffic splitting, variant allocation, metric collection, and winner determination. |
| `feedback_collector.py` | Multi-source feedback ingestion. User ratings, implicit signals (clicks, time-on-task), automated quality scores, and downstream outcome tracking. |
| `metrics_registry.py` | Centralized metric definitions. Numerator/denominator specs, window functions, targets, guardrails, and owner assignment. |
| `cost_optimizer.py` | Cost management and optimization. Budget tracking, anomaly detection, model downgrade suggestions, and provider routing for cost efficiency. |

---

#### System 7: `deployment/`

**Purpose:** Getting things to production safely and keeping them running.

| File | Responsibility |
|------|---------------|
| `deploy_engine.py` | Deployment pipeline. Blue-green deployments, canary releases, rollback automation, and environment management. |
| `reliability.py` | System reliability. Health monitoring, incident detection, automatic remediation, SLO tracking, and chaos testing. |

---

#### System 8: `cross_venture/`

**Purpose:** Learning across ventures. Extracts patterns from successful ventures and applies them to new ones.

| File | Responsibility |
|------|---------------|
| `pattern_library.py` | Catalogs reusable patterns. Successful agent configurations, prompt templates, workflow designs, and tool compositions that worked well. |
| `meta_learning.py` | Learns meta-strategies. Identifies which patterns apply to which domains, predicts success likelihood, and suggests configurations for new ventures. |

---

### `ventures/` — Venture Layer

**Purpose:** Manages the lifecycle of AI ventures — isolated workspaces that combine systems into purpose-built applications. A venture is a namespace that scopes all data, agents, experiments, and costs.

**Key Files:**

| File | Responsibility |
|------|---------------|
| `base.py` | `BaseVenture` class — defines venture lifecycle (create, configure, activate, pause, archive). Manages which modules are enabled and their configuration. |
| `registry.py` | Tracks all ventures, handles creation/deletion, enforces naming and resource limits. Provides venture discovery and status aggregation. |
| `templates/` | Pre-built venture configurations. Each template specifies which modules to enable, default agent configurations, initial prompts, and recommended integrations. |

**Interactions:**
- Ventures reference modules but don't contain them — they configure module instances
- API routes are venture-scoped (most requests include `venture_id`)
- Templates instantiate modules with sensible defaults
- Cross-venture system reads from all ventures to extract patterns

**Design Patterns:**
- Factory Pattern (templates produce configured ventures)
- Namespace Pattern (venture as isolation boundary)
- Configuration-driven (ventures are primarily config, not code)

---

### `channels/` — Multi-Channel Interaction

**Purpose:** Provides multiple interaction surfaces to the platform — Slack bot for conversational access, CLI for developer automation, and WebSocket for the real-time web app. All channels share a central Conversation Router that handles intent detection and context management.

**Key Files:**

| File | Responsibility |
|------|---------------|
| `router.py` | Conversation Router — the "brain" of multi-channel interaction. Detects user intent, maintains conversation context across channels, routes to appropriate modules, and formats responses for each channel. Handles context switching (e.g., user starts in Slack, continues in web). |
| `slack_bot.py` | Slack Bolt integration. Handles events, slash commands (`/flywheel`), interactive messages (approvals, selections), modals, app home tab, and thread-based conversations. Translates Slack-specific formats to/from the router. |
| `cli.py` | CLI interface (Click-based). Provides commands for all major operations. Supports piped input/output, JSON output mode for scripting, and interactive prompts. Used in CI/CD and developer workflows. |
| `websocket.py` | WebSocket handler for the Next.js web app. Streams agent execution tokens, real-time metric updates, experiment progress, and notification delivery. Manages connection lifecycle and reconnection. |

**Interactions:**
- All channels call `router.py` — never modules directly
- Router uses `core.identity` to authenticate across channels
- Router maintains session state in Redis (shared across channels)
- Slack bot publishes human review responses back through `core.events`
- WebSocket streams events from `core.events` to the frontend

**Design Patterns:**
- Adapter Pattern (each channel adapts to/from the router's unified format)
- Strategy Pattern (router selects response strategy based on channel capabilities)
- Mediator Pattern (router mediates between channels and modules)

---

### `api/` — FastAPI Application

**Purpose:** The HTTP and WebSocket interface to the platform. Exposes REST endpoints for all operations, serves as the backbone for the web frontend, and provides webhook endpoints for external integrations.

**Key Files:**

| File | Responsibility |
|------|---------------|
| `main.py` | FastAPI app creation, middleware setup (CORS, auth, telemetry, rate limiting), lifespan management (startup/shutdown hooks), router registration. |
| `routers/` | API routes organized by domain — ventures, agents, experiments, prompts, datasets, models, tools, monitoring, webhooks. |
| `middleware/` | Request/response middleware — authentication, request tracing, rate limiting, error formatting, and venture context injection. |

**Interactions:**
- Routers depend on `core.schemas` for request/response typing
- Routers call module methods (never raw DB queries)
- Middleware injects venture context and trace IDs into every request
- WebSocket endpoints (`channels/websocket.py`) are mounted here

**Design Patterns:**
- Router separation (one file per domain)
- Dependency Injection (FastAPI's `Depends` for auth, DB, modules)
- Middleware pipeline (composable request processing)
- CQRS-lite (separate read/write paths where beneficial)

---

### `web/` — Next.js Frontend

**Purpose:** Full-stack frontend providing the visual interface for the entire platform. Built with Next.js (App Router), TypeScript, and React. Server components handle data fetching; client components handle interactivity.

**Key Routes:**

| Route | Purpose |
|-------|---------|
| `/` (Dashboard) | Overview of all ventures — health, costs, key metrics, recent activity, system status. |
| `/ventures/[id]` | Venture detail view — configuration, active modules, metrics, and management. |
| `/agents` | Visual node-based editor (React Flow) for designing multi-agent systems and workflows. |
| `/prompts` | Side-by-side prompt editing with live testing, version comparison, and performance metrics. |
| `/experiments` | Create hypotheses, configure variants, monitor running experiments, view statistical results. |
| `/data` | Browse discovered datasets, preview schemas, trigger ingestion, view quality reports. |
| `/models` | Configure training runs, compare model metrics, promote to production, view lineage. |
| `/market` | Market intelligence dashboards, competitor analysis, customer discovery insights. |
| `/ops` | Real-time cost tracking, error rates, latency, system health, deployment status. |

**Key Directories:**

| Directory | Purpose |
|-----------|---------|
| `app/` | Next.js App Router pages and layouts. Server components for data fetching, client components for interactivity. |
| `components/` | Reusable UI components — graph editor (React Flow), charts (Recharts), data tables, forms, and shadcn/ui primitives. |
| `lib/` | API client (typed fetch wrappers), utilities, constants, and type definitions. |
| `stores/` | Zustand state management — one store per domain (agents, experiments, ventures, etc.). |

**Interactions:**
- Server components fetch data directly from the Python FastAPI backend
- Client components use `@tanstack/react-query` for mutations and real-time updates
- WebSocket connections for real-time agent status streaming and notifications
- Vercel AI SDK handles streaming LLM responses with `useChat` hooks
- State management via Zustand stores (one per domain)

**Design Patterns:**
- Server components for data fetching, client components for interactivity
- Component composition (small, reusable components via shadcn/ui)
- Store-per-domain (Zustand slices for client state)
- Streaming responses with Vercel AI SDK for LLM outputs
- Route-based code splitting (automatic with App Router)
- Optimistic updates for responsive UI

---

### `tests/` — Test Suite

**Purpose:** Comprehensive testing at unit, integration, and end-to-end levels.

| Directory | Purpose |
|-----------|---------|
| `unit/` | Tests individual module methods in isolation with mocked dependencies. Fast, no external services. |
| `integration/` | Tests module interactions, database operations, API endpoints, and channel routing. Uses test database and docker services. |
| `fixtures/` | Shared test data — sample ventures, mock LLM responses, test datasets, Slack event payloads. |

**Design Patterns:**
- pytest with async support (pytest-asyncio)
- Factory Boy for model fixtures
- Test database with automatic migration
- Dependency override for FastAPI testing
- Channel mocks (simulated Slack events, CLI invocations)

---

### `alembic/` — Database Migrations

**Purpose:** Manages database schema evolution using Alembic with async support.

**Conventions:**
- One migration per logical change
- Migrations are reversible (downgrade path always defined)
- Migration naming: `YYYYMMDD_HHMM_description.py`
- Auto-generation from SQLAlchemy models with manual review
- Data migrations separated from schema migrations

---

## Module Base Class

Every module inherits from `BaseModule`, which provides Task Runtime integration and Trace integration built in. This ensures consistent behavior across all modules and enforces the flywheel pattern (every action feeds back into improvement).

```python
from core.tasks import TaskRuntime
from core.traces import Tracer, traced
from core.events import EventBus
from core.artifacts import ArtifactManager


class BaseModule:
    """
    Every module gets these capabilities for free.
    
    Built-in integrations:
    - Task Runtime: async task execution with retries, priority, and DAGs
    - Tracing: automatic span creation for all operations
    - Event Bus: inter-module communication
    - Artifacts: versioned binary storage
    """
    
    # Identity
    name: str
    system: str          # Which system this module belongs to (2-8)
    version: str
    
    # Injected dependencies
    task_runtime: TaskRuntime
    tracer: Tracer
    event_bus: EventBus
    artifact_manager: ArtifactManager
    
    # Lifecycle
    async def initialize(self, venture_id: str | None = None):
        """Called when module is activated. Subscribes to events, loads config."""
        ...
    
    async def shutdown(self):
        """Graceful teardown. Flushes pending tasks, closes connections."""
        ...
    
    # ─── Task Runtime Integration ───────────────────────────────────
    
    async def submit_task(
        self,
        task_type: str,
        input: dict,
        priority: int = 5,
        parent_task_id: str | None = None,
    ) -> str:
        """Submit a task for async execution. Returns task_id."""
        return await self.task_runtime.submit(
            module_name=self.name,
            venture_id=self.venture_context.id if self.venture_context else None,
            task_type=task_type,
            input=input,
            priority=priority,
            parent_task_id=parent_task_id,
        )
    
    async def get_task_status(self, task_id: str) -> TaskStatus:
        """Check task progress."""
        return await self.task_runtime.get_status(task_id)
    
    async def await_task(self, task_id: str, timeout: float = 300) -> TaskResult:
        """Wait for task completion with timeout."""
        return await self.task_runtime.await_result(task_id, timeout=timeout)
    
    # ─── Trace Integration ──────────────────────────────────────────
    
    @traced  # Decorator automatically creates spans
    async def execute(self, operation: str, input: dict) -> dict:
        """
        Primary execution method. Override in subclasses.
        Automatically traced with input/output, duration, cost.
        """
        raise NotImplementedError
    
    def span(self, operation: str) -> SpanContext:
        """Create a child span for sub-operations."""
        return self.tracer.span(
            module_name=self.name,
            operation=operation,
            venture_id=self.venture_context.id if self.venture_context else None,
        )
    
    # ─── Event Bus (inter-module communication) ─────────────────────
    
    async def publish(self, event_type: str, payload: dict):
        """Publish event with automatic correlation ID and venture scoping."""
        await self.event_bus.publish(
            event_type=event_type,
            source_module=self.name,
            venture_id=self.venture_context.id if self.venture_context else None,
            payload=payload,
        )
    
    async def subscribe(self, event_type: str, handler: Callable):
        """Subscribe to events. Handler receives typed EventPayload."""
        await self.event_bus.subscribe(event_type, handler)
    
    # ─── Feedback Loop ──────────────────────────────────────────────
    
    async def record_outcome(self, action_id: str, outcome: Outcome):
        """Record the outcome of an action for flywheel learning."""
        ...
    
    async def get_performance_history(
        self, period: str = "7d"
    ) -> list[Metric]:
        """Retrieve performance metrics over time."""
        ...
    
    async def suggest_improvements(self) -> list[Suggestion]:
        """LLM-powered analysis of outcome patterns to suggest improvements."""
        ...
    
    # ─── Experiment Integration ─────────────────────────────────────
    
    async def run_experiment(
        self, variants: list, metric: str, duration: str = "24h"
    ) -> ExperimentResult:
        """Run an A/B experiment on module behavior."""
        ...
    
    # ─── Cost Tracking ──────────────────────────────────────────────
    
    async def track_cost(
        self, operation: str, amount: float, provider: str,
        tokens_input: int = 0, tokens_output: int = 0
    ):
        """Record cost of an operation. Auto-attributed to venture."""
        ...
    
    async def get_cost_summary(self, period: str = "30d") -> CostReport:
        """Cost breakdown by operation, provider, and time."""
        ...
    
    # ─── Artifact Management ────────────────────────────────────────
    
    async def store_artifact(
        self, name: str, data: bytes, artifact_type: str,
        metadata: dict | None = None
    ) -> str:
        """Store a versioned artifact. Returns artifact_id."""
        return await self.artifact_manager.store(
            venture_id=self.venture_context.id if self.venture_context else None,
            module_name=self.name,
            name=name,
            artifact_type=artifact_type,
            data=data,
            metadata=metadata or {},
        )
    
    async def load_artifact(
        self, artifact_id: str | None = None,
        name: str | None = None, version: int | None = None
    ) -> bytes:
        """Load artifact by ID or by name (latest version if version not specified)."""
        ...
    
    # ─── Venture Scoping ────────────────────────────────────────────
    
    @property
    def venture_context(self) -> VentureContext | None:
        """Current venture context. None for global modules."""
        ...
```

---

## Capability Deep Dive

### Task Runtime Integration

Every module operation that takes more than a few seconds is executed as a **Task**. Tasks provide:

- **Async execution**: Non-blocking. Submit and poll, or submit and await.
- **Priority queuing**: Critical tasks (human-facing) execute before background tasks.
- **Retries with backoff**: Configurable retry policies for transient failures.
- **Parent-child relationships**: Complex operations decompose into task trees.
- **Status tracking**: Every task has a lifecycle (pending → running → completed/failed).
- **Celery backend**: Tasks execute on distributed workers, scaling horizontally.

```python
# Submit a background task
task_id = await self.submit_task(
    task_type="train_model",
    input={"dataset_id": "...", "config": {...}},
    priority=3,  # Higher priority (1=highest, 10=lowest)
)

# Check status later
status = await self.get_task_status(task_id)
# TaskStatus(state="running", progress=0.45, started_at=...)

# Or await completion
result = await self.await_task(task_id, timeout=600)
# TaskResult(output={...}, duration_ms=45230, cost=0.12)
```

### Trace Integration

Every module operation is automatically traced, creating a complete picture of system behavior:

- **Automatic spans**: The `@traced` decorator wraps any method with span creation.
- **Input/output recording**: What went in and what came out (with configurable redaction).
- **Cost attribution**: LLM costs, API costs, and compute costs are attached to spans.
- **Token counting**: Input and output tokens for LLM calls.
- **Duration tracking**: Millisecond-precision timing.
- **Correlation**: Traces link across modules via correlation IDs.

```python
@traced
async def analyze_market(self, query: str) -> MarketReport:
    # This entire method is automatically wrapped in a span
    
    async with self.span("fetch_competitors") as span:
        competitors = await self.fetch_competitors(query)
        span.set_attribute("competitor_count", len(competitors))
    
    async with self.span("generate_report") as span:
        report = await self.llm_gateway.complete(...)
        # Cost and tokens automatically recorded
    
    return report
```

### Event Bus

Modules communicate through typed events, never direct imports. This ensures loose coupling and allows the system to scale horizontally.

```python
# Publisher (e.g., Data Quality finds an issue)
await self.publish("data.quality_issue", {
    "dataset_id": "...",
    "issue_type": "missing_values",
    "severity": "high",
    "affected_columns": ["email", "phone"]
})

# Subscriber (e.g., Universal Ingestor re-processes)
await self.subscribe("data.quality_issue", self.handle_quality_issue)
```

### Feedback Loop

The core flywheel mechanism. Every module records the outcomes of its actions, enabling continuous improvement:

```python
# After an agent completes a task
await self.record_outcome(
    action_id="agent_exec_123",
    outcome=Outcome(
        type="quality",
        value=0.92,
        metadata={"user_rating": 5, "latency_ms": 340}
    )
)

# Get improvement suggestions (powered by pattern analysis)
suggestions = await self.suggest_improvements()
# [Suggestion(action="increase_temperature", confidence=0.78, evidence="...")]
```

---

## Design Philosophy

### Why 8 Systems?

The 8-system architecture balances cohesion and separation:
- Systems group modules that frequently interact and share concepts
- Each system has a clear responsibility boundary
- Systems can evolve independently while sharing the kernel
- The numbering provides a clear dependency direction (lower systems don't depend on higher ones)

### Why Multi-Channel?

Users interact with AI tools in different contexts:
- **Slack**: Quick questions, approvals, notifications (low-friction, conversational)
- **Web**: Deep analysis, visual workflows, complex configuration (high-fidelity)
- **CLI**: Automation, scripting, CI/CD integration (developer-first)

The Conversation Router ensures all channels share context — start a conversation in Slack, continue it in the web UI with full history.

### Why a Monorepo?

- **Shared types** — Pydantic schemas and SQLAlchemy models are used across modules, API, channels, and tests without version drift
- **Atomic refactoring** — Rename a field and fix all references in one commit
- **Single dependency lockfile** — No diamond dependency conflicts between packages
- **Simplified CI** — One test suite, one Docker build, one deploy artifact
- **Channel consistency** — All interaction surfaces import from the same code

### Event Bus as Seam

The event bus is the primary mechanism that would enable future service extraction. If Module X needs to become its own service, it simply subscribes to events over a message broker instead of in-process. No other code changes required.

### JSONB for Flexibility

Configuration, metadata, and variant payloads use JSONB columns. This allows modules to evolve their schemas without database migrations for every field addition. Structured columns are reserved for fields that need indexing, foreign keys, or type enforcement.
