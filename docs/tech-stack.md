# Technology Stack

## Overview

The AI Flywheel platform is built as a **Python backend** with a **Next.js frontend** and **multi-channel interaction** (Slack bot, Web App, CLI). Every technology choice optimizes for three things: rapid iteration speed, AI/ML ecosystem compatibility, and a clear scaling path.

The same backend serves all interaction surfaces — a conversational Slack bot for quick queries, a rich web dashboard for deep analysis, and a developer CLI for automation. This multi-channel architecture ensures the platform meets users where they work.

---

## Core Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Language | Python 3.12+ | AI/ML ecosystem, async, type hints |
| Web Framework | FastAPI | Async, typed, auto-docs, WebSocket |
| Frontend | Next.js + TypeScript | SSR, App Router, API routes, Vercel AI SDK |
| Database | PostgreSQL | Relational, JSONB, proven scale |
| Vector Store | pgvector (+ optional Qdrant) | Co-located with relational data |
| Task Queue | Celery + Redis | Async execution, ML jobs, background tasks |
| Event Bus | Redis Streams (→ Kafka later) | Inter-module communication |
| Cache | Redis | Prompt caching, response dedup, session state |
| Object Storage | MinIO (local) / S3 (prod) | Datasets, artifacts, documents |
| Containerization | Docker + Docker Compose | Dev environment, deployment |
| Slack Integration | Slack Bolt (Python) | Bot framework for Slack channel |

---

## Detailed Rationale

### Python 3.12+

**What it does:** Primary language for all backend logic — agent orchestration, ML pipelines, API services, Slack bot, and CLI tool.

**Why this choice:**
- The AI/ML ecosystem is Python-first. Every major library (PyTorch, transformers, langchain, scikit-learn) is Python-native. Fighting this means fighting the ecosystem.
- Python 3.12+ brings meaningful performance improvements (faster interpreter, better error messages, `type` statement).
- Native `async/await` enables concurrent agent execution without threads.
- Type hints + Pydantic give us runtime validation and IDE support without a separate language.

**Why not alternatives:**
- **TypeScript/Node**: Better for pure web services, but ML ecosystem is immature. Would require Python anyway for ML, leading to two languages.
- **Go/Rust**: Great performance, but ecosystem mismatch. Every LLM API client, every ML library would need wrappers.
- **Java/Kotlin**: Enterprise-grade but heavy. Slower iteration for a startup.

**Scaling path:** Python handles throughput well for our workload (I/O-bound LLM calls, not CPU-bound computation). If specific modules become CPU-bound, we can extract them to Rust/C extensions or separate services.

**Key dependencies:**
- `pydantic` — runtime type validation
- `structlog` — structured logging
- `httpx` — async HTTP client
- `litellm` — unified LLM interface
- `celery` — distributed task execution
- `slack-bolt` — Slack bot framework

---

### FastAPI

**What it does:** HTTP API layer for all external communication — frontend, webhooks, third-party integrations, and WebSocket connections for real-time streaming.

**Why this choice:**
- Built on Starlette/uvicorn for async performance
- Pydantic integration means request/response validation is automatic
- Auto-generated OpenAPI docs for every endpoint
- WebSocket support for real-time agent status and streaming responses
- Dependency injection system is clean and testable

**Why not alternatives:**
- **Django**: Too opinionated, ORM is limiting, async support bolted on
- **Flask**: No async, no built-in validation, no auto-docs
- **Litestar**: Newer, less ecosystem support, smaller community

**Scaling path:** FastAPI on uvicorn already handles high concurrency. For extreme load, add more workers behind a load balancer. The framework itself is never the bottleneck — LLM API calls and database are.

**Key dependencies it enables:**
- `uvicorn` — ASGI server
- `pydantic` — validation layer (shared across entire codebase)
- `python-multipart` — file uploads
- `websockets` — real-time agent communication

---

### Next.js + TypeScript (App Router)

**What it does:** Full-stack frontend with server-side rendering, API routes, and rich client-side interactivity for venture management, agent monitoring, workflow visualization, experiment tracking, and real-time system observation.

