"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ReactFlow,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
  type Node,
  type Edge,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { motion, AnimatePresence } from "framer-motion";

import VisionNode from "@/components/vision/vision-node";
import {
  visionNodes,
  visionEdges,
  nodePositions,
  simulationSequence,
  storyText,
  FILTER_OPTIONS,
  type VisionNodeData,
  type NodeCategory,
} from "@/components/vision/vision-data";

// ─── Edge Styling ────────────────────────────────────────────────────────────

function getEdgeStyle(edgeType: string, isOnPath: boolean) {
  switch (edgeType) {
    case "hero":
      return {
        stroke: isOnPath ? "rgba(167, 139, 250, 1)" : "rgba(139, 92, 246, 0.7)",
        strokeWidth: isOnPath ? 3.5 : 3,
      };
    case "feedback":
      return {
        stroke: isOnPath ? "rgba(251, 191, 36, 0.9)" : "rgba(234, 179, 8, 0.5)",
        strokeWidth: isOnPath ? 2.5 : 1.8,
        strokeDasharray: "8 5",
      };
    case "kill":
      return {
        stroke: "rgba(239, 68, 68, 0.7)",
        strokeWidth: 1.8,
        strokeDasharray: "5 4",
      };
    case "spine":
      return {
        stroke: isOnPath ? "rgba(232, 121, 249, 0.9)" : "rgba(217, 70, 239, 0.5)",
        strokeWidth: isOnPath ? 2.5 : 2,
      };
    case "flywheel":
      return {
        stroke: isOnPath ? "rgba(251, 191, 36, 0.9)" : "rgba(234, 179, 8, 0.55)",
        strokeWidth: isOnPath ? 2.2 : 1.8,
        strokeDasharray: "6 4",
      };
    case "foundation":
      return {
        stroke: "rgba(99, 102, 241, 0.2)",
        strokeWidth: 1,
        strokeDasharray: "3 3",
      };
    case "module":
    default:
      return {
        stroke: isOnPath ? "rgba(139, 92, 246, 0.5)" : "rgba(139, 92, 246, 0.15)",
        strokeWidth: isOnPath ? 1.5 : 1,
      };
  }
}

// ─── Build Nodes ─────────────────────────────────────────────────────────────

function buildNodes(activeId: string | null, filter: string | null): Node[] {
  return visionNodes.map((n) => {
    const matchesFilter =
      !filter ||
      n.group === filter ||
      n.type === filter;

    return {
      id: n.id,
      type: "visionNode",
      position: nodePositions[n.id] || { x: 0, y: 0 },
      data: {
        id: n.id,
        title: n.title,
        type: n.type,
        description: n.description,
        group: n.group,
        isActive: n.id === activeId,
        isDimmed: filter ? !matchesFilter : false,
      },
    };
  });
}

// ─── Build Edges ─────────────────────────────────────────────────────────────

function buildEdges(activeId: string | null): Edge[] {
  return visionEdges.map((e) => {
    const isOnPath = e.source === activeId || e.target === activeId;
    const style = getEdgeStyle(e.edgeType, isOnPath);
    return {
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.label,
      animated: e.animated || (isOnPath && e.edgeType === "hero"),
      style,
      labelStyle: {
        fill: "rgba(200, 200, 220, 0.55)",
        fontSize: 9,
        fontWeight: 500,
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: style.stroke,
        width: 14,
        height: 14,
      },
    };
  });
}

// ─── Legend Items ─────────────────────────────────────────────────────────────

const LEGEND_ITEMS = [
  { color: "bg-violet-400", label: "Lifecycle (Hero)" },
  { color: "bg-amber-400", label: "Founder / Outcome" },
  { color: "bg-emerald-400", label: "Business Intel" },
  { color: "bg-blue-400", label: "Technical" },
  { color: "bg-fuchsia-400", label: "Execution Spine" },
  { color: "bg-yellow-400", label: "Flywheel / Feedback" },
  { color: "bg-red-400", label: "Kill Signal" },
  { color: "bg-cyan-400", label: "Validation" },
  { color: "bg-indigo-400", label: "Systems" },
  { color: "bg-purple-400", label: "Architecture" },
  { color: "bg-teal-400", label: "Channels" },
];

