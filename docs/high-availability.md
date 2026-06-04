# High Availability & Reliability

How the platform ensures high availability across all components — from managed services to application code.

---

## Design Philosophy

**HA comes from architecture choices (stateless app + managed stateful services + Temporal), not from building custom HA mechanisms.** The code itself just needs to be stateless and idempotent — enforced through Temporal Activity patterns and database-as-source-of-truth.

---

## Layer 1: Managed Services (HA Built-In)

These are the stateful components. By using managed services, we don't build replication, failover, or backup — it's their job.

| Component | Provider | HA Mechanism | Our Effort |
|-----------|----------|--------------|------------|
| **Database** | Neon | Multi-AZ replication, auto-failover, read replicas | Zero — it just works |
| **Workflow Engine** | Temporal Cloud | Multi-AZ, event-sourced, survives any failure | Zero — Temporal guarantees this |
| **Redis/Cache** | Upstash | Multi-region replication, auto-failover | Zero |
| **Frontend** | Vercel | Edge CDN, global distribution | Zero |
| **Object Storage** | Cloudflare R2 | Globally distributed, 11 9's durability | Zero |

---

## Layer 2: Application Code (Must Be HA-Safe)

### FastAPI Backend (on Fly.io)

**Requirement:** Must be **stateless** — no in-memory state that matters.

```
Request → Load Balancer → Instance A (or B, or C)
                              │
                              ▼
                    All state lives in:
                    • Neon (data)
                    • Upstash (cache, sessions)
                    • Temporal (workflow state)
```

**How Fly.io provides HA:**
- Multiple instances across regions (`min_machines_running = 2`)
- Auto-restart on crash (health checks)
- Rolling deploys (zero-downtime)
- If one instance dies, traffic routes to others instantly

**Our responsibility:** Keep the app stateless. No in-memory state that can't be lost.

---

### Temporal Workers (on Fly.io)

This is where the design is **inherently HA by architecture:**

```
Temporal Cloud (holds all workflow state)
       │
       ├── Worker A (Fly.io, region X) ── dies mid-task
       ├── Worker B (Fly.io, region Y) ── picks up where A left off
       └── Worker C (Fly.io, region Z) ── handles new work
```

**Why this is HA without extra effort:**
- Temporal workers are **stateless** — they poll for tasks, execute them, report results
- If a worker crashes mid-Activity, Temporal retries on another worker
- Workflow state is in Temporal Cloud, not the worker
- We can run 1 worker or 10 workers — same correctness, different throughput

**The killer feature:** A workflow can be mid-execution (e.g., ProspectForge outreach on Day 7 of a sequence), the worker crashes, and Temporal replays the event history on a different worker. The workflow resumes exactly where it left off. This is why we chose Temporal.

---

### LLM Gateway

**Fallback chains provide provider-level HA:**

```
Primary (gpt-4o) fails → Fallback 1 (claude-3-5-sonnet) → Fallback 2 (gpt-4o-mini)
```

If an entire provider goes down (OpenAI outage), traffic automatically routes to the next provider in the chain. No manual intervention.

**Idempotency cache:**

| Phase | Implementation | HA Status |
|-------|---------------|-----------|
| Development | In-memory dict | Not HA (cleared on restart) |
| Production | Redis/Upstash with TTL | Fully HA (multi-region Redis) |

Even without the Redis cache, correctness is maintained because:
- Temporal Activity IDs ensure at-most-once semantics at the workflow level
- Worst case on cache miss = double LLM payment (cost issue, not correctness issue)
- Temporal retries handle transient failures automatically

---

### Event Bus

| Phase | Implementation | HA Status |
|-------|---------------|-----------|
| Phase 0 | In-process (single instance) | Not HA — events only reach same-process handlers |
| Production | Redis Streams (Upstash) | Fully HA — consumer groups, cross-instance delivery |

**Production architecture:**

