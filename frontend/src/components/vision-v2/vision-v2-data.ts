/**
 * Vision V2 — Bottom-up, event-driven, 3-layer model.
 *
 * Layout (~2400x1700, default zoom 0.5):
 *   Top (y: 80-180):       Layer 3 — Meta (watch & guide)
 *   Band 1 (y: 320):       The Event Bus — labeled events flowing along it
 *   Band 2 (y: 480-720):   Layer 2 — Venture: PostlineAI (a topology)
 *   Bottom-left (y: 920+): Layer 1 — Event-driven nodes (dumb + agentic)
 *   Bottom-right (y: 920+):Layer 1 — Library tools
 *   Bottom (y: 1500):      Layer 1 — Substrate (trace-recorder)
 *
 * The point of this map is to show:
 *   1. Three clearly distinct layers with one-way dependency.
 *   2. Layer 1 is two flavors (event-driven nodes + plain library tools),
 *      with one substrate that wraps every call.
 *   3. Layer 2 is a thin composition (a venture topology).
 *   4. Layer 3 only reads the event stream; it never executes venture work.
 */

// ─── Types ──────────────────────────────────────────────────────────────────

export type V2Category =
  | "layer3_meta"
  | "event_bus"
  | "event"
  | "l2_venture_header"
  | "l2_stage"
  | "l1_node_dumb"
  | "l1_node_agentic"
  | "l1_lib"
  | "l1_substrate"
  | "layer_label";

export interface V2Node {
  id: string;
  title: string;
  type: V2Category;
  description: string;
  group: string;
}

export type V2EdgeKind =
  | "emits" // L1 node -> event on bus
  | "reacts" // event on bus -> L1 node (it subscribes)
  | "calls" // L1 node -> library tool (direct call)
  | "wraps" // substrate -> L1 node/lib (always-on)
  | "meta_reads" // Layer 3 -> event bus (read-only)
  | "venture_wires" // L2 stage -> L1 node (the venture composes)
  | "stage_flow" // L2 stage -> next L2 stage
  | "promotion"; // L3 -> L1 (proposes a new node)

export interface V2Edge {
  id: string;
  source: string;
  target: string;
  label?: string;
  edgeType: V2EdgeKind;
  animated?: boolean;
}

// ─── Nodes ──────────────────────────────────────────────────────────────────

