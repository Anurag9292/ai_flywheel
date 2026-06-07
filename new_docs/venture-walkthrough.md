# Venture Walkthrough — PostlineAI

> **The heart of these docs.** We walk one real venture chronologically, and
> *every* Layer 1 node you'll ever see in `layer1-nodes.md` is *derived* from
> something the venture actually needed in this walkthrough. Nothing is
> designed up front.

If you only read one doc, read this one.

---

## 0. The venture, in one paragraph

**PostlineAI** is a B2B LinkedIn ghostwriting service for early-stage founders
and execs. They know they should post on LinkedIn to build pipeline; they have
no time and bad results. PostlineAI turns 10 minutes of voice notes per week
into a consistent, on-brand LinkedIn presence that generates inbound leads.

- **ICP (working hypothesis):** seed/Series-A B2B SaaS founders, 50–500
  employees, post inconsistently, currently rely on cold outbound.
- **Price (working hypothesis):** $499/mo.
- **Riskiest assumption:** they will pay $499/mo for ghostwritten LinkedIn
  posts in a market full of $30/mo Buffer-style tools and $5k/mo human
  ghostwriters.

Why this venture for the walkthrough: it forces us through ad campaigns, market
research, agentic content generation, scheduling, analytics, lead capture, and
billing — a wide cross-section that surfaces enough Layer 1 nodes to make the
model real, but not so wide it becomes overwhelming.

---

## How to read this walkthrough

Each step has the same shape:

> **Step N — \<what the founder is trying to do\>**
>
> *The venture needs to: \<concrete capability\>*
>
> → **Derives Layer 1 node:** `name` — *reacts to* `event.in`, *calls libraries*
> `libA, libB`, *emits* `event.out`. (One-line description.)
>
> → **Derives Layer 1 library tool:** `name` — *what it wraps*. (When applicable.)

When a node *already exists* (because an earlier step derived it), we just
*reuse* it. Watching reuse begin is how you know the model is working.

The full set of nodes derived here is mirrored, deduplicated, in
`layer1-nodes.md`.

---

## Step 1 — The founder has a hunch

The founder thinks "B2B founders are bad at LinkedIn but know they should be
good at it. Maybe a ghostwriting agent could nail this." Pure intuition, zero
evidence.

> *The venture needs to: capture the hunch in a structured form so its
> assumptions can be tracked and falsified.*

The thesis itself isn't a Layer 1 node — it's a domain artifact (a YAML file
in the venture). But surfacing it consistently and tracking which assumptions
have been tested is.

→ **Derives Layer 1 node:** `thesis-tracker` — reacts to
`evidence.collected`, updates which assumptions in the venture's thesis are
supported / contradicted / untested, emits `thesis.state.updated`. Pure
bookkeeping; no LLM yet.

→ **Derives Layer 1 library tool:** `event-bus` — minimal pub/sub the venture
and all nodes share. *(This is substrate. It's also the one library every other
node depends on.)*

→ **Derives Layer 1 substrate:** `trace-recorder` — automatically wraps every
node invocation, recording inputs/outputs/cost/latency. Not a node you call;
it's the always-on layer that makes Layer 3 possible.

**Layer 1 so far:** `thesis-tracker` (node), `event-bus` (lib), `trace-recorder`
(substrate).

---

## Step 2 — Desk research

Cheapest evidence. Before talking to anyone, what does the market look like?
Are competitors winning here? What keywords do potential customers actually
search?

> *The venture needs to: pull search-volume and keyword data for "linkedin
> ghostwriter", "B2B founder content", "thought leadership writing", etc.*

→ **Derives Layer 1 library tool:** `semrush-client` — a thin wrapper around
the SEMrush API. Pure function calls; no events.

> *The venture needs to: discover the named competitors in this space and what
> they charge.*

→ **Derives Layer 1 library tool:** `web-search-client` — wraps a search API
(Brave / Serper / Exa). Functions: `search(query)`, `fetch(url)`.

> *The venture needs to: read those competitor pages and synthesize a
> positioning landscape — pricing, claims, audience.*

→ **Derives Layer 1 node:** `market-scanner` (agentic) — reacts to
`research.requested`, calls `semrush-client` + `web-search-client` + the
LLM gateway, emits `market.landscape.summarized` carrying a structured market
map.

