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
import { buildFlow } from "@/lib/topology-layout";
import {
  fetchTopology,
  fetchTraces,
  type Topology,
  type TraceChain,
} from "@/lib/topology-api";

const nodeTypes = { flow: FlowNode };

export default function TopologyPage() {
  const [topo, setTopo] = useState<Topology | null>(null);
  const [chains, setChains] = useState<TraceChain[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Trace-replay state: which chain is selected and how far we've stepped.
  const [selectedChain, setSelectedChain] = useState<string | null>(null);
  const [step, setStep] = useState(0);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [t, tr] = await Promise.all([fetchTopology(), fetchTraces()]);
      setTopo(t);
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

  const { nodes: baseNodes, edges } = useMemo<{ nodes: Node[]; edges: Edge[] }>(
    () => (topo ? buildFlow(topo) : { nodes: [], edges: [] }),
    [topo],
  );

  // For trace replay: the node that fired at the current step is highlighted.
  const activeChain = chains.find((c) => c.correlation_id === selectedChain);
  const activeNodeName =
    activeChain && step < activeChain.steps.length
      ? activeChain.steps[step].node
      : null;

  const nodes = useMemo<Node[]>(
    () =>
      baseNodes.map((n) =>
        n.id === `node:${activeNodeName}`
          ? { ...n, data: { ...n.data, active: true } }
          : { ...n, data: { ...n.data, active: false } },
      ),
    [baseNodes, activeNodeName],
  );

  return (
    <div className="flex h-screen w-screen flex-col bg-[#0a0a14] text-white">
      <header className="flex items-center justify-between border-b border-white/10 px-6 py-3">
        <div>
          <h1 className="text-lg font-semibold">Topology — live, code-derived</h1>
          <p className="text-xs text-slate-400">
            From <code className="text-fuchsia-300">runtime.describe()</code> +
            the <code className="text-fuchsia-300">trace.captured</code> stream.
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
        <div className="border-b border-rose-500/40 bg-rose-950/40 px-6 py-3 text-sm text-rose-200">
          Could not reach the dev API ({error}). Start it with{" "}
          <code>uv run uvicorn flywheel.devserver.app:app --port 8000</code>.
        </div>
      )}

      {topo && (topo.lint.orphan_emitted.length > 0 ||
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
            edges={edges}
            nodeTypes={nodeTypes}
            fitView
            proOptions={{ hideAttribution: true }}
          >
            <Background variant={BackgroundVariant.Dots} gap={24} color="#1e293b" />
            <Controls />
            <MiniMap pannable zoomable className="!bg-slate-900" />
          </ReactFlow>
        </div>

        {/* Trace replay panel (View 2). */}
        <aside className="w-80 shrink-0 overflow-y-auto border-l border-white/10 bg-[#0d0d1a] p-4">
          <h2 className="mb-2 text-sm font-semibold">Trace replay</h2>
          <p className="mb-3 text-xs text-slate-400">
            Pick a recorded run (grouped by correlation id) and step through what
            actually fired.
          </p>

          {chains.length === 0 && (
            <p className="text-xs text-slate-500">
              No traces yet. Run a demo (e.g.{" "}
              <code>uv run python demo_step2.py</code>) then Refresh.
            </p>
          )}

          <ul className="space-y-1">
            {chains.map((c) => (
              <li key={c.correlation_id}>
                <button
                  onClick={() => {
                    setSelectedChain(c.correlation_id);
                    setStep(0);
                  }}
                  className={`w-full rounded-lg border px-2 py-1.5 text-left text-xs ${
                    selectedChain === c.correlation_id
                      ? "border-amber-300/60 bg-amber-500/10"
                      : "border-white/10 hover:bg-white/5"
                  }`}
                >
                  <div className="font-mono text-[10px] text-slate-400">
                    {c.correlation_id.slice(0, 12)}…
                  </div>
                  <div className="text-slate-200">
                    {c.steps.length} step{c.steps.length === 1 ? "" : "s"} ·{" "}
                    {c.steps[0]?.trigger_type}
                  </div>
                </button>
              </li>
            ))}
          </ul>

          {activeChain && (
            <div className="mt-4 rounded-lg border border-white/10 p-3">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs text-slate-400">
                  Step {step + 1} / {activeChain.steps.length}
                </span>
                <div className="flex gap-1">
                  <button
                    onClick={() => setStep((s) => Math.max(0, s - 1))}
                    disabled={step === 0}
                    className="rounded border border-white/15 px-2 py-0.5 text-xs disabled:opacity-40"
                  >
                    ‹
                  </button>
                  <button
                    onClick={() =>
                      setStep((s) => Math.min(activeChain.steps.length - 1, s + 1))
                    }
                    disabled={step >= activeChain.steps.length - 1}
                    className="rounded border border-white/15 px-2 py-0.5 text-xs disabled:opacity-40"
                  >
                    ›
                  </button>
                </div>
              </div>
              {(() => {
                const s = activeChain.steps[step];
                return (
                  <div className="space-y-1 text-xs">
                    <Row label="node" value={s.node} />
                    <Row label="reacted to" value={s.trigger_type} />
                    <Row label="emitted" value={s.emitted_types?.join(", ") || "—"} />
                    <Row label="latency" value={`${s.latency_ms} ms`} />
                    <Row label="cost" value={`$${s.cost_usd}`} />
                    {s.error && <Row label="error" value={s.error} />}
                  </div>
                );
              })()}
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-2">
      <span className="text-slate-500">{label}</span>
      <span className="text-right font-mono text-slate-200">{value}</span>
    </div>
  );
}