**Why this choice:**
- App Router with server components minimizes client-side JavaScript and enables streaming
- Server-side rendering for fast initial loads and SEO when needed
- API routes provide a BFF (Backend-for-Frontend) layer, reducing round trips to the Python API
- Vercel AI SDK for streaming LLM responses directly in the UI with built-in hooks
- Built on React — richest ecosystem for complex UI: node graph editors (react-flow), data visualization (recharts, d3), real-time dashboards
- TypeScript catches bugs at compile time and provides excellent DX
- Component ecosystem (shadcn/ui, radix) accelerates UI development

**Why not alternatives:**
- **Vite + React SPA**: No SSR, no built-in API routes, no server components, more infrastructure to manage
- **Vue/Svelte**: Smaller ecosystems for the specialized components we need (graph editors, complex data tables)
- **HTMX/server-side only**: Not suited for the rich interactivity we need — dragging nodes, real-time updates, complex state
- **No frontend (CLI only)**: Would limit accessibility and make the multi-venture dashboard impractical

**Scaling path:** Next.js deploys naturally to Vercel or self-hosted with Docker. Server components reduce client bundle. If we need mobile, React Native shares mental model.

**Key dependencies:**
- `react-flow` — agent network and workflow visual editor
- `@tanstack/react-query` — server state management with caching and real-time updates
- `recharts` — metrics and experiment visualization
- `zustand` — lightweight client state management
- `tailwindcss` — utility-first styling
- `shadcn/ui` — accessible component primitives
- `ai` (Vercel AI SDK) — streaming LLM responses, useChat/useCompletion hooks

---

### Slack Bolt (Python)

**What it does:** Powers the conversational Slack bot channel — the primary interaction surface for quick queries, notifications, approvals, and lightweight task management without leaving Slack.

**Why this choice:**
- Official Slack framework with first-class Python support
- Handles Socket Mode and HTTP-based events
- Built-in middleware for authentication, message parsing, and event routing
- Supports slash commands, interactive messages, modals, and app home tabs
- Async support aligns with our FastAPI-based backend

**Why not alternatives:**
- **Custom webhook handling**: Reinventing message parsing, auth, rate limiting that Bolt provides for free
- **Node.js Bolt**: Would introduce a second language for one integration
- **Third-party wrappers**: Less maintained, missing features

**Scaling path:** Slack Bolt supports both Socket Mode (simple, no public endpoint needed) and Events API (HTTP webhooks for high-volume). For enterprise deployments with many workspaces, switch to Events API behind a load balancer.

**Key dependencies:**
- `slack-bolt` — core framework
- `slack-sdk` — low-level Slack API client (bundled with bolt)

---

### PostgreSQL

**What it does:** Primary data store for all structured data — venture definitions, agent configurations, workflow state, experiment results, user data, audit logs.

**Why this choice:**
- Battle-tested at any scale (Instagram, Discord, Notion all use it)
- JSONB columns give schema flexibility where needed (agent configs, experiment metadata) without sacrificing relational integrity where it matters
- Excellent indexing: B-tree, GIN (for JSONB), GiST, and via pgvector for embeddings
- ACID transactions for consistency in multi-step operations
- Rich ecosystem: pgvector, pg_cron, pg_stat_statements

**Why not alternatives:**
- **MongoDB**: Flexible but loses relational integrity. Cross-collection queries are painful. Harder to maintain data consistency.
- **MySQL**: Works, but JSONB support is weaker, extension ecosystem is smaller.
- **SQLite**: Great for prototypes, but won't handle concurrent writes from multiple agents.
- **Multiple databases**: Unnecessary complexity at this stage. Postgres handles everything.

**Scaling path:** Vertical scaling handles a lot (modern Postgres easily handles millions of rows and thousands of connections with pgbouncer). When needed: read replicas for dashboards, table partitioning for time-series data, Citus for horizontal sharding.

---

### pgvector (+ optional Qdrant)

**What it does:** Stores and searches vector embeddings — document chunks, agent memories, candidate profiles, semantic search indexes.

