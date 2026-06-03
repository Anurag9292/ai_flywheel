# System 1 — Core Kernel

> Foundation infrastructure that every other system depends on. Provides configuration, identity, event routing, task execution, observability, and artifact management.

---

## Module 1: Platform Core

**Config, secrets, settings, and service registry**

### What It Does

- Manages hierarchical configuration with environment-specific overrides (dev, staging, production) and hot-reload without restarts
- Provides a secrets vault with rotation policies, access auditing, and integration with external KMS providers (AWS KMS, Vault, GCP Secret Manager)
- Maintains a service registry for all platform modules, tracking health status, version, endpoint, and dependencies
- Exposes a unified settings API where ventures can override platform defaults within permitted boundaries
- Handles feature flags with gradual rollout percentages, venture-level targeting, and automatic expiration
- Orchestrates platform bootstrapping sequence ensuring modules start in correct dependency order
- Provides schema-validated configuration with migration support when config shapes evolve across versions
- Emits config-change events to the Event Bus so dependent modules can react to setting changes in real time

### Feedback Loop

Configuration drift and misconfiguration errors detected by Trace & Observability (5) feed back as validation rules and safer defaults. Frequently overridden settings across ventures become candidates for new first-class platform features.

### Feeds Into

- **All modules** — Every module reads configuration, secrets, and feature flags from Platform Core
- **Event Bus (3)** — Config changes are published as events
- **Trace & Observability (5)** — Config state is attached to traces for debugging

### Fed By

- **Trace & Observability (5)** — Error patterns from misconfigurations improve default settings and validation rules
- **Meta-Learning & Flywheel Engine (39)** — Cross-venture analysis identifies optimal default configurations

---

## Module 2: Identity & Tenancy

**Users, ventures, permissions, API keys, and data isolation**

### What It Does

- Manages user accounts with SSO integration (SAML, OIDC), MFA enforcement, and session management across all platform interfaces
- Implements venture-level tenancy with strict data isolation guarantees — no data from one venture is ever accessible to another unless explicitly shared
- Provides a fine-grained permission system with roles (owner, admin, operator, viewer, agent) and resource-level access controls
- Issues and manages API keys with scoping (per-venture, per-module, per-action), rate limits, and automatic rotation schedules
- Tracks usage quotas per venture with configurable hard/soft limits across compute, storage, LLM calls, and API requests
- Supports venture hierarchies (parent/child) for portfolio management with inherited and overridable permissions
- Maintains audit logs of all access and permission changes with tamper-evident storage
- Handles venture lifecycle: creation, configuration, archival, and deletion with proper data cleanup cascades

### Feedback Loop

Access patterns and permission escalation attempts feed back to tighten default permission sets. Ventures that consistently need the same custom roles trigger new built-in role templates.

### Feeds Into

- **All modules** — Every request is authenticated and authorized through Identity & Tenancy
- **Policy Engine (13)** — Venture context determines which policies apply
- **Privacy & PII Engine (19)** — Data isolation rules are enforced at the tenancy layer
- **Cost Optimizer (35)** — Usage tracked per venture for billing and budget enforcement

### Fed By

- **Trace & Observability (5)** — Suspicious access patterns trigger security alerts and permission reviews
- **Pattern & Template Library (38)** — Successful venture configurations become templates for new ventures

---

## Module 3: Event Bus

**Pub/sub, persistence, replay, wildcard subscriptions**

### What It Does

- Provides a high-throughput event streaming backbone connecting all 39 modules with guaranteed at-least-once delivery
- Supports topic-based publish/subscribe with wildcard subscriptions (e.g., `agent.*`, `venture.acme.*`) for flexible event routing
- Persists all events with configurable retention (default 90 days) enabling full system replay for debugging or reprocessing
- Implements event schemas with versioning, backward compatibility validation, and automatic schema registry updates
- Supports dead-letter queues for failed event processing with configurable retry policies and alerting
- Provides event replay from any timestamp with filtering, enabling modules to rebuild state or reprocess after bug fixes
- Offers exactly-once semantics for critical paths (payments, deployments) via idempotency keys and deduplication windows
- Exposes consumer group management for horizontal scaling of event processors with partition-aware load balancing

### Feedback Loop

Event delivery failures and processing latencies feed back to optimize routing, partition strategies, and consumer group sizing. Replay frequency data identifies which event streams need longer retention.

### Feeds Into

- **All modules** — Every module both publishes and subscribes to events for decoupled communication
- **Trace & Observability (5)** — Events form the backbone of distributed traces
- **Task Runtime (4)** — Events trigger task creation and status updates
- **Experiment Tracker (31)** — All experiment-relevant events are captured for analysis

### Fed By

- **Trace & Observability (5)** — Latency data optimizes event routing and partitioning
- **Cost Optimizer (35)** — Identifies high-volume low-value events that can be batched or downsampled

---

## Module 4: Task Runtime

**Work queues, status tracking, retries, dependencies, bulk execution at scale**

### What It Does

