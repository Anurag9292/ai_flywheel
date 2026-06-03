# Infrastructure & Hosting

How the platform is hosted, orchestrated, and scaled — from local development to production.

---

## Compute Profile

This platform is primarily an **orchestration layer** — it coordinates LLM API calls, manages workflows, stores results, and serves a UI. It does NOT run heavy local computation. 90%+ of "compute" is API calls to external providers (OpenAI, Anthropic, Voyage, etc.).

| Component | Pattern | Resource Need |
|-----------|---------|---------------|
| FastAPI backend | Always-on, low CPU, I/O-bound | 1-2 vCPU, 1GB RAM |
| Next.js frontend | Always-on, edge-cacheable | 1 vCPU, 512MB RAM |
| Temporal workers | Always-on, variable load | 1-2 vCPU, 1-2GB RAM |
| PostgreSQL | Always-on, IO-bound | 2 vCPU, 4GB RAM |
| Redis | Always-on, memory-bound | 1 vCPU, 512MB RAM |
| Slack bot | Always-on, negligible | Shares with backend |
| Agent execution | Bursty, I/O-bound (waiting on LLM APIs) | Minimal local CPU |
| Validation pipelines | Bursty (days idle, then 1000 calls/hour) | Minimal local CPU |
| Model fine-tuning | Rare (weekly at most), GPU for minutes | Modal scale-to-zero |

---

## Three Environments

### Local Development ($0/month)

Everything runs on your machine via Docker Compose + direct processes:

```yaml
# docker-compose.yml (infrastructure services only)
services:
  postgres:
    image: pgvector/pgvector:pg16
    ports: ["5432:5432"]
    environment:
      POSTGRES_USER: flywheel
      POSTGRES_PASSWORD: flywheel_dev
      POSTGRES_DB: ai_flywheel
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
```

```bash
# Temporal (lightweight, in-memory, no Docker needed)
temporal server start-dev
# → UI at localhost:8233

# Backend (hot reload)
uvicorn ai_flywheel.api.main:app --reload --port 8000

# Frontend (hot reload)
cd web && next dev
# → App at localhost:3000
```

**Total cost: $0.** Everything local.

---

### Production — Early Stage ($50-150/month)

The stack for 1-3 active ventures, pre-revenue or early revenue:

```
┌─────────────────────────────────────────────────────────────┐
│                    PRODUCTION TOPOLOGY                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────┐                │
│  │  COMPUTE: Fly.io                         │                │
│  │                                          │                │
│  │  ├── api (FastAPI + Slack bot)           │                │
│  │  │   └── 1 machine, auto-sleep when idle │                │
│  │  │                                       │                │
│  │  └── workers (Temporal activity workers) │                │
│  │      └── 1-2 machines, scale with load   │                │
│  │                                          │                │
│  │  Cost: $20-50/month                      │                │
│  └─────────────────────────────────────────┘                │
│                                                              │
│  ┌─────────────────────────────────────────┐                │
│  │  FRONTEND: Vercel                        │                │
│  │                                          │                │
│  │  ├── Next.js (edge deployment)           │                │
│  │  ├── API routes (serverless functions)   │                │
│  │  └── SSE streaming                       │                │
│  │                                          │                │
│  │  Cost: $0-20/month (free tier generous)  │                │
│  └─────────────────────────────────────────┘                │
│                                                              │
│  ┌─────────────────────────────────────────┐                │
│  │  DATABASE: Neon (serverless Postgres)    │                │
│  │                                          │                │
│  │  ├── pgvector enabled                    │                │
│  │  ├── Auto-suspend when idle (5 min)      │                │
│  │  ├── Auto-scale compute on load          │                │
│  │  ├── Branching for testing               │                │
│  │  └── Point-in-time recovery included     │                │
│  │                                          │                │
│  │  Cost: $0-25/month (free tier → Pro)     │                │
│  └─────────────────────────────────────────┘                │
│                                                              │
│  ┌─────────────────────────────────────────┐                │
│  │  CACHE: Upstash Redis (serverless)       │                │
│  │                                          │                │
│  │  ├── Per-request pricing                 │                │
│  │  ├── Event streaming (Redis Streams)     │                │
│  │  └── $0 when idle                        │                │
│  │                                          │                │
│  │  Cost: $0-10/month                       │                │
│  └─────────────────────────────────────────┘                │
│                                                              │
│  ┌─────────────────────────────────────────┐                │
│  │  WORKFLOWS: Temporal Cloud               │                │
│  │                                          │                │
│  │  ├── Managed workflow orchestration      │                │
│  │  ├── Built-in UI for debugging           │                │
│  │  ├── Namespace per venture               │                │
│  │  └── No ops burden                       │                │
│  │                                          │                │
│  │  Cost: $25/month (starter tier)          │                │
│  └─────────────────────────────────────────┘                │
│                                                              │
│  ┌─────────────────────────────────────────┐                │
│  │  STORAGE: Cloudflare R2                  │                │
│  │                                          │                │
│  │  ├── S3-compatible                       │                │
│  │  ├── No egress fees                      │                │
│  │  ├── Artifacts, models, backups          │                │
│  │  └── Versioning enabled                  │                │
│  │                                          │                │
│  │  Cost: $1-5/month                        │                │
│  └─────────────────────────────────────────┘                │
│                                                              │
│  ┌─────────────────────────────────────────┐                │
│  │  GPU BURST: Modal (scale-to-zero)        │                │
│  │                                          │                │
│  │  ├── Model fine-tuning (LoRA/QLoRA)      │                │
│  │  ├── Batch embedding (if self-hosting)   │                │
│  │  ├── Pay-per-second (A100: ~$2-4/hour)   │                │
│  │  └── $0 when not in use                  │                │
│  │                                          │                │
│  │  Cost: $0-30/month (only when training)  │                │
│  └─────────────────────────────────────────┘                │
│                                                              │
└─────────────────────────────────────────────────────────────┘

Total infrastructure: $50-150/month
```

