# Database Schema

## Overview

AI Flywheel uses PostgreSQL with the pgvector extension. The schema is designed around four principles:

1. **Venture-scoped isolation** — Almost every table has a `venture_id` foreign key, enabling multi-tenant data separation
2. **Universal observability** — Tracing, task tracking, and event logging are first-class schema citizens
3. **Feedback loops baked in** — Outcome recording and experiment measurement are structural, not bolted on
4. **JSONB for evolution** — Configuration and metadata use JSONB to allow modules to evolve without migrations

The schema mirrors the 8-system architecture, with tables grouped by the system that owns them.

---

## Row-Level Security (Multi-Tenancy Enforcement)

Every table with a `venture_id` column has Row-Level Security enabled. This enforces data isolation at the database layer — not just application code.

### Why RLS?

In a system where LLM-generated queries and dynamic RAG retrieval access the database, application-level filtering (`WHERE venture_id = ?`) is insufficient. One missed filter = cross-venture data leakage. RLS makes this impossible:

```sql
-- Enable RLS on every venture-scoped table
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE experiments ENABLE ROW LEVEL SECURITY;
ALTER TABLE traces ENABLE ROW LEVEL SECURITY;
-- ... (all tables with venture_id)

-- Policy: rows only visible if venture_id matches session context
CREATE POLICY venture_isolation ON agents
  USING (venture_id = current_setting('app.current_venture_id')::text);

-- At connection time (set by application):
SET app.current_venture_id = 'venture_abc123';
```

### How it works in practice:
- When a database session is created, the application sets `app.current_venture_id`
- ALL queries on RLS-enabled tables are automatically filtered — even if the query omits a WHERE clause
- LLM-generated SQL, dynamic queries, and RAG retrieval are all isolated
- Global data (shared patterns, platform-level configs) lives in tables WITHOUT RLS

### Tables WITH RLS (venture-scoped):
All tables that contain venture-specific data: agents, prompts, experiments, traces, tasks, feedback, costs, models, datasets, knowledge_edges, etc.

### Tables WITHOUT RLS (global):
Platform-level tables: users, patterns (shared across ventures), metrics_definitions (global templates), tool definitions (shared integrations).

---

## System 1: Core Kernel

### `ventures`

```sql
ventures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    domain TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',  -- active, paused, archived
    config JSONB NOT NULL DEFAULT '{}',
    metrics_summary JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
)
```

**Purpose:** Top-level namespace for all AI ventures. Every other entity is scoped to a venture (or is global). The venture is the organizational boundary — all data, agents, experiments, and costs are attributed here.

**Key Relationships:**
- Parent of almost every other table via `venture_id` FK
- Referenced by tasks, events, traces, artifacts, agents, experiments, costs, deployments, patterns

**Indexing Strategy:**
- Primary key on `id`
- Unique index on `name`
- Index on `status` for filtering active ventures
- GIN index on `config` for JSONB queries

**Feedback Loop Role:** The `metrics_summary` JSONB is a denormalized rollup of key metrics across all systems — updated periodically by a background task. Enables fast dashboard rendering without joining across all tables.

**Growth:** Low volume — tens to hundreds of ventures. This table stays small.

---

### `tasks`

```sql
tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    module_name TEXT NOT NULL,
    type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, running, completed, failed, cancelled
    input JSONB NOT NULL DEFAULT '{}',
    output JSONB,
    parent_task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    retries INT NOT NULL DEFAULT 0,
    priority INT NOT NULL DEFAULT 5,  -- 1=highest, 10=lowest
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
)
```

**Purpose:** Queryable index/cache of workflow state managed by Temporal.io. Every background operation — agent execution, model training, data ingestion, report generation — creates a task record here. Supports parent-child relationships for complex task DAGs.

**Relationship to Temporal.io:** The source of truth for workflow execution state (step progress, retry history, current activity) is Temporal's event history, not this table. The `tasks` table exists for dashboards, history queries, and cross-referencing with other tables (traces, costs, feedback). Task status is synced from Temporal via event listeners — if Temporal says a workflow is running, this table reflects that.

**Key Relationships:**
- FK to `ventures(id)` — scoped to a venture
- Self-referential FK `parent_task_id` for task trees
- `module_name` identifies the owning system/module
- Correlated with `traces` via shared `venture_id` + timestamps

**Indexing Strategy:**
- Composite index on `(venture_id, status)` for active task queries
- Composite index on `(module_name, status)` for per-module task monitoring
- Index on `parent_task_id` for tree traversal
- Index on `priority` for queue ordering
- Composite index on `(status, priority, created_at)` for worker task selection

**Feedback Loop Role:** Task completion times and retry counts feed into reliability metrics. Patterns in task failures trigger automated investigation. The Cost Optimizer uses task duration to estimate compute costs.

**Growth:** **HIGH VOLUME** — Every async operation creates a row. Thousands per day for active ventures. Partitioning by month recommended.

---

### `events`

```sql
events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL,
    source_module TEXT NOT NULL,
    venture_id UUID REFERENCES ventures(id) ON DELETE SET NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    correlation_id UUID,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
)
```

**Purpose:** Persistent event log. Every event published on the event bus is written here for audit, replay, and analytics. This is the system's memory of what happened and enables debugging cross-module interactions.

**Key Relationships:**
- FK to `ventures(id)` — nullable for global events
- `correlation_id` links related events across modules (e.g., all events from a single user request)
- No FK to modules (uses `source_module` text for flexibility)

**Indexing Strategy:**
- Index on `event_type` for subscription replay
- Composite index on `(venture_id, timestamp)` for venture-scoped time queries
- Composite index on `(source_module, timestamp)` for per-module auditing
- Index on `correlation_id` for tracing event chains
- Partial index on recent events (last 7 days) for hot queries

