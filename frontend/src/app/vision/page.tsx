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
  storyModeText,
  type VisionNodeData,
  type NodeCategory,
} from "@/components/vision/vision-data";

// ─── Build React Flow nodes from data ────────────────────────────────────────

function buildNodes(activeId: string | null, highlightGroup: string | null): Node[] {
  return visionNodes.map((n) => ({
    id: n.id,
    type: "visionNode",
    position: nodePositions[n.id] || { x: 0, y: 0 },
    data: {
      title: n.title,
      type: n.type,
      description: n.description,
      group: n.group,
      isActive: n.id === activeId,
      isHighlighted: highlightGroup
        ? n.group === highlightGroup || n.type === highlightGroup
        : undefined,
    },
  }));
}

// ─── Edge styling ────────────────────────────────────────────────────────────

function getEdgeStyle(type?: string, isOnPath?: boolean) {
  if (type === "kill") {
    return {
      stroke: "rgba(239, 68, 68, 0.7)",
      strokeWidth: 2,
      strokeDasharray: "4 4",
    };
  }
  if (type === "feedback") {
    return {
      stroke: isOnPath ? "rgba(234, 179, 8, 0.8)" : "rgba(234, 179, 8, 0.35)",
      strokeWidth: isOnPath ? 2.5 : 1.5,
      strokeDasharray: "6 4",
    };
  }
  if (type === "spine") {
    return {
      stroke: isOnPath ? "rgba(217, 70, 239, 0.8)" : "rgba(217, 70, 239, 0.4)",
      strokeWidth: isOnPath ? 3 : 2,
    };
  }
  // Default (lifecycle & connections)
  return {
    stroke: isOnPath ? "rgba(139, 92, 246, 0.9)" : "rgba(139, 92, 246, 0.25)",
    strokeWidth: isOnPath ? 3 : 1.5,
  };
}

function buildEdges(activeId: string | null): Edge[] {
  return visionEdges.map((e) => {
    const isOnPath = e.source === activeId || e.target === activeId;
    const style = getEdgeStyle(e.type, isOnPath);
    return {
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.label,
      animated: e.animated || isOnPath,
      style,
      labelStyle: { fill: "rgba(200,200,220,0.6)", fontSize: 9, fontWeight: 500 },
      markerEnd: { type: MarkerType.ArrowClosed, color: style.stroke },
    };
  });
}

// ─── Filter groups ───────────────────────────────────────────────────────────

const FILTERS = [
  { key: null, label: "All" },
  { key: "lifecycle", label: "Lifecycle" },
  { key: "business", label: "Business Intel" },
  { key: "technical", label: "Technical" },
  { key: "spine", label: "Spine" },
  { key: "flywheel", label: "Flywheel" },
  { key: "validation", label: "Validation" },
  { key: "systems", label: "Systems" },
];

// ─── Main Page Component ─────────────────────────────────────────────────────

