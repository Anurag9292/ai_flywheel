"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { motion } from "framer-motion";
import type { V2Category } from "./vision-v2-data";

// ─── Per-category visual style ──────────────────────────────────────────────

interface CatStyle {
  bg: string;
  border: string;
  glow: string;
  accent: string;
  size: "xl" | "lg" | "md" | "sm" | "xs";
  pill?: boolean;
  label?: boolean;
}

const styles: Record<V2Category, CatStyle> = {
  layer_label: {
    bg: "from-transparent to-transparent",
    border: "border-transparent",
    glow: "",
    accent: "text-gray-500",
    size: "xs",
    label: true,
  },
  layer3_meta: {
    bg: "from-amber-900/55 to-yellow-900/40",
    border: "border-amber-300/70",
    glow: "shadow-[0_0_45px_rgba(251,191,36,0.45),0_0_90px_rgba(245,158,11,0.18)]",
    accent: "text-amber-100",
    size: "xl",
  },
  event_bus: {
    bg: "from-fuchsia-900/55 to-pink-900/35",
    border: "border-fuchsia-400/70",
    glow: "shadow-[0_0_36px_rgba(217,70,239,0.45)]",
    accent: "text-fuchsia-100",
    size: "lg",
  },
  event: {
    bg: "from-fuchsia-950/60 to-pink-950/40",
    border: "border-fuchsia-400/40",
    glow: "shadow-[0_0_10px_rgba(217,70,239,0.25)]",
    accent: "text-fuchsia-200",
    size: "xs",
    pill: true,
  },
  l2_venture_header: {
    bg: "from-purple-900/40 to-indigo-900/30",
    border: "border-purple-400/50",
    glow: "shadow-[0_0_18px_rgba(147,51,234,0.3)]",
    accent: "text-purple-100",
    size: "md",
  },
  l2_stage: {
    bg: "from-violet-900/45 to-indigo-900/30",
    border: "border-violet-400/55",
    glow: "shadow-[0_0_22px_rgba(139,92,246,0.4)]",
    accent: "text-violet-100",
    size: "md",
  },
  l1_node_dumb: {
    bg: "from-blue-900/40 to-cyan-900/25",
    border: "border-blue-400/50",
    glow: "shadow-[0_0_18px_rgba(59,130,246,0.35)]",
    accent: "text-blue-100",
    size: "sm",
  },
  l1_node_agentic: {
    bg: "from-emerald-900/40 to-teal-900/25",
    border: "border-emerald-400/55",
    glow: "shadow-[0_0_20px_rgba(16,185,129,0.4)]",
    accent: "text-emerald-100",
    size: "sm",
  },
  l1_lib: {
    bg: "from-slate-900/55 to-slate-950/40",
    border: "border-slate-500/40",
    glow: "shadow-[0_0_8px_rgba(100,116,139,0.25)]",
    accent: "text-slate-200",
    size: "xs",
  },
  l1_substrate: {
    bg: "from-rose-900/40 to-orange-900/25",
    border: "border-rose-400/55",
    glow: "shadow-[0_0_22px_rgba(244,63,94,0.35)]",
    accent: "text-rose-100",
    size: "md",
  },
};

const sizeMap = {
  xl: "min-w-[260px] max-w-[340px] px-6 py-4",
  lg: "min-w-[200px] max-w-[260px] px-5 py-3",
  md: "min-w-[160px] max-w-[210px] px-4 py-2.5",
  sm: "min-w-[140px] max-w-[180px] px-3 py-2.5",
  xs: "min-w-[120px] max-w-[170px] px-3 py-1.5",
};

const fontSizeMap = {
  xl: "text-base",
  lg: "text-sm",
  md: "text-xs",
  sm: "text-[11px]",
  xs: "text-[10px]",
};

// ─── Handle layout per type ─────────────────────────────────────────────────

function getHandles(type: V2Category) {
  // Most things connect vertically (top/bottom) since the layout is layered
  switch (type) {
    case "layer3_meta":
      return { source: Position.Bottom, target: Position.Top };
    case "event_bus":
    case "event":
      return { source: Position.Bottom, target: Position.Top };
    case "l2_stage":
    case "l2_venture_header":
      // Stage flow is horizontal, but venture-wires go down to L1 — use bottom for source by default
      return { source: Position.Bottom, target: Position.Top };
    case "l1_node_dumb":
    case "l1_node_agentic":
      return { source: Position.Top, target: Position.Top };
    case "l1_lib":
      return { source: Position.Top, target: Position.Top };
    case "l1_substrate":
      return { source: Position.Top, target: Position.Top };
    default:
      return { source: Position.Right, target: Position.Left };
  }
}

// ─── Internal data shape ────────────────────────────────────────────────────

