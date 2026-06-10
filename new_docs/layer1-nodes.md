# Layer 1 — Node & Tool Catalog

> **The running catalog of Layer 1 capabilities, discovered (not designed) by
> walking PostlineAI in `venture-walkthrough.md`.** This file grows only when a
> real venture demands a new capability. If you want to add a node here without
> a venture step that needs it, *don't*.

---

## How to read this file

Three sections, matching the three flavors of Layer 1 thing:

1. **Substrate** — wraps every call automatically. Not invoked.
2. **Library tools** — plain functions/clients you import and call. No events.
3. **Event-driven nodes** — react to events, do work, emit events.

For each node we record:

| Field | Meaning |
|---|---|
| **Reacts to** | Event types it subscribes to. |
| **Calls** | Library tools or LLM Gateway it depends on. |
| **Emits** | Event types it publishes. |
| **Kind** | `dumb` (deterministic / API stitching) or `agentic` (reasons with LLM). |
| **Derived in** | Walkthrough step that introduced it. |

Event names follow `<domain>.<verb>` (past tense for "happened" events,
imperative for "requested" events): `campaign.launched`, `survey.requested`.

---

## 1. Substrate

These are not nodes you invoke — they're the always-on layer that wraps every
Layer 1 call. Without them, Layer 3 has nothing to read.

### `trace-recorder`

Captures inputs, outputs, latency, cost, and version of every Layer 1 node and
library-tool call. Emits a `trace.captured` event on every wrapped call,
consumable by Layer 3.

- **Derived in:** Step 1.
- **Why it isn't a node:** ventures don't call it; it sits underneath every
  call. Adding it as a "node to wire" would defeat its purpose.

### `event-bus` *(also listed under libraries — it's both)*

The pub/sub mechanism every node uses. Listed here too because **it is the
single dependency that everything else in Layer 1 has.**

### `timer-source`

Publishes `tick.daily` / `tick.minute` events onto the bus so timer-driven nodes
re-run on a cadence. Like `trace-recorder`, it is substrate, not a node you wire:
it just emits a timer event and any subscriber reacts through the normal Runtime
path (and is traced automatically). Thin first impl calls `tick()` manually (dev
API / script / test); a real scheduler (cron / Temporal cron) drives it in prod
behind the same surface.

- **Derived in:** Public-data ingestion step (closed the long-deferred
  `tick.daily` trigger).

### Persistence stores (`source-store`, `raw-record-store`, `knowledge-store`)

The first **durable** substrate. Each is a Protocol with an in-memory fake
(zero-infra, the test/demo default) and a real sync-SQLAlchemy impl against Neon
Postgres (any Postgres; swappable via `DB_URL`). They hold, respectively: the
source catalog + per-source resume cursor; the append-only idempotent raw
records with a monotonic watermark; and the knowledge graph (entities/edges) +
materialized views. Migrations via Alembic.

- **Derived in:** Public-data ingestion step (the concrete trigger `stack.md`
  names for Postgres/Neon).

---

## 2. Library tools (plain function calls — no events)

API wrappers, clients, gateways. Pure libraries. Imported and called directly.
A Layer 1 node typically calls one or more of these inside its handler.

