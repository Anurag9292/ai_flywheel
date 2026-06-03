# State Management, Versioning & Recovery

How the platform tracks project movement, enables revert to any previous state, and ensures data is never lost.

---

## The 6 Layers of State

| Layer | Examples | Changes | Revert Strategy |
|-------|----------|---------|-----------------|
| **Code & Infra** | App code, prompt files, agent configs (YAML) | Daily during dev | Git revert/reset |
| **Configuration** | Venture settings, policies, feature flags, thresholds | Weekly | Venture Snapshots |
| **Operational Data** | Interviews, experiments, feedback, metrics, costs, traces | Continuously | Point-in-time recovery |
| **ML Artifacts** | Trained models, embeddings, datasets, benchmarks | Per training run | Model version pointer |
| **Knowledge** | Knowledge graph, memory engine, pattern library | Continuously | Graph checkpoints |
| **External State** | Ad campaigns, sent emails, published content | Irreversible | Stop + contain (can't un-send) |

---

## Layer 1: Code & Infrastructure (Git)

Standard Git versioning. But in this platform, "code" includes configuration-as-code:

```
What lives in Git (source of truth for released versions):
├── Application code (Python, Next.js)
├── Prompt templates (canonical/released versions)
├── Agent blueprint definitions (YAML)
├── Workflow definitions (YAML)
├── Policy rules (YAML)
├── Database migrations (Alembic)
├── Docker/infrastructure configs
└── Deployment manifests
```

### Promotion Flow

Draft configs live in the database (for rapid experimentation). Once validated, they get committed to Git:

```
Draft (DB only) → Tested → Approved → Committed to Git → Deployed
```

This means:
- You can experiment with prompt variants in the DB without a deploy
- Once a variant wins, it gets promoted to Git (becomes the canonical version)
- Git history shows the complete lineage of every released config

### Revert

```bash
# Undo last deploy
git revert HEAD

# Go back to specific known-good state
git checkout v1.2.3

# See what changed between two states
git diff v1.2.0..v1.3.0 -- prompts/ agents/
```

---

## Layer 2: Configuration State (Venture Snapshots)

The most important concept for day-to-day "undo." A **Venture Snapshot** captures the complete configuration state of a venture at a point in time.

### What a Snapshot Contains

```yaml
venture_snapshot:
  id: vs_01HYXZ3K...
  venture: matchhire
  created_at: "2026-06-01T14:30:00Z"
  created_by: founder
  reason: "Before changing screening threshold from 0.7 to 0.5"
  
  configuration:
    agents:
      - {name: screening_agent, version: 3, prompt_id: prompt_v3, tools: [...]}
      - {name: matching_agent, version: 2, prompt_id: prompt_v2, tools: [...]}
      - {name: jd_optimizer, version: 1, prompt_id: prompt_v1, tools: [...]}
    
    prompts:
      - {name: screening, version: 3, template: "...", performance_score: 0.89}
      - {name: matching, version: 2, template: "...", performance_score: 0.82}
    
    policies:
      - {name: screening_policy, rules: {auto_approve_above: 0.92, review_between: [0.5, 0.92]}}
      - {name: budget_policy, rules: {daily_limit: 50, alert_at: 40}}
    
    feature_flags:
      jd_optimizer: true
      salary_suggestion: {enabled: true, rollout: 50%}
      new_ranking_model: false
    
    thresholds:
      screening_confidence_min: 0.7
      auto_approve_confidence: 0.92
      cost_alert_daily: 50.0
    
    models_active:
      screening_classifier: v3
      matching_embeddings: v2
      jd_quality_scorer: v1
    
    integrations:
      indeed_api: {version: 2, status: active}
      linkedin_api: {version: 1, status: active}
      stripe: {status: active, plan: tier_2}

  # References (not full copies — for efficiency)
  data_refs:
    knowledge_graph_checkpoint: kg_checkpoint_20260601
    experiment_count: 47
    total_executions: 12340
```

### When Snapshots Are Auto-Created

| Trigger | Why |
|---------|-----|
| Before any production config change | Safety net — always revertible |
| Before deploying new agent/prompt versions | In case new version is worse |
| Before experiment starts | Can revert if experiment causes issues |
| Daily (scheduled) | Regular checkpoints |
| Before major data ingestion | In case ingestion corrupts knowledge |
| Manual (on demand) | "I'm about to try something risky" |

### Snapshot Operations

```yaml
operations:
  # Revert configs only (keep all data/metrics/feedback)
  restore_config:
    from: vs_01HYXZ3K
    scope: config_only
    effect: "Agents, prompts, policies, flags, thresholds revert. Data stays."
    
  # Full revert (config + reset active model versions)
  restore_full:
    from: vs_01HYXZ3K
    scope: config_and_models
    effect: "Everything reverts to snapshot state. Operational data since then is kept but marked."
    
  # Clone to staging
  clone:
    from: vs_01HYXZ3K
    target: matchhire_staging
    effect: "Creates a copy of the venture at this state for testing."
    
  # Diff between two snapshots
  diff:
    from: vs_01HYXZ3K
    to: vs_01HYZAB4M
    shows: "What changed between these two states (which configs, which versions)"
    
  # Export (portable archive)
  export:
    from: vs_01HYXZ3K
    format: tar.gz
    includes: "All configs + model artifact references + knowledge checkpoint"
```

### How Revert Works in Practice

```
You: "Screening accuracy dropped after yesterday's change. Revert."

System:
  1. Identifies latest snapshot before the change (vs_01HYXZ3K, created 2026-06-01T14:30)
  2. Shows diff: "screening_confidence_min changed from 0.7 to 0.5, prompt_v4 deployed"
  3. You confirm: "Revert to vs_01HYXZ3K"
  4. System restores: threshold → 0.7, prompt → v3
  5. Active model pointer unchanged (model itself is fine, just config was wrong)
  6. Takes effect immediately (no redeploy needed — config is hot-loaded)
  7. Logs: "Reverted to snapshot vs_01HYXZ3K. Reason: accuracy regression."
```

---

## Workflow State (Temporal.io)

The platform uses Temporal.io as its workflow engine. This fundamentally changes how mid-execution state is managed:

### How Temporal Handles State Hydration

Traditional approach (fragile):
```
Workflow starts → writes checkpoint to DB → continues → writes checkpoint → 
  container dies → 
  new container reads last checkpoint → tries to resume → 
  often fails (missed state, race conditions, partial writes)
```

Temporal approach (durable):
```
Workflow starts → executes Step 1 → calls Agent A → 
  pauses (waiting for human approval) →
  container dies →
  new container picks up →
  Temporal replays event history (Step 1 complete, Agent A called, waiting for approval) →
  workflow state reconstructed automatically →
  approval signal arrives →
  workflow resumes at exact point →
  continues to Step 2
```

### Why This Matters for Our System

Multi-agent workflows routinely:
- **Pause for human approval** — employer reviews candidate shortlist (could be hours/days)
- **Fan out to parallel agents** — 5 agents research simultaneously, then converge
- **Wait for external triggers** — API callback, scheduled timer, customer action
- **Retry failed activities** — LLM provider down, retry with backoff on another provider

Without Temporal, each of these patterns requires custom state machines, checkpoint tables, and recovery logic. With Temporal, they're native primitives.

### What This Means for Recovery

| Scenario | Without Temporal | With Temporal |
|----------|-----------------|---------------|
| Container dies mid-workflow | Custom checkpoint + manual resume logic | Automatic — another worker picks up, replays history |
| Need to retry a failed step | Custom retry table + scheduler | Built-in — configurable retry policy per activity |
| Workflow paused for days | Timeout handling, state expiry logic | Native — workflow sleeps until signal, no resource usage |
| Want to see workflow state | Query checkpoint table (often stale) | Temporal UI shows exact current state in real-time |
| Need to cancel a workflow | Find checkpoint, clean up partial state | `workflow.cancel()` — Temporal handles cleanup |

### Integration Points

- **Task Runtime (Module 4)**: Thin wrapper around Temporal — provides the API for other modules to launch workflows
- **Agent Factory (Module 9)**: Multi-agent orchestration = Temporal workflows. Each agent call = Temporal activity.
- **Human Review Engine (Module 12)**: Approval = Temporal signal. Workflow waits until signal received.
- **Venture Snapshots**: Temporal workflow history is part of the audit trail (not part of snapshots — it's infrastructure state)

---

## Layer 3: Operational Data (Backup & Point-in-Time Recovery)

Operational data — interviews, experiments, feedback, metrics, traces, costs — is the venture's accumulated intelligence. Losing it is catastrophic.

### Backup Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                    BACKUP LAYERS                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Layer A: Real-time replication                              │
│  ├── PostgreSQL streaming replication (hot standby)          │
│  ├── Redis AOF persistence + replication                     │
│  └── RPO: ~0 seconds (no data loss)                         │
│                                                              │
│  Layer B: Continuous WAL archiving                           │
│  ├── PostgreSQL WAL segments archived to S3 every minute     │
│  ├── Enables point-in-time recovery to any second            │
│  └── RPO: < 1 minute                                        │
│                                                              │
│  Layer C: Daily full snapshots                               │
│  ├── pg_dump (logical backup, per-venture export available)  │
│  ├── S3 bucket inventory + cross-region copy                 │
│  ├── Retention: 30 daily + 12 monthly + indefinite yearly    │
│  └── RPO: 24 hours (but Layer B covers the gap)             │
│                                                              │
│  Layer D: Per-venture logical exports                        │
│  ├── On-demand export of all data for a single venture       │
│  ├── Portable format (JSON + referenced artifacts)           │
│  └── For: migration, sharing, archival                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Soft Deletes Everywhere

Nothing is ever physically deleted. Every table uses soft deletes:

```sql
-- Instead of DELETE:
UPDATE experiments SET deleted_at = NOW() WHERE id = 'exp_123';

-- To "undelete":
UPDATE experiments SET deleted_at = NULL WHERE id = 'exp_123';

-- Queries automatically filter deleted records:
SELECT * FROM experiments WHERE deleted_at IS NULL;
```

This means:
- "I accidentally deleted that experiment" → Just undelete it (instant)
- Data integrity is maintained (foreign keys never break)
- Audit trail shows who deleted what and when
- Periodic cleanup job purges records deleted > 90 days ago (configurable)

### Point-in-Time Recovery

```yaml
recovery_scenarios:
  
  accidental_deletion:
    problem: "I deleted experiment exp_47 by mistake"
    solution: "Undelete (soft delete reversal)"
    time: instant
    data_loss: none
    
  data_corruption:
    problem: "A bug corrupted feedback records for the last 2 hours"
    solution: "Point-in-time recovery: restore DB to 2 hours ago for affected tables"
    time: 5-15 minutes
    data_loss: "Last 2 hours of feedback (but other data preserved via selective restore)"
    
  venture_data_issue:
    problem: "Something went wrong with MatchHire's data specifically"
    solution: "Restore MatchHire's tables from last good backup (other ventures unaffected)"
    time: 10-30 minutes
    data_loss: "MatchHire data since backup (other ventures untouched)"
    
  full_disaster:
    problem: "Database server completely gone"
    solution: "Restore from cross-region replica or latest backup + WAL replay"
    time: 30-60 minutes
    data_loss: "< 1 minute (WAL archiving gap)"
```

---

## Layer 4: ML Artifacts (Model Registry)

Every model version is stored immutably. You never lose a model.

### Model Version Registry

```yaml
model_registry:
  venture: matchhire
  
  models:
    screening_classifier:
      versions:
        - v1: {accuracy: 0.72, artifact: s3://artifacts/screening_v1.pt, created: "2026-05-15"}
        - v2: {accuracy: 0.81, artifact: s3://artifacts/screening_v2.pt, created: "2026-05-22"}
        - v3: {accuracy: 0.89, artifact: s3://artifacts/screening_v3.pt, created: "2026-06-01"}  ← active
        - v4: {accuracy: 0.84, artifact: s3://artifacts/screening_v4.pt, created: "2026-06-03"}  ← rolled back
      active: v3
      
    matching_embeddings:
      versions:
        - v1: {retrieval_precision: 0.71, artifact: s3://artifacts/matching_v1/, created: "2026-05-20"}
        - v2: {retrieval_precision: 0.83, artifact: s3://artifacts/matching_v2/, created: "2026-05-28"}  ← active
      active: v2
```

### Revert

```yaml
# Model v4 is worse than v3
action: rollback_model
model: screening_classifier
from_version: v4
to_version: v3
effect: "Immediately serve v3. v4 artifact stays in storage (never deleted)."
time: instant (pointer change)
```

### Dataset Versioning

Training datasets are also versioned:

```yaml
datasets:
  screening_ground_truth:
    versions:
      - v1: {size: 500, created: "2026-05-15", path: s3://datasets/gt_v1.parquet}
      - v2: {size: 1200, created: "2026-05-28", path: s3://datasets/gt_v2.parquet}
      - v3: {size: 3400, created: "2026-06-10", path: s3://datasets/gt_v3.parquet}
    
    lineage:
      v1: "Initial 500 manually labeled by founder"
      v2: "v1 + 700 from employer approve/reject decisions"
      v3: "v2 + 2200 from 3 months of production feedback"
```

### Object Storage Versioning

S3/MinIO buckets have versioning enabled:
- Every upload creates a new version (previous versions preserved)
- No artifact is ever overwritten
- Lifecycle policy: move old versions to cold storage after 90 days
- Can restore any previous version of any artifact

---

## Layer 5: Knowledge State (Graph Checkpoints)

Knowledge graphs and memory engines are the hardest to version because they're interconnected.

### Knowledge Graph Checkpoints

```yaml
knowledge_graph_versioning:
  strategy: checkpoint_and_delta
  
  checkpoints:
    schedule: daily (full graph export)
    triggers: [before_major_ingestion, on_demand]
    format: "nodes + edges + metadata as JSONL"
    storage: s3://backups/knowledge_graphs/matchhire/
    
  deltas:
    tracking: "Every mutation (add/remove/update) is logged with timestamp and source"
    enables: "Undo specific changes without full checkpoint restore"
    
  operations:
    restore_checkpoint:
      effect: "Full graph reverts to checkpoint state"
      use_when: "Major corruption or bad bulk ingestion"
      
    undo_ingestion:
      input: "source_id (e.g., 'indeed_scrape_20260603')"
      effect: "Remove all nodes/edges from that source, keep everything else"
      use_when: "Bad data was ingested from a specific source"
      
    undo_time_range:
      input: "from: T1, to: T2"
      effect: "Remove all mutations between T1 and T2"
      use_when: "Something went wrong during a specific period"
      
    fork:
      effect: "Create a copy of the graph for experimentation"
      use_when: "Want to test a major change without risking the live graph"
```

### Memory Engine Versioning

```yaml
memory_versioning:
  strategy: append_only_with_forget
  
  # Memories are never mutated — only appended or marked as "forgotten"
  properties:
    - Every memory has: id, timestamp, source, content, venture_id
    - "Forgetting" = marking as inactive (not deleting)
    - Compression creates a summary but keeps originals
    
  operations:
    forget_after_date:
      effect: "Mark all memories after date X as inactive"
      use_when: "Agent learned bad patterns from recent data"
      
    forget_from_source:
      effect: "Mark all memories from source Y as inactive"
      use_when: "A data source was unreliable"
      
    restore_forgotten:
      effect: "Reactivate previously forgotten memories"
      use_when: "Oops, those memories were actually good"
```

---

## Layer 6: External State (Irreversible — Stop & Contain)

Some actions cannot be undone. The strategy is prevention + rapid containment.

### Prevention

| Mechanism | How it works |
|-----------|-------------|
| **Human Review Engine** | Approvals before external actions (first email batch, first ad campaign) |
| **Policy Engine** | Hard limits (budget caps, send rate limits, content safety) |
| **Staging/Preview** | Test externally-facing actions in sandbox before production |
| **Gradual rollout** | Send to 10% first, check results, then 100% |

### Containment

| Situation | Action |
|-----------|--------|
| Bad ad campaign live | Pause instantly via API (< 1 second) |
| Wrong email sent | Send correction/apology immediately |
| Bad candidate notification | Send update with correct information |
| Overspending | Cost Optimizer auto-pauses at budget ceiling |

### Audit Trail

Every external action is logged in Trace & Observability with:
- What was sent/done
- To whom
- When
- Which agent/module triggered it
- What approval (if any) was given
- Whether it can be undone or only contained

---

## The "Time Machine" View

The platform provides a unified timeline view across all layers:

```
Timeline for MatchHire:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Jun 1, 14:30  [SNAPSHOT] vs_01HY... "Before threshold change"
Jun 1, 14:31  [CONFIG] screening_confidence_min: 0.7 → 0.5
Jun 1, 14:35  [DEPLOY] prompt screening_v4 activated
Jun 1, 15:00  [DATA] 120 new screening executions
Jun 1, 16:00  [METRIC] screening_accuracy dropped: 89% → 74% ⚠️
Jun 1, 16:01  [ALERT] "Accuracy regression detected since last config change"
Jun 1, 16:05  [REVERT] Restored to vs_01HY... (config only)
Jun 1, 16:06  [METRIC] screening_accuracy recovering: 74% → 87%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Available actions at any point:
  [Restore to this state]  [Show diff since here]  [Clone from here]
```

---

## How This Maps to Existing Modules

| Module | State Management Role |
|--------|----------------------|
| **Artifact Manager (#6)** | Stores and versions all artifacts (models, datasets, exports, snapshots) |
| **Trace & Observability (#5)** | Records every mutation as an event — the audit trail for "what changed when" |
| **Deployment Engine (#36)** | Manages code/infra rollbacks, blue/green deploys |
| **Event Bus (#3)** | Every state change is an event (enables replay and audit) |
| **Task Runtime (#4)** | Tracks all work — provides the "what happened" view |
| **Platform Core (#1)** | Configuration management, snapshot creation/restoration |
| **Model Forge (#21)** | Model registry with version pointers and rollback |
| **Knowledge Graph (#17)** | Checkpoint and delta-based graph versioning |
| **Memory Engine (#11)** | Append-only with soft-forget and restore |
| **Policy Engine (#13)** | Prevents irreversible mistakes (budget caps, approval gates) |

---

## Summary: Recovery Cheat Sheet

| "I need to..." | Method | Time |
|----------------|--------|------|
| Undo a prompt change | Revert prompt to previous version | Instant |
| Undo a config change | Restore venture snapshot (config only) | < 1 min |
| Roll back a model | Change active version pointer | Instant |
| Undelete something | Reverse soft delete | Instant |
| Undo a bad data ingestion | Remove by source ID from knowledge graph | 2-5 min |
| Recover from DB corruption | Point-in-time recovery from WAL | 5-30 min |
| Test something risky | Clone venture to staging first | 5 min |
| Go back to "last Tuesday" | Restore daily snapshot + replay WAL to desired time | 15-60 min |
| Complete disaster recovery | Restore from cross-region backup | 1-4 hours |
| Undo an external action | Can't — but can pause/contain immediately | < 1 min to contain |
