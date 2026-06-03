# Validation Configuration & Overrides

The [Evidence Ladder](validation-framework.md) defines the default 5-rung validation flow. This document covers how to customize, skip, or override that flow based on your situation.

---

## Why Override?

The default ladder assumes zero prior knowledge and full budget. Real founders often have:

- **Domain expertise** — Worked in the industry, already know the market structure
- **Existing relationships** — Have customer contacts, don't need cold sourcing
- **Budget constraints** — Can't afford $500 in ads to validate, need free/cheap methods
- **High conviction** — Strong thesis from previous venture, just need to confirm
- **Time pressure** — Want to validate in days, not weeks
- **Organic reach** — Have an audience already, don't need paid acquisition

The validation pipeline is configurable, not rigid.

---

## Rung-Level Controls

Each rung can be set to one of three modes:

| Mode | Behavior |
|------|----------|
| `run` | Execute the rung fully (default) |
| `skip` | Skip entirely, provide reason and manual confidence |
| `partial` | Run some checks within the rung, skip others |

```yaml
validation_config:
  venture: matchhire
  
  rungs:
    market_structure:
      mode: skip
      reason: "I worked in HR tech for 5 years, I know this market"
      manual_confidence: 0.9
      
    proxy_data:
      mode: partial
      run: [search_demand, time_cost_estimation, alternative_solutions]
      skip: [competitive_pricing]  # I already know competitor pricing
      budget_cap: $50
      
    verbal_signals:
      mode: run
      sample_size: 8  # Fewer interviews than default 15 (I have conviction)
      skip_sourcing: true  # I'll provide my own interview contacts
      
    behavioral_signals:
      mode: partial
      run: [landing_page, content_test]
      skip: [ad_campaigns]  # Too expensive right now
      budget_cap: $200
      
    money_signals:
      mode: run  # Always run this — the only signal that truly matters
```

---

## Preset Profiles

Instead of configuring each rung manually, pick a preset:

### Full Validation (Default)

**When:** New market, no prior knowledge, sufficient budget ($500-1000)

```yaml
preset: full
# All 5 rungs, full budget, sequential with kill signals
# Timeline: 4-6 weeks
```

### Domain Expert

**When:** You know the market deeply but need to validate the specific solution/offer

```yaml
preset: domain_expert
# Skip Rung 1-2 (you already know market structure and proxy data)
# Start at Rung 3 (interviews to validate specific pain + WTP)
# Then Rung 4-5
# Timeline: 2-3 weeks
```

### Speed Run

**When:** High conviction, just want quick confirmation before building

```yaml
preset: speed_run
# Rung 1 (fast, 2 hours, just confirm no obvious kill signals)
# Skip Rung 2-3
# Jump to Rung 4 (landing page only, no ads) + Rung 5 (pre-sale)
# Timeline: 1 week
```

### Zero Budget

**When:** No money for paid tools or ads

```yaml
preset: zero_budget
# Rung 1: Free data only (Google Trends, free APIs, manual research)
# Rung 2: Free checks only (no SEMrush, use free alternatives)
# Rung 3: Source interviews via personal network + free communities
# Rung 4: Organic only (content, communities, direct outreach — no paid ads)
# Rung 5: Direct pre-sale via email/DM (no landing page spend)
# Timeline: 3-4 weeks (slower without paid acceleration)
```

### Pivot Validation

**When:** Existing customers, testing a new direction or adjacent product

```yaml
preset: pivot
# Skip Rung 1-2 (you already have a market)
# Rung 3: Interview existing customers about new pain/direction
# Rung 4: Test with existing audience (email list, existing users)
# Rung 5: Offer to existing customers first
# Timeline: 1-2 weeks
```

### Audience-First

**When:** You have organic reach (newsletter, social following, community) and want to validate through your audience

```yaml
preset: audience_first
# Rung 1: Quick sanity check (1-2 hours)
# Skip Rung 2-3 (your audience IS the proxy data and verbal signal)
# Rung 4: Content to audience, measure response (free)
# Rung 5: Pre-sell to audience (free)
# Timeline: 1-2 weeks
```

### Custom

**When:** None of the presets match your situation

```yaml
preset: custom
# Configure each rung individually (see Rung-Level Controls above)
```

