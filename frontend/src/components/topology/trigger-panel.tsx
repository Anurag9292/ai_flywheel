"use client";

import { useState } from "react";
import { publishEvent, resetTraces } from "@/lib/topology-api";

// Example payloads per known event type. Used both to pre-fill the custom-event
// form (so you see the expected shape, not a bare `{}`) and as the source for
// the one-click presets below. Each entry documents what reacts to the event.
const EVENT_CATALOG: Record<
  string,
  { payload: Record<string, unknown>; reacts: string }
> = {
  "research.requested": {
    reacts: "market-scanner → thesis-tracker → founder-notifier",
    payload: {
      thesis: "B2B founders will pay $499/mo for AI LinkedIn ghostwriting",
      keywords: ["linkedin ghostwriter", "b2b founder content"],
      competitor_query: "AI LinkedIn ghostwriting competitors",
    },
  },
  "transcript.captured": {
    reacts: "pain-extractor → thesis-tracker → founder-notifier",
    payload: {
      transcript:
        "I know I should post on LinkedIn but I have no time, and when I do post it gets no engagement.",
      speaker: "Founder A",
    },
  },
  "campaign.requested": {
    reacts:
      "ad-campaign-runner → ad-analytics-collector → signal-analyzer → thesis-tracker / founder-notifier",
    payload: {
      platform: "linkedin",
      name: "ghostwriting waitlist",
      budget_usd: 200,
      landing_page: "/postlineai",
      rubric: "would pay $499/mo",
    },
  },
  "inbound.received": {
    reacts: "input-intake → post-drafter → human-review-queue (parks for approval)",
    payload: {
      customer_id: "c1",
      kind: "text",
      content: "Want a post about why we moved off Kubernetes.",
    },
  },
  "subscription.requested": {
    reacts: "subscription-manager (activates + charges)",
    payload: { customer_id: "c1", plan: "trial", amount_usd: 299 },
  },
  "survey.requested": {
    reacts: "customer-survey → signal-analyzer / thesis-tracker → founder-notifier",
    payload: { customer_id: "c1", nps: 9, leads: 2, rubric: "happy enough to renew?" },
  },
  "evidence.collected": {
    reacts: "thesis-tracker → founder-notifier",
    payload: { assumption: "willing_to_pay_499", supports: true },
  },
  "signal.verdict": {
    reacts: "thesis-tracker → founder-notifier",
    payload: { verdict: "kill" },
  },
  "market.landscape.summarized": {
    reacts: "thesis-tracker → founder-notifier",
    payload: {
      summary: "a clear gap exists at $499",
      competitors: [{ name: "Taplio", pricing: "$39/mo" }],
      top_keywords: ["linkedin ghostwriter"],
    },
  },
  "pain.extracted": {
    reacts: "thesis-tracker → founder-notifier",
    payload: {
      pains: [
        { pain: "no time to post", frequency: 8, intensity: 0.8 },
        { pain: "posts get no engagement", frequency: 5, intensity: 0.7 },
      ],
    },
  },
  "survey.responded": {
    reacts: "thesis-tracker → founder-notifier",
    payload: { nps: 9, comment: "saves me hours" },
  },
};

const KNOWN_EVENT_TYPES = Object.keys(EVENT_CATALOG);

function examplePayload(type: string): string {
  const entry = EVENT_CATALOG[type];
  return JSON.stringify(entry ? entry.payload : {}, null, 2);
}

// Curated one-click scenarios for the events that currently produce runs.
const PRESETS: { label: string; type: string; hint: string }[] = [
  { label: "Run desk research", type: "research.requested", hint: "market-scanner → thesis-tracker" },
  { label: "Capture a discovery call", type: "transcript.captured", hint: "pain-extractor → thesis-tracker" },
  { label: "Run the ad test", type: "campaign.requested", hint: "ads → analyze → decide loop" },
  { label: "Customer sends input", type: "inbound.received", hint: "drafts a post, parks for review" },
  { label: "New subscription", type: "subscription.requested", hint: "subscription-manager" },
  { label: "Send NPS survey", type: "survey.requested", hint: "survey → signal → thesis" },
  { label: "Submit evidence (supports)", type: "evidence.collected", hint: "thesis-tracker" },
  { label: "Signal verdict: kill", type: "signal.verdict", hint: "thesis-tracker (contradicts)" },
];

export default function TriggerPanel({
  onTriggered,
}: {
  onTriggered: (correlationId: string) => void;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  // Raw form state. Payload starts pre-filled with the example for the type.
  const [rawType, setRawType] = useState("research.requested");
  const [rawPayload, setRawPayload] = useState(examplePayload("research.requested"));
  const [showRaw, setShowRaw] = useState(false);

  // When the chosen type changes to a known event, pre-fill its example payload.
  function onTypeChange(type: string) {
    setRawType(type);
    if (EVENT_CATALOG[type]) {
      setRawPayload(examplePayload(type));
    }
  }

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
            onClick={() => fire(p.type, EVENT_CATALOG[p.type].payload)}
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
            list="known-event-types"
            onChange={(e) => onTypeChange(e.target.value)}
            placeholder="event.type (e.g. research.requested)"
            className="w-full rounded-md border border-white/15 bg-black/30 px-2 py-1 font-mono text-xs"
          />
          <datalist id="known-event-types">
            {KNOWN_EVENT_TYPES.map((t) => (
              <option key={t} value={t} />
            ))}
          </datalist>
          {EVENT_CATALOG[rawType] && (
            <p className="font-mono text-[10px] text-slate-500">
              reacts: {EVENT_CATALOG[rawType].reacts}
            </p>
          )}
          <textarea
            value={rawPayload}
            onChange={(e) => setRawPayload(e.target.value)}
            rows={6}
            placeholder={examplePayload(rawType)}
            spellCheck={false}
            className="w-full rounded-md border border-white/15 bg-black/30 px-2 py-1 font-mono text-[11px]"
          />
          <div className="flex gap-1.5">
            <button
              onClick={() => setRawPayload(examplePayload(rawType))}
              className="rounded-md border border-white/15 px-2 py-1 text-[11px] text-slate-300 hover:bg-white/10"
            >
              Reset payload
            </button>
            <button
              onClick={fireRaw}
              disabled={busy !== null}
              className="flex-1 rounded-md border border-white/15 px-2 py-1 text-xs hover:bg-white/10 disabled:opacity-50"
            >
              Publish event
            </button>
          </div>
        </div>
      )}

      {err && <p className="mt-2 text-[11px] text-rose-400">{err}</p>}
    </div>
  );
}
