"use client";

import { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  active?: boolean;
  onClick?: () => void;
  padding?: "sm" | "md" | "lg";
}

export function Card({ children, className = "", active, onClick, padding = "md" }: CardProps) {
  const paddings = { sm: "p-3", md: "p-5", lg: "p-6" };
  const base = active ? "glass-card glass-card-active" : "glass-card";
  const clickable = onClick ? "cursor-pointer" : "";

  return (
    <div className={`${base} ${paddings[padding]} ${clickable} ${className}`} onClick={onClick}>
      {children}
    </div>
  );
}
