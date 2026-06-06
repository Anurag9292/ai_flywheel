/**
 * AI Flywheel Vision Map — Graph Data
 * 
 * Edit nodes and edges here to modify the vision visualization.
 * Categories determine visual styling of each node.
 */

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
  | "outcome";

export interface VisionNodeData {
  id: string;
  title: string;
  type: NodeCategory;
  description: string;
  group?: string;
}

export interface VisionEdgeData {
  id: string;
  source: string;
  target: string;
  label?: string;
  animated?: boolean;
  type?: "default" | "feedback" | "spine";
}

// =============================================
// NODES
// =============================================

export const visionNodes: VisionNodeData[] = [
  // --- Main Lifecycle ---
  { id: "founder_hunch", title: "Founder Hunch", type: "founder_state", description: "The starting point: a possible opportunity, pain, or product idea. Gut feeling meets pattern recognition.", group: "lifecycle" },
  { id: "discover_opportunity", title: "Discover Opportunity", type: "lifecycle_stage", description: "Research the market, detect signals, identify customer pain, and define the opportunity space.", group: "lifecycle" },
  { id: "validate_demand", title: "Validate Demand", type: "lifecycle_stage", description: "Use customer discovery, landing pages, waitlists, and evidence thresholds to decide go/no-go.", group: "lifecycle" },
  { id: "design_product", title: "Design Product", type: "lifecycle_stage", description: "Define the product experience, AI interaction patterns, UX flows, and agent architecture.", group: "lifecycle" },
  { id: "build_agents", title: "Build Agents", type: "lifecycle_stage", description: "Configure agent networks, prompts, tools, memory, and workflows. The system builds itself.", group: "lifecycle" },
  { id: "deploy_product", title: "Deploy Product", type: "lifecycle_stage", description: "Ship to real users with canary rollouts, monitoring, and auto-healing reliability.", group: "lifecycle" },
  { id: "learn_metrics", title: "Learn from Metrics", type: "lifecycle_stage", description: "Capture traces, costs, feedback, and performance metrics from real usage.", group: "lifecycle" },
  { id: "extract_patterns", title: "Extract Patterns", type: "feedback_loop", description: "Winning strategies auto-extracted from experiments and stored for cross-venture reuse.", group: "lifecycle" },
  { id: "compound_intelligence", title: "Compound Intelligence", type: "feedback_loop", description: "Platform gets smarter with each venture. Shared utils, patterns, and benchmarks accumulate.", group: "lifecycle" },
  { id: "next_venture", title: "Next Venture Faster", type: "outcome", description: "Each successive venture launches faster: 5 weeks → 3 weeks → 2 weeks → 1 week.", group: "lifecycle" },

  // --- Business Intelligence Side ---
  { id: "customer_discovery", title: "Customer Discovery", type: "business_intelligence", description: "JTBD interviews, pain extraction, persona synthesis, buying trigger identification.", group: "business" },
  { id: "hypothesis_validation", title: "Hypothesis Validation", type: "business_intelligence", description: "Structured thesis with evidence ladder, Bayesian confidence updates, kill signal detection.", group: "business" },
  { id: "market_signals", title: "Market Signals", type: "business_intelligence", description: "Competitor monitoring, trend detection, funding signals, opportunity scoring.", group: "business" },
  { id: "icp_definition", title: "ICP Definition", type: "business_intelligence", description: "Behavioral, firmographic, and psychographic customer profiling with buying triggers.", group: "business" },
  { id: "offer_design", title: "Offer Design", type: "business_intelligence", description: "Positioning canvas, pricing strategy, landing copy, objection rebuttals.", group: "business" },
  { id: "kill_signals", title: "Kill Signal Detection", type: "decision_point", description: "Automatic alerts when evidence contradicts thesis. Kill early, kill cheap.", group: "business" },
  { id: "product_experience", title: "Product Experience", type: "business_intelligence", description: "UX flow mapping, AI interaction patterns, screen architecture, feature prioritization.", group: "business" },
  { id: "workflow_translation", title: "Workflow → Agent", type: "business_intelligence", description: "Process maps compile into executable agent orchestration configs.", group: "business" },

  // --- Technical Execution Side ---
  { id: "agent_orchestration", title: "Agent Orchestration", type: "technical_execution", description: "Multi-agent coordination: delegation, debate, consensus, pipeline, supervisor patterns.", group: "technical" },
  { id: "prompt_management", title: "Prompt Management", type: "technical_execution", description: "Version-controlled prompts with diff tracking, A/B testing, and regression detection.", group: "technical" },
  { id: "tool_runtime", title: "Tool Runtime", type: "technical_execution", description: "Typed tool definitions, API integrations, credential management, reliability tracking.", group: "technical" },
  { id: "memory_engine", title: "Memory Engine", type: "technical_execution", description: "Working, episodic, semantic, and procedural memory. Agents remember and learn.", group: "technical" },
  { id: "human_review", title: "Human Review", type: "technical_execution", description: "Policy-driven approval workflows. System handles 95%, surfaces 5% for human judgment.", group: "technical" },
  { id: "policy_enforcement", title: "Policy Engine", type: "technical_execution", description: "Safety boundaries, compliance rules, cost limits, content filters. Guardrails that protect.", group: "technical" },
  { id: "data_pipelines", title: "Data Pipelines", type: "technical_execution", description: "Universal ingestion, quality scoring, embeddings, knowledge graphs. Data in, knowledge out.", group: "technical" },
  { id: "experiment_tracking", title: "Experiments", type: "technical_execution", description: "Statistical A/B testing, multi-armed bandits, feedback collection, metric aggregation.", group: "technical" },
  { id: "cost_optimization", title: "Cost Optimization", type: "technical_execution", description: "Per-token tracking, smart routing, response caching, budget alerts, Pareto optimization.", group: "technical" },

  // --- Execution Spine ---
  { id: "spine_event", title: "Event", type: "execution_spine", description: "Something occurred: user action, scheduled trigger, external signal, agent output.", group: "spine" },
  { id: "spine_task", title: "Task", type: "execution_spine", description: "Work unit with clear inputs, expected outputs, success criteria, and deadline.", group: "spine" },
  { id: "spine_agent", title: "Agent/Tool", type: "execution_spine", description: "The actual work: LLM call, API hit, computation. Isolated, policy-gated, bounded.", group: "spine" },
  { id: "spine_trace", title: "Trace", type: "execution_spine", description: "Full execution history. Immutable, structured, queryable, cost-attributed.", group: "spine" },
  { id: "spine_metric", title: "Metric", type: "execution_spine", description: "Quantitative signal: accuracy, cost, latency, conversion, satisfaction.", group: "spine" },
  { id: "spine_feedback", title: "Feedback", type: "execution_spine", description: "Human or automated judgment. Timestamped, weighted by source reliability.", group: "spine" },
  { id: "spine_experiment", title: "Experiment", type: "execution_spine", description: "Statistical aggregation. Rigorous, versioned, reproducible, decision-ready.", group: "spine" },
  { id: "spine_pattern", title: "Pattern", type: "execution_spine", description: "Extracted winning strategy. Searchable, scored, context-tagged, recommended.", group: "spine" },

  // --- 8 Systems ---
  { id: "sys_kernel", title: "Core Kernel", type: "system", description: "Config, identity, events, task queues, tracing, artifacts. The boot sequence.", group: "systems" },
  { id: "sys_agent_runtime", title: "LLM & Agent Runtime", type: "system", description: "LLM routing, prompt management, agent orchestration, tools, memory, review, policy.", group: "systems" },
  { id: "sys_data", title: "Data & Knowledge", type: "system", description: "Ingestion, quality, embeddings, knowledge graphs, labeling, privacy. Knowledge foundation.", group: "systems" },
  { id: "sys_ml", title: "ML & Evaluation", type: "system", description: "Features, model training, evaluation, synthetic data, simulation. Measurable learning.", group: "systems" },
  { id: "sys_product_intel", title: "Product & Market Intel", type: "system", description: "THE KEY DIFFERENTIATOR. Market signals, discovery, thesis, offers, UX, blueprints.", group: "systems" },
  { id: "sys_experimentation", title: "Experimentation", type: "system", description: "A/B testing, feedback, metrics registry, cost optimization. Flywheel acceleration.", group: "systems" },
  { id: "sys_deployment", title: "Deployment & Reliability", type: "system", description: "Packaging, canary releases, circuit breakers, health monitoring, incident response.", group: "systems" },
  { id: "sys_cross_venture", title: "Cross-Venture Learning", type: "system", description: "Pattern library, meta-learning, velocity tracking. The compounding layer.", group: "systems" },

  // --- Architecture Layers ---
  { id: "layer1", title: "Layer 1: Shared Foundation", type: "architecture_layer", description: "39 venture-agnostic modules. Built once, used everywhere. Compounds with each venture.", group: "architecture" },
  { id: "layer2_v1", title: "Venture 1 (0% reuse)", type: "architecture_layer", description: "First venture builds the foundation. 100% new code and configuration.", group: "architecture" },
  { id: "layer2_v3", title: "Venture 3 (60% reuse)", type: "architecture_layer", description: "Third venture mostly reuses existing modules. Only domain logic is new.", group: "architecture" },
  { id: "layer2_v5", title: "Venture 5 (80% reuse)", type: "architecture_layer", description: "Fifth venture is mostly prompts + domain config. Launches in weeks, not months.", group: "architecture" },

  // --- Validation Ladder ---
  { id: "val_desk", title: "Desk Research", type: "validation_checkpoint", description: "Free. What does the market look like? Who are the players?", group: "validation" },
  { id: "val_conversations", title: "Customer Conversations", type: "validation_checkpoint", description: "Time only. Do people actually have this pain? How do they solve it today?", group: "validation" },
  { id: "val_landing", title: "Landing Page", type: "validation_checkpoint", description: "Hours to build. Will people sign up? What's the conversion rate?", group: "validation" },
  { id: "val_wizard", title: "Wizard-of-Oz", type: "validation_checkpoint", description: "Days to build. Can you deliver value manually before automating?", group: "validation" },
  { id: "val_mvp", title: "MVP with Agents", type: "validation_checkpoint", description: "Weeks to build. Real agents, real users, real feedback loops.", group: "validation" },

  // --- Decision Points ---
  { id: "decision_pain", title: "Pain Exists?", type: "decision_point", description: "Do 7+/10 interviews confirm real, frequent, urgent pain?", group: "validation" },
  { id: "decision_pay", title: "Will They Pay?", type: "decision_point", description: "Is willingness-to-pay above break-even? Have they tried to solve this before?", group: "validation" },
  { id: "decision_kill", title: "Kill or Continue?", type: "decision_point", description: "Evidence score below threshold? Kill early, save learnings, move to next idea.", group: "validation" },

  // --- Interaction Channels ---
  { id: "channel_slack", title: "Slack", type: "interaction_channel", description: "Reactive. Notifications, approvals, quick commands, status checks.", group: "channels" },
  { id: "channel_webapp", title: "Web App", type: "interaction_channel", description: "Proactive. Deep work, visual tools, dashboards, conversational co-pilot.", group: "channels" },
  { id: "channel_cli", title: "CLI", type: "interaction_channel", description: "Automation. Scripting, batch operations, CI/CD integration, power-user workflows.", group: "channels" },
  { id: "conversation_router", title: "Conversation Router", type: "interaction_channel", description: "Routes by complexity, urgency, context. Same brain, different interfaces.", group: "channels" },

  // --- North Star ---
  { id: "north_star", title: "North Star", type: "outcome", description: "A single founder launches a validated, revenue-generating, self-improving AI-native product every 3 weeks.", group: "outcome" },
];