> *The agent needs to call an LLM.*

→ **Derives Layer 1 library tool:** `llm-gateway` — multi-provider, retries,
cost tracking. Pure library you import. Used by every agentic node from now on.

**New this step:** `semrush-client`, `web-search-client`, `llm-gateway` (libs),
`market-scanner` (node).

---

## Step 3 — Customer conversations

Talk to 10 founders matching the ICP. Capture transcripts. Extract pain.

> *The venture needs to: schedule the calls and capture transcripts.*

Scheduling and transcription are commodity I/O.

→ **Derives Layer 1 library tool:** `calendar-client` — wraps Calendly /
Google Calendar.

→ **Derives Layer 1 library tool:** `transcription-client` — wraps
Whisper / Deepgram.

> *The venture needs to: ingest transcripts and extract pain points,
> frequency, and emotional intensity.*

→ **Derives Layer 1 node:** `pain-extractor` (agentic) — reacts to
`transcript.captured`, calls `llm-gateway`, emits `pain.extracted` with a
structured list of pain points and their frequency across calls.

> *The venture needs to: feed the pains back into the thesis tracker.*

The thesis-tracker already exists (Step 1). Reuse — by *subscription*. The
thesis-tracker simply also subscribes to `pain.extracted`. **No code change to
the venture wiring.** This is the first taste of the event-driven payoff.

**New this step:** `calendar-client`, `transcription-client` (libs),
`pain-extractor` (node). One reuse.

---

## Step 4 — Landing page + ad test

The founder builds a one-page site claiming "Your LinkedIn, ghostwritten by AI
that sounds like you. $499/mo. Join the waitlist." Then runs $200 of LinkedIn
ads and $200 of Facebook ads to it.

> *The venture needs to: launch and configure ad campaigns on LinkedIn and
> Facebook with copy + creative + targeting.*

→ **Derives Layer 1 library tool:** `linkedin-ads-client` — wraps the
LinkedIn Marketing API.

→ **Derives Layer 1 library tool:** `meta-ads-client` — wraps the Meta
Marketing API.

→ **Derives Layer 1 node:** `ad-campaign-runner` — reacts to
`campaign.requested`, calls the appropriate ads client, emits
`campaign.launched`.

> *The venture needs to: collect ad metrics on a schedule (impressions, CTR,
> CPC, CPL) and the landing page's signups.*

→ **Derives Layer 1 node:** `ad-analytics-collector` — reacts to
`campaign.launched` (and a daily timer), pulls metrics, emits
`campaign.metrics.updated`.

→ **Derives Layer 1 library tool:** `analytics-client` — wraps PostHog /
Plausible for the landing page side.

> *The venture needs to: judge whether the conversion signal is strong, weak,
> or kill-worthy — given the working thesis ("would pay $499/mo").*

This is judgment, not API stitching. It's an agentic Layer 1 node.

→ **Derives Layer 1 node:** `signal-analyzer` (agentic) — reacts to
`campaign.metrics.updated`, computes the relevant signal, calls `llm-gateway`
to interpret in context, emits `signal.verdict` (one of `strong | weak | kill`)
plus a confidence score and a one-line explanation.

> *The venture needs to: surface the verdict to the founder for the
> go/kill decision.*

→ **Derives Layer 1 node:** `founder-notifier` — reacts to
`signal.verdict` (and many other event types — see Step 7), routes to Slack /
email / web inbox based on urgency. Emits `founder.notified`.

→ **Derives Layer 1 library tool:** `slack-client` — wraps Slack web API.

→ **Derives Layer 1 library tool:** `email-client` — wraps Postmark / Resend.

**New this step:** `linkedin-ads-client`, `meta-ads-client`, `analytics-client`,
`slack-client`, `email-client` (libs), `ad-campaign-runner`,
`ad-analytics-collector`, `signal-analyzer`, `founder-notifier` (nodes).

This is the densest step on purpose — it's the "set up ads, analyze, decide"
flow that motivates the whole architecture. Notice every concern is a separate,
small, reusable node.

---