**Feedback Loop Role:** The event log enables:
- Replaying sequences to debug issues
- Pattern detection (which event sequences correlate with good outcomes?)
- Cross-module analytics (how do upstream events affect downstream performance?)
- Audit trail for compliance

**Growth:** **HIGH VOLUME** — Potentially thousands of events per hour per venture. This is the highest-growth table. Partitioning required.

---

### `traces`

```sql
traces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    trace_id UUID NOT NULL,
    span_id UUID NOT NULL UNIQUE,
    parent_span_id UUID,
    module_name TEXT NOT NULL,
    operation TEXT NOT NULL,
    input JSONB,
    output JSONB,
    duration_ms INT,
    cost FLOAT,
    tokens INT,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
)
```

**Purpose:** Distributed tracing storage. Every module operation creates a span with its input, output, timing, cost, and token usage. Spans form trees via `parent_span_id`, enabling drill-down from high-level operations to atomic LLM calls.

**Key Relationships:**
- FK to `ventures(id)` — scoped to a venture
- `trace_id` groups all spans from a single top-level operation
- `parent_span_id` references another span's `span_id` for tree structure
- `module_name` + `operation` identify what was executed

**Indexing Strategy:**
- Index on `trace_id` for retrieving complete traces
- Composite index on `(venture_id, module_name, timestamp)` for per-module performance analysis
- Index on `parent_span_id` for tree traversal
- Composite index on `(module_name, operation, timestamp)` for operation-specific analytics
- Index on `cost` for identifying expensive operations

**Feedback Loop Role:** Traces are the primary source for:
- Performance regression detection (duration_ms trending up)
- Cost anomaly detection (unexpected cost spikes)
- Token usage optimization (identifying verbose prompts)
- Bottleneck identification (which spans dominate total duration?)

**Growth:** **HIGH VOLUME** — Multiple spans per user action. Comparable to events table. Partitioning by month required.

---

### `artifacts`

```sql
artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    module_name TEXT NOT NULL,
    type TEXT NOT NULL,  -- model, dataset, report, export, checkpoint
    name TEXT NOT NULL,
    version INT NOT NULL DEFAULT 1,
    storage_path TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
)
```

**Purpose:** Registry of versioned binary artifacts stored in object storage (S3/MinIO). Tracks what was produced, by which module, with what metadata — without storing the actual bytes in the database.

**Key Relationships:**
- FK to `ventures(id)` — scoped to a venture
- Referenced by `models(artifact_id)` for model binaries
- `storage_path` points to S3/MinIO location

**Indexing Strategy:**
- Composite index on `(venture_id, module_name, name)` for artifact lookup
- Composite index on `(venture_id, type)` for type-filtered queries
- Unique constraint on `(venture_id, module_name, name, version)` for version integrity

**Feedback Loop Role:** Artifact versioning enables rollback when new versions underperform. Version-over-version comparison drives improvement measurement.

**Growth:** Moderate — tens to hundreds per venture. The artifacts themselves grow (stored in S3), but the registry stays manageable.

---

### `users`

```sql
users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'developer',  -- admin, developer, viewer
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
)
```

**Purpose:** User identity for authentication and authorization. Kept minimal — the platform doesn't need extensive user profiles at this stage.

**Key Relationships:**
- Referenced by `api_keys(user_id)` for API access
- Referenced by `review_queue(reviewer_id)` for human-in-the-loop attribution

**Indexing Strategy:**
- Unique index on `email`
- Index on `role` for permission queries

**Growth:** Low — tens to hundreds of users.

---

### `api_keys`

```sql
api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    key_hash TEXT NOT NULL,
    permissions JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    expires_at TIMESTAMP WITH TIME ZONE
)
```

**Purpose:** API key management for programmatic access. Keys are scoped to a specific venture with explicit permissions. Only the hash is stored — the key itself is shown once at creation.

**Key Relationships:**
- FK to `users(id)` — who owns this key
- FK to `ventures(id)` — which venture it accesses
- `permissions` JSONB lists allowed operations

**Indexing Strategy:**
- Index on `key_hash` for authentication lookup (must be fast)
- Composite index on `(user_id, venture_id)` for user key management
- Index on `expires_at` for cleanup of expired keys

**Growth:** Low — a few keys per user per venture.

---

## System 2: Agent Runtime

### `prompts`

```sql
prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    version INT NOT NULL DEFAULT 1,
    system_template TEXT NOT NULL,
    user_template TEXT,
    variables JSONB DEFAULT '[]',
    performance_score FLOAT,
    usage_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    UNIQUE (venture_id, name, version)
)
```

**Purpose:** Versioned prompt templates with separate system and user components. Every prompt change creates a new version, enabling rollback, A/B testing between versions, and performance tracking over time.

**Key Relationships:**
- FK to `ventures(id)`
- Referenced by `agents(prompt_id)` — agents use specific prompt versions
- Performance score derived from `agent_executions` quality scores

**Indexing Strategy:**
- Unique composite index on `(venture_id, name, version)`
- Index on `performance_score` for finding best-performing prompts
- Composite index on `(venture_id, name)` with `ORDER BY version DESC` for latest version lookup

**Feedback Loop Role:** Prompt performance scores are computed from agent execution outcomes. Low-performing prompts trigger improvement suggestions. The Prompt Studio surfaces this data and `usage_count` for human-in-the-loop refinement.

**Growth:** Moderate — hundreds of prompts with tens of versions each.

---

### `agents`

```sql
agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    archetype TEXT NOT NULL,  -- researcher, analyst, writer, coder, coordinator
    prompt_id UUID REFERENCES prompts(id),
    tools JSONB DEFAULT '[]',
    constraints JSONB DEFAULT '{}',
    config JSONB DEFAULT '{}',
    version INT NOT NULL DEFAULT 1,
    performance_score FLOAT,
    execution_count INT NOT NULL DEFAULT 0,
    UNIQUE (venture_id, name, version)
)
```

