# Interaction Model: How You Work With the Platform

## The Three Channels

The platform meets you where you are through three complementary interfaces. Same underlying brain, different UX optimized for different contexts.

### Slack — Reactive

The system pushes to you. You react.

- Notifications arrive when something needs attention
- Quick approvals via buttons (30 seconds)
- Status checks via natural language
- Brief commands ("pause the experiment", "show me today's spend")
- Mobile-friendly for on-the-go decisions

### Web App — Proactive

You go there intentionally to think, design, and build.

- Deep work: designing agents, reviewing analytics, configuring ventures
- Visual tools: graphs, dashboards, experiment results, flow builders
- Conversational co-pilot sidebar for context-aware assistance
- Complex configuration that needs visual feedback

### CLI — Automation

For power users and scripted workflows.

- Batch operations across ventures
- Cron-scheduled tasks
- Scripting and piping with other tools
- Programmatic access to all platform capabilities
- CI/CD integration

---

## Interaction Modes

| Mode | What It Is | Best Channel | Why |
|------|-----------|--------------|-----|
| **Command** | "Launch validation for MatchHire" | Any (Slack, App, CLI) | Simple instruction, works everywhere |
| **Approve** | "Yes, launch that campaign" | Slack (quick) or App (complex) | Quick = Slack button; complex = App for full context |
| **Monitor** | "How's the experiment going?" | Slack (quick) or App (detailed) | Quick status = Slack; deep dive = App dashboard |
| **Deep work** | Design agents, review analytics, configure flows | App only | Needs visual tools, screen real estate, focus |
| **On the go** | Quick approvals from mobile | Slack | Push notification → tap approve → done |
| **Automation** | Scheduled tasks, batch operations | CLI | Scriptable, cron-compatible, composable |

---

## Slack Architecture

### Workspace Structure

| Channel | Purpose | Traffic Level |
|---------|---------|---------------|
| `#flywheel-general` | Platform-wide updates, system health, daily summaries | Low (1-3/day) |
| `#[venture]-ops` | Per-venture operations, experiment updates, results | Medium (5-15/day per active venture) |
| `#approval-queue` | All pending approvals in one place | Medium (varies) |
| `#experiments` | Experiment launches, completions, and results | Low-medium |
| `#costs` | Spend alerts, budget warnings, daily cost summaries | Low (1-2/day) |

### Bot Capabilities

**Natural language understanding:**
```
You: "How's MatchHire doing?"
Bot: MatchHire validation is at Rung 4 (Behavioral Signals).
     Landing page: 3.8% conversion (good)
     Google Ads: $47 spent, 12 clicks, 2 conversions
     LinkedIn Ads: $38 spent, 8 clicks, 1 conversion
     Recommendation: Continue for 4 more days to reach significance.
```

**Button interactions:**
```
Bot: 🔔 Campaign ready for launch
     Venture: MatchHire
     Platform: Google Ads
     Budget: $50/day for 7 days
     Targeting: SMB hiring managers, US, 10-200 employees
     
     [✓ Approve] [✏️ Edit] [✗ Reject] [👁️ View Details]
```

**Modal dialogs (for more complex input):**
- Budget adjustment with custom amount
- Campaign brief editing
- Interview candidate selection
- Pricing tier configuration

**DM with bot for private queries:**
- Financial data you don't want in shared channels
- Strategic questions about pivots
- Personal productivity queries ("what should I focus on today?")

### Example Interactions

**Morning brief (auto-sent at 8 AM):**
```
Bot: Good morning. Here's your daily brief:

     Active ventures: 3
     Pending approvals: 2
     
     MatchHire: Experiment running (day 3/7), on track
     DataClean: Interviews scheduled (3 today)
     PriceBot: Rung 1 complete, ready for Rung 2 [Approve]
     
     Total spend yesterday: $89
     Budget remaining this week: $411
```

**Campaign approval:**
```
Bot: LinkedIn campaign for MatchHire is ready.
     
     Audience: 45,000 SMB hiring managers
     Creative: 3 variants (problem-aware messaging)
     Budget: $30/day × 7 days = $210 total
     Expected: 20-40 clicks, 2-5 conversions
     
     [✓ Launch] [👁️ Preview Creatives] [✏️ Adjust Budget]
```

**Status check:**
```
You: "what's the CPA on matchhire google ads?"
Bot: MatchHire Google Ads CPA: $23.50 (target: $30)
     Running for 3 days. 4 conversions from 18 clicks.
     Trending well — no action needed.
```

---

## Web App Co-pilot Sidebar

### Always Present, Collapsible

The co-pilot sidebar lives on the right side of every page in the web app. It can be collapsed to a thin strip or expanded to a full conversational panel.

### Context-Aware

The sidebar knows which page and venture you're currently viewing:

- **On Dashboard:** "Ask me about any venture's status, or say 'what needs my attention?'"
- **On Agent Graph:** "I can explain any agent's role, show its recent activity, or help you configure it."
- **On Experiment page:** "I can explain these results, suggest next steps, or help you design a follow-up test."

### Seamless Escalation

The sidebar can escalate from chat to visual tools without breaking flow:

```
You: "Show me how MatchHire's conversion changed over time"
Sidebar: [Renders inline chart showing conversion rate by day]
         Conversion started at 2.1% and improved to 4.2% after 
         the headline change on Day 3. The new variant is winning
         with 94% confidence.
         
         [Open full experiment dashboard →]
```

### Structured Output

Responses aren't just text — they include:
- **Embedded charts** (sparklines, bar charts, trend lines)
- **Approval cards** (same as Slack, but richer with previews)
- **Data tables** (sortable, filterable)
- **Links** (deep links to relevant pages, external URLs)
- **Action buttons** ("Run this", "Deploy that", "Schedule this")

### Example: Sidebar on Different Pages

**Dashboard page:**
```
You: "Which venture should I focus on today?"
Sidebar: Based on pending items and time-sensitivity:

         1. MatchHire — 2 approvals waiting (campaign + landing page)
            Impact: Blocking Rung 4 progress
         2. DataClean — Interview at 2 PM (prep recommended)
            Prep doc: [View interview guide →]
         3. PriceBot — No action needed today
         
         Estimated time needed: 25 minutes for approvals + 15 min prep
```

**Agent Graph page:**
```
You: "Why did Market Intelligence run 3 times yesterday?"
Sidebar: Market Intelligence triggered 3 runs:
         
         1. Scheduled daily trend check (routine)
         2. MatchHire competitor launched new feature (alert trigger)
         3. PriceBot market sizing refresh (you requested this Tuesday)
         
         All completed successfully. No anomalies.
         [View run logs →]
```

**Experiment page:**
```
You: "Is this result significant enough to act on?"
Sidebar: Not yet. Current stats:
         
         Variant A: 3.2% conversion (n=125)
         Variant B: 4.8% conversion (n=118)
         
         p-value: 0.12 (need < 0.05)
         Estimated days to significance: 3-4 more days
         
         Recommendation: Wait. Don't peek-and-decide.
```

---

## CLI Interface

### Key Commands

```bash
# Status
flywheel status                          # All ventures summary
flywheel status matchhire                # Specific venture detail
flywheel status --experiments            # All running experiments

# Approvals
flywheel approve                         # List pending approvals
flywheel approve 7                       # Approve item #7
flywheel approve --all                   # Approve all pending (use carefully)
flywheel reject 7 --reason "budget too high"

# Validation
flywheel validate matchhire --rung 2     # Start Rung 2 for MatchHire
flywheel validate matchhire --kill       # Kill venture with reason prompt
flywheel validate matchhire --pivot      # Initiate pivot workflow

# Ask (natural language)
flywheel ask "what's the CPA on matchhire google ads?"
flywheel ask "compare conversion rates across all ventures"

# Deploy
flywheel deploy matchhire-landing        # Deploy latest landing page
flywheel deploy --preview                # Deploy to preview URL only

# Experiments
flywheel experiment list                 # All experiments
flywheel experiment create --config exp.yaml
flywheel experiment stop matchhire-pricing-v2
flywheel experiment results matchhire-pricing-v2 --format json

# Cost
flywheel cost                            # Today's spend
flywheel cost --week                     # This week
flywheel cost --by-venture               # Breakdown by venture
flywheel cost --by-service               # Breakdown by integration
```

### Scriptability

```bash
# Morning automation script
#!/bin/bash
flywheel status --json | jq '.ventures[] | select(.pending_approvals > 0)'
flywheel cost --week --json | jq '.total'

# Batch operations
for venture in matchhire dataclean pricebot; do
  flywheel status $venture --json >> /tmp/daily-report.json
done

# Cron job: pause all ads if weekly budget exceeded
if [ $(flywheel cost --week --json | jq '.total') -gt 500 ]; then
  flywheel ask "pause all ad campaigns, weekly budget exceeded"
fi
```

### Output Formats

All commands support `--format` flag:
- `--format human` (default): Colored, formatted terminal output
- `--format json`: Machine-readable JSON
- `--format csv`: For spreadsheet/data tools
- `--format markdown`: For documentation/reports

---

## Conversation Router (Architecture)

The Conversation Router is the central nervous system that makes multi-channel interaction coherent.

### How It Works

