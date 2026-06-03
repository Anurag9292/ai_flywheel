# Feature Development Loop

How new features are identified, validated, built, shipped, and improved within a running venture. This is the inner development cycle — distinct from [venture validation](validation-framework.md) which decides whether a business should exist.

---

## Overview

```
SIGNAL DETECTION (automatic)
     ↓
FEATURE HYPOTHESIS (system proposes, you approve)
     ↓
MINI-VALIDATION (configurable — often skippable)
     ↓
PRODUCT DESIGN (quick — UX flow + interaction pattern)
     ↓
BUILD (prompts, agents, UI — typically 1-3 days)
     ↓
SIMULATE & TEST (pre-launch quality check)
     ↓
SHIP (behind feature flag, A/B test)
     ↓
MEASURE & LEARN (metrics, feedback, traces)
     ↓
ITERATE or KILL
     ↓
(back to SIGNAL DETECTION)
```

---

## How This Differs from Venture Validation

| Aspect | Venture Validation | Feature Loop |
|--------|-------------------|--------------|
| **Question** | "Should this business exist?" | "Should we add this to the product?" |
| **Evidence source** | External (market, strangers, money) | Internal (usage data, feedback, metrics) |
| **Timeline** | 4-6 weeks | 3-7 days |
| **Cost** | $200-1000 | ~$0 (using existing infrastructure) |
| **Risk** | High (wrong venture = months wasted) | Low (feature flag, easy rollback) |
| **Validation** | Strangers paying money | Existing users engaging more |
| **Kill signal** | Nobody pays | Core metric doesn't move (or drops) |
| **Success signal** | Revenue + retention | Core metric improves significantly |

---

## Stage 1: Signal Detection

**Fully automatic.** The platform continuously synthesizes patterns from:

| Signal Source | Module | What it detects |
|---------------|--------|-----------------|
| User feedback (explicit) | Feedback Collector | Feature requests, complaints, suggestions |
| User behavior (implicit) | Metrics Registry | Drop-offs, retries, time-on-task anomalies |
| Agent failures | Error Analyzer (in Trace) | Patterns in what agents struggle with |
| Support interactions | Customer Discovery | Repeated questions or issues |
| Override patterns | Human Review Engine | Where humans consistently disagree with AI |
| Performance gaps | Evaluation Framework | Where accuracy/quality is below threshold |
| Cost anomalies | Cost Optimizer | Operations that are disproportionately expensive |

### Example (MatchHire: JD Optimizer)

```yaml
signal_synthesis:
  pattern_detected: "job_description_quality_drives_screening_accuracy"
  
  evidence:
    - source: feedback_collector
      signal: "3 employers cited 'candidates don't match' when overriding AI"
      
    - source: trace_and_observability
      signal: "Screening confidence drops 50% when JD has < 5 structured requirements"
      
    - source: metrics_registry
      signal: "Jobs with structured requirements get 2.3x better screening accuracy"
      
    - source: customer_discovery (historical interviews)
      signal: "4/15 interviewees mentioned 'my JD attracts wrong people' unprompted"
      
    - source: human_review_engine
      signal: "Employer override reasons frequently mention 'not what I was looking for'"
      
  confidence_from_signals: 0.75
  
  auto_recommendation:
    feature: "AI Job Description Optimizer"
    rationale: "Improving input quality (JDs) will improve output quality (screening)"
    estimated_impact: "+30% screening accuracy for affected jobs"
    estimated_effort: "3-5 days"
    priority_score: 8.2/10
```

**Key point:** The system PROPOSES features from data. You don't have to think of every improvement yourself.

---

## Stage 2: Feature Hypothesis

The system generates a lightweight hypothesis (not full venture-level):

```yaml
feature_hypothesis:
  id: FH-012
  venture: matchhire
  feature: "AI Job Description Optimizer"
  
  hypotheses:
    - id: FH-012-A
      type: user_wants_it
      statement: "Employers will use the optimizer if offered"
      success_metric: usage_rate > 40% of new job posts
      
    - id: FH-012-B
      type: improves_core_metric
      statement: "Optimized JDs improve screening accuracy by >30%"
      success_metric: A/B test shows significant improvement
      
    - id: FH-012-C
      type: reduces_friction
      statement: "Fewer 'bad match' overrides after JD optimization"
      success_metric: override_rate drops >50%

  effort_estimate: 3-5 days
  risk_level: low (additive, doesn't change core flow, easily rolled back)
  dependencies: none (can ship independently)
  
  decision_options:
    - BUILD (signal strong enough, effort low, risk low)
    - VALIDATE_FIRST (need more evidence before building)
    - DEFER (good idea but not the priority right now)
    - KILL (on reflection, not worth it)
```

**Your decision:** Approve, defer, or kill. One click.

---

