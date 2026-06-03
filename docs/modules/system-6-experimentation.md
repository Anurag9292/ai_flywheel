# System 6 — Experimentation

> Unified experiment tracking, statistical testing, feedback collection, metric management, and cost optimization. The scientific method applied systematically across every platform decision.

---

## Module 31: Experiment Tracker

**Unified tracking across all modules, hyperparameters, metrics, artifacts, comparison views, meta-learning to predict which experiments to run next, cross-venture insights**

### What It Does

- Provides unified experiment tracking across all platform modules: prompt experiments, model training runs, agent configurations, A/B tests, feature experiments, and business experiments share one system of record
- Captures comprehensive metadata per experiment: hypothesis, parameters, metrics, artifacts, duration, cost, code version, and data version with automatic collection
- Offers comparison views: side-by-side metric comparison across experiments with statistical significance testing, visualizations, and automatic highlighting of meaningful differences
- Implements meta-learning: analyzes experiment history to predict which experiments are most likely to yield improvements, reducing wasted compute and time
- Provides cross-venture insights: (with permission) surfaces relevant experiments from other ventures that addressed similar problems, including what worked and what didn't
- Supports experiment templates: pre-configured experiment setups for common patterns (prompt A/B test, model architecture search, feature ablation study)
- Tracks experiment lineage: which experiments built on which prior results, forming a tree of exploration with clear decision points
- Generates experiment summary reports: automated narratives explaining what was tried, what was learned, and recommended next steps

### Feedback Loop

Experiment outcome predictions (from meta-learning) are validated against actual results — prediction accuracy improves the recommendation engine. Experiments that are run but never analyzed identify process gaps. Cross-venture insight utility (was it actually helpful?) refines sharing algorithms.

### Feeds Into

- **Model Forge (21)** — Training experiment results guide model selection
- **Prompt Studio (8)** — Prompt experiment results drive optimization
- **Venture Thesis Engine (27)** — Experiment outcomes update hypothesis confidence
- **Artifact Manager (6)** — Experiment artifacts are versioned and stored
- **Meta-Learning & Flywheel Engine (39)** — Experiment data feeds cross-venture learning

### Fed By

- **All modules** — Every module running experiments reports to the tracker
- **Evaluation Framework (22)** — Eval metrics are the primary experiment outcomes
- **Feedback Collector (33)** — Production feedback validates experiment conclusions
- **Cost Optimizer (35)** — Cost data is attached to every experiment

---

## Module 32: A/B Test & Optimization Engine

**Statistical testing, sample size calculation, sequential testing, multi-variant, bandits/Thompson sampling/UCB, Bayesian optimization, contextual bandits, traffic splitting — merges old A/B Test + Bandit Optimizer**

### What It Does

- **Default: Multi-Armed Bandits (Thompson Sampling)** for early-stage and low-traffic scenarios (< 1000 visitors per variant). Converges in days not months. Minimizes regret by dynamically allocating traffic to the best performer. After ~30-50 observations, Thompson Sampling is already allocating 70%+ of traffic to the winning variant. Works equally well with 2 variants or 20 variants.
- **Traditional frequentist A/B testing** reserved for high-traffic scenarios where statistical rigor is needed (10K+ users, regulatory requirements, irreversible decisions). Includes proper sample size calculation, power analysis, multiple comparison correction, and stopping rules.
- **Auto-selection** — the engine automatically chooses the right method based on expected traffic volume. Below threshold = Thompson Sampling. Above = frequentist.
- **Why this matters for venture validation**: Early-stage landing pages might get 150 visitors/week. Traditional A/B testing would take 4-6 weeks for significance. Thompson Sampling gives actionable signal in days by allocating 70%+ traffic to the best performer after just 30-50 observations.
- Implements sequential testing (always-valid p-values): enables early stopping when results are conclusive without inflating false positive rates
- Supports multi-variant testing (A/B/C/n): tests multiple alternatives simultaneously with appropriate statistical adjustments
- Implements Bayesian optimization for continuous parameter spaces: efficiently searches for optimal configurations with minimal evaluations
- Supports contextual bandits: selects variants based on user/context features, personalizing treatment allocation for heterogeneous populations
- Manages traffic splitting: hash-based consistent assignment, venture-level isolation, mutual exclusion between concurrent experiments, and holdout groups
- Provides experiment lifecycle management: design, launch, monitor, analyze, and conclude with guardrail metric protection and auto-shutdown on harm

