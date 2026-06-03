# Integrations: Tool Forge Architecture

## Three Tiers of Automation

Every integration operates at one of three automation tiers. The tier determines the human effort required:

### Tier 1: Fully Agentic

Agent decides, executes, monitors, and adjusts. Zero human effort after initial setup.

- Agent pulls Google Trends data every morning
- Agent adjusts ad bids based on CPA targets
- Agent deploys updated landing page variant
- Agent sends scheduled email sequences

### Tier 2: Agent Proposes, Human Approves

Agent does all preparation and presents a decision for one-click approval. ~30 seconds of human effort.

- Agent drafts ad campaign, sends Slack message: "Launch this campaign? [Approve] [Edit] [Reject]"
- Agent writes cold outreach batch, sends preview: "Send to 50 targets? [Approve]"
- Agent proposes budget increase: "Experiment performing well. Increase from $50 → $150? [Approve]"

### Tier 3: Human Must Do

One-time account setup, legal agreements, or actions requiring the founder's identity. Typically 5-15 minutes per service, done once.

- Create Google Ads account and add billing
- Accept Meta Business Manager terms of service
- Connect personal LinkedIn account
- Sign Stripe Terms of Service

---

## Integration Categories

### Data & Research (mostly Tier 1)

| Service | What It Does | API | Tier | Cost |
|---------|-------------|-----|------|------|
| Google Trends | Search interest over time, geographic breakdown, related queries | pytrends (unofficial) | 1 | Free |
| SEMrush/Ahrefs | Keyword volumes, competitor organic/paid analysis, backlink data | Paid REST API | 1 | $120-400/mo |
| Reddit | Forum analysis, pain detection, sentiment tracking | Reddit API (OAuth2) | 1 | Free |
| G2/Capterra | Competitor reviews, feature comparison, satisfaction scores | Scraping + limited API | 1 | Free-$200/mo |
| BLS/Census | Labor statistics, industry data, demographic data, market sizing | Free public REST APIs | 1 | Free |
| Crunchbase | Funding rounds, competitor intelligence, market maps | Paid REST API | 1 | $300/mo |
| LinkedIn data | Company/people data, ICP targeting, hiring signals | API (TOS-sensitive) | 2 | Varies |
| Job boards (Indeed, LinkedIn Jobs) | Job market data, role demand, skill requirements | Various REST APIs | 1 | Free-$100/mo |
| arxiv/Semantic Scholar | Academic papers, technical feasibility, state-of-the-art | Free REST APIs | 1 | Free |
| ProductHunt/HackerNews | Launch data, community sentiment, early adopter signals | APIs + scraping | 1 | Free |
| App Store/Play Store | Download estimates, ratings, review analysis | Various APIs | 1 | Free-$50/mo |

---

### Ad Platforms (Tier 2 → Tier 1)

Initial campaign launch requires approval (Tier 2). Once running, optimization is fully agentic (Tier 1).

#### Google Ads

| Aspect | Details |
|--------|---------|
| **Autonomous (Tier 1)** | Bid adjustments (CPA targets), pause underperforming keywords/ads, scale winning ad groups, create new keyword variants, adjust day-parting, geographic bid modifiers, negative keyword additions |
| **Needs Approval (Tier 2)** | Initial campaign brief and structure, first creative batch, budget above ceiling ($X/day), new audience targeting strategies, brand term bidding decisions |
| **One-Time Setup (Tier 3)** | Create Google Ads account (~5 min), add billing/payment method (~3 min), apply for Developer Token (~10 min, may take days to approve), link Google Analytics (~2 min) |
| **API Capabilities** | Campaign CRUD, ad group management, keyword management, bidding strategies, responsive search ads, reporting/analytics, keyword planner, audience management |

#### LinkedIn Ads

| Aspect | Details |
|--------|---------|
| **Autonomous (Tier 1)** | Bid optimization, pause underperforming creatives, audience expansion based on converters, budget pacing adjustments, A/B test rotation |
| **Needs Approval (Tier 2)** | Initial campaign objectives and targeting, creative copy/images, budget above ceiling, InMail content, new audience segments |
| **One-Time Setup (Tier 3)** | Create Campaign Manager account (~5 min), add payment method (~3 min), request Marketing API access (~10 min, may require LinkedIn rep approval) |
| **API Capabilities** | Campaign CRUD, audience building (job title, company, seniority, skills), creative management, lead gen forms, reporting, conversion tracking |