**Why this choice:**
- Co-located with relational data (no separate system to manage)
- Supports IVFFlat and HNSW indexes for fast approximate nearest neighbor search
- Can join vector similarity results with relational filters in a single query
- Simpler ops: one database to backup, monitor, and maintain

**Why not alternatives:**
- **Pinecone**: Managed but expensive, vendor lock-in, can't join with relational data
- **Weaviate**: Full-featured but another system to run and maintain
- **Qdrant**: Better pure vector performance — available as optional add-on when pgvector becomes a bottleneck
- **ChromaDB**: Development-only, not production-grade at scale

**Scaling path:** pgvector handles millions of vectors well with HNSW indexes. For billion-scale or very low-latency requirements, add Qdrant as a dedicated vector store. The abstraction layer makes this a configuration change, not a rewrite.

---

### Celery + Redis

**What it does:** Executes background tasks — agent runs, ML training jobs, data ingestion pipelines, scheduled maintenance, bulk operations.

**Why this choice:**
- Mature, well-understood distributed task queue
- Redis as broker is fast and simple
- Supports task priorities, retries, rate limiting, and chains/chords
- Canvas (workflow primitives) enables complex task DAGs
- Worker scaling is horizontal — add more workers for more throughput

**Why not alternatives:**
- **Dramatiq**: Lighter but smaller community, fewer features
- **Temporal**: More powerful workflow engine but heavier operational burden at this stage
- **RQ (Redis Queue)**: Too simple for our needs (no task chaining, limited monitoring)
- **AWS Step Functions**: Cloud-locked, harder to develop locally

**Scaling path:** Celery scales horizontally by adding workers. If we outgrow Celery's coordination model, migrate critical workflows to Temporal while keeping Celery for simple background tasks.

---

### Redis Streams (→ Kafka later)

**What it does:** Inter-module event bus for feedback loops. Modules publish events, other modules subscribe and react.

