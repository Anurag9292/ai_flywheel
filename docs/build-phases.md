# Build Phases

## Overview

AI Flywheel is built in seven phases (Phase 0–6) over 13+ weeks. Each phase delivers a working increment — you can use the platform after every phase, with expanding capabilities. The ordering is driven by a single principle: **the Execution Spine comes first**. Phase 0 proves the bare metal works (Temporal workflows survive restarts, traces capture everything, cost is tracked). Phase 1 proves a real agent can run through that spine. Nothing else proceeds until these foundations are proven solid.

---

## Current Status (as of 2026-06-06)

| Phase | Status | Completion | Key Unlock |
|-------|--------|-----------|------------|
| **0: Bare Metal** | ✅ Complete | ~100% | Execution spine proven |
| **1: First Agent** | ✅ Complete | ~90% | Agent runs real work through spine |
| **2: Data + Market** | ⚠️ Mostly done | ~60% | Market research works, data pipeline untested |
| **3: Product + Offer** | ⚠️ Mostly done | ~50% | Offer works, no integrations/evidence ladder |
| **4: ML + Advanced** | ⚠️ Services exist | ~30% | All services built, none operational E2E |
| **5: Production** | ❌ Not done | ~15% | Services exist, all simulated |
| **6: Flywheel** | ⚠️ Partial | ~40% | Visual builder + CLI + Slack built |

### What Works End-to-End Today
- Venture Lifecycle Workflow: Thesis → Discovery → Market → Offer → Blueprint → Agents (via Temporal)
- Agent execution with LLM (GPT-4o-mini), cost tracking, tracing
- Customer Discovery: interview guide generation, transcript analysis
- Market Intelligence: signal analysis, opportunity scoring (LLM-powered)
- Offer Design: ICP + positioning auto-generated on creation
- Workflow Blueprint: LLM-generated graph compilation
- Visual Workflow Builder (React Flow)
- CLI with real service calls
- Slack Bolt integration (structure in place)
- Dark cosmic UI with 12 pages + reusable component library

### Critical Gaps
1. **Outputs don't feed forward** — agent results disappear, no unified venture context
2. **Memory Engine not wired** — agents don't remember previous interactions
3. **Data pipeline untested** — Ingestor, Embeddings, Knowledge Graph never exercised E2E
4. **No real external integrations** — Tool Forge has no connected tools
5. **No Evidence Ladder enforcement** — thesis tracks evidence but doesn't gate the lifecycle
6. **No cross-venture dashboard** — can't see flywheel effect
7. **Feedback → Experiment → Pattern loop not closed in practice**

---

## Phase 0: Bare Metal (Week 1-2) — ✅ COMPLETE

### Goal

Prove the execution spine works. A dummy workflow can execute across multiple steps, survive a restart, trace every action, and record cost.

### What Gets Built (5 modules)

