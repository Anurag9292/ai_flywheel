# Layer 2: Venture System

## What is a Venture?

A **venture** is a namespace for a specific AI-native startup you're building on the platform. It represents a complete, self-contained business unit with its own domain logic, agent network, data assets, and flywheel dynamics.

Think of the AI Flywheel platform as your startup studio infrastructure. Each venture is one startup within that studio — isolated enough to have its own identity and logic, but sharing the common platform capabilities (LLM Gateway, Workflow Engine, Experiment Tracker, etc.) that would be prohibitively expensive to build from scratch each time.

A venture encapsulates:
- A specific **market problem** you're solving
- The **agent network** that solves it
- The **domain data** that makes your solution defensible
- The **flywheel** that compounds improvement over time

---

## Venture Lifecycle

Every venture progresses through a defined lifecycle. Not every venture makes it to the end — and that's by design. The platform helps you fail fast and cheap on bad ideas, and accelerate good ones.

```
Ideation → Discovery → Data Foundation → Intelligence → Agent Network → Optimization → Production → Scale
```

### 1. Ideation
- Market Scanner surfaces opportunities
- You define the problem space and hypothesize a solution
- Quick viability check: Is there data? Is there a wedge? Is there a flywheel?

### 2. Discovery
- Dataset Scout searches for available data sources
- Competitive landscape analysis
- Define minimum viable agent network
- Validate that AI can meaningfully improve on status quo

### 3. Data Foundation
- Ingest initial datasets (public, purchased, or generated)
- Build domain-specific embeddings
- Establish data pipelines for ongoing collection
- Define quality metrics for your data

### 4. Intelligence
- Model Forge trains or fine-tunes domain models
- Evaluation Framework benchmarks against baselines
- Prompt engineering for domain-specific tasks
- Build the knowledge base that agents will draw from

### 5. Agent Network
- Agent Factory creates specialist agents
- Define coordination protocol between agents
- Wire up the manager agent
- End-to-end workflow testing

### 6. Optimization
- Bandit Optimizer tunes routing and parameters
- Cost Optimizer finds quality/cost sweet spots
- A/B test different agent configurations
- Error Analyzer identifies failure patterns

### 7. Production
- Deploy to real users
- Monitor quality, latency, cost
- Collect feedback and usage data
- Flywheel begins spinning

### 8. Scale
- Data compounds, models improve
- Add more agent capabilities
- Expand to adjacent use cases
- Cross-venture transfer of validated patterns

---

## Venture Components

### Venture Definition

Every venture starts with a structured definition:

```yaml
venture:
  name: "talent-ai"
  domain: "HR/Recruiting"
  
  value_proposition: >
    Reduce time-to-hire by 60% while improving candidate quality
    through AI-powered sourcing, screening, and coordination.
  
  success_metrics:
    primary: time_to_hire_days
    secondary:
      - candidate_quality_score
      - hiring_manager_satisfaction
      - cost_per_hire
    north_star: successful_hires_per_month
  
  customer_model:
    segment: "Mid-market companies (100-2000 employees)"
    buyer: "VP of People / Head of Talent"
    user: "Recruiters, Hiring Managers"
    pain: "Drowning in applicants, slow process, losing good candidates"
    willingness_to_pay: "$500-2000/month per recruiter seat"
  
  data_moat:
    - Hiring outcome data (what actually predicts success)
    - Company culture embeddings (match beyond keywords)
    - Candidate interaction patterns (engagement signals)
```

### Agent Network

Each venture has a **manager agent** that orchestrates a team of **specialist agents**:

```
                    ┌─────────────────────┐
                    │   Manager Agent     │
                    │  (Orchestrator)     │
                    └─────────┬───────────┘
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
    ┌───────▼───────┐ ┌──────▼──────┐ ┌───────▼───────┐
    │  Specialist   │ │ Specialist  │ │  Specialist   │
    │   Agent A     │ │  Agent B    │ │   Agent C     │
    └───────────────┘ └─────────────┘ └───────────────┘
```

**Coordination Protocol:**
- Manager receives incoming tasks/events
- Manager decomposes into sub-tasks
- Manager routes to appropriate specialists
- Specialists execute and return results
- Manager aggregates, validates, and responds
- All interactions logged to shared memory

**Shared Memory:**
- Conversation context persists across agent interactions
- Learning from past decisions informs future routing
- Cross-agent knowledge (Agent A's output enriches Agent B's context)
- Stored in PostgreSQL + pgvector for semantic retrieval

### Domain Workflows

Each venture defines workflows specific to its domain, built on the shared Workflow Engine:

```python
# Example: HR venture workflow
workflow = VentureWorkflow(
    name="new_job_to_hire",
    venture="talent-ai",
    steps=[
        Step("parse_job", agent="job_parser"),
        Step("source_candidates", agent="candidate_sourcer"),
        Step("screen_resumes", agent="resume_screener", parallel=True),
        Step("rank_candidates", agent="candidate_ranker"),
        Step("schedule_interviews", agent="interview_scheduler"),
        Step("draft_offer", agent="offer_drafter", condition="candidate_accepted"),
    ],
    triggers=["job_posted", "job_updated"],
    sla={"total_time": "48h", "first_candidates": "4h"},
)
```

### Domain Knowledge Base

Each venture accumulates a proprietary knowledge base:

- **Industry Data**: Market-specific information, benchmarks, standards
- **Customer Data**: Interactions, preferences, feedback, outcomes
- **Learning Repository**: What worked, what didn't, why — indexed for retrieval

The knowledge base is the venture's moat. As it grows, the agents get better, which attracts more usage, which generates more data.

### Venture Flywheel

Every venture has its own flywheel:

```
    ┌──────────┐
    │  Usage   │──────────────────┐
    └────▲─────┘                  │
         │                        ▼
    ┌────┴─────┐           ┌──────────┐
    │  More    │           │   Data   │
    │  Usage   │           │ Generated│
    └────▲─────┘           └────┬─────┘
         │                      │
    ┌────┴─────────┐     ┌─────▼──────┐
    │ Better       │◄────│Improvement │
    │ Performance  │     │ (Training) │
    └──────────────┘     └────────────┘
```

The platform instruments every venture flywheel automatically:
- Track data volume growth
- Measure model/agent performance over time
- Identify flywheel stalls (where is growth plateauing?)
- Suggest interventions to restart momentum

---

## Example Ventures

### 1. HR/Recruiting Startup ("TalentAI")

**Manager:** Recruiting Orchestrator
- Coordinates the full hiring pipeline
- Balances speed vs. quality based on role urgency
- Learns hiring manager preferences over time

**Specialist Agents:**

| Agent | Role | Key Capability |
|-------|------|----------------|
| Job Parser | Extract structured requirements from job descriptions | NER, classification, salary benchmarking |
| Candidate Sourcer | Find candidates from multiple channels | Web scraping, API integrations, boolean search generation |
| Resume Screener | Score and rank candidates against requirements | Embedding similarity, skill extraction, bias detection |
| Interview Scheduler | Coordinate availability across parties | Calendar APIs, timezone handling, preference learning |
| Offer Drafter | Generate competitive offer packages | Market data, candidate history, negotiation modeling |

**Workflows:**
```
New job posted → parse requirements → source candidates → screen →
rank → present shortlist → schedule interviews → collect feedback →
draft offer → track outcome
```

**Data Assets:**
- Job descriptions (structured + raw)
- Resumes and candidate profiles
- LinkedIn/GitHub/portfolio data
- Interview transcripts and feedback
- Hiring outcomes (accepted, rejected, tenure, performance)
- Time-to-hire and funnel conversion metrics

**Flywheel:** More hires completed → better understanding of what predicts success → better screening → faster hires → more companies adopt → more hires completed

---

### 2. Sales Lead Conversion ("ConvertAI")

**Manager:** Lead Conversion Orchestrator
- Manages leads through the full conversion pipeline
- Dynamically adjusts strategy based on lead behavior
- Optimizes for conversion rate and deal size

**Specialist Agents:**

| Agent | Role | Key Capability |
|-------|------|----------------|
| Lead Enricher | Augment raw leads with company/person data | API enrichment, web scraping, data fusion |
| Lead Scorer | Predict conversion probability and deal size | ML scoring, behavioral signals, firmographics |
| Copywriter | Generate personalized outreach messages | Tone matching, personalization, A/B variants |
| Sequencer | Orchestrate multi-touch outreach campaigns | Timing optimization, channel selection, cadence |
| Response Analyzer | Interpret replies and determine intent | Sentiment, objection detection, buying signals |
| Escalator | Route hot leads to humans at the right moment | Threshold detection, context packaging, handoff |

**Workflows:**
```
New lead → enrich with company/person data → score and prioritize →
route (auto vs. human) → generate personalized outreach → send sequence →
analyze responses → adjust strategy → follow-up → escalate or close
```

**Data Assets:**
- CRM records and deal history
- Email threads and response patterns
- Company firmographic data
- Outreach copy and performance metrics
- Response rates by segment, channel, timing
- Conversion outcomes and revenue attribution

**Flywheel:** More outreach → more response data → better personalization and timing → higher conversion → more revenue → more leads fed in → more outreach

---

### 3. Knowledge Management ("KnowAI")

**Manager:** Knowledge Orchestrator
- Ensures organizational knowledge is captured, organized, and accessible
- Identifies knowledge gaps and stale information
- Learns what knowledge is most valuable to whom

**Specialist Agents:**

