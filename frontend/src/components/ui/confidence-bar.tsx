"use client";

interface ConfidenceBarProps {
  value: number; // 0-1
  height?: "sm" | "md" | "lg";
  showLabel?: boolean;
  label?: string;
}

function getConfClass(c: number) {
  if (c >= 0.7) return "confidence-high";
  if (c >= 0.4) return "confidence-mid";
  return "confidence-low";
}

export function ConfidenceBar({ value, height = "md", showLabel = false, label }: ConfidenceBarProps) {
  const heights = { sm: "4px", md: "6px", lg: "8px" };

  return (
    <div>
      {showLabel && (
        <div className="flex justify-between text-xs text-[var(--text-muted)] mb-1.5">
          <span>{label || "Confidence"}</span>
          <span>{(value * 100).toFixed(0)}%</span>
        </div>
      )}
      <div className="confidence-bar" style={{ height: heights[height] }}>
        <div
          className={`confidence-bar-fill ${getConfClass(value)}`}
          style={{ width: `${value * 100}%` }}
        />
      </div>
    </div>
  );
}
