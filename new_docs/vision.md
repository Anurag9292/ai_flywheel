# Vision

> One founder. Multiple ventures. Shared, event-driven capabilities that get
> better with every run. **Bottom-up, not top-down.**

---

## What we're building

A **personal venture operating system** that helps a single founder discover,
validate, build, ship, and grow AI-native products — and gets compounding
faster with every venture, because every venture's events feed shared
capabilities.

What's different about *this* take versus the previous design (`../docs/`):

| Old (top-down) | New (bottom-up) |
|---|---|
| Specify 39 modules across 8 systems first | Pick a real venture; derive nodes only when it needs them |
| Layer 1 = a pre-designed catalog | Layer 1 = the residue of building real ventures |
| "Validation" is a distinct phase with its own machinery | Validation is just *early-stage tool use* of the same nodes production uses |
| Modules talk by direct call OR event (mixed) | **Flow between capabilities is event-driven; leaf I/O is a library** |

---

## The model in one picture

```
                        ┌──────────────────────────────────┐
                        │   LAYER 3 — META (watch & guide) │
                        │   reads event streams across all │
                        │   ventures; promotes patterns;   │
                        │   guides the founder.            │
                        └───────────────┬──────────────────┘
                                        │ (read-only)
            ┌──────────── EVENT BUS ────┴─────────────────┐
            │  campaign.launched, post.published,         │
            │  signal.weak, lead.qualified, ...           │
            └────────┬────────────────────────────┬───────┘
                     ▲                            ▲
       emits/reacts  │                            │  emits/reacts
                     │                            │
   ┌─────────────────┴──────────────┐  ┌──────────┴─────────────────┐
   │  LAYER 2 — VENTURE: PostlineAI │  │  LAYER 2 — VENTURE: ...    │
   │  topology.yaml + prompts +     │  │                            │
   │  knowledge + custom/           │  │                            │
   └────────┬────────────────┬──────┘  └────────────────────────────┘
            │ wires          │ wires
            ▼                ▼
   ┌──────────────────────────────────────────────────────────────┐
   │  LAYER 1 — CAPABILITIES                                      │
   │                                                              │
   │  Event-driven nodes (the nervous system)                     │
   │   • ad-campaign-runner   • signal-analyzer                   │
   │   • ad-analytics-collector  • post-drafter (agentic)  …      │
   │                                                              │
   │  Library tools (the hands — plain function calls)            │
   │   • LLM Gateway   • LinkedIn API   • SEMrush   • Email   …   │
   └──────────────────────────────────────────────────────────────┘
```

Two flavors of capability. One nervous system between them.

---

## The principles (kept short on purpose)

### 1. Bottom-up: ventures come first

We do not design Layer 1 in advance. We pick one venture, walk through what it
actually needs, and create a Layer 1 node *only* when the venture demands it.
The catalog grows by demand, not by speculation. See `venture-walkthrough.md`
for the working example.

### 2. Event-driven flow, library leaves

- **Between capabilities:** events. A node reacts to an event, does work, emits
  a result event. Loose coupling. New nodes can subscribe to existing streams
  without modifying anyone. The event log is the audit trail and the substrate
  Layer 3 watches.
- **Leaf I/O:** plain libraries. The LLM Gateway, the LinkedIn client, the
  SEMrush client are functions/classes you import and call. They don't need to
  pretend to be event-driven; they're the hands.

If you find yourself emitting an event purely so a single, fixed downstream
node can do the next step, that's overkill — call the library directly. Use
events where *decoupling* or *observation* is genuinely valuable.

### 3. Validation is not a separate layer

The same `ad-campaign-runner` that runs a $200 demand-validation ad on day 4
runs the $50k/mo growth campaigns once the product is live. Same node, same
events, same metrics — different scale and stage. That's why the flywheel works:
every event in every stage of every venture flows through the same substrate
and is therefore learnable.

The only meaningful "stage" difference is what's *behind* a node — early on, a
"draft post" node may be implemented by a human (Wizard-of-Oz) before being
swapped for an LLM-backed agent. The event interface stays the same.

### 4. Layer 2 is composition, with a small escape hatch

A venture is, in order of preference:

1. **A topology** (`topology.yaml`) — which Layer 1 nodes, wired to which
   events, with which configuration.
2. **Domain assets** — prompts, knowledge base, ICP, brand voice.
3. **`custom/`** — bespoke Python the topology can't yet express. *Used as a
   last resort.* Repeated patterns here get promoted down into Layer 1.

The escape hatch exists because reality is messy. The promotion mechanism
exists so reality's messiness gets absorbed back into shared capability.

### 5. Layer 3 only thinks and guides

Layer 3 never executes venture work. It reads the event stream, extracts
patterns, surfaces guidance ("you've validated price but not retention — here's
the cheapest next experiment"), and proposes promotions of repeated `custom/`
patterns into Layer 1. It is a co-pilot, not an operator.

### 6. Observability is automatic, not opt-in

Every Layer 1 node call — whether triggered by event or invoked as a library —
emits a trace, a cost, and a metric *automatically*, without the venture author
wiring it. This is the only thing in the system that is not a "node you call":
it's substrate that wraps every call. Without it, Layer 3 has nothing to read,
and the flywheel doesn't spin.

### 7. Cheapest evidence first; kill early, kill cheap

Inherited from the old vision and still right. The platform should make it
*easier* to run a $200 ad test than to spend a week building the wrong agent.
The walkthrough shows how the topology naturally enforces this — the cheapest
nodes (desk research, ads, landing pages) come before the expensive ones
(building real agents).

---

## What "done" looks like for a venture

A venture is "done with the engine" — i.e. genuinely living on the platform —
when:

- Its topology is declared in `topology.yaml`, not scattered code.
- Every step in its lifecycle (discover → validate → ship → grow) is composed
  from Layer 1 nodes.
- Its `custom/` folder is small and shrinking as patterns get promoted.
- Layer 3 can answer: "what did this venture learn that the next one should
  inherit?" — because every meaningful action emitted an event Layer 3 read.

That's the bar. Not "39 modules implemented."

---

## What this doc deliberately does *not* do

- It does **not** enumerate Layer 1 modules. Open `layer1-nodes.md` for the
  small set discovered so far. That file grows over time; this one shouldn't.
- It does **not** prescribe a tech stack. Pick the simplest thing that makes
  the events real — a Python process with an in-memory bus is a perfectly fine
  starting point. Upgrade to Redis Streams / Kafka only when a venture's load
  demands it.
- It does **not** define a phased roadmap. The roadmap is: "ship PostlineAI's
  topology end-to-end, derive nodes as needed, then start venture #2." Phases
  are an output, not an input.

---

## See also

- **`README.md`** — context and reading order.
- **`venture-walkthrough.md`** — PostlineAI, step by step, deriving each
  Layer 1 node from a real need.
- **`layer1-nodes.md`** — the running catalog.
- **`../docs/`** — the previous (top-down) design, kept for reference.