**Purpose:** Agent definitions — the blueprint for an AI agent including its personality (prompt), capabilities (tools), guardrails (constraints), and performance tracking.

**Key Relationships:**
- FK to `ventures(id)`
- FK to `prompts(id)` — which prompt template drives this agent
- Parent of `agent_executions`
- `tools` JSONB array references `tools(id)` by name
- `constraints` references policies from `policies` table

**Indexing Strategy:**
- Composite index on `(venture_id, name)`
- Index on `archetype` for filtering by agent type
- Index on `performance_score` for ranking

**Feedback Loop Role:** Agent performance scores are rolling averages from execution outcomes. `execution_count` tracks usage. Underperforming agents trigger the improvement cycle: analyze errors → suggest prompt/tool changes → experiment → adopt winner.

**Growth:** Low-moderate — tens of agents per venture.

---

### `agent_executions`

```sql
agent_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    trace_id UUID,
    input JSONB NOT NULL,
    output JSONB,
    tokens_used INT,
    cost FLOAT,
    duration_ms INT,
    quality_score FLOAT,
    status TEXT NOT NULL DEFAULT 'running',  -- running, completed, failed
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
)
```

**Purpose:** Complete audit trail of every agent execution. Records what went in, what came out, how much it cost, how long it took, and how good it was. Links to task and trace for full observability.

**Key Relationships:**
- FK to `agents(id)` and `ventures(id)`
- FK to `tasks(id)` — the task that triggered this execution
- `trace_id` correlates to the `traces` table for detailed span breakdown
- Quality score feeds back into `agents.performance_score`

**Indexing Strategy:**
- Composite index on `(agent_id, timestamp)` for per-agent history
- Composite index on `(venture_id, timestamp)` for venture-wide activity
- Index on `trace_id` for joining with trace data
- Index on `quality_score` for finding outliers
- Index on `status` for monitoring active executions

**Feedback Loop Role:** Each execution produces a quality score (from user feedback, automated evaluation, or downstream success signals). This data trains the system to understand what makes a good execution and how to improve.

**Growth:** **HIGH VOLUME** — Every agent interaction creates a row. Thousands per day for active ventures. Partitioning required.

---

### `tools`

```sql
tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    schema JSONB NOT NULL,  -- JSON Schema for input/output
    implementation_type TEXT NOT NULL,  -- api, function, workflow
    config JSONB DEFAULT '{}',
    usage_count INT NOT NULL DEFAULT 0,
    success_rate FLOAT,
    avg_latency_ms FLOAT
)
```

**Purpose:** Registry of tools available to agents via Tool Forge. Each tool has a schema (for LLM function calling), implementation type, and usage statistics. Covers internal utilities and external integrations (Google Ads, LinkedIn, Stripe, etc.).

**Key Relationships:**
- Referenced by `agents.tools` JSONB array (by name)
- Referenced by `tool_credentials` for auth management
- Usage stats updated from `agent_executions`

**Indexing Strategy:**
- Unique index on `name`
- Index on `success_rate` for reliability ranking
- Index on `implementation_type` for type-filtered queries

**Feedback Loop Role:** Tool success rates and latencies are tracked automatically. Low-reliability tools are flagged for repair or replacement. The Tool Forge can generate new tools based on patterns in failed tool calls.

**Growth:** Low — tens to hundreds of tools total (shared across ventures).

---

### `tool_credentials`

```sql
tool_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id UUID REFERENCES tools(id) ON DELETE CASCADE,
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,  -- google_ads, linkedin, stripe, etc.
    credentials_encrypted TEXT NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE
)
```

**Purpose:** Encrypted credential storage for external tool integrations. Scoped per-venture so each venture can have its own API keys for ad platforms, payment providers, etc.

**Key Relationships:**
- FK to `tools(id)` — which tool these credentials are for
- FK to `ventures(id)` — which venture owns them

**Indexing Strategy:**
- Composite index on `(tool_id, venture_id)` for credential lookup
- Index on `expires_at` for rotation reminders

**Feedback Loop Role:** Credential expiration tracking prevents silent failures. Usage patterns inform which integrations are most valuable per venture.

**Growth:** Low — one credential set per tool per venture.

---

### `review_queue`

```sql
review_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    module_name TEXT NOT NULL,
    item_type TEXT NOT NULL,  -- agent_decision, content, deployment, policy_violation
    item_id UUID NOT NULL,
    ai_decision JSONB NOT NULL,
    ai_confidence FLOAT NOT NULL,
    ai_reasoning TEXT,
    human_decision JSONB,
    reviewer_id UUID REFERENCES users(id),
    feedback TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    reviewed_at TIMESTAMP WITH TIME ZONE
)
```

**Purpose:** Human-in-the-loop review queue. When AI confidence is below threshold or policies require human approval, items are queued here. Captures both AI reasoning and human decisions for training.

**Key Relationships:**
- FK to `ventures(id)` — scoped to venture
- FK to `users(id)` via `reviewer_id` — who reviewed it
- `item_id` references the entity being reviewed (polymorphic)

**Indexing Strategy:**
- Composite index on `(venture_id, reviewed_at IS NULL)` for pending items
- Index on `module_name` for per-module review queues
- Index on `ai_confidence` for prioritizing low-confidence items
- Index on `reviewer_id` for reviewer workload tracking

**Feedback Loop Role:** The gap between AI decisions and human decisions is the primary signal for improvement. When humans consistently override AI, it indicates the model/prompt needs updating. Agreement rates track calibration over time.

**Growth:** Moderate — depends on confidence thresholds. Decreases over time as AI improves.