| # | Tool | Wraps | Used by | Derived in |
|---|---|---|---|---|
| 1 | `event-bus` | In-memory pub/sub at first; Redis Streams / Kafka later | *every node* | Step 1 |
| 2 | `llm-gateway` | OpenAI / Anthropic / Google etc., with retries and cost tracking | every agentic node | Step 2 |
| 3 | `semrush-client` | SEMrush API (keyword/search-volume) | `market-scanner` | Step 2 |
| 4 | `web-search-client` | Brave / Serper / Exa search & fetch | `market-scanner` | Step 2 |
| 5 | `calendar-client` | Calendly / Google Calendar | venture wiring (Step 3) | Step 3 |
| 6 | `transcription-client` | Whisper / Deepgram | venture wiring (Step 3) | Step 3 |
| 7 | `linkedin-ads-client` | LinkedIn Marketing API | `ad-campaign-runner`, `ad-analytics-collector` | Step 4 |
| 8 | `meta-ads-client` | Meta Marketing API | `ad-campaign-runner`, `ad-analytics-collector` | Step 4 |
| 9 | `analytics-client` | PostHog / Plausible (landing-page analytics) | `ad-analytics-collector` | Step 4 |
| 10 | `slack-client` | Slack web API | `founder-notifier`, `customer-survey` | Step 4 |
| 11 | `email-client` | Postmark / Resend | `founder-notifier`, `customer-survey` | Step 4 |
| 12 | `inbound-collector` | Webhook + email-to-bucket | `input-intake` | Step 5 |
| 13 | `linkedin-posting-client` | LinkedIn content posting API (separate from ads) | `post-scheduler`, `post-analytics-collector` | Step 5 |
| 14 | `billing-client` | Stripe | `subscription-manager` | Step 5 |
| 15 | `job-board-client` | Job aggregator (Indeed / LinkedIn Jobs / Greenhouse / Lever) | `lead-sourcer` | Lead-gen step |
| 16 | `web-scraper-client` | Managed page-scrape/extract (Firecrawl / ScrapingBee). Distinct from `web-search-client`: this *reads* a URL, that one *finds* URLs. | `lead-sourcer` | Lead-gen step |
| 17 | `api-fetch-client` | Generic, auth-aware, content-type-negotiating HTTP GET (httpx). Source-agnostic: returns parsed body + headers; does **not** know any provider. | `source-scraper` | Ingestion step |

> Add a library here only when a node already exists (or is being derived) that
> needs to call it. Don't pre-create wrappers "in case."

---

## 3. Event-driven nodes

Each node is an event-triggered handler. The full table first, then a
canonical entry per node.

| # | Node | Kind | Derived in |
|---|---|---|---|
| 1 | `thesis-tracker` | dumb | Step 1 |
| 2 | `market-scanner` | agentic | Step 2 |
| 3 | `pain-extractor` | agentic | Step 3 |
| 4 | `ad-campaign-runner` | dumb | Step 4 |
| 5 | `ad-analytics-collector` | dumb | Step 4 |
| 6 | `signal-analyzer` | agentic | Step 4 (refactored Step 6) |
| 7 | `founder-notifier` | dumb | Step 4 |
| 8 | `input-intake` | dumb | Step 5 |
| 9 | `post-drafter` | dumb (Step 5, human impl) → agentic (Step 7) | Step 5 |
| 10 | `human-review-queue` | dumb | Step 5 |
| 11 | `post-scheduler` | dumb | Step 5 |
| 12 | `subscription-manager` | dumb | Step 5 |
| 13 | `post-analytics-collector` | dumb | Step 6 |
| 14 | `customer-survey` | dumb | Step 6 |
| 15 | `voice-profile-builder` | agentic | Step 7 |
| 16 | `feedback-collector` | dumb | Step 7 |
| 17 | `prompt-tuner` *(placement TBD — see Open Questions in walkthrough)* | agentic | Step 7 |
| 18 | `lead-sourcer` | dumb | Lead-gen step |
| 19 | `company-needs-analyzer` | agentic | Lead-gen step |
| 20 | `pitch-generator` | agentic | Lead-gen step |
| 21 | `source-registry` | dumb | Ingestion step |
| 22 | `source-scraper` | agentic | Ingestion step |
| 23 | `knowledge-builder` | dumb (LLM-ready seam) | Ingestion step |

### Canonical entries

#### `thesis-tracker`

Maintains the structured thesis for a venture and updates the support state of
each assumption as evidence arrives.

- **Reacts to:** `evidence.collected`, `pain.extracted`, `signal.verdict`,
  `survey.responded`.
- **Calls:** *(none)* — pure bookkeeping over venture-scoped state.
- **Emits:** `thesis.state.updated`.
- **Kind:** dumb.