export const v2Nodes: V2Node[] = [
  // ═══ Layer labels (decorative, non-interactive headings) ═══
  {
    id: "label_l3",
    title: "LAYER 3 — META",
    type: "layer_label",
    description: "Watches every venture's events. Thinks and guides. Never executes venture work.",
    group: "labels",
  },
  {
    id: "label_bus",
    title: "EVENT BUS",
    type: "layer_label",
    description: "The nervous system. Every meaningful action flows through here. Layer 3 reads it; Layer 1 nodes emit and subscribe.",
    group: "labels",
  },
  {
    id: "label_l2",
    title: "LAYER 2 — VENTURE: PostlineAI (topology)",
    type: "layer_label",
    description: "A composition of Layer 1 nodes wired by events, plus prompts/knowledge/ICP. May import Layer 1; never the reverse.",
    group: "labels",
  },
  {
    id: "label_l1_nodes",
    title: "LAYER 1 — EVENT-DRIVEN NODES",
    type: "layer_label",
    description: "React to events; do work; emit events. Some are dumb (API stitching), some are agentic (reason with an LLM).",
    group: "labels",
  },
  {
    id: "label_l1_libs",
    title: "LAYER 1 — LIBRARY TOOLS",
    type: "layer_label",
    description: "Plain function calls. API wrappers, gateways. No events. Imported and called by nodes.",
    group: "labels",
  },
  {
    id: "label_l1_sub",
    title: "LAYER 1 — SUBSTRATE",
    type: "layer_label",
    description: "Always-on, wraps every Layer 1 call automatically. Not invoked. Without this, Layer 3 has nothing to read.",
    group: "labels",
  },

  // ═══ Layer 3 — Meta ═══
  {
    id: "l3_meta",
    title: "Watch & Guide",
    type: "layer3_meta",
    description:
      "Reads the full event stream across every venture. Surfaces patterns, proposes promotions of repeated custom/ logic into Layer 1, and guides the founder on the highest-leverage next move. Read-only.",
    group: "layer3",
  },

  // ═══ Event Bus & key events ═══
  {
    id: "bus",
    title: "Event Bus",
    type: "event_bus",
    description: "The pub/sub backbone. In-memory at first; Redis Streams or Kafka when load demands it.",
    group: "bus",
  },
  {
    id: "ev_research_requested",
    title: "research.requested",
    type: "event",
    description: "Venture asks for a market research pass.",
    group: "events",
  },
  {
    id: "ev_pain_extracted",
    title: "pain.extracted",
    type: "event",
    description: "Customer pain points and frequencies extracted from a transcript.",
    group: "events",
  },
  {
    id: "ev_campaign_launched",
    title: "campaign.launched",
    type: "event",
    description: "An ad campaign is live on a platform.",
    group: "events",
  },
  {
    id: "ev_metrics_updated",
    title: "campaign.metrics.updated",
    type: "event",
    description: "Latest ad/landing metrics for a campaign.",
    group: "events",
  },
  {
    id: "ev_signal_verdict",
    title: "signal.verdict",
    type: "event",
    description: "Strong / weak / kill verdict on a signal, with confidence and explanation.",
    group: "events",
  },
  {
    id: "ev_input_captured",
    title: "input.captured",
    type: "event",
    description: "A customer's raw input (voice / bullets / email) normalized.",
    group: "events",
  },
  {
    id: "ev_post_drafted",
    title: "post.drafted",
    type: "event",
    description: "A LinkedIn post draft is ready (from a human or the agent).",
    group: "events",
  },
  {
    id: "ev_post_published",
    title: "post.published",
    type: "event",
    description: "A post is live on LinkedIn.",
    group: "events",
  },
  {
    id: "ev_feedback_captured",
    title: "feedback.captured",
    type: "event",
    description: "Normalized correction/rating feedback. Read by Layer 3.",
    group: "events",
  },
  {
    id: "ev_trace_captured",
    title: "trace.captured",
    type: "event",
    description: "Substrate-emitted record of every node call. The basis for every measurement.",
    group: "events",
  },

  // ═══ Layer 2 — PostlineAI venture topology (stages of the walkthrough) ═══
  {
    id: "v_thesis",
    title: "Hunch & Thesis",
    type: "l2_stage",
    description: "Capture a structured thesis with falsifiable assumptions. Walkthrough Step 1.",
    group: "venture",
  },
  {
    id: "v_research",
    title: "Desk Research",
    type: "l2_stage",
    description: "Cheapest evidence first: keyword volumes, competitors, pricing. Walkthrough Step 2.",
    group: "venture",
  },
  {
    id: "v_discovery",
    title: "Customer Discovery",
    type: "l2_stage",
    description: "Talk to the ICP, capture transcripts, extract pain. Walkthrough Step 3.",
    group: "venture",
  },
  {
    id: "v_demand_test",
    title: "Demand Test (Ads + Landing)",
    type: "l2_stage",
    description: "$200 LinkedIn + $200 Meta ads to a landing page. Walkthrough Step 4.",
    group: "venture",
  },
  {
    id: "v_woz",
    title: "Wizard-of-Oz Launch",
    type: "l2_stage",
    description: "3 paying customers; founder ghostwrites manually. Same nodes, human impl. Walkthrough Step 5.",
    group: "venture",
  },
  {
    id: "v_measure",
    title: "Measure & Decide",
    type: "l2_stage",
    description: "Engagement, leads, NPS — same signal-analyzer, new rubric. Walkthrough Step 6.",
    group: "venture",
  },
  {
    id: "v_agent",
    title: "Build the Agent",
    type: "l2_stage",
    description: "Swap post-drafter's impl from human to agent. Topology unchanged. Walkthrough Step 7.",
    group: "venture",
  },
  {
    id: "v_grow",
    title: "Grow",
    type: "l2_stage",
    description: "Same ad infrastructure, turned up. Zero new Layer 1 nodes. Walkthrough Step 8.",
    group: "venture",
  },

  // ═══ Layer 1 — Event-driven nodes ═══
  // Dumb nodes
  {
    id: "n_thesis_tracker",
    title: "thesis-tracker",
    type: "l1_node_dumb",
    description: "Bookkeeps the venture's thesis state as evidence arrives. Reacts: evidence.collected, pain.extracted, signal.verdict, survey.responded → Emits: thesis.state.updated.",
    group: "l1_nodes",
  },
  {
    id: "n_ad_campaign_runner",
    title: "ad-campaign-runner",
    type: "l1_node_dumb",
    description: "Reacts: campaign.requested → Calls: linkedin-ads-client / meta-ads-client → Emits: campaign.launched.",
    group: "l1_nodes",
  },
  {
    id: "n_ad_analytics",
    title: "ad-analytics-collector",
    type: "l1_node_dumb",
    description: "Reacts: campaign.launched, tick.daily → Calls: ads + analytics clients → Emits: campaign.metrics.updated.",
    group: "l1_nodes",
  },
  {
    id: "n_founder_notifier",
    title: "founder-notifier",
    type: "l1_node_dumb",
    description: "Reacts: signal.verdict, urgent=true events → Calls: slack-client / email-client → Emits: founder.notified.",
    group: "l1_nodes",
  },
  {
    id: "n_input_intake",
    title: "input-intake",
    type: "l1_node_dumb",
    description: "Reacts: inbound.received → Calls: transcription-client (when audio) → Emits: input.captured.",
    group: "l1_nodes",
  },
  {
    id: "n_human_review",
    title: "human-review-queue",
    type: "l1_node_dumb",
    description: "Reacts: any event tagged requires_human=true → Presents to a human → Emits: the original expected result event.",
    group: "l1_nodes",
  },
  {
    id: "n_post_scheduler",
    title: "post-scheduler",
    type: "l1_node_dumb",
    description: "Reacts: post.approved, tick.minute → Calls: linkedin-posting-client → Emits: post.scheduled, post.published.",
    group: "l1_nodes",
  },
  {
    id: "n_subscription",
    title: "subscription-manager",
    type: "l1_node_dumb",
    description: "Reacts: subscription.requested → Calls: billing-client (Stripe) → Emits: subscription.activated/cancelled.",
    group: "l1_nodes",
  },
  {
    id: "n_post_analytics",
    title: "post-analytics-collector",
    type: "l1_node_dumb",
    description: "Reacts: post.published, tick.daily → Calls: linkedin-posting-client → Emits: post.metrics.updated.",
    group: "l1_nodes",
  },
  {
    id: "n_survey",
    title: "customer-survey",
    type: "l1_node_dumb",
    description: "Reacts: survey.requested → Calls: email-client / slack-client → Emits: survey.responded.",
    group: "l1_nodes",
  },
  {
    id: "n_feedback",
    title: "feedback-collector",
    type: "l1_node_dumb",
    description: "Reacts: post.edited_by_human, post.rated, survey.responded → Emits: feedback.captured (for Layer 3).",
    group: "l1_nodes",
  },
  // Agentic nodes
  {
    id: "n_market_scanner",
    title: "market-scanner",
    type: "l1_node_agentic",
    description: "Agentic. Reacts: research.requested → Calls: semrush, web-search, llm-gateway → Emits: market.landscape.summarized.",
    group: "l1_nodes",
  },
  {
    id: "n_pain_extractor",
    title: "pain-extractor",
    type: "l1_node_agentic",
    description: "Agentic. Reacts: transcript.captured → Calls: llm-gateway → Emits: pain.extracted.",
    group: "l1_nodes",
  },
  {
    id: "n_signal_analyzer",
    title: "signal-analyzer",
    type: "l1_node_agentic",
    description: "Agentic. The single node that decides 'is this signal good?'. Reacts: campaign.metrics.updated, post.metrics.updated, survey.responded → Calls: llm-gateway → Emits: signal.verdict.",
    group: "l1_nodes",
  },
  {
    id: "n_post_drafter",
    title: "post-drafter",
    type: "l1_node_agentic",
    description: "Drafts LinkedIn posts in the customer's voice. Impl is human at first (Wizard-of-Oz), swapped to agent later — event interface unchanged. Reacts: input.captured → Emits: post.drafted.",
    group: "l1_nodes",
  },
  {
    id: "n_voice_profile",
    title: "voice-profile-builder",
    type: "l1_node_agentic",
    description: "Agentic. Reacts: onboarding.materials.received → Calls: llm-gateway → Emits: voice-profile.built.",
    group: "l1_nodes",
  },

  // ═══ Layer 1 — Library tools ═══
  {
    id: "lib_event_bus",
    title: "event-bus",
    type: "l1_lib",
    description: "Pub/sub mechanism every node depends on. The one universal library.",
    group: "l1_libs",
  },
  {
    id: "lib_llm",
    title: "llm-gateway",
    type: "l1_lib",
    description: "Multi-provider LLM access with retries and cost tracking. Used by every agentic node.",
    group: "l1_libs",
  },
  {
    id: "lib_semrush",
    title: "semrush-client",
    type: "l1_lib",
    description: "SEMrush API wrapper.",
    group: "l1_libs",
  },
  {
    id: "lib_search",
    title: "web-search-client",
    type: "l1_lib",
    description: "Search & fetch (Brave / Serper / Exa).",
    group: "l1_libs",
  },
  {
    id: "lib_calendar",
    title: "calendar-client",
    type: "l1_lib",
    description: "Calendly / Google Calendar wrapper.",
    group: "l1_libs",
  },
  {
    id: "lib_transcription",
    title: "transcription-client",
    type: "l1_lib",
    description: "Whisper / Deepgram wrapper.",
    group: "l1_libs",
  },
  {
    id: "lib_li_ads",
    title: "linkedin-ads-client",
    type: "l1_lib",
    description: "LinkedIn Marketing API wrapper.",
    group: "l1_libs",
  },
  {
    id: "lib_meta_ads",
    title: "meta-ads-client",
    type: "l1_lib",
    description: "Meta Marketing API wrapper.",
    group: "l1_libs",
  },
  {
    id: "lib_li_post",
    title: "linkedin-posting-client",
    type: "l1_lib",
    description: "LinkedIn content posting + read API (separate from ads).",
    group: "l1_libs",
  },
  {
    id: "lib_analytics",
    title: "analytics-client",
    type: "l1_lib",
    description: "PostHog / Plausible for landing-page analytics.",
    group: "l1_libs",
  },
  {
    id: "lib_inbound",
    title: "inbound-collector",
    type: "l1_lib",
    description: "Webhook + email-to-bucket inbound ingest.",
    group: "l1_libs",
  },
  {
    id: "lib_slack",
    title: "slack-client",
    type: "l1_lib",
    description: "Slack web API wrapper.",
    group: "l1_libs",
  },
  {
    id: "lib_email",
    title: "email-client",
    type: "l1_lib",
    description: "Postmark / Resend wrapper.",
    group: "l1_libs",
  },
  {
    id: "lib_billing",
    title: "billing-client",
    type: "l1_lib",
    description: "Stripe wrapper.",
    group: "l1_libs",
  },

  // ═══ Layer 1 — Substrate ═══
  {
    id: "sub_trace",
    title: "trace-recorder",
    type: "l1_substrate",
    description: "Wraps every Layer 1 call. Captures inputs, outputs, latency, cost. Emits trace.captured. The reason Layer 3 can exist.",
    group: "l1_sub",
  },
];

