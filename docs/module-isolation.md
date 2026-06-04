# Module Isolation

How modules remain independent, composable, and safely extractable — enforced programmatically, not by discipline alone.

---

## The Core Rules

1. **Modules never import other modules** — enforced by linter in CI
2. **All inter-module communication flows through events or Core services** — no direct calls
3. **Shared data contracts live in `core/contracts/`** — typed, versioned, module-agnostic
4. **Each module owns its own tables** — other modules cannot query them directly
5. **The LLM Gateway is a Core service** — modules call `core.llm`, not the agent_runtime module

---

## 1. Enforcing Isolation Programmatically

The "no cross-module imports" rule is enforced automatically in CI using `import-linter`. If someone tries to import from one module inside another, the build fails immediately.

### Configuration

```ini
# .importlinter
[importlinter]
root_package = ai_flywheel

[importlinter:contract:1]
name = Independent Modules
type = independence
modules =
    ai_flywheel.modules.agent_runtime
    ai_flywheel.modules.data_knowledge
    ai_flywheel.modules.ml_evaluation
    ai_flywheel.modules.product_intelligence
    ai_flywheel.modules.experimentation
    ai_flywheel.modules.deployment
    ai_flywheel.modules.cross_venture

[importlinter:contract:2]
name = Modules Depend Only On Core
type = layers
layers =
    ai_flywheel.modules
    ai_flywheel.core
```

### What Gets Blocked

```python
# ❌ BLOCKED — Module B importing from Module A
# File: ai_flywheel/modules/experimentation/experiment_tracker.py
from ai_flywheel.modules.agent_runtime.llm_gateway import LLMGateway  # BUILD FAILURE

# ✓ ALLOWED — Module imports from Core
from ai_flywheel.core.config import settings
from ai_flywheel.core.events import get_event_bus
from ai_flywheel.core.contracts.events import AgentCompletedEvent
```

### CI Integration

```yaml
# In CI pipeline
- name: Check module isolation
  run: lint-imports
```

A violation produces a clear error:

```
BROKEN CONTRACT: Independent Modules
- ai_flywheel.modules.experimentation.experiment_tracker imports 
  ai_flywheel.modules.agent_runtime.llm_gateway
  (modules cannot import from each other)
```

---

## 2. Data Sharing Patterns

When Module B needs data that Module A produces, there are exactly two allowed patterns depending on the latency requirement:

### Pattern A: Asynchronous (Event-Driven) — 90% of Cases

Module A publishes an event when something changes. Module B subscribes and updates its own local read model.

```
Module A (Agent Runtime)                Module B (Experimentation)
         │                                        │
         │  agent completes task                  │
         │         │                              │
         │         ▼                              │
         │  publish("agent.completed", {          │
         │    agent_id: "...",                    │
         │    duration_ms: 340,                   │
         │    cost_usd: 0.03,         ──────────▶ │  subscribes to "agent.completed"
         │    output_quality: 0.92                │  updates its own experiment metrics table
         │  })                                    │
         │                                        │
```

**When to use:** Module B doesn't need the data instantly. It can tolerate milliseconds of delay. This covers most flows: feedback collection, cost tracking, metric updates, pattern extraction.

**Benefits:**
- Zero coupling — Module A doesn't know Module B exists
- Module A's schema can change internally without breaking Module B (only the event contract matters)
- Naturally scales to N subscribers without changing the publisher

### Pattern B: Synchronous (Data Gateway) — Rare Cases

If Module B needs a real-time answer from Module A (e.g., "what's the current cost budget for this venture?"), Module A exposes a **typed internal service method** in its public interface.

```python
# ai_flywheel/modules/experimentation/public.py (Module A's PUBLIC interface)
# This is the ONLY file other modules are allowed to know about

from ai_flywheel.core.contracts.schemas import CostBudgetStatus

async def get_cost_budget_status(venture_id: str) -> CostBudgetStatus:
    """Public interface — returns current cost budget status.
    
    This is the typed contract. Internal implementation can change freely.
    """
    ...
```