#### `market-scanner`

Researches the market for a working thesis: keywords, competitors, pricing,
positioning. Synthesizes a structured market map.

- **Reacts to:** `research.requested`.
- **Calls:** `semrush-client`, `web-search-client`, `llm-gateway`.
- **Emits:** `market.landscape.summarized`.
- **Kind:** agentic.

#### `pain-extractor`

Reads transcripts and extracts pain points with frequency and emotional
intensity, deduplicating across calls.

- **Reacts to:** `transcript.captured`.
- **Calls:** `llm-gateway`.
- **Emits:** `pain.extracted`.
- **Kind:** agentic.

#### `ad-campaign-runner`

Launches and configures an ad campaign on the requested platform.

- **Reacts to:** `campaign.requested`.
- **Calls:** `linkedin-ads-client` and/or `meta-ads-client`.
- **Emits:** `campaign.launched`.
- **Kind:** dumb.

#### `ad-analytics-collector`

Collects ad metrics on a daily timer (or whenever a campaign first launches).

- **Reacts to:** `campaign.launched`, `tick.daily`.
- **Calls:** `linkedin-ads-client`, `meta-ads-client`, `analytics-client`.
- **Emits:** `campaign.metrics.updated`.
- **Kind:** dumb.

#### `signal-analyzer`

Interprets metrics against a venture- and stage-specific success rubric and
issues a verdict. **The single node that decides "is this signal good?"** —
reused for ad tests, product engagement, and growth.

- **Reacts to:** `campaign.metrics.updated`, `post.metrics.updated`,
  `survey.responded`.
- **Calls:** `llm-gateway`.
- **Emits:** `signal.verdict` (one of `strong | weak | kill`, with confidence
  and explanation).
- **Kind:** agentic.
- **Note:** the rubric is passed in the reacting event's metadata or read from
  venture state — *the node itself is generic.* Step-6 refactor.

#### `founder-notifier`

Routes important events to the founder via Slack / email / web inbox based on
urgency.

- **Reacts to:** `signal.verdict`, `thesis.state.updated`, `subscription.*`,
  any event tagged `urgent=true`.
- **Calls:** `slack-client`, `email-client`.
- **Emits:** `founder.notified`.
- **Kind:** dumb.

#### `input-intake`

Normalizes raw inbound (voice notes, bullet points, emails) into a
canonical input record keyed by customer.

- **Reacts to:** `inbound.received`.
- **Calls:** `transcription-client` (when audio).
- **Emits:** `input.captured`.
- **Kind:** dumb.

#### `post-drafter`

Turns a customer's raw input into draft LinkedIn posts in their voice.

- **Reacts to:** `input.captured`.
- **Calls:** `llm-gateway` *(once impl is the agent)*; routes through
  `human-review-queue` *(when impl is human)*.
- **Emits:** `post.drafted`.
- **Kind:** dumb (Wizard-of-Oz binding) → agentic (after Step 7).
- **Note:** the prototypical "graduates up the evidence ladder" node. Event
  interface stable; only `impl` changes.

#### `human-review-queue`

Presents events tagged `requires_human=true` to a human reviewer; emits the
expected result event-type once approved or edited.

- **Reacts to:** any event tagged `requires_human=true`.
- **Calls:** `slack-client` (notify), web inbox (present).
- **Emits:** the *original* expected result type (e.g. `post.drafted`,
  `post.approved`).
- **Kind:** dumb.

#### `post-scheduler`

Schedules approved posts and publishes them at their scheduled time.

- **Reacts to:** `post.approved`, `tick.minute`.
- **Calls:** `linkedin-posting-client`.
- **Emits:** `post.scheduled`, `post.published`.
- **Kind:** dumb.

#### `subscription-manager`

Creates, cancels, and updates customer subscriptions; settles billing events.

