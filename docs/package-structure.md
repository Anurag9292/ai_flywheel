# Package Structure

## Overview

AI Flywheel is organized as a single Python monorepo package (`ai_flywheel`) with a Next.js frontend (`web/`). The architecture follows a modular, domain-driven design where 30 utility modules plug into a shared kernel, scoped by venture namespaces.

```
ai_flywheel/
├── pyproject.toml                    # Single monorepo package
├── docker-compose.yml                # Full local dev environment
├── alembic/                          # Database migrations
│
├── core/                             # Shared kernel
│   ├── config.py                     # Settings, env vars, secrets
│   ├── database.py                   # DB connection, session management
│   ├── events.py                     # Event bus (publish/subscribe)
│   ├── models/                       # SQLAlchemy base models
│   │   ├── base.py                   # Base model with audit fields
│   │   ├── venture.py                # Venture namespace model
│   │   └── feedback.py              # Universal feedback model
│   ├── schemas/                      # Pydantic schemas (API contracts)
│   ├── auth.py                       # Authentication/authorization
│   └── telemetry.py                  # Logging, metrics, tracing
│
├── modules/                          # The 30 utils
│   ├── __init__.py                   # Module registry & discovery
│   ├── base.py                       # Base module class
│   │
│   ├── intelligence/                 # Category A: Modules 1-5
│   │   ├── dataset_scout.py
│   │   ├── market_scanner.py
│   │   ├── academic_radar.py
│   │   ├── signal_aggregator.py
│   │   └── domain_knowledge_extractor.py
│   │
│   ├── data_engineering/             # Category B: Modules 6-10
│   │   ├── universal_ingestor.py
│   │   ├── data_quality_engine.py
│   │   ├── feature_factory.py
│   │   ├── synthetic_data_generator.py
│   │   └── knowledge_graph_builder.py
│   │
│   ├── ml_pipeline/                  # Category C: Modules 11-15
│   │   ├── model_forge.py
│   │   ├── embedding_engine.py
│   │   ├── experiment_tracker.py
│   │   ├── evaluation_framework.py
│   │   └── pipeline_orchestrator.py
│   │
│   ├── agent_infra/                  # Category D: Modules 16-20
│   │   ├── prompt_studio.py
│   │   ├── agent_factory.py
│   │   ├── tool_forge.py
│   │   ├── memory_engine.py
│   │   └── orchestration_patterns.py
│   │
│   ├── experimentation/              # Category E: Modules 21-25
│   │   ├── ab_test_engine.py
│   │   ├── bandit_optimizer.py
│   │   ├── feedback_collector.py
│   │   ├── reward_modeler.py
│   │   └── error_analyzer.py
│   │
│   └── operations/                   # Category F: Modules 26-30
│       ├── deployment_engine.py
│       ├── cost_optimizer.py
│       ├── reliability_engine.py
│       ├── governance_audit.py
│       └── llm_gateway.py
│
├── ventures/                         # Venture layer
│   ├── __init__.py
│   ├── base.py                       # Base Venture class
│   ├── registry.py                   # Venture registry & lifecycle
│   └── templates/                    # Pre-built venture templates
│       ├── hr_startup.py
│       ├── sales_startup.py
│       └── knowledge_mgmt.py
│
├── api/                              # FastAPI application
│   ├── main.py                       # App entry point
│   ├── routers/                      # API routes per module
│   │   ├── ventures.py
│   │   ├── agents.py
│   │   ├── experiments.py
│   │   ├── prompts.py
│   │   ├── datasets.py
│   │   ├── models.py
│   │   └── monitoring.py
│   └── websockets/                   # Real-time updates
│       ├── agent_stream.py
│       └── experiment_stream.py
│
├── web/                              # Next.js frontend
│   ├── package.json
│   ├── next.config.ts
│   ├── app/                          # Next.js App Router
│   │   ├── layout.tsx                # Root layout
│   │   ├── page.tsx                  # Dashboard (all ventures overview)
│   │   ├── ventures/
│   │   │   └── [id]/page.tsx         # Venture detail/builder
│   │   ├── agents/
│   │   │   └── page.tsx              # Visual agent network editor
│   │   ├── prompts/
│   │   │   └── page.tsx              # Prompt engineering UI
│   │   ├── experiments/
│   │   │   └── page.tsx              # Experiment management
│   │   ├── data/
│   │   │   └── page.tsx              # Dataset discovery & browsing
│   │   ├── models/
│   │   │   └── page.tsx              # ML model training & eval
│   │   └── ops/
│   │       └── page.tsx              # Monitoring & costs
│   ├── components/
│   │   ├── graph-editor/             # React Flow based node editor
│   │   ├── charts/                   # Visualization components
│   │   └── ui/                       # shadcn/ui components
│   ├── lib/                          # API client, utilities
│   └── stores/                       # Zustand state management
│
└── tests/
    ├── unit/
    ├── integration/
    └── fixtures/
```

