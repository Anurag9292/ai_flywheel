# System 2 — Agent Runtime

> Everything needed to build, run, and govern AI agents: LLM access, prompt engineering, orchestration patterns, tools, memory, human oversight, and policy enforcement.

---

## Module 7: LLM Gateway

**Multi-provider routing, caching, fallback chains, cost per call**

### What It Does

- Routes LLM requests across multiple providers (OpenAI, Anthropic, Google, Mistral, Cohere, open-source) with unified API surface and response normalization
- Implements smart routing based on task requirements: selects the cheapest model meeting quality thresholds using historical performance data per task type
- Provides semantic caching — stores responses keyed by semantic similarity of prompts, reducing redundant API calls by 30-60% for repetitive workloads
- Manages fallback chains: if primary provider fails or exceeds latency threshold, automatically retries with next provider in the chain with transparent failover
- Tracks cost per call with attribution to venture, agent, task type, and user — enabling granular cost allocation and budget enforcement
- Implements rate limiting per provider, per venture, and per agent with queuing and backpressure to stay within API quotas
- Supports streaming responses with token-level callbacks for real-time UX and early termination when quality criteria are met
- Provides request/response logging with configurable sampling, PII scrubbing, and structured metadata for downstream analysis

### Feedback Loop

Response quality scores (from Evaluation Framework and human feedback) continuously update the routing model — shifting traffic toward providers/models that perform best for each task type. Cache hit rates and cost data optimize caching strategies.

### Feeds Into

- **Prompt Studio (8)** — Latency and quality data per model inform prompt optimization choices
- **Agent Factory (9)** — Agents consume LLM calls through the gateway
- **Cost Optimizer (35)** — Per-call cost data feeds cost tracking and optimization
- **Trace & Observability (5)** — Every LLM call is a traced span with full metadata

### Fed By

- **Trace & Observability (5)** — Provider reliability and latency data updates routing preferences
- **Evaluation Framework (22)** — Quality scores per model/task update routing decisions
- **Cost Optimizer (35)** — Budget constraints and cost targets shape routing rules
- **Policy Engine (13)** — Policies restrict which models can be used per venture/task

---

## Module 8: Prompt Studio

**Version control, composition, DSPy-style optimization, multi-model testing, analytics**

### What It Does

- Provides version-controlled prompt management with branching, diffing, rollback, and promotion workflows (draft → staging → production)
- Supports prompt composition: build complex prompts from reusable fragments (system instructions, persona blocks, output format specs, few-shot example sets)
- Implements DSPy-style automatic prompt optimization — given a metric and dataset, iteratively refines prompts through LLM-guided search
- Enables multi-model testing: run the same prompt against multiple models simultaneously and compare outputs on quality, cost, and latency
- Provides prompt analytics: tracks performance metrics per prompt version (accuracy, user satisfaction, cost, latency) with automatic regression detection
- Supports parameterized prompts with type-safe variable injection, validation, and default values for safe reuse across contexts
- Implements prompt A/B testing with traffic splitting, statistical significance calculation, and automatic winner promotion
- Maintains a prompt library with tagging, search, and cross-venture sharing (with permission controls) for institutional knowledge

### Feedback Loop

Production performance metrics and human corrections automatically identify underperforming prompt versions. The optimizer uses these signals to propose improvements. Prompts that degrade over time (model drift) trigger automatic re-optimization.

### Feeds Into

- **Agent Factory (9)** — Agents reference managed prompts by ID and version
- **LLM Gateway (7)** — Prompt metadata informs model selection and caching strategies
- **Evaluation Framework (22)** — Prompt versions are evaluated as part of agent evaluation
- **Experiment Tracker (31)** — Prompt experiments are tracked with full metadata

### Fed By

- **Feedback Collector (33)** — User corrections and ratings identify prompt weaknesses
- **Evaluation Framework (22)** — Benchmark results drive optimization targets
- **LLM Gateway (7)** — Model performance data informs which models to optimize for
- **Pattern & Template Library (38)** — Proven prompt patterns are surfaced for reuse

---

## Module 9: Agent Factory & Orchestration

**Blueprints, 8 archetypes, execution, multi-agent patterns: sequential, parallel, hierarchical, debate, consensus, routing, MapReduce**

### What It Does

- Defines agent blueprints: declarative specifications of an agent's purpose, prompts, tools, memory config, policies, and success metrics
- Implements 8 agent archetypes (researcher, analyst, creator, reviewer, executor, monitor, coordinator, specialist) with archetype-specific defaults and best practices
- Orchestrates multi-agent patterns: sequential pipelines, parallel fan-out, hierarchical delegation, adversarial debate, consensus voting, intelligent routing, and MapReduce for data-parallel tasks
- Multi-agent workflows are implemented as Temporal workflows — agent execution is a Temporal activity, orchestration patterns (sequential, parallel, hierarchical) are Temporal workflow patterns, and human-in-the-loop is a Temporal signal
- Manages agent lifecycle: instantiation, execution, pause/resume, timeout, graceful shutdown, and resource cleanup
- Provides agent-level observability: execution traces, decision logs, tool call sequences, and performance metrics per agent instance
- Supports dynamic agent composition — agents can spawn sub-agents, delegate tasks, and aggregate results based on runtime conditions
- Implements agent versioning with gradual rollout, A/B testing between agent versions, and automatic rollback on quality regression
- Maintains an agent registry with capability descriptions, enabling intelligent routing of tasks to the most suitable agent