**Critical constraints:**
- The public interface returns **only** `core.contracts` schemas (never internal models)
- The public interface is a **thin file** — 3-5 methods max per module
- Even this pattern goes through a Core registry (not direct import):

```python
# How Module B accesses Module A's public interface:
from ai_flywheel.core.services import get_module_service

cost_service = get_module_service("experimentation")
status = await cost_service.get_cost_budget_status(venture_id)
```

**When to use:** Only when the event pattern introduces unacceptable latency AND the data is owned by another module. This should be rare (< 10% of inter-module interactions).

### Pattern C: Shared Read from Core Tables — Platform Data

Some data is genuinely global (ventures, users, platform config). This lives in Core tables that any module can query directly via `core.database`:

```python
# Any module can read Core tables
from ai_flywheel.core.database import get_session
from ai_flywheel.core.models import Venture

async with get_session(venture_id) as session:
    venture = await session.get(Venture, venture_id)
```

**This is only for Core-owned data** — never for module-owned tables.

---

## 3. Shared Contracts (core/contracts/)

All data exchanged between modules (via events, signals, or public interfaces) must use schemas defined in `core/contracts/`. This is the single source of truth for inter-module data shapes.

### Directory Structure

```
ai_flywheel/
├── core/
│   ├── contracts/                    # THE truth for inter-module schemas
│   │   ├── __init__.py
│   │   ├── events.py                # All event payload schemas
│   │   ├── commands.py              # Command schemas (request/response)
│   │   └── schemas.py              # Shared data transfer objects
│   ├── config.py
│   ├── database.py
│   └── ...
└── modules/
    ├── agent_runtime/               # Imports from core.contracts ✓
    └── experimentation/             # Imports from core.contracts ✓
```

### Event Contracts

```python
# core/contracts/events.py
"""Typed event definitions. Both publisher and subscriber import from here."""

from datetime import datetime
from pydantic import BaseModel


class AgentCompletedEvent(BaseModel):
    """Fired when an agent finishes executing a task."""
    agent_id: str
    venture_id: str
    task_id: str
    duration_ms: float
    cost_usd: float
    tokens_input: int
    tokens_output: int
    output_quality: float | None = None
    model_used: str
    timestamp: datetime


class ExperimentConcludedEvent(BaseModel):
    """Fired when an experiment reaches statistical significance."""
    experiment_id: str
    venture_id: str
    winner_variant: str
    confidence: float
    metric_name: str
    improvement_pct: float
    timestamp: datetime


class CostThresholdBreachedEvent(BaseModel):
    """Fired when a venture's cost exceeds its configured threshold."""
    venture_id: str
    current_spend_usd: float
    threshold_usd: float
    period: str  # "daily", "weekly", "monthly"
    top_contributor_module: str
    timestamp: datetime
```

### Why This Works

- **Type safety** — Both publisher and subscriber validate against the same Pydantic model
- **Zero coupling** — Neither module knows about the other; they only know about the contract
- **Versioning** — Schema changes are explicit (add optional fields for backward compat, new event types for breaking changes)
- **Discoverability** — All inter-module interfaces are in one place (`core/contracts/`)
- **Testing** — Modules can be tested in isolation using contract schemas as fixtures

---

## 4. LLM Gateway as a Core Service

The LLM Gateway is NOT a module that other modules import. It's a Core service — available everywhere, like the database or event bus.

### Why

If the LLM Gateway lived only inside `modules/agent_runtime/`, every other module that needs LLM access would need to import from `agent_runtime` — violating isolation. Instead:

```
ai_flywheel/
├── core/
│   ├── llm.py                       # Core LLM service interface
│   └── ...
└── modules/
    └── agent_runtime/
        └── llm_gateway.py           # Full implementation (routing, caching, fallbacks)
```