---

## Budget-Aware Auto-Skipping

Set a total validation budget. The system allocates intelligently and auto-skips checks that would exceed the budget:

```yaml
validation_budget: $300

# System auto-allocates:
#   Rung 1: $0 (free public data, Google Trends, Reddit, G2 scraping)
#   Rung 2: $50 (SEMrush limited queries)
#   Rung 3: $50 (Amazon gift cards for interview incentives)
#   Rung 4: $150 (small LinkedIn ad test + Vercel deploy)
#   Rung 5: $50 (Stripe account + direct outreach)
```

```yaml
validation_budget: $0

# System uses only free methods:
#   Rung 1: Google Trends (pytrends), Reddit API, free review scraping, BLS data
#   Rung 2: Free keyword tools, manual competitor research, GitHub/HN analysis
#   Rung 3: Source via personal network, free communities, X/LinkedIn posts
#   Rung 4: Free landing page (Vercel free tier), organic content only
#   Rung 5: Direct DMs/emails asking for pre-payment (Stripe free to set up)
```

Budget allocation priorities (most money goes to highest-signal activities):
1. Money signals (Rung 5) — always cheap, always run
2. Behavioral signals (Rung 4) — highest signal-per-dollar when using ads
3. Verbal signals (Rung 3) — interview incentives
4. Proxy data (Rung 2) — paid data tools
5. Market structure (Rung 1) — almost always free

---

## Confidence Injection (Manual Overrides)

Skip any rung by manually injecting your confidence level with justification:

```yaml
manual_overrides:
  - hypothesis: problem_exists
    confidence: 0.95
    evidence: "5 years as hiring manager, experienced this pain daily, discussed with 50+ peers"
    skip_rungs: [1, 2]
    
  - hypothesis: channel_exists
    confidence: 0.85
    evidence: "12K LinkedIn followers in HR space, 40% engagement rate on hiring content"
    skip_rungs: [4]  # Don't need paid ads, I have organic distribution
    
  - hypothesis: willingness_to_pay
    confidence: 0.7
    evidence: "3 former colleagues said they'd pay, but haven't seen the product"
    skip_rungs: []  # Not confident enough to skip any rung for WTP
```

**Rules for manual overrides:**
- The system accepts your override but logs it as "founder assertion" (not validated)
- If the venture later fails, the system flags which overrides might have caught it early
- You can always go back and run skipped rungs later if confidence drops
- Money signals (Rung 5) should almost never be skipped — nothing replaces actual payment

---

## Parallel vs Sequential Execution

By default, the ladder runs sequentially (stop early if kill signal detected). But you can run rungs in parallel for speed:

### Sequential (Default)

```yaml
execution_mode: sequential
# Rung 1 → if pass → Rung 2 → if pass → Rung 3 → ...
# Stops immediately on kill signal
# Slowest but cheapest (saves money if early rungs fail)
```

### Parallel

```yaml
execution_mode: parallel
# Run all rungs simultaneously
# Fastest but most expensive (pays for everything upfront)
# Use when you have high conviction and want speed
```

### Custom Ordering

```yaml
execution_mode: custom
stages:
  - parallel: [1, 2]        # Market + proxy data run simultaneously (both cheap/fast)
  - sequential: [3]          # Interviews after data confirms direction
  - parallel: [4, 5]         # Behavioral + money tests simultaneously (save time)
```

### Inverted (Money First)

```yaml
execution_mode: inverted
# Start with Rung 5 (money signal) — put up a landing page with Stripe
# If people pay → THEN do Rung 3-4 to understand WHY they paid
# If nobody pays → kill immediately (saved weeks of research)
# Bold but fast. Works when you can describe the offer clearly.
```

---

## Skipping Best Practices

### Safe to Skip

| Rung | Safe to skip when... |
|------|---------------------|
| Rung 1 (Market Structure) | You've worked in this exact market for 3+ years |
| Rung 2 (Proxy Data) | You have direct customer access (why estimate when you can ask?) |
| Rung 3 (Interviews) | You ARE the customer and have 10+ peers who share the pain |
| Rung 4 (Behavioral) | You have an existing audience to test with (skip paid ads) |

### Never Skip

