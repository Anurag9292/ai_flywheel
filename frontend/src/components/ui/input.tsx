"use client";

import { InputHTMLAttributes, TextareaHTMLAttributes, SelectHTMLAttributes, ReactNode } from "react";

interface LabeledProps {
  label?: string;
  className?: string;
}

export function Input({ label, className = "", ...props }: LabeledProps & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div className={className}>
      {label && <label className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider block mb-1.5">{label}</label>}
      <input className="input-dark" {...props} />
    </div>
  );
}

export function Textarea({ label, className = "", ...props }: LabeledProps & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <div className={className}>
      {label && <label className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider block mb-1.5">{label}</label>}
      <textarea className="input-dark" {...props} />
    </div>
  );
}

interface SelectProps extends LabeledProps {
  children: ReactNode;
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLSelectElement>) => void;
}

export function Select({ label, className = "", children, ...props }: SelectProps & SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <div className={className}>
      {label && <label className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider block mb-1.5">{label}</label>}
      <select className="input-dark" {...props}>{children}</select>
    </div>
  );
}
