# Validation Framework: The Evidence Ladder

## Philosophy

The Evidence Ladder is System 5's (Product & Market Intelligence) systematic approach to validating whether a venture should exist. It embodies five core principles:

1. **Cheapest evidence first.** Never spend $500 when a $0 data pull would kill the idea. Every dollar spent on a dead idea is a dollar stolen from a live one.

2. **Kill early, kill cheap.** The goal is not to prove an idea works — it's to find the fastest reason it won't. A "no" at Rung 1 saves weeks of wasted effort. Celebrate kills.

3. **Triangulation over single data points.** No single signal is conclusive. Market size alone means nothing. Search demand alone means nothing. Three weak signals pointing the same direction beat one strong signal.

4. **Escalating commitment (from potential customers).** Each rung demands more from the market: attention → time → intent → money. If commitment drops off at any rung, the signal is clear.

5. **AI accelerates every rung.** Agents compress research from days to hours, generate interview guides from data, build landing pages in minutes, and optimize campaigns autonomously. The founder's scarce resource is judgment, not labor.

---

## The Evidence Ladder

### Rung 1: Market Structure

| Attribute | Value |
|-----------|-------|
| Cost | $0 |
| Time | 2-4 hours |
| Automation | ~95% agentic |
| Modules | Market & Signal Intelligence |

**What you're answering:** Is the market big enough, unhappy enough, and ready enough?

**Activities:**

- **Market size analysis (TAM/SAM/SOM)** — Top-down from industry reports, bottom-up from unit economics. Agent pulls from BLS, Census, Statista, and triangulates.
- **Existing spend analysis** — What do people pay today for the closest alternative? If the answer is $0 and they're not in pain, stop here.
- **Dissatisfaction signals** — Reviews (G2, Capterra, App Store), complaints (Reddit, Twitter, forums), support tickets (if accessible). Agent scores volume and intensity.
- **Timing signals** — Why now? Regulatory change, technology inflection, demographic shift, pandemic aftermath, platform policy change. No "why now" = uphill battle.
- **Competitive gap analysis** — Map incumbents on a 2x2 (capability vs. price, or automation vs. customization). Find the whitespace. If there's no whitespace, stop.

**Kill signals:**
- Market too small (TAM < $100M for software, < $1B for marketplace)
- No existing spend (people don't pay for this category today)
- Strong incumbent with no clear gap
- Bad timing (too early, too late, or no catalyst)

---

### Rung 2: Proxy Data

| Attribute | Value |
|-----------|-------|
| Cost | $0-50 |
| Time | 4-8 hours |
| Automation | ~95% agentic |
| Modules | Market & Signal Intelligence, Dataset Scout capabilities |

**What you're answering:** Do people actively seek solutions, and is this technically buildable?

**Activities:**

- **Search demand** — Google Trends trajectory (growing, flat, declining?), SEMrush/Ahrefs keyword volumes for problem-aware and solution-aware queries.
- **Behavioral proxies** — Job postings (are companies hiring for this problem?), app store data (downloads/ratings of adjacent tools), social media trends (growing communities?).
- **Time/cost estimation** — Quantify the pain in dollars. "SMBs spend 8 hours/week on X at $50/hr effective cost = $20,800/year pain per company."
- **Alternative solution analysis** — What are people actually doing today? Spreadsheets? Manual processes? Hiring people? Ignoring the problem?
- **Technical feasibility check** — Can AI actually do this with current capabilities? What's the accuracy floor? Are there training data constraints?
- **Competitive pricing analysis** — What do adjacent solutions charge? What price band is the market trained on?

**Kill signals:**
- No search demand (< 1,000 monthly searches for core problem terms)
- Pain too small in dollars (< $1,000/year per customer for B2B, < $50/year for B2C)
- Technically infeasible (AI accuracy too low for the use case, no training data available)
- Current solutions good enough (high NPS on existing tools, low switching motivation)

---

### Rung 3: Verbal Signals

| Attribute | Value |
|-----------|-------|
| Cost | $100-500 |
| Time | 1-2 weeks |
| Automation | ~40% agentic |
| Modules | Customer Discovery Engine, Venture Thesis Engine |

**What you're answering:** Do real humans confirm the pain, and would they pay to solve it?

**Activities:**

- **Customer interview design** — AI generates optimized interview guides based on Rung 1-2 findings. Questions are structured to avoid leading, probe for severity, and surface willingness-to-pay without anchoring.
- **Target sourcing** — AI finds ideal interview candidates via LinkedIn/Apollo based on ICP criteria. Generates personalized outreach. Manages scheduling.
- **Interview conducting** — HUMAN. This stays manual. Nuance, follow-up questions, emotional reading, and trust-building cannot be delegated. 8-12 interviews minimum.
- **Transcript analysis** — AI extracts: pain statements, direct quotes, severity scores (1-10), frequency of mention, emotional intensity markers, and cross-interview patterns.
- **Willingness-to-pay probing** — "What would you pay?" is useless. Instead: "What do you currently spend?", "What would you give up to solve this?", "If this existed at $X, would you buy it today?"
- **Emotional intensity detection** — AI flags interviews where founders hear frustration, anger, resignation, or desperation. Mild inconvenience ≠ venture-worthy pain.
- **Objection cataloging** — Every "but..." gets logged. Trust objections, switching cost objections, budget objections, authority objections. Each needs a counter-strategy or is a kill signal.

**Kill signals:**
- Low severity (average < 6/10 across interviews)
- No emotional energy ("yeah, it's annoying, but whatever")
- $0-50 WTP (not worth building a business around)
- "I'd never trust AI for this" (fundamental adoption barrier)
- Can't find interview targets (market doesn't congregate, ICP too vague)

