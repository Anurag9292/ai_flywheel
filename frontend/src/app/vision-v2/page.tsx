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

import V2Node from "@/components/vision-v2/vision-v2-node";
import {
  v2Nodes,
  v2Edges,
  v2Positions,
  v2Story,
  V2_FILTERS,
  type V2Node as V2NodeData,
  type V2Category,
  type V2EdgeKind,
} from "@/components/vision-v2/vision-v2-data";

// ─── Edge styling ────────────────────────────────────────────────────────────

function edgeStyle(kind: V2EdgeKind, onPath: boolean) {
  switch (kind) {
    case "emits":
      return {
        stroke: onPath ? "rgba(217, 70, 239, 0.95)" : "rgba(217, 70, 239, 0.45)",
        strokeWidth: onPath ? 2.4 : 1.6,
      };
    case "reacts":
      return {
        stroke: onPath ? "rgba(232, 121, 249, 0.9)" : "rgba(217, 70, 239, 0.4)",
        strokeWidth: onPath ? 2.2 : 1.4,
        strokeDasharray: "6 4",
      };
    case "calls":
      return {
        stroke: onPath ? "rgba(148, 163, 184, 0.9)" : "rgba(148, 163, 184, 0.4)",
        strokeWidth: onPath ? 1.6 : 1,
        strokeDasharray: "3 3",
      };
    case "wraps":
      return {
        stroke: "rgba(244, 63, 94, 0.45)",
        strokeWidth: 1.2,
        strokeDasharray: "2 4",
      };
    case "meta_reads":
      return {
        stroke: onPath ? "rgba(251, 191, 36, 1)" : "rgba(251, 191, 36, 0.7)",
        strokeWidth: onPath ? 3 : 2.2,
        strokeDasharray: "8 4",
      };
    case "promotion":
      return {
        stroke: "rgba(251, 191, 36, 0.45)",
        strokeWidth: 1.3,
        strokeDasharray: "5 6",
      };
    case "venture_wires":
      return {
        stroke: onPath ? "rgba(167, 139, 250, 0.9)" : "rgba(139, 92, 246, 0.35)",
        strokeWidth: onPath ? 2 : 1.2,
      };
    case "stage_flow":
      return {
        stroke: onPath ? "rgba(167, 139, 250, 1)" : "rgba(139, 92, 246, 0.7)",
        strokeWidth: onPath ? 3 : 2,
      };
    default:
      return {
        stroke: "rgba(139, 92, 246, 0.3)",
        strokeWidth: 1,
      };
  }
}

// ─── Build nodes / edges ─────────────────────────────────────────────────────

function buildNodes(activeId: string | null, filter: string | null): Node[] {
  return v2Nodes.map((n) => {
    const matches = !filter || n.group === filter;
    return {
      id: n.id,
      type: "v2Node",
      position: v2Positions[n.id] || { x: 0, y: 0 },
      data: {
        id: n.id,
        title: n.title,
        type: n.type,
        description: n.description,
        group: n.group,
        isActive: n.id === activeId,
        isDimmed: filter ? !matches : false,
      },
      draggable: n.type !== "layer_label",
      selectable: n.type !== "layer_label",
    };
  });
}

function buildEdges(activeId: string | null): Edge[] {
  return v2Edges.map((e) => {
    const onPath = e.source === activeId || e.target === activeId;
    const style = edgeStyle(e.edgeType, onPath);
    return {
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.label,
      animated: e.animated || (onPath && (e.edgeType === "emits" || e.edgeType === "stage_flow")),
      style,
      labelStyle: {
        fill: "rgba(200, 200, 220, 0.55)",
        fontSize: 9,
        fontWeight: 500,
      },
      markerEnd:
        e.edgeType === "wraps" || e.edgeType === "promotion"
          ? undefined
          : {
              type: MarkerType.ArrowClosed,
              color: style.stroke,
              width: 12,
              height: 12,
            },
    };
  });
}

