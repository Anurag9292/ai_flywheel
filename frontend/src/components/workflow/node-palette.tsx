"use client";

const nodeTypes = [
  { type: "agent", label: "Agent", icon: "M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z", color: "violet" },
  { type: "tool", label: "Tool", icon: "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35", color: "cyan" },
  { type: "human_review", label: "Human Review", icon: "M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z", color: "amber" },
  { type: "condition", label: "Condition", icon: "M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z", color: "pink" },
];

const colorMap: Record<string, string> = {
  violet: "border-violet-500/30 hover:border-violet-500/60 hover:shadow-[0_0_12px_rgba(139,92,246,0.2)]",
  cyan: "border-cyan-500/30 hover:border-cyan-500/60 hover:shadow-[0_0_12px_rgba(6,182,212,0.2)]",
  amber: "border-amber-500/30 hover:border-amber-500/60 hover:shadow-[0_0_12px_rgba(245,158,11,0.2)]",
  pink: "border-pink-500/30 hover:border-pink-500/60 hover:shadow-[0_0_12px_rgba(236,72,153,0.2)]",
};

interface NodePaletteProps {
  onAddNode: (type: string, label: string) => void;
}

export function NodePalette({ onAddNode }: NodePaletteProps) {
  return (
    <div className="space-y-2">
      <p className="text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider px-1">Drag to Add</p>
      {nodeTypes.map((node) => (
        <button
          key={node.type}
          onClick={() => onAddNode(node.type, node.label)}
          className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg border bg-[rgba(0,0,0,0.3)] transition-all cursor-grab active:cursor-grabbing ${colorMap[node.color]}`}
        >
          <svg className="w-4 h-4 text-[var(--text-secondary)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d={node.icon} />
          </svg>
          <span className="text-sm text-[var(--text-secondary)]">{node.label}</span>
        </button>
      ))}
    </div>
  );
}
