"use client";

interface StatCardProps {
  label: string;
  value: string | number;
  icon?: string; // SVG path
  color?: string; // gradient classes e.g. "from-violet-500 to-purple-600"
}

export function StatCard({ label, value, icon, color = "from-violet-500 to-purple-600" }: StatCardProps) {
  return (
    <div className="glass-card p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider">{label}</p>
          <p className="mt-2 text-3xl font-bold text-[var(--text-primary)]">{value}</p>
        </div>
        {icon && (
          <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${color} flex items-center justify-center shadow-lg`}>
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d={icon} />
            </svg>
          </div>
        )}
      </div>
    </div>
  );
}