export default function VisionMapPage() {
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<VisionNodeData | null>(null);
  const [highlightGroup, setHighlightGroup] = useState<string | null>(null);
  const [simulating, setSimulating] = useState(false);
  const [storyText, setStoryText] = useState<string | null>(null);
  const simRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const simIndex = useRef(0);

  const nodeTypes = useMemo(() => ({ visionNode: VisionNode }), []);
  const nodes = useMemo(() => buildNodes(activeNode, highlightGroup), [activeNode, highlightGroup]);
  const edges = useMemo(() => buildEdges(activeNode), [activeNode]);

  // ─── Simulation ──────────────────────────────────────────────────────────

  function startSimulation() {
    setSimulating(true);
    setSelectedNode(null);
    simIndex.current = 0;

    const step = () => {
      const nodeId = simulationSequence[simIndex.current];
      setActiveNode(nodeId);
      setStoryText(storyModeText[nodeId] || null);
      simIndex.current = (simIndex.current + 1) % simulationSequence.length;
    };

    step(); // immediate first step
    simRef.current = setInterval(step, 1000); // 1s per step = ~10s full cycle
  }

  function stopSimulation() {
    setSimulating(false);
    setStoryText(null);
    if (simRef.current) clearInterval(simRef.current);
    setActiveNode(null);
  }

  useEffect(() => {
    return () => {
      if (simRef.current) clearInterval(simRef.current);
    };
  }, []);

  // Auto-start simulation on mount for dramatic effect
  useEffect(() => {
    const timer = setTimeout(() => {
      startSimulation();
    }, 800);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleNodeClick(_: any, node: Node) {
    if (simulating) stopSimulation();
    const data = visionNodes.find((n) => n.id === node.id);
    setSelectedNode(data || null);
    setActiveNode(node.id);
    setStoryText(data?.storyText || null);
  }

  return (
    <div className="h-[calc(100vh-32px)] flex flex-col relative">
      {/* ─── Header ──────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-6 py-3 z-10 relative">
        <div>
          <h1 className="text-2xl font-bold gradient-text">AI Flywheel Vision Map</h1>
          <p className="text-sm text-amber-300/80 font-medium mt-0.5 tracking-wide">
            From hunch to revenue. Every cycle faster.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Filter Buttons */}
          <div className="flex gap-1 bg-[rgba(0,0,0,0.4)] rounded-lg p-1.5 border border-[var(--border-subtle)]">
            {FILTERS.map((f) => (
              <button
                key={f.key || "all"}
                onClick={() => setHighlightGroup(f.key)}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                  highlightGroup === f.key
                    ? "bg-violet-600/40 text-violet-100 border border-violet-400/40 shadow-[0_0_10px_rgba(139,92,246,0.2)]"
                    : "text-gray-400 hover:text-gray-200 hover:bg-white/5"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
          {/* Simulation Control */}
          <button
            onClick={simulating ? stopSimulation : startSimulation}
            className={`px-4 py-2 text-sm font-semibold rounded-lg transition-all ${
              simulating
                ? "bg-red-600/30 text-red-200 border border-red-500/40 shadow-[0_0_15px_rgba(239,68,68,0.2)]"
                : "bg-emerald-600/30 text-emerald-200 border border-emerald-500/40 shadow-[0_0_15px_rgba(16,185,129,0.2)]"
            }`}
          >
            {simulating ? "Stop Story" : "Play Story"}
          </button>
        </div>
      </div>

      {/* ─── Story Mode Overlay ──────────────────────────────────────────── */}
      <AnimatePresence>
        {storyText && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3 }}
            className="absolute top-[72px] left-1/2 -translate-x-1/2 z-20 px-6 py-3 rounded-xl
              bg-[rgba(10,10,20,0.9)] backdrop-blur-xl border border-violet-500/30
              shadow-[0_0_30px_rgba(139,92,246,0.15)]"
          >
            <p className="text-sm text-violet-100 font-medium text-center whitespace-nowrap">
              {storyText}
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ─── Canvas ──────────────────────────────────────────────────────── */}
      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodeClick={handleNodeClick}
          onPaneClick={() => {
            if (simulating) return;
            setSelectedNode(null);
            setActiveNode(null);
            setStoryText(null);
          }}
          minZoom={0.15}
          maxZoom={2.5}
          proOptions={{ hideAttribution: true }}
          defaultViewport={{ x: 50, y: 20, zoom: 0.55 }}
        >
          <Controls
            className="!bg-[rgba(10,10,20,0.9)] !border-[var(--border-subtle)] !rounded-lg
              [&>button]:!bg-transparent [&>button]:!border-[var(--border-subtle)]
              [&>button]:!text-gray-400 [&>button:hover]:!bg-violet-600/10"
          />
          <MiniMap
            className="!bg-[rgba(10,10,20,0.9)] !border-[var(--border-subtle)] !rounded-lg"
            nodeColor={(n) => {
              const type = (n.data as any)?.type as NodeCategory;
              const colors: Partial<Record<NodeCategory, string>> = {
                founder_state: "#f59e0b",
                lifecycle_stage: "#8b5cf6",
                business_intelligence: "#10b981",
                technical_execution: "#3b82f6",
                execution_spine: "#d946ef",
                system: "#6366f1",
                outcome: "#fbbf24",
                feedback_loop: "#eab308",
                kill_signal: "#ef4444",
                validation_checkpoint: "#06b6d4",
              };
              return colors[type] || "#4b5563";
            }}
            maskColor="rgba(0,0,0,0.75)"
          />
          <Background
            variant={BackgroundVariant.Dots}
            gap={40}
            size={1}
            color="rgba(139, 92, 246, 0.06)"
          />
        </ReactFlow>

        {/* ─── Detail Panel (Right Side — Wider) ──────────────────────────── */}
        <AnimatePresence>
          {selectedNode && (
            <motion.div
              initial={{ x: 400, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 400, opacity: 0 }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
              className="absolute top-4 right-4 w-[360px] bg-[rgba(10,10,18,0.95)] backdrop-blur-xl
                border border-[var(--border-subtle)] rounded-xl p-6 shadow-2xl z-20"
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <p className="text-[10px] text-violet-400 uppercase tracking-widest font-semibold">
                    {selectedNode.type.replace(/_/g, " ")}
                  </p>
                  <h3 className="text-lg font-bold text-white mt-1">{selectedNode.title}</h3>
                </div>
                <button
                  onClick={() => { setSelectedNode(null); setActiveNode(null); setStoryText(null); }}
                  className="text-gray-500 hover:text-gray-200 text-xl leading-none p-1"
                >
                  &times;
                </button>
              </div>
              <p className="text-sm text-gray-300 leading-relaxed">{selectedNode.description}</p>
              {selectedNode.group && (
                <div className="mt-4 pt-3 border-t border-[var(--border-subtle)]">
                  <p className="text-xs text-gray-500">
                    Group: <span className="text-gray-300 font-medium">{selectedNode.group}</span>
                  </p>
                </div>
              )}
              {selectedNode.storyText && (
                <div className="mt-3 p-3 rounded-lg bg-violet-950/30 border border-violet-500/20">
                  <p className="text-xs text-violet-200 italic">{selectedNode.storyText}</p>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* ─── Legend ─────────────────────────────────────────────────────── */}
        <div className="absolute bottom-4 left-4 bg-[rgba(10,10,18,0.9)] backdrop-blur-sm
          border border-[var(--border-subtle)] rounded-lg p-3 z-20">
          <p className="text-[9px] text-gray-500 uppercase tracking-wider mb-2 font-semibold">Legend</p>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
            {[
              { color: "bg-violet-500", label: "Lifecycle" },
              { color: "bg-amber-500", label: "Founder / Outcome" },
              { color: "bg-emerald-500", label: "Business Intel" },
              { color: "bg-blue-500", label: "Technical" },
              { color: "bg-fuchsia-500", label: "Execution Spine" },
              { color: "bg-yellow-500", label: "Feedback Loop" },
              { color: "bg-red-500", label: "Kill Signal" },
              { color: "bg-cyan-500", label: "Validation" },
            ].map((l) => (
              <div key={l.label} className="flex items-center gap-1.5">
                <div className={`w-2.5 h-2.5 rounded-full ${l.color}`} />
                <span className="text-[10px] text-gray-400">{l.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
