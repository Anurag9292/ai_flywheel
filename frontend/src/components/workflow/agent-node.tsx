"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";

export type AgentNodeData = {
  label: string;
  type: "agent" | "tool" | "human_review" | "condition" | "start" | "end";
  model?: string;
  description?: string;
};

const typeStyles: Record<string, { bg: string; border: string; icon: string }> = {
  agent: {
    bg: "from-violet-600/20 to-indigo-600/20",
    border: "border-violet-500/40",
    icon: "M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z",
  },
  tool: {
    bg: "from-cyan-600/20 to-teal-600/20",
    border: "border-cyan-500/40",
    icon: "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z",
  },
  human_review: {
    bg: "from-amber-600/20 to-orange-600/20",
    border: "border-amber-500/40",
    icon: "M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z",
  },
  condition: {
    bg: "from-pink-600/20 to-rose-600/20",
    border: "border-pink-500/40",
    icon: "M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  },
  start: {
    bg: "from-emerald-600/20 to-green-600/20",
    border: "border-emerald-500/40",
    icon: "M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z",
  },
  end: {
    bg: "from-red-600/20 to-rose-600/20",
    border: "border-red-500/40",
    icon: "M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  },
};

function AgentNode({ data }: NodeProps) {
  const nodeData = data as unknown as AgentNodeData;
  const style = typeStyles[nodeData.type] || typeStyles.agent;

  return (
    <div className={`relative px-4 py-3 rounded-xl border ${style.border} bg-gradient-to-br ${style.bg} backdrop-blur-sm min-w-[180px] shadow-lg`}>
      {/* Input handle */}
      {nodeData.type !== "start" && (
        <Handle type="target" position={Position.Top} className="!w-3 !h-3 !bg-violet-500 !border-2 !border-violet-300/50" />
      )}

      <div className="flex items-center gap-2">
        <svg className="w-4 h-4 text-[var(--text-secondary)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d={style.icon} />
        </svg>
        <div>
          <p className="text-sm font-medium text-[var(--text-primary)]">{nodeData.label}</p>
          {nodeData.model && (
            <p className="text-[10px] text-[var(--text-muted)]">{nodeData.model}</p>
          )}
        </div>
      </div>

      {nodeData.description && (
        <p className="mt-1.5 text-[10px] text-[var(--text-muted)] leading-tight">{nodeData.description}</p>
      )}

      {/* Output handle */}
      {nodeData.type !== "end" && (
        <Handle type="source" position={Position.Bottom} className="!w-3 !h-3 !bg-indigo-500 !border-2 !border-indigo-300/50" />
      )}
    </div>
  );
}

export default memo(AgentNode);