// ─── Legend ──────────────────────────────────────────────────────────────────

const LEGEND = [
  { color: "bg-amber-300", label: "Layer 3 — Meta (read-only)" },
  { color: "bg-fuchsia-400", label: "Event Bus / Events" },
  { color: "bg-violet-400", label: "Layer 2 — Venture stages" },
  { color: "bg-blue-400", label: "L1 node — dumb" },
  { color: "bg-emerald-400", label: "L1 node — agentic" },
  { color: "bg-slate-400", label: "L1 library tool" },
  { color: "bg-rose-400", label: "L1 substrate (always-on)" },
];

const EDGE_LEGEND = [
  { color: "rgba(217, 70, 239, 0.9)", dashed: false, label: "emits → bus" },
  { color: "rgba(217, 70, 239, 0.9)", dashed: true, label: "reacts (subscription)" },
  { color: "rgba(148, 163, 184, 0.7)", dashed: true, label: "calls (library, no event)" },
  { color: "rgba(244, 63, 94, 0.5)", dashed: true, label: "substrate wraps" },
  { color: "rgba(251, 191, 36, 0.9)", dashed: true, label: "Layer 3 reads" },
  { color: "rgba(139, 92, 246, 0.8)", dashed: false, label: "venture wires / stage flow" },
];

// ─── Page ────────────────────────────────────────────────────────────────────