---

## Directory Reference

### `core/` — Shared Kernel

**Purpose:** Provides the foundational infrastructure that every other component depends on. No module or venture operates without the kernel.

**Key Files:**

| File | Responsibility |
|------|---------------|
| `config.py` | Loads environment variables, manages secrets (via environment or vault), exposes typed `Settings` object using Pydantic BaseSettings. Supports per-venture config overrides. |
| `database.py` | Creates the async SQLAlchemy engine, manages session lifecycle with async context managers, provides `get_db()` dependency for FastAPI. Connection pooling via asyncpg. |
| `events.py` | In-process async event bus using publish/subscribe. Events are persisted to the `events` table for replay and audit. Supports wildcard subscriptions and venture-scoped routing. |
| `models/base.py` | Declarative base with `id` (UUID), `created_at`, `updated_at`, `deleted_at` (soft delete) audit fields. Mixin for venture-scoped models. |
| `models/venture.py` | The Venture SQLAlchemy model — top-level namespace that scopes all data. |
| `models/feedback.py` | Universal outcome/feedback model. Every module records outcomes here for the flywheel to learn from. |
| `schemas/` | Pydantic v2 schemas for all API request/response contracts. Shared across routers and modules. |
| `auth.py` | JWT-based authentication, role-based authorization (admin, developer, viewer). Venture-scoped permissions. |
| `telemetry.py` | Structured logging (structlog), OpenTelemetry traces, Prometheus metrics export. |

**Interactions:**
- Every module imports from `core` — it never imports from `modules`
- `api/` depends on `core.schemas` and `core.database`
- `ventures/` extends `core.models.venture`

**Design Patterns:**
- Dependency Injection (FastAPI `Depends()`)
- Repository Pattern (database access abstracted behind session management)
- Observer Pattern (event bus)
- Configuration as Code (Pydantic BaseSettings)

---

### `modules/` — The 30 Utility Modules

**Purpose:** Contains the actual business logic organized into six categories. Each module is a self-contained unit that implements a specific capability, inheriting standard behaviors from `BaseModule`.

**Key Files:**

| File | Responsibility |
|------|---------------|
| `__init__.py` | Module registry — auto-discovers modules via class inspection, provides `get_module(name)` and `list_modules()`. |
| `base.py` | The `BaseModule` abstract class. Defines the contract every module must fulfill. Provides free capabilities (events, feedback, experiments, cost tracking). |

**Category Breakdown:**

| Category | Modules | Focus |
|----------|---------|-------|
| `intelligence/` | 1-5 | Finding and monitoring external data, research, signals |
| `data_engineering/` | 6-10 | Ingestion, quality, features, synthetic data, knowledge graphs |
| `ml_pipeline/` | 11-15 | Model training, embeddings, evaluation, orchestration |
| `agent_infra/` | 16-20 | Prompts, agents, tools, memory, multi-agent coordination |
| `experimentation/` | 21-25 | A/B tests, bandits, feedback, rewards, error analysis |
| `operations/` | 26-30 | Deploy, cost, reliability, governance, LLM routing |

**Interactions:**
- Modules communicate via the event bus (`core.events`), never by direct import
- Modules are instantiated per-venture (scoped) or globally (shared services like LLM Gateway)
- Modules register with the module registry on import

**Design Patterns:**
- Strategy Pattern (each module is a pluggable strategy)
- Template Method (BaseModule defines skeleton, subclasses fill in)
- Event-Driven Architecture (loose coupling via events)
- Plugin Architecture (auto-discovery, registry)

---

### `ventures/` — Venture Layer

**Purpose:** Manages the lifecycle of AI ventures — isolated workspaces that combine modules into purpose-built applications. A venture is a namespace that scopes data, agents, experiments, and costs.

**Key Files:**