- **Reacts to:** `subscription.requested`, `subscription.cancellation_requested`.
- **Calls:** `billing-client`.
- **Emits:** `subscription.activated`, `subscription.cancelled`, `payment.captured`,
  `payment.failed`.
- **Kind:** dumb.

#### `post-analytics-collector`

Pulls engagement metrics for published posts on a daily timer.

- **Reacts to:** `post.published`, `tick.daily`.
- **Calls:** `linkedin-posting-client` (read endpoints).
- **Emits:** `post.metrics.updated`.
- **Kind:** dumb.

#### `customer-survey`

Sends NPS / open-ended surveys on a cadence and captures responses.

- **Reacts to:** `survey.requested`, `tick.daily`.
- **Calls:** `email-client`, `slack-client`.
- **Emits:** `survey.responded`.
- **Kind:** dumb.

#### `voice-profile-builder`

Builds a structured voice profile per customer from past posts, brand
guidelines, and exemplars.

- **Reacts to:** `onboarding.materials.received`.
- **Calls:** `llm-gateway`.
- **Emits:** `voice-profile.built`.
- **Kind:** agentic.

#### `feedback-collector`

Normalizes corrections and ratings (from humans, customers, surveys) into a
unified feedback stream that Layer 3 reads.

- **Reacts to:** `post.edited_by_human`, `post.rated`, `survey.responded`.
- **Calls:** *(none)*.
- **Emits:** `feedback.captured`.
- **Kind:** dumb.

#### `prompt-tuner` *(placement TBD)*

Proposes prompt changes for agentic nodes based on accumulated feedback. May
belong in Layer 3 (proposing) with a Layer 1 `prompt-store` doing the apply.
Flagged as an open question in the walkthrough.

- **Reacts to:** `feedback.captured` (batched).
- **Calls:** `llm-gateway`.
- **Emits:** `prompt.tuning_proposed`.
- **Kind:** agentic.

#### `lead-sourcer`

Finds companies hiring for content / brand / founder-comms roles (a strong
"they need ghostwriting now" buying signal), groups postings per company, and
optionally enriches each with a career-page scrape to surface a contact email.

- **Reacts to:** `lead-search.requested`.
- **Calls:** `job-board-client`, `web-scraper-client`.
- **Emits:** `companies.discovered`.
- **Kind:** dumb.

#### `company-needs-analyzer`

Reads each discovered company's postings + career-page snippet and infers what
they most need right now, with a fit score and a one-line pitch angle.

- **Reacts to:** `companies.discovered`.
- **Calls:** `llm-gateway`.
- **Emits:** `company.needs.profiled`.
- **Kind:** agentic.

#### `pitch-generator`

Drafts a tailored outbound pitch per company — both an **email** form (subject
+ short body, when an address is known) and a **LinkedIn** DM variant. Each
pitch is emitted tagged `requires_human=true` so it parks in the existing
`human-review-queue` for founder approval before any send.

- **Reacts to:** `company.needs.profiled`.
- **Calls:** `llm-gateway`.
- **Emits:** `pitch.drafted` (per company; tagged `requires_human`).
- **Kind:** agentic.
- **Note:** the `human-review-queue`'s `result_map` is extended at
  registry-time with `pitch.drafted → pitch.approved`, so the *same* review
  surface parks both posts and pitches — no node-code change.

---

#### `source-registry`

Maintains the enrichable catalog of opaque public-API sources. Stores a URL plus
optional human hints (which override inference) and free-form enrichment; does
not know what any source *is*. Announces the active set.

- **Reacts to:** `source.register.requested`, `source.enrich.requested`.
- **Calls:** `source-store`.
- **Emits:** `sources.updated`.
- **Kind:** dumb.

#### `source-scraper`

The agentic heart of ingestion. Handed an opaque source, it fetches it, infers
*how to read it* (record location, id field, timestamp field, pagination) with
an `Inferencer` (LLM) **once** — caching the plan and re-inferring only on shape
drift — applies human-hint overrides, executes the plan (pagination + cursor),
upserts records idempotently on `(source_id, external_id)`, and advances a
per-source resume cursor so the next scheduled run starts where it left off.