## Stage 3: Mini-Validation (Often Skippable)

For features within a running venture, you often have enough signal from production data to skip formal validation. But when you're less certain:

```yaml
mini_validation:
  mode: lightweight  # Not full Evidence Ladder
  
  options:
    # Option A: Skip (signal is strong enough)
    skip:
      reason: "4 interview mentions + 3 override patterns + metric correlation = enough"
      confidence: 0.8
      
    # Option B: Quick user check (1-2 days)
    quick_check:
      method: "Ask next 5 employers during onboarding: 'Would AI help writing your JD?'"
      duration: 3 days
      
    # Option C: Technical feasibility only
    tech_check:
      method: "Can GPT-4o generate good JDs from brief inputs? Test 20 samples."
      duration: 2 hours
      
    # Option D: Prototype test (fake door)
    fake_door:
      method: "Add 'Optimize with AI' button, measure clicks (don't build yet)"
      duration: 1 week
```

---

## Stage 4: Product Design

**Module: Product Experience Engine**

Quick design pass — not a full product spec, just enough to build:

```yaml
feature_design:
  name: jd_optimizer
  
  user_flow:
    1. Employer clicks "Create Job Post"
    2. New first step: "Describe the role in 2-3 sentences"
    3. AI generates full structured JD (requirements, nice-to-haves, salary range)
    4. Employer reviews, edits inline, approves
    5. Optimized JD flows into screening pipeline
    
  interaction_pattern: copilot_inline
    # Augments existing flow, not a separate page
    # AI suggests, human edits and approves
    
  ui_components:
    - text_input: brief role description
    - ai_generation_panel: structured JD (editable)
    - quality_score_badge: "This JD scores 8.5/10 for screening clarity"
    - inline_suggestions: "Add salary range to attract 40% more qualified candidates"
    
  fallback: employer can skip AI and write manually (always available)
```

---

## Stage 5: Build

**Modules: Agent Factory, Prompt Studio, Tool Forge, Task Runtime**

```yaml
build_plan:
  tasks:
    - name: "Design JD generation prompt"
      module: prompt_studio
      time: 2 hours
      details: "System + user prompt, test on 20 sample inputs, iterate"
      
    - name: "Create JD Optimizer agent"
      module: agent_factory
      time: 30 min
      details: "Blueprint with tools (salary lookup, skills taxonomy, historical JD data)"
      
    - name: "Build UI component"
      module: web_app (Next.js)
      time: 4 hours
      details: "Inline generation panel in job creation flow"
      
    - name: "Connect to screening pipeline"
      module: task_runtime
      time: 1 hour
      details: "Wire optimized JD output as input to screening agent"
      
    - name: "Set up feature flag + A/B test"
      module: ab_test_engine + deployment
      time: 30 min
      details: "50/50 split, define metrics, set duration"
      
  total_time: ~1 day
  artifacts_produced:
    - prompt: jd_optimizer_v1
    - agent: jd_optimizer_agent_v1
    - ui: JDOptimizerPanel component
    - config: feature flag + experiment definition
```

---

## Stage 6: Simulate & Test

**Modules: Simulation Engine, Evaluation Framework**

```yaml
pre_launch_tests:
  
  quality_test:
    method: "Generate 50 JDs from brief descriptions, score against quality rubric"
    threshold: average quality > 7/10
    result: 8.2/10 ✓
    
  pipeline_test:
    method: "Run generated JDs through full screening pipeline, compare accuracy"
    threshold: > 20% improvement over unstructured JDs
    result: 34% improvement ✓
    
  bias_test:
    method: "Check generated JDs for gendered/biased language"
    threshold: < 5% gendered terms
    result: 2.1% ✓
    
  edge_cases:
    method: "Test with vague inputs, non-standard roles, multiple languages"
    results:
      - vague_input: "Gracefully asks clarifying questions" ✓
      - niche_role: "Quality drops to 6.5/10 — acceptable for v1" ⚠️
      - non_english: "Generates in input language" ✓
      
  cost_estimate:
    per_generation: $0.012 (GPT-4o-mini for generation)
    monthly_at_scale: ~$15 (assuming 1200 JDs/month)
    verdict: "Negligible cost" ✓
    
  launch_decision: APPROVED
```

---

## Stage 7: Ship

**Modules: Deployment Engine, A/B Test Engine, Policy Engine**

```yaml
rollout:
  strategy: feature_flag_ab_test
  
  configuration:
    flag_name: jd_optimizer_enabled
    groups:
      control: "Normal job creation (manual JD writing)"
      variant: "AI JD Optimizer offered at start of creation"
    split: 50/50
    duration: 2 weeks (or until statistical significance reached)
    
  metrics_tracked:
    primary: screening_accuracy_per_job
    secondary:
      - employer_override_rate
      - time_to_post_job
      - optimizer_usage_rate
      - candidate_quality_score
      - employer_satisfaction
      
  guardrails:
    - employer_satisfaction must not drop below 4.0/5
    - if bias_score > 5% on any generated JD → auto-pause + alert
    - if screening_accuracy drops (opposite of expected) → auto-pause + alert
    
  auto_actions:
    on_guardrail_violation: pause experiment, alert founder, create snapshot
    on_statistical_significance: notify founder with recommendation
```