#### Meta Ads (Facebook/Instagram)

| Aspect | Details |
|--------|---------|
| **Autonomous (Tier 1)** | Creative rotation, audience refinement via lookalikes, bid adjustments, placement optimization, ad scheduling, budget allocation across ad sets |
| **Needs Approval (Tier 2)** | Initial campaign structure, first creatives, new audience definitions, budget above ceiling, any content involving claims/testimonials |
| **One-Time Setup (Tier 3)** | Create Business Manager account (~5 min), verify business (~10 min, may take days), add payment method (~3 min), request Marketing API access (~5 min), install Meta Pixel on landing pages (~5 min) |
| **API Capabilities** | Campaign CRUD, creative testing at scale, custom/lookalike audiences, dynamic creative optimization, detailed reporting, conversion API, catalog management |

---

### Deployment & Product (mostly Tier 1)

| Service | What It Does | Tier | Key Capabilities |
|---------|-------------|------|------------------|
| Vercel | Deploy Next.js apps, environment management, preview deploys | 1 | Deploy via API, environment variables, domain management, serverless functions, edge config |
| Stripe | Products, pricing, checkout, subscriptions, billing | 1 (after setup) | Create products/prices, generate checkout sessions, manage subscriptions, webhooks, billing portal, invoices |
| Resend/SendGrid | Email sequences, transactional mail, templates | 1 | Send transactional email, manage templates, track opens/clicks, suppression lists, scheduled sends |
| PostHog/Mixpanel | Event tracking, funnels, cohorts, feature flags | 1 | Define events, create funnels, segment users, feature flags, session recording config, A/B test assignment |
| Cal.com/Calendly | Scheduling, availability, interview booking | 1 | Create event types, manage availability, embed scheduling, webhooks on booking, automated reminders |
| Supabase/PlanetScale | Database, auth, storage, realtime | 1 | Schema management, user auth, file storage, realtime subscriptions, edge functions |

---

### Communication (Tier 1-2)

| Service | What It Does | Tier | Notes |
|---------|-------------|------|-------|
| Slack | Bot integration, notifications, approval workflows | 1 (notifications) / 2 (outreach) | Push updates, collect approvals via buttons, thread conversations, file sharing |
| Email (outreach) | Cold outreach to interview targets, follow-ups | 2 (approve first batch) | AI drafts sequences, human approves messaging, then AI sends + optimizes timing |
| LinkedIn messaging | Interview scheduling, networking, relationship building | 2 | Always human-approved; TOS risk requires oversight |
| Twilio/SMS | Appointment reminders, urgent notifications | 1 (reminders) / 2 (outreach) | Transactional = auto, marketing = approval required |

---

## How Tool Forge Manages Integrations

### Credential Vault

- All credentials stored encrypted at rest (AES-256)
- OAuth tokens stored per venture (Venture A's Google Ads ≠ Venture B's)
- API keys rotated on schedule where supported
- Scoped access — agents only get credentials for their assigned venture
- Audit log of every credential access

### Auto-Refresh Expired Tokens

- Background job monitors token expiry timestamps
- Refreshes OAuth tokens 15 minutes before expiry
- Alerts founder if refresh fails (requires re-auth)
- Graceful degradation — queues requests during refresh window

### Rate Limit Handling

- Per-service rate limit tracking (requests/minute, requests/day)
- Exponential backoff on 429 responses
- Request queuing with priority (time-sensitive requests processed first)
- Distributed rate limiting across multiple ventures sharing a service
- Pre-flight rate limit checking before batched operations

### Failure Recovery

