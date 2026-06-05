"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface VentureSelectorProps {
  value: string;
  onChange: (id: string) => void;
}

export function VentureSelector({ value, onChange }: VentureSelectorProps) {
  const [ventures, setVentures] = useState<any[]>([]);

  useEffect(() => {
    api.ventures.list().then(setVentures).catch(() => {});
  }, []);

  return (
    <select value={value} onChange={(e) => onChange(e.target.value)} className="input-dark w-48">
      <option value="">Select venture...</option>
      {ventures.map((v) => (
        <option key={v.id} value={v.id}>{v.name}</option>
      ))}
    </select>
  );
}