interface V2NodeInternal {
  id?: string;
  title: string;
  type: V2Category;
  description: string;
  group?: string;
  isActive?: boolean;
  isDimmed?: boolean;
}

// ─── Component ──────────────────────────────────────────────────────────────

function V2NodeComponent({ data }: NodeProps) {
  const d = data as unknown as V2NodeInternal;
  const s = styles[d.type] || styles.l1_node_dumb;
  const isActive = !!d.isActive;
  const isDimmed = !!d.isDimmed;
  const handles = getHandles(d.type);

  // Layer label rendering (decorative, no border, no handle activity)
  if (s.label) {
    return (
      <div
        className="pointer-events-none select-none"
        style={{
          minWidth: 240,
          opacity: isDimmed ? 0.25 : 0.85,
        }}
      >
        <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-gray-400/80">
          {d.title}
        </p>
        <div className="mt-1 h-px bg-gradient-to-r from-gray-500/30 via-gray-500/10 to-transparent" />
      </div>
    );
  }

  const size = sizeMap[s.size];
  const fontSize = fontSizeMap[s.size];

  // Pill (used for events along the bus)
  if (s.pill) {
    return (
      <motion.div
        initial={{ scale: 0.7, opacity: 0 }}
        animate={{
          scale: isActive ? 1.08 : 1,
          opacity: isDimmed ? 0.18 : 1,
        }}
        transition={{ duration: 0.3, ease: "easeOut" }}
        className={`
          relative rounded-full border backdrop-blur-md
          bg-gradient-to-br ${s.bg} ${s.border}
          ${isActive ? s.glow : ""}
          ${isActive ? "ring-2 ring-fuchsia-300/50 z-10" : ""}
          px-3 py-1
        `}
      >
        <Handle
          type="target"
          position={handles.target}
          className="!w-1.5 !h-1.5 !bg-fuchsia-300/40 !border-0"
        />
        <p className={`font-mono ${fontSize} ${s.accent} whitespace-nowrap`}>
          {d.title}
        </p>
        <Handle
          type="source"
          position={handles.source}
          className="!w-1.5 !h-1.5 !bg-fuchsia-300/40 !border-0"
        />
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ scale: 0.85, opacity: 0 }}
      animate={{
        scale: isActive ? 1.08 : 1,
        opacity: isDimmed ? 0.2 : 1,
      }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={`
        relative rounded-xl border backdrop-blur-md
        ${size}
        bg-gradient-to-br ${s.bg} ${s.border}
        ${isActive ? s.glow : ""}
        ${isActive ? "ring-2 ring-white/40 z-10" : ""}
      `}
    >
      <Handle
        type="target"
        position={handles.target}
        className="!w-2 !h-2 !bg-white/20 !border-0 !rounded-full"
      />

      {isActive && (
        <motion.div
          className="absolute inset-0 rounded-xl border-2 border-white/30"
          animate={{ opacity: [0.2, 0.7, 0.2], scale: [1, 1.03, 1] }}
          transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
        />
      )}

      <div className="flex items-baseline gap-2">
        <p
          className={`font-bold leading-tight ${fontSize} ${s.accent}`}
          style={{ fontFamily: d.type === "l1_lib" || d.type.startsWith("l1_node") ? "var(--font-mono, ui-monospace)" : undefined }}
        >
          {d.title}
        </p>
        {d.type === "l1_node_agentic" && (
          <span className="text-[8px] uppercase tracking-wider text-emerald-300/70 bg-emerald-500/15 px-1.5 py-0.5 rounded">
            agentic
          </span>
        )}
        {d.type === "l1_node_dumb" && (
          <span className="text-[8px] uppercase tracking-wider text-blue-300/70 bg-blue-500/15 px-1.5 py-0.5 rounded">
            dumb
          </span>
        )}
        {d.type === "l1_lib" && (
          <span className="text-[8px] uppercase tracking-wider text-slate-300/70 bg-slate-500/15 px-1.5 py-0.5 rounded">
            lib
          </span>
        )}
        {d.type === "l1_substrate" && (
          <span className="text-[8px] uppercase tracking-wider text-rose-300/80 bg-rose-500/15 px-1.5 py-0.5 rounded">
            substrate
          </span>
        )}
      </div>

      {(s.size === "xl" || s.size === "lg") && (
        <p className="text-[10px] text-gray-400/85 mt-1.5 leading-snug line-clamp-3">
          {d.description}
        </p>
      )}
      {s.size === "md" && d.type === "l2_stage" && (
        <p className="text-[9px] text-gray-400/75 mt-1 leading-tight line-clamp-2">
          {d.description}
        </p>
      )}

      <Handle
        type="source"
        position={handles.source}
        className="!w-2 !h-2 !bg-white/20 !border-0 !rounded-full"
      />
    </motion.div>
  );
}

export default memo(V2NodeComponent);
