# AI Flywheel — Documentation

**ai_flywheel** — *one flow to rule them all.*

AI Flywheel is a personal venture operating system built with Python + Next.js. It enables a solo founder to rapidly discover, validate, build, and scale multiple AI-native businesses by providing 39 shared modules across 8 systems as a reusable foundation, with domain-specific orchestrators composed on top for each venture.

The platform answers two questions traditional AI frameworks ignore: **"Should this venture exist?"** and **"What should the product experience be?"** — alongside the technical **"How do I build it with agents that continuously improve?"**

---

## Table of Contents

### Core Architecture
| Document | Description |
|----------|-------------|
| [vision.md](vision.md) | Vision, principles, and what makes this different |
| [architecture.md](architecture.md) | 8-system architecture, execution spine, interaction model |
| [modules/README.md](modules/README.md) | All 39 module specifications across 8 systems |

### Systems & Modules
| Document | Description |
|----------|-------------|
| [modules/system-1-core-kernel.md](modules/system-1-core-kernel.md) | Platform Core, Identity, Event Bus, Task Runtime, Traces, Artifacts |
| [modules/system-2-agent-runtime.md](modules/system-2-agent-runtime.md) | LLM Gateway, Prompts, Agents, Tools, Memory, Human Review, Policy |
| [modules/system-3-data-knowledge.md](modules/system-3-data-knowledge.md) | Ingestor, Data Quality, Embeddings, Knowledge Graph, Labeling, Privacy |
| [modules/system-4-ml-evaluation.md](modules/system-4-ml-evaluation.md) | Features, Models, Evaluation, Synthetic Data, Simulation |
| [modules/system-5-product-intelligence.md](modules/system-5-product-intelligence.md) | Market Intel, Customer Discovery, Thesis, Offer, Product UX, Workflows |
| [modules/system-6-experimentation.md](modules/system-6-experimentation.md) | Experiments, A/B Testing, Feedback, Metrics, Cost Optimization |
| [modules/system-7-deployment.md](modules/system-7-deployment.md) | Deployment, Reliability & Incidents |
| [modules/system-8-cross-venture.md](modules/system-8-cross-venture.md) | Pattern Library, Meta-Learning & Flywheel |

### Operations & Design
| Document | Description |
|----------|-------------|
| [ventures.md](ventures.md) | Venture system, MatchHire happy flow, venture economics |
| [validation-framework.md](validation-framework.md) | Evidence Ladder — 5 rungs from market structure to money signals |
| [validation-config.md](validation-config.md) | Override, skip, or customize validation — presets, budgets, parallel execution |
| [integrations.md](integrations.md) | Tool Forge scope, automation tiers, external service catalog |
| [interaction-model.md](interaction-model.md) | Multi-channel: Slack + Web App + CLI, Conversation Router |
| [feature-loop.md](feature-loop.md) | Inner development cycle — signal → build → ship → learn within a running venture |
| [feedback-loops.md](feedback-loops.md) | 6 loop types, cross-system flows, meta-learning |
| [state-management.md](state-management.md) | Versioning, snapshots, backup, recovery — revert anything |

### Implementation
| Document | Description |
|----------|-------------|
| [tech-stack.md](tech-stack.md) | Python + Next.js + PostgreSQL + Redis stack choices |
| [package-structure.md](package-structure.md) | Directory layout, BaseModule class, channel architecture |
| [module-isolation.md](module-isolation.md) | Module independence rules, import-linter enforcement, data sharing patterns |
| [database-schema.md](database-schema.md) | 30+ tables across all 8 systems |
| [build-phases.md](build-phases.md) | 6-phase roadmap, execution spine first |
| [temporal-patterns.md](temporal-patterns.md) | Temporal.io patterns, determinism rules, frontend integration |
| [infrastructure.md](infrastructure.md) | Hosting, compute, cost breakdown, scale-to-zero philosophy |
| [high-availability.md](high-availability.md) | HA architecture, failure scenarios, scaling model |
| [auth-rbac.md](auth-rbac.md) | Clerk + Neon RLS via Custom JWTs, per-venture roles, permissions |