### Feedback Loop

Agent execution outcomes (success/failure, quality scores, cost, duration) train the orchestration layer to select better patterns and configurations. Failed multi-agent coordinations surface as anti-patterns to avoid.

### Feeds Into

- **Tool Forge (10)** — Agents invoke tools during execution
- **Memory Engine (11)** — Agents read and write to memory stores
- **Human Review Engine (12)** — Agents route uncertain decisions for human approval
- **Policy Engine (13)** — Agent actions are validated against active policies
- **Task Runtime (4)** — Agent executions are managed as tasks
- **Experiment Tracker (31)** — Agent performance is tracked as experiments

### Fed By

- **Prompt Studio (8)** — Optimized prompts improve agent quality
- **LLM Gateway (7)** — Model routing ensures agents use appropriate models
- **Evaluation Framework (22)** — Eval results identify which agent configurations perform best
- **Pattern & Template Library (38)** — Proven agent patterns inform blueprint design
- **Simulation Engine (24)** — Pre-production testing validates agent behavior

---

## Module 10: Tool Forge

**Tool definitions, auto-generation from API docs, testing harness, composition, discovery, credential vault, rate limiting — includes ALL external integrations**

### What It Does

- Manages a unified tool registry: every external capability (ad platforms, data APIs, deployment tools, payment processors, analytics, email, CRMs, etc.) is wrapped as a typed, versioned tool
- Auto-generates tool definitions from OpenAPI/Swagger specs, GraphQL schemas, and API documentation using LLM-powered parsing
- Provides a credential vault with per-venture, per-tool secret management, OAuth token refresh, and automatic rotation
- Implements rate limiting per tool, per venture, and per agent — respecting external API quotas with queuing and backoff
- Supports tool composition: combine multiple tools into higher-level capabilities (e.g., "research competitor" = web search + scrape + summarize)
- Provides a testing harness with mock responses, recording/replay, and contract testing to validate tool behavior without hitting external APIs
- Implements tool discovery: agents can search for tools by capability description, and the system recommends tools based on task context
- Tracks tool reliability, latency, and cost metrics — automatically flagging degraded tools and suggesting alternatives

### Feedback Loop

Tool invocation success rates and agent satisfaction scores identify unreliable tools for improvement. Common tool composition patterns become first-class composite tools. Failed tool calls with manual workarounds generate training data for better tool selection.

### Feeds Into

- **Agent Factory (9)** — Agents discover and invoke tools from the registry
- **Cost Optimizer (35)** — Tool costs are tracked and optimized
- **Trace & Observability (5)** — Tool calls are traced spans with latency and error data
- **Workflow Blueprint Engine (30)** — Available tools determine what workflows can automate

### Fed By

- **Agent Factory (9)** — Agent execution patterns reveal which tools are needed and how they're combined
- **Feedback Collector (33)** — Tool failure reports drive reliability improvements
- **Policy Engine (13)** — Policies restrict tool access per venture/agent
- **Pattern & Template Library (38)** — Proven tool compositions are cataloged for reuse

---

## Module 11: Memory Engine

**Working, episodic, semantic, procedural memory, compression, cross-agent sharing**

### What It Does

- Manages four memory types: working (current task context), episodic (past interactions and outcomes), semantic (factual knowledge), and procedural (learned how-to sequences)
- Implements intelligent compression: summarizes old episodic memories while preserving key decisions, outcomes, and lessons learned
- Supports cross-agent memory sharing with access controls — agents in the same venture can read shared semantic and episodic memory
- Provides memory retrieval via semantic search, temporal queries, and importance-weighted recall to surface the most relevant context
- Implements memory consolidation: periodically reviews episodic memories to extract reusable patterns and update semantic knowledge
- Manages context window optimization: intelligently selects which memories to include in LLM context based on relevance scoring and token budget
- Supports venture-level institutional memory: accumulates knowledge across all agent interactions, building a shared knowledge base
- Provides memory versioning and rollback — recover from corrupted or poisoned memory states

### Memory Access Control & Routing

- Agent blueprints explicitly declare which memory tiers they can access (working, episodic, semantic, procedural, cross-agent)
- The Memory Engine enforces these permissions — an agent can only retrieve from granted tiers
- This prevents context pollution: a stateless screening agent shouldn't access episodic memory from other agents' conversations
- Default access levels per archetype (e.g., executor = working + procedural only, researcher = working + semantic + episodic)
- Strict routing prevents one agent's context from polluting another's reasoning