- Automatic retries with exponential backoff (3 attempts, then alert)
- Fallback services where available (Resend → SendGrid, SEMrush → Ahrefs)
- Circuit breaker pattern (stop calling a service that's consistently failing)
- Dead letter queue for failed operations (retry manually or discard)
- Incident logging with root cause tracking

### Cost Tracking

- Per-integration cost tracking (API calls, spend, resource usage)
- Per-venture cost attribution
- Budget alerts when approaching limits
- Monthly cost reports with trend analysis
- Cost-per-insight metrics (how much did this data cost vs. value delivered?)

### Usage Analytics

- Which integrations are used most frequently
- Which integrations fail most often (reliability scoring)
- Time-to-value per integration (how quickly does data become insight?)
- Unused integration detection (paying for something never queried)

---

## Policy Engine Integration

The Policy Engine acts as a governance layer between agents and Tool Forge. Every action passes through policy checks before execution.

### Budget Ceilings

- Per-venture daily/weekly/monthly spend limits
- Per-integration spend limits (e.g., max $50/day on Google Ads)
- Auto-block if ceiling exceeded (agent cannot override)
- Alert founder with option to increase ceiling

### Approval Requirements

Configurable per tool, per venture, per action type:

```
google_ads:
  create_campaign: requires_approval
  adjust_bids: autonomous (within ±20%)
  pause_ad: autonomous
  increase_budget: requires_approval (if > $50 increase)
  
stripe:
  create_product: requires_approval
  create_checkout: autonomous
  issue_refund: requires_approval (if > $50)
```

### Brand Safety

- Content review before any public-facing deployment
- Tone/voice consistency checking against brand guidelines
- Claim verification (no unsupported claims in ad copy)
- Competitor mention policy enforcement
- Image/creative brand alignment scoring

### GDPR/Compliance Checks

- PII detection before data storage or transmission
- Consent verification before outreach
- Data retention policy enforcement
- Right-to-erasure request handling
- Cross-border data transfer checks

### Escalation Rules

- Two failed attempts → escalate to founder
- Budget anomaly detected → immediate Slack alert
- Compliance risk detected → block action + alert
- Service outage → notify + activate fallback
- Unexpected results (conversion spike/crash) → flag for review

---

## One-Time Setup Table

Complete list of accounts and services to configure before the platform is fully operational:

| Service | Setup Action | Time | Tier 3 Notes |
|---------|-------------|------|--------------|
| Google Ads | Create account, add billing, request dev token | 15 min + approval wait | Dev token approval can take 1-5 business days |
| Meta Ads | Create Business Manager, verify business, add payment | 15 min + verification wait | Business verification can take 1-3 days |
| LinkedIn Ads | Create Campaign Manager, request API access | 10 min + approval wait | API access may require LinkedIn rep |
| Stripe | Create account, verify identity, add bank | 10 min | Instant for most countries |
| Vercel | Create account, connect GitHub | 5 min | — |
| SEMrush or Ahrefs | Subscribe, generate API key | 5 min | Paid subscription required |
| Crunchbase | Subscribe, generate API key | 5 min | Paid subscription required |
| Slack | Create workspace, install bot app | 10 min | — |
| Resend/SendGrid | Create account, verify domain, add DNS records | 15 min | DNS propagation can take hours |
| PostHog/Mixpanel | Create project, install snippet | 5 min | — |
| Cal.com | Create account, set availability | 5 min | — |
| Reddit | Register app, get OAuth credentials | 5 min | — |

**Total active setup time: ~2 hours**
(Some services have approval/verification delays of 1-5 days, but these run in parallel and require no active effort.)

---

## The Realistic Automation Flow

### Example: "Validate SMB Hiring Pain with $300 Ad Budget"

Here's exactly what happens, step by step, showing which steps are agentic vs. need approval:

---

**Phase 1: Market Research (Rung 1-2) — Fully Agentic**

| Step | Action | Actor | Time |
|------|--------|-------|------|
| 1 | Pull Google Trends data for "hiring software SMB", "applicant tracking small business" | Agent | 2 min |
| 2 | Pull SEMrush keyword volumes for 50 related terms | Agent | 3 min |
| 3 | Analyze 200 G2 reviews of competing ATS tools | Agent | 10 min |
| 4 | Pull BLS data on SMB employment patterns | Agent | 2 min |
| 5 | Scan Reddit r/smallbusiness, r/recruiting for pain posts | Agent | 5 min |
| 6 | Compile market structure report with kill/proceed recommendation | Agent | 5 min |
| 7 | **Founder reviews 2-page summary, decides to proceed** | **Human** | **5 min** |

**Human effort: 5 minutes** (read summary, say "proceed")

---

**Phase 2: Interview Prep (Rung 3 setup) — Mostly Agentic**

| Step | Action | Actor | Time |
|------|--------|-------|------|
| 8 | Generate interview guide (15 questions, probes, WTP section) | Agent | 3 min |
| 9 | Find 40 SMB hiring managers via LinkedIn/Apollo matching ICP | Agent | 10 min |
| 10 | Draft personalized outreach messages (3 variants) | Agent | 5 min |
| 11 | **Founder reviews guide + outreach, approves** | **Human** | **10 min** |
| 12 | Send outreach to first batch of 40 targets | Agent | 2 min |
| 13 | Manage scheduling via Cal.com as responses come in | Agent | Ongoing |

**Human effort: 10 minutes** (review and approve)

---

**Phase 3: Interviews (Rung 3) — Human-Led**

| Step | Action | Actor | Time |
|------|--------|-------|------|
| 14 | **Conduct 8-12 interviews (30 min each)** | **Human** | **6 hours** |
| 15 | Transcribe and analyze all interviews | Agent | 15 min |
| 16 | Extract pain scores, WTP data, objections, quotes | Agent | 5 min |
| 17 | Generate insight report with hypothesis confidence updates | Agent | 5 min |
| 18 | **Founder reviews insights, decides to proceed to Rung 4** | **Human** | **15 min** |

**Human effort: ~6.5 hours** (interviews are irreplaceable)

---

**Phase 4: Landing Page + Ads (Rung 4) — Mostly Agentic**

| Step | Action | Actor | Time |
|------|--------|-------|------|
| 19 | Generate landing page copy from interview insights | Agent | 5 min |
| 20 | Build and deploy landing page to Vercel | Agent | 10 min |
| 21 | Design Google Ads campaign (keywords, ad copy, targeting) | Agent | 10 min |
| 22 | Design LinkedIn Ads campaign (audience, creative) | Agent | 10 min |
| 23 | **Founder reviews landing page + ad campaigns** | **Human** | **15 min** |
| 24 | **Founder approves: [Launch Google] [Launch LinkedIn]** | **Human** | **30 sec** |
| 25 | Launch campaigns, set up conversion tracking | Agent | 5 min |
| 26 | Monitor performance, adjust bids, pause underperformers | Agent | Ongoing (7 days) |
| 27 | Daily Slack summary: spend, clicks, conversions, CPA | Agent | Auto |
| 28 | Mid-flight optimization: new ad variants, bid changes | Agent | Ongoing |
| 29 | **Founder receives end-of-experiment report** | **Human** | **10 min** |

**Human effort: ~25 minutes** (review, approve, read report)

---

**Phase 5: Money Test (Rung 5) — Mostly Agentic**

| Step | Action | Actor | Time |
|------|--------|-------|------|
| 30 | Create Stripe product + 3 pricing tiers based on WTP data | Agent | 5 min |
| 31 | Update landing page with pricing + checkout | Agent | 5 min |
| 32 | Set up pricing A/B test (different prices to different segments) | Agent | 5 min |
| 33 | **Founder approves pricing strategy** | **Human** | **5 min** |
| 34 | Drive traffic to checkout page (reuse winning ads) | Agent | Ongoing |
| 35 | Monitor conversions, cancellations, revenue | Agent | Ongoing (7 days) |
| 36 | Generate final validation report with go/no-go recommendation | Agent | 10 min |
| 37 | **Founder makes final decision: build, kill, or pivot** | **Human** | **30 min** |

**Human effort: ~35 minutes** (strategy approval + final decision)

---

### Total Effort Summary

| Category | Time |
|----------|------|
| Total calendar time | ~4 weeks |
| Total founder active time | ~8 hours |
| Of which: interviews | ~6 hours |
| Of which: reviews/approvals | ~1.5 hours |
| Of which: strategic decisions | ~30 minutes |
| Total cost | ~$300 (ads) + $0-50 (tools) |
| Agent autonomous work | ~60 hours equivalent |

**The founder's 8 hours replaced what would traditionally take 80-120 hours of solo work.**