| Rung | Why it's dangerous to skip |
|------|---------------------------|
| Rung 5 (Money) | Verbal intent does not equal payment. Always test WTP with real money. |
| Rung 3 (if WTP is unvalidated) | "I think they'd pay" is not the same as "they told me they'd pay $X" |

### The One Rule

**If you skip rungs, you must still validate every hypothesis before committing to a full build.** Skipping a rung means getting that evidence from a different source, not ignoring it entirely.

```
Skipped Rung 1 because you know the market?
  → Document your knowledge as evidence in Venture Thesis Engine.

Skipped Rung 4 because no budget for ads?
  → Validate behavioral interest through free methods (content, outreach, communities).
```

---

## Configuration in Practice

### Example: "I know HR tech, just test this specific product idea"

```yaml
validation_config:
  venture: matchhire
  preset: domain_expert
  budget: $200
  timeline_target: 2_weeks
  
  overrides:
    - hypothesis: market_exists
      confidence: 0.95
      evidence: "10 years in HR tech, ran recruiting at 3 companies"
      
  rungs:
    market_structure: { mode: skip }
    proxy_data: { mode: skip }
    verbal_signals:
      mode: run
      sample_size: 8
      skip_sourcing: true  # Using my network
    behavioral_signals:
      mode: partial
      run: [landing_page, content_test]
      skip: [ad_campaigns]
    money_signals:
      mode: run

  execution_mode: custom
  stages:
    - sequential: [3]      # Interviews first (confirm specific pain + WTP)
    - parallel: [4, 5]     # Then landing page + pre-sale simultaneously
```

### Example: "Zero budget, just me and my laptop"

```yaml
validation_config:
  venture: ai_tutoring
  preset: zero_budget
  budget: $0
  timeline_target: 3_weeks
  
  rungs:
    market_structure:
      mode: run  # All free (Google Trends, Reddit, G2 scraping)
    proxy_data:
      mode: partial
      run: [search_demand, alternative_solutions, time_cost_estimation]
      skip: [competitive_pricing_semrush]  # Would need paid tool
    verbal_signals:
      mode: run
      sample_size: 10
      sourcing: [personal_network, reddit_posts, twitter_dm]  # Free
    behavioral_signals:
      mode: partial
      run: [content_test]  # Free: post content, measure response
      skip: [landing_page, ad_campaigns]
    money_signals:
      mode: run
      method: direct_dm_presale  # Email/DM people asking for payment
```

### Example: "4th venture, just confirm fast"

```yaml
validation_config:
  venture: sales_automation
  preset: speed_run
  budget: $100
  timeline_target: 5_days
  
  overrides:
    - hypothesis: problem_exists
      confidence: 0.9
      evidence: "Built 3 similar products, same pain confirmed every time"
    - hypothesis: channel_exists
      confidence: 0.85
      evidence: "Pattern Library shows LinkedIn + content works for B2B SMB"
      
  rungs:
    market_structure: { mode: skip }
    proxy_data: { mode: skip }
    verbal_signals: { mode: skip }
    behavioral_signals:
      mode: partial
      run: [landing_page]  # Just the page, no ads
    money_signals:
      mode: run  # The only thing that truly matters

  execution_mode: parallel  # Run remaining rungs at once
```

---

## How This Connects to Other Modules

| Module | Role in Configuration |
|--------|------|
| **Venture Thesis Engine (#27)** | Stores config, tracks which rungs were skipped and why, monitors if skips were justified |
| **Customer Discovery Engine (#26)** | Adapts interview count, sourcing method, and analysis depth based on config |
| **Market & Signal Intelligence (#25)** | Skips paid data sources when budget is $0, uses free alternatives |
| **A/B Test & Optimization (#32)** | Adjusts sample sizes and test duration based on budget/timeline constraints |
| **Tool Forge (#10)** | Only activates integrations needed for configured rungs (no ad platform API if ads are skipped) |
| **Cost Optimizer (#35)** | Enforces budget caps, suggests cheapest methods that still give valid signal |
| **Pattern & Template Library (#38)** | Recommends presets based on what worked for similar ventures in the past |
| **Meta-Learning & Flywheel (#39)** | Tracks outcomes per configuration — learns which skips are safe vs. risky |