| File | Responsibility |
|------|---------------|
| `base.py` | `BaseVenture` class — defines venture lifecycle (create, configure, activate, pause, archive). Manages which modules are enabled for a venture. |
| `registry.py` | Tracks all ventures, handles creation/deletion, enforces naming and resource limits. |
| `templates/` | Pre-built venture configurations. Each template specifies which modules to enable, default agent configurations, and initial prompts. |

**Interactions:**
- Ventures reference modules but don't contain them — they configure module instances
- API routes are venture-scoped (most requests include `venture_id`)
- Templates instantiate modules with sensible defaults

**Design Patterns:**
- Factory Pattern (templates produce configured ventures)
- Namespace Pattern (venture as isolation boundary)
- Configuration-driven (ventures are primarily config, not code)

---

### `api/` — FastAPI Application

**Purpose:** The HTTP and WebSocket interface to the platform. Exposes REST endpoints for all operations and real-time streams for live updates.

**Key Files:**

| File | Responsibility |
|------|---------------|
| `main.py` | FastAPI app creation, middleware setup (CORS, auth, telemetry), lifespan management (startup/shutdown hooks), router registration. |
| `routers/ventures.py` | CRUD for ventures, status, metrics summary. |
| `routers/agents.py` | Agent definitions, execution triggers, execution history. |
| `routers/experiments.py` | Create/monitor/conclude experiments across any module. |
| `routers/prompts.py` | Prompt CRUD, version management, A/B testing integration. |
| `routers/datasets.py` | Dataset discovery results, ingestion triggers, quality reports. |
| `routers/models.py` | ML model training, evaluation, deployment status. |
| `routers/monitoring.py` | Cost dashboards, health checks, system metrics. |
| `websockets/agent_stream.py` | Streams agent execution tokens and tool calls in real-time. |
| `websockets/experiment_stream.py` | Live experiment progress and results. |

**Interactions:**
- Routers depend on `core.schemas` for request/response typing
- Routers call module methods (never raw DB queries)
- WebSockets subscribe to the event bus for real-time data