---

### `policies`

```sql
policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    scope TEXT NOT NULL,  -- global, module, agent, tool
    rules JSONB NOT NULL,
    enforcement_mode TEXT NOT NULL DEFAULT 'enforce',  -- enforce, warn, log
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
)
```

**Purpose:** Safety and governance policies. Defines rules that constrain agent behavior — content filters, budget limits, action restrictions, and compliance requirements.

**Key Relationships:**
- FK to `ventures(id)` — scoped to venture (or global if `venture_id` is NULL)
- Referenced by Policy Engine during agent execution
- Violations trigger `review_queue` entries

**Indexing Strategy:**
- Composite index on `(venture_id, scope)` for policy lookup
- Index on `enforcement_mode` for active enforcement queries

**Feedback Loop Role:** Policy violations are tracked. Policies that are rarely triggered may be too permissive; those triggered constantly may be too restrictive. Both patterns inform policy tuning.

**Growth:** Low — tens of policies per venture.

---

## Systems 3-4: Data & Knowledge, ML & Evaluation

### `datasets`

```sql
datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    source TEXT NOT NULL,  -- huggingface, kaggle, web_scrape, upload, synthetic, api
    name TEXT NOT NULL,
    schema JSONB DEFAULT '{}',
    quality_score FLOAT,
    size BIGINT,  -- bytes
    license TEXT,
    metadata JSONB DEFAULT '{}',
    discovered_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
)
```

**Purpose:** Registry of all datasets — discovered externally, uploaded, or synthetically generated. Metadata-only (actual data stored in object storage or referenced by URL).

**Key Relationships:**
- FK to `ventures(id)`
- Referenced by `labels(dataset_id)` for annotation tracking
- Referenced by model training runs (via `models.config`)
- Quality score from Data Quality assessments

**Indexing Strategy:**
- Composite index on `(venture_id, source)`
- Index on `quality_score` for filtering high-quality datasets
- Full-text index on `name` for search
- GIN index on `metadata` for JSONB queries

**Feedback Loop Role:** Dataset quality scores improve over time as Data Quality learns what constitutes "good data" for each venture's domain. Discovery relevance improves as the system learns which discovered datasets actually get used.

**Growth:** Moderate — hundreds to low thousands per venture.

---

### `models`

```sql
models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    type TEXT NOT NULL,  -- classifier, regressor, embedding, generation, rl, scoring
    config JSONB NOT NULL DEFAULT '{}',
    metrics JSONB DEFAULT '{}',
    artifact_id UUID REFERENCES artifacts(id),
    status TEXT NOT NULL DEFAULT 'training',  -- training, evaluating, deployed, archived
    version INT NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
)
```

**Purpose:** Registry of trained ML models with their configuration, evaluation metrics, deployment status, and link to stored model artifacts.

**Key Relationships:**
- FK to `ventures(id)`
- FK to `artifacts(id)` — link to stored model binary
- `config` references `datasets(id)` used for training
- `metrics` stores evaluation results (accuracy, F1, etc.)

**Indexing Strategy:**
- Composite index on `(venture_id, name, version)`
- Index on `status` for finding deployed models
- Index on `type` for filtering

**Feedback Loop Role:** Model metrics are tracked per version. The Evaluation module continuously compares deployed models against holdout data and new models, triggering retraining when performance degrades.

**Growth:** Low-moderate — tens of models per venture with multiple versions.

---

### `labels`

```sql
labels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    dataset_id UUID REFERENCES datasets(id) ON DELETE CASCADE,
    item_id TEXT NOT NULL,
    label JSONB NOT NULL,
    annotator_id UUID,  -- user or "llm:gpt-4"
    confidence FLOAT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
)
```

**Purpose:** Data annotation storage. Supports human labels, LLM-assisted labels, and active learning selection. Tracks who labeled what and with what confidence.

**Key Relationships:**
- FK to `ventures(id)` and `datasets(id)`
- `annotator_id` references `users(id)` for human annotators or stores LLM identifier as text
- `item_id` identifies the specific data point within the dataset

**Indexing Strategy:**
- Composite index on `(dataset_id, item_id)` for per-item label lookup
- Index on `annotator_id` for annotator-specific queries
- Index on `confidence` for active learning (query low-confidence items)

**Feedback Loop Role:** Inter-annotator agreement (human vs. LLM) measures labeling quality. Items where labels disagree are candidates for re-labeling or expert review.

**Growth:** Moderate to high — scales with dataset size and labeling effort.

---

### `embedding_collections`

```sql
-- Embedding collections (versioned, namespaced)
embedding_collections (
    id TEXT PRIMARY KEY,
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    name TEXT NOT NULL,              -- e.g., "resume_embeddings"
    model_name TEXT NOT NULL,        -- e.g., "text-embedding-3-small"
    model_version TEXT NOT NULL,     -- e.g., "v2"
    dimensions INT NOT NULL,         -- e.g., 1536
    status TEXT DEFAULT 'active',    -- "active" | "migrating" | "deprecated"
    document_count BIGINT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
)
```

**Purpose:** Versioned, namespaced embedding collections. Each collection is tied to a specific model + dimension. When upgrading embedding models, a new collection is created and a background Temporal workflow migrates data. Queries route to the active collection. This prevents the silent failure of comparing vectors of different dimensions.

**Key Relationships:**
- FK to `ventures(id)` — scoped to a venture
- Parent of `embeddings` via `collection_id`
- `status` controls query routing: only `active` collections receive queries

**Indexing Strategy:**
- Composite index on `(venture_id, name, status)` for active collection lookup
- Index on `status` for migration management

