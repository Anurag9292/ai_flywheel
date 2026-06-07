# Visualization — Topology Map & Trace Replay (TODO)

> **Status: planned / in progress.** This doc specifies how we *see* the
> event-driven system: the nodes, the events between them, and the inputs and
> outputs of each run. It is derived **from the real code**, never hand-drawn,
> so the picture can't drift from reality.

---

## Why this exists

The whole architecture *is* a graph: Layer 1 nodes react to events and emit
events; nodes call library tools; the substrate wraps every call. A static
prose catalog (`layer1-nodes.md`) can't show that wiring at a glance, and it
goes stale the moment code changes.

There is already a hand-authored, aspirational map at **`/vision-v2`**
(`frontend/src/components/vision-v2/`) built on **React Flow (`@xyflow/react`)**
+ framer-motion. It is beautiful but **static data** describing the *design*,
not the running system. This plan keeps that rendering engine and feeds it
**code-derived data** instead.

---

## Two views

### View 1 — Static topology map (the wiring)

"What nodes exist, what events they react to / emit, what libraries they call."
A structural graph **derived from the code itself**.

Answers: *Is the wiring correct? What reacts to `campaign.metrics.updated`? Is
any event emitted that nothing reacts to (orphan)? Which nodes are agentic?*

### View 2 — Live trace replay (the flow)

"What actually happened when an event was published." Replays the
`trace.captured` stream: event in → node fired → events out, following the
`correlation_id` chain, with per-call latency and cost.

Answers: *What did this run actually do? With what inputs/outputs? How fast?
How much did it cost? Where did the chain stop?*

Both are generated from the real system, so neither can lie.

---

## Data source — derived from code, not hand-maintained

The single source of truth is the runtime itself:

- **`Node` metadata.** Each node already declares `name`, `version`,
  `reacts_to`. We add descriptive `emits: list[str]` and `calls: list[str]`
  (the library tools / agent it depends on). These are declarative labels for
  introspection — they do not change dispatch.
- **`Runtime.describe()`** walks every registered node plus its bus
  subscriptions and returns a structured topology graph:
  - **nodes** — name, version, kind (`dumb`/`agentic`), `reacts_to`, `emits`, `calls`
  - **library tools** — referenced by nodes' `calls`
  - **events** — as edges: `emits` (node → event) and `reacts` (event → node)
  - **substrate** — the `wraps`-all relationship (`trace-recorder`)
  - **lint** — flags orphan events (emitted but nothing reacts; reacted-to but
    nothing emits). Doubles as a correctness check, not just a picture.
- **Trace stream.** `traces.jsonl` (the `trace.captured` events) feeds View 2.
  Grouped by `correlation_id` into causal chains.

---

## Delivery — dev introspection API

A minimal **FastAPI dev server** owns a single long-lived runtime (one bus +
the registered nodes) and exposes it to the frontend:

- `GET  /api/topology` → `runtime.describe()` JSON (View 1)
- `GET  /api/traces` → live in-memory `trace.captured` rows, grouped into
  ordered, causally-linked chains (View 2)
- `POST /api/publish` → publish an event onto the live bus and run it through
  the real nodes; returns the resulting trace chain. **This is how the frontend
  triggers a real run** — no seeding.
- `POST /api/reset` → clear the in-memory traces.
- CORS for the Next dev origin.

Traces are held **in memory** in the API process (instant, no disk round-trip,
no staleness) and reset when the process restarts. Headless scripts
(`demo*.py`) can additionally append to a JSONL file by passing a `trace_log`.

> **Caveat vs. `stack.md`.** `stack.md` defers standing up a backend HTTP
> service until a venture demands it. This endpoint is a deliberate, narrow
> exception: a **dev-only, local, ephemeral** surface — *not* the venture
> runtime or a production API. It can now *publish* events, but only onto its
> own in-process bus; durable, multi-process transport (Redis/Kafka) stays
> deferred. State resets on restart. If we ever want zero backend services, the
> fallback is a script that writes a static `topology.json` the frontend
> imports.

### Why not seed a file?

An earlier iteration wrote a `traces.jsonl` from a separate seed script that the
API merely read. That meant two processes with two different in-memory buses
that never shared state — the file was the only bridge, and it went stale. Since
the API now owns a persistent runtime, the frontend publishes a **real** event
through the **real** bus and watches the **real** nodes react. Fake *libraries*
(LLM/search) keep it offline and deterministic — exactly the fake/real seam.

---

## Rendering — reuse the `/vision-v2` engine

A new **`/topology`** route reuses the existing React Flow node/edge components
and styling from `vision-v2`:

- Map `runtime.describe()` → the existing `V2Node` / `V2Edge` shapes (the edge
  kinds `emits` / `reacts` / `calls` / `wraps` already exist).
- Layered auto-layout: an event-bus band, nodes below, libraries to the side,
  substrate underneath — mirroring the `vision-v2` layout bands.
- Each node tile shows **name, kind, reacts_to, emits, calls**; click → a detail
  panel with the node's full event in/out contract.
- Trace replay (View 2) reuses the existing `animated` edges + story-stepper
  mechanism to animate a real run over the topology.

---

## Phased plan

1. **Phase 1 — Introspection (backend).** Add `emits`/`calls` to `Node`;
   implement `Runtime.describe()` + orphan-event lint; tests.
2. **Phase 2 — Dev API (backend).** FastAPI app with `/api/topology` +
   `/api/traces`, CORS; register the dev server.
3. **Phase 3 — Static map (frontend).** `/topology` route fetching
   `/api/topology` via react-query; render with the `vision-v2` engine; node
   detail panel.
4. **Phase 4 — Trace replay (frontend).** Fetch `/api/traces`, group by
   `correlation_id`, animate real runs with latency/cost.

Build order: Phases 1–3 (static map) first, then Phase 4 (trace replay).

---

## Deferred / out of scope

- Production API hardening (auth, persistence, deployment) — this is a dev
  introspection surface only.
- Trace persistence beyond JSONL (Postgres) — stays deferred per `stack.md`.

---

## See also

- **`layer1-nodes.md`** — the node/event catalog this map renders.
- **`stack.md`** — the lazy-arrival rule and the dev-API caveat above.
- `frontend/src/components/vision-v2/` — the React Flow engine being reused.