---

## Stage 8: Measure & Learn

**Modules: Metrics Registry, Experiment Tracker, Feedback Collector, Trace & Observability**

```yaml
results_after_2_weeks:
  
  adoption:
    optimizer_offered_to: 156 job posts
    optimizer_used: 118 (75.6%)
    manually_skipped: 38 (24.4%)
    verdict: "Exceeds 40% threshold" ✓
    
  primary_metric:
    screening_accuracy_control: 78%
    screening_accuracy_variant: 91%
    improvement: +13 percentage points (16.7% relative)
    p_value: 0.002
    verdict: "Statistically significant, exceeds 30% relative target" ✓
    
  secondary_metrics:
    override_rate: 22% → 8% (-64%) ✓
    time_to_post: 35 min → 12 min (-66%) ✓
    candidate_quality: 6.8 → 8.1 (+19%) ✓
    
  unexpected_discoveries:
    - "Employers who use optimizer post 40% more jobs (reduced friction)"
    - "Generated JDs get 28% more applications (better descriptions)"
    - "Salary range suggestion independently valuable — potential standalone feature"
    
  hypothesis_results:
    FH-012-A: VALIDATED (75.6% > 40%)
    FH-012-B: VALIDATED (16.7% relative improvement)
    FH-012-C: VALIDATED (64% override reduction)
    
  decision: SHIP TO 100%
  
  # Venture snapshot auto-created before 100% rollout
  snapshot_created: vs_01HZ2AB...
```

---

## Stage 9: Iterate

The loop continues. New signals emerge from full rollout:

```yaml
post_ship_signals:
  
  iteration_1:
    signal: "Employers edit 'requirements' section 60% of the time"
    insight: "AI over-specifies (lists 10 requirements when 5-7 is optimal)"
    action: "Update prompt: cap at 5-7 requirements, order by importance"
    result: "Edit rate drops from 60% to 25%"
    time: 2 hours
    
  iteration_2:
    signal: "Quality drops for niche roles (ML Engineer, Biotech Researcher)"
    insight: "Generic model lacks specialized domain vocabulary"
    action: "Add RAG from Knowledge Graph — pull language from similar successful JDs"
    result: "Niche role quality: 6.1 → 8.4"
    time: 4 hours
    
  iteration_3:
    signal: "Employers love salary suggestion most (highest engagement)"
    insight: "This could be a standalone feature / marketing hook"
    action: "Log as new feature signal: 'Salary Intelligence Dashboard'"
    feeds_back_to: Stage 1 (Signal Detection for next feature)

  # Cross-venture pattern captured
  pattern_extracted:
    name: "copilot_at_creation_moment"
    description: "Offering AI generation at the start of a creation flow 
                  (before manual work begins) achieves 75%+ adoption and 
                  dramatically improves downstream quality"
    applicable_to: 
      - sales_venture: email composition
      - knowledge_venture: document tagging
      - tutoring_venture: lesson plan creation
```

---

## Automation Level Per Stage

| Stage | % Automatic | Your effort |
|-------|-------------|-------------|
| Signal Detection | 100% | Read the synthesis |
| Feature Hypothesis | 90% | Approve/reject/defer (one click) |
| Mini-Validation | Configurable (0-100%) | Choose to skip or run quick check |
| Product Design | 70% | Review proposed UX, refine if needed |
| Build | 50-70% | Review generated prompts, approve UI |
| Simulate & Test | 95% | Review pass/fail results |
| Ship | 90% | "Approve to launch?" (one click) |
| Measure | 100% | Read results |
| Decide | System recommends | "Ship 100%?" / "Kill?" / "Iterate?" |
| Iterate | 80% | Approve suggested improvements |

**Total founder time per feature loop: 2-4 hours of decision-making spread over 1-2 weeks.** The platform handles the other 40+ hours of execution, testing, monitoring, and analysis.

---

## Connecting to State Management

Every stage creates revertible state:

| Stage | State created | Revert method |
|-------|--------------|---------------|
| Build | New prompt version, agent version | Revert to previous version |
| Ship | Feature flag + experiment config | Disable flag (instant) |
| Ship 100% | Venture snapshot (auto-created) | Restore snapshot |
| Iterate | Prompt/config updates | Revert individual changes or snapshot |

If anything goes wrong at any stage, you can always go back. See [State Management](state-management.md) for details.