### Feedback Loop

Experiments that conclude with surprising results (violating prior assumptions) update Bayesian priors for future tests. Sample size estimates compared to actual required samples improve power calculations. Bandit regret analysis optimizes algorithm selection per problem type.

### Feeds Into

- **Offer Design Engine (28)** — Messaging and pricing A/B test results refine offers
- **Product Experience Engine (29)** — Feature experiments guide product decisions
- **Prompt Studio (8)** — Prompt A/B tests identify winning versions
- **Agent Factory (9)** — Agent variant tests select best configurations
- **Venture Thesis Engine (27)** — Test results serve as evidence for hypotheses

### Fed By

- **Venture Thesis Engine (27)** — Hypotheses define what to test
- **Offer Design Engine (28)** — Messaging variants become test treatments
- **Metrics & Reward Registry (34)** — Metric definitions determine test success criteria
- **Feedback Collector (33)** — Feedback signals serve as experiment metrics
- **Cost Optimizer (35)** — Cost constraints limit experiment scope

---

## Module 33: Feedback Collector

**Human feedback: thumbs/corrections/ratings, automated: downstream metrics, implicit: clicks/ignores/retries/escalations, routing to correct module, quality scoring, optimal feedback timing**

### What It Does

- Collects explicit human feedback: thumbs up/down, star ratings, free-text corrections, preference comparisons, and structured evaluations
- Captures automated feedback: downstream metric movements (did a recommendation lead to conversion? did a generated email get a reply?)
- Tracks implicit feedback signals: user clicks vs ignores, retries (user tried again → first attempt failed), escalations to human, edit distance from generated to final
- Routes feedback to the correct consuming module: prompt corrections → Prompt Studio, model quality → Model Forge, agent behavior → Agent Factory, tool failures → Tool Forge
- Implements quality scoring for feedback: weights feedback by provider reliability, context completeness, and agreement with other signals
- Optimizes feedback timing: determines the best moment to request feedback (not too early, not too late) to maximize response rate and accuracy
- Supports feedback attribution: maps feedback to the specific model version, prompt, agent, and parameters that produced the output
- Maintains feedback datasets with versioning: structured collections of (input, output, feedback) triples for training and evaluation

### Feedback Loop

Feedback collection rates (what percentage of users provide feedback) inform UI optimization. Feedback that correlates with outcome metrics is weighted higher. Feedback signals that fail to predict downstream quality are deprioritized.

### Feeds Into

- **Model Forge (21)** — Feedback becomes training data for fine-tuning
- **Prompt Studio (8)** — Corrections identify prompt weaknesses
- **Evaluation Framework (22)** — Feedback validates evaluation relevance
- **Human Review Engine (12)** — Negative feedback escalates items for review
- **Labeling & Ground Truth (18)** — Corrections become labeled examples
- **Metrics & Reward Registry (34)** — Feedback data feeds reward modeling
- **Memory Engine (11)** — Outcome feedback identifies valuable memories

### Fed By

- **Agent Factory (9)** — Agent outputs are the subjects of feedback
- **LLM Gateway (7)** — Response metadata enables attribution
- **Product Experience Engine (29)** — UX design determines feedback collection methods
- **A/B Test & Optimization Engine (32)** — Experiments generate outcomes to collect feedback on

---

## Module 34: Metrics & Reward Registry

**Metric definitions with numerator/denominator/window, business vs model vs agent vs system metrics, north star per venture, guardrail metrics, reward modeling, proxy metric validation, Goodhart's Law detection — merges old Metrics Registry + Reward Modeler**

### What It Does

