"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { motion } from "framer-motion";
import type { NodeCategory } from "./vision-data";

// ─── Category Style Map ──────────────────────────────────────────────────────

interface CategoryStyle {
  bg: string;
  border: string;
  glow: string;
  accent: string;
  size: "lg" | "md" | "sm" | "xs";
}

const categoryStyles: Record<NodeCategory, CategoryStyle> = {
  founder_state: {
    bg: "from-amber-900/50 to-yellow-900/40",
    border: "border-amber-400/70",
    glow: "shadow-[0_0_40px_rgba(251,191,36,0.5),0_0_80px_rgba(245,158,11,0.2)]",
    accent: "text-amber-100",
    size: "lg",
  },
  lifecycle_stage: {
    bg: "from-violet-900/50 to-indigo-900/40",
    border: "border-violet-400/60",
    glow: "shadow-[0_0_35px_rgba(139,92,246,0.5),0_0_70px_rgba(99,102,241,0.2)]",
    accent: "text-violet-100",
    size: "lg",
  },
  business_intelligence: {
    bg: "from-emerald-900/40 to-teal-900/30",
    border: "border-emerald-400/50",
    glow: "shadow-[0_0_20px_rgba(16,185,129,0.4)]",
    accent: "text-emerald-200",
    size: "md",
  },
  technical_execution: {
    bg: "from-blue-900/40 to-cyan-900/30",
    border: "border-blue-400/50",
    glow: "shadow-[0_0_20px_rgba(59,130,246,0.4)]",
    accent: "text-blue-200",
    size: "md",
  },
  execution_spine: {
    bg: "from-fuchsia-900/35 to-pink-900/25",
    border: "border-fuchsia-400/45",
    glow: "shadow-[0_0_18px_rgba(217,70,239,0.35)]",
    accent: "text-fuchsia-200",
    size: "sm",
  },
  system: {
    bg: "from-indigo-950/40 to-slate-900/30",
    border: "border-indigo-400/30",
    glow: "shadow-[0_0_10px_rgba(99,102,241,0.2)]",
    accent: "text-indigo-300",
    size: "xs",
  },
  architecture_layer: {
    bg: "from-purple-900/30 to-indigo-900/20",
    border: "border-purple-400/35",
    glow: "shadow-[0_0_12px_rgba(147,51,234,0.25)]",
    accent: "text-purple-200",
    size: "sm",
  },
  validation_checkpoint: {
    bg: "from-cyan-900/30 to-sky-900/20",
    border: "border-cyan-400/40",
    glow: "shadow-[0_0_14px_rgba(6,182,212,0.3)]",
    accent: "text-cyan-200",
    size: "sm",
  },
  decision_point: {
    bg: "from-amber-900/40 to-yellow-900/30",
    border: "border-amber-400/55",
    glow: "shadow-[0_0_22px_rgba(245,158,11,0.4)]",
    accent: "text-amber-200",
    size: "sm",
  },
  feedback_loop: {
    bg: "from-yellow-900/35 to-amber-900/25",
    border: "border-yellow-400/45",
    glow: "shadow-[0_0_20px_rgba(234,179,8,0.35)]",
    accent: "text-yellow-200",
    size: "md",
  },
  interaction_channel: {
    bg: "from-teal-900/30 to-emerald-900/20",
    border: "border-teal-400/35",
    glow: "shadow-[0_0_12px_rgba(20,184,166,0.25)]",
    accent: "text-teal-200",
    size: "sm",
  },
  outcome: {
    bg: "from-amber-900/50 to-yellow-900/40",
    border: "border-amber-300/70",
    glow: "shadow-[0_0_45px_rgba(251,191,36,0.5),0_0_90px_rgba(245,158,11,0.25)]",
    accent: "text-amber-50",
    size: "lg",
  },
  kill_signal: {
    bg: "from-red-950/60 to-rose-950/50",
    border: "border-red-500/80",
    glow: "shadow-[0_0_35px_rgba(239,68,68,0.6)]",
    accent: "text-red-100",
    size: "md",
  },
  flywheel: {
    bg: "from-amber-900/40 to-yellow-900/30",
    border: "border-amber-400/50",
    glow: "shadow-[0_0_22px_rgba(234,179,8,0.4)]",
    accent: "text-amber-200",
    size: "sm",
  },
};

// ─── Size Classes ────────────────────────────────────────────────────────────

const sizeMap = {
  lg: "min-w-[190px] max-w-[240px] px-5 py-4",
  md: "min-w-[150px] max-w-[190px] px-4 py-3",
  sm: "min-w-[110px] max-w-[150px] px-3 py-2.5",
  xs: "min-w-[100px] max-w-[140px] px-3 py-2",
};

const fontSizeMap = {
  lg: "text-sm",
  md: "text-xs",
  sm: "text-[11px]",
  xs: "text-[10px]",
};

// ─── Handle Position Logic ───────────────────────────────────────────────────