- Manages distributed work queues with priority levels, ensuring critical tasks (deployments, human reviews) execute before background work
- Tracks task status through lifecycle states (queued, claimed, running, succeeded, failed, cancelled, retrying) with full state machine semantics
- Implements configurable retry policies with exponential backoff, jitter, max attempts, and dead-letter routing for permanently failed tasks
- Supports DAG-based task dependencies — tasks can declare prerequisites and the runtime ensures correct execution ordering
- Provides bulk execution capabilities for running thousands of tasks in parallel with configurable concurrency limits and backpressure
- Handles task timeouts, heartbeats, and zombie detection — reclaiming tasks from workers that die mid-execution
- Exposes a task scheduling system with cron-like recurring tasks, one-off delayed execution, and rate-limited batch processing
- Maintains task execution history with duration, resource usage, and outcome for capacity planning and optimization

### Feedback Loop

Task failure patterns and execution duration distributions feed back to auto-tune retry policies, timeout values, and concurrency limits. Frequently failing task types trigger alerts for module owners.

### Feeds Into

- **All modules** — Any module can enqueue work for async processing
- **Trace & Observability (5)** — Task execution spans are key components of distributed traces
- **Deployment Engine (36)** — Deployment steps execute as managed tasks
- **Agent Factory (9)** — Agent executions are managed as tasks with orchestration

### Fed By

- **Trace & Observability (5)** — Error analysis identifies systemic task failures requiring infrastructure fixes
- **Cost Optimizer (35)** — Execution cost data informs priority and scheduling decisions
- **Meta-Learning & Flywheel Engine (39)** — Cross-venture patterns optimize default task configurations

---

## Module 5: Trace & Observability

**Distributed tracing, error analysis, replay, debugging — absorbs old Error Analyzer**

### What It Does

- Implements OpenTelemetry-compatible distributed tracing across all module boundaries, capturing the full request path from user action to final response
- Provides automated error clustering — grouping similar errors by root cause, stack trace similarity, and temporal correlation
- Supports full execution replay: given a trace ID, reconstruct the exact sequence of events, LLM calls, tool invocations, and data transformations
- Runs anomaly detection on latency, error rates, and throughput, triggering alerts before users notice degradation
- Maintains per-module health dashboards with SLI/SLO tracking, burn-rate alerts, and automatic escalation
- Performs root cause analysis by correlating errors with recent deployments, config changes, or upstream failures
- Captures LLM-specific observability: token counts, latency per model, cache hit rates, prompt/completion pairs for debugging
- Provides a queryable trace store with structured search (by venture, module, user, error type, duration) and sampling strategies for cost-effective retention

### Feedback Loop

Recurring error patterns become automated detection rules. Debug session outcomes (what the operator actually investigated) train the system to surface more relevant traces and pre-compute root cause hypotheses.

### Feeds Into

- **Platform Core (1)** — Misconfiguration signals improve defaults and validation
- **Task Runtime (4)** — Task failure patterns tune retry policies
- **LLM Gateway (7)** — Provider reliability data informs routing decisions
- **Reliability & Incident Engine (37)** — Anomalies trigger incident detection
- **Cost Optimizer (35)** — Resource usage data feeds cost tracking

### Fed By

- **All modules** — Every module emits traces, metrics, and logs
- **Event Bus (3)** — Events provide the correlation backbone for distributed traces
- **Deployment Engine (36)** — Deployment events enable change-correlated root cause analysis

---

## Module 6: Artifact Manager

**Versioned outputs, reports, model cards, reproducibility, cross-venture search**

### What It Does

- Stores and versions all platform outputs: trained models, evaluation reports, generated datasets, agent outputs, experiment results, and any file-based artifact
- Provides content-addressable storage with deduplication — identical artifacts across ventures are stored once with proper access controls
- Maintains full provenance chains: every artifact links to the code version, config, input data, and execution trace that produced it
- Implements model cards and datasheets as structured metadata, auto-generated from training runs and evaluation results
- Supports cross-venture search with permission-respecting discovery — find similar artifacts, prior art, and reusable components
- Provides artifact lifecycle management: retention policies, archival to cold storage, and garbage collection of orphaned outputs
- Enables reproducibility by capturing the complete execution environment (dependencies, config, seeds) needed to regenerate any artifact
- Exposes comparison tools: diff two model versions, compare evaluation reports side-by-side, track metric progression across artifact versions

### Feedback Loop

Artifact access patterns (which versions are referenced, which are never accessed) feed back to optimize storage tiers and retention policies. Artifacts that get reused across ventures are surfaced to the Pattern Library (38).

### Feeds Into

- **Model Forge (21)** — Model registry stores trained models as versioned artifacts
- **Evaluation Framework (22)** — Evaluation reports and benchmark results are stored artifacts
- **Experiment Tracker (31)** — All experiment outputs are persisted as artifacts
- **Pattern & Template Library (38)** — Reusable artifacts become cross-venture patterns
- **Deployment Engine (36)** — Deployment packages are versioned artifacts

### Fed By

- **All modules** — Every module producing outputs stores them through the Artifact Manager
- **Trace & Observability (5)** — Execution traces link to produced artifacts for debugging
- **Cost Optimizer (35)** — Storage cost data informs retention and tiering decisions