// =============================================
// EDGES
// =============================================

export const visionEdges: VisionEdgeData[] = [
  // Main lifecycle flow
  { id: "e-hunch-discover", source: "founder_hunch", target: "discover_opportunity", label: "explore" },
  { id: "e-discover-validate", source: "discover_opportunity", target: "validate_demand", label: "evidence gathered" },
  { id: "e-validate-design", source: "validate_demand", target: "design_product", label: "demand validated" },
  { id: "e-design-build", source: "design_product", target: "build_agents", label: "spec ready" },
  { id: "e-build-deploy", source: "build_agents", target: "deploy_product", label: "agents configured" },
  { id: "e-deploy-learn", source: "deploy_product", target: "learn_metrics", label: "in production" },
  { id: "e-learn-extract", source: "learn_metrics", target: "extract_patterns", label: "data accumulated" },
  { id: "e-extract-compound", source: "extract_patterns", target: "compound_intelligence", label: "patterns stored" },
  { id: "e-compound-next", source: "compound_intelligence", target: "next_venture", label: "platform smarter" },

  // Flywheel feedback loops
  { id: "e-feedback-learn-validate", source: "learn_metrics", target: "validate_demand", type: "feedback", animated: true },
  { id: "e-feedback-extract-discover", source: "extract_patterns", target: "discover_opportunity", type: "feedback", animated: true },
  { id: "e-feedback-compound-build", source: "compound_intelligence", target: "build_agents", type: "feedback", animated: true },
  { id: "e-feedback-next-hunch", source: "next_venture", target: "founder_hunch", type: "feedback", animated: true },

  // Execution spine chain
  { id: "e-spine-1", source: "spine_event", target: "spine_task", type: "spine" },
  { id: "e-spine-2", source: "spine_task", target: "spine_agent", type: "spine" },
  { id: "e-spine-3", source: "spine_agent", target: "spine_trace", type: "spine" },
  { id: "e-spine-4", source: "spine_trace", target: "spine_metric", type: "spine" },
  { id: "e-spine-5", source: "spine_metric", target: "spine_feedback", type: "spine" },
  { id: "e-spine-6", source: "spine_feedback", target: "spine_experiment", type: "spine" },
  { id: "e-spine-7", source: "spine_experiment", target: "spine_pattern", type: "spine" },
  { id: "e-spine-loop", source: "spine_pattern", target: "spine_event", type: "feedback", animated: true },

  // Validation ladder
  { id: "e-val-1", source: "val_desk", target: "val_conversations" },
  { id: "e-val-2", source: "val_conversations", target: "val_landing" },
  { id: "e-val-3", source: "val_landing", target: "val_wizard" },
  { id: "e-val-4", source: "val_wizard", target: "val_mvp" },

  // Channels to router
  { id: "e-slack-router", source: "channel_slack", target: "conversation_router" },
  { id: "e-web-router", source: "channel_webapp", target: "conversation_router" },
  { id: "e-cli-router", source: "channel_cli", target: "conversation_router" },

  // Architecture
  { id: "e-l1-v1", source: "layer1", target: "layer2_v1" },
  { id: "e-l1-v3", source: "layer1", target: "layer2_v3" },
  { id: "e-l1-v5", source: "layer1", target: "layer2_v5" },
];

