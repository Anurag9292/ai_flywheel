# Database Schema

## Overview

AI Flywheel uses PostgreSQL with the pgvector extension. The schema is designed around three principles:

1. **Venture-scoped isolation** — Almost every table has a `venture_id` foreign key, enabling multi-tenant data separation
2. **Universal feedback** — Outcome recording is baked into the schema, not bolted on
3. **JSONB for evolution** — Configuration and metadata use JSONB to allow modules to evolve without migrations

---

## Core Tables

### `ventures`

```sql
ventures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    domain TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',  -- active, paused, archived
    config JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    metrics_summary JSONB DEFAULT '{}'
)
```

**Purpose:** Top-level namespace for all AI ventures. Every other entity is scoped to a venture (or is global). The venture is the organizational boundary — all data, agents, experiments, and costs are attributed here.

**Key Relationships:**
- Parent of almost every other table via `venture_id` FK
- Referenced by `module_instances`, `events`, `outcomes`, `experiments`, `prompts`, `agents`, `datasets`, `models`, `costs`, `knowledge_edges`

**Indexing Strategy:**
- Primary key on `id`
- Unique index on `name`
- Index on `status` for filtering active ventures
- GIN index on `config` for JSONB queries

**Feedback Loop Role:** The `metrics_summary` JSONB is a denormalized rollup of key metrics across all modules — updated periodically by a background task. Enables fast dashboard rendering without joining across all tables.

**Growth:** Low volume — tens to hundreds of ventures. This table stays small.

---

### `module_instances`

```sql
module_instances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_name TEXT NOT NULL,
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    config JSONB NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'initialized',  -- initialized, running, paused, error
    version TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    UNIQUE (module_name, venture_id)
)
```

**Purpose:** Tracks which modules are active for each venture and their configuration. A module can be instantiated globally (`venture_id = NULL`) or per-venture.

**Key Relationships:**
- FK to `ventures(id)` — nullable for global modules (e.g., LLM Gateway)
- Referenced by name from `events`, `outcomes`, `costs`

**Indexing Strategy:**
- Unique composite index on `(module_name, venture_id)`
- Index on `status` for health monitoring
- Index on `venture_id` for per-venture queries

**Feedback Loop Role:** Module status transitions are event-sourced. Error states trigger the Reliability Engine to investigate and potentially restart.

**Growth:** Low volume — 30 modules × number of ventures. Hundreds of rows.

---

### `events`

```sql
events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL,
    source_module TEXT NOT NULL,
    venture_id UUID REFERENCES ventures(id) ON DELETE SET NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
)
```

**Purpose:** Persistent event log. Every event published on the event bus is written here for audit, replay, and analytics. This is the system's memory of what happened.

**Key Relationships:**
- FK to `ventures(id)` — nullable for global events
- No FK to `module_instances` (uses `source_module` text for flexibility)

**Indexing Strategy:**
- Index on `event_type` for subscription replay
- Composite index on `(venture_id, timestamp)` for venture-scoped time queries
- Composite index on `(source_module, timestamp)` for per-module auditing
- Partial index on recent events (last 7 days) for hot queries

**Feedback Loop Role:** The event log enables:
- Replaying sequences to debug issues
- Pattern detection (which event sequences correlate with good outcomes?)
- Cross-module analytics (how do upstream events affect downstream performance?)

**Growth:** **HIGH VOLUME** — Potentially thousands of events per hour per venture. This is the highest-growth table. Partitioning required (see Partitioning section).

---

### `outcomes`

```sql
outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_name TEXT NOT NULL,
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    action_id TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    outcome_type TEXT NOT NULL,  -- quality, latency, cost, accuracy, user_satisfaction
    outcome_value FLOAT NOT NULL,
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
)
```

**Purpose:** Universal feedback storage. Every module records the outcome of its actions here. This is the raw material for the flywheel — the data that enables continuous improvement.

**Key Relationships:**
- FK to `ventures(id)`
- `action_id` correlates to specific executions (e.g., `agent_executions.id`)
- `input_hash` enables finding outcomes for similar inputs

**Indexing Strategy:**
- Composite index on `(module_name, venture_id, timestamp)` for per-module performance queries
- Index on `action_id` for looking up outcomes of specific actions
- Index on `input_hash` for similar-input analysis
- Composite index on `(outcome_type, timestamp)` for type-specific trending

**Feedback Loop Role:** This IS the feedback loop. Modules query their own outcomes to:
- Track performance over time
- Identify degradation
- Feed the Reward Modeler for optimization
- Power `suggest_improvements()` via pattern analysis

