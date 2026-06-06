"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ReactFlow,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
  useNodesState,
  useEdgesState,
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
  type VisionNodeData,
  type NodeCategory,
} from "@/components/vision/vision-data";

// Build React Flow nodes from data
function buildNodes(activeId: string | null, highlightGroup: string | null): Node[] {
  return visionNodes.map((n) => ({
    id: n.id,
    type: "visionNode",
    position: nodePositions[n.id] || { x: 0, y: 0 },
    data: {
      title: n.title,
      type: n.type,
      description: n.description,
      isActive: n.id === activeId,
      isHighlighted: highlightGroup ? n.group === highlightGroup || n.type === highlightGroup : undefined,
    },
  }));
}

// Edge styles per type
function getEdgeStyle(type?: string, isOnPath?: boolean) {
  if (type === "feedback") {
    return {
      stroke: "rgba(234, 179, 8, 0.5)",
      strokeWidth: isOnPath ? 2.5 : 1.5,
      strokeDasharray: "5 5",
    };
  }
  if (type === "spine") {
    return {
      stroke: "rgba(217, 70, 239, 0.6)",
      strokeWidth: isOnPath ? 3 : 2,
    };
  }
  return {
    stroke: isOnPath ? "rgba(139, 92, 246, 0.8)" : "rgba(139, 92, 246, 0.3)",
    strokeWidth: isOnPath ? 2.5 : 1.5,
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
      labelStyle: { fill: "rgba(200,200,220,0.7)", fontSize: 9 },
      markerEnd: { type: MarkerType.ArrowClosed, color: style.stroke },
    };
  });
}

// Filter groups
const FILTERS = [
  { key: null, label: "All" },
  { key: "lifecycle", label: "Lifecycle" },
  { key: "business", label: "Business Intel" },
  { key: "technical", label: "Technical" },
  { key: "spine", label: "Execution Spine" },
  { key: "systems", label: "8 Systems" },
  { key: "validation", label: "Evidence Ladder" },
  { key: "channels", label: "Channels" },
  { key: "architecture", label: "Architecture" },
];

