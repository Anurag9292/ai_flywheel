"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { motion } from "framer-motion";
import type { NodeCategory } from "./vision-data";

const categoryStyles: Record<NodeCategory, { bg: string; border: string; glow: string; accent: string }> = {
  founder_state: {
    bg: "from-amber-900/40 to-orange-900/30",
    border: "border-amber-500/60",
    glow: "shadow-[0_0_30px_rgba(245,158,11,0.5)]",
    accent: "text-amber-200",
  },
  lifecycle_stage: {
    bg: "from-violet-900/40 to-indigo-900/30",
    border: "border-violet-500/50",
    glow: "shadow-[0_0_25px_rgba(139,92,246,0.4)]",
    accent: "text-violet-200",
  },
  business_intelligence: {
    bg: "from-emerald-900/30 to-teal-900/20",
    border: "border-emerald-500/40",
    glow: "shadow-[0_0_15px_rgba(16,185,129,0.3)]",
    accent: "text-emerald-300",
  },
  technical_execution: {
    bg: "from-blue-900/30 to-cyan-900/20",
    border: "border-blue-500/40",
    glow: "shadow-[0_0_15px_rgba(59,130,246,0.3)]",
    accent: "text-blue-300",
  },
  execution_spine: {
    bg: "from-fuchsia-900/30 to-pink-900/20",
    border: "border-fuchsia-500/40",
    glow: "shadow-[0_0_20px_rgba(217,70,239,0.3)]",
    accent: "text-fuchsia-300",
  },
  system: {
    bg: "from-indigo-900/20 to-purple-900/15",
    border: "border-indigo-400/30",
    glow: "shadow-[0_0_10px_rgba(99,102,241,0.2)]",
    accent: "text-indigo-300",
  },
  validation_checkpoint: {
    bg: "from-cyan-900/25 to-sky-900/15",
    border: "border-cyan-500/35",
    glow: "shadow-[0_0_12px_rgba(6,182,212,0.25)]",
    accent: "text-cyan-300",
  },
  decision_point: {
    bg: "from-red-900/30 to-rose-900/20",
    border: "border-red-500/50",
    glow: "shadow-[0_0_20px_rgba(239,68,68,0.35)]",
    accent: "text-red-300",
  },
  feedback_loop: {
    bg: "from-yellow-900/30 to-amber-900/20",
    border: "border-yellow-500/40",
    glow: "shadow-[0_0_20px_rgba(234,179,8,0.3)]",
    accent: "text-yellow-300",
  },
  interaction_channel: {
    bg: "from-teal-900/25 to-emerald-900/15",
    border: "border-teal-500/35",
    glow: "shadow-[0_0_12px_rgba(20,184,166,0.2)]",
    accent: "text-teal-300",
  },
  kill_signal: {
    bg: "from-red-950/50 to-rose-950/40",
    border: "border-red-500/70",
    glow: "shadow-[0_0_30px_rgba(239,68,68,0.5)]",
    accent: "text-red-200",
  },
  outcome: {
    bg: "from-amber-900/40 to-yellow-900/30",
    border: "border-amber-400/60",
    glow: "shadow-[0_0_35px_rgba(251,191,36,0.4)]",
    accent: "text-amber-100",
  },
};

// Determine handle positions based on node type/group
function getHandlePositions(type: NodeCategory, group?: string) {
  if (type === "execution_spine") {
    return { source: Position.Right, target: Position.Left };
  }
  if (group === "validation") {
    return { source: Position.Bottom, target: Position.Top };
  }
  if (type === "business_intelligence") {
    return { source: Position.Right, target: Position.Top };
  }
  if (type === "technical_execution") {
    return { source: Position.Left, target: Position.Top };
  }
  if (type === "feedback_loop" && group === "flywheel") {
    return { source: Position.Right, target: Position.Left };
  }
  // Default: lifecycle horizontal flow
  return { source: Position.Right, target: Position.Left };
}

interface VisionNodeInternalData {
  title: string;
  type: NodeCategory;
  description: string;
  group?: string;
  isActive?: boolean;
  isHighlighted?: boolean;
}

function VisionNode({ data }: NodeProps) {
  const nodeData = data as unknown as VisionNodeInternalData;
  const style = categoryStyles[nodeData.type] || categoryStyles.lifecycle_stage;
  const isActive = nodeData.isActive;
  const isHighlighted = nodeData.isHighlighted;
  const handles = getHandlePositions(nodeData.type, nodeData.group);

  const isLifecycle = nodeData.group === "lifecycle";
  const isKill = nodeData.type === "kill_signal";
  const isOutcome = nodeData.type === "outcome";
  const isSpine = nodeData.type === "execution_spine";

  // Lifecycle nodes are larger and more prominent
  const sizeClasses = isLifecycle
    ? "min-w-[180px] max-w-[220px] px-5 py-4"
    : isSpine
    ? "min-w-[100px] max-w-[130px] px-3 py-2"
    : "min-w-[140px] max-w-[180px] px-4 py-3";

  return (
    <motion.div
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{
        scale: isActive ? 1.08 : 1,
        opacity: isHighlighted === false ? 0.25 : 1,
      }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={`relative rounded-xl border backdrop-blur-sm ${sizeClasses}
        bg-gradient-to-br ${style.bg} ${style.border}
        ${isActive ? style.glow : ""}
        ${isActive ? "ring-2 ring-white/30" : ""}
        ${isOutcome && !isActive ? "ring-1 ring-amber-400/20" : ""}
      `}
    >
      <Handle
        type="target"
        position={handles.target}
        className="!w-2 !h-2 !bg-white/30 !border-0"
      />

      {/* Active pulse ring */}
      {isActive && (
        <motion.div
          className="absolute inset-0 rounded-xl border-2 border-white/30"
          animate={{ opacity: [0.3, 0.8, 0.3], scale: [1, 1.02, 1] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
        />
      )}

      {/* Kill signal red pulse */}
      {isKill && (
        <motion.div
          className="absolute inset-0 rounded-xl border-2 border-red-500/60"
          animate={{ opacity: [0.4, 1, 0.4] }}
          transition={{ duration: 1, repeat: Infinity, ease: "easeInOut" }}
        />
      )}

      {/* Outcome golden shimmer */}
      {isOutcome && (
        <motion.div
          className="absolute inset-0 rounded-xl"
          style={{
            background: "linear-gradient(135deg, rgba(251,191,36,0.1) 0%, rgba(251,191,36,0) 50%, rgba(251,191,36,0.08) 100%)",
          }}
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
        />
      )}

      <p className={`font-bold leading-tight ${style.accent} ${isLifecycle ? "text-sm" : isSpine ? "text-[10px]" : "text-xs"}`}>
        {nodeData.title}
      </p>

      {/* Show description only for lifecycle nodes (small) */}
      {isLifecycle && (
        <p className="text-[10px] text-gray-400 mt-1 leading-tight line-clamp-2 opacity-80">
          {nodeData.description}
        </p>
      )}

      <Handle
        type="source"
        position={handles.source}
        className="!w-2 !h-2 !bg-white/30 !border-0"
      />
    </motion.div>
  );
}

export default memo(VisionNode);