```
Instance A publishes event → Redis Stream "events:agent.completed"
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
              Instance A       Instance B       Instance C
              (consumer)       (consumer)       (consumer)
```

Consumer groups ensure each event is processed exactly once across all instances.

---

## Layer 3: Failure Scenarios & Recovery

| Failure | What Happens | Recovery | Downtime |
|---------|-------------|----------|----------|
| FastAPI instance crashes | Fly.io routes to healthy instance, restarts crashed one | Automatic | < 5s |
| Temporal worker crashes mid-Activity | Temporal retries Activity on another worker | Automatic | Retry delay (configurable) |
| Temporal worker crashes mid-Workflow | Workflow replays from event history on new worker | Automatic | Instant |
| Neon Postgres failover | Automatic failover to replica | Automatic | ~1s |
| Redis/Upstash failover | Multi-AZ failover | Automatic | Sub-second |
| OpenAI API down | LLM Gateway fallback chain routes to Anthropic | Automatic | Per-call (zero) |
| Entire Fly.io region down | Multi-region machines serve traffic | Automatic | < 10s |
| Temporal Cloud outage | Workflows pause, resume when Temporal recovers (state is durable) | Automatic | Minutes |
| Full deployment (new version) | Rolling deploy — old instances drain, new instances start | Automatic | Zero (rolling) |

---

## What's NOT HA (By Design)

| Component | Why | Impact |
|-----------|-----|--------|
| Local dev environment | Single everything (Docker Compose) | Fine — it's dev |
| In-memory caches (Phase 0) | Cleared on restart | Minor cost (re-fetch/re-compute), no correctness impact |
| Slack bot (single process) | Low traffic, fast restart | ~5s reconnect on crash |

These are acceptable tradeoffs for a solo-founder platform. The critical path (workflows, data, customer-facing operations) is always HA.

---

## Statelessness Rules

For the application code to be HA-safe, these rules must be followed:

1. **No request-scoped state in memory** — All session/user state lives in Redis or Postgres
2. **No workflow state in workers** — Temporal holds all workflow state; workers are disposable
3. **No singleton caches that affect correctness** — Caches are optimization only; cache miss = slower, not broken
4. **Idempotent Activities** — Every Temporal Activity must produce the same result if retried (use Activity ID as cache key)
5. **No local file storage** — All persistent files go to R2/S3; local filesystem is ephemeral
6. **Health checks on every instance** — Fly.io removes unhealthy instances from load balancer automatically

---

## Scaling Model

```
Traffic increases
       │
       ├── More API requests → Fly.io auto-scales FastAPI instances (horizontal)
       ├── More workflows → Add Temporal workers (horizontal, instant)
       ├── More DB queries → Neon auto-scales compute + add read replicas
       ├── More cache pressure → Upstash auto-scales (serverless, no config)
       └── More LLM calls → Already handled by external providers (their problem)
```

**Scale-to-zero:** When idle, Fly.io machines stop (pay nothing). Neon scales compute to zero. Upstash charges per-request. Total idle cost approaches $0.

**Scale-to-peak:** Each component scales independently. No single bottleneck. The platform is I/O-bound (waiting on LLM APIs), not CPU-bound, so horizontal scaling is trivially effective.

---

## Summary

| Question | Answer |
|----------|--------|
| Is the database HA? | Yes — Neon handles it |
| Are workflows HA? | Yes — Temporal's core guarantee |
| Is the API HA? | Yes — run 2+ Fly.io instances |
| Is the LLM Gateway HA? | Yes — fallback chains + idempotency (Redis in prod) |
| Is the Event Bus HA? | Phase 0: No. Production: Yes (Redis Streams) |
| Can we lose data on crash? | No — all durable state is in Postgres/Temporal/R2 |
| Can we lose a workflow on crash? | No — Temporal guarantees this, it's the whole point |
| Can a single instance failure cause downtime? | No — multi-instance + auto-failover on all layers |
