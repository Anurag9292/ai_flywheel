/**
 * AI Flywheel Vision Map — Story-Driven Canvas Data
 *
 * Three-layer layout:
 *   Top:    Execution Spine (horizontal heartbeat)
 *   Middle: Main Venture Lifecycle (hero flow, S-curve)
 *   Bottom: Flywheel compounding loop (circular)
 *
 * Supporting clusters: Business Intel (left), Technical (right)
 * Canvas: ~2000×1600 — fits at 0.55 zoom on one screen.
 */

export type NodeCategory =
  | "founder_state"
  | "lifecycle_stage"
  | "business_intelligence"
  | "technical_execution"
  | "execution_spine"
  | "system"
  | "validation_checkpoint"
  | "decision_point"
  | "feedback_loop"
  | "interaction_channel"
  | "kill_signal"
  | "outcome";

export interface VisionNodeData {
  id: string;
  title: string;
  type: NodeCategory;
  description: string;
  group?: string;
  storyText?: string; // Displayed in story mode overlay
}

export interface VisionEdgeData {
  id: string;
  source: string;
  target: string;
  label?: string;
  animated?: boolean;
  type?: "default" | "feedback" | "spine" | "kill";
}

// =============================================
// NODES
// =============================================

export const visionNodes: VisionNodeData[] = [
  // --- Main Lifecycle (Hero Flow — S-curve) ---
  { id: "founder_hunch", title: "Founder Hunch", type: "founder_state", description: "Gut feeling meets pattern recognition. A possible opportunity sparks.", group: "lifecycle", storyText: "It starts with a hunch — pattern recognition from lived experience." },
  { id: "discover_opportunity", title: "Discover", type: "lifecycle_stage", description: "Research the market, detect signals, identify customer pain.", group: "lifecycle", storyText: "Signals detected. The opportunity space becomes clear." },
  { id: "validate_demand", title: "Validate Demand", type: "lifecycle_stage", description: "Customer evidence: interviews, waitlists, conversion data.", group: "lifecycle", storyText: "Validating with real customer evidence. Kill early or proceed." },
  { id: "design_product", title: "Design", type: "lifecycle_stage", description: "Product experience, AI interaction patterns, feature priority.", group: "lifecycle", storyText: "Designing the product experience and agent architecture." },
  { id: "build_agents", title: "Build", type: "lifecycle_stage", description: "Configure agents, prompts, tools, memory, workflows.", group: "lifecycle", storyText: "Building agents that execute the product vision." },
  { id: "deploy_product", title: "Deploy", type: "lifecycle_stage", description: "Ship to real users with monitoring and auto-healing.", group: "lifecycle", storyText: "Live in production. Real users, real feedback." },
  { id: "learn_metrics", title: "Learn", type: "lifecycle_stage", description: "Capture traces, costs, feedback, performance metrics.", group: "lifecycle", storyText: "Learning from every interaction and metric." },
  { id: "extract_patterns", title: "Extract", type: "feedback_loop", description: "Winning strategies extracted for cross-venture reuse.", group: "lifecycle", storyText: "Extracting reusable patterns from this venture's data." },
  { id: "compound_intelligence", title: "Compound", type: "feedback_loop", description: "Platform gets smarter. Shared utils and benchmarks accumulate.", group: "lifecycle", storyText: "Intelligence compounds. The platform evolves." },
  { id: "next_venture", title: "Next Venture", type: "outcome", description: "Each successive venture launches faster: 5→3→2→1 week.", group: "lifecycle", storyText: "Next venture launches faster. The flywheel accelerates." },

  // --- Kill Signal ---
  { id: "kill_early", title: "Kill Early", type: "kill_signal", description: "Evidence contradicts thesis. Kill cheap, save learnings, move on.", group: "lifecycle", storyText: "No signal? Kill early and cheap. Preserve capital." },

  // --- Validated Product (convergence) ---
  { id: "validated_product", title: "Validated Product", type: "outcome", description: "Business demand + technical feasibility converge into a validated product.", group: "lifecycle", storyText: "Business and technical validation converge." },

  // --- Business Intelligence (Left Cluster) ---
  { id: "customer_discovery", title: "Customer Discovery", type: "business_intelligence", description: "JTBD interviews, pain extraction, persona synthesis.", group: "business" },
  { id: "hypothesis_validation", title: "Hypothesis Testing", type: "business_intelligence", description: "Structured thesis, evidence ladder, Bayesian confidence.", group: "business" },
  { id: "market_signals", title: "Market Signals", type: "business_intelligence", description: "Competitor monitoring, trend detection, opportunity scoring.", group: "business" },
  { id: "icp_definition", title: "ICP Definition", type: "business_intelligence", description: "Behavioral and firmographic customer profiling.", group: "business" },
  { id: "offer_design", title: "Offer Design", type: "business_intelligence", description: "Positioning, pricing, landing copy, objection rebuttals.", group: "business" },

  // --- Technical Execution (Right Cluster) ---
  { id: "agent_orchestration", title: "Agent Orchestration", type: "technical_execution", description: "Multi-agent coordination: delegation, debate, consensus.", group: "technical" },
  { id: "prompt_management", title: "Prompt Management", type: "technical_execution", description: "Version-controlled prompts with A/B testing.", group: "technical" },
  { id: "tool_runtime", title: "Tool Runtime", type: "technical_execution", description: "Typed tools, API integrations, credential management.", group: "technical" },
  { id: "memory_engine", title: "Memory Engine", type: "technical_execution", description: "Working, episodic, semantic, procedural memory.", group: "technical" },
  { id: "cost_optimization", title: "Cost Optimization", type: "technical_execution", description: "Per-token tracking, smart routing, budget alerts.", group: "technical" },

  // --- Execution Spine (Top) ---
  { id: "spine_event", title: "Event", type: "execution_spine", description: "Trigger: user action, schedule, external signal.", group: "spine" },
  { id: "spine_task", title: "Task", type: "execution_spine", description: "Work unit with inputs, outputs, success criteria.", group: "spine" },
  { id: "spine_agent", title: "Agent", type: "execution_spine", description: "LLM call, API hit, computation — policy-gated.", group: "spine" },
  { id: "spine_trace", title: "Trace", type: "execution_spine", description: "Immutable execution history, cost-attributed.", group: "spine" },
  { id: "spine_metric", title: "Metric", type: "execution_spine", description: "Accuracy, cost, latency, conversion, satisfaction.", group: "spine" },
  { id: "spine_feedback", title: "Feedback", type: "execution_spine", description: "Human or automated judgment, timestamped.", group: "spine" },
  { id: "spine_experiment", title: "Experiment", type: "execution_spine", description: "Statistical aggregation, decision-ready.", group: "spine" },
  { id: "spine_pattern", title: "Pattern", type: "execution_spine", description: "Extracted winning strategy, context-tagged.", group: "spine" },

  // --- Validation Ladder (near validate_demand) ---
  { id: "val_desk", title: "Desk Research", type: "validation_checkpoint", description: "Free. What does the market look like?", group: "validation" },
  { id: "val_conversations", title: "Conversations", type: "validation_checkpoint", description: "Time only. Do people have this pain?", group: "validation" },
  { id: "val_landing", title: "Landing Page", type: "validation_checkpoint", description: "Hours. Will people sign up?", group: "validation" },
  { id: "val_wizard", title: "Wizard-of-Oz", type: "validation_checkpoint", description: "Days. Can you deliver value manually?", group: "validation" },
  { id: "val_mvp", title: "MVP", type: "validation_checkpoint", description: "Weeks. Real agents, real users.", group: "validation" },

  // --- Flywheel Loop (Bottom Center) ---
  { id: "flywheel_data", title: "More Data", type: "feedback_loop", description: "Each user generates training signal.", group: "flywheel" },
  { id: "flywheel_better", title: "Better Models", type: "feedback_loop", description: "Models improve with accumulated data.", group: "flywheel" },
  { id: "flywheel_value", title: "More Value", type: "feedback_loop", description: "Better outputs attract more users.", group: "flywheel" },
  { id: "flywheel_users", title: "More Users", type: "feedback_loop", description: "Growth compounds — network effects.", group: "flywheel" },

  // --- Systems (Compact Row at Bottom) ---
  { id: "sys_kernel", title: "Core Kernel", type: "system", description: "Config, identity, events, task queues, tracing.", group: "systems" },
  { id: "sys_agent_runtime", title: "Agent Runtime", type: "system", description: "LLM routing, prompts, orchestration, tools, memory.", group: "systems" },
  { id: "sys_data", title: "Data & Knowledge", type: "system", description: "Ingestion, embeddings, knowledge graphs.", group: "systems" },
  { id: "sys_ml", title: "ML & Eval", type: "system", description: "Features, training, evaluation, simulation.", group: "systems" },
  { id: "sys_product_intel", title: "Product Intel", type: "system", description: "Market signals, discovery, thesis, offers.", group: "systems" },
  { id: "sys_experimentation", title: "Experimentation", type: "system", description: "A/B testing, metrics, cost optimization.", group: "systems" },
  { id: "sys_deployment", title: "Deployment", type: "system", description: "Canary releases, monitoring, incident response.", group: "systems" },
  { id: "sys_cross_venture", title: "Cross-Venture", type: "system", description: "Pattern library, meta-learning, velocity tracking.", group: "systems" },
];