**Design Decisions:**
- Embeddings are NEVER stored in a global flat table. Each collection is tied to a specific model + dimension.
- When upgrading embedding models, a new collection is created and a background Temporal workflow migrates data.
- Queries route to the active collection. This prevents the silent failure of comparing vectors of different dimensions.

**Growth:** Low — a handful of collections per venture (one per embedding use case × model version).

---

### `embeddings`

```sql
-- Embeddings belong to a specific collection (never global)
embeddings (
    id TEXT PRIMARY KEY,
    collection_id TEXT REFERENCES embedding_collections(id),
    source_type TEXT NOT NULL,       -- document, chunk, entity, query, memory
    source_id TEXT NOT NULL,
    vector VECTOR,                   -- dimension matches collection's dimensions
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
)
```

**Purpose:** Vector embedding storage for semantic search, RAG, similarity matching, and agent memory retrieval. Uses pgvector for co-located vector operations with relational data. Every embedding belongs to a specific collection — never stored globally.

**Key Relationships:**
- FK to `embedding_collections(id)` — scoped to a versioned collection
- `source_type` + `source_id` provide polymorphic reference to original content
- Queried by Memory Engine and Knowledge Graph for retrieval

**Indexing Strategy:**
- HNSW index on `vector` with `vector_cosine_ops` for fast similarity search
- Composite index on `(collection_id, source_type)` for scoped retrieval
- Index on `source_id` for lookups by source

**Design Decisions:**
- Separate table (not alongside source data) keeps source tables lean
- Collection-scoped architecture ensures vectors from different models are never mixed in similarity search
- HNSW chosen over IVFFlat for better recall with acceptable insert performance
- Dimension is not fixed in schema — it matches the parent collection's `dimensions` field

> **Important:** Embeddings are NEVER stored in a global flat table. Each collection is tied to a specific model + dimension. When upgrading embedding models, a new collection is created and a background Temporal workflow migrates data. Queries route to the active collection. This prevents the silent failure of comparing vectors of different dimensions.

**Growth:** **HIGH VOLUME** — scales with ingested content. Millions of vectors for active ventures.

---

## System 5: Product & Market Intelligence

### `hypotheses`

```sql
hypotheses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    type TEXT NOT NULL,  -- market, product, pricing, channel, technical
    statement TEXT NOT NULL,
    validation_method TEXT NOT NULL,
    success_threshold FLOAT NOT NULL,
    status TEXT NOT NULL DEFAULT 'proposed',  -- proposed, testing, validated, invalidated
    confidence FLOAT,
    evidence JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    validated_at TIMESTAMP WITH TIME ZONE
)
```

**Purpose:** Tracks business hypotheses through their lifecycle — from proposal through validation or invalidation. The scientific backbone of venture development.

**Key Relationships:**
- FK to `ventures(id)`
- Referenced by `experiments(hypothesis_id)` — experiments test hypotheses
- `evidence` JSONB accumulates supporting/contradicting data points

**Indexing Strategy:**
- Composite index on `(venture_id, status)` for active hypothesis queries
- Index on `type` for category filtering
- Index on `confidence` for prioritization

**Feedback Loop Role:** Hypothesis confidence updates as evidence accumulates. Validated hypotheses become venture assumptions; invalidated ones redirect strategy. The Venture Thesis module tracks validation velocity.

**Growth:** Low-moderate — tens to hundreds per venture.

---

### `customer_interviews`

```sql
customer_interviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    interviewee TEXT NOT NULL,
    transcript TEXT NOT NULL,
    extracted_pains JSONB DEFAULT '[]',
    severity_score FLOAT,
    wtp_stated FLOAT,  -- willingness to pay (stated)
    emotional_intensity FLOAT,
    metadata JSONB DEFAULT '{}',
    conducted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
)
```

**Purpose:** Customer discovery interview storage with AI-extracted insights. Records full transcripts and structured extraction of pains, willingness to pay, and emotional signals.

**Key Relationships:**
- FK to `ventures(id)`
- `extracted_pains` feeds into hypothesis generation
- Severity scores inform product prioritization

**Indexing Strategy:**
- Composite index on `(venture_id, conducted_at)` for chronological browsing
- Index on `severity_score` for prioritizing high-pain customers
- GIN index on `extracted_pains` for pain-pattern queries

**Feedback Loop Role:** Interview insights accumulate over time, increasing confidence in pain severity and WTP estimates. Patterns across interviews validate or challenge hypotheses.

**Growth:** Low — tens to hundreds per venture (interviews are expensive).

---

### `offers`

```sql
offers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    version INT NOT NULL DEFAULT 1,
    icp JSONB NOT NULL,  -- ideal customer profile
    positioning JSONB NOT NULL,
    pricing JSONB NOT NULL,
    messaging JSONB NOT NULL,
    objections JSONB DEFAULT '[]',
    landing_copy JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
)
```

**Purpose:** Offer design iterations. Captures the full offer construct — who it's for (ICP), how it's positioned, how it's priced, how it's communicated, and anticipated objections with responses.

**Key Relationships:**
- FK to `ventures(id)`
- `version` tracks offer evolution
- Informed by `customer_interviews` and `hypotheses`

**Indexing Strategy:**
- Composite index on `(venture_id, version)` for version history
- Index on `created_at` for chronological tracking

**Feedback Loop Role:** Offer versions are compared by conversion metrics. Each iteration incorporates learnings from customer interviews, A/B tests on messaging, and market response data.

**Growth:** Low — tens of offer versions per venture.

---

## System 6: Experimentation

### `experiments`

```sql
experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    module_name TEXT NOT NULL,
    name TEXT NOT NULL,
    hypothesis_id UUID REFERENCES hypotheses(id) ON DELETE SET NULL,
    variants JSONB NOT NULL,  -- [{name, config, allocation_pct}]
    primary_metric TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',  -- draft, running, concluded, cancelled
    results JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    completed_at TIMESTAMP WITH TIME ZONE
)
```

