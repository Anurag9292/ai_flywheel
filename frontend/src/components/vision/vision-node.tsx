"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { motion } from "framer-motion";
import type { NodeCategory } from "./vision-data";

const categoryStyles: Record<NodeCategory, { bg: string; border: string; glow: string; accent: string }> = {
  founder_state: { bg: "from-amber-900/30 to-orange-900/20", border: "border-amber-500/50", glow: "shadow-[0_0_20px_rgba(245,158,11,0.3)]", accent: "text-amber-300" },
  lifecycle_stage: { bg: "from-violet-900/30 to-indigo-900/20", border: "border-violet-500/40", glow: "shadow-[0_0_15px_rgba(139,92,246,0.25)]", accent: "text-violet-300" },
  business_intelligence: { bg: "from-emerald-900/30 to-teal-900/20", border: "border-emerald-500/40", glow: "shadow-[0_0_15px_rgba(16,185,129,0.2)]", accent: "text-emerald-300" },
  technical_execution: { bg: "from-blue-900/30 to-cyan-900/20", border: "border-blue-500/40", glow: "shadow-[0_0_15px_rgba(59,130,246,0.2)]", accent: "text-blue-300" },
  execution_spine: { bg: "from-fuchsia-900/30 to-pink-900/20", border: "border-fuchsia-500/50", glow: "shadow-[0_0_20px_rgba(217,70,239,0.3)]", accent: "text-fuchsia-300" },
  system: { bg: "from-indigo-900/30 to-purple-900/20", border: "border-indigo-400/40", glow: "shadow-[0_0_12px_rgba(99,102,241,0.2)]", accent: "text-indigo-300" },
  architecture_layer: { bg: "from-slate-800/40 to-gray-900/30", border: "border-slate-500/30", glow: "", accent: "text-slate-300" },
  validation_checkpoint: { bg: "from-cyan-900/30 to-sky-900/20", border: "border-cyan-500/40", glow: "shadow-[0_0_12px_rgba(6,182,212,0.2)]", accent: "text-cyan-300" },
  decision_point: { bg: "from-red-900/30 to-rose-900/20", border: "border-red-500/50", glow: "shadow-[0_0_15px_rgba(239,68,68,0.25)]", accent: "text-red-300" },
  feedback_loop: { bg: "from-yellow-900/30 to-amber-900/20", border: "border-yellow-500/40", glow: "shadow-[0_0_15px_rgba(234,179,8,0.2)]", accent: "text-yellow-300" },
  interaction_channel: { bg: "from-teal-900/30 to-emerald-900/20", border: "border-teal-500/40", glow: "shadow-[0_0_12px_rgba(20,184,166,0.2)]", accent: "text-teal-300" },
  outcome: { bg: "from-purple-900/40 to-violet-900/30", border: "border-purple-400/60", glow: "shadow-[0_0_25px_rgba(168,85,247,0.4)]", accent: "text-purple-200" },
};

interface VisionNodeInternalData {
  title: string;
  type: NodeCategory;
  description: string;
  isActive?: boolean;
  isHighlighted?: boolean;
}

function VisionNode({ data }: NodeProps) {
  const nodeData = data as unknown as VisionNodeInternalData;
  const style = categoryStyles[nodeData.type] || categoryStyles.lifecycle_stage;
  const isActive = nodeData.isActive;
  const isHighlighted = nodeData.isHighlighted;

  return (
    <motion.div
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{
        scale: isActive ? 1.05 : 1,
        opacity: isHighlighted === false ? 0.3 : 1,
      }}
      transition={{ duration: 0.3 }}
      className={`relative px-4 py-3 rounded-xl border backdrop-blur-sm min-w-[160px] max-w-[200px]
        bg-gradient-to-br ${style.bg} ${style.border}
        ${isActive ? style.glow : ""}
        ${isActive ? "ring-1 ring-white/20" : ""}
      `}
    >
      <Handle type="target" position={Position.Left} className="!w-2 !h-2 !bg-white/40 !border-0" />

      {isActive && (
        <motion.div
          className="absolute inset-0 rounded-xl border border-white/20"
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
      )}

      <p className={`text-xs font-semibold ${style.accent} leading-tight`}>{nodeData.title}</p>
      <p className="text-[9px] text-gray-400 mt-1 leading-tight line-clamp-2">{nodeData.description}</p>

      <Handle type="source" position={Position.Right} className="!w-2 !h-2 !bg-white/40 !border-0" />
    </motion.div>
  );
}

export default memo(VisionNode);