// ─── Edges ──────────────────────────────────────────────────────────────────

export const v2Edges: V2Edge[] = [
  // Layer 3 reads the bus
  { id: "e-l3-bus", source: "l3_meta", target: "bus", edgeType: "meta_reads", label: "reads", animated: true },

  // L3 promotion arrows (suggesting upgrades back to L1) — drawn subtly
  { id: "e-l3-prom1", source: "l3_meta", target: "n_signal_analyzer", edgeType: "promotion", label: "tunes" },
  { id: "e-l3-prom2", source: "l3_meta", target: "n_post_drafter", edgeType: "promotion", label: "tunes" },

  // L1 nodes emit to bus (a representative subset — the visually meaningful ones)
  { id: "e-emit-thesis", source: "n_thesis_tracker", target: "bus", edgeType: "emits" },
  { id: "e-emit-market", source: "n_market_scanner", target: "bus", edgeType: "emits" },
  { id: "e-emit-pain", source: "n_pain_extractor", target: "bus", edgeType: "emits" },
  { id: "e-emit-camp", source: "n_ad_campaign_runner", target: "bus", edgeType: "emits" },
  { id: "e-emit-metrics", source: "n_ad_analytics", target: "bus", edgeType: "emits" },
  { id: "e-emit-verdict", source: "n_signal_analyzer", target: "bus", edgeType: "emits" },
  { id: "e-emit-notif", source: "n_founder_notifier", target: "bus", edgeType: "emits" },
  { id: "e-emit-input", source: "n_input_intake", target: "bus", edgeType: "emits" },
  { id: "e-emit-draft", source: "n_post_drafter", target: "bus", edgeType: "emits" },
  { id: "e-emit-pub", source: "n_post_scheduler", target: "bus", edgeType: "emits" },
  { id: "e-emit-postm", source: "n_post_analytics", target: "bus", edgeType: "emits" },
  { id: "e-emit-fb", source: "n_feedback", target: "bus", edgeType: "emits" },
  { id: "e-emit-vp", source: "n_voice_profile", target: "bus", edgeType: "emits" },
  { id: "e-emit-survey", source: "n_survey", target: "bus", edgeType: "emits" },
  { id: "e-emit-sub", source: "n_subscription", target: "bus", edgeType: "emits" },
  { id: "e-emit-hr", source: "n_human_review", target: "bus", edgeType: "emits" },

  // Substrate emits trace.captured for every node
  { id: "e-sub-trace", source: "sub_trace", target: "bus", edgeType: "emits", animated: true, label: "trace.captured" },

  // Substrate wraps every node (visual: a few representative connections, dashed)
  { id: "e-sub-wrap1", source: "sub_trace", target: "n_signal_analyzer", edgeType: "wraps" },
  { id: "e-sub-wrap2", source: "sub_trace", target: "n_post_drafter", edgeType: "wraps" },
  { id: "e-sub-wrap3", source: "sub_trace", target: "n_ad_campaign_runner", edgeType: "wraps" },
  { id: "e-sub-wrap4", source: "sub_trace", target: "n_market_scanner", edgeType: "wraps" },

  // Library calls (representative — dashed, no events)
  { id: "e-call-1", source: "n_market_scanner", target: "lib_semrush", edgeType: "calls" },
  { id: "e-call-2", source: "n_market_scanner", target: "lib_search", edgeType: "calls" },
  { id: "e-call-3", source: "n_market_scanner", target: "lib_llm", edgeType: "calls" },
  { id: "e-call-4", source: "n_pain_extractor", target: "lib_llm", edgeType: "calls" },
  { id: "e-call-5", source: "n_signal_analyzer", target: "lib_llm", edgeType: "calls" },
  { id: "e-call-6", source: "n_ad_campaign_runner", target: "lib_li_ads", edgeType: "calls" },
  { id: "e-call-7", source: "n_ad_campaign_runner", target: "lib_meta_ads", edgeType: "calls" },
  { id: "e-call-8", source: "n_ad_analytics", target: "lib_analytics", edgeType: "calls" },
  { id: "e-call-9", source: "n_founder_notifier", target: "lib_slack", edgeType: "calls" },
  { id: "e-call-10", source: "n_founder_notifier", target: "lib_email", edgeType: "calls" },
  { id: "e-call-11", source: "n_post_scheduler", target: "lib_li_post", edgeType: "calls" },
  { id: "e-call-12", source: "n_post_drafter", target: "lib_llm", edgeType: "calls" },
  { id: "e-call-13", source: "n_subscription", target: "lib_billing", edgeType: "calls" },
  { id: "e-call-14", source: "n_post_analytics", target: "lib_li_post", edgeType: "calls" },
  { id: "e-call-15", source: "n_voice_profile", target: "lib_llm", edgeType: "calls" },
  { id: "e-call-16", source: "n_input_intake", target: "lib_transcription", edgeType: "calls" },
  { id: "e-call-17", source: "n_survey", target: "lib_email", edgeType: "calls" },

  // Layer 2 venture stage flow (the chronological walkthrough)
  { id: "e-v-1", source: "v_thesis", target: "v_research", edgeType: "stage_flow", label: "step 1→2" },
  { id: "e-v-2", source: "v_research", target: "v_discovery", edgeType: "stage_flow", label: "→3" },
  { id: "e-v-3", source: "v_discovery", target: "v_demand_test", edgeType: "stage_flow", label: "→4" },
  { id: "e-v-4", source: "v_demand_test", target: "v_woz", edgeType: "stage_flow", label: "→5" },
  { id: "e-v-5", source: "v_woz", target: "v_measure", edgeType: "stage_flow", label: "→6" },
  { id: "e-v-6", source: "v_measure", target: "v_agent", edgeType: "stage_flow", label: "→7" },
  { id: "e-v-7", source: "v_agent", target: "v_grow", edgeType: "stage_flow", label: "→8" },

  // Venture stages wire to L1 nodes (the topology — kept thin)
  { id: "e-vw-1", source: "v_thesis", target: "n_thesis_tracker", edgeType: "venture_wires" },
  { id: "e-vw-2", source: "v_research", target: "n_market_scanner", edgeType: "venture_wires" },
  { id: "e-vw-3", source: "v_discovery", target: "n_pain_extractor", edgeType: "venture_wires" },
  { id: "e-vw-4", source: "v_demand_test", target: "n_ad_campaign_runner", edgeType: "venture_wires" },
  { id: "e-vw-5", source: "v_demand_test", target: "n_signal_analyzer", edgeType: "venture_wires" },
  { id: "e-vw-6", source: "v_woz", target: "n_post_drafter", edgeType: "venture_wires" },
  { id: "e-vw-7", source: "v_woz", target: "n_human_review", edgeType: "venture_wires" },
  { id: "e-vw-8", source: "v_woz", target: "n_subscription", edgeType: "venture_wires" },
  { id: "e-vw-9", source: "v_measure", target: "n_post_analytics", edgeType: "venture_wires" },
  { id: "e-vw-10", source: "v_measure", target: "n_survey", edgeType: "venture_wires" },
  { id: "e-vw-11", source: "v_agent", target: "n_voice_profile", edgeType: "venture_wires" },
  { id: "e-vw-12", source: "v_agent", target: "n_feedback", edgeType: "venture_wires" },
  { id: "e-vw-13", source: "v_grow", target: "n_ad_campaign_runner", edgeType: "venture_wires", label: "reuse" },
];