**Growth:** **HIGH VOLUME** — Every module action produces at least one outcome. Scales with platform usage. Partitioning by month recommended.

---

### `experiments`

```sql
experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_name TEXT NOT NULL,
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    hypothesis TEXT NOT NULL,
    variants JSONB NOT NULL,  -- [{name, config, allocation_pct}]
    metric TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',  -- draft, running, concluded, cancelled
    results JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    completed_at TIMESTAMP WITH TIME ZONE
)
```

**Purpose:** Unified experiment management across all modules. Any module can run A/B tests, multi-armed bandits, or before/after comparisons using this table.

**Key Relationships:**
- FK to `ventures(id)`
- `module_name` identifies which module owns the experiment
- Results reference `outcomes` data via `action_id` correlation

**Indexing Strategy:**
- Composite index on `(venture_id, status)` for active experiment queries
- Index on `module_name` for per-module experiment history
- Index on `status` for finding running experiments

**Feedback Loop Role:** Experiments are the mechanism for testing improvements suggested by the feedback loop. The cycle is: outcomes reveal a pattern → hypothesis formed → experiment runs → winner adopted → new outcomes measured.

**Growth:** Moderate — hundreds to low thousands. Experiments are created deliberately, not automatically at high frequency.

---

### `prompts`

```sql
prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    version INT NOT NULL DEFAULT 1,
    template TEXT NOT NULL,
    variables JSONB DEFAULT '[]',
    performance_score FLOAT,
    tokens_avg INT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    UNIQUE (venture_id, name, version)
)
```

**Purpose:** Versioned prompt templates. Every prompt change creates a new version, enabling rollback, A/B testing between versions, and performance tracking over time.

**Key Relationships:**
- FK to `ventures(id)`
- Referenced by `agents(prompt_id)`
- Performance score derived from `outcomes` for executions using this prompt

**Indexing Strategy:**
- Unique composite index on `(venture_id, name, version)`
- Index on `performance_score` for finding best-performing prompts
- Composite index on `(venture_id, name)` with `ORDER BY version DESC` for latest version lookup

