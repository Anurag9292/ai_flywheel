/**
 * AI Flywheel Vision Map V2 — Premium Story-Driven Canvas Data
 *
 * Three-layer layout (~2200x1800 canvas, default zoom 0.5):
 *   Top (y: 50-80):         Execution Spine — System Heartbeat
 *   Center (y: 350-500):    Main Venture Lifecycle — HERO path (gentle arc)
 *   Left (y: 650-950):      Business Intelligence (green/teal)
 *   Right (y: 650-950):     Technical Execution (blue)
 *   Bottom-center (y: 1050-1200): Flywheel compounding loop (gold)
 *   Bottom row (y: 1350-1500):    Layer 1 Foundation + Layer 2 Orchestrators
 *   Bottom-right (y: 1350):       Interaction Channels
 */

// ─── Types ───────────────────────────────────────────────────────────────────

export type NodeCategory =
  | "founder_state"
  | "lifecycle_stage"
  | "business_intelligence"
  | "technical_execution"
  | "execution_spine"
  | "system"
  | "architecture_layer"
  | "validation_checkpoint"
  | "decision_point"
  | "feedback_loop"
  | "interaction_channel"
  | "outcome"
  | "kill_signal"
  | "flywheel";

export interface VisionNodeData {
  id: string;
  title: string;
  type: NodeCategory;
  description: string;
  group: string;
  layer?: string;
}

export interface VisionEdgeData {
  id: string;
  source: string;
  target: string;
  label?: string;
  animated?: boolean;
  edgeType: "hero" | "feedback" | "spine" | "kill" | "module" | "foundation" | "flywheel";
}

// ─── Nodes ───────────────────────────────────────────────────────────────────