```
┌─────────┐     ┌─────────┐     ┌─────────┐
│  Slack   │     │ Web App │     │   CLI   │
└────┬─────┘     └────┬────┘     └────┬────┘
     │                │               │
     └────────────────┼───────────────┘
                      │
              ┌───────▼───────┐
              │ Conversation  │
              │    Router     │
              └───────┬───────┘
                      │
          ┌───────────┼───────────┐
          │           │           │
    ┌─────▼────┐ ┌───▼────┐ ┌───▼──────┐
    │ Module   │ │ Agent  │ │ Context  │
    │ Dispatch │ │ Graph  │ │ Manager  │
    └──────────┘ └────────┘ └──────────┘
```

### Core Responsibilities

**1. Receive messages from any channel**
- Slack: via Bolt SDK event listener
- Web App: via WebSocket connection
- CLI: via REST API call

**2. Maintain conversation context per thread**
- Each Slack thread, app chat session, or CLI session has its own context
- Context includes: current venture focus, recent interactions, pending state
- Context persists across channel switches (start in Slack, continue in App)

**3. Route to the right module/agent**
- Intent classification: what does the user want? (status, approval, command, question)
- Entity extraction: which venture? which experiment? which integration?
- Module selection: which system module handles this?
- Agent delegation: which specialized agent should execute?

**4. Format responses per channel**
- **Web App:** Rich cards, embedded charts, interactive elements, full markdown
- **Slack:** Slack Block Kit (buttons, sections, context blocks), concise formatting
- **CLI:** Plain text or structured data (JSON/CSV), ANSI colors for human format

**5. Track approvals across channels**
- Approval given in Slack is immediately reflected in Web App and CLI
- No double-prompting — once approved anywhere, it's approved everywhere
- Audit trail records which channel and timestamp for every approval

**6. The "Founder-Facing Agent"**
- A meta-agent that knows about ALL modules and ALL ventures
- Acts as the unified interface personality across channels
- Maintains founder preferences (communication style, detail level, notification frequency)
- Learns which types of decisions founder wants more/less detail on

---

## Smart Routing Rules

The system intelligently decides which channel to use for each interaction type:

### Simple Approvals → Slack Buttons

**Rule:** If the decision requires < 30 seconds of thought and the context fits in a Slack message, don't make the user open the app.

Examples:
- "Launch this campaign?" → Slack button
- "Increase budget by $20?" → Slack button
- "Pause underperforming ad?" → Slack button

### Complex Reviews → Link to App from Slack

**Rule:** If the decision requires reading/reviewing substantial content, send a Slack notification with a deep link.

Examples:
- "Interview transcript ready for review" → Slack message + [Open in App →]
- "Landing page ready for approval" → Slack preview + [View full page →]
- "Experiment results ready" → Slack summary + [See detailed analysis →]

### Configuration Changes → App

**Rule:** If the action requires visual tools, multi-step forms, or spatial reasoning, route to the app.

Examples:
- Agent graph configuration
- Experiment design with multiple variables
- Budget allocation across ventures
- Policy engine rule editing

### Urgent Alerts → Slack Push Notification

**Rule:** If something requires immediate attention (budget exceeded, service down, kill signal detected), push notification regardless of time.

Examples:
- "Budget ceiling hit — ads paused automatically"
- "Kill signal: 0 conversions after 200 clicks"
- "Stripe webhook failing — checkout broken"

### Batch Results → App Dashboard + Slack Summary

**Rule:** Large result sets get a Slack summary with key metrics and a link to the full dashboard.

```
Slack: "MatchHire Rung 4 complete. Summary:
        Landing page: 4.2% conversion ✓
        Google Ads CPA: $23 (target $30) ✓
        LinkedIn CPA: $41 (target $30) ✗
        Recommendation: Proceed to Rung 5, drop LinkedIn.
        [View full report →]"
```

---

## The Key Insight

**Slack is for REACTIVE work.** The system pushes information and decisions to you. You react with minimal effort — approve, reject, acknowledge, ask a quick question. Optimized for low-friction, high-frequency micro-interactions.

**The App is for PROACTIVE work.** You go there intentionally when you want to think deeply, design something, review complex data, or make strategic decisions. Optimized for depth, visual richness, and creative flow.

**The CLI is for AUTOMATED work.** Scripts, cron jobs, batch operations, and power-user workflows where you want programmatic control without a GUI.

**Same brain, different body.** All three channels connect to the same Conversation Router, the same module graph, the same data. Your context follows you across channels. An approval in Slack is instantly reflected in the App. A command in the CLI triggers the same Slack notification as it would from the App.

The platform adapts to your energy and context:
- Busy day, back-to-back meetings? Everything important reaches you in Slack. Tap approve between calls.
- Saturday morning with coffee, ready to think? Open the App, dive deep into strategy.
- Building automation for your workflow? Script it with the CLI.

No channel is "better" — they're complementary tools for different cognitive modes.
