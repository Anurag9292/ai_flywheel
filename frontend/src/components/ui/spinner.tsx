"use client";

interface SpinnerProps {
  text?: string;
}

export function Spinner({ text = "Loading..." }: SpinnerProps) {
  return (
    <div className="flex items-center gap-3 text-[var(--text-muted)]">
      <div className="w-4 h-4 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin" />
      {text}
    </div>
  );
}
