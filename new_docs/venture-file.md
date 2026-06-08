# The Venture File & the Function Layer

> **Status: built.** This answers the walkthrough's open question #2 — "what does
> `topology.yaml` actually look like?" — now that PostlineAI's topology (Steps
> 1–6, 14 nodes) is real enough to need an explicit definition.

---

## Why this exists

Until now, "what PostlineAI *is*" lived hardcoded in `build_runtime()` — a flat
list of `runtime.register(...)` calls. At 14 nodes with real event fan-out, two
problems showed up:

1. **Legibility** — tracking which node reacts to / emits what, by reading node
   files, doesn't scale.
2. **Multi-venture** — there was no per-venture artifact at all; a second
   venture would have meant forking code.

A **venture file** (`ventures/<name>.yaml`) fixes both: it is the single,
readable, declarative definition of one venture, and the runtime is *built from
it* (`flywheel/venture/loader.py`).

This is the `topology.yaml` from `vision.md` — made concrete.

---

## The three things a venture file holds

Per `vision.md` principle 4, a venture is, in order of preference:

1. **Topology** — which Layer 1 nodes are active, with construction config.
2. **Domain assets** — thesis, ICP, price hypothesis (the `domain:` block).
3. **`custom/`** — a small escape hatch. *(Deferred — not built yet.)*

---

## Functions: a declarative grouping layer

Nodes inside a venture are organized into **functions** (departments):
`market-exploration`, `gtm`, `customer-success`, `billing`, … A function is a
**named bundle of nodes** — marketing, sales, GTM, etc. — that exists for
**composition and legibility**.

> **A function is metadata + a topology fragment. It does NOT orchestrate.**

This is the critical rule. A function does *not* have a `.run()` that sequences
nodes; it does not call nodes. Events still flow node→node via the bus exactly
as before. The function is purely a **grouping lens** over the event graph:

- It groups nodes under a human-meaningful name.
- The events it "owns" (inputs/outputs) are *derived* from its members'
  `reacts_to` / `emits` — not declared.
- Functions **overlap**: a node can belong to several (e.g. `signal-analyzer`
  is in both `market-exploration` and `customer-success`). No function owns a
  node exclusively.

### Why not an orchestrator?

Because an orchestrating "function" that called desk-research → ad-test → decide
would reintroduce exactly the tight, top-down coupling the bottom-up rewrite
exists to remove. The whole point of `signal.verdict` fanning out to
`thesis-tracker` *and* `founder-notifier` is that **nobody orchestrates it** —
nodes react. If a capability genuinely needs multi-step stateful sequencing,
that belongs *inside a single node* behind the `Agent` seam (a `GraphAgent`),
not in a new orchestration layer. See `stack.md`.

---

## Example: `ventures/postlineai.yaml`

```yaml
name: postlineai
domain:
  icp: "seed/Series-A B2B SaaS founders"
  riskiest_assumption: "founders will pay $499/mo for ghostwritten posts"
  price_hypothesis_usd: 499

functions:
  - name: market-exploration
    description: Desk research + the ad-test demand loop.
    nodes:
      - name: market-scanner
      - name: ad-campaign-runner
      - name: ad-analytics-collector
      - name: signal-analyzer          # shared with customer-success

  - name: gtm
    description: The Wizard-of-Oz product flow.
    nodes:
      - name: input-intake
      - name: post-drafter
        config:
          impl: human                  # Step-7 swaps this to agent-v1 (one line)
      - name: human-review-queue
      - name: post-scheduler
  # … thesis, discovery, billing, customer-success …
```

### Node config

`config` is passed to the node's factory in the **registry**
(`flywheel/venture/registry.py`) at *construction* time. Today the only real
binding is `post-drafter.impl` (`human` → `agent-v1` is the Step-7 swap).

> **Note:** per-event *rubrics* (e.g. `signal-analyzer`'s "would pay $499/mo")
> are **not** node config — they still travel in the event payload at runtime.
> `config` is for construction-time bindings only.

---

## How it loads

```
ventures/postlineai.yaml
   └── load_venture()            → a validated Venture (Pydantic)
        └── build_runtime_from_venture()
             └── for each (deduplicated) node spec: registry.build_node(name, config)
                  └── runtime.register(node)
```

`build_runtime()` in `flywheel/devserver/topology.py` is now a thin wrapper that
loads the default venture — so the dev API, demos, and tests are unchanged.
Overlapping nodes (a node in multiple functions) register **once**.

---

## Intended vs. actual: the lint round-trip

The venture file is the **intended** composition; `Runtime.describe()` is the
**actual**, code-derived graph. `flywheel/venture/view.py` closes the loop:

- **`function_view(venture, describe)`** — groups the live topology by function,
  with the events each function owns as inputs/outputs. *(This is the structured
  "who reacts to / emits what" view, per-department.)*
- **`lint_venture(venture, describe)`** — flags `unknown_nodes` (named but not in
  the registry), `inactive_nodes` (named but not registered), `config_conflicts`
  (same node, differing config), plus the Layer 1 orphan/unproduced lint.

Both are exposed at **`GET /api/venture`** for the dev UI.

---

## Deferred (faithful to the bottom-up rule)

- **Event wiring declared in the file** (nodes dropping hardcoded `reacts_to`) —
  only if a second venture needs *different* wiring. Today subscriptions stay in
  node code; the file declares the roster + config.
- **`custom/` escape hatch**, per-venture credentials / multi-tenancy, durable
  venture state (Postgres) — unchanged deferrals per `stack.md`.
- **A second venture** — the schema supports it; building one is what will prove
  function reuse across ventures.

---

## See also

- **`vision.md`** — Layer 2 as composition; the three-part venture model.
- **`layer1-nodes.md`** — the node/event catalog the venture composes.
- **`visualization.md`** — the live topology the function view groups.
- `flywheel/venture/` — schema, registry, loader, and the function view/lint.