export const visionNodes: VisionNodeData[] = [
  // ═══ Super Founder (Golden special node) ═══
  {
    id: "super_founder",
    title: "Super Founder",
    type: "founder_state",
    description: "The human operator makes the high-leverage 5% decisions.",
    group: "lifecycle",
  },

  // ═══ Main Lifecycle — HERO PATH ═══
  {
    id: "founder_hunch",
    title: "Founder Hunch",
    type: "lifecycle_stage",
    description: "Gut feeling meets pattern recognition. A pain, signal, or opportunity worth investigating.",
    group: "lifecycle",
  },
  {
    id: "discover",
    title: "Discover",
    type: "lifecycle_stage",
    description: "Research the market, detect signals, identify customer pain points.",
    group: "lifecycle",
  },
  {
    id: "validate_demand",
    title: "Validate Demand",
    type: "lifecycle_stage",
    description: "Customer evidence: interviews, waitlists, prototype tests, conversion data.",
    group: "lifecycle",
  },
  {
    id: "design",
    title: "Design",
    type: "lifecycle_stage",
    description: "Product experience, AI interaction patterns, feature priority, UX flows.",
    group: "lifecycle",
  },
  {
    id: "build",
    title: "Build",
    type: "lifecycle_stage",
    description: "Configure agent networks: prompts, tools, memory, policies, orchestration.",
    group: "lifecycle",
  },
  {
    id: "deploy",
    title: "Deploy",
    type: "lifecycle_stage",
    description: "Ship to real users with monitoring, canary releases, and auto-healing.",
    group: "lifecycle",
  },
  {
    id: "learn",
    title: "Learn",
    type: "lifecycle_stage",
    description: "Capture traces, costs, feedback, performance metrics from live usage.",
    group: "lifecycle",
  },
  {
    id: "extract",
    title: "Extract",
    type: "lifecycle_stage",
    description: "Winning strategies extracted as reusable patterns for cross-venture use.",
    group: "lifecycle",
  },
  {
    id: "compound",
    title: "Compound",
    type: "lifecycle_stage",
    description: "Intelligence compounds. Winning patterns become platform infrastructure.",
    group: "lifecycle",
  },
  {
    id: "next_venture",
    title: "Next Venture",
    type: "outcome",
    description: "Next venture starts with 60-80% of the work already done. 5 weeks becomes 1.",
    group: "lifecycle",
  },

  // ═══ Kill Path ═══
  {
    id: "decision_go_kill",
    title: "Go / Kill?",
    type: "decision_point",
    description: "Cheapest evidence first. Is there signal or not?",
    group: "validation",
  },
  {
    id: "kill_early",
    title: "Kill Early",
    type: "kill_signal",
    description: "Cheapest evidence first. Kill early, kill cheap. Preserve capital and learnings.",
    group: "validation",
  },

  // ═══ Execution Spine (Top — System Heartbeat) ═══
  {
    id: "spine_event",
    title: "Event",
    type: "execution_spine",
    description: "Trigger: user action, schedule, external signal, webhook.",
    group: "spine",
  },
  {
    id: "spine_task",
    title: "Task",
    type: "execution_spine",
    description: "Work unit with inputs, outputs, success criteria, budget.",
    group: "spine",
  },
  {
    id: "spine_agent",
    title: "Agent/Tool",
    type: "execution_spine",
    description: "LLM call, API hit, computation — policy-gated execution.",
    group: "spine",
  },
  {
    id: "spine_trace",
    title: "Trace",
    type: "execution_spine",
    description: "Immutable execution history, cost-attributed, version-tagged.",
    group: "spine",
  },
  {
    id: "spine_metric",
    title: "Metric",
    type: "execution_spine",
    description: "Accuracy, cost, latency, conversion, satisfaction scores.",
    group: "spine",
  },
  {
    id: "spine_feedback",
    title: "Feedback",
    type: "execution_spine",
    description: "Human or automated judgment, timestamped and attributed.",
    group: "spine",
  },
  {
    id: "spine_experiment",
    title: "Experiment",
    type: "execution_spine",
    description: "Statistical aggregation, A/B tests, decision-ready reports.",
    group: "spine",
  },
  {
    id: "spine_pattern",
    title: "Pattern",
    type: "execution_spine",
    description: "Extracted winning strategy, context-tagged, reusable.",
    group: "spine",
  },

  // ═══ Business Intelligence (Left Cluster — green/teal) ═══
  {
    id: "customer_discovery",
    title: "Customer Discovery",
    type: "business_intelligence",
    description: "JTBD interviews, pain extraction, persona synthesis.",
    group: "business",
  },
  {
    id: "hypothesis_testing",
    title: "Hypothesis Testing",
    type: "business_intelligence",
    description: "Structured thesis, evidence ladder, Bayesian confidence scoring.",
    group: "business",
  },
  {
    id: "market_signals",
    title: "Market Signals",
    type: "business_intelligence",
    description: "Competitor monitoring, trend detection, opportunity scoring.",
    group: "business",
  },
  {
    id: "icp_definition",
    title: "ICP Definition",
    type: "business_intelligence",
    description: "Behavioral and firmographic customer profiling.",
    group: "business",
  },
  {
    id: "offer_design",
    title: "Offer Design",
    type: "business_intelligence",
    description: "Positioning, pricing, landing copy, objection rebuttals.",
    group: "business",
  },

  // ═══ Technical Execution (Right Cluster — blue) ═══
  {
    id: "agent_orchestration",
    title: "Agent Orchestration",
    type: "technical_execution",
    description: "Multi-agent coordination: delegation, debate, consensus protocols.",
    group: "technical",
  },
  {
    id: "prompt_management",
    title: "Prompt Management",
    type: "technical_execution",
    description: "Version-controlled prompts with A/B testing and rollback.",
    group: "technical",
  },
  {
    id: "tool_runtime",
    title: "Tool Runtime",
    type: "technical_execution",
    description: "Typed tools, API integrations, credential management, sandboxing.",
    group: "technical",
  },
  {
    id: "memory_engine",
    title: "Memory Engine",
    type: "technical_execution",
    description: "Working, episodic, semantic, procedural memory layers.",
    group: "technical",
  },
  {
    id: "cost_optimization",
    title: "Cost Optimization",
    type: "technical_execution",
    description: "Per-token tracking, smart routing, budget alerts, model switching.",
    group: "technical",
  },

  // ═══ Flywheel Loop (Bottom Center — gold/amber) ═══
  {
    id: "fw_venture_runs",
    title: "Venture Runs",
    type: "flywheel",
    description: "Each venture generates real-world execution data.",
    group: "flywheel",
  },
  {
    id: "fw_edge_cases",
    title: "Edge Cases Found",
    type: "flywheel",
    description: "Production reveals edge cases no simulation can predict.",
    group: "flywheel",
  },
  {
    id: "fw_utils_improve",
    title: "Utils Improve",
    type: "flywheel",
    description: "Shared utilities hardened by real usage patterns.",
    group: "flywheel",
  },
  {
    id: "fw_patterns_accumulate",
    title: "Patterns Accumulate",
    type: "flywheel",
    description: "Winning strategies extracted and catalogued.",
    group: "flywheel",
  },
  {
    id: "fw_agents_sharpen",
    title: "Agents Sharpen",
    type: "flywheel",
    description: "Agent prompts, tools, and policies refined from data.",
    group: "flywheel",
  },
  {
    id: "fw_benchmarks_grow",
    title: "Benchmarks Grow",
    type: "flywheel",
    description: "Evaluation suites expand with each venture's test cases.",
    group: "flywheel",
  },
  {
    id: "fw_next_faster",
    title: "Next Venture Faster",
    type: "flywheel",
    description: "Platform improvements compound into launch velocity.",
    group: "flywheel",
  },

  // ═══ Validation Checkpoints ═══
  {
    id: "val_desk",
    title: "Desk Research",
    type: "validation_checkpoint",
    description: "Free. What does the market look like?",
    group: "validation",
  },
  {
    id: "val_conversations",
    title: "Conversations",
    type: "validation_checkpoint",
    description: "Time only. Do people have this pain?",
    group: "validation",
  },
  {
    id: "val_landing",
    title: "Landing Page",
    type: "validation_checkpoint",
    description: "Hours. Will people sign up?",
    group: "validation",
  },
  {
    id: "val_wizard",
    title: "Wizard-of-Oz",
    type: "validation_checkpoint",
    description: "Days. Can you deliver value manually?",
    group: "validation",
  },
  {
    id: "val_mvp",
    title: "MVP",
    type: "validation_checkpoint",
    description: "Weeks. Real agents, real users, real metrics.",
    group: "validation",
  },

  // ═══ Layer 1 Foundation (8 system pills) ═══
  {
    id: "sys_kernel",
    title: "Core Kernel",
    type: "system",
    description: "Config, identity, events, task queues, tracing infrastructure.",
    group: "systems",
    layer: "foundation",
  },
  {
    id: "sys_agent_runtime",
    title: "LLM & Agent Runtime",
    type: "system",
    description: "LLM routing, prompts, orchestration, tools, memory management.",
    group: "systems",
    layer: "foundation",
  },
  {
    id: "sys_data",
    title: "Data & Knowledge",
    type: "system",
    description: "Ingestion, embeddings, knowledge graphs, vector stores.",
    group: "systems",
    layer: "foundation",
  },
  {
    id: "sys_ml",
    title: "ML & Evaluation",
    type: "system",
    description: "Features, training, evaluation, simulation, benchmarks.",
    group: "systems",
    layer: "foundation",
  },
  {
    id: "sys_product_intel",
    title: "Product & Market Intel",
    type: "system",
    description: "Market signals, discovery, thesis validation, offer design.",
    group: "systems",
    layer: "foundation",
  },
  {
    id: "sys_experimentation",
    title: "Experimentation",
    type: "system",
    description: "A/B testing, metrics, cost optimization, statistical analysis.",
    group: "systems",
    layer: "foundation",
  },
  {
    id: "sys_deployment",
    title: "Deployment",
    type: "system",
    description: "Canary releases, monitoring, incident response, auto-healing.",
    group: "systems",
    layer: "foundation",
  },
  {
    id: "sys_cross_venture",
    title: "Cross-Venture Learning",
    type: "system",
    description: "Pattern library, meta-learning, velocity tracking, knowledge transfer.",
    group: "systems",
    layer: "foundation",
  },

  // ═══ Layer 2 — Venture Orchestrators ═══
  {
    id: "layer2_v1",
    title: "Venture 1 (0% reuse)",
    type: "architecture_layer",
    description: "First venture: everything built from scratch. Maximum learning.",
    group: "architecture",
    layer: "orchestrator",
  },
  {
    id: "layer2_v3",
    title: "Venture 3 (~60%)",
    type: "architecture_layer",
    description: "Third venture: 60% reuse from platform patterns and agents.",
    group: "architecture",
    layer: "orchestrator",
  },
  {
    id: "layer2_v5",
    title: "Venture 5 (~80%)",
    type: "architecture_layer",
    description: "Fifth venture: 80% reuse. Launch in days, not weeks.",
    group: "architecture",
    layer: "orchestrator",
  },
  {
    id: "layer2_future",
    title: "Future N",
    type: "architecture_layer",
    description: "Convergence: near-instant venture scaffolding from accumulated intelligence.",
    group: "architecture",
    layer: "orchestrator",
  },

  // ═══ Interaction Channels (Bottom-Right) ═══
  {
    id: "channel_slack",
    title: "Slack",
    type: "interaction_channel",
    description: "Conversational interface for founder commands and agent updates.",
    group: "channels",
  },
  {
    id: "channel_web",
    title: "Web Dashboard",
    type: "interaction_channel",
    description: "Visual control center for metrics, agents, and venture state.",
    group: "channels",
  },
  {
    id: "channel_cli",
    title: "CLI",
    type: "interaction_channel",
    description: "Developer-first interface for power users and automation.",
    group: "channels",
  },
  {
    id: "channel_router",
    title: "Router",
    type: "interaction_channel",
    description: "Intelligent routing: maps intents to the right agent or workflow.",
    group: "channels",
  },
];