// ─── Main Page Component ─────────────────────────────────────────────────────

export default function VisionMapPage() {
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<VisionNodeData | null>(null);
  const [filter, setFilter] = useState<string | null>(null);
  const [simulating, setSimulating] = useState(false);
  const [storyStep, setStoryStep] = useState<number>(0);
  const [currentStoryText, setCurrentStoryText] = useState<string | null>(null);
  const [legendOpen, setLegendOpen] = useState(false);
  const simRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const simIndex = useRef(0);

  const nodeTypes = useMemo(() => ({ visionNode: VisionNode }), []);
  const nodes = useMemo(() => buildNodes(activeNode, filter), [activeNode, filter]);
  const edges = useMemo(() => buildEdges(activeNode), [activeNode]);

  // ─── Simulation (Story Mode) ──────────────────────────────────────────────

  const startSimulation = useCallback(() => {
    setSimulating(true);
    setSelectedNode(null);
    simIndex.current = 0;

    const step = () => {
      const nodeId = simulationSequence[simIndex.current];
      setActiveNode(nodeId);
      setStoryStep(simIndex.current + 1);
      setCurrentStoryText(storyText[nodeId] || null);
      simIndex.current = (simIndex.current + 1) % simulationSequence.length;
    };

    step();
    simRef.current = setInterval(step, 1200);
  }, []);

  const stopSimulation = useCallback(() => {
    setSimulating(false);
    setCurrentStoryText(null);
    setStoryStep(0);
    if (simRef.current) clearInterval(simRef.current);
    setActiveNode(null);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (simRef.current) clearInterval(simRef.current);
    };
  }, []);

  // Auto-start story on mount
  useEffect(() => {
    const timer = setTimeout(() => {
      startSimulation();
    }, 600);
    return () => clearTimeout(timer);
  }, [startSimulation]);

  // ─── Node Click Handler ───────────────────────────────────────────────────

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      if (simulating) stopSimulation();
      const data = visionNodes.find((n) => n.id === node.id);
      setSelectedNode(data || null);
      setActiveNode(node.id);
      setCurrentStoryText(data ? storyText[data.id] || data.description : null);
    },
    [simulating, stopSimulation]
  );

  const handlePaneClick = useCallback(() => {
    if (simulating) return;
    setSelectedNode(null);
    setActiveNode(null);
    setCurrentStoryText(null);
  }, [simulating]);

  // ─── MiniMap node color ───────────────────────────────────────────────────

  const minimapNodeColor = useCallback((n: Node) => {
    const type = (n.data as Record<string, unknown>)?.type as NodeCategory | undefined;
    const colors: Partial<Record<NodeCategory, string>> = {
      founder_state: "#fbbf24",
      lifecycle_stage: "#8b5cf6",
      business_intelligence: "#10b981",
      technical_execution: "#3b82f6",
      execution_spine: "#d946ef",
      system: "#6366f1",
      architecture_layer: "#9333ea",
      outcome: "#f59e0b",
      feedback_loop: "#eab308",
      kill_signal: "#ef4444",
      validation_checkpoint: "#06b6d4",
      decision_point: "#f59e0b",
      flywheel: "#eab308",
      interaction_channel: "#14b8a6",
    };
    return colors[type as NodeCategory] || "#4b5563";
  }, []);

  return (
    <div className="h-[calc(100vh-32px)] flex flex-col relative overflow-hidden">
      {/* ─── Compact Header with Title + Filter Bar ────────────────────── */}
      <div className="absolute top-0 left-0 right-0 z-30 px-4 py-2 bg-gradient-to-b from-[var(--bg-primary)] via-[var(--bg-primary)]/90 to-transparent pointer-events-none">
        <div className="flex items-center justify-between pointer-events-auto">
          {/* Title (compact) */}
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold gradient-text">AI Flywheel</h1>
            <p className="text-[10px] text-[var(--text-muted)] hidden sm:block">
              Personal Venture Operating System — Validate, build, learn, launch faster.
            </p>
          </div>

          {/* Filter Bar + Story Control (single row) */}
          <div className="flex items-center gap-2">
            <div className="flex gap-0.5 bg-[rgba(5,5,15,0.85)] backdrop-blur-md rounded-lg p-0.5 border border-[var(--border-subtle)]">
              {FILTER_OPTIONS.map((f) => (
                <button
                  key={f.key || "all"}
                  onClick={() => setFilter(f.key)}
                  className={`px-2 py-1 text-[9px] font-medium rounded-md transition-all ${
                    filter === f.key
                      ? "bg-violet-600/40 text-violet-100 border border-violet-400/40 shadow-[0_0_8px_rgba(139,92,246,0.2)]"
                      : "text-gray-500 hover:text-gray-300 hover:bg-white/5"
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>

            {/* Story Control */}
            <button
              onClick={simulating ? stopSimulation : startSimulation}
              className={`px-3 py-1.5 text-[10px] font-semibold rounded-lg transition-all whitespace-nowrap ${
                simulating
                  ? "bg-red-600/25 text-red-200 border border-red-500/40 shadow-[0_0_12px_rgba(239,68,68,0.15)]"
                  : "bg-emerald-600/25 text-emerald-200 border border-emerald-500/40 shadow-[0_0_12px_rgba(16,185,129,0.15)]"
              }`}
            >
              {simulating ? "Stop Story" : "Play Story"}
            </button>
          </div>
        </div>
      </div>

      {/* ─── Story Mode Card (top-right below filters) ───────────────────── */}
      <AnimatePresence>
        {currentStoryText && simulating && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            transition={{ duration: 0.3 }}
            className="absolute top-[48px] right-4 z-20 w-[300px] p-3 rounded-xl
              bg-[rgba(8,8,18,0.95)] backdrop-blur-xl border border-violet-500/30
              shadow-[0_0_40px_rgba(139,92,246,0.12)]"
          >
            <div className="flex items-center gap-2 mb-2">
              <span className="px-2 py-0.5 text-[9px] font-bold uppercase tracking-widest text-violet-300 bg-violet-900/50 rounded">
                Step {storyStep} / {simulationSequence.length}
              </span>
              <span className="text-[10px] text-violet-300/70 font-medium">
                {simulationSequence[storyStep - 1] &&
                  visionNodes.find((n) => n.id === simulationSequence[storyStep - 1])?.title}
              </span>
            </div>
            <p className="text-sm text-gray-200 leading-relaxed">{currentStoryText}</p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ─── Spine Label (top center, below header) ──────────────────────── */}
      <div className="absolute top-[42px] left-1/2 -translate-x-1/2 z-10 pointer-events-none text-center">
        <p className="text-[9px] text-fuchsia-400/50 font-semibold uppercase tracking-[0.2em]">
          Execution Spine &mdash; System Heartbeat
        </p>
      </div>

      {/* ─── Canvas ──────────────────────────────────────────────────────── */}
      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodeClick={handleNodeClick}
          onPaneClick={handlePaneClick}
          minZoom={0.1}
          maxZoom={3}
          proOptions={{ hideAttribution: true }}
          defaultViewport={{ x: 30, y: -60, zoom: 0.47 }}
        >
          <Controls
            className="!bg-[rgba(8,8,18,0.95)] !border-[var(--border-subtle)] !rounded-lg !shadow-lg
              [&>button]:!bg-transparent [&>button]:!border-[var(--border-subtle)]
              [&>button]:!text-gray-400 [&>button:hover]:!bg-violet-600/10 [&>button:hover]:!text-gray-200"
            position="bottom-left"
          />
          <MiniMap
            className="!bg-[rgba(8,8,18,0.95)] !border-[var(--border-subtle)] !rounded-lg"
            nodeColor={minimapNodeColor}
            maskColor="rgba(0,0,0,0.8)"
            position="bottom-right"
          />
          <Background
            variant={BackgroundVariant.Dots}
            gap={50}
            size={1}
            color="rgba(139, 92, 246, 0.04)"
          />
        </ReactFlow>

        {/* ─── Detail Panel (Right Side Slide-in) ─────────────────────────── */}
        <AnimatePresence>
          {selectedNode && (
            <motion.div
              initial={{ x: 400, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 400, opacity: 0 }}
              transition={{ type: "spring", damping: 28, stiffness: 220 }}
              className="absolute top-4 right-4 w-[340px] bg-[rgba(8,8,16,0.97)] backdrop-blur-xl
                border border-[var(--border-subtle)] rounded-xl p-5 shadow-2xl z-30"
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <p className="text-[9px] text-violet-400/80 uppercase tracking-[0.15em] font-semibold">
                    {selectedNode.type.replace(/_/g, " ")}
                  </p>
                  <h3 className="text-lg font-bold text-white mt-1">{selectedNode.title}</h3>
                </div>
                <button
                  onClick={() => {
                    setSelectedNode(null);
                    setActiveNode(null);
                    setCurrentStoryText(null);
                  }}
                  className="text-gray-500 hover:text-gray-200 text-lg leading-none p-1 transition-colors"
                >
                  &times;
                </button>
              </div>
              <p className="text-sm text-gray-300 leading-relaxed">{selectedNode.description}</p>
              {selectedNode.group && (
                <div className="mt-4 pt-3 border-t border-[var(--border-subtle)]">
                  <p className="text-[10px] text-gray-500">
                    Group:{" "}
                    <span className="text-gray-300 font-medium capitalize">{selectedNode.group}</span>
                  </p>
                  {selectedNode.layer && (
                    <p className="text-[10px] text-gray-500 mt-1">
                      Layer:{" "}
                      <span className="text-gray-300 font-medium capitalize">{selectedNode.layer}</span>
                    </p>
                  )}
                </div>
              )}
              {storyText[selectedNode.id] && (
                <div className="mt-3 p-3 rounded-lg bg-violet-950/30 border border-violet-500/15">
                  <p className="text-[10px] text-violet-300/80 italic leading-relaxed">
                    {storyText[selectedNode.id]}
                  </p>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* ─── Collapsible Legend (Bottom-Left) ───────────────────────────── */}
        <div className="absolute bottom-14 left-4 z-20">
          <button
            onClick={() => setLegendOpen(!legendOpen)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-semibold text-gray-400
              bg-[rgba(8,8,18,0.9)] backdrop-blur-sm border border-[var(--border-subtle)]
              rounded-lg hover:text-gray-200 hover:border-violet-500/30 transition-all"
          >
            Legend {legendOpen ? "\u25BE" : "\u25B8"}
          </button>
          <AnimatePresence>
            {legendOpen && (
              <motion.div
                initial={{ opacity: 0, y: 8, height: 0 }}
                animate={{ opacity: 1, y: 0, height: "auto" }}
                exit={{ opacity: 0, y: 8, height: 0 }}
                transition={{ duration: 0.2 }}
                className="mt-1.5 bg-[rgba(8,8,18,0.95)] backdrop-blur-md border border-[var(--border-subtle)]
                  rounded-lg p-3 overflow-hidden"
              >
                <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
                  {LEGEND_ITEMS.map((l) => (
                    <div key={l.label} className="flex items-center gap-1.5">
                      <div className={`w-2 h-2 rounded-full ${l.color}`} />
                      <span className="text-[9px] text-gray-400">{l.label}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-2 pt-2 border-t border-[var(--border-subtle)]">
                  <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-[3px] bg-violet-400 rounded" />
                      <span className="text-[8px] text-gray-500">Hero path (thick)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-[2px] bg-amber-400 rounded" style={{ borderTop: "2px dashed" }} />
                      <span className="text-[8px] text-gray-500">Feedback (dashed gold)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-[2px] bg-red-400 rounded" style={{ borderTop: "2px dashed" }} />
                      <span className="text-[8px] text-gray-500">Kill (dashed red)</span>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* ─── Flywheel Caption (near flywheel loop) ─────────────────────── */}
        <div className="absolute bottom-[340px] left-1/2 -translate-x-1/2 z-10 pointer-events-none text-center">
          <p className="text-[9px] text-amber-400/50 font-medium italic">
            Each venture improves the platform. Each improvement makes the next venture faster.
          </p>
        </div>
      </div>
    </div>
  );
}
