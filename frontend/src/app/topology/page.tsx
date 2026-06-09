"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import FlowNode from "@/components/topology/flow-node";
import FunctionLegend from "@/components/topology/function-legend";
import ReviewPanel from "@/components/topology/review-panel";
import TriggerPanel from "@/components/topology/trigger-panel";
import { buildFlow, type NodeFunctionMap } from "@/lib/topology-layout";
import {
  fetchTopology,
  fetchTraces,
  fetchVenture,
  type Topology,
  type TraceChain,
  type TraceRow,
  type VentureResponse,
} from "@/lib/topology-api";

const nodeTypes = { flow: FlowNode };
const PLAY_INTERVAL_MS = 1400;

// A stable, readable palette for functions (assigned in declaration order).
const FUNCTION_PALETTE = [
  "#f59e0b", // amber
  "#3b82f6", // blue
  "#10b981", // emerald
  "#ec4899", // pink
  "#a855f7", // purple
  "#14b8a6", // teal
  "#ef4444", // red
  "#84cc16", // lime
];

export default function TopologyPage() {
  const [topo, setTopo] = useState<Topology | null>(null);
  const [venture, setVenture] = useState<VentureResponse | null>(null);
  const [chains, setChains] = useState<TraceChain[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Replay state.
  const [selectedChain, setSelectedChain] = useState<string | null>(null);
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  // Bumped on each trigger/approval so the review queue reloads its pending list.
  const [reviewRefresh, setReviewRefresh] = useState(0);
  // Which function the legend is focusing (dims everything else); null = none.
  const [focusedFunction, setFocusedFunction] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [t, tr, v] = await Promise.all([
        fetchTopology(),
        fetchTraces(),
        fetchVenture(),
      ]);
      setTopo(t);
      setVenture(v);
      const filtered = (tr.chains ?? []).filter((c) =>
        (c.steps ?? []).some((s) => s.node),
      );
      setChains(filtered);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // After triggering a run, reload traces and jump to (and play) the new run.
  const onTriggered = useCallback(
    async (correlationId: string) => {
      // Let the review queue re-check for newly parked / cleared items.
      setReviewRefresh((n) => n + 1);
      try {
        const tr = await fetchTraces();
        const filtered = (tr.chains ?? []).filter((c) =>
          (c.steps ?? []).some((s) => s.node),
        );
        setChains(filtered);
        if (correlationId) {
          setSelectedChain(correlationId);
          setStep(0);
          setPlaying(true);
        } else {
          // Cleared: drop selection.
          setSelectedChain(null);
          setStep(0);
          setPlaying(false);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      }
    },
    [],
  );

  // Assign each function a stable color (declaration order) and build the
  // node -> function-tags map that colors node tiles. A node can be in several
  // functions (overlap), so it gets multiple tags.
  const functionColors = useMemo<Record<string, string>>(() => {
    const map: Record<string, string> = {};
    (venture?.functions ?? []).forEach((f, i) => {
      map[f.name] = FUNCTION_PALETTE[i % FUNCTION_PALETTE.length];
    });
    return map;
  }, [venture]);

  const nodeFunctions = useMemo<NodeFunctionMap>(() => {
    const map: NodeFunctionMap = {};
    for (const f of venture?.functions ?? []) {
      for (const nodeName of f.nodes) {
        (map[nodeName] ??= []).push({ name: f.name, color: functionColors[f.name] });
      }
    }
    return map;
  }, [venture, functionColors]);

  // The set of node names belonging to the focused function (for dimming).
  const focusedNodeNames = useMemo<Set<string>>(() => {
    if (!focusedFunction) return new Set();
    const f = venture?.functions.find((x) => x.name === focusedFunction);
    return new Set(f?.nodes ?? []);
  }, [focusedFunction, venture]);

  const { nodes: baseNodes, edges: baseEdges } = useMemo<{
    nodes: Node[];
    edges: Edge[];
  }>(
    () => (topo ? buildFlow(topo, nodeFunctions) : { nodes: [], edges: [] }),
    [topo, nodeFunctions],
  );

  const activeChain = chains.find((c) => c.correlation_id === selectedChain);
  const steps = activeChain?.steps ?? [];
  const current: TraceRow | undefined = steps[step];

  // Auto-play: advance one step on a timer, stop at the end.
  useEffect(() => {
    if (!playing || !activeChain) return;
    if (step >= steps.length - 1) {
      setPlaying(false);
      return;
    }
    const id = setTimeout(() => setStep((s) => s + 1), PLAY_INTERVAL_MS);
    return () => clearTimeout(id);
  }, [playing, step, steps.length, activeChain]);

  // Highlight the firing node for the current step; dim nodes outside the
  // focused function (if any).
  const activeNodeName = current?.node ?? null;
  const nodes = useMemo<Node[]>(
    () =>
      baseNodes.map((n) => {
        const nodeName = n.id.startsWith("node:") ? n.id.slice("node:".length) : null;
        const dimmed = focusedFunction !== null
          ? !(nodeName !== null && focusedNodeNames.has(nodeName))
          : false;
        return {
          ...n,
          data: { ...n.data, active: n.id === `node:${activeNodeName}`, dimmed },
        };
      }),
    [baseNodes, activeNodeName, focusedFunction, focusedNodeNames],
  );

  // Highlight the edges involved in the current step: trigger event -> node,
  // and node -> each emitted event.
  const edges = useMemo<Edge[]>(() => {
    if (!current) return baseEdges;
    const hot = new Set<string>();
    hot.add(`event:${current.trigger_type}->node:${current.node}`); // reacts
    for (const t of current.emitted_types) {
      hot.add(`node:${current.node}->event:${t}`); // emits
    }
    return baseEdges.map((e) => {
      const key = `${e.source}->${e.target}`;
      const isHot = hot.has(key);
      return {
        ...e,
        animated: isHot ? true : e.animated,
        style: {
          ...e.style,
          stroke: isHot ? "rgba(251,191,36,1)" : e.style?.stroke,
          strokeWidth: isHot ? 3 : e.style?.strokeWidth,
        },
      };
    });
  }, [baseEdges, current]);

  // When a function is focused, fade edges that don't touch one of its nodes.
  const displayEdges = useMemo<Edge[]>(() => {
    if (focusedFunction === null) return edges;
    return edges.map((e) => {
      const src = e.source.startsWith("node:") ? e.source.slice("node:".length) : null;
      const tgt = e.target.startsWith("node:") ? e.target.slice("node:".length) : null;
      const touches =
        (src !== null && focusedNodeNames.has(src)) ||
        (tgt !== null && focusedNodeNames.has(tgt));
      return touches ? e : { ...e, style: { ...e.style, opacity: 0.12 } };
    });
  }, [edges, focusedFunction, focusedNodeNames]);

  const t0 = steps[0]?.captured_at ? Date.parse(steps[0].captured_at) : 0;

  const selectChain = (cid: string) => {
    setSelectedChain(cid);
    setStep(0);
    setPlaying(false);
  };

  return (
    <div className="flex h-screen w-screen flex-col bg-[#0a0a14] text-white">
      <header className="flex items-center justify-between border-b border-white/10 px-6 py-3">
        <div>
          <h1 className="text-lg font-semibold">
            Topology — live, code-derived
            {venture && (
              <span className="ml-2 text-sm font-normal text-slate-400">
                · venture: <span className="text-fuchsia-300">{venture.name}</span>
                {" · "}
                {venture.functions.length} functions
              </span>
            )}
            {venture && (
              <span
                title={
                  venture.mode === "live"
                    ? "Lead-gen discovery hits real public ATS APIs (Greenhouse/Lever/Ashby)."
                    : "Lead-gen discovery uses canned fixtures — fast, offline, deterministic."
                }
                className={`ml-2 rounded px-1.5 py-0.5 align-middle text-[10px] font-semibold uppercase tracking-wide ${
                  venture.mode === "live"
                    ? "bg-amber-500/20 text-amber-200"
                    : "bg-slate-500/20 text-slate-300"
                }`}
              >
                {venture.mode === "live" ? "● live" : "fake"}
              </span>
            )}
          </h1>
          <p className="text-xs text-slate-400">
            From <code className="text-fuchsia-300">runtime.describe()</code> +
            the <code className="text-fuchsia-300">trace.captured</code> stream
            {" · "}functions from{" "}
            <code className="text-fuchsia-300">/api/venture</code>.
          </p>
        </div>
        <button
          onClick={() => void load()}
          className="rounded-lg border border-white/15 px-3 py-1.5 text-sm hover:bg-white/10"
        >
          Refresh
        </button>
      </header>

      {error && (
        <div className="flex items-center justify-between gap-4 border-b border-amber-500/40 bg-amber-950/30 px-6 py-3 text-sm text-amber-100">
          <span>⏸ {error}</span>
          <button
            onClick={() => void load()}
            className="shrink-0 rounded-md border border-amber-300/40 px-3 py-1 text-xs hover:bg-amber-500/10"
          >
            Retry
          </button>
        </div>
      )}

      {topo &&
        (topo.lint.orphan_emitted.length > 0 ||
          topo.lint.unproduced_reacted.length > 0) && (
          <div className="border-b border-amber-500/30 bg-amber-950/30 px-6 py-2 text-xs text-amber-200">
            <span className="font-semibold">Lint:</span>{" "}
            {topo.lint.orphan_emitted.length > 0 &&
              `orphan emitted: ${topo.lint.orphan_emitted.join(", ")}. `}
            {topo.lint.unproduced_reacted.length > 0 &&
              `reacted but not produced here: ${topo.lint.unproduced_reacted.join(", ")}.`}
          </div>
        )}

      <div className="flex min-h-0 flex-1">
        <div className="min-w-0 flex-1">
          <ReactFlow
            nodes={nodes}
            edges={displayEdges}
            nodeTypes={nodeTypes}
            fitView
            proOptions={{ hideAttribution: true }}
          >
            <Background variant={BackgroundVariant.Dots} gap={24} color="#1e293b" />
            <Controls />
            <MiniMap
              pannable
              zoomable
              maskColor="rgba(10,10,20,0.7)"
              style={{ background: "#0d1117" }}
              nodeColor={(n) =>
                (n.data as { kind?: string }).kind === "event"
                  ? "#d946ef"
                  : (n.data as { kind?: string }).kind === "node_agentic"
                    ? "#10b981"
                    : (n.data as { kind?: string }).kind === "node_dumb"
                      ? "#3b82f6"
                      : "#64748b"
              }
            />
          </ReactFlow>
        </div>

        {/* Chronological timeline / replay (View 2). The whole sidebar scrolls
            as a single column — there are too many stacked panels (Trigger,
            Functions, Review queue, Run timeline + steps) to fit on one screen
            in tall configurations, and a single scroll is simpler and more
            predictable than nested scroll regions. */}
        <aside className="flex w-96 shrink-0 flex-col overflow-y-auto border-l border-white/10 bg-[#0d0d1a]">
          <TriggerPanel onTriggered={onTriggered} />

          {venture && (
            <FunctionLegend
              functions={venture.functions}
              colors={functionColors}
              active={focusedFunction}
              onSelect={setFocusedFunction}
            />
          )}

          <ReviewPanel onApproved={onTriggered} refreshKey={reviewRefresh} />

          <div className="border-b border-white/10 p-4">
            <h2 className="mb-1 text-sm font-semibold">Run timeline</h2>
            <p className="text-xs text-slate-400">
              Each run = one published event + every reaction it caused, in
              chronological order.
            </p>
          </div>

          {/* Run picker. */}
          <div className="border-b border-white/10 p-3">
            {chains.length === 0 && (
              <p className="text-xs text-slate-500">
                No runs yet. Use <span className="text-emerald-300">Trigger a run</span>{" "}
                above to publish a real event and watch it flow.
              </p>
            )}
            <div className="flex flex-wrap gap-1.5">
              {chains.map((c) => (
                <button
                  key={c.correlation_id}
                  onClick={() => selectChain(c.correlation_id)}
                  className={`rounded-md border px-2 py-1 text-left text-[11px] ${
                    selectedChain === c.correlation_id
                      ? "border-amber-300/60 bg-amber-500/10"
                      : "border-white/10 hover:bg-white/5"
                  }`}
                >
                  <span className="font-mono text-slate-400">
                    {c.correlation_id.slice(0, 8)}
                  </span>{" "}
                  <span className="text-slate-200">
                    {c.steps.length} step{c.steps.length === 1 ? "" : "s"}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Playback controls. */}
          {activeChain && (
            <div className="flex items-center gap-2 border-b border-white/10 p-3">
              <button
                onClick={() => {
                  if (step >= steps.length - 1) setStep(0);
                  setPlaying((p) => !p);
                }}
                className="rounded-md border border-white/15 px-3 py-1 text-xs hover:bg-white/10"
              >
                {playing ? "⏸ Pause" : "▶ Play"}
              </button>
              <button
                onClick={() => {
                  setPlaying(false);
                  setStep((s) => Math.max(0, s - 1));
                }}
                disabled={step === 0}
                className="rounded-md border border-white/15 px-2 py-1 text-xs disabled:opacity-40"
              >
                ‹ Prev
              </button>
              <button
                onClick={() => {
                  setPlaying(false);
                  setStep((s) => Math.min(steps.length - 1, s + 1));
                }}
                disabled={step >= steps.length - 1}
                className="rounded-md border border-white/15 px-2 py-1 text-xs disabled:opacity-40"
              >
                Next ›
              </button>
              <button
                onClick={() => {
                  setPlaying(false);
                  setStep(0);
                }}
                className="ml-auto rounded-md border border-white/15 px-2 py-1 text-xs hover:bg-white/10"
              >
                ⟲ Reset
              </button>
            </div>
          )}

          {/* The chronological steps. Lays out at natural height; the sidebar
              itself scrolls (no nested scroll region). */}
          <ol className="p-3">
            {steps.map((s, i) => {
              const dt = s.captured_at ? Date.parse(s.captured_at) - t0 : 0;
              const isActive = i === step;
              const past = i < step;
              return (
                <li key={i} className="relative pl-5">
                  {/* connector line */}
                  {i < steps.length - 1 && (
                    <span className="absolute left-[7px] top-5 h-full w-px bg-white/15" />
                  )}
                  <button
                    onClick={() => {
                      setPlaying(false);
                      setStep(i);
                    }}
                    className={`mb-2 block w-full rounded-lg border p-2.5 text-left transition-all ${
                      isActive
                        ? "border-amber-300/70 bg-amber-500/10 shadow-[0_0_18px_rgba(251,191,36,0.25)]"
                        : past
                          ? "border-white/10 bg-white/[0.03] opacity-80"
                          : "border-white/10 hover:bg-white/5"
                    }`}
                  >
                    <span
                      className={`absolute left-0 top-3 h-3.5 w-3.5 rounded-full border-2 ${
                        isActive
                          ? "border-amber-300 bg-amber-400"
                          : past
                            ? "border-emerald-400 bg-emerald-500"
                            : "border-slate-500 bg-slate-800"
                      }`}
                    />
                    <div className="mb-1 flex items-center justify-between">
                      <span className="font-mono text-[10px] text-slate-400">
                        t+{dt}ms
                      </span>
                      <span className="flex gap-1">
                        {s.is_start && (
                          <span className="rounded bg-sky-500/20 px-1 text-[9px] font-semibold text-sky-200">
                            START
                          </span>
                        )}
                        {s.is_end && (
                          <span className="rounded bg-rose-500/20 px-1 text-[9px] font-semibold text-rose-200">
                            END
                          </span>
                        )}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-400">
                      on <span className="font-mono text-fuchsia-300">{s.trigger_type}</span>
                    </div>
                    <div className="text-sm font-medium text-white">{s.node}</div>
                    <div className="text-[11px] text-slate-400">
                      emits{" "}
                      <span className="font-mono text-emerald-300">
                        {s.emitted_types.length ? s.emitted_types.join(", ") : "—"}
                      </span>
                    </div>
                    <div className="mt-1 flex gap-3 text-[10px] text-slate-500">
                      <span>{s.latency_ms} ms</span>
                      <span>${s.cost_usd}</span>
                      {s.error && <span className="text-rose-400">error</span>}
                    </div>
                  </button>
                </li>
              );
            })}
          </ol>
        </aside>
      </div>
    </div>
  );
}