// ─── Edges ───────────────────────────────────────────────────────────────────

export const visionEdges: VisionEdgeData[] = [
  // ═══ HERO PATH — Main Lifecycle ═══
  { id: "e-sf-hunch", source: "super_founder", target: "founder_hunch", edgeType: "hero", label: "initiates" },
  { id: "e-hunch-discover", source: "founder_hunch", target: "discover", edgeType: "hero" },
  { id: "e-discover-validate", source: "discover", target: "validate_demand", edgeType: "hero", label: "evidence" },
  { id: "e-validate-design", source: "validate_demand", target: "design", edgeType: "hero", label: "go" },
  { id: "e-design-build", source: "design", target: "build", edgeType: "hero", label: "spec" },
  { id: "e-build-deploy", source: "build", target: "deploy", edgeType: "hero", label: "ship" },
  { id: "e-deploy-learn", source: "deploy", target: "learn", edgeType: "hero", label: "live" },
  { id: "e-learn-extract", source: "learn", target: "extract", edgeType: "hero", label: "data" },
  { id: "e-extract-compound", source: "extract", target: "compound", edgeType: "hero", label: "patterns" },
  { id: "e-compound-next", source: "compound", target: "next_venture", edgeType: "hero", label: "faster" },

  // ═══ Feedback loops (gold dashed, animated) ═══
  { id: "e-fb-learn-validate", source: "learn", target: "validate_demand", edgeType: "feedback", animated: true },
  { id: "e-fb-extract-discover", source: "extract", target: "discover", edgeType: "feedback", animated: true },
  { id: "e-fb-compound-build", source: "compound", target: "build", edgeType: "feedback", animated: true },
  { id: "e-fb-next-hunch", source: "next_venture", target: "founder_hunch", edgeType: "feedback", animated: true },

  // ═══ Super Founder connections ═══
  { id: "e-sf-validate", source: "super_founder", target: "validate_demand", edgeType: "module" },
  { id: "e-sf-kill", source: "super_founder", target: "kill_early", edgeType: "module" },
  { id: "e-sf-next", source: "super_founder", target: "next_venture", edgeType: "module" },

  // ═══ Kill Path ═══
  { id: "e-validate-decision", source: "validate_demand", target: "decision_go_kill", edgeType: "kill", label: "assess" },
  { id: "e-decision-kill", source: "decision_go_kill", target: "kill_early", edgeType: "kill", label: "no signal" },

  // ═══ Execution Spine chain ═══
  { id: "e-spine-1", source: "spine_event", target: "spine_task", edgeType: "spine" },
  { id: "e-spine-2", source: "spine_task", target: "spine_agent", edgeType: "spine" },
  { id: "e-spine-3", source: "spine_agent", target: "spine_trace", edgeType: "spine" },
  { id: "e-spine-4", source: "spine_trace", target: "spine_metric", edgeType: "spine" },
  { id: "e-spine-5", source: "spine_metric", target: "spine_feedback", edgeType: "spine" },
  { id: "e-spine-6", source: "spine_feedback", target: "spine_experiment", edgeType: "spine" },
  { id: "e-spine-7", source: "spine_experiment", target: "spine_pattern", edgeType: "spine" },
  { id: "e-spine-loop", source: "spine_pattern", target: "spine_event", edgeType: "feedback", animated: true },

  // ═══ Spine → Lifecycle connections ═══
  { id: "e-spine-build", source: "build", target: "spine_agent", edgeType: "module" },
  { id: "e-spine-deploy", source: "deploy", target: "spine_trace", edgeType: "module" },
  { id: "e-spine-learn", source: "learn", target: "spine_metric", edgeType: "module" },
  { id: "e-spine-extract", source: "extract", target: "spine_pattern", edgeType: "module" },

  // ═══ Business Intelligence → Lifecycle ═══
  { id: "e-biz-discover1", source: "customer_discovery", target: "discover", edgeType: "module" },
  { id: "e-biz-discover2", source: "market_signals", target: "discover", edgeType: "module" },
  { id: "e-biz-validate1", source: "hypothesis_testing", target: "validate_demand", edgeType: "module" },
  { id: "e-biz-validate2", source: "icp_definition", target: "validate_demand", edgeType: "module" },
  { id: "e-biz-design", source: "offer_design", target: "design", edgeType: "module" },

  // ═══ Technical Execution → Lifecycle ═══
  { id: "e-tech-build1", source: "agent_orchestration", target: "build", edgeType: "module" },
  { id: "e-tech-build2", source: "prompt_management", target: "build", edgeType: "module" },
  { id: "e-tech-build3", source: "memory_engine", target: "build", edgeType: "module" },
  { id: "e-tech-deploy", source: "tool_runtime", target: "deploy", edgeType: "module" },
  { id: "e-tech-learn", source: "cost_optimization", target: "learn", edgeType: "module" },

  // ═══ Validation ladder ═══
  { id: "e-val-1", source: "val_desk", target: "val_conversations", edgeType: "module" },
  { id: "e-val-2", source: "val_conversations", target: "val_landing", edgeType: "module" },
  { id: "e-val-3", source: "val_landing", target: "val_wizard", edgeType: "module" },
  { id: "e-val-4", source: "val_wizard", target: "val_mvp", edgeType: "module" },
  { id: "e-val-to-lifecycle", source: "val_mvp", target: "validate_demand", edgeType: "module" },

  // ═══ Flywheel loop (gold, animated) ═══
  { id: "e-fw-1", source: "fw_venture_runs", target: "fw_edge_cases", edgeType: "flywheel", animated: true },
  { id: "e-fw-2", source: "fw_edge_cases", target: "fw_utils_improve", edgeType: "flywheel", animated: true },
  { id: "e-fw-3", source: "fw_utils_improve", target: "fw_patterns_accumulate", edgeType: "flywheel", animated: true },
  { id: "e-fw-4", source: "fw_patterns_accumulate", target: "fw_agents_sharpen", edgeType: "flywheel", animated: true },
  { id: "e-fw-5", source: "fw_agents_sharpen", target: "fw_benchmarks_grow", edgeType: "flywheel", animated: true },
  { id: "e-fw-6", source: "fw_benchmarks_grow", target: "fw_next_faster", edgeType: "flywheel", animated: true },
  { id: "e-fw-7", source: "fw_next_faster", target: "fw_venture_runs", edgeType: "flywheel", animated: true },

  // ═══ Foundation connections (subtle) ═══
  { id: "e-found-1", source: "sys_agent_runtime", target: "agent_orchestration", edgeType: "foundation" },
  { id: "e-found-2", source: "sys_product_intel", target: "market_signals", edgeType: "foundation" },
  { id: "e-found-3", source: "sys_data", target: "memory_engine", edgeType: "foundation" },
  { id: "e-found-4", source: "sys_ml", target: "cost_optimization", edgeType: "foundation" },
  { id: "e-found-5", source: "sys_experimentation", target: "hypothesis_testing", edgeType: "foundation" },
  { id: "e-found-6", source: "sys_cross_venture", target: "compound", edgeType: "foundation" },

  // ═══ Interaction Channels ═══
  { id: "e-ch-slack", source: "channel_slack", target: "channel_router", edgeType: "module" },
  { id: "e-ch-web", source: "channel_web", target: "channel_router", edgeType: "module" },
  { id: "e-ch-cli", source: "channel_cli", target: "channel_router", edgeType: "module" },
  { id: "e-ch-router-spine", source: "channel_router", target: "spine_event", edgeType: "module" },
];