### Feedback Loop

Memory retrieval quality (did the recalled memory actually help the agent?) feeds back to improve relevance scoring. Memories that consistently lead to good outcomes get higher importance weights. Compression quality is evaluated by checking if agents can still perform tasks with compressed context.

### Feeds Into

- **Agent Factory (9)** — Agents read memories for context during execution
- **Knowledge Graph Builder (17)** — Procedural and semantic memories feed into the knowledge graph
- **Embedding Engine (16)** — Memory content is embedded for semantic retrieval
- **Pattern & Template Library (38)** — Consolidated procedural memories become reusable patterns

### Fed By

- **Agent Factory (9)** — Agent interactions produce new episodic memories
- **Feedback Collector (33)** — Outcome data determines which memories are valuable
- **Knowledge Graph Builder (17)** — Structured knowledge provides semantic memory content
- **Human Review Engine (12)** — Human corrections update and fix incorrect memories

---

## Module 12: Human Review Engine

**Queues, approval policies, corrections as training data, escalation rules, reviewer disagreement tracking**

### What It Does

- Manages review queues with priority scoring, SLA tracking, and load balancing across available reviewers
- Implements configurable approval policies: which actions require review (based on risk, cost, novelty, confidence score, or policy rules)
- Captures human corrections as structured training data — every correction is a labeled example of "what the agent should have done"
- Provides escalation rules: if no reviewer responds within SLA, or if reviewers disagree, escalate to senior reviewer or auto-approve with monitoring
- Tracks reviewer disagreement: when multiple reviewers evaluate the same item, measures inter-annotator agreement and identifies ambiguous cases
- Supports review templates per task type with guided evaluation criteria, reducing reviewer cognitive load and improving consistency
- Implements reviewer performance tracking: accuracy, speed, consistency, and calibration against gold-standard decisions
- Provides a feedback-to-training pipeline: approved corrections are automatically formatted and routed to model fine-tuning or prompt improvement

### Feedback Loop

Review outcomes train the system to better predict which items need review (reducing unnecessary reviews over time). Reviewer disagreement patterns identify areas where policies or agent instructions are ambiguous and need clarification.

### Feeds Into

- **Labeling & Ground Truth (18)** — Corrections become labeled training examples
- **Policy Engine (13)** — Review patterns inform policy refinement
- **Prompt Studio (8)** — Systematic corrections identify prompt weaknesses
- **Model Forge (21)** — Corrections feed fine-tuning datasets
- **Evaluation Framework (22)** — Human judgments become evaluation benchmarks

### Fed By

- **Agent Factory (9)** — Agents route uncertain decisions for human review
- **Policy Engine (13)** — Policies determine what requires review
- **Trace & Observability (5)** — Error patterns trigger increased review requirements
- **Feedback Collector (33)** — User complaints escalate items to review queues

---

## Module 13: Policy Engine

**Active constraints, rules per venture/agent, safety boundaries, budget limits, brand tone, compliance enforcement, blocking vs warning**

### What It Does

- Enforces active constraints on all agent actions: content policies, safety boundaries, budget limits, rate limits, and compliance rules
- Supports rule hierarchies: platform-level policies (always enforced) > venture-level policies > agent-level policies, with inheritance and override semantics
- Implements both blocking (hard stop) and warning (flag for review) modes per policy, with configurable thresholds for escalation
- Provides brand tone enforcement: ensures agent outputs match venture-specific voice, terminology, and communication style guidelines
- Manages budget policies: per-venture and per-agent spending limits with configurable actions (warn, throttle, block) at percentage thresholds
- Supports compliance rule sets (GDPR, HIPAA, SOC2, industry-specific) with pre-built templates and custom rule authoring
- Implements policy testing: simulate agent actions against policies to verify behavior before deployment, catching conflicts and gaps
- Tracks policy violations with full context (what was attempted, why it was blocked, what the agent did instead) for audit and refinement

### Feedback Loop

False positive policy blocks (legitimate actions incorrectly blocked) and false negative violations (harmful actions that slipped through) continuously refine policy rules. Violation patterns across ventures identify gaps requiring new platform-level policies.

### Feeds Into

- **Agent Factory (9)** — Policies constrain agent behavior at runtime
- **LLM Gateway (7)** — Policies restrict model choices and token budgets
- **Tool Forge (10)** — Policies restrict tool access and usage limits
- **Human Review Engine (12)** — Policy triggers can require human approval
- **Deployment Engine (36)** — Deployment policies gate releases

### Fed By

- **Human Review Engine (12)** — Review outcomes identify policy gaps and over-restrictions
- **Trace & Observability (5)** — Error and violation patterns suggest new policy rules
- **Feedback Collector (33)** — User complaints about agent behavior inform policy refinement
- **Reliability & Incident Engine (37)** — Incidents may require emergency policy changes
- **Identity & Tenancy (2)** — Venture context determines applicable policies