## Step 5 — Wizard-of-Oz: the founder ghostwrites manually for 3 paying customers

Three people from the waitlist agree to a 30-day trial at $299/mo. The founder
*personally* writes their LinkedIn posts, masquerading as the agent. Goal: prove
people pay and use it before any AI is built.

> *The venture needs to: collect raw input (voice notes / bullet points) from
> each customer on a cadence.*

→ **Derives Layer 1 library tool:** `inbound-collector` — wraps a webhook
endpoint + email-to-bucket. Routes inbound to the right venture/customer.

→ **Derives Layer 1 node:** `input-intake` — reacts to
`inbound.received`, normalizes into an `input.captured` event keyed by
customer.

> *The venture needs to: turn that input into draft LinkedIn posts.*

→ **Derives Layer 1 node:** `post-drafter` — reacts to `input.captured`,
emits `post.drafted`.
**This is the Wizard-of-Oz node.** Its first implementation routes to a human
(the founder) via the human-review queue. The event interface stays the same;
the implementation is a human.

→ **Derives Layer 1 node:** `human-review-queue` — reacts to events tagged
`requires_human=true`, presents to a human, emits the original event-type
result once approved/edited. The single mechanism for "AI eventually, human
for now."

> *The venture needs to: schedule and publish posts at the right time.*

→ **Derives Layer 1 library tool:** `linkedin-posting-client` — wraps
LinkedIn's content posting API (different from the ads API).

→ **Derives Layer 1 node:** `post-scheduler` — reacts to `post.approved`,
emits `post.scheduled` and (at the right time) `post.published`.

> *The venture needs to: bill the three customers $299.*

→ **Derives Layer 1 library tool:** `billing-client` — wraps Stripe.

→ **Derives Layer 1 node:** `subscription-manager` — reacts to
`subscription.requested` and `subscription.cancelled`, calls `billing-client`,
emits `subscription.activated` / `subscription.cancelled`.

**New this step:** `inbound-collector`, `linkedin-posting-client`,
`billing-client` (libs), `input-intake`, `post-drafter` (Wizard-of-Oz),
`human-review-queue`, `post-scheduler`, `subscription-manager` (nodes).

The crucial observation: **`post-drafter` is on the topology now**, even though
its "agent" is a human. When the agent is built later (Step 7), the event
interface doesn't change — only the implementation behind one node does. The
venture's wiring is untouched.

---

## Step 6 — Measure what's working

After 30 days, the founder needs to know: did engagement go up? Did any of the
three customers convert inbound leads? Are they happy enough to renew?

> *The venture needs to: pull engagement metrics for each customer's published
> posts.*

`linkedin-posting-client` already exposes the read endpoints needed. We extend
the existing `ad-analytics-collector`? No — different domain, different events.
Better to derive a sibling.

→ **Derives Layer 1 node:** `post-analytics-collector` — reacts to
`post.published` (and a daily timer), emits `post.metrics.updated`.

> *The venture needs to: ask each customer for an NPS-style rating and capture
> any inbound leads they got.*

→ **Derives Layer 1 node:** `customer-survey` — reacts to
`survey.requested` (timer-driven), sends an email/Slack via existing libs,
collects response, emits `survey.responded`.

> *The venture needs to: roll all of this — engagement, leads, survey — into a
> "is this working?" verdict.*

We already have `signal-analyzer` from Step 4. Can we reuse it?

Yes — but it currently understands ad metrics. We can either (a) parameterize
it with a "what does success mean here?" rubric, or (b) keep it specialized
and derive a sibling. We choose (a): the agent's prompt takes the venture's
current-stage rubric as input, so the same node handles both ad-test signals
and product-engagement signals. Reuse via configuration, not new code.

This is the *first refactor* of a Layer 1 node driven by a second use case —
exactly when refactoring should happen. Not before.

**New this step:** `post-analytics-collector`, `customer-survey` (nodes).
**Reuses:** `signal-analyzer`, `founder-notifier`, `email-client`, `slack-client`.

---

## Step 7 — Build the actual agent

Three customers paid, renewed, used it weekly. The Wizard-of-Oz proves the
product works. Now the founder builds the AI agent that drafts posts —
replacing the human inside `post-drafter`.