// ─── Layout positions (~2400 x 1700) ────────────────────────────────────────

export const v2Positions: Record<string, { x: number; y: number }> = {
  // Layer labels
  label_l3: { x: 30, y: 50 },
  label_bus: { x: 30, y: 290 },
  label_l2: { x: 30, y: 460 },
  label_l1_nodes: { x: 30, y: 880 },
  label_l1_libs: { x: 1700, y: 880 },
  label_l1_sub: { x: 30, y: 1500 },

  // Layer 3
  l3_meta: { x: 1100, y: 90 },

  // Event bus + events on it (horizontal rail at y ~ 320)
  bus: { x: 1100, y: 320 },
  ev_research_requested: { x: 200, y: 360 },
  ev_pain_extracted: { x: 420, y: 360 },
  ev_campaign_launched: { x: 640, y: 360 },
  ev_metrics_updated: { x: 880, y: 360 },
  ev_signal_verdict: { x: 1140, y: 380 },
  ev_input_captured: { x: 1360, y: 360 },
  ev_post_drafted: { x: 1560, y: 360 },
  ev_post_published: { x: 1760, y: 360 },
  ev_feedback_captured: { x: 1960, y: 360 },
  ev_trace_captured: { x: 2160, y: 360 },

  // Layer 2 venture topology (8 stage pills, y ~ 540, then flow line at y ~ 700)
  v_thesis: { x: 110, y: 560 },
  v_research: { x: 360, y: 560 },
  v_discovery: { x: 610, y: 560 },
  v_demand_test: { x: 870, y: 560 },
  v_woz: { x: 1180, y: 560 },
  v_measure: { x: 1450, y: 560 },
  v_agent: { x: 1700, y: 560 },
  v_grow: { x: 1970, y: 560 },

  // Layer 1 — Event-driven nodes (left side, y ~ 940 onward, grid)
  // Dumb (column 1-2), Agentic (column 3)
  n_thesis_tracker: { x: 80, y: 970 },
  n_ad_campaign_runner: { x: 320, y: 970 },
  n_ad_analytics: { x: 560, y: 970 },
  n_founder_notifier: { x: 800, y: 970 },
  n_input_intake: { x: 80, y: 1090 },
  n_human_review: { x: 320, y: 1090 },
  n_post_scheduler: { x: 560, y: 1090 },
  n_subscription: { x: 800, y: 1090 },
  n_post_analytics: { x: 80, y: 1210 },
  n_survey: { x: 320, y: 1210 },
  n_feedback: { x: 560, y: 1210 },

  // Agentic
  n_market_scanner: { x: 80, y: 1330 },
  n_pain_extractor: { x: 320, y: 1330 },
  n_signal_analyzer: { x: 560, y: 1330 },
  n_post_drafter: { x: 800, y: 1330 },
  n_voice_profile: { x: 1040, y: 1330 },

  // Layer 1 — Library tools (right side, y ~ 940 onward, grid)
  lib_event_bus: { x: 1740, y: 970 },
  lib_llm: { x: 1900, y: 970 },
  lib_semrush: { x: 2060, y: 970 },
  lib_search: { x: 2220, y: 970 },
  lib_calendar: { x: 1740, y: 1070 },
  lib_transcription: { x: 1900, y: 1070 },
  lib_li_ads: { x: 2060, y: 1070 },
  lib_meta_ads: { x: 2220, y: 1070 },
  lib_li_post: { x: 1740, y: 1170 },
  lib_analytics: { x: 1900, y: 1170 },
  lib_inbound: { x: 2060, y: 1170 },
  lib_slack: { x: 2220, y: 1170 },
  lib_email: { x: 1740, y: 1270 },
  lib_billing: { x: 1900, y: 1270 },

  // Substrate (bottom)
  sub_trace: { x: 1100, y: 1530 },
};