| Agent | Role | Key Capability |
|-------|------|----------------|
| Document Ingestor | Process documents from any source/format | PDF parsing, OCR, chunking, metadata extraction |
| Taxonomy Builder | Create and maintain knowledge classification | Clustering, ontology, auto-tagging, hierarchy |
| Search Agent | Find relevant knowledge for user queries | Semantic search, re-ranking, context assembly |
| Synthesis Agent | Combine multiple sources into coherent answers | RAG, summarization, citation, conflict resolution |
| Gap Identifier | Detect missing or outdated knowledge | Coverage analysis, staleness detection, usage gaps |

**Workflows:**
```
New document → ingest and parse → classify in taxonomy → generate embeddings →
index for retrieval → surface to relevant users → track utility →
identify gaps → request new content
```

**Data Assets:**
- Internal documents (policies, procedures, guides)
- Wiki pages and knowledge base articles
- Conversation logs (Slack, meetings, support tickets)
- Search queries and click-through patterns
- Usage analytics (what's read, what's useful, what's stale)
- Expert identification (who knows what)

**Flywheel:** More documents ingested → better search and synthesis → more usage → more signal on what's valuable → better organization and surfacing → more adoption → more documents contributed

---

## Cross-Venture Patterns

Certain patterns prove valuable across multiple ventures. The platform identifies and extracts these:

### Patterns That Transfer

| Pattern | HR Venture | Sales Venture | Knowledge Venture |
|---------|-----------|---------------|-------------------|
| Onboarding Flow | New recruiter setup | New sales rep setup | New team member setup |
| Data Ingestion | Resume parsing | Lead import | Document processing |
| Quality Scoring | Candidate fit score | Lead quality score | Content relevance score |
| Customer Communication | Candidate outreach | Prospect outreach | Knowledge notifications |
| Feedback Collection | Hiring manager feedback | Deal win/loss analysis | Content usefulness ratings |
| Escalation Logic | Complex role routing | Hot lead handoff | Expert routing |

### How Transfer Works

1. **Pattern Recognition**: Platform identifies structural similarities across ventures
2. **Abstraction**: Common logic is extracted into a reusable pattern
3. **Suggestion**: When a new venture is created, relevant patterns are suggested
4. **Customization**: Patterns are adapted to the new domain's specifics
5. **Validation**: Performance tracked to confirm pattern works in new context
6. **Library Update**: Success/failure informs future suggestions

---

## Venture Templates

Pre-built starting configurations that accelerate new venture creation:

### Available Templates

**B2B SaaS Template**
- Pre-configured for: lead gen, onboarding, support, expansion
- Includes: CRM integration, email agents, usage tracking
- Best for: Sales-led or product-led growth businesses

**Marketplace Template**
- Pre-configured for: supply/demand matching, trust/safety, pricing
- Includes: Matching algorithms, review systems, dynamic pricing agents
- Best for: Two-sided marketplace businesses

**Content/Media Template**
- Pre-configured for: content creation, distribution, personalization
- Includes: Content generators, audience segmentation, engagement tracking
- Best for: Media companies, content platforms, newsletters

**Professional Services Template**
- Pre-configured for: client intake, project management, delivery, billing
- Includes: Scope agents, timeline estimators, quality checkers
- Best for: Consulting, agencies, freelance platforms

### Using Templates

```python
from flywheel.ventures import VentureTemplate

venture = VentureTemplate.create(
    template="b2b_saas",
    name="my-saas-venture",
    customization={
        "domain": "developer tools",
        "primary_channel": "product_led",
        "integrations": ["github", "slack", "linear"],
    }
)
# Template provides: base agents, workflows, data schemas, metrics
# You customize: domain logic, specific prompts, integrations
```

---

## Multi-Venture Dashboard

The platform provides a unified view across all your ventures:

### Metrics Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    VENTURE PORTFOLIO                              │
├──────────────┬──────────┬──────────┬──────────┬────────────────┤
│ Venture      │ Stage    │ Health   │ Flywheel │ MRR            │
├──────────────┼──────────┼──────────┼──────────┼────────────────┤
│ TalentAI     │ Scale    │ ████████ │ ▲ 12%/wk │ $45,000        │
│ ConvertAI    │ Prod     │ ██████░░ │ ▲  8%/wk │ $12,000        │
│ KnowAI       │ Optimize │ █████░░░ │ ▶  2%/wk │ $0 (pre-rev)  │
│ ScheduleAI   │ Discovery│ ███░░░░░ │ —        │ —              │
└──────────────┴──────────┴──────────┴──────────┴────────────────┘
```

### Health Indicators
- **Data growth rate**: Is the flywheel generating data?
- **Agent success rate**: Are agents completing tasks reliably?
- **User engagement**: Are users coming back?
- **Cost efficiency**: Cost per successful outcome trending down?
- **Learning velocity**: Is performance improving over time?

### Cross-Venture Intelligence
- Which venture is generating the most transferable patterns?
- Where are shared resources (LLM calls, compute) being consumed?
- Which ventures share user bases or data that could be combined?
- Portfolio-level risk: too concentrated? too diversified?
