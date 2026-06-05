"use client";

import { ButtonHTMLAttributes } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "ghost" | "danger";
  size?: "sm" | "md";
}

export function Button({ variant = "primary", size = "md", className = "", children, ...props }: ButtonProps) {
  const variants = {
    primary: "btn-glow",
    ghost: "btn-ghost",
    danger: "btn-glow bg-gradient-to-r from-red-600 to-red-700",
  };
  const sizes = {
    sm: "!px-3 !py-1.5 !text-xs",
    md: "",
  };

  return (
    <button className={`${variants[variant]} ${sizes[size]} ${className}`} {...props}>
      {children}
    </button>
  );
}