### The Interface

```python
# core/llm.py — Clean interface available to ALL modules
"""Core LLM service. Provides model access without coupling to agent_runtime internals."""

from ai_flywheel.core.contracts.schemas import LLMRequest, LLMResponse


async def generate(
    messages: list[dict[str, str]],
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    max_tokens: int | None = None,
    idempotency_key: str | None = None,
    venture_id: str | None = None,
    module_name: str = "unknown",
) -> LLMResponse:
    """Generate a completion via the LLM Gateway.
    
    Any module can call this. Cost tracking and tracing happen automatically.
    """
    ...
```

### Usage From Any Module

```python
# Inside modules/product_intelligence/market_intelligence.py
from ai_flywheel.core.llm import generate  # ✓ Core service, always allowed

async def analyze_market(query: str, venture_id: str) -> MarketReport:
    response = await generate(
        messages=[{"role": "user", "content": f"Analyze market: {query}"}],
        model="gpt-4o",
        venture_id=venture_id,
        module_name="market_intelligence",
    )
    ...
```

The full implementation (fallback chains, caching, provider management) lives in `modules/agent_runtime/llm_gateway.py`, but modules never touch it directly. They call the Core interface.

---

## 5. Module Ownership Boundaries

Each module owns specific database tables. No other module may query these tables directly.

| Module | Owns Tables | Others Access Via |
|--------|------------|-------------------|
| Agent Runtime | `agents`, `agent_executions`, `prompts`, `prompt_versions` | Events (`agent.completed`, `prompt.updated`) |
| Data & Knowledge | `datasets`, `documents`, `chunks`, `embeddings`, `knowledge_edges` | Events (`data.ingested`, `embedding.created`) |
| ML & Evaluation | `models`, `evaluations`, `features`, `training_runs` | Events (`model.trained`, `evaluation.completed`) |
| Product Intelligence | `market_signals`, `interviews`, `hypotheses`, `offers` | Events (`signal.detected`, `hypothesis.validated`) |
| Experimentation | `experiments`, `variants`, `experiment_results` | Events (`experiment.concluded`) |
| Deployment | `deployments`, `health_checks`, `incidents` | Events (`deployment.succeeded`, `incident.detected`) |
| Cross-Venture | `patterns`, `pattern_applications` | Events (`pattern.extracted`, `pattern.applied`) |

**Core owns:** `ventures`, `tasks`, `events`, `trace_spans`, `cost_records`, `users`

---

## 6. Service Extraction Path

Because modules communicate only via events and Core contracts, extracting a module into its own service requires:

1. **Replace in-process event bus with Redis Streams** (already planned for production)
2. **Deploy the module as a separate service** (its own container, its own DB connection)
3. **No code changes to other modules** — they still publish/subscribe to the same events

```
Before (monolith):
  [FastAPI Process]
    ├── Module A (in-process)
    ├── Module B (in-process)
    └── Event Bus (in-process)

After (extracted Module B):
  [FastAPI Process]
    ├── Module A (in-process)
    └── Event Bus → Redis Streams ──▶ [Module B Service]
                                          └── Own DB, own container
```

This is possible ONLY because:
- No direct imports between modules
- Events carry all necessary context (no implicit shared state)
- Contracts are defined in Core (both sides validate against same schemas)

---

## Summary

| Principle | Mechanism | Enforcement |
|-----------|-----------|-------------|
| No cross-module imports | `import-linter` in CI | Automated (build fails) |
| Inter-module data exchange | Events (async) or Core service registry (sync) | Architectural pattern |
| Typed contracts | `core/contracts/` with Pydantic schemas | Type checking + runtime validation |
| Table ownership | Each module owns specific tables | Convention + code review |
| LLM access | `core.llm` interface (not module import) | `import-linter` contract |
| Future extraction | Event bus as seam | No code changes needed to extract |

These rules ensure that at module 39, the platform is as composable as it was at module 1.