---

### Production — Scaled ($300-1000/month)

When running 5+ ventures with real customer traffic:

| Component | Service | Scaling |
|-----------|---------|---------|
| Backend | Fly.io (2-4 instances, auto-scale) | Scale on request count |
| Frontend | Vercel Pro (edge, analytics) | Automatic |
| Database | Neon Pro (read replicas, larger compute) | Scale on connections/queries |
| Cache | Upstash Pro (higher limits, multi-region) | Per-request |
| Workflows | Temporal Cloud Pro | Scale on workflow volume |
| Traces | ClickHouse Cloud (OLAP for observability) | Scale on write volume |
| Storage | Cloudflare R2 | Unlimited |
| GPU | Modal (more frequent training) | Scale to zero |

---

## Service Selection Rationale

### Fly.io (Compute)

**What:** Runs the FastAPI backend and Temporal workers.

**Why Fly.io:**
- Machines auto-suspend when idle → $0 when sleeping
- Wake from sleep in <1 second on first request
- Simple deployment (`fly deploy`)
- Multi-region if needed later
- Fair pricing (pay for actual usage, not reserved capacity)

**Why not alternatives:**
- **Railway:** Similar but slightly more expensive, less control over machine lifecycle
- **Render:** Good but slower cold starts, no auto-sleep on free tier
- **AWS ECS/Lambda:** More complex, more expensive for always-on services
- **Kubernetes:** Massive overkill for 1 person (see below)

### Vercel (Frontend)

**What:** Hosts the Next.js application.

**Why Vercel:**
- Native Next.js support (built by the same team)
- Edge deployment (fast globally)
- Serverless functions for API routes
- Free tier handles most early-stage traffic
- Vercel AI SDK integration for streaming

**Why not alternatives:**
- **Fly.io for frontend too:** Works but loses edge optimization and Next.js-specific features
- **Cloudflare Pages:** Good but less Next.js integration
- **Self-hosted:** Unnecessary complexity

### Neon (PostgreSQL)

**What:** Primary database (application data + pgvector).

**Why Neon:**
- Serverless — auto-suspends when idle ($0 when sleeping)
- pgvector support built-in
- Database branching (create instant copies for testing)
- Point-in-time recovery included
- Auto-scaling compute (handles traffic spikes without pre-provisioning)
- Connection pooling built-in

