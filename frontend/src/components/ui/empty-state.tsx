"use client";

interface EmptyStateProps {
  message: string;
  hint?: string;
}

export function EmptyState({ message, hint }: EmptyStateProps) {
  return (
    <div className="glass-card p-8 text-center">
      <p className="text-[var(--text-muted)]">{message}</p>
      {hint && <p className="text-xs text-[var(--text-muted)] mt-1 opacity-70">{hint}</p>}
    </div>
  );
}