**Purpose:** Unified experiment management across all systems. Any module can run A/B tests, multi-armed bandits, or before/after comparisons. Links experiments to formal hypotheses for structured validation.

**Key Relationships:**
- FK to `ventures(id)`
- FK to `hypotheses(id)` — which hypothesis this experiment tests
- `module_name` identifies the owning module
- Results correlate with `observations` table

**Indexing Strategy:**
- Composite index on `(venture_id, status)` for active experiment queries
- Index on `module_name` for per-module experiment history
- Index on `hypothesis_id` for hypothesis-linked experiments
- Index on `status` for finding running experiments

**Feedback Loop Role:** Experiments are the mechanism for testing improvements. The cycle: feedback reveals pattern → hypothesis formed → experiment runs → winner adopted → new feedback measured.

**Growth:** Moderate — hundreds to low thousands. Created deliberately, not at high frequency.

---

### `observations`

```sql
observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID REFERENCES experiments(id) ON DELETE CASCADE,
    variant_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value FLOAT NOT NULL,
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
)
```

**Purpose:** Raw metric observations for running experiments. Each observation is a single data point — one metric value for one variant at one point in time.

**Key Relationships:**
- FK to `experiments(id)` — parent experiment
- `variant_id` identifies which variant produced this observation
- `metric_name` allows multi-metric experiments

**Indexing Strategy:**
- Composite index on `(experiment_id, variant_id, metric_name)` for aggregation queries
- Composite index on `(experiment_id, timestamp)` for time-series analysis

**Feedback Loop Role:** Observations are the raw data for statistical significance calculations. Sufficient observations trigger automatic experiment conclusion.

**Growth:** **HIGH VOLUME** — many observations per experiment. Partitioning by experiment or time recommended for long-running experiments.

---

### `metrics_definitions`

```sql
metrics_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    type TEXT NOT NULL,  -- ratio, count, duration, rate, score
    numerator TEXT NOT NULL,
    denominator TEXT,
    window TEXT NOT NULL DEFAULT '24h',  -- aggregation window
    target FLOAT,
    guardrail_threshold FLOAT,
    owner_module TEXT NOT NULL,
    UNIQUE (venture_id, name)
)
```

**Purpose:** Centralized metric definitions. Ensures everyone means the same thing by "conversion rate" or "quality score." Defines how metrics are computed, what's good, and what's a guardrail violation.

**Key Relationships:**
- FK to `ventures(id)`
- Referenced by `experiments.primary_metric` by name
- `owner_module` identifies which module is responsible for this metric

**Indexing Strategy:**
- Unique composite index on `(venture_id, name)`
- Index on `owner_module` for per-module metric listing

**Feedback Loop Role:** Metrics definitions are the language of improvement. Clear definitions enable automated monitoring — guardrail breaches trigger alerts, target achievement triggers celebration.

**Growth:** Low — tens to hundreds of metric definitions per venture.

---

### `feedback`

```sql
feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    module_name TEXT NOT NULL,
    source_type TEXT NOT NULL,  -- user_explicit, user_implicit, automated, downstream
    signal_type TEXT NOT NULL,  -- rating, thumbs, click, conversion, quality_score
    value FLOAT NOT NULL,
    item_id UUID,  -- polymorphic reference to what was rated
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
)
```

**Purpose:** Universal feedback storage. Captures all forms of feedback signals — explicit user ratings, implicit behavioral signals (clicks, time-on-task), automated quality assessments, and downstream outcome signals.

**Key Relationships:**
- FK to `ventures(id)`
- `item_id` references the entity being rated (agent_execution, prompt, offer, etc.)
- `module_name` identifies which module the feedback relates to

**Indexing Strategy:**
- Composite index on `(venture_id, module_name, timestamp)` for per-module feedback queries
- Composite index on `(item_id, signal_type)` for per-item feedback aggregation
- Index on `source_type` for filtering by feedback source
- Composite index on `(module_name, signal_type, timestamp)` for trending

**Feedback Loop Role:** This IS the feedback loop. Modules query their own feedback to track performance, identify degradation, and power the `suggest_improvements()` mechanism.

**Growth:** **HIGH VOLUME** — Every user interaction and automated evaluation generates feedback. Partitioning by month recommended.

---

### `costs`

```sql
costs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    module_name TEXT NOT NULL,
    operation TEXT NOT NULL,
    amount FLOAT NOT NULL,
    provider TEXT NOT NULL,  -- openai, anthropic, cohere, google, aws
    model TEXT,
    tokens_input INT,
    tokens_output INT,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
)
```

**Purpose:** Granular cost tracking for every billable operation. Enables per-venture, per-module, per-provider, per-model cost attribution and budget enforcement. Separates input and output tokens for accurate pricing.

**Key Relationships:**
- FK to `ventures(id)`
- Aggregated into `ventures.metrics_summary`
- Correlated with `traces` for cost-per-operation analysis

**Indexing Strategy:**
- Composite index on `(venture_id, timestamp)` for venture cost queries
- Composite index on `(module_name, timestamp)` for per-module spend
- Composite index on `(provider, model, timestamp)` for provider/model analysis
- Index on `timestamp` for time-range aggregations

**Feedback Loop Role:** Cost data feeds the Cost Optimizer which:
- Detects spending anomalies
- Suggests cheaper model alternatives where quality permits
- Enforces budget limits
- Routes requests to optimal providers (cost/quality tradeoff)

**Growth:** **HIGH VOLUME** — Every LLM call, API request, and compute operation generates a cost record. Partitioning required.

---

## Systems 7-8: Deployment & Cross-Venture

### `deployments`