**Feedback Loop Role:** Prompt performance scores are computed from agent execution outcomes. Low-performing prompts trigger improvement suggestions. The Prompt Studio UI surfaces this data for human-in-the-loop refinement.

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
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
)
```

**Purpose:** Agent definitions — the blueprint for an AI agent including its personality (prompt), capabilities (tools), and guardrails (constraints).

**Key Relationships:**
- FK to `ventures(id)`
- FK to `prompts(id)` — which prompt template drives this agent
- Parent of `agent_executions`
- Tools array references `tools(id)` by name

**Indexing Strategy:**
- Composite index on `(venture_id, name)`
- Index on `archetype` for filtering by agent type
- Index on `performance_score` for ranking

**Feedback Loop Role:** Agent performance scores are rolling averages from execution outcomes. Underperforming agents trigger the improvement cycle: analyze errors → suggest prompt/tool changes → experiment → adopt winner.

**Growth:** Low-moderate — tens of agents per venture.

---

### `agent_executions`

```sql
agent_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    input JSONB NOT NULL,
    output JSONB,
    tokens_used INT,
    cost FLOAT,
    duration_ms INT,
    quality_score FLOAT,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
)
```

**Purpose:** Complete audit trail of every agent execution. Records what went in, what came out, how much it cost, and how good it was.

**Key Relationships:**
- FK to `agents(id)` and `ventures(id)`
- `id` is referenced as `action_id` in `outcomes` table
- Cost data feeds into `costs` table aggregations

**Indexing Strategy:**
- Composite index on `(agent_id, timestamp)` for per-agent history
- Composite index on `(venture_id, timestamp)` for venture-wide activity
- Index on `quality_score` for finding outliers
- Index on `cost` for spend analysis

**Feedback Loop Role:** Each execution produces a quality score (from user feedback, automated evaluation, or downstream success signals). This data trains the system to understand what makes a good execution and how to improve.

**Growth:** **HIGH VOLUME** — Every agent interaction creates a row. Thousands per day for active ventures. Partitioning required.

---

### `datasets`

```sql
datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    source TEXT NOT NULL,  -- huggingface, kaggle, web_scrape, upload, synthetic
    name TEXT NOT NULL,
    schema JSONB DEFAULT '{}',
    quality_score FLOAT,
    size BIGINT,  -- bytes
    license TEXT,
    url TEXT,
    metadata JSONB DEFAULT '{}',
    discovered_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
)
```

**Purpose:** Registry of all datasets — discovered externally, uploaded, or synthetically generated. Metadata-only (actual data stored in object storage or referenced by URL).

**Key Relationships:**
- FK to `ventures(id)`
- Referenced by model training runs
- Quality score from Data Quality Engine assessments

**Indexing Strategy:**
- Composite index on `(venture_id, source)`
- Index on `quality_score` for filtering high-quality datasets
- Full-text index on `name` for search
- GIN index on `metadata` for JSONB queries

**Feedback Loop Role:** Dataset quality scores improve over time as the Data Quality Engine learns what constitutes "good data" for each venture's domain. Discovery relevance improves as the Dataset Scout learns from which discovered datasets actually get used.

**Growth:** Moderate — hundreds to low thousands per venture.

---

### `models`

```sql
models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    type TEXT NOT NULL,  -- classifier, regressor, embedding, generation, rl
    config JSONB NOT NULL DEFAULT '{}',
    metrics JSONB DEFAULT '{}',
    artifact_path TEXT,
    status TEXT NOT NULL DEFAULT 'training',  -- training, evaluating, deployed, archived
    version INT NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
)
```

**Purpose:** Registry of trained ML models with their configuration, evaluation metrics, and deployment status.

**Key Relationships:**
- FK to `ventures(id)`
- `config` references `datasets(id)` used for training
- `artifact_path` points to model storage (S3/local)

**Indexing Strategy:**
- Composite index on `(venture_id, name, version)`
- Index on `status` for finding deployed models
- Index on `type` for filtering

**Feedback Loop Role:** Model metrics are tracked per version. The Evaluation Framework continuously compares deployed models against holdout data and new models, triggering retraining when performance degrades.

**Growth:** Low-moderate — tens of models per venture with multiple versions.

---

### `tools`

```sql
tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    schema JSONB NOT NULL,  -- JSON Schema for input/output
    implementation TEXT NOT NULL,  -- module path or API endpoint
    usage_count INT NOT NULL DEFAULT 0,
    success_rate FLOAT,
    avg_latency_ms FLOAT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
)
```

**Purpose:** Registry of tools available to agents. Each tool has a schema (for LLM function calling), implementation reference, and usage statistics.

**Key Relationships:**
- Referenced by `agents.tools` JSONB array (by name)
- Usage stats updated from `agent_executions`

**Indexing Strategy:**
- Unique index on `name`
- Index on `success_rate` for reliability ranking

**Feedback Loop Role:** Tool success rates and latencies are tracked automatically. Low-reliability tools are flagged for repair or replacement. The Tool Forge can generate new tools based on patterns in failed tool calls.

**Growth:** Low — tens to hundreds of tools total (shared across ventures).

---

### `costs`

```sql
costs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_name TEXT NOT NULL,
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    operation TEXT NOT NULL,
    amount FLOAT NOT NULL,
    provider TEXT NOT NULL,  -- openai, anthropic, cohere, aws, gcp
    tokens INT,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
)
```

**Purpose:** Granular cost tracking for every billable operation. Enables per-venture, per-module, per-provider cost attribution and budget enforcement.

**Key Relationships:**
- FK to `ventures(id)`
- Aggregated into `ventures.metrics_summary`

**Indexing Strategy:**
- Composite index on `(venture_id, timestamp)` for venture cost queries
- Composite index on `(module_name, timestamp)` for per-module spend
- Composite index on `(provider, timestamp)` for provider-level analysis
- Index on `timestamp` for time-range aggregations

**Feedback Loop Role:** Cost data feeds the Cost Optimizer module which:
- Detects spending anomalies
- Suggests cheaper model alternatives where quality permits
- Enforces budget limits
- Routes requests to optimal providers (cost/quality tradeoff)

**Growth:** **HIGH VOLUME** — Every LLM call, API request, and compute operation generates a cost record. Partitioning required.

---

### `knowledge_edges`

```sql
knowledge_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object TEXT NOT NULL,
    confidence FLOAT NOT NULL DEFAULT 1.0,
    source TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
)
```

**Purpose:** Knowledge graph storage as subject-predicate-object triples. Enables structured reasoning, relationship queries, and domain knowledge representation.

**Key Relationships:**
- FK to `ventures(id)`
- Built by Knowledge Graph Builder module
- Queried by agents for structured knowledge retrieval

**Indexing Strategy:**
- Composite index on `(venture_id, subject)` for entity-centric queries
- Composite index on `(venture_id, predicate)` for relationship-type queries
- Composite index on `(venture_id, object)` for reverse lookups
- Trigram index on `subject` and `object` for fuzzy search
- Index on `confidence` for filtering high-confidence facts

**Feedback Loop Role:** Edge confidence scores are updated as new evidence confirms or contradicts relationships. The Knowledge Graph Builder tracks which edges prove useful in downstream tasks and prioritizes expanding high-value subgraphs.

**Growth:** **HIGH VOLUME** — Knowledge graphs can grow to millions of edges for complex domains. Partitioning by venture recommended.

---

## Vector Storage (pgvector)

For embedding-based retrieval, the following columns are added to relevant tables:

```sql
-- Extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Embeddings table (separate for performance)
embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venture_id UUID REFERENCES ventures(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL,  -- document, chunk, entity, query
    source_id TEXT NOT NULL,
    content_preview TEXT,
    embedding vector(1536) NOT NULL,  -- OpenAI ada-002 dimension
    model TEXT NOT NULL DEFAULT 'text-embedding-ada-002',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
)