- **Reacts to:** `sources.updated`, `scrape.requested`, `tick.daily`.
- **Calls:** `api-fetch-client`, `inferencer` (`llm-gateway`), `source-store`,
  `raw-record-store`.
- **Emits:** `source.records.ingested`; `source.inference.low_confidence`
  (tagged `requires_human`) when unsure and no hints exist — parked by the
  existing `human-review-queue` (reuse).
- **Kind:** agentic (it reasons about an unknown source's schema with an LLM).
- **Note:** the `Inferencer` is a seam mirroring `Agent`/`Drafter` —
  `LLMInferencer` now, deterministic `FakeInferencer` (structural heuristic) for
  offline tests/demo.

#### `knowledge-builder`

Reads **only newly-added** raw records since its own watermark and builds the
easy-to-consume output: knowledge-graph entities (Company, Job, Department,
Location) + typed edges (`posts`, `in_department`, `in_location`) and
materialized views (`open_roles_by_company`, `job_catalog`). Generic over the
inferred field structure (no provider-specific keys) via an `Extractor` seam.

- **Reacts to:** `source.records.ingested`, `tick.daily`.
- **Calls:** `raw-record-store` (read new), `knowledge-store` (write).
- **Emits:** `knowledge.updated`.
- **Kind:** dumb (`StructuralExtractor`); an `LLMExtractor` can swap in behind
  the seam with no event-contract change — the prototypical dumb→agentic graduation.

## Event vocabulary (so far)

The events that have appeared above, grouped by domain.

- **Thesis:** `evidence.collected`, `thesis.state.updated`.
- **Research:** `research.requested`, `market.landscape.summarized`.
- **Discovery:** `transcript.captured`, `pain.extracted`.
- **Demand testing:** `campaign.requested`, `campaign.launched`,
  `campaign.metrics.updated`, `signal.verdict`.
- **Product (drafting & publishing):** `inbound.received`, `input.captured`,
  `post.drafted`, `post.approved`, `post.scheduled`, `post.published`,
  `post.edited_by_human`, `post.rated`, `post.metrics.updated`.
- **Onboarding:** `onboarding.materials.received`, `voice-profile.built`.
- **Customer success:** `survey.requested`, `survey.responded`.
- **Billing:** `subscription.requested`, `subscription.cancellation_requested`,
  `subscription.activated`, `subscription.cancelled`, `payment.captured`,
  `payment.failed`.
- **Notification & feedback:** any-event `urgent=true`, `founder.notified`,
  `feedback.captured`, `prompt.tuning_proposed`.
- **Outbound lead-gen:** `lead-search.requested`, `companies.discovered`,
  `company.needs.profiled`, `pitch.drafted`, `pitch.approved`.
- **Public-data ingestion:** `source.register.requested`,
  `source.enrich.requested`, `sources.updated`, `scrape.requested`,
  `source.records.ingested`, `source.inference.low_confidence`,
  `knowledge.updated`.
- **Timers (substrate):** `tick.minute`, `tick.daily`.
- **Substrate:** `trace.captured`, `requires_human=true` *(meta-tag, not an
  event type)*.

---

## Conventions

- **Naming.** `<domain>.<verb>` — past tense for things that happened, present
  tense + `.requested` for things being asked for.
- **Event payload.** Always carry `venture_id`, `correlation_id` (so a chain
  of reactions traces back to the originating event), and `emitted_at`.
- **Idempotency.** Nodes treat events as at-least-once. Handlers must be safe
  to re-run. *(How exactly we enforce this is an open question — see
  walkthrough.)*
- **Kind boundary.** A node is `agentic` only if it must reason with an LLM.
  Bias towards `dumb` — it's cheaper, faster, and easier to reason about.
- **Implementation swap.** A node's `impl` (e.g. `human` vs. `agent-v1`) is a
  binding the venture's `topology.yaml` controls. Changing it must not change
  the event interface — that's the rule that lets Wizard-of-Oz graduate
  cleanly into agents.

---

## What is *not* here (by design)

Compared to the old `../docs/`, the following are **deliberately absent** from
this catalog because no PostlineAI step has demanded them yet:

- A "Knowledge Graph Builder" — PostlineAI doesn't need one.
- A "Synthetic Data Generator" — no synthetic data is needed yet.
- A "Simulation Engine" — premature without a venture's load to simulate.
- A "Pattern Library" / "Meta-Learning Engine" — these *might* exist in
  Layer 3, but as Layer 3 capabilities, not Layer 1 nodes.
- "Deployment Engine" / "Reliability & Incident Engine" — infra concerns;
  re-enter only when a venture genuinely needs them.

When a real venture demands one, it gets added — derived from a step in *its*
walkthrough. Until then, it doesn't exist.

---

## Status snapshot

- **Date of derivation:** initial pass (PostlineAI walkthrough, Steps 1–9).
- **Implementation status (live):** the substrate + Steps 1–6 are now built in
  the `flywheel/` package:
  - **Substrate:** `event-bus` (`InMemoryEventBus`), `trace-recorder` — done.
  - **Step 1:** `thesis-tracker` node — done.
  - **Step 2:** `llm-gateway` (Protocol + fake), `web-search-client`,
    `semrush-client` (libraries, Protocol + fakes), the `Agent` seam
    (`SingleCallAgent`), and the `market-scanner` agentic node — done.
  - **Step 3:** `calendar-client`, `transcription-client` (libraries, Protocol +
    fakes) and the `pain-extractor` agentic node — done. `pain.extracted` feeds
    the existing `thesis-tracker` by subscription (no wiring change).
  - **Step 4:** `linkedin-ads-client` / `meta-ads-client` (shared `AdsClient`
    Protocol + fakes), `analytics-client`, `slack-client`, `email-client`
    (Protocol + fakes), and the `ad-campaign-runner`, `ad-analytics-collector`,
    `signal-analyzer` (agentic), `founder-notifier` nodes — done. This closes
    the `campaign.requested → launched → metrics.updated → signal.verdict →
    {thesis-tracker, founder-notifier}` decision loop.
  - **Deferred within Step 4:** the `tick.daily` timer trigger on
    `ad-analytics-collector` (no timer substrate yet — see node TODO).
  - **Step 5 (Wizard-of-Oz):** `inbound-collector`, `linkedin-posting-client`,
    `billing-client` (libraries, Protocol + fakes), and the `input-intake`,
    `post-drafter` (human impl via a `Drafter` seam), `human-review-queue`,
    `post-scheduler`, `subscription-manager` nodes — done. The Wizard-of-Oz
    flow runs `inbound.received → input.captured → post.drafted (requires_human)
    → [parked]`, and on a separate `review.approved` the queue re-emits
    `post.approved → post.scheduled → post.published` under the *same*
    correlation id (park-and-resume across two runs).
  - **Deferred within Step 5 (documented):** durable parking / venture state
    (Postgres), durable waits (Temporal), the `tick.minute` publish timer
    (approved posts publish immediately for now), and `topology.yaml` — all per
    `stack.md`. The `post-drafter` impl binding is reflected in the node version
    (`0.1.0-human`); swapping to `agent-v1` (Step 7) won't change the event
    contract.
  - **Step 6 (measure what's working):** `post-analytics-collector`
    (`post.published → post.metrics.updated`, via a new `get_post_metrics` read
    endpoint on `linkedin-posting-client`) and `customer-survey`
    (`survey.requested → survey.responded`) — done. **No new agentic node:**
    `signal-analyzer` is *reused* by adding `post.metrics.updated` and
    `survey.responded` to its subscriptions, judging each against its payload
    rubric with **zero change to `handle()`** — the first real proof of the
    "validation built the production nodes" claim. Publishing a post now flows
    straight into engagement analytics → signal → thesis/founder.
  - **Deferred within Step 6 (documented):** the `tick.daily` timers on both
    collectors; `customer-survey` returns a deterministic response inline rather
    than waiting on a real human (the park-and-resume shape from Step 5 is the
    documented upgrade).
  - **Outbound lead-gen (PostlineAI customer acquisition, derived from the
    venture's own need to find paying customers):** `job-board-client`,
    `web-scraper-client` (libraries, Protocol + fakes), and the `lead-sourcer`,
    `company-needs-analyzer` (agentic), `pitch-generator` (agentic) nodes —
    done. Composes a new `lead-generation` function in
    `ventures/postlineai.yaml`, reusing `human-review-queue` (with the
    `result_map` extended at registry-time to also resume `pitch.drafted →
    pitch.approved`) and `founder-notifier` with **zero node-code changes**.
    Closes the loop `lead-search.requested → companies.discovered →
    company.needs.profiled → pitch.drafted (parked) → pitch.approved`.
  - **Deferred within lead-gen (documented):** real job-board/scraping APIs
    (today: fakes); durable lead/company state (Postgres trigger); scheduled
    re-scraping (`tick.daily`, Temporal trigger); rate-limiting / proxies; and
    a future `outreach-sender` node + `outreach-client` library (today the
    chain stops at human-approved pitch).
  - **Public-data ingestion cluster (durable persistence arrives):** the first
    real, durable, resumable storage in the system. Adds the `api-fetch-client`
    library (real httpx + auth + content-type negotiation; fake for offline),
    the `Inferencer` seam (`LLMInferencer` + `FakeInferencer`/structural
    heuristic), the `timer-source` substrate (`tick.daily`/`tick.minute`), and
    three durable stores (`source-store`, `raw-record-store`, `knowledge-store`)
    as Protocol + in-memory fake + **sync SQLAlchemy/Neon Postgres** impl with
    Alembic migrations (swappable via `DB_URL`; tests/demo stay on fakes,
    zero-infra). New nodes: `source-registry`, `source-scraper` (agentic — infers
    each source's schema/ingest plan at runtime, caches it, re-infers on drift,
    resumes from a per-source cursor, idempotent upserts), and
    `knowledge-builder` (incremental KG + materialized views over only new
    records). Composed as a new `data-ingestion` function in
    `ventures/postlineai.yaml`; the six public ATS boards the founder pointed at
    (Lever / Greenhouse / Ashby) are **seed sources**, not encoded adapters —
    the scraper infers them generically. Dev API gains
    `/api/ingestion/sources` and `/api/ingestion/knowledge`. **Reuses**
    `human-review-queue` (low-confidence inference parks for a human) with zero
    node-code change.
  - **Deferred within ingestion (documented):** async/Redis transport (still
    sync in-memory); offset/`link_header` pagination (seed sources are
    snapshots; cursor-token paging is implemented); a real secret store for
    `auth_ref` (today an injected resolver); RSS/HTML structured parsing (JSON
    now, behind the same content-type seam); real Postgres `MATERIALIZED VIEW`s
    (today refreshable rows, identical behavior to the fake); and an
    `LLMExtractor` for the knowledge-builder (the `Extractor` seam is in place).
  - Everything from Step 7 onward remains a derived requirement, not yet built.
- **Next slices:** Step 7 — swap `post-drafter`'s human impl for a real LLM
  agent (the `Drafter` seam is already in place) + `voice-profile-builder`,
  where embeddings/pgvector first arrive per `stack.md`.
- **Visualization:** the live topology + trace-replay views are specified in
  `visualization.md` and derive their data from `Runtime.describe()` and the
  `trace.captured` stream. All Steps 1–6 nodes are registered in the dev
  runtime (`flywheel/devserver/topology.py`) and triggerable from `/topology`;
  the human-review queue is visible/approvable via `/api/review` and the
  `/topology` review panel.