// =============================================
// EDGES
// =============================================

export const visionEdges: VisionEdgeData[] = [
  // Main lifecycle flow (hero path)
  { id: "e-hunch-discover", source: "founder_hunch", target: "discover_opportunity", label: "explore" },
  { id: "e-discover-validate", source: "discover_opportunity", target: "validate_demand", label: "evidence" },
  { id: "e-validate-design", source: "validate_demand", target: "design_product", label: "go" },
  { id: "e-design-build", source: "design_product", target: "build_agents", label: "spec" },
  { id: "e-build-deploy", source: "build_agents", target: "deploy_product", label: "ship" },
  { id: "e-deploy-learn", source: "deploy_product", target: "learn_metrics", label: "live" },
  { id: "e-learn-extract", source: "learn_metrics", target: "extract_patterns", label: "data" },
  { id: "e-extract-compound", source: "extract_patterns", target: "compound_intelligence", label: "patterns" },
  { id: "e-compound-next", source: "compound_intelligence", target: "next_venture", label: "faster" },

  // Kill signal from validate
  { id: "e-validate-kill", source: "validate_demand", target: "kill_early", type: "kill", label: "no signal" },

  // Validated product convergence
  { id: "e-design-validated", source: "design_product", target: "validated_product" },
  { id: "e-build-validated", source: "build_agents", target: "validated_product" },

  // Flywheel feedback loops
  { id: "e-feedback-next-hunch", source: "next_venture", target: "founder_hunch", type: "feedback", animated: true },
  { id: "e-feedback-learn-validate", source: "learn_metrics", target: "validate_demand", type: "feedback", animated: true },
  { id: "e-feedback-compound-build", source: "compound_intelligence", target: "build_agents", type: "feedback", animated: true },

  // Execution spine chain
  { id: "e-spine-1", source: "spine_event", target: "spine_task", type: "spine" },
  { id: "e-spine-2", source: "spine_task", target: "spine_agent", type: "spine" },
  { id: "e-spine-3", source: "spine_agent", target: "spine_trace", type: "spine" },
  { id: "e-spine-4", source: "spine_trace", target: "spine_metric", type: "spine" },
  { id: "e-spine-5", source: "spine_metric", target: "spine_feedback", type: "spine" },
  { id: "e-spine-6", source: "spine_feedback", target: "spine_experiment", type: "spine" },
  { id: "e-spine-7", source: "spine_experiment", target: "spine_pattern", type: "spine" },
  { id: "e-spine-loop", source: "spine_pattern", target: "spine_event", type: "feedback", animated: true },

  // Business intel connections to lifecycle
  { id: "e-biz-discover", source: "customer_discovery", target: "discover_opportunity" },
  { id: "e-biz-validate", source: "hypothesis_validation", target: "validate_demand" },
  { id: "e-biz-market", source: "market_signals", target: "discover_opportunity" },
  { id: "e-biz-icp", source: "icp_definition", target: "validate_demand" },
  { id: "e-biz-offer", source: "offer_design", target: "design_product" },

  // Technical connections to lifecycle
  { id: "e-tech-build1", source: "agent_orchestration", target: "build_agents" },
  { id: "e-tech-build2", source: "prompt_management", target: "build_agents" },
  { id: "e-tech-build3", source: "tool_runtime", target: "deploy_product" },
  { id: "e-tech-build4", source: "memory_engine", target: "build_agents" },
  { id: "e-tech-cost", source: "cost_optimization", target: "learn_metrics" },

  // Validation ladder
  { id: "e-val-1", source: "val_desk", target: "val_conversations" },
  { id: "e-val-2", source: "val_conversations", target: "val_landing" },
  { id: "e-val-3", source: "val_landing", target: "val_wizard" },
  { id: "e-val-4", source: "val_wizard", target: "val_mvp" },
  { id: "e-val-to-lifecycle", source: "val_mvp", target: "validate_demand" },

  // Flywheel loop
  { id: "e-fly-1", source: "flywheel_data", target: "flywheel_better", type: "feedback", animated: true },
  { id: "e-fly-2", source: "flywheel_better", target: "flywheel_value", type: "feedback", animated: true },
  { id: "e-fly-3", source: "flywheel_value", target: "flywheel_users", type: "feedback", animated: true },
  { id: "e-fly-4", source: "flywheel_users", target: "flywheel_data", type: "feedback", animated: true },
];

