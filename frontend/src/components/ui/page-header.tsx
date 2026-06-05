"use client";

import { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}

export function PageHeader({ title, subtitle, actions }: PageHeaderProps) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h1 className="text-3xl font-bold gradient-text">{title}</h1>
        {subtitle && <p className="text-[var(--text-secondary)] mt-1">{subtitle}</p>}
      </div>
      {actions && <div className="flex gap-3 items-center">{actions}</div>}
    </div>
  );
}