export default function VisionV2Page() {
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<V2NodeData | null>(null);
  const [filter, setFilter] = useState<string | null>(null);
  const [storyOn, setStoryOn] = useState(false);
  const [storyStep, setStoryStep] = useState(0);
  const [storyTextNow, setStoryTextNow] = useState<string | null>(null);
  const [legendOpen, setLegendOpen] = useState(false);
  const stepRef = useRef(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const nodeTypes = useMemo(() => ({ v2Node: V2Node }), []);
  const nodes = useMemo(() => buildNodes(activeNode, filter), [activeNode, filter]);
  const edges = useMemo(() => buildEdges(activeNode), [activeNode]);

  // ─── Story walk ───────────────────────────────────────────────────────────

  const startStory = useCallback(() => {
    setStoryOn(true);
    setSelectedNode(null);
    stepRef.current = 0;

    const advance = () => {
      const step = v2Story[stepRef.current];
      setActiveNode(step.id);
      setStoryStep(stepRef.current + 1);
      setStoryTextNow(step.text);
      stepRef.current = (stepRef.current + 1) % v2Story.length;
    };

    advance();
    intervalRef.current = setInterval(advance, 2400);
  }, []);

  const stopStory = useCallback(() => {
    setStoryOn(false);
    setStoryTextNow(null);
    setStoryStep(0);
    if (intervalRef.current) clearInterval(intervalRef.current);
    setActiveNode(null);
  }, []);

  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  // Auto-start the story shortly after mount
  useEffect(() => {
    const t = setTimeout(() => startStory(), 700);
    return () => clearTimeout(t);
  }, [startStory]);

  // ─── Click handlers ───────────────────────────────────────────────────────

  const onNodeClick = useCallback(
    (_: React.MouseEvent, n: Node) => {
      if (storyOn) stopStory();
      const data = v2Nodes.find((x) => x.id === n.id);
      if (data?.type === "layer_label") return;
      setSelectedNode(data || null);
      setActiveNode(n.id);
    },
    [storyOn, stopStory]
  );

  const onPaneClick = useCallback(() => {
    if (storyOn) return;
    setSelectedNode(null);
    setActiveNode(null);
  }, [storyOn]);

  // ─── MiniMap node color ───────────────────────────────────────────────────

  const minimapColor = useCallback((n: Node) => {
    const t = (n.data as Record<string, unknown>)?.type as V2Category | undefined;
    const map: Partial<Record<V2Category, string>> = {
      layer3_meta: "#fbbf24",
      event_bus: "#d946ef",
      event: "#d946ef",
      l2_stage: "#8b5cf6",
      l2_venture_header: "#a855f7",
      l1_node_dumb: "#3b82f6",
      l1_node_agentic: "#10b981",
      l1_lib: "#94a3b8",
      l1_substrate: "#f43f5e",
      layer_label: "#1f2937",
    };
    return map[t as V2Category] || "#4b5563";
  }, []);

  return (
    <div className="h-[calc(100vh-32px)] flex flex-col relative overflow-hidden">
      {/* ─── Header ─────────────────────────────────────────────────────── */}
      <div className="absolute top-0 left-0 right-0 z-30 px-4 py-2 bg-gradient-to-b from-[var(--bg-primary)] via-[var(--bg-primary)]/90 to-transparent pointer-events-none">
        <div className="flex items-center justify-between pointer-events-auto">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold gradient-text">AI Flywheel — V2</h1>
            <p className="text-[10px] text-[var(--text-muted)] hidden sm:block">
              Bottom-up · 3 layers · event-driven · derived from PostlineAI
            </p>
            <a
              href="/vision"
              className="text-[10px] text-violet-300/70 hover:text-violet-200 underline underline-offset-2"
            >
              ← old vision (v1)
            </a>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex gap-0.5 bg-[rgba(5,5,15,0.85)] backdrop-blur-md rounded-lg p-0.5 border border-[var(--border-subtle)]">
              {V2_FILTERS.map((f) => (
                <button
                  key={f.key || "all"}
                  onClick={() => setFilter(f.key)}
                  className={`px-2 py-1 text-[9px] font-medium rounded-md transition-all ${
                    filter === f.key
                      ? "bg-violet-600/40 text-violet-100 border border-violet-400/40"
                      : "text-gray-500 hover:text-gray-300 hover:bg-white/5"
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>

            <button
              onClick={storyOn ? stopStory : startStory}
              className={`px-3 py-1.5 text-[10px] font-semibold rounded-lg transition-all whitespace-nowrap ${
                storyOn
                  ? "bg-red-600/25 text-red-200 border border-red-500/40"
                  : "bg-emerald-600/25 text-emerald-200 border border-emerald-500/40"
              }`}
            >
              {storyOn ? "Stop Walkthrough" : "Play Walkthrough"}
            </button>
          </div>
        </div>
      </div>

      {/* ─── Walkthrough story card ────────────────────────────────────── */}
      <AnimatePresence>
        {storyTextNow && storyOn && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            transition={{ duration: 0.3 }}
            className="absolute top-[48px] right-4 z-20 w-[340px] p-3 rounded-xl
              bg-[rgba(8,8,18,0.96)] backdrop-blur-xl border border-violet-500/30
              shadow-[0_0_40px_rgba(139,92,246,0.12)]"
          >
            <div className="flex items-center gap-2 mb-2">
              <span className="px-2 py-0.5 text-[9px] font-bold uppercase tracking-widest text-violet-300 bg-violet-900/50 rounded">
                Step {storyStep} / {v2Story.length}
              </span>
              <span className="text-[10px] text-violet-300/70 font-medium">
                PostlineAI walkthrough
              </span>
            </div>
            <p className="text-sm text-gray-200 leading-relaxed">{storyTextNow}</p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ─── Canvas ────────────────────────────────────────────────────── */}
      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          minZoom={0.1}
          maxZoom={3}
          proOptions={{ hideAttribution: true }}
          defaultViewport={{ x: 30, y: -40, zoom: 0.45 }}
        >
          <Controls
            className="!bg-[rgba(8,8,18,0.95)] !border-[var(--border-subtle)] !rounded-lg !shadow-lg
              [&>button]:!bg-transparent [&>button]:!border-[var(--border-subtle)]
              [&>button]:!text-gray-400 [&>button:hover]:!bg-violet-600/10 [&>button:hover]:!text-gray-200"
            position="bottom-left"
          />
          <MiniMap
            className="!bg-[rgba(8,8,18,0.95)] !border-[var(--border-subtle)] !rounded-lg"
            nodeColor={minimapColor}
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

        {/* ─── Detail panel ──────────────────────────────────────────── */}
        <AnimatePresence>
          {selectedNode && (
            <motion.div
              initial={{ x: 400, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 400, opacity: 0 }}
              transition={{ type: "spring", damping: 28, stiffness: 220 }}
              className="absolute top-4 right-4 w-[360px] bg-[rgba(8,8,16,0.97)] backdrop-blur-xl
                border border-[var(--border-subtle)] rounded-xl p-5 shadow-2xl z-30"
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <p className="text-[9px] text-violet-400/80 uppercase tracking-[0.15em] font-semibold">
                    {selectedNode.type.replace(/_/g, " ")}
                  </p>
                  <h3 className="text-lg font-bold text-white mt-1">
                    {selectedNode.title}
                  </h3>
                </div>
                <button
                  onClick={() => {
                    setSelectedNode(null);
                    setActiveNode(null);
                  }}
                  className="text-gray-500 hover:text-gray-200 text-lg leading-none p-1 transition-colors"
                >
                  ×
                </button>
              </div>
              <p className="text-sm text-gray-300 leading-relaxed">
                {selectedNode.description}
              </p>
              <div className="mt-4 pt-3 border-t border-[var(--border-subtle)] text-[10px] text-gray-500">
                <p>
                  Group:{" "}
                  <span className="text-gray-300 font-medium capitalize">
                    {selectedNode.group}
                  </span>
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ─── Legend ────────────────────────────────────────────────── */}
        <div className="absolute bottom-14 left-4 z-20">
          <button
            onClick={() => setLegendOpen(!legendOpen)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-semibold text-gray-400
              bg-[rgba(8,8,18,0.9)] backdrop-blur-sm border border-[var(--border-subtle)]
              rounded-lg hover:text-gray-200 hover:border-violet-500/30 transition-all"
          >
            Legend {legendOpen ? "▾" : "▸"}
          </button>
          <AnimatePresence>
            {legendOpen && (
              <motion.div
                initial={{ opacity: 0, y: 8, height: 0 }}
                animate={{ opacity: 1, y: 0, height: "auto" }}
                exit={{ opacity: 0, y: 8, height: 0 }}
                transition={{ duration: 0.2 }}
                className="mt-1.5 bg-[rgba(8,8,18,0.95)] backdrop-blur-md border border-[var(--border-subtle)]
                  rounded-lg p-3 overflow-hidden w-[280px]"
              >
                <p className="text-[9px] uppercase tracking-widest text-gray-500 mb-2">
                  Nodes
                </p>
                <div className="grid grid-cols-1 gap-1.5 mb-3">
                  {LEGEND.map((l) => (
                    <div key={l.label} className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${l.color}`} />
                      <span className="text-[10px] text-gray-300">{l.label}</span>
                    </div>
                  ))}
                </div>
                <p className="text-[9px] uppercase tracking-widest text-gray-500 mb-2">
                  Edges
                </p>
                <div className="grid grid-cols-1 gap-1.5">
                  {EDGE_LEGEND.map((l) => (
                    <div key={l.label} className="flex items-center gap-2">
                      <svg width="28" height="6">
                        <line
                          x1={0}
                          y1={3}
                          x2={28}
                          y2={3}
                          stroke={l.color}
                          strokeWidth={2}
                          strokeDasharray={l.dashed ? "4 3" : undefined}
                        />
                      </svg>
                      <span className="text-[10px] text-gray-300">{l.label}</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* ─── Bus caption ────────────────────────────────────────────── */}
        <div className="absolute top-[105px] left-1/2 -translate-x-1/2 z-10 pointer-events-none text-center">
          <p className="text-[9px] text-amber-400/60 font-semibold uppercase tracking-[0.22em]">
            Layer 3 reads everything — never executes venture work
          </p>
        </div>
      </div>
    </div>
  );
}