---

### Rung 4: Behavioral Signals

| Attribute | Value |
|-----------|-------|
| Cost | $200-1,000 |
| Time | 1-2 weeks |
| Automation | ~80% agentic |
| Modules | Offer Design Engine, A/B Test & Optimization, Tool Forge (ad platform APIs) |

**What you're answering:** Will people take action (not just talk) when presented with a solution?

**Activities:**

- **Landing page test** — AI generates copy from interview insights, designs page structure, deploys to Vercel. Founder approves messaging/positioning. Drives traffic via ads.
- **Ad campaigns** — AI designs targeting (from ICP), writes creative variants, sets bid strategies, and optimizes in real-time. Founder approves initial brief and budget ceiling.
- **Wizard-of-Oz / concierge test** — Founder delivers the "product" manually with AI assist (AI drafts deliverables, founder reviews and sends). Tests whether the *outcome* is valued, independent of automation.
- **Content/community signal** — AI generates content (blog posts, tweets, guides) targeting the problem space. Measures organic pull: shares, saves, comments, DMs asking "where can I buy this?"

**Kill signals:**
- < 2% landing page conversion (message/market mismatch)
- No real commitment (email signups but zero engagement after)
- "Meh" reaction (no shares, no forwards, no "this is exactly what I need")
- Zero organic interest (content gets crickets, no inbound)
- Ad costs unsustainable (CPA > LTV at any reasonable conversion rate)

---

### Rung 5: Money Signals

| Attribute | Value |
|-----------|-------|
| Cost | $0-500 |
| Time | 1-2 weeks |
| Automation | ~70% agentic |
| Modules | Tool Forge (Stripe), A/B Test & Optimization, Cost Optimizer |

**What you're answering:** Will people give you money before the product is fully built?

**Activities:**

- **Pre-sale with credit card** — Stripe checkout or waitlist with payment. Not "enter your email" — "enter your credit card." The ultimate signal of intent.
- **Pricing sensitivity testing** — Different prices shown to different segments (geographic, firmographic, or random). Find the demand curve. Where does conversion collapse?
- **Upgrade/expansion signals** — If offering a pilot/beta, do early users ask for more? Request features? Refer others? Increase usage?