-- HNSW index for fast similarity search
CREATE INDEX ON embeddings USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

**Design Decisions:**
- Embeddings are stored in a dedicated table rather than alongside source data — this keeps source tables lean and allows independent scaling
- `source_type` + `source_id` provide a polymorphic reference back to the original content
- Multiple embedding models supported via `model` column (dimension must match index)
- HNSW index chosen over IVFFlat for better recall at scale with acceptable insert performance

**Growth:** High — scales with ingested content. Millions of vectors for active ventures.

---

## Partitioning Strategy

Three tables require partitioning due to high write volume:

### `events` — Range partition by month

```sql
CREATE TABLE events (
    ...
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
) PARTITION BY RANGE (timestamp);

-- Monthly partitions created automatically by pg_partman
CREATE TABLE events_2024_01 PARTITION OF events
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

### `agent_executions` — Range partition by month

Same strategy as events. Old partitions can be moved to cold storage or compressed.

### `costs` — Range partition by month

Enables fast monthly billing queries and old partition archival.

### `knowledge_edges` — List partition by venture_id

```sql
CREATE TABLE knowledge_edges (
    ...
) PARTITION BY LIST (venture_id);
```

Knowledge graphs are venture-specific and queried within a single venture context. List partitioning by venture enables partition pruning for all queries.

**Partition Management:**
- `pg_partman` extension handles automatic partition creation
- Retention policy: hot (current month), warm (last 6 months, compressed), cold (archived to object storage)
- Partition detach/attach for zero-downtime archival

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
alembic revision --autogenerate -m "add_performance_score_to_agents"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1

# Show current state
alembic current
```

### Multi-tenant Considerations

Migrations run once against the shared database. Venture isolation is achieved through row-level filtering (`venture_id`), not separate schemas. This simplifies migration management at the cost of requiring discipline in query construction (enforced by the ORM layer).

---

## JSONB Usage Philosophy

### When to Use JSONB

| Use Case | Example | Rationale |
|----------|---------|-----------|
| Module-specific config | `module_instances.config` | Each module has different configuration needs |
| Experiment variants | `experiments.variants` | Variant structure varies by experiment type |
| Tool schemas | `tools.schema` | JSON Schema format, inherently JSON |
| Metadata bags | `datasets.metadata` | Extensible without migrations |
| Aggregated results | `experiments.results` | Complex nested structures |

### When to Use Structured Columns

| Use Case | Example | Rationale |
|----------|---------|-----------|
| Foreign keys | `venture_id UUID` | Referential integrity |
| Filterable status | `status TEXT` | Indexed, constrained enum |
| Numeric metrics | `quality_score FLOAT` | Aggregation, comparison, indexing |
| Timestamps | `created_at TIMESTAMP` | Range queries, sorting, partitioning |
| Identifiers | `name TEXT` | Uniqueness constraints, human readability |

### Rule of Thumb

> If you need to `WHERE` on it, `JOIN` on it, or `ORDER BY` it frequently, it should be a column. If it's configuration, metadata, or a schema that varies by context, use JSONB.

### JSONB Indexing

GIN indexes are applied selectively:
- `config` columns get GIN indexes only on tables where JSONB queries are common
- `@>` containment queries are preferred over deep path extraction for index utilization
- Partial GIN indexes on specific JSONB keys for hot query patterns

---

## Entity-Relationship Summary

```
ventures (1) ──── (N) module_instances
    │
    ├──── (N) events
    ├──── (N) outcomes
    ├──── (N) experiments
    ├──── (N) prompts ──── (N) agents ──── (N) agent_executions
    ├──── (N) datasets
    ├──── (N) models
    ├──── (N) costs
    ├──── (N) knowledge_edges
    └──── (N) embeddings
```

The venture is the gravitational center. Deleting a venture cascades to all child records (with the exception of events, which are set to NULL for audit preservation).