// ─── Story walk: 8 venture steps ────────────────────────────────────────────

export const v2Story: { id: string; text: string }[] = [
  { id: "v_thesis", text: "Step 1 — The founder writes a structured thesis. We derive thesis-tracker (dumb node) + the event-bus library + the trace-recorder substrate." },
  { id: "v_research", text: "Step 2 — Desk research: keyword volumes + competitor scan. Derives market-scanner (agentic) + semrush-client, web-search-client, llm-gateway libraries." },
  { id: "v_discovery", text: "Step 3 — Customer interviews. Derives pain-extractor (agentic) + calendar-client, transcription-client. thesis-tracker is reused via event subscription." },
  { id: "v_demand_test", text: "Step 4 — $200 LinkedIn + $200 Meta ads to a landing page. Derives ad-campaign-runner, ad-analytics-collector, signal-analyzer, founder-notifier + the ads/analytics/slack/email libraries." },
  { id: "v_woz", text: "Step 5 — Three paying customers; the founder ghostwrites manually. Derives input-intake, post-drafter (human impl), human-review-queue, post-scheduler, subscription-manager + their libraries." },
  { id: "v_measure", text: "Step 6 — Measure engagement, leads, NPS. Derives post-analytics-collector + customer-survey. signal-analyzer is generalized — same node, new rubric. First refactor." },
  { id: "v_agent", text: "Step 7 — Build the actual agent. post-drafter's impl swaps from human to agent — event interface unchanged. Derives voice-profile-builder + feedback-collector." },
  { id: "v_grow", text: "Step 8 — Scale to 30 customers. ZERO new Layer 1 nodes. The validation infrastructure IS the production infrastructure. The flywheel is paying off." },
];

// ─── Filters ────────────────────────────────────────────────────────────────

export const V2_FILTERS = [
  { key: null, label: "All" },
  { key: "layer3", label: "Layer 3" },
  { key: "bus", label: "Event Bus" },
  { key: "events", label: "Events" },
  { key: "venture", label: "Venture (L2)" },
  { key: "l1_nodes", label: "L1 Nodes" },
  { key: "l1_libs", label: "L1 Libs" },
  { key: "l1_sub", label: "Substrate" },
] as const;