> *The venture needs to: capture each customer's voice/style — past posts,
> brand guidelines, examples they like.*

→ **Derives Layer 1 node:** `voice-profile-builder` (agentic) — reacts to
`onboarding.materials.received`, calls `llm-gateway`, emits
`voice-profile.built`. Stores the profile in the venture's per-customer state.

> *The venture needs to: actually draft posts in that voice from raw input.*

The `post-drafter` node already exists, with a human implementation. We swap
the implementation: the new one calls `llm-gateway` with the customer's voice
profile + the input. Event interface unchanged. The venture's `topology.yaml`
is unchanged. Only the binding `post-drafter.impl: human` becomes
`post-drafter.impl: agent-v1`.

**This is what "graduating up the evidence ladder" looks like, mechanically.**

> *The venture needs to: keep a human safety net for the first month of agent
> drafts.*

The `human-review-queue` already exists. We just *don't disconnect it yet* —
drafts flow `post-drafter (agent) → human-review-queue → post-scheduler`.
After confidence builds, the venture removes the human-review hop from its
topology — a one-line change.

> *The venture needs to: continually improve the agent based on edits the
> human (or customer) makes to drafts.*

→ **Derives Layer 1 node:** `feedback-collector` — reacts to events that
carry corrections or ratings (`post.edited_by_human`, `post.rated`,
`survey.responded`), normalizes, emits `feedback.captured`. Feeds Layer 3.

→ **Derives Layer 1 node:** `prompt-tuner` (agentic, lives at the boundary —
arguably this should be a Layer 3 *suggestion* + Layer 2 *application* rather
than a Layer 1 node — flagged for revisit; see "Open questions" below).

**New this step:** `voice-profile-builder`, `feedback-collector` (nodes).
**Reuses:** `post-drafter` (impl swap), `human-review-queue`, `llm-gateway`.
**Open question:** `prompt-tuner` placement.

---

## Step 8 — Grow

The product works for 3 customers. Time to scale to 30. Same ad infrastructure
from Step 4 — just turned up.

> *The venture needs to: launch larger ad campaigns and route signups through
> the now-real onboarding flow.*

→ **Reuses:** `ad-campaign-runner`, `ad-analytics-collector`, `signal-analyzer`
(now interpreting growth signals — same node, different rubric — exactly as
the refactor in Step 6 enables).

> *The venture needs to: handle real customer onboarding at scale.*

→ **Reuses:** `subscription-manager`, `voice-profile-builder`, `input-intake`,
`post-drafter`, `post-scheduler`.

**No new Layer 1 nodes are derived in this step.** That's not a coincidence —
that's the model paying off. The validation phase already built the production
nodes. Scaling is turning up volume.

The only thing that changes is **edges, not nodes**: the venture's topology
adds new event subscriptions (e.g. routing high-CPL alerts from
`signal-analyzer` directly to `founder-notifier` with `urgent=true`) and tweaks
configuration. The Layer 1 catalog grows zero.

---

## Step 9 — Layer 3 starts paying off

The founder is ready to think about venture #2. Layer 3 has been silently
recording every event since Step 1. It now does what it's for:

- **Pattern surfacing:** "Across PostlineAI, you found product-market signal
  faster after the $200 LinkedIn ad than after 10 customer interviews. The
  evidence-ladder rung you actually want is rung 3 (ad+landing) before rung 2
  (interviews) for B2B SaaS founder personas."
- **Promotion suggestion:** "Your `voice-profile-builder` agentic prompt has
  a sub-pattern (style-extraction → exemplar-clustering) that 3 of your other
  agentic nodes informally implement. Promote it to a shared Layer 1 node?"
- **Next-venture guidance:** "Venture #2 should clone PostlineAI's
  Steps 4–6 topology (ads → analytics → signal-analyzer) on day 1. That alone
  saves ~3 weeks."

Layer 3 doesn't do venture work; it reads what every Layer 1 call emitted (via
`trace-recorder`) and points the founder at the highest-leverage moves.

**No new Layer 1 nodes.** Layer 3 is its own thing.

---

## What we ended up with

Layer 1 derived from **one venture, walked end-to-end**:

**Library tools (12):** `event-bus`, `llm-gateway`, `semrush-client`,
`web-search-client`, `calendar-client`, `transcription-client`,
`linkedin-ads-client`, `meta-ads-client`, `linkedin-posting-client`,
`analytics-client`, `inbound-collector`, `slack-client`, `email-client`,
`billing-client`. *(Pure functions/clients; no events.)*

**Substrate (1):** `trace-recorder`. *(Wraps every call; not invoked.)*

**Event-driven nodes (~17):** `thesis-tracker`, `market-scanner`,
`pain-extractor`, `ad-campaign-runner`, `ad-analytics-collector`,
`signal-analyzer`, `founder-notifier`, `input-intake`, `post-drafter`,
`human-review-queue`, `post-scheduler`, `subscription-manager`,
`post-analytics-collector`, `customer-survey`, `voice-profile-builder`,
`feedback-collector`, `prompt-tuner` *(placement TBD)*.

That's *roughly* 30 Layer 1 things — discovered, not designed. Compare to the
old docs' 39 modules in 8 systems specified up front. The bottom-up set is
smaller, every item is justified by a real need, and every one was reused
within this same walkthrough.

For the canonical, deduplicated list with event signatures, see
`layer1-nodes.md`.

---

## What this walkthrough taught us about the model

1. **Reuse begins fast and grows.** By Step 8, *zero* new nodes are derived.
   That's the goal — the platform should plateau at "almost everything is
   reuse" as ventures accumulate.
2. **Wizard-of-Oz is a binding, not a phase.** `post-drafter` exists from
   Step 5; only its `impl` changes (human → agent) at Step 7. Climbing the
   evidence ladder is a one-line config change, not a re-architecture.
3. **"Validation" is the same nodes as "production."** `ad-campaign-runner` is
   used identically in Step 4 ($200 demand test) and Step 8 (growth). Same
   node, different rubric the `signal-analyzer` interprets through.
4. **Events are for flow; libraries are for I/O.** Every API client (LinkedIn,
   Stripe, SEMrush) is a plain library. Every step that another part of the
   system might want to react to is an event. The split is natural and never
   felt arbitrary in the walkthrough.
5. **Some nodes are agentic and that's fine.** `signal-analyzer`,
   `pain-extractor`, `voice-profile-builder` all reason with an LLM. They're
   still Layer 1 — the boundary isn't "dumb wrapper vs. smart" but "reusable
   capability vs. venture-specific composition."

---

## Open questions surfaced by the walkthrough

These are things the walkthrough *exposed* but didn't resolve. They are the
right next things to think about — not now, but after PostlineAI is real.

1. **Where does `prompt-tuner` belong?** It was tentatively placed in Layer 1
   in Step 7, but its job (improving prompts based on cross-venture feedback)
   smells more like Layer 3. Likely answer: Layer 3 *proposes* tuning; Layer 1
   has a `prompt-store` (not yet derived) that *applies* approved tunings.
   Defer until a second venture forces the question.
2. **What does `topology.yaml` actually look like?** We've described it
   abstractly. The first concrete schema should be designed only when
   PostlineAI's topology is real enough to need persistence (probably at
   Step 4 in code).
3. **State and idempotency.** Many nodes are timer-driven
   (`ad-analytics-collector`, `customer-survey`). What guarantees we don't
   double-bill / double-publish on retries? Defer until the first such bug
   bites.
4. **Multi-tenancy inside a venture.** PostlineAI has multiple paying
   customers. The walkthrough mostly waved at "keyed by customer." Real
   tenancy concerns (per-customer state, per-customer credentials) need
   designing in before scaling beyond 3 customers. Likely a small shared
   substrate — but derive it from need, not now.

These are intentionally *not* solved in this doc. Solving them now would be
the same mistake the old `docs/` made.

---

## Where to go next

- **`layer1-nodes.md`** — every node above, deduplicated, with event
  signatures.
- **`vision.md`** — the model and principles in concise form.
- **The `/vision-v2` page** in the frontend — this walkthrough rendered
  visually, with the PostlineAI topology wired by event edges.
- **`visualization.md`** — the plan for a *code-derived* topology map and live
  trace replay (the running system, not the hand-drawn design).
