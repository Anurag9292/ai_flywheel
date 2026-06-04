# Reference Implementations

Open-source projects and codebases to reference when building specific modules. These are "cheat codes" — proven solutions to steal patterns from rather than building from scratch. Each reference maps to a specific build phase so you don't get distracted prematurely.

**Rule:** Reference these when you REACH the relevant phase. Do not pre-build integrations from Phase 3-6 during Phase 0-1.

---

## Phase 2-3: Browser Automation (Strongest Steal)

**Relevant modules:** Tool Forge (#10), Market & Signal Intelligence (#25)

**What you need:** Agents that browse the web — scrape competitor pricing, analyze search demand, fill forms, extract structured data from SPAs.

**Reference: Clawd Bot (browser automation layer)**

What to steal:
- Page navigation patterns for SPAs (wait for hydration, handle dynamic content)
- Form auto-filling with validation
- Data extraction from complex layouts (tables, nested elements, paginated lists)
- Anti-bot detection handling (headless browser fingerprinting, delays, rotation)
- Session and cookie management for authenticated scraping

How to integrate:
```python
@activity.defn
async def scrape_competitor_pricing(url: str, selectors: dict) -> ScrapedData:
    """Temporal Activity wrapping browser automation.
    
    - Clawd Bot's Playwright logic handles the actual browsing
    - Temporal provides: retries on failure, timeouts, cost tracking
    - Idempotency: same URL + selectors = cached result
    """
    browser = await launch_browser(headless=True)
    try:
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle")
        # ... extraction logic borrowed from reference
        return extracted_data
    finally:
        await browser.close()
```

**What NOT to steal:** Their orchestration/agent loop — that's Temporal's job.

---

## Phase 6: Slack/Messaging Integration

**Relevant modules:** Conversation Router, Slack Bot (channels/)

**What you need:** Bidirectional Slack integration — receive commands, send notifications, handle approval flows in threads, maintain conversation context across channels.

**Reference: Clawd Bot (messaging adapter layer)**

What to steal:
- Webhook routing and event deduplication
- Thread-based conversation context management
- Multi-channel context threading (user starts in Slack, continues in web)
- Interactive message components (buttons, modals, dropdowns for approvals)
- Rate limit handling and message queuing

What to evaluate first:
- **Slack Bolt (Python)** already handles most webhook/event complexity natively
- Compare: if Clawd Bot adds value OVER Slack Bolt (conversation state, multi-channel sync) → steal that layer
- If it's mostly wrapping Slack's API → just use Slack Bolt directly (already in tech stack)

How to integrate:
```python
# The Slack adapter feeds INTO Temporal workflows, never replaces them

@app.event("message")
async def handle_message(event, say):
    """Slack Bolt handler → triggers Temporal workflow."""
    # Parse intent (borrowed context-threading logic)
    intent = await parse_intent(event)
    
    if intent.type == "approval_response":
        # Signal existing workflow to resume
        await temporal_client.get_workflow_handle(intent.workflow_id).signal(
            "approval_received", ApprovalSignal(approved=True, by=event["user"])
        )
    elif intent.type == "new_command":
        # Start new workflow
        await temporal_client.start_workflow(
            CommandWorkflow.run, args=[intent.command, intent.context],
            id=f"slack-cmd-{event['ts']}",
        )
```

**What NOT to steal:** Their AI agent loop, model routing, or response generation — those are your LLM Gateway + Agent Factory.

---

## Phase 6: CLI Bridge

**Relevant modules:** CLI interface (channels/cli.py)

**What you need:** Local terminal interface that talks to the cloud-hosted backend — command execution, streaming workflow output, interactive approval flows.

**Reference: Clawd Bot (system-access / CLI layer)**

What to steal (if applicable):
- Streaming output patterns (SSE from Temporal workflows to terminal)
- Interactive approval flows rendered in terminal (confirm/reject with context)
- Secure credential management (API keys, tokens, refresh logic)
- Local file access patterns (reading project context, config files)

What's probably simpler to write fresh:
- Basic command structure → just `click` + `httpx` (trivial)
- API communication → typed client generated from your FastAPI OpenAPI spec
- Auth flow → standard JWT/API key in header

How to integrate:
```python
# CLI is a thin client over your FastAPI backend + Temporal

@click.command()
@click.argument("venture")
@click.argument("command")
def run(venture: str, command: str):
    """Execute a command against a venture."""
    # POST to FastAPI → starts Temporal workflow → stream results via SSE
    with httpx.stream("POST", f"{API_URL}/ventures/{venture}/commands",
                      json={"command": command}) as response:
        for line in response.iter_lines():
            click.echo(line)
```

**Lower priority steal** — most CLI needs are straightforward HTTP + streaming.

---

## General Patterns Worth Stealing

These apply across phases, not to a specific module:

| Pattern | Reference | When You'll Need It |
|---------|-----------|-------------------|
| Structured output parsing (LLM → typed data) | Instructor library | Phase 1 (Agent Factory) |
| Evaluation frameworks (LLM output quality) | Ragas, DeepEval | Phase 1-2 (Evaluation) |
| RAG chunking strategies | LangChain text splitters, Unstructured.io | Phase 2 (Data & Knowledge) |
| Knowledge graph extraction | LlamaIndex KG module | Phase 2 (Knowledge Graph) |
| Prompt versioning patterns | Humanloop, Braintrust | Phase 1 (Prompt Studio) |
| Feature flags for AI | LaunchDarkly AI patterns | Phase 3 (Experimentation) |
| Cost tracking per LLM call | LiteLLM (already chosen) | Phase 0 (LLM Gateway) |

---

## Anti-Patterns (What NOT to Reference)

| Don't Steal | Why |
|-------------|-----|
| LangChain's agent abstractions | Too opaque, doesn't compose with Temporal. Write your own thin agent logic. |
| AutoGPT/BabyAGI recursive loops | Uncontrolled recursion without durable execution = disasters at scale. Use Temporal child workflows. |
| Any framework's "memory" system | They're all in-memory or simple vector stores. Your memory is Temporal state + Postgres + Redis (tiered, access-controlled). |
| Multi-agent "debate" frameworks (CAMEL, etc.) | Interesting research, terrible in production. Use structured Temporal workflows with explicit handoffs. |
| Vector DB-as-a-service SDKs (Pinecone, Weaviate clients) | You're using pgvector co-located with relational data. Don't add network hops to a separate vector service. |

---

## When to Look vs. When to Build

```
Phase 0-1:  Build everything. The spine must be yours.
Phase 2:    Reference chunking/embedding patterns. Build the pipeline yourself.
Phase 3:    Reference browser automation heavily. Steal and wrap as Activities.
Phase 4:    Reference evaluation frameworks (Ragas/DeepEval). Integrate, don't reinvent.
Phase 5:    Reference deployment patterns (Fly.io docs). Straightforward infra.
Phase 6:    Reference Clawd Bot messaging + CLI. Steal adapters, wire to your Temporal.
```

The rule: **steal the leaf nodes (specific solved problems), never steal the trunk (orchestration, state, coordination).** The trunk is Temporal + your Core Kernel.