// =============================================
// LAYOUT POSITIONS — 2000×1600 canvas
// =============================================

export const nodePositions: Record<string, { x: number; y: number }> = {
  // === Execution Spine (Top — y:60) ===
  spine_event: { x: 200, y: 60 },
  spine_task: { x: 430, y: 60 },
  spine_agent: { x: 660, y: 60 },
  spine_trace: { x: 890, y: 60 },
  spine_metric: { x: 1120, y: 60 },
  spine_feedback: { x: 1350, y: 60 },
  spine_experiment: { x: 1580, y: 60 },
  spine_pattern: { x: 1810, y: 60 },

  // === Main Lifecycle — Hero S-curve (y: 380-480) ===
  founder_hunch: { x: 100, y: 450 },
  discover_opportunity: { x: 300, y: 400 },
  validate_demand: { x: 520, y: 450 },
  design_product: { x: 740, y: 400 },
  build_agents: { x: 960, y: 450 },
  deploy_product: { x: 1180, y: 400 },
  learn_metrics: { x: 1400, y: 450 },
  extract_patterns: { x: 1600, y: 400 },
  compound_intelligence: { x: 1780, y: 450 },
  next_venture: { x: 1950, y: 400 },

  // Kill signal (near validate)
  kill_early: { x: 520, y: 580 },

  // Validated product (between design and build)
  validated_product: { x: 850, y: 560 },

  // === Business Intelligence (Left Cluster — x:50-400, y:700-1000) ===
  customer_discovery: { x: 80, y: 720 },
  hypothesis_validation: { x: 300, y: 720 },
  market_signals: { x: 80, y: 850 },
  icp_definition: { x: 300, y: 850 },
  offer_design: { x: 190, y: 970 },

  // === Technical Execution (Right Cluster — x:1200-1700, y:700-1000) ===
  agent_orchestration: { x: 1250, y: 720 },
  prompt_management: { x: 1470, y: 720 },
  tool_runtime: { x: 1250, y: 850 },
  memory_engine: { x: 1470, y: 850 },
  cost_optimization: { x: 1360, y: 970 },

  // === Validation Ladder (near validate_demand — left side) ===
  val_desk: { x: 420, y: 700 },
  val_conversations: { x: 420, y: 790 },
  val_landing: { x: 420, y: 880 },
  val_wizard: { x: 420, y: 970 },
  val_mvp: { x: 420, y: 1060 },

  // === Flywheel Loop (Bottom Center — y:1100-1300) ===
  flywheel_data: { x: 820, y: 1130 },
  flywheel_better: { x: 1020, y: 1200 },
  flywheel_value: { x: 1020, y: 1100 },
  flywheel_users: { x: 820, y: 1200 },

  // === Systems (Compact Row — y:1400) ===
  sys_kernel: { x: 100, y: 1400 },
  sys_agent_runtime: { x: 340, y: 1400 },
  sys_data: { x: 580, y: 1400 },
  sys_ml: { x: 820, y: 1400 },
  sys_product_intel: { x: 1060, y: 1400 },
  sys_experimentation: { x: 1300, y: 1400 },
  sys_deployment: { x: 1540, y: 1400 },
  sys_cross_venture: { x: 1780, y: 1400 },
};

// =============================================
// SIMULATION SEQUENCE — tells the 10-second story
// =============================================

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
  "founder_hunch", // loop restarts
];

// Story mode captions per step
export const storyModeText: Record<string, string> = {
  founder_hunch: "Step 1: A hunch emerges — pattern recognition from lived experience.",
  discover_opportunity: "Step 2: Exploring the opportunity space with market signals.",
  validate_demand: "Step 3: Validating demand with customer evidence...",
  design_product: "Step 4: Designing the product experience and agent architecture.",
  build_agents: "Step 5: Building intelligent agents that execute the vision.",
  deploy_product: "Step 6: Shipping to real users with auto-healing reliability.",
  learn_metrics: "Step 7: Learning from every trace, metric, and feedback signal.",
  extract_patterns: "Step 8: Extracting reusable patterns for future ventures.",
  compound_intelligence: "Step 9: Intelligence compounds — the platform evolves.",
  next_venture: "Step 10: Next venture launches faster. The flywheel accelerates.",
};