// =============================================
// LAYOUT POSITIONS (approximate — React Flow will render)
// =============================================

export const nodePositions: Record<string, { x: number; y: number }> = {
  // Lifecycle (horizontal top band)
  founder_hunch: { x: 50, y: 100 },
  discover_opportunity: { x: 300, y: 100 },
  validate_demand: { x: 550, y: 100 },
  design_product: { x: 800, y: 100 },
  build_agents: { x: 1050, y: 100 },
  deploy_product: { x: 1300, y: 100 },
  learn_metrics: { x: 1550, y: 100 },
  extract_patterns: { x: 1800, y: 100 },
  compound_intelligence: { x: 2050, y: 100 },
  next_venture: { x: 2300, y: 100 },

  // Execution Spine (horizontal middle band)
  spine_event: { x: 200, y: 350 },
  spine_task: { x: 450, y: 350 },
  spine_agent: { x: 700, y: 350 },
  spine_trace: { x: 950, y: 350 },
  spine_metric: { x: 1200, y: 350 },
  spine_feedback: { x: 1450, y: 350 },
  spine_experiment: { x: 1700, y: 350 },
  spine_pattern: { x: 1950, y: 350 },

  // Business Intelligence (left cluster)
  customer_discovery: { x: 100, y: 550 },
  hypothesis_validation: { x: 350, y: 550 },
  market_signals: { x: 100, y: 700 },
  icp_definition: { x: 350, y: 700 },
  offer_design: { x: 100, y: 850 },
  kill_signals: { x: 350, y: 850 },
  product_experience: { x: 600, y: 550 },
  workflow_translation: { x: 600, y: 700 },

  // Technical Execution (right cluster)
  agent_orchestration: { x: 1100, y: 550 },
  prompt_management: { x: 1350, y: 550 },
  tool_runtime: { x: 1100, y: 700 },
  memory_engine: { x: 1350, y: 700 },
  human_review: { x: 1600, y: 550 },
  policy_enforcement: { x: 1600, y: 700 },
  data_pipelines: { x: 1850, y: 550 },
  experiment_tracking: { x: 1850, y: 700 },
  cost_optimization: { x: 2100, y: 625 },

  // 8 Systems (bottom ring)
  sys_kernel: { x: 150, y: 1050 },
  sys_agent_runtime: { x: 450, y: 1050 },
  sys_data: { x: 750, y: 1050 },
  sys_ml: { x: 1050, y: 1050 },
  sys_product_intel: { x: 1350, y: 1050 },
  sys_experimentation: { x: 1650, y: 1050 },
  sys_deployment: { x: 1950, y: 1050 },
  sys_cross_venture: { x: 2250, y: 1050 },

  // Architecture
  layer1: { x: 900, y: 1250 },
  layer2_v1: { x: 600, y: 1400 },
  layer2_v3: { x: 900, y: 1400 },
  layer2_v5: { x: 1200, y: 1400 },

  // Validation Ladder
  val_desk: { x: 100, y: 1250 },
  val_conversations: { x: 100, y: 1350 },
  val_landing: { x: 100, y: 1450 },
  val_wizard: { x: 100, y: 1550 },
  val_mvp: { x: 100, y: 1650 },
  decision_pain: { x: 350, y: 1300 },
  decision_pay: { x: 350, y: 1450 },
  decision_kill: { x: 350, y: 1600 },

  // Channels
  channel_slack: { x: 1700, y: 1250 },
  channel_webapp: { x: 1950, y: 1250 },
  channel_cli: { x: 2200, y: 1250 },
  conversation_router: { x: 1950, y: 1400 },

  // North Star
  north_star: { x: 1100, y: 1600 },
};

// Simulation sequence — the auto-play path
export const simulationSequence = [
  "founder_hunch",
  "discover_opportunity",
  "validate_demand",
  "design_product",
  "build_agents",
  "deploy_product",
  "learn_metrics",
  "extract_patterns",
  "compound_intelligence",
  "next_venture",
  "founder_hunch", // loop
];