**Design Patterns:**
- Router separation (one file per domain)
- Dependency Injection (FastAPI's `Depends` for auth, DB, modules)
- CQRS-lite (separate read/write paths where beneficial)

---

### `web/` — Next.js Frontend

**Purpose:** Full-stack frontend providing the visual interface for the entire platform. Built with Next.js (App Router), TypeScript, and Zustand for client state management. Server components handle data fetching; client components handle interactivity.

**Key Routes:**

| Route | Purpose |
|-------|---------|
| `/` (Dashboard) | Overview of all ventures — health, costs, key metrics, recent activity. |
| `/ventures/[id]` | Venture detail view and builder wizard for creating/configuring ventures. |
| `/agents` | Visual node-based editor (React Flow) for designing multi-agent systems. |
| `/prompts` | Side-by-side prompt editing with live testing, version comparison, and performance metrics. |
| `/experiments` | Create hypotheses, configure variants, monitor running experiments, view results. |
| `/data` | Browse discovered datasets, preview schemas, trigger ingestion. |
| `/models` | Configure training runs, compare model metrics, promote to production. |
| `/ops` | Real-time cost tracking, error rates, latency, system health. |

**Interactions:**
- Server components fetch data directly from the Python FastAPI backend
- Client components use `@tanstack/react-query` for mutations and real-time updates
- API routes in Next.js act as a BFF (Backend-for-Frontend) layer where needed
- WebSocket connections for real-time agent status streaming
- State management via Zustand stores (one per domain)

**Design Patterns:**
- Server components for data fetching, client components for interactivity
- Component composition (small, reusable components via shadcn/ui)
- Store-per-domain (Zustand slices for client state)
- Streaming responses with Vercel AI SDK for LLM outputs
- Route-based code splitting (automatic with App Router)

---

### `tests/` — Test Suite

**Purpose:** Comprehensive testing at unit, integration, and end-to-end levels.

| Directory | Purpose |
|-----------|---------|
| `unit/` | Tests individual module methods in isolation with mocked dependencies. Fast, no external services. |
| `integration/` | Tests module interactions, database operations, API endpoints. Uses test database and docker services. |
| `fixtures/` | Shared test data — sample ventures, mock LLM responses, test datasets. |

**Design Patterns:**
- pytest with async support (pytest-asyncio)
- Factory Boy for model fixtures
- Test database with automatic migration
- Dependency override for FastAPI testing

---

### `alembic/` — Database Migrations

**Purpose:** Manages database schema evolution using Alembic with async support.

**Conventions:**
- One migration per logical change
- Migrations are reversible (downgrade path always defined)
- Migration naming: `YYYYMMDD_HHMM_description.py`
- Auto-generation from SQLAlchemy models with manual review

---

## Module Base Class

Every module inherits from `BaseModule`, which provides a rich set of capabilities out of the box. This ensures consistent behavior across all 30 modules and enforces the flywheel pattern (every action feeds back into improvement).

```python
class BaseModule:
    """Every module gets these capabilities for free."""
    
    # Identity
    name: str
    category: str
    version: str
    
    # Lifecycle
    async def initialize(self, venture_id: str | None = None)
    async def shutdown(self)
    
    # Event Bus (inter-module communication)
    async def publish(self, event_type: str, payload: dict)
    async def subscribe(self, event_type: str, handler: Callable)
    
    # Feedback Loop (built into every module)
    async def record_outcome(self, action_id: str, outcome: Outcome)
    async def get_performance_history(self) -> list[Metric]
    async def suggest_improvements(self) -> list[Suggestion]
    
    # Experiment Integration
    async def run_experiment(self, variants: list, metric: str) -> ExperimentResult
    
    # Cost Tracking
    async def track_cost(self, operation: str, cost: float)
    async def get_cost_summary(self, period: str) -> CostReport
    
    # Audit
    async def log_action(self, action: str, inputs: dict, outputs: dict)
    
    # Venture Scoping
    @property
    def venture_context(self) -> VentureContext | None
```

### Capability Breakdown

#### Identity

Every module declares its `name`, `category`, and `version`. The registry uses these for discovery, routing, and compatibility checks. Version follows semver — breaking changes require migration logic.

#### Lifecycle

- `initialize(venture_id)` — Called when a module is activated for a venture (or globally). Loads config, establishes connections, subscribes to relevant events.
- `shutdown()` — Graceful teardown. Flushes pending events, closes connections, persists in-flight state.

#### Event Bus

Modules communicate through typed events, never direct imports. This ensures loose coupling and allows the system to scale horizontally.

```python
# Publisher (e.g., Dataset Scout finds a new dataset)
await self.publish("dataset.discovered", {
    "source": "huggingface",
    "name": "financial-qa-v2",
    "relevance_score": 0.87
})

# Subscriber (e.g., Universal Ingestor reacts)
await self.subscribe("dataset.discovered", self.handle_new_dataset)
```

#### Feedback Loop

The core flywheel mechanism. Every module records the outcomes of its actions, enabling:
- Performance tracking over time
- Automated improvement suggestions (via LLM analysis of outcome patterns)
- Reward modeling for reinforcement-style optimization

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
```

#### Experiment Integration

Any module can run experiments on its own behavior. This is the mechanism for continuous improvement — test a hypothesis, measure results, adopt the winner.

```python
result = await self.run_experiment(
    variants=[
        {"prompt_version": "v3", "temperature": 0.7},
        {"prompt_version": "v4", "temperature": 0.5},
    ],
    metric="quality_score"
)
```

#### Cost Tracking

Every LLM call, API request, or compute operation is tracked. This feeds into the Cost Optimizer module for system-wide budget management.

#### Audit

All actions are logged with their inputs and outputs. This provides a complete audit trail for governance, debugging, and replay.

#### Venture Scoping

Modules are aware of their venture context. When operating within a venture, all data is automatically scoped — queries filter by `venture_id`, events are routed within the namespace, and costs are attributed correctly.

---

## Design Philosophy

### Why a Monorepo?

- **Shared types** — Pydantic schemas and SQLAlchemy models are used across modules, API, and tests without version drift
- **Atomic refactoring** — Rename a field and fix all references in one commit
- **Single dependency lockfile** — No diamond dependency conflicts between packages
- **Simplified CI** — One test suite, one Docker build, one deploy artifact

### Why Not Microservices?

At this stage, a monolith deployed as a single service is correct:
- Simpler local development (one `docker-compose up`)
- No network overhead between modules (they're function calls)
- Easier debugging (single process, unified logs)
- The module boundaries are designed for future extraction if needed

### Event Bus as Seam

The event bus is the primary mechanism that would enable future service extraction. If Module X needs to become its own service, it simply subscribes to events over a message broker instead of in-process. No other code changes required.

### JSONB for Flexibility

Configuration, metadata, and variant payloads use JSONB columns. This allows modules to evolve their schemas without database migrations for every field addition. Structured columns are reserved for fields that need indexing, foreign keys, or type enforcement.