```sql
deployments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    version TEXT NOT NULL,
    environment TEXT NOT NULL,  -- staging, production, canary
    status TEXT NOT NULL DEFAULT 'deploying',  -- deploying, active, rolled_back, superseded
    config JSONB NOT NULL DEFAULT '{}',
    deployed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    rolled_back_at TIMESTAMP WITH TIME ZONE
)
```

**Purpose:** Deployment history. Tracks what version is deployed where, enables rollback, and provides audit trail for production changes.

**Key Relationships:**
- FK to `ventures(id)`
- `config` captures the full deployment configuration (models, agents, prompts at that version)
- Referenced by `incidents` for root cause correlation

**Indexing Strategy:**
- Composite index on `(venture_id, environment, status)` for current deployment lookup
- Index on `status` for finding active deployments
- Index on `deployed_at` for deployment timeline

**Feedback Loop Role:** Deployment metrics (error rate, latency, quality) are compared pre/post deployment. Automated rollback triggers when post-deployment metrics breach guardrails.

**Growth:** Low-moderate — one deployment per release per environment.

---

### `incidents`

```sql
incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    severity TEXT NOT NULL,  -- critical, high, medium, low
    description TEXT NOT NULL,
    root_cause TEXT,
    resolution TEXT,
    detected_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    resolved_at TIMESTAMP WITH TIME ZONE
)
```

**Purpose:** Incident tracking for reliability. Records what went wrong, why, and how it was fixed. Powers post-mortems and reliability improvements.

**Key Relationships:**
- FK to `ventures(id)`
- Correlated with `deployments` by timing for root cause analysis
- Correlated with `events` for timeline reconstruction

**Indexing Strategy:**
- Composite index on `(venture_id, severity)` for priority filtering
- Index on `resolved_at IS NULL` for open incidents
- Index on `detected_at` for timeline

**Feedback Loop Role:** Incident patterns reveal systemic weaknesses. Repeated incidents of the same type trigger automated prevention measures.

**Growth:** Low — ideally very few incidents per venture.

---

### `patterns`

```sql
patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    type TEXT NOT NULL,  -- agent_config, prompt_template, workflow, tool_composition, architecture
    source_venture_id UUID REFERENCES ventures(id) ON DELETE SET NULL,
    config JSONB NOT NULL,
    success_count INT NOT NULL DEFAULT 0,
    failure_count INT NOT NULL DEFAULT 0,
    applicable_domains JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
)
```

**Purpose:** Cross-venture pattern library. Captures successful configurations, workflows, and approaches that worked well in one venture and may apply to others.

**Key Relationships:**
- FK to `ventures(id)` via `source_venture_id` — where the pattern was discovered
- `applicable_domains` lists which venture types benefit from this pattern
- Referenced by Meta-Learning for recommendations

**Indexing Strategy:**
- Index on `type` for pattern-type filtering
- GIN index on `applicable_domains` for domain matching
- Computed column or index on `success_count / (success_count + failure_count)` for success rate ranking

**Feedback Loop Role:** Pattern success/failure counts update each time a pattern is applied. Patterns with high success rates are promoted; those with high failure rates are demoted or deprecated.

**Growth:** Low — tens to hundreds of patterns total.

---

### `flywheel_metrics`

```sql
flywheel_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    metric_name TEXT NOT NULL,
    value FLOAT NOT NULL,
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    trend FLOAT  -- rate of change vs previous period
)
```

**Purpose:** High-level flywheel health metrics. Tracks whether the system is actually improving over time — the meta-measure of the entire platform's value.

**Key Relationships:**
- FK to `ventures(id)`
- Aggregated from all other tables' performance metrics
- Powers the executive dashboard

**Indexing Strategy:**
- Composite index on `(venture_id, metric_name, period_start)` for time-series queries
- Index on `trend` for identifying improving/degrading metrics

**Feedback Loop Role:** This table IS the flywheel measurement. If metrics aren't trending positive, the platform isn't working. Tracks improvement velocity across all dimensions.

**Growth:** Low — one row per metric per time period per venture.

---

## Vector Storage Design (pgvector)

```sql
-- Extension
CREATE EXTENSION IF NOT EXISTS vector;

-- HNSW index for fast similarity search
CREATE INDEX ON embeddings USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

**Design Decisions:**

1. **Separate table**: Embeddings are stored in a dedicated `embeddings` table rather than alongside source data. This keeps source tables lean, allows independent scaling, and avoids bloating frequently-queried tables with large vector columns.

2. **Polymorphic reference**: `source_type` + `source_id` provide a flexible reference back to any content type — documents, entities, queries, agent memories.

3. **Model tracking**: The `model_used` column enables multiple embedding models to coexist. When upgrading models, old embeddings can be identified and re-generated.

4. **HNSW over IVFFlat**: HNSW provides better recall at scale with acceptable insert performance. No need to retrain the index when data changes.

5. **Dimension flexibility**: While the schema shows `vector(1536)`, the actual dimension depends on the embedding model. Multiple tables or a configurable dimension may be needed for different models.

6. **Qdrant escape hatch**: If pgvector becomes a bottleneck (>10M vectors or sub-10ms latency requirements), the abstraction layer allows transparent migration to Qdrant without application code changes.

---

## Partitioning Strategy

Five tables require partitioning due to high write volume:

### `events` — Range partition by month

```sql
CREATE TABLE events (
    ...
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
) PARTITION BY RANGE (timestamp);