**Why this choice:**
- Already running Redis for Celery and caching (no new infrastructure)
- Consumer groups provide pub/sub with acknowledgment (events aren't lost)
- Sufficient throughput for our current scale (millions of events/day)
- Simple to reason about and debug
- Supports event replay from any point in the stream

**Why not alternatives:**
- **Kafka**: The right choice at scale, but massive operational overhead for a small team. Topic management, partition rebalancing, ZooKeeper/KRaft — too much for now.
- **RabbitMQ**: Message broker, not event stream. No replay, no consumer groups in the same way.
- **NATS**: Fast but less ecosystem support for Python.

**Scaling path:** When event volume exceeds Redis capacity or we need multi-datacenter replication, migrate to Kafka. The event interface is abstracted — publishers and subscribers don't know the underlying transport.

---

### Redis (Cache)

**What it does:** Multi-purpose caching layer — LLM prompt/response caching, session state, rate limiting counters, real-time metrics aggregation.

**Why this choice:**
- Sub-millisecond reads for hot data
- TTL-based expiration for cache invalidation
- Pub/sub for real-time notifications
- Atomic operations for counters and rate limiting
- Already in the stack (shared with Celery broker and event bus)

**Specific uses:**
- **Prompt cache**: Identical LLM calls return cached responses (huge cost savings)
- **Response dedup**: Prevent duplicate agent executions for the same input
- **Session state**: Track multi-turn conversations across channels (Slack, web, CLI)
- **Rate limiting**: Per-venture, per-model API rate limiting
- **Real-time metrics**: Aggregate counters before flushing to Postgres

**Scaling path:** Redis Cluster for horizontal scaling. For very large caches, add a secondary layer (e.g., DragonflyDB or KeyDB for higher throughput).

---

### MinIO (local) / S3 (prod)

**What it does:** Stores binary objects — datasets (CSV, Parquet), trained model artifacts, uploaded documents, generated reports, backups.

**Why this choice:**
- S3-compatible API is the standard for object storage
- MinIO runs locally in Docker — same API, no cloud dependency for development
- Versioning for model artifacts (track every model version)
- Lifecycle policies for cost management (move old artifacts to cold storage)
- Direct upload/download URLs for frontend file handling

**Why not alternatives:**
- **Local filesystem**: Doesn't work in multi-container or multi-machine setups
- **Database BLOBs**: Wrong tool — databases aren't designed for large binary objects
- **GCS/Azure Blob**: Fine, but S3 API is more universal and portable

**Scaling path:** S3 itself scales infinitely. Cost optimization via intelligent tiering (frequent access → infrequent → glacier).

---

### Docker + Docker Compose

**What it does:** Packages the entire development environment — all services, databases, and dependencies in isolated containers. One command to start everything.

**Why this choice:**
- Reproducible environment across all developers
- `docker compose up` starts Postgres, Redis, MinIO, API, Celery worker, Slack bot, frontend
- Isolation prevents dependency conflicts
- Same container images can deploy to any cloud
- Easy to add new services (just add to compose file)

**Why not alternatives:**
- **Bare metal development**: "Works on my machine" problems, dependency hell
- **Kubernetes (for dev)**: Massive overhead for local development
- **Nix**: Interesting but steep learning curve, less mainstream

**Scaling path:** Docker Compose for dev → Docker Swarm or Kubernetes for production. Container images are the same; only orchestration changes.

---

## Python Libraries

### Core

| Library | Purpose |
|---------|---------|
| `pydantic` | Data validation, settings, API schemas. Used everywhere — the backbone of type safety at runtime. |
| `sqlalchemy` | ORM and database toolkit. Async support via `asyncpg`. Powers all database interactions. |
| `alembic` | Database migrations. Schema changes tracked in version control, applied automatically. |
| `httpx` | Async HTTP client. Used for LLM API calls, web scraping, external integrations. |
| `litellm` | Unified interface to 100+ LLM providers. Powers the LLM Gateway's model abstraction. |
| `structlog` | Structured logging for observability. JSON output, context binding, processor pipeline. |
| `celery` | Distributed task execution for agents and ML jobs. Canvas for complex workflows. |
| `slack-bolt` | Slack bot framework. Handles events, slash commands, interactive components, modals. |

### ML/AI

| Library | Purpose |
|---------|---------|
| `numpy` | Numerical computation foundation. Array operations for embeddings and feature engineering. |
| `pandas` | Data manipulation for datasets, analysis, and reporting. |
| `scikit-learn` | Classical ML models for scoring, classification, clustering. Fast and interpretable. |
| `sentence-transformers` | Generate embeddings for semantic search, similarity, and RAG. |
| `transformers` | Hugging Face models for fine-tuning and inference of open models. |

### Infrastructure

| Library | Purpose |
|---------|---------|
| `redis-py` | Redis client for cache, pub/sub, and streams. |
| `boto3` / `minio` | S3-compatible object storage client. |
| `tenacity` | Retry logic for flaky external API calls (LLM providers, ad platforms). |

### External Service SDKs

| Library | Purpose |
|---------|---------|
| `google-ads` | Google Ads API client. Campaign management, performance data, bid optimization. |
| `linkedin-api` | LinkedIn Marketing API. Ad management, audience targeting, analytics. |
| `stripe` | Payment processing. Subscription billing, usage metering, invoicing. |
| `resend` | Transactional email. Notifications, reports, alerts, onboarding sequences. |

These SDKs are managed through Tool Forge, which provides a unified interface for agents to interact with external platforms. Tool Forge handles authentication rotation, rate limiting, error retries, and schema normalization across all integrations.

---

## Frontend Libraries (npm)

| Library | Purpose |
|---------|---------|
| `react-flow` | Visual node graph editor for agent networks and workflows. |
| `@tanstack/react-query` | Server state management with caching, optimistic updates, and real-time sync. |
| `recharts` | Charts and graphs for metrics dashboards and experiment results. |
| `zustand` | Lightweight client state management. One store per domain. |
| `tailwindcss` | Utility-first CSS framework. Rapid UI development without context switching. |
| `shadcn/ui` | Pre-built accessible component library built on Radix primitives. |
| `ai` (Vercel AI SDK) | Streaming LLM responses in UI. `useChat`, `useCompletion`, `useAssistant` hooks. |

---

## Development Tools

| Tool | Purpose |
|------|---------|
| `pytest` | Testing framework. Fixtures for database, Redis, and agent mocks. Async test support. |
| `ruff` | Linting and formatting (replaces flake8, black, isort). Extremely fast (Rust-based). |
| `mypy` | Static type checking. Catches type errors before runtime. Strict mode on new code. |
| `pre-commit` | Git hooks that run ruff, mypy, and tests before allowing commits. Prevents broken code in main. |

### Development Workflow

```bash
# Start all services
docker compose up -d

# Run tests
pytest tests/ -v

# Type check
mypy src/

# Lint and format
ruff check src/ --fix
ruff format src/

# Database migration
alembic revision --autogenerate -m "add agent_runs table"
alembic upgrade head
```

---

## Multi-Channel Architecture

The platform serves three interaction surfaces from a single backend, connected through a **Conversation Router** that maintains context across channels.

```
┌─────────────────────────────────────────────────────────────┐
│                     Conversation Router                       │
│            (Intent detection, context management)             │
└──────────┬────────────────────┬────────────────────┬────────┘
           │                    │                    │
    ┌──────▼──────┐     ┌──────▼──────┐     ┌──────▼──────┐
    │  Slack Bot   │     │   Web App    │     │     CLI      │
    │  (Bolt)      │     │  (Next.js)   │     │   (Click)    │
    └─────────────┘     └─────────────┘     └─────────────┘
```

### Slack Bot (Primary conversational interface)
- Quick queries: "What's the conversion rate for Venture X?"
- Approvals: Human-in-the-loop review via interactive messages
- Notifications: Experiment completions, anomalies, budget alerts
- Slash commands: `/flywheel status`, `/flywheel deploy`

### Web App (Rich visual interface)
- Node graph editors for agent workflows
- Real-time dashboards with streaming metrics
- Experiment configuration and monitoring
- Dataset browsing and model management

### CLI (Developer automation)
- Scripting and CI/CD integration
- Bulk operations and data import
- Local development and testing
- Piped output for Unix toolchain integration

All three channels share:
- Session state (via Redis)
- User identity and permissions
- Conversation history and context
- The same agent execution engine

---

## Why Monorepo

The platform is structured as a **single Python package with modules** plus a **co-located Next.js frontend**, not as microservices. This is a deliberate choice for the current stage.

### Arguments For Monorepo

1. **Shared types and validation**: Pydantic models are shared across modules. No API contract drift.
2. **Atomic refactoring**: Rename a function, and every caller updates in the same commit.
3. **Single test suite**: Integration tests run across module boundaries easily.
4. **Simpler deployment**: One Docker image for backend, one for frontend. One deployment pipeline.
5. **Reduced overhead**: No service discovery, no API versioning between services, no distributed tracing complexity.
6. **Faster iteration**: Change any module and see the effect immediately. No deploy-and-wait.
7. **Multi-channel consistency**: All interaction surfaces (Slack, web, CLI) import from the same codebase — behavior is guaranteed consistent.

### Structure

```
ai_flywheel/
├── core/              # System 1: Core Kernel
├── modules/           # Systems 2-8: Business logic
├── ventures/          # Venture layer
├── channels/          # Multi-channel interaction (Slack, CLI, WebSocket)
├── api/               # FastAPI routes and middleware
├── web/               # Next.js frontend
└── tests/             # Comprehensive test suite
```

### When to Split

We'd extract a module into a separate service when:
- It needs to scale independently (e.g., agent execution workers)
- It has fundamentally different resource requirements (GPU for training)
- Team boundaries form around it (separate team owns it)
- Deployment cadence diverges (one module deploys hourly, others weekly)

Until then, the coordination cost of microservices outweighs their benefits for a small team moving fast.

### The Middle Path

Even within the monorepo, modules communicate through **well-defined interfaces**:
- Each module exposes a public API (Python functions/classes)
- Modules communicate asynchronously via the event bus
- No module directly imports another module's internal implementation
- Database tables are owned by one module (others go through the API)
- The Conversation Router abstracts channel-specific details from business logic

This gives us the **organizational benefits** of service boundaries without the **operational overhead** of actual network calls between services.