**Kill signals:**
- 0 conversions (talked a big game, won't pay)
- Immediate cancellations (buyer's remorse = value not understood or not delivered)
- Only converts at trivial price (willing to pay $5 but not $50 = hobby, not business)
- No expansion behavior (use it once, forget it)

---

## Hypothesis Management

The Venture Thesis Engine maintains a living hypothesis graph for each venture. This is the intellectual scaffolding that the Evidence Ladder populates.

### Hypothesis Types

| Type | Question | Example |
|------|----------|---------|
| `problem_exists` | Is this a real, painful problem? | "SMB hiring managers waste 10+ hrs/week screening unqualified candidates" |
| `willingness_to_pay` | Will they pay to solve it? | "SMBs will pay $200-500/mo for AI-assisted candidate screening" |
| `solution_works` | Can we actually solve it? | "GPT-4 can screen resumes with 85%+ accuracy vs human reviewers" |
| `channel_exists` | Can we reach them efficiently? | "LinkedIn Ads can reach SMB hiring managers at < $50 CPA" |
| `unit_economics_work` | Can we make money? | "LTV:CAC > 3:1 at $300/mo price point" |

### Evidence Linking

Every hypothesis is linked to specific evidence gathered at specific rungs:

```
Hypothesis: "SMBs will pay $200-500/mo"
├── Rung 2: Competitors charge $150-800/mo (pricing analysis)
├── Rung 3: 7/12 interviewees said $200-300 "reasonable" (interviews)
├── Rung 4: Landing page converted at 4.2% at $249/mo (behavioral)
└── Rung 5: 3 pre-sales at $299/mo (money signal)
    → Confidence: 82% (HIGH)
```

### Confidence Scoring

Confidence updates after each rung using a Bayesian-inspired approach:

- **Prior:** Set at 50% (maximum uncertainty) when hypothesis is created
- **Update magnitude:** Depends on evidence quality (money > behavior > words > proxy > desk research)
- **Direction:** Supporting evidence increases, contradicting evidence decreases
- **Threshold:** > 75% = proceed, < 25% = kill, 25-75% = gather more evidence

### Kill Signal Monitoring

The system automatically:
- Flags when 2+ kill signals trigger at any rung
- Alerts the founder via Slack with a structured kill recommendation
- Presents the evidence and asks for a decision: kill, pivot, or override with rationale
- Logs the decision for pattern learning

### Pivot Detection

When evidence contradicts the primary thesis but suggests an adjacent opportunity:
- "Problem exists but in a different segment" → ICP pivot
- "Problem exists but different solution needed" → Solution pivot
- "Different problem is actually bigger" → Problem pivot
- System generates a new hypothesis set for the pivot and resets relevant rungs

---

## Automation Breakdown

| Rung | % Agentic | Human Role | Why Human is Needed |
|------|-----------|------------|---------------------|
| 1: Market Structure | ~95% | Review conclusions, apply domain intuition | Agents may miss context, founder knows their domain |
| 2: Proxy Data | ~95% | Validate technical feasibility judgment | Founder has builder context agents lack |
| 3: Verbal Signals | ~40% | Conduct interviews, make judgment calls | Trust, nuance, follow-up instinct, relationship building |
| 4: Behavioral Signals | ~80% | Approve messaging/creative, deliver concierge | Brand judgment, manual delivery quality |
| 5: Money Signals | ~70% | Set pricing strategy, approve offers | Pricing is strategic, affects positioning |

**Where human judgment is irreplaceable:**
- Reading emotional subtext in interviews
- Making "taste" decisions on brand/messaging
- Deciding when to kill vs. pivot (ultimately a judgment + risk tolerance call)
- Evaluating technical feasibility at the frontier
- Making strategic pricing decisions that affect long-term positioning

---

## The Flywheel in Validation

Validating Venture 3 is dramatically faster than Venture 1. Here's why:

### Pattern Library Accumulation

After validating 2 ventures, the Pattern Library has learned:
- Which market signals actually predicted success/failure
- Which interview questions yielded the most useful data
- Which ad creative structures converted best
- Which pricing frames produced the most accurate WTP data
- Which kill signals were real vs. noise

### Cached Intelligence

- **Market Intelligence** has already indexed adjacent markets, competitors, and data sources. Rung 1 for Venture 3 starts from a warm cache, not cold.
- **Customer Discovery** has refined its transcript extraction models on your specific market's language and pain patterns.
- **Offer Design** knows which layouts, headline structures, and CTA placements convert for your audience type.
- **A/B Testing** has baseline conversion rates for your market, so statistical significance arrives faster.

### Concrete Time Compression

| Activity | Venture 1 | Venture 3 | Why Faster |
|----------|-----------|-----------|------------|
| Market sizing | 3 hours | 45 min | Adjacent market, cached data sources |
| Interview guide | 2 hours | 20 min | Refined question bank, known anti-patterns |
| Landing page | 4 hours | 30 min | Proven templates, known messaging patterns |
| Ad optimization | 5 days | 2 days | Known audiences, proven creative structures |
| Pricing test | 1 week | 3 days | Baseline data, known price sensitivity curves |

### The Compounding Effect

Each validated (or killed) venture makes the *platform itself* smarter. This is not just "the founder learned something" — it's encoded in the system's models, templates, and decision logic. The flywheel spins faster with every revolution.

---

## See Also

- **[Validation Configuration & Overrides](validation-config.md)** — How to skip rungs, set budget caps, use presets, inject manual confidence, and run rungs in parallel or inverted order.
