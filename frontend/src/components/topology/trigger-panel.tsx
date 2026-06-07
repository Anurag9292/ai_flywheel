"use client";

import { useState } from "react";
import { publishEvent, resetTraces } from "@/lib/topology-api";

// Curated one-click scenarios for the events that currently produce runs.
const PRESETS: {
  label: string;
  type: string;
  payload: Record<string, unknown>;
  hint: string;
}[] = [
  {
    label: "Run desk research",
    type: "research.requested",
    hint: "market-scanner → thesis-tracker",
    payload: {
      thesis: "B2B founders will pay $499/mo for AI LinkedIn ghostwriting",
      keywords: ["linkedin ghostwriter", "b2b founder content"],
      competitor_query: "AI LinkedIn ghostwriting competitors",
    },
  },
  {
    label: "Submit evidence (supports)",
    type: "evidence.collected",
    hint: "thesis-tracker",
    payload: { assumption: "willing_to_pay_499", supports: true },
  },
  {
    label: "Signal verdict: kill",
    type: "signal.verdict",
    hint: "thesis-tracker (contradicts)",
    payload: { verdict: "kill" },
  },
];

export default function TriggerPanel({
  onTriggered,
}: {
  onTriggered: (correlationId: string) => void;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  // Raw form state.
  const [rawType, setRawType] = useState("research.requested");
  const [rawPayload, setRawPayload] = useState("{}");
  const [showRaw, setShowRaw] = useState(false);

  async function fire(type: string, payload: Record<string, unknown>) {
    setBusy(type);
    setErr(null);
    try {
      const res = await publishEvent({ type, payload });
      onTriggered(res.correlation_id);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  async function fireRaw() {
    let payload: Record<string, unknown>;
    try {
      payload = JSON.parse(rawPayload || "{}");
    } catch {
      setErr("Payload must be valid JSON.");
      return;
    }
    await fire(rawType, payload);
  }

  return (
    <div className="border-b border-white/10 p-3">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-semibold">Trigger a run</h2>
        <button
          onClick={async () => {
            await resetTraces();
            onTriggered("");
          }}
          className="rounded-md border border-white/15 px-2 py-0.5 text-[11px] hover:bg-white/10"
        >
          ⟲ Clear all
        </button>
      </div>

      <div className="space-y-1.5">
        {PRESETS.map((p) => (
          <button
            key={p.label}
            onClick={() => fire(p.type, p.payload)}
            disabled={busy !== null}
            className="block w-full rounded-md border border-emerald-400/30 bg-emerald-500/10 px-2.5 py-1.5 text-left text-xs hover:bg-emerald-500/20 disabled:opacity-50"
          >
            <span className="font-medium text-emerald-100">
              {busy === p.type ? "Running…" : p.label}
            </span>
            <span className="block font-mono text-[10px] text-slate-400">
              {p.type} · {p.hint}
            </span>
          </button>
        ))}
      </div>

      <button
        onClick={() => setShowRaw((s) => !s)}
        className="mt-2 text-[11px] text-slate-400 hover:text-slate-200"
      >
        {showRaw ? "▾ Hide custom event" : "▸ Custom event…"}
      </button>

      {showRaw && (
        <div className="mt-2 space-y-1.5">
          <input
            value={rawType}
            onChange={(e) => setRawType(e.target.value)}
            placeholder="event.type"
            className="w-full rounded-md border border-white/15 bg-black/30 px-2 py-1 font-mono text-xs"
          />
          <textarea
            value={rawPayload}
            onChange={(e) => setRawPayload(e.target.value)}
            rows={3}
            placeholder='{"key": "value"}'
            className="w-full rounded-md border border-white/15 bg-black/30 px-2 py-1 font-mono text-[11px]"
          />
          <button
            onClick={fireRaw}
            disabled={busy !== null}
            className="w-full rounded-md border border-white/15 px-2 py-1 text-xs hover:bg-white/10 disabled:opacity-50"
          >
            Publish event
          </button>
        </div>
      )}

      {err && <p className="mt-2 text-[11px] text-rose-400">{err}</p>}
    </div>
  );
}
