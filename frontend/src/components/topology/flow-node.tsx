"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { FlowKind, FunctionTag } from "@/lib/topology-layout";

const KIND_STYLE: Record<FlowKind, { ring: string; bg: string; tag: string; tagText: string }> = {
  event: {
    ring: "border-fuchsia-400/60",
    bg: "from-fuchsia-950/70 to-pink-950/50",
    tag: "bg-fuchsia-500/20 text-fuchsia-200",
    tagText: "event",
  },
  node_dumb: {
    ring: "border-blue-400/60",
    bg: "from-blue-900/50 to-cyan-900/30",
    tag: "bg-blue-500/20 text-blue-200",
    tagText: "node · dumb",
  },
  node_agentic: {
    ring: "border-emerald-400/60",
    bg: "from-emerald-900/50 to-teal-900/30",
    tag: "bg-emerald-500/20 text-emerald-200",
    tagText: "node · agentic",
  },
  library: {
    ring: "border-slate-400/50",
    bg: "from-slate-800/60 to-slate-900/40",
    tag: "bg-slate-500/20 text-slate-200",
    tagText: "library",
  },
  substrate: {
    ring: "border-rose-400/60",
    bg: "from-rose-950/60 to-rose-900/30",
    tag: "bg-rose-500/20 text-rose-200",
    tagText: "substrate",
  },
};

export interface FlowNodeProps {
  label: string;
  kind: FlowKind;
  active?: boolean;
  functions?: FunctionTag[];
  dimmed?: boolean;
}

function FlowNodeComponent({ data }: NodeProps) {
  const d = data as unknown as FlowNodeProps;
  const s = KIND_STYLE[d.kind];
  const fns = d.functions ?? [];
  // The primary function colors a left accent bar; all functions show as chips.
  const accent = fns[0]?.color;
  return (
    <div
      className={`relative overflow-hidden rounded-xl border bg-gradient-to-br px-4 py-3 backdrop-blur-sm transition-all ${s.ring} ${s.bg} ${
        d.active ? "scale-110 ring-2 ring-amber-300 shadow-[0_0_30px_rgba(251,191,36,0.6)]" : ""
      } ${d.dimmed ? "opacity-25" : ""}`}
      style={{ minWidth: 150 }}
    >
      {accent && (
        <span
          className="absolute left-0 top-0 h-full w-1.5"
          style={{ backgroundColor: accent }}
        />
      )}
      <Handle type="target" position={Position.Top} className="!bg-slate-400" />
      <div className={`mb-1 inline-block rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide ${s.tag}`}>
        {s.tagText}
      </div>
      <div className="font-mono text-sm text-white">{d.label}</div>
      {fns.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1">
          {fns.map((f) => (
            <span
              key={f.name}
              className="rounded px-1 py-0.5 text-[8px] font-semibold uppercase tracking-wide text-white/90"
              style={{ backgroundColor: `${f.color}33`, border: `1px solid ${f.color}` }}
            >
              {f.name}
            </span>
          ))}
        </div>
      )}
      <Handle type="source" position={Position.Bottom} className="!bg-slate-400" />
    </div>
  );
}

export default memo(FlowNodeComponent);