-- Monthly partitions created automatically by pg_partman
CREATE TABLE events_2025_01 PARTITION OF events
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
```

### `traces` — Range partition by month

Same strategy as events. Traces have similar growth characteristics and access patterns.

### `agent_executions` — Range partition by month

Same strategy. Old partitions can be moved to cold storage or compressed.

### `costs` — Range partition by month

Enables fast monthly billing queries and old partition archival.

### `feedback` — Range partition by month

High-volume feedback data with time-based access patterns.

### Partition Management

- `pg_partman` extension handles automatic partition creation
- Retention policy: hot (current month), warm (last 6 months, compressed), cold (archived to object storage)
- Partition detach/attach for zero-downtime archival
- Partitions are created 3 months ahead to prevent insertion failures

---

## Migration Strategy (Alembic)

### Setup

```
alembic/
├── env.py              # Async engine configuration
├── versions/           # Migration scripts
└── alembic.ini         # Configuration
```

### Conventions

1. **Auto-generate from models:** `alembic revision --autogenerate -m "description"` — always review generated code
2. **Reversible migrations:** Every `upgrade()` has a corresponding `downgrade()`
3. **Data migrations separate:** Schema changes and data migrations are separate revisions
4. **No breaking changes in production:** Additive-only for deployed systems (add columns nullable, backfill, then add constraints)
5. **Naming:** `YYYYMMDD_HHMM_short_description.py`

### Workflow

```bash
# Generate migration from model changes
alembic revision --autogenerate -m "add_trace_id_to_agent_executions"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1

# Show current state
alembic current
```

### Multi-tenant Considerations

Migrations run once against the shared database. Venture isolation is achieved through row-level filtering (`venture_id`), not separate schemas. This simplifies migration management at the cost of requiring discipline in query construction (enforced by the ORM layer and middleware that auto-injects `venture_id` filters).

---

## JSONB Usage Philosophy

### When to Use JSONB

| Use Case | Example | Rationale |
|----------|---------|-----------|
| Module-specific config | `agents.config` | Each agent type has different configuration needs |
| Experiment variants | `experiments.variants` | Variant structure varies by experiment type |
| Tool schemas | `tools.schema` | JSON Schema format, inherently JSON |
| Metadata bags | `datasets.metadata` | Extensible without migrations |
| Aggregated results | `experiments.results` | Complex nested structures |
| Extracted data | `customer_interviews.extracted_pains` | Semi-structured AI extractions |
| Policy rules | `policies.rules` | Rule structure varies by scope and type |

### When to Use Structured Columns

| Use Case | Example | Rationale |
|----------|---------|-----------|
| Foreign keys | `venture_id UUID` | Referential integrity |
| Filterable status | `status TEXT` | Indexed, constrained enum |
| Numeric metrics | `quality_score FLOAT` | Aggregation, comparison, indexing |
| Timestamps | `created_at TIMESTAMP` | Range queries, sorting, partitioning |
| Identifiers | `name TEXT` | Uniqueness constraints, human readability |
| Cost amounts | `amount FLOAT` | Summation, comparison, budgets |
| Token counts | `tokens_input INT` | Aggregation, cost calculation |

### Rule of Thumb

> If you need to `WHERE` on it, `JOIN` on it, or `ORDER BY` it frequently, it should be a column. If it's configuration, metadata, or a schema that varies by context, use JSONB.

### JSONB Indexing

GIN indexes are applied selectively:
- `config` columns get GIN indexes only on tables where JSONB queries are common
- `@>` containment queries are preferred over deep path extraction for index utilization
- Partial GIN indexes on specific JSONB keys for hot query patterns
- Expression indexes on commonly-queried JSONB paths (e.g., `CREATE INDEX ON agents ((config->>'model'))`)

---

## Multi-Tenancy via `venture_id`

### Approach

Row-level filtering via `venture_id` on every table (except `users`, `tools`, and `patterns` which may be global). This is simpler than schema-per-tenant while providing sufficient isolation for the current scale.

### Enforcement Layers

1. **PostgreSQL RLS**: Row-Level Security policies enforce isolation at the database layer (see "Row-Level Security" section above)
2. **ORM layer**: SQLAlchemy query builder automatically injects `venture_id` filter
3. **API middleware**: Extracts venture context from auth token, sets `app.current_venture_id` on the database session
4. **Database constraints**: Foreign keys enforce referential integrity to `ventures(id)`
5. **Application code**: `BaseModule.venture_context` provides scoping for all module operations

### Isolation Guarantees

- Data isolation: Queries never return data from other ventures (enforced by RLS + ORM)
- Cost isolation: Costs are attributed per-venture for accurate billing
- Performance isolation: Heavy ventures don't block others (task queue priority, connection limits)
- Configuration isolation: Each venture has independent module configs

### Future Options

If stricter isolation is needed beyond RLS:
- Schema-per-venture (complicates migrations but provides stronger isolation)
- Separate databases (maximum isolation, maximum operational overhead)

---

## Entity-Relationship Summary

```
ventures (1) ─────┬──── (N) tasks
                   ├──── (N) events
                   ├──── (N) traces
                   ├──── (N) artifacts
                   ├──── (N) api_keys
                   ├──── (N) prompts ──── (N) agents ──── (N) agent_executions
                   ├──── (N) tool_credentials
                   ├──── (N) review_queue
                   ├──── (N) policies
                   ├──── (N) datasets ──── (N) labels
                   ├──── (N) models
                   ├──── (N) embeddings
                   ├──── (N) hypotheses ──── (N) experiments ──── (N) observations
                   ├──── (N) customer_interviews
                   ├──── (N) offers
                   ├──── (N) metrics_definitions
                   ├──── (N) feedback
                   ├──── (N) costs
                   ├──── (N) deployments
                   ├──── (N) incidents
                   └──── (N) flywheel_metrics

users (1) ──── (N) api_keys
           ──── (N) review_queue (as reviewer)

tools (1) ──── (N) tool_credentials

patterns (standalone, references source_venture_id)
```

The venture is the gravitational center. Deleting a venture cascades to all child records (with the exception of events and patterns, which are preserved for cross-venture learning and audit).