// ─── Layout Positions (~2200x1800 canvas) ────────────────────────────────────

export const nodePositions: Record<string, { x: number; y: number }> = {
  // ═══ Execution Spine (Top — y: 60) ═══
  spine_event: { x: 180, y: 60 },
  spine_task: { x: 430, y: 60 },
  spine_agent: { x: 680, y: 60 },
  spine_trace: { x: 930, y: 60 },
  spine_metric: { x: 1180, y: 60 },
  spine_feedback: { x: 1430, y: 60 },
  spine_experiment: { x: 1680, y: 60 },
  spine_pattern: { x: 1930, y: 60 },

  // ═══ Super Founder (left, connected to hero path) ═══
  super_founder: { x: 50, y: 350 },

  // ═══ Main Lifecycle — HERO (gentle arc, y: 350-500) ═══
  founder_hunch: { x: 250, y: 380 },
  discover: { x: 450, y: 350 },
  validate_demand: { x: 680, y: 380 },
  design: { x: 900, y: 350 },
  build: { x: 1120, y: 380 },
  deploy: { x: 1340, y: 350 },
  learn: { x: 1540, y: 380 },
  extract: { x: 1740, y: 350 },
  compound: { x: 1920, y: 380 },
  next_venture: { x: 2100, y: 350 },

  // ═══ Kill Path (below validate_demand) ═══
  decision_go_kill: { x: 680, y: 520 },
  kill_early: { x: 680, y: 640 },

  // ═══ Business Intelligence (Left — y: 650-950, x: 50-450) ═══
  customer_discovery: { x: 80, y: 680 },
  hypothesis_testing: { x: 300, y: 680 },
  market_signals: { x: 80, y: 820 },
  icp_definition: { x: 300, y: 820 },
  offer_design: { x: 190, y: 950 },

  // ═══ Technical Execution (Right — y: 650-950, x: 1400-1850) ═══
  agent_orchestration: { x: 1430, y: 680 },
  prompt_management: { x: 1670, y: 680 },
  tool_runtime: { x: 1430, y: 820 },
  memory_engine: { x: 1670, y: 820 },
  cost_optimization: { x: 1550, y: 950 },

  // ═══ Validation Checkpoints (near validate_demand) ═══
  val_desk: { x: 500, y: 700 },
  val_conversations: { x: 500, y: 800 },
  val_landing: { x: 500, y: 900 },
  val_wizard: { x: 500, y: 1000 },
  val_mvp: { x: 500, y: 1100 },

  // ═══ Flywheel Loop (Bottom Center — circular, y: 1050-1200) ═══
  fw_venture_runs: { x: 750, y: 1060 },
  fw_edge_cases: { x: 920, y: 1100 },
  fw_utils_improve: { x: 1070, y: 1170 },
  fw_patterns_accumulate: { x: 1070, y: 1060 },
  fw_agents_sharpen: { x: 920, y: 1200 },
  fw_benchmarks_grow: { x: 750, y: 1170 },
  fw_next_faster: { x: 910, y: 1050 },

  // ═══ Layer 2 — Venture Orchestrators (y: 1350) ═══
  layer2_v1: { x: 200, y: 1350 },
  layer2_v3: { x: 500, y: 1350 },
  layer2_v5: { x: 800, y: 1350 },
  layer2_future: { x: 1100, y: 1350 },

  // ═══ Layer 1 Foundation (y: 1500) ═══
  sys_kernel: { x: 50, y: 1500 },
  sys_agent_runtime: { x: 300, y: 1500 },
  sys_data: { x: 550, y: 1500 },
  sys_ml: { x: 780, y: 1500 },
  sys_product_intel: { x: 1010, y: 1500 },
  sys_experimentation: { x: 1270, y: 1500 },
  sys_deployment: { x: 1520, y: 1500 },
  sys_cross_venture: { x: 1770, y: 1500 },

  // ═══ Interaction Channels (Bottom-Right — y: 1350, x: 1600-2000) ═══
  channel_slack: { x: 1620, y: 1350 },
  channel_web: { x: 1800, y: 1350 },
  channel_cli: { x: 1980, y: 1350 },
  channel_router: { x: 1800, y: 1480 },
};

