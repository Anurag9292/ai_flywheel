# The Scraping Engine — an agentic, provider-agnostic crawler

> **Status: Phase 1 built.** This doc describes how `lead-sourcer` enriches a
> discovered company by *navigating* its website — following `<a href>` links
> best-first to find contact + positioning signal — rather than scraping a
> single URL. It is grounded in current focused-crawling / web-agent research and
> fits the repo's existing seams (`Agent` Protocol + `WebScraperClient` Protocol).

---

## 1. Why this exists (the bug it fixes)

The first enrichment impl scraped **the ATS job-posting URL** (e.g.
`https://jobs.lever.co/scaleway/<id>`) and kept whatever came back. In a real
live run that produced *useless apply-page chrome* ("Powered by Ashby", "Privacy
Policy") and **no emails** — because the job page isn't the company, and a single
page rarely holds the contact/positioning signal we want.

The fix is to treat enrichment as a **goal-conditioned crawl of the company's own
site**: seed at the company domain, follow links, prioritise `about` / `contact` /
`careers` / `team`, stop when the goal (a contact email + some positioning text)
is met or a budget is hit.

---

## 2. State of the art (what we borrow)

| Idea | Source | What we take |
|---|---|---|
| **Focused / Best-First crawling** over naive BFS/DFS | classic focused crawlers; "Neural Prioritisation for Web Crawling" | The frontier is a **priority queue**, not a FIFO/LIFO. Each discovered link gets a score; we always expand the most promising. |
| **Neural / LLM frontier scoring** | "neural crawling" (+149% on natural-language goals vs BFS) | *Optional* LLM scoring of ambiguous links (Phase 2). Phase 1 uses cheap heuristics. |
| **Planner / Executor split** | BrowseMaster | The executor returns **structured summaries + scored links**, never raw HTML, so the planner's reasoning stays coherent and cheap. |
| **Aggregator + goal-conditioned stop** | INFOGENT | A component accumulates findings and decides *"do I have enough yet?"* — crawl stops on goal, not on site exhaustion. |
| **Graph memory + backtracking + pruning** | Go-Browse, Branch-and-Browse | A `visited` set (dedupe, no re-fetch) and a frontier that naturally backtracks; low-value branches are simply never popped. |

**What we deliberately skip:** full browser-driving web agents (clicking, forms,
multimodal). For *reading SSR company pages* that machinery is overkill — see §4.

---

## 3. Architecture — three layers on existing seams

```
lead-sourcer (Layer 1 node — event contract unchanged)
   └── CrawlAgent  (flywheel/agents/ — a reusable, GOAL-AGNOSTIC capability)
        │   owns the MECHANISM: frontier (priority queue) + visited graph +
        │   budgets + same-domain restriction. Carries NO use-case logic.
        ├── CrawlGoal  (the pluggable INTENT — swap it to reuse the crawler)
        │     • score_link / absorb / satisfied / result
        │     • ContactCrawlGoal  → lead-gen (email + positioning)
        │     • KeywordCrawlGoal  → market research / topic capture
        │     • …RAG ingestion, diligence, etc. (just write a new goal)
        └── WebScraperClient (Protocol — the swappable executor leaf)
              ├── HttpxScraperClient    (in-house, default real impl)
              ├── FirecrawlScraperClient (managed; JS-heavy / anti-bot)
              └── FakeWebScraperClient   (offline, deterministic — tests/default)
```

**Why goal-agnostic.** The crawl *mechanism* (frontier, best-first, dedupe,
budgets, same-domain) is identical for every use case; only the *intent* —
which links to prefer, when to stop, what to extract — varies. So the agent
takes a ``CrawlGoal`` strategy and stays a pure, reusable Layer 1 capability.
``lead-sourcer`` builds a ``ContactCrawlGoal`` and passes it in; a market-research
node would pass a ``KeywordCrawlGoal``; the crawler code is untouched. It lives in
``flywheel/agents/`` (composite capabilities), **not** ``core/`` (substrate).

- **The composite-agent layer** is exactly where a stateful multi-step loop
  belongs — `stack.md` predicted this: *"a node's `handle()` becomes a loop with
  state… that's where a `GraphAgent` plugs in."* `CrawlAgent` is that
  capability, in `flywheel/agents/`. **Hand-rolled** (no LangGraph) — a frontier
  loop, fully traceable via the existing substrate. (The generic single-call
  `Agent` seam in `flywheel/core/agent.py` is a sibling, used by the LLM nodes.)
- The **`WebScraperClient` Protocol** is the executor swap point. The crawler
  never knows which fetcher backs it, so dropping/adding a provider is a one-line
  registry change.
- `lead-sourcer` stays a dumb event handler: it builds a seed URL + a
  `ContactCrawlGoal` and calls `crawl(seed, goal)` once. Events/topology
  unchanged.

---

## 4. SSR vs. JS — why the default executor is `httpx`, not a browser

A plain `httpx.get(url)` returns the **raw HTML the server sent**. For
**server-side-rendered (SSR)** pages — which is *most* company marketing /
about / contact / careers pages, because they need to rank on Google — the
content and every `<a href>` are already in that HTML. So "follow the link" is
just *read the href and fetch it*. **No browser, no clicking.**

Empirically (measured against the live roster): plain `httpx` returns
**5k–17k chars** of visible text from `scaleway.com`, `posthog.com`,
`webflow.com`, `vercel.com` about pages, and a heuristic best-first crawl found
`hey@posthog.com` in **3 pages**.

A real browser (**Playwright**) is only needed when content **doesn't exist in
the HTML until JavaScript runs it** — single-page apps, infinite scroll,
click-to-reveal, or interaction-gated pages. That is the *minority* for company
sites, so Playwright is an **optional fallback** (Phase 3), deferred until a real
target demands it. Its cost is real: ~300 MB Chromium, 200–500 MB RAM/browser,
heavier deploys, and anti-bot/proxy maintenance.

> **Rule:** try `httpx` first; only escalate to a browser-backed executor for
> pages that come back empty/thin. (Firecrawl already covers that slice today.)

---

## 5. The `CrawlAgent` loop (hand-rolled)

```text
run(inputs={seed_url, goal, company}) -> (CrawlResult, Completion):
    frontier = PriorityQueue()          # best-first: highest score popped next
    visited  = set()                    # dedupe (no re-fetch / backtrack-safe)
    agg      = Aggregator(goal)         # accumulates emails + context
    frontier.push(score=1.0, seed_url, depth=0)

    while frontier and within_budget(pages, depth, cost, time):
        url, depth = frontier.pop_highest()
        if url in visited: continue
        page = scraper.scrape(url)      # WebScraperClient leaf (provider-agnostic)
        visited.add(url)
        agg.absorb(page)                # extract emails / positioning snippet
        if agg.satisfied(goal): break   # goal-conditioned stop
        if depth >= max_depth: continue
        for link in page.links:
            s = priority(link, goal)    # tiered scoring (below)
            if s > threshold and link.url not in visited:
                frontier.push(s, link.url, depth+1)
    return agg.result(), completion
```

**`priority(link, goal)` — tiered, cheap-first:**
1. **Heuristic (free, Phase 1):** boost links whose URL/anchor match
   `contact|about|team|careers|company|jobs|press|people`; **same-domain only**;
   decay by path depth. Covers the large majority.
2. **LLM batch-score (Phase 2, optional, gated):** when heuristics are
   ambiguous, score candidate links with one cheap `llm-gateway` call.

**Hard budgets (non-negotiable):** `max_pages`, `max_depth`, `max_cost_usd`,
`time_limit`, **same-domain restriction**, and (real-executor) **robots.txt** +
per-host rate limiting.

**`Aggregator.satisfied(goal)`** for lead-gen = found ≥1 contact email **and** a
positioning snippet — *or* budget exhausted. Note: many company contact pages are
**form-based with no email**; "found the contact page" is itself a useful outcome,
so the aggregator records the best contact *route* even when no `mailto:` exists.

---

## 6. `WebScraperClient` extension + executors

`ScrapedPage` gains `links: list[Link]` (`url`, `anchor`, `same_domain`). All
executors populate it:

- **`HttpxScraperClient` (in-house, default real):** `httpx.get` → strip
  scripts/styles/tags → visible text + `<a href>` extraction (absolute-resolved,
  same-domain tagged) + email regex. Tenacity retries, timeout, max-bytes guard,
  polite User-Agent. No browser. **This drops the hard Firecrawl dependency.**
- **`FirecrawlScraperClient` (managed):** kept for JS-heavy / anti-bot pages;
  now also returns `links` from Firecrawl's link output.
- **`FakeWebScraperClient` (offline):** canned pages with canned links → the
  default venture + tests stay deterministic and network-free.

Swapping executor = one line in the registry; the `CrawlAgent`, node, events and
tests above the Protocol are untouched.

---

## 7. Observability

`CrawlAgent` returns a `CrawlResult` (seed, `pages_visited[]`, emails,
`company_context`, `stop_reason`, page count) which rides into the trace payload
(full in `traces.jsonl` + `/api/traces`, truncated in stdout — per the payload
work). So a crawl is fully inspectable: which pages, in what order, why it
stopped. The `/topology` step "output" panel renders it.

---

## 8. Doctrine & safety

- **Fakes are the default** → offline, deterministic tests; the live crawl runs
  only in the LIVE venture.
- **Best-effort, non-fatal:** a crawl failure (bad page, timeout, 403) is logged
  and skipped — discovery already succeeded; enrichment is a bonus.
- **Politeness/legal:** same-domain only, robots.txt respect, rate limiting,
  bounded budgets — we are a guest on these sites.

---

## 9. Phasing

- **Phase 1 (this slice):** `ScrapedPage.links` + `HttpxScraperClient` +
  hand-rolled heuristic `CrawlAgent` (frontier, best-first, budgets, goal-stop,
  visited graph) + `lead-sourcer` seeds the **company domain** (derived from the
  job posting) and crawls. Offline fakes keep tests deterministic. *No browser,
  no new LLM cost.*
- **Phase 2:** LLM-scored frontier (neural prioritisation) + planner replan,
  gated by budget.
- **Phase 3:** browser-backed executor (`PlaywrightScraperClient`) for the
  JS-rendered minority, behind the same Protocol; richer Aggregator goals.

---

## 10. Open questions (decide as we go)

- robots.txt: strict-respect (skip disallowed) vs. configurable override?
- LLM frontier scoring: default off (cost) — turn on per-venture?
- Per-crawl `max_cost_usd` / `max_pages` defaults?
- Crawl4AI vs. hand-rolled Playwright for the eventual browser executor?

---

## See also

- `flywheel/agents/crawl_agent.py` — the goal-agnostic `CrawlAgent` + `CrawlGoal`
  Protocol + the shipped goals (`ContactCrawlGoal`, `KeywordCrawlGoal`).
- `flywheel/libraries/web_scraper_client.py` — the `WebScraperClient` Protocol +
  executors.
- `flywheel/nodes/lead_sourcer.py` — the node that drives the crawl.
- `stack.md` — the "agent frameworks deferred behind an `Agent` seam" rationale.
