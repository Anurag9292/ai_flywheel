"use client";

type BadgeVariant = "purple" | "green" | "red" | "yellow" | "blue" | "default";

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
}

const variantMap: Record<BadgeVariant, string> = {
  purple: "badge-purple",
  green: "badge-green",
  red: "badge-red",
  yellow: "badge-yellow",
  blue: "badge-blue",
  default: "badge-purple",
};

/** Auto-map common status/risk strings to badge colors */
export function statusVariant(status: string): BadgeVariant {
  switch (status) {
    case "validated": case "active": case "connected": case "healthy": case "approved": case "low":
      return "green";
    case "invalidated": case "killed": case "failed": case "rejected": case "critical": case "error":
      return "red";
    case "pending": case "draft": case "medium": case "warning":
      return "yellow";
    case "running": case "in_progress": case "high":
      return "blue";
    default:
      return "purple";
  }
}

export function Badge({ children, variant = "default" }: BadgeProps) {
  return <span className={`badge ${variantMap[variant]}`}>{children}</span>;
}