- Defines metrics with formal specifications: numerator, denominator, time window, segmentation dimensions, and computation logic — ensuring consistent measurement across the platform
- Categorizes metrics into tiers: business metrics (revenue, retention), model metrics (accuracy, latency), agent metrics (task success, cost), and system metrics (uptime, throughput)
- Designates a north star metric per venture: the single most important measure of venture success that all optimization ultimately serves
- Manages guardrail metrics: measures that must not degrade regardless of what's being optimized (safety, fairness, user trust, legal compliance)
- Implements reward modeling: learns reward functions from human preferences using comparison data, enabling RLHF and preference-based optimization
- Validates proxy metrics: continuously checks that optimizing proxy metrics (easy to measure) still improves true metrics (hard to measure) detecting divergence
- Detects Goodhart's Law violations: identifies when optimizing a metric causes it to lose its correlation with the underlying goal it was meant to measure
- Provides metric dependency mapping: visualizes how metrics relate to each other, identifying leading/lagging indicators and causal chains

### Feedback Loop

Metrics that stop correlating with business outcomes are flagged for review or retirement. Proxy metrics that diverge from true metrics trigger recalibration. Goodhart's Law detection results refine which metrics are safe to optimize directly.

### Feeds Into

- **A/B Test & Optimization Engine (32)** — Metric definitions determine experiment success criteria
- **Cost Optimizer (35)** — Cost metrics are defined in the registry
- **Evaluation Framework (22)** — Metrics define evaluation targets
- **Agent Factory (9)** — Agent success metrics drive optimization
- **Venture Thesis Engine (27)** — Metric movements serve as evidence for hypotheses
- **Model Forge (21)** — Reward models guide training optimization

### Fed By

- **Feedback Collector (33)** — Human preferences train reward models
- **Trace & Observability (5)** — System metrics are collected from observability
- **A/B Test & Optimization Engine (32)** — Experiment results validate metric utility
- **Meta-Learning & Flywheel Engine (39)** — Cross-venture patterns identify universally useful metrics

---

## Module 35: Cost Optimizer

**Per-token LLM tracking by model/agent/task/venture, smart routing to cheapest model meeting quality, caching, budget alerts, hard limits, cost/quality Pareto frontier, spend prediction**

### What It Does

- Tracks per-token LLM costs with multi-dimensional attribution: by model, provider, agent, task type, venture, user, and time period
- Implements smart routing: for each request, selects the cheapest model that meets the quality threshold based on task classification and historical performance
- Maximizes cache utilization: identifies semantically similar requests that can reuse cached responses, measuring cache hit rates and savings
- Provides budget alerts at configurable thresholds (50%, 75%, 90%, 100%) with escalation to venture owners and automatic actions (warn, throttle, block)
- Enforces hard spending limits: per-venture, per-agent, per-day/week/month caps that prevent runaway costs with graceful degradation
- Visualizes the cost/quality Pareto frontier: shows which configurations achieve the best quality at each price point, identifying dominated options
- Predicts future spend: extrapolates from current usage patterns to project monthly/quarterly costs, flagging ventures on trajectory to exceed budgets
- Recommends cost reduction actions: identifies specific opportunities (prompt shortening, model downgrading for easy tasks, increased caching, batch processing)

### Feedback Loop

Cost predictions compared to actual spend improve forecasting models. Quality regressions caused by cost-saving routing refinements tighten quality thresholds. Ventures that consistently hit budget limits without degradation suggest limits can be lowered.

### Feeds Into

- **LLM Gateway (7)** — Cost targets influence routing decisions
- **Policy Engine (13)** — Budget limits become enforced policies
- **Identity & Tenancy (2)** — Cost data informs venture billing
- **Simulation Engine (24)** — Cost projections inform pre-launch estimates
- **Experiment Tracker (31)** — Cost is tracked per experiment

### Fed By

- **LLM Gateway (7)** — Per-call cost data from every LLM interaction
- **Tool Forge (10)** — External tool costs (API calls, compute)
- **Task Runtime (4)** — Compute infrastructure costs per task
- **Trace & Observability (5)** — Resource utilization data
- **Metrics & Reward Registry (34)** — Quality metrics validate cost/quality tradeoffs
