"use client";

import type { VentureFunction } from "@/lib/topology-api";

/**
 * Legend + filter for the venture's functions (departments). Each row shows a
 * color swatch, the function name, and its node/event counts. Clicking a row
 * focuses that function (dims everything else on the graph); clicking the active
 * row clears the focus.
 */
export default function FunctionLegend({
  functions,
  colors,
  active,
  onSelect,
}: {
  functions: VentureFunction[];
  colors: Record<string, string>;
  active: string | null;
  onSelect: (name: string | null) => void;
}) {
  if (functions.length === 0) return null;

  return (
    <div className="border-b border-white/10 p-3">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-semibold">Functions</h2>
        {active && (
          <button
            onClick={() => onSelect(null)}
            className="rounded-md border border-white/15 px-2 py-0.5 text-[11px] hover:bg-white/10"
          >
            Clear focus
          </button>
        )}
      </div>
      <div className="space-y-1">
        {functions.map((f) => {
          const isActive = active === f.name;
          return (
            <button
              key={f.name}
              onClick={() => onSelect(isActive ? null : f.name)}
              title={f.description}
              className={`flex w-full items-center gap-2 rounded-md border px-2 py-1.5 text-left text-xs transition-colors ${
                isActive
                  ? "border-white/40 bg-white/10"
                  : "border-white/10 hover:bg-white/5"
              }`}
            >
              <span
                className="h-3 w-3 shrink-0 rounded-sm"
                style={{ backgroundColor: colors[f.name] }}
              />
              <span className="flex-1 truncate font-medium text-slate-100">
                {f.name}
              </span>
              <span className="font-mono text-[10px] text-slate-400">
                {f.nodes.length}n · {f.events_in.length}→{f.events_out.length}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