function getHandles(type: NodeCategory, group?: string) {
  // Spine flows horizontally
  if (type === "execution_spine") {
    return { source: Position.Right, target: Position.Left };
  }
  // Validation ladder flows vertically
  if (type === "validation_checkpoint") {
    return { source: Position.Bottom, target: Position.Top };
  }
  // Flywheel nodes: circular connections
  if (type === "flywheel") {
    return { source: Position.Right, target: Position.Left };
  }
  // Business intel connects right toward lifecycle
  if (type === "business_intelligence") {
    return { source: Position.Right, target: Position.Top };
  }
  // Technical connects left toward lifecycle
  if (type === "technical_execution") {
    return { source: Position.Left, target: Position.Top };
  }
  // Channels connect downward
  if (type === "interaction_channel") {
    return { source: Position.Bottom, target: Position.Top };
  }
  // Systems connect upward
  if (type === "system" || type === "architecture_layer") {
    return { source: Position.Top, target: Position.Bottom };
  }
  // Default: lifecycle horizontal
  return { source: Position.Right, target: Position.Left };
}

// ─── Node Internal Data Interface ────────────────────────────────────────────

interface VisionNodeInternalData {
  id?: string;
  title: string;
  type: NodeCategory;
  description: string;
  group?: string;
  isActive?: boolean;
  isDimmed?: boolean;
}

// ─── The Node Component ──────────────────────────────────────────────────────

function VisionNodeComponent({ data }: NodeProps) {
  const d = data as unknown as VisionNodeInternalData;
  const style = categoryStyles[d.type] || categoryStyles.lifecycle_stage;
  const handles = getHandles(d.type, d.group);
  const size = sizeMap[style.size];
  const fontSize = fontSizeMap[style.size];

  const isActive = d.isActive;
  const isDimmed = d.isDimmed;
  const isKill = d.type === "kill_signal";
  const isOutcome = d.type === "outcome";
  const isFounder = d.type === "founder_state";
  const isDecision = d.type === "decision_point";
  const isLifecycle = d.type === "lifecycle_stage";
  const isProminent = d.id === "sys_product_intel";

  return (
    <motion.div
      initial={{ scale: 0.7, opacity: 0 }}
      animate={{
        scale: isActive ? 1.1 : 1,
        opacity: isDimmed ? 0.2 : 1,
      }}
      transition={{ duration: 0.35, ease: "easeOut" }}
      className={`
        relative rounded-xl border backdrop-blur-md
        ${size}
        bg-gradient-to-br ${style.bg} ${style.border}
        ${isActive ? style.glow : ""}
        ${isActive ? "ring-2 ring-white/40 z-10" : ""}
        ${isFounder && !isActive ? "ring-1 ring-amber-400/30" : ""}
        ${isOutcome && !isActive ? "ring-1 ring-amber-300/25" : ""}
        ${isDecision ? "rotate-0" : ""}
        ${isProminent ? "ring-1 ring-emerald-400/40 !min-w-[140px]" : ""}
        transition-shadow duration-300
      `}
    >
      {/* Target Handle */}
      <Handle
        type="target"
        position={handles.target}
        className="!w-2 !h-2 !bg-white/20 !border-0 !rounded-full"
      />

      {/* Active pulse ring */}
      {isActive && (
        <motion.div
          className="absolute inset-0 rounded-xl border-2 border-white/30"
          animate={{ opacity: [0.2, 0.7, 0.2], scale: [1, 1.03, 1] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
        />
      )}

      {/* Kill signal red pulse */}
      {isKill && (
        <motion.div
          className="absolute inset-0 rounded-xl border-2 border-red-400/70"
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{ duration: 0.8, repeat: Infinity, ease: "easeInOut" }}
        />
      )}

      {/* Founder / Outcome golden shimmer */}
      {(isFounder || isOutcome) && (
        <motion.div
          className="absolute inset-0 rounded-xl overflow-hidden"
          style={{
            background:
              "linear-gradient(135deg, rgba(251,191,36,0.12) 0%, transparent 40%, rgba(251,191,36,0.08) 100%)",
          }}
          animate={{ opacity: [0.4, 0.9, 0.4] }}
          transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
        />
      )}

      {/* Title */}
      <p
        className={`font-bold leading-tight ${style.accent} ${fontSize} ${
          isLifecycle || isFounder || isOutcome ? "tracking-tight" : ""
        }`}
      >
        {d.title}
      </p>

      {/* Description — shown on lifecycle/founder/outcome nodes */}
      {(isLifecycle || isFounder || isOutcome) && (
        <p className="text-[9px] text-gray-400/80 mt-1 leading-tight line-clamp-2">
          {d.description}
        </p>
      )}

      {/* Source Handle */}
      <Handle
        type="source"
        position={handles.source}
        className="!w-2 !h-2 !bg-white/20 !border-0 !rounded-full"
      />
    </motion.div>
  );
}

export default memo(VisionNodeComponent);