// ─── Simulation Sequence (10 steps for story mode) ───────────────────────────

export const simulationSequence: string[] = [
  "founder_hunch",
  "discover",
  "validate_demand",
  "design",
  "build",
  "deploy",
  "learn",
  "extract",
  "compound",
  "next_venture",
];

// ─── Story Text — step descriptions for the story card ───────────────────────

export const storyText: Record<string, string> = {
  founder_hunch: "The founder has a hunch \u2014 a pain, signal, or opportunity worth investigating.",
  discover: "Exploring the opportunity space. Market signals, competitor gaps, customer pain.",
  validate_demand: "Validating demand with customer evidence. Interviews, waitlists, prototype tests.",
  design: "Designing the product experience: UX flows, agent architecture, feature priority.",
  build: "Configuring agent networks: prompts, tools, memory, policies, orchestration.",
  deploy: "Shipping to real users with monitoring, canary releases, and auto-healing.",
  learn: "Learning from every trace, metric, and feedback signal. What worked? What didn't?",
  extract: "Extracting reusable patterns. Winning strategies become shared infrastructure.",
  compound: "Intelligence compounds. Winning patterns become platform infrastructure.",
  next_venture: "Next venture starts with 60-80% of the work already done.",
};

// ─── Filter Definitions ──────────────────────────────────────────────────────

export const FILTER_OPTIONS = [
  { key: null, label: "All" },
  { key: "lifecycle", label: "Lifecycle" },
  { key: "founder_state", label: "Founder" },
  { key: "business", label: "Business Intel" },
  { key: "technical", label: "Technical" },
  { key: "spine", label: "Spine" },
  { key: "flywheel", label: "Flywheel" },
  { key: "validation", label: "Validation" },
  { key: "systems", label: "Systems" },
  { key: "architecture", label: "Architecture" },
  { key: "channels", label: "Channels" },
] as const;
