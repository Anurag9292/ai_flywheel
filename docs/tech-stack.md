# Technology Stack

## Overview

The AI Flywheel platform is built as a **Python backend** with a **Next.js frontend**. Every technology choice optimizes for three things: rapid iteration speed, AI/ML ecosystem compatibility, and a clear scaling path.

---

## Core Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Language | Python 3.12+ | AI/ML ecosystem, async, type hints |
| Web Framework | FastAPI | Async, typed, auto-docs, WebSocket support |
| Frontend | Next.js + TypeScript | SSR, API routes, node graph editors, dashboards, real-time |
| Database | PostgreSQL | Relational, JSONB for flexibility, proven at scale |
| Vector Store | pgvector (+ optional Qdrant) | Embeddings, similarity search, co-located |
| Task Queue | Celery + Redis | Async agent execution, ML jobs, background tasks |
| Event Bus | Redis Streams (→ Kafka later) | Inter-module communication, event sourcing |
| Cache | Redis | Prompt caching, LLM response dedup, session state |
| Object Storage | MinIO (local) / S3 (prod) | Datasets, model artifacts, documents |
| ML Tracking | Custom (on Postgres) | Integrated with experiment system |
| Containerization | Docker + Docker Compose | Dev environment, isolation, deployment |

---

## Detailed Rationale

### Python 3.12+

**What it does:** Primary language for all backend logic, agent orchestration, ML pipelines, and API services.

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

---

### FastAPI

**What it does:** HTTP API layer for all external communication — frontend, webhooks, third-party integrations, and inter-module REST calls.

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

### Next.js + TypeScript

**What it does:** Full-stack frontend with server-side rendering, API routes, and rich client-side interactivity for venture management, agent monitoring, workflow visualization, experiment tracking, and real-time system observation.

**Why this choice:**
- Built on React — richest ecosystem for complex UI: node graph editors (react-flow), data visualization (recharts, d3), real-time dashboards
- Server-side rendering for fast initial loads and SEO when needed
- API routes provide a BFF (Backend-for-Frontend) layer, reducing round trips to the Python API
- App Router with server components minimizes client-side JavaScript
- TypeScript catches bugs at compile time and provides excellent DX
- Component ecosystem (shadcn/ui, radix) accelerates UI development
- Vercel AI SDK for streaming LLM responses directly in the UI

**Why not alternatives:**
- **Vite + React SPA**: No SSR, no built-in API routes, more infrastructure to manage
- **Vue/Svelte**: Smaller ecosystems for the specialized components we need (graph editors, complex data tables)
- **HTMX/server-side only**: Not suited for the rich interactivity we need — dragging nodes, real-time updates, complex state
- **No frontend (CLI only)**: Would limit accessibility and make the multi-venture dashboard impractical

**Scaling path:** Next.js deploys naturally to Vercel or self-hosted with Docker. Server components reduce client bundle. If we need mobile, React Native shares mental model.

**Key dependencies:**
- `react-flow` — agent network and workflow visual editor
- `@tanstack/react-query` — server state management
- `recharts` — metrics and experiment visualization
- `zustand` — client state management
- `tailwindcss` — utility-first styling
- `ai` (Vercel AI SDK) — streaming LLM responses in UI
- `shadcn/ui` — accessible component primitives

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
- **Session state**: Track multi-turn agent conversations
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

### Custom ML Tracking (on Postgres)

**What it does:** Records experiments, model versions, metrics, hyperparameters, and lineage — all integrated directly with the platform's experiment and evaluation systems.

**Why this choice:**
- Tight integration with our Experiment Tracker and Evaluation Framework
- No separate system to maintain or sync data between
- Query experiment results alongside venture data, agent performance, and cost metrics
- Custom schema designed for our specific workflow (not a generic tool)

**Why not alternatives:**
- **MLflow**: Full-featured but a separate service to run. Its data model doesn't match our venture/agent structure.
- **Weights & Biases**: Great UI but SaaS cost scales with usage, data leaves your system, and integration is one-way.
- **Neptune/Comet**: Same SaaS concerns as W&B.

**Scaling path:** If we need richer experiment visualization, add a lightweight UI layer. The data stays in Postgres regardless.

---

### Docker + Docker Compose

**What it does:** Packages the entire development environment — all services, databases, and dependencies in isolated containers. One command to start everything.

**Why this choice:**
- Reproducible environment across all developers
- `docker compose up` starts Postgres, Redis, MinIO, API, worker, frontend
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
| `celery` | Distributed task execution for agents and ML jobs. |
| `redis-py` | Redis client for cache, pub/sub, and streams. |
| `boto3` / `minio` | S3-compatible object storage client. |
| `tenacity` | Retry logic for flaky external API calls (LLM providers). |
| `structlog` | Structured logging for observability and debugging. |

### Frontend (npm)

| Library | Purpose |
|---------|---------|
| `react-flow` | Visual node graph editor for agent networks and workflows. |
| `@tanstack/react-query` | Server state management with caching and real-time updates. |
| `recharts` | Charts and graphs for metrics dashboards. |
| `zustand` | Lightweight client state management. |
| `tailwindcss` | Utility-first CSS framework. |
| `shadcn/ui` | Pre-built accessible component library. |

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

## Why Monorepo

The platform is structured as a **single Python package with modules**, not as microservices. This is a deliberate choice for the current stage.

### Arguments For Monorepo

1. **Shared types and validation**: Pydantic models are shared across modules. No API contract drift.
2. **Atomic refactoring**: Rename a function, and every caller updates in the same commit.
3. **Single test suite**: Integration tests run across module boundaries easily.
4. **Simpler deployment**: One Docker image, one deployment pipeline, one version number.
5. **Reduced overhead**: No service discovery, no API versioning between services, no distributed tracing complexity.
6. **Faster iteration**: Change any module and see the effect immediately. No deploy-and-wait.

### Structure

```
src/flywheel/
├── __init__.py
├── core/              # Shared utilities, base classes, config
├── gateway/           # LLM Gateway module
├── agents/            # Agent Factory + execution
├── data/              # Dataset Scout, ingestion, quality
├── experiments/       # Experiment Tracker, Model Forge
├── evaluation/        # Evaluation Framework, benchmarks
├── optimization/      # Bandit Optimizer, Cost Optimizer
├── workflows/         # Workflow Engine
├── ventures/          # Venture management, templates
├── events/            # Event bus, pub/sub infrastructure
├── api/               # FastAPI routes and WebSocket handlers
└── models/            # SQLAlchemy models, Alembic migrations
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

This gives us the **organizational benefits** of service boundaries without the **operational overhead** of actual network calls between services.
