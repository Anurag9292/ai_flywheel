# AI Flywheel — New Docs

> A fresh start. The old `docs/` folder is preserved as-is for reference. These
> docs describe a **leaner, bottom-up** way of building the platform.

---

## The shift in philosophy

The previous design (see `../docs/`) was **top-down**: it specified 39 modules
across 8 systems *before* a single venture was built. That is premature
optimization — designing a cathedral before knowing if anyone wants a church.

These docs invert it. We are **bottom-up and venture-first**:

> **Pick one real venture. Walk through what it actually needs, step by step.
> Every time the venture needs a capability, that capability becomes a Layer 1
> node — and not a moment before.**

Layer 1 is not a catalog we design up front. It is the *residue* of building real
ventures. It grows only when a venture demands it.

---

## The three layers

| Layer | What it is | What it does |
|---|---|---|
| **Layer 1 — Capabilities** | Event-driven **nodes** + a few plain **library tools** | Does the actual work. Venture-agnostic. Reusable. |
| **Layer 2 — Ventures** | A **composition / topology** of Layer 1 nodes wired by events | Builds and runs one product. |
| **Layer 3 — Meta** | A watcher over all ventures' event streams | Only thinks and guides. Never executes venture work. |

### Layer 1 — Capabilities

Two flavors live here:

- **Event-driven nodes** — the nervous system. A node *reacts* to an event,
  does something, and *emits* a result event. This is how the system stays
  decoupled and how Layer 3 can observe everything. Example: `ad-analytics-collector`
  reacts to `campaign.launched`, pulls metrics, emits `campaign.metrics.updated`.
- **Library tools** — the hands. Plain functions/clients you call directly. No
  events, no subscriptions. Example: the **LLM Gateway**, the **LinkedIn API
  client**, the **SEMrush client**. A node *calls* a library tool to get work done.

> **Rule of thumb:** *flow between capabilities is event-driven; leaf I/O
> (API wrappers, model gateways) is a library you call.* A typical node is an
> event-triggered handler that calls one or more library tools and emits a
> result event.

A node may be **dumb** (a thin wrapper around an API) or **agentic** (it reasons
over data with an LLM). Both are Layer 1.

### Layer 2 — Ventures

A venture is **not** a forked codebase. It is a **topology**: a declaration of
which Layer 1 nodes are wired to which events, plus the venture's domain assets
(prompts, knowledge, ICP) and a small **escape hatch** (`custom/`) for the rare
logic no node can express yet.

When three ventures all write similar `custom/` code, that pattern gets
**promoted down** into a new Layer 1 node. That promotion *is* the flywheel.

There is no separate "validation" machinery. Discovery, validation, and
production are all just **the venture using Layer 1 nodes at different points in
its life**. Running a LinkedIn ad to *test demand* uses the same node as running
a LinkedIn ad to *grow a live product*.

### Layer 3 — Meta

Reads the event stream from every Layer 2 venture. Extracts patterns, promotes
them into Layer 1, and guides the founder ("ventures that ran ads before
interviews validated 2x faster"). It thinks and guides; it never does venture
work itself. It can only do its job *because* every Layer 1 node call is
automatically observed.

---

## The dependency rule (what makes layering real)

One monorepo. One-way imports, enforced:

```
Layer 2 (ventures)        ──may import──▶  Layer 1 (capabilities)
Layer 1 (capabilities)    ──must NEVER import──▶  Layer 2 (ventures)
Layer 3 (meta)            ──reads events from──▶  Layer 1 + Layer 2
```

If `core/` ever imports `ventures/`, the layering is a lie. The one-way arrow is
the whole game.

---

## Reading order

1. **`vision.md`** — the concise model and principles.
2. **`venture-walkthrough.md`** — the heart of it. We walk one real venture
   (**PostlineAI**) chronologically and *derive* Layer 1 from its needs.
3. **`layer1-nodes.md`** — the running catalog of nodes discovered so far. Small
   on purpose. Grows only as ventures demand.

---

## The venture we walk: PostlineAI

A B2B LinkedIn ghostwriting service for founders/execs who know they should post
but have no time and get no engagement. It's chosen because it exercises the
exact flow that motivates this design — *run ads → analyze them → decide* — and
because the capabilities used to **validate** it (ad running, analytics, signal
analysis) are the **same** ones the live product reuses. That proves the central
claim: validation is not special; it's just early tool use.
