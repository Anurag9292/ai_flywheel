# Stack — Target & Lazy Arrival

> **The destination stack is good; we just don't pre-pay for it.** This doc
> reconciles the previous (top-down) stack docs with the bottom-up doctrine:
> *don't stand up infrastructure until a venture demands it.*

---

## The principle

The old stack docs were written for the "39 modules up front" world, so they
specify heavy infrastructure (Temporal, Redis Streams, Postgres+pgvector,
MinIO/S3, a 7-service Docker Compose, Slack Bolt) as **day-one requirements**.
That contradicts the principle in `README.md` and `vision.md`: capability —
including infrastructure — should be **the residue of real demand**, not a
speculative catalog.

So we keep the destination and change the *arrival schedule*:

> **Target stack = the old `../docs/tech-stack.md` + `../docs/infrastructure.md`,
> which remain the canonical reference for the production end-state.
> Arrival = lazy. Each piece is introduced only when a PostlineAI step (see
> `venture-walkthrough.md`) actually forces it.**

This is the same **fake/real Protocol seam** we use for library tools
(`layer1-nodes.md`), now applied to infrastructure: program against an
interface, ship a thin first implementation, swap in the heavy one behind the
same interface when load or durability genuinely demands it.

---

## What we keep, use now

These are sound and have day-one value — no reason to defer:

| Choice | Role | Notes |
|---|---|---|
| **Python 3.12+** | Backend language | AI/ML ecosystem is Python-first. |
| **Pydantic** | Event model + library protocols | The `Event` contract and tool interfaces want exactly this. |
| **structlog** | The `trace-recorder` substrate | Substrate *is* structured logging that also emits `trace.captured`. |
| **litellm** | `llm-gateway` real impl | Already the seam we designed for agentic nodes. |
| **httpx, tenacity** | Real library clients | LinkedIn / Slack / analytics clients need these. |
| **ruff, mypy, pytest** | Tooling | Nothing to defer. |
| **Next.js + TypeScript** | Frontend | Already live (`frontend/`, `/vision` + `/vision-v2`). |

---

## What we defer (and the trigger that un-defers it)

Each row keeps the old docs' choice as the eventual answer. The "Defer until"
column is the concrete PostlineAI step (or condition) that makes it worth
paying for.

| Capability | Thin first impl (now) | Target (old docs) | Defer until |
|---|---|---|---|
| **Event bus** | `InMemoryEventBus` (sync, in-process) | Redis Streams → Kafka (Upstash) | Multiple processes/workers, or events must survive a restart. |
| **Persistence** | in-memory + JSONL trace log | Postgres (Neon) + SQLAlchemy + Alembic | A node needs durable venture state (thesis state, subscriptions) — PostlineAI **Step 5**. |
| **Vector store** | — (none) | pgvector (+ optional Qdrant) | Embeddings appear — PostlineAI **Step 7** (`voice-profile-builder`) or RAG. |
| **Workflow engine** | synchronous bus dispatch | Temporal.io (Cloud) | A flow must pause for hours/days, resume after crash, or wait on a human — PostlineAI **Step 5** (Wizard-of-Oz waits) or **Step 7** (review hold). |
| **Object storage** | — (none) | Cloudflare R2 / MinIO | Artifacts/datasets need storing — later (no Step 1–4 need). |
| **Cache** | dict / function memo | Upstash Redis | Hot-path dedup or cross-process caching matters at load. |
| **Slack** | `FakeSlack` \| thin `httpx` webhook POST | Slack Bolt (Socket Mode / Events API) | Two-way Slack (slash commands, interactive approvals) is needed — around **Step 5**. |
| **Containerization** | `uv run` locally | Docker + Compose → Fly.io | More than one service must run together, or first deploy. |

> **Rule:** adding any deferred item early is the exact premature optimization
> the bottom-up model exists to prevent. Wait for the trigger.

---

## Arrival schedule, mapped to the walkthrough

A compact view of when each heavy piece is expected to enter, by walkthrough
step (see `venture-walkthrough.md`):

- **Steps 1–4 (thesis → desk research → discovery → ad demand test):**
  In-memory bus, JSONL traces, fake/real libraries via Protocol, synchronous
  dispatch. **No Postgres, Redis, Temporal, Docker, or Bolt.** This is the
  walking skeleton that proves the event-driven model.
- **Step 5 (Wizard-of-Oz launch):** First durable state (subscriptions,
  per-customer input) → **Postgres (Neon)**. First long pause / human wait →
  **Temporal**. First two-way Slack (approvals) → **Slack Bolt**. First
  multi-service runtime → **Docker / Fly.io**.
- **Step 6 (measure & decide):** Possibly **Redis** for cross-process metric
  aggregation if collectors run as separate workers.
- **Step 7 (build the agent):** Embeddings for voice profiles → **pgvector**.
  Artifacts (profiles, exemplars) → **R2** if they outgrow the DB.
- **Step 8 (grow):** Scale-out as the old `infrastructure.md` describes —
  Fly.io autoscale, Neon Pro, Upstash, Temporal Cloud. No new *kinds* of
  infra; just turning the existing ones up.

---

## Production target (unchanged from old docs)

For the end-state we adopt `../docs/infrastructure.md` as-is. It is genuinely
well-suited to a solo founder running multiple ventures:

- **Compute:** Fly.io (auto-suspend, scale-to-zero)
- **Frontend:** Vercel
- **Database:** Neon (serverless Postgres + pgvector, branching, PITR)
- **Cache / event transport:** Upstash Redis
- **Workflows:** Temporal Cloud
- **Object storage:** Cloudflare R2 (no egress fees)
- **GPU burst:** Modal (scale-to-zero)
- **Idle cost:** ~$25/month; **early stage:** ~$50–150/month infra.

The scale-to-zero philosophy and "why NOT Kubernetes" reasoning in that doc
hold. We're not changing the destination — only deferring the on-ramp.

---

## Notes & known inconsistencies in the old docs

- **Celery vs. Temporal:** `../docs/package-structure.md` mentions **Celery**
  while `../docs/tech-stack.md` specifies **Temporal** (and explicitly rejects
  Celery). Since we defer both, it doesn't bite now — but when the workflow
  engine arrives, **Temporal is the choice**, per `tech-stack.md`.
- **Frontend libs:** `../docs/tech-stack.md` lists `recharts`, `zustand`,
  `shadcn/ui`, Vercel AI SDK — not all are installed in the current
  `frontend/package.json`. Add each when a screen needs it (same lazy rule).
- These two old docs live in the **top-down** `../docs/` world. This file is
  the bridge; when in doubt about *what* to use, read them — about *when*, read
  this.

---

## See also

- **`../docs/tech-stack.md`** — full target stack rationale (canonical).
- **`../docs/infrastructure.md`** — full hosting/production plan (canonical).
- **`venture-walkthrough.md`** — the steps that trigger each arrival.
- **`layer1-nodes.md`** — the fake/real Protocol seam this doc extends to infra.