export default function VisionMapPage() {
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<VisionNodeData | null>(null);
  const [highlightGroup, setHighlightGroup] = useState<string | null>(null);
  const [simulating, setSimulating] = useState(false);
  const simRef = useRef<NodeJS.Timeout | null>(null);
  const simIndex = useRef(0);

  const nodeTypes = useMemo(() => ({ visionNode: VisionNode }), []);
  const nodes = useMemo(() => buildNodes(activeNode, highlightGroup), [activeNode, highlightGroup]);
  const edges = useMemo(() => buildEdges(activeNode), [activeNode]);

  // Simulation
  function startSimulation() {
    setSimulating(true);
    simIndex.current = 0;
    simRef.current = setInterval(() => {
      setActiveNode(simulationSequence[simIndex.current]);
      simIndex.current = (simIndex.current + 1) % simulationSequence.length;
    }, 1500);
  }

  function stopSimulation() {
    setSimulating(false);
    if (simRef.current) clearInterval(simRef.current);
    setActiveNode(null);
  }

  useEffect(() => {
    return () => { if (simRef.current) clearInterval(simRef.current); };
  }, []);

  function handleNodeClick(_: any, node: Node) {
    const data = visionNodes.find((n) => n.id === node.id);
    setSelectedNode(data || null);
    setActiveNode(node.id);
  }

  return (
    <div className="h-[calc(100vh-32px)] flex flex-col relative">
      {/* Header bar */}
      <div className="flex items-center justify-between px-6 py-4 z-10 relative">
        <div>
          <h1 className="text-2xl font-bold gradient-text">AI Flywheel Vision Map</h1>
          <p className="text-xs text-[var(--text-muted)] mt-0.5">Interactive state machine — the full venture operating system</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Filters */}
          <div className="flex gap-1 bg-[rgba(0,0,0,0.3)] rounded-lg p-1">
            {FILTERS.map((f) => (
              <button
                key={f.key || "all"}
                onClick={() => setHighlightGroup(f.key)}
                className={`px-2.5 py-1 text-[10px] font-medium rounded-md transition-all ${
                  highlightGroup === f.key
                    ? "bg-violet-600/30 text-violet-200 border border-violet-500/30"
                    : "text-gray-400 hover:text-gray-200"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
          {/* Sim controls */}
          <button
            onClick={simulating ? stopSimulation : startSimulation}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
              simulating
                ? "bg-red-600/20 text-red-300 border border-red-500/30"
                : "bg-emerald-600/20 text-emerald-300 border border-emerald-500/30"
            }`}
          >
            {simulating ? "Stop" : "Simulate"}
          </button>
        </div>
      </div>

      {/* Canvas */}
      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodeClick={handleNodeClick}
          onPaneClick={() => { setSelectedNode(null); setActiveNode(null); }}
          fitView
          minZoom={0.2}
          maxZoom={2}
          proOptions={{ hideAttribution: true }}
          defaultViewport={{ x: 0, y: 0, zoom: 0.6 }}
        >
          <Controls className="!bg-[rgba(10,10,20,0.9)] !border-[var(--border-subtle)] !rounded-lg [&>button]:!bg-transparent [&>button]:!border-[var(--border-subtle)] [&>button]:!text-gray-400 [&>button:hover]:!bg-violet-600/10" />
          <MiniMap
            className="!bg-[rgba(10,10,20,0.9)] !border-[var(--border-subtle)] !rounded-lg"
            nodeColor={(n) => {
              const type = (n.data as any)?.type as NodeCategory;
              const colors: Partial<Record<NodeCategory, string>> = {
                lifecycle_stage: "#8b5cf6",
                business_intelligence: "#10b981",
                technical_execution: "#3b82f6",
                execution_spine: "#d946ef",
                system: "#6366f1",
                outcome: "#a855f7",
                feedback_loop: "#eab308",
              };
              return colors[type] || "#4b5563";
            }}
            maskColor="rgba(0,0,0,0.7)"
          />
          <Background variant={BackgroundVariant.Dots} gap={30} size={1} color="rgba(139, 92, 246, 0.08)" />
        </ReactFlow>

        {/* Detail Panel */}
        <AnimatePresence>
          {selectedNode && (
            <motion.div
              initial={{ x: 320, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 320, opacity: 0 }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
              className="absolute top-4 right-4 w-[300px] bg-[rgba(12,12,22,0.95)] backdrop-blur-xl border border-[var(--border-subtle)] rounded-xl p-5 shadow-2xl z-20"
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <p className="text-xs text-[var(--text-muted)] uppercase tracking-wider">{selectedNode.type.replace(/_/g, " ")}</p>
                  <h3 className="text-base font-bold text-[var(--text-primary)] mt-0.5">{selectedNode.title}</h3>
                </div>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="text-gray-500 hover:text-gray-300 text-lg leading-none"
                >
                  &times;
                </button>
              </div>
              <p className="text-sm text-[var(--text-secondary)] leading-relaxed">{selectedNode.description}</p>
              {selectedNode.group && (
                <div className="mt-3 pt-3 border-t border-[var(--border-subtle)]">
                  <p className="text-[10px] text-[var(--text-muted)]">Group: <span className="text-[var(--text-secondary)]">{selectedNode.group}</span></p>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Legend */}
        <div className="absolute bottom-4 left-4 bg-[rgba(12,12,22,0.9)] backdrop-blur-sm border border-[var(--border-subtle)] rounded-lg p-3 z-20">
          <p className="text-[9px] text-[var(--text-muted)] uppercase tracking-wider mb-2">Legend</p>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1">
            {[
              { color: "bg-violet-500", label: "Lifecycle Stage" },
              { color: "bg-emerald-500", label: "Business Intel" },
              { color: "bg-blue-500", label: "Technical" },
              { color: "bg-fuchsia-500", label: "Execution Spine" },
              { color: "bg-yellow-500", label: "Feedback Loop" },
              { color: "bg-red-500", label: "Decision Point" },
              { color: "bg-indigo-400", label: "System" },
              { color: "bg-purple-400", label: "Outcome" },
            ].map((l) => (
              <div key={l.label} className="flex items-center gap-1.5">
                <div className={`w-2 h-2 rounded-full ${l.color}`} />
                <span className="text-[9px] text-gray-400">{l.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