**Why not alternatives:**
- **Supabase:** Good but more opinionated, includes features we don't need (auth UI, realtime)
- **AWS RDS:** Not serverless, always-on cost, more ops burden
- **Fly Postgres:** Self-managed, no auto-suspend, more ops
- **PlanetScale:** MySQL only (we need Postgres for pgvector + RLS)

### Upstash (Redis)

**What:** Caching, event streaming, session state.

**Why Upstash:**
- Serverless — per-request pricing ($0 when idle)
- Redis Streams support (for event bus)
- No connection limits to worry about
- Multi-region available when needed

**Why not alternatives:**
- **Fly Redis:** Self-managed, no auto-suspend
- **AWS ElastiCache:** Expensive always-on, overkill
- **Dragonfly:** Self-hosted, ops burden

### Temporal Cloud (Workflows)

**What:** Manages all workflow orchestration (agent execution, validation pipelines, migrations).

**Why Temporal Cloud:**
- Zero ops burden (they manage the Temporal server)
- Built-in UI for debugging workflows
- Namespace isolation per venture
- SLA guarantees on availability
- Handles scaling automatically

**Why not alternatives:**
- **Self-hosted Temporal:** Requires managing Temporal server + Cassandra/Postgres backend. Significant ops burden for a solo founder.
- **AWS Step Functions:** Vendor lock-in, less flexible, JSON-based (not Python code)
- **Inngest/Trigger.dev:** Lighter but less mature for complex multi-agent orchestration
- **Custom (Celery/etc.):** No durable execution, no state hydration, fragile

### Cloudflare R2 (Object Storage)

**What:** Stores model artifacts, datasets, backups, venture exports.

**Why R2:**
- S3-compatible API (drop-in replacement)
- Zero egress fees (huge cost saving vs S3)
- Object versioning
- Cheap ($0.015/GB/month)

### Modal (GPU Burst)

**What:** Occasional model fine-tuning (LoRA/QLoRA), batch embedding if self-hosting models.

**Why Modal:**
- Scale-to-zero (pay nothing when not training)
- Pay-per-second GPU (A100: ~$2-4/hour)
- Python-native (define compute in Python decorators)
- Fast cold start (~10 seconds)
- No Docker/K8s complexity

**Why not alternatives:**
- **RunPod/Lambda Labs:** Require manual provisioning, no scale-to-zero
- **AWS SageMaker:** Complex, expensive, overkill
- **Google Colab:** Not production-grade, manual
- **Local GPU:** Expensive hardware, always-on power cost, maintenance

---

## Why NOT Kubernetes

| Aspect | Kubernetes | This Platform |
|--------|-----------|---------------|
| Team size | Designed for 10+ engineers | 1 person |
| Service count | Optimal for 50+ microservices | ~5 services |
| Minimum cost | $150+/month (control plane) | $50/month handles everything |
| Setup time | Weeks to configure properly | Hours with Fly.io |
| Ops knowledge | Needs dedicated SRE | PaaS handles infra |
| When justified | 100K+ requests/day, strict compliance | We're at 1K-10K/day |

**When to reconsider:** If a venture scales to thousands of concurrent users with strict compliance requirements (SOC2, HIPAA), dedicated infrastructure via K8s might make sense for THAT specific venture. But the platform itself doesn't need it.

---

## Scale-to-Zero Philosophy

The platform should cost **near $0 when idle** and scale automatically when active:

| Component | When Idle | When Active | Wake Time |
|-----------|-----------|-------------|-----------|
| Fly.io machines | Suspended ($0) | Auto-wake on request | <1 second |
| Neon Postgres | Auto-suspend ($0) | Wake on first query | <1 second |
| Upstash Redis | Per-request ($0) | Pay per command | Instant |
| Temporal Cloud | Sleeping workflows ($0 compute) | Pay per action | Instant |
| Modal GPU | Scale to zero ($0) | Pay per second | ~10 seconds |
| Vercel | Edge-cached ($0 compute) | Scales automatically | Instant |

**Vacation mode:** If you do nothing for 2 weeks, bill drops to ~$25/month (just Temporal Cloud base fee). Everything else sleeps.

---

## Multi-Venture Compute Isolation

Ventures share infrastructure. Isolation is at the data and workflow layer, not compute:

```
Shared compute (all ventures):
├── One FastAPI backend (routes by venture_id)
├── One set of Temporal workers (workflows tagged by venture namespace)
├── One PostgreSQL instance (RLS isolates data at DB level)
├── One Redis (keys prefixed by venture_id)
└── One Next.js app (UI filters by active venture)

Per-venture isolation (logical, not physical):
├── Temporal namespace per venture (workflow isolation)
├── PostgreSQL RLS (data isolation — impossible to read other venture's data)
├── Cost tracking per venture (budget isolation)
├── Feature flags per venture (behavior isolation)
├── Embedding collections per venture (vector isolation)
```

**Physical isolation** (separate databases, separate compute) only needed if a venture has paying customers who contractually require it (SOC2, HIPAA). That's a far-future concern — handle it by deploying that specific venture on dedicated infrastructure when the time comes.

---

## Cost Breakdown (Realistic)

### Early Stage (~3 ventures, pre-revenue)

```
Monthly costs:

LLM API calls:              $100-300  (dominant cost)
├── Agent executions:        $50-150
├── Embeddings:              $20-50
├── Validation pipelines:    $30-100

Infrastructure:             $50-100
├── Fly.io (compute):        $20-40
├── Neon (database):         $0-25
├── Temporal Cloud:          $25
├── Upstash (Redis):         $0-10
├── R2 (storage):            $1-5
├── Vercel (frontend):       $0-20

GPU (occasional):           $0-30
├── Fine-tuning (Modal):     $5-20 per run

External services:          $100-400
├── SEMrush/Ahrefs:          $120
├── Ad spend (validation):   $0-300
├── Domain/SSL:              $10

─────────────────────────────────────
Total:                      $250-800/month
```

### Scaled (5+ ventures, some revenue)

```
Monthly costs:

LLM API calls:              $300-800
Infrastructure:             $200-500
GPU:                        $30-100
External services:          $200-600
─────────────────────────────────────
Total:                      $700-2000/month
```

**The Cost Optimizer module's primary job:** Minimize LLM API spend (smart routing to cheaper models, caching, deduplication). A 30% reduction in LLM costs saves more than eliminating all infrastructure costs.

---

## Deployment Pipeline

```
git push → GitHub Actions → 
  ├── Run tests (pytest)
  ├── Lint (ruff)
  ├── Build Next.js
  ├── Deploy backend to Fly.io (fly deploy)
  ├── Deploy frontend to Vercel (auto on push)
  └── Run Alembic migrations (if schema changed)
```

For the early stage, this can be even simpler:
```
git push → Fly.io auto-deploy (Dockerfile)
git push → Vercel auto-deploy (Next.js detection)
```

---

## Disaster Recovery

| Scenario | Recovery | RTO |
|----------|----------|-----|
| Fly.io machine dies | Auto-restart on another host | <10 seconds |
| Neon outage | Failover to standby (managed) | <30 seconds |
| Temporal Cloud outage | Workflows paused, resume when back | Minutes |
| Need to migrate away from any service | All services use standard protocols (Postgres, Redis, S3, Temporal) | Days (planned) |

**Vendor lock-in risk:** Minimal. Every service uses open standards:
- Neon → any Postgres (migrate with pg_dump)
- Upstash → any Redis
- R2 → any S3-compatible store
- Fly.io → any Docker host
- Temporal Cloud → self-hosted Temporal
- Modal → any GPU provider

---

## Getting Started (First Deploy)

```bash
# 1. Create accounts (one-time, ~30 minutes total)
# - fly.io (free tier)
# - neon.tech (free tier)
# - upstash.com (free tier)
# - temporal.io/cloud (starter plan)
# - vercel.com (free tier)
# - cloudflare.com (R2 free tier)

# 2. Set up Fly.io app
fly launch --name ai-flywheel-api
fly secrets set DATABASE_URL="postgres://..." REDIS_URL="redis://..." TEMPORAL_ADDRESS="..."

# 3. Deploy backend
fly deploy

# 4. Frontend deploys automatically on git push to Vercel

# 5. Run initial migration
fly ssh console -C "alembic upgrade head"

# 6. Done. Platform is live.
```