| Source System | Module | Purpose |
|---------------|--------|---------|
| System 1: Platform Core | **Platform Core (#1)** | Config, secrets, settings |
| System 1: Platform Core | **Event Bus (#3)** | Pub/sub with persistence |
| System 1: Platform Core | **Task Runtime (#4)** | Temporal-based workflow engine |
| System 1: Platform Core | **Trace & Observability (#5)** | Distributed tracing, error analysis |
| System 2: Agent Intelligence | **LLM Gateway (#7)** | Multi-provider with cost tracking |

### Success Criteria — ALL MET ✅

- [x] A multi-step workflow executes via Temporal
- [x] Workflow survives container restart (state hydration works)
- [x] Every step is traced with timing, cost, and inputs/outputs
- [x] LLM call goes through gateway, cost is recorded
- [x] RLS prevents cross-venture data access at the DB level

### Deliverable

The execution spine is proven solid. ✅

---

## Phase 1: First Agent (Week 3-4) — ✅ COMPLETE

### Goal

A real agent runs a real task through the spine.

### What Gets Built (5 modules)

| Source System | Module | Purpose |
|---------------|--------|---------|
| System 1: Platform Core | **Identity & Tenancy (#2)** | Venture scoping, RLS enforcement |
| System 2: Agent Intelligence | **Agent Factory & Orchestration (#9)** | Config-driven agents, multi-agent patterns as Temporal workflows |
| System 2: Agent Intelligence | **Prompt Studio (#8)** | Template management, versioning, no UI |
| System 5: Venture Validation | **Customer Discovery Engine (#26)** | First real use case |
| System 6: Learning & Optimization | **Cost Optimizer (#35)** | Budget tracking and alerts |

### Success Criteria

- [x] Create an agent via config, execute it against a task
- [x] Agent execution traces through the full spine (event → task → trace → metric → cost)
- [x] Customer Discovery Engine generates interview guide from domain input
- [x] Multi-step workflow pauses for approval, resumes when approved
- [x] Cost tracked per agent per execution

### Known Issues
- Old Temporal workflows (created before signal handler fix) cannot replay — must be terminated and recreated

### Deliverable

A real agent does real work, fully traced and costed. ✅

---

## Phase 2: Data Foundation + Market Intelligence (Week 5-6) — ⚠️ 60% COMPLETE

### Goal

Build the research and data layer. The platform can discover markets, ingest data, validate quality, generate embeddings for RAG, and construct knowledge graphs.

### What Gets Built (7 modules)

| Source System | Module | Purpose | Status |
|---------------|--------|---------|--------|
| System 1: Platform Core | **Identity & Tenancy** | Multi-tenant isolation | ✅ Done |
| System 3: Data & Knowledge | **Universal Ingestor** | Ingest data from any source | ⚠️ Service exists, not tested E2E |
| System 3: Data & Knowledge | **Data Quality Engine** | Validate, profile, score | ⚠️ Service exists, not tested E2E |
| System 3: Data & Knowledge | **Embedding Engine** | Generate/manage vectors | ⚠️ Service exists, not tested E2E |
| System 3: Data & Knowledge | **Knowledge Graph Builder** | Extract entities/relationships | ⚠️ Service exists, not tested E2E |
| System 5: Venture Validation | **Market & Signal Intelligence** | Monitor markets, competitors | ✅ Working with LLM |
| System 5: Venture Validation | **Venture Thesis Engine** | Formalize/track hypotheses | ✅ Working with evidence + kill signals |

### Success Criteria

- [x] Market & Signal Intelligence identifies relevant trends for a given venture domain
- [x] Venture Thesis Engine tracks hypotheses through evidence ladder rungs
- [ ] **Universal Ingestor successfully ingests CSV, JSON, and PDF formats**
- [ ] **Data Quality Engine produces quality report with actionable findings**
- [ ] **Embedding Engine generates vectors and similarity search returns relevant results**
- [ ] **Knowledge Graph Builder extracts entities and relationships from text**
- [x] Identity & Tenancy isolates data between ventures
- [ ] All modules publish events and track costs through Task Runtime
- [ ] **End-to-end: market signal → hypothesis → data ingestion → quality check → embed → graph**

### Remaining Action Items

| # | Action | Priority | Effort |
|---|--------|----------|--------|
| 2.1 | Test Universal Ingestor with real CSV/JSON/PDF files | High | Small |
| 2.2 | Test Embedding Engine — create collection, embed docs, run similarity search | High | Small |
| 2.3 | Test Knowledge Graph — ingest text, verify entity/relationship extraction | High | Small |
| 2.4 | Test Data Quality Engine — feed bad data, verify quality report | Medium | Small |
| 2.5 | Wire end-to-end pipeline: ingest → quality → embed → graph (Temporal workflow) | High | Medium |
| 2.6 | Ensure all data modules emit events + track cost | Medium | Small |
| 2.7 | Add frontend pages for Ingestor, Embeddings, Knowledge Graph | Medium | Medium |

---

## Phase 3: Product Design + Offer (Week 7-8) — ⚠️ 50% COMPLETE

### Goal

Complete the validation pipeline. Design offers, create landing pages, run campaigns, collect behavioral signals, test pricing. The Evidence Ladder is fully operational.

### What Gets Built (6 modules)

| Source System | Module | Purpose | Status |
|---------------|--------|---------|--------|
| System 5: Venture Validation | **Offer Design Engine** | ICP, positioning, pricing, copy | ⚠️ ICP + positioning work; pricing + copy not auto-triggered |
| System 5: Venture Validation | **Product Experience Engine** | Screen architecture, AI patterns | ⚠️ Service exists, no UI, not tested |
| System 5: Venture Validation | **Workflow Blueprint Engine** | Map user flows, compile to agents | ✅ Working in lifecycle |
| System 2: Agent Intelligence | **Tool Forge** | Create/manage tools for agents | ⚠️ Service exists, no real integrations |
| System 6: Learning & Optimization | **A/B Test & Optimization Engine** | Statistical A/B testing | ⚠️ Service exists, not tested E2E |
| System 6: Learning & Optimization | **Feedback Collector** | Collect human/automated feedback | ⚠️ Service exists, not wired |

### Success Criteria

- [x] Offer Design Engine produces ICP and positioning from market research input
- [ ] **Offer Design produces complete package: ICP + positioning + pricing + landing copy**
- [ ] **Product Experience Engine generates interaction specifications for AI agent behaviors**
- [x] Workflow Blueprint Engine compiles user flows into executable agent orchestration
- [ ] **Tool Forge connects to at least 4 external integrations (ad platform, payment, hosting, email)**
- [ ] **A/B Test Engine reaches statistical significance and declares winner**
- [ ] **Feedback Collector captures explicit, implicit, and automated signals**
- [ ] **Evidence Ladder is fully operational: validate venture from research through signal collection**
- [ ] **End-to-end: offer → landing page → campaign → signals → hypothesis validated/invalidated**

### Remaining Action Items

| # | Action | Priority | Effort |
|---|--------|----------|--------|
| 3.1 | Add pricing + landing copy generation to lifecycle workflow offer stage | High | Small |
| 3.2 | Build Product Experience page (feature prioritization, AI patterns, screens) | Medium | Medium |
| 3.3 | Connect Tool Forge to real external APIs (start with 2: email via SendGrid, payments via Stripe) | High | Medium |
| 3.4 | Wire Feedback Collector — after agent execution, prompt for rating → store → route to experiment | High | Medium |
| 3.5 | Test A/B Engine end-to-end: create experiment, record observations, reach significance | High | Small |
| 3.6 | Build Evidence Ladder enforcement: gate lifecycle stages based on evidence score | High | Medium |
| 3.7 | End-to-end: lifecycle generates landing page copy → deploy to Vercel → collect conversion signals | Low | Large |

---

## Phase 4: ML + Advanced Agents (Week 9-10) — ⚠️ 30% COMPLETE

### Goal

Move beyond LLM prompts to real ML models, human review workflows, safety/compliance, and labeled datasets for rigorous evaluation.

### What Gets Built (8 modules)

| Source System | Module | Purpose | Status |
|---------------|--------|---------|--------|
| System 2: Agent Intelligence | **Memory Engine** | Short/long-term memory for continuity | ⚠️ Service exists (488 lines), NOT wired to agent execution |
| System 2: Agent Intelligence | **Human Review Engine** | Configurable HITL workflows | ⚠️ Service exists, approval flow works but routing not tested |
| System 2: Agent Intelligence | **Policy Engine** | Safety, compliance, governance | ⚠️ Service exists (558 lines), not tested in practice |
| System 4: Model & ML | **Feature Factory** | Transform raw data to ML features | ⚠️ Service exists, not tested |
| System 4: Model & ML | **Model Forge** | Train/manage ML models | ⚠️ Service exists (simulated baseline, no real ML) |
| System 4: Model & ML | **Evaluation Framework** | Comprehensive model evaluation | ⚠️ Service exists, not tested |
| System 3: Data & Knowledge | **Labeling & Ground Truth** | Create/manage labeled datasets | ⚠️ Service exists, not tested |
| System 3: Data & Knowledge | **Privacy & PII Engine** | Detect, mask, manage PII | ⚠️ Service exists, not tested |

### Success Criteria

- [ ] **Agent remembers context from previous interactions (working + episodic + semantic memory)**
- [ ] **Human Review routes decisions correctly (auto-approve, queue, escalate) based on confidence**
- [ ] **Policy Engine enforces safety rules and produces audit trail**
- [ ] **Feature Factory transforms raw data into ML-ready features declaratively**
- [ ] **Model Forge trains a classifier on venture data with proper evaluation**
- [ ] **Evaluation Framework produces multi-dimensional report (accuracy, fairness, cost, latency)**
- [ ] **Labeling Engine manages gold datasets with inter-annotator agreement tracking**
- [ ] **Privacy Engine detects and masks PII in ingested documents**
- [ ] **End-to-end: data → features → train → evaluate → review → approve → deploy**

### Remaining Action Items

| # | Action | Priority | Effort |
|---|--------|----------|--------|
| 4.1 | **Wire Memory Engine to agent execution** — agents auto-store/retrieve context between runs | Critical | Medium |
| 4.2 | Test Human Review routing: set confidence threshold → low-confidence outputs go to queue | High | Small |
| 4.3 | Test Policy Engine: create policy rules → execute agent → verify rule enforcement | High | Small |
| 4.4 | Test Privacy Engine: feed text with PII → verify detection + masking | Medium | Small |
| 4.5 | Test Labeling Engine: create task, add items, label, compute agreement | Medium | Small |
| 4.6 | Test Feature Factory: define transforms, compute features on data | Medium | Small |
| 4.7 | Replace simulated Model Forge with real sklearn training (basic classifier) | Medium | Medium |
| 4.8 | Test Evaluation Framework: create suite, run eval, compare runs | Medium | Small |
| 4.9 | Wire end-to-end: ingest data → extract features → train model → evaluate → human review | Low | Large |
| 4.10 | Human review decisions become training labels (close the loop) | Medium | Medium |

---

## Phase 5: Production + Scale (Week 11-12) — ❌ 15% COMPLETE

### Goal

Production-grade deployment, reliability, simulation testing. Can ship real ventures to real customers with confidence.

### What Gets Built (4 modules)

| Source System | Module | Purpose | Status |
|---------------|--------|---------|--------|
| System 4: Model & ML | **Synthetic Data Generator** | Generate training data | ⚠️ Service exists, not tested |
| System 4: Model & ML | **Simulation Engine** | Test agent networks vs scenarios | ⚠️ Service exists, not tested |
| System 7: Production & Reliability | **Deployment Engine** | Package and deploy agents | ⚠️ Service exists (simulated URLs) |
| System 7: Production & Reliability | **Reliability & Incident Engine** | Monitor, detect, auto-heal | ⚠️ Service exists, not tested |

### Success Criteria

- [ ] **Synthetic Data Generator produces statistically valid data**
- [ ] **Simulation Engine tests agent network against 100+ synthetic scenarios before deploy**
- [ ] **Deployment Engine packages and deploys agent network as production service**
- [ ] **Canary deployment detects regression and auto-rolls back**
- [ ] **Reliability Engine detects anomalies and auto-scales or circuit-breaks**
- [ ] **Incident Engine captures resolution and applies to future incidents**
- [ ] **End-to-end: simulate → deploy canary → monitor → promote or rollback**

### Remaining Action Items

| # | Action | Priority | Effort |
|---|--------|----------|--------|
| 5.1 | Test Synthetic Data Generator: generate data from schema, validate statistical properties | Medium | Small |
| 5.2 | Test Simulation Engine: define scenarios, run agent network against them | Medium | Medium |
| 5.3 | Replace simulated Deployment Engine with real Docker container deployment | High | Large |
| 5.4 | Implement canary deployment logic: route 10% traffic, compare metrics, promote/rollback | Medium | Large |
| 5.5 | Implement real health monitoring with anomaly detection | Medium | Medium |
| 5.6 | Test incident capture and resolution replay | Low | Medium |
| 5.7 | Docker Compose production deployment (already built — needs testing on real VPS) | High | Small |

---

## Phase 6: Flywheel + Visual Builder (Week 13+) — ⚠️ 40% COMPLETE

### Goal

Complete platform with cross-venture learning, visual tools, multi-channel interaction, and the meta-learning layer.

### What Gets Built

| Source System | Component | Purpose | Status |
|---------------|-----------|---------|--------|
| System 8: Meta-Learning | **Pattern & Template Library** | Reusable patterns across ventures | ⚠️ Service exists, Learning Loop built, not auto-triggered |
| System 8: Meta-Learning | **Meta-Learning & Flywheel Engine** | System-wide intelligence | ⚠️ Service exists, velocity tracking built, no real data |
| Platform UI | **Visual Graph Editor** | React Flow drag-and-drop designer | ✅ Built |
| Platform UI | **Venture Templates** | Pre-built configs for common types | ❌ Not built |
| Platform UI | **Cross-Venture Dashboard** | Unified view + comparative metrics | ❌ Not built |
| Platform UI | **Venture Command Center** | Unified per-venture view with "next action" | ❌ Not built |
| Integration | **Slack Integration** | Bot, notifications, approvals | ⚠️ Structure built, commands are stubs |
| Integration | **CLI Tool** | Command-line interface | ✅ Real service calls |

### Success Criteria

- [x] User can design multi-agent system visually by dragging nodes and connecting edges
- [ ] **Graph editor generates valid config that actually executes as a Temporal workflow**
- [ ] **Venture template creates working venture in under 5 minutes**
- [ ] **Pattern Library identifies and suggests applicable cross-venture patterns automatically**
- [ ] **Meta-Learning Engine measures flywheel velocity and identifies bottlenecks**
- [ ] **Cross-venture dashboard shows comparative metrics with improvement trends**
- [x] Slack bot handles basic commands (structure in place)
- [x] CLI provides full platform access for power users
- [ ] **Flywheel metrics clearly show each successive venture getting faster/cheaper**
- [ ] **Venture Command Center: unified view with "what to do next" AI recommendations**

### Remaining Action Items

| # | Action | Priority | Effort |
|---|--------|----------|--------|
| 6.1 | **Build Venture Command Center** — single unified page per venture showing all intelligence + AI "next action" recommendation | Critical | Large |
| 6.2 | **Wire graph editor to execution** — "Deploy" button compiles graph → creates Temporal workflow → runs | High | Medium |
| 6.3 | **Build venture templates** — SaaS, marketplace, API product, agency presets | Medium | Medium |
| 6.4 | **Auto-trigger Learning Loop** — when experiment concludes, auto-extract pattern without manual call | High | Small |
| 6.5 | **Pattern recommendations at lifecycle start** — check library before starting new venture | Medium | Small |
| 6.6 | **Cross-venture dashboard** — compare ventures side-by-side, show velocity trends | Medium | Medium |
| 6.7 | **Wire Slack commands to real DB** — `/flywheel ventures` queries actual ventures, costs, etc. | Medium | Small |
| 6.8 | **Flywheel velocity display** — show in UI that venture N is X% faster than venture N-1 | Medium | Small |
| 6.9 | **Store + display agent outputs** as venture intelligence (persist execution results) | Critical | Medium |
| 6.10 | **Memory-backed agents** — agent execution reads/writes to Memory Engine for continuity | Critical | Medium |

---

## Priority Order — What To Build Next

Based on impact and the "disconnected" problem:

### Tier 1: Make It Feel Like One Product (Critical)

| # | Action | From Phase | Why |
|---|--------|-----------|-----|
| 6.1 | Venture Command Center | Phase 6 | Single unified view ties everything together |
| 6.9 | Persist agent outputs as venture intelligence | Phase 6 | Outputs feed forward instead of disappearing |
| 4.1 | Wire Memory Engine to agent execution | Phase 4 | Agents remember context between runs |
| 6.10 | Memory-backed agents | Phase 6 | Continuity across the entire venture |
| 3.4 | Wire Feedback Collector | Phase 3 | Rate outputs → feeds experiments → improves system |

### Tier 2: Complete the Core Pipeline (High)

| # | Action | From Phase | Why |
|---|--------|-----------|-----|
| 2.5 | Wire data pipeline end-to-end | Phase 2 | Ingest → quality → embed → graph as one flow |
| 3.1 | Add pricing + copy to lifecycle offer stage | Phase 3 | Complete offer generation |
| 3.3 | Connect Tool Forge to real APIs | Phase 3 | Agents can actually DO things externally |
| 3.6 | Evidence Ladder enforcement | Phase 3 | Kill gates with teeth |
| 6.2 | Graph editor → execution | Phase 6 | Visual builder actually deploys workflows |
| 6.4 | Auto-trigger Learning Loop | Phase 6 | Flywheel spins automatically |

### Tier 3: Polish & Production (Medium)

| # | Action | From Phase | Why |
|---|--------|-----------|-----|
| 5.7 | Test Docker Compose on real VPS | Phase 5 | Actually deployable |
| 6.3 | Venture templates | Phase 6 | Fast venture creation |
| 6.6 | Cross-venture dashboard | Phase 6 | Visualize the flywheel |
| 3.2 | Product Experience page | Phase 3 | Complete the UI coverage |
| 6.7 | Wire Slack to real DB | Phase 6 | Slack becomes actually useful |

### Tier 4: Advanced / Can Wait (Lower)

| # | Action | From Phase | Why |
|---|--------|-----------|-----|
| 4.7 | Real ML training | Phase 4 | Nice-to-have, simulated works for now |
| 5.3-5.6 | Real deployment engine | Phase 5 | Complex, Docker Compose sufficient initially |
| 2.7 | Data module frontend pages | Phase 2 | Backend works, UI is nice-to-have |
| 4.9 | Full ML pipeline E2E | Phase 4 | Advanced, depends on real ML |

---

## Dependency Graph

```
Phase 0 (Bare Metal — Execution Spine) ✅
    │
    └── Phase 1 (First Agent) ✅
            │
            ├── Phase 2 (Data + Market Intelligence) ⚠️ 60%
            │       │
            │       └── Phase 3 (Product Design + Offer) ⚠️ 50%
            │               │
            │               └── Phase 4 (ML + Advanced Agents) ⚠️ 30%
            │                       │
            │                       └── Phase 5 (Production + Scale) ❌ 15%
            │                               │
            │                               └── Phase 6 (Flywheel + Visual Builder) ⚠️ 40%
            │
            └── [Each phase depends on all previous phases]
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| LLM API instability | LLM Gateway with fallback providers from Phase 0 ✅ |
| Cost overrun during development | Cost tracking active from Phase 0 ✅ |
| Workflow state loss | Temporal.io guarantees durable execution ✅ |
| Module coupling | Event bus enforces loose coupling ✅ |
| Scope creep per module | Each module has clear contract ✅ |
| **Disconnected user experience** | **Build Venture Command Center (Tier 1 priority)** |
| **Agent outputs lost** | **Persist execution results + venture intelligence store** |
| **No compound learning** | **Wire Learning Loop auto-trigger + Pattern recommendations** |
| Over-engineering early | Config-driven agents mean behavior changes without code ✅ |
| Integration fragility | Tool Forge abstracts external APIs ✅ |
