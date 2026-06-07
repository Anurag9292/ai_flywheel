/**
 * Client for the dev introspection API (see new_docs/visualization.md).
 *
 * The backend base URL is configurable via NEXT_PUBLIC_FLYWHEEL_API so the
 * browser can reach the (exposed) dev server on its own origin/port.
 */

// Default to same-origin: next.config.ts rewrites /api/* to the backend, so
// the browser never makes a cross-origin request and the preview just works.
const API_BASE = process.env.NEXT_PUBLIC_FLYWHEEL_API ?? "";

// ─── Topology (View 1) ───────────────────────────────────────────────────────

export interface TopoNode {
  name: string;
  version: string;
  kind: "dumb" | "agentic" | string;
  reacts_to: string[];
  emits: string[];
  calls: string[];
}

export interface TopoEvent {
  type: string;
  emitted_by: string[];
  reacted_by: string[];
}

export type TopoEdgeKind = "reacts" | "emits" | "calls";

export interface TopoEdge {
  source: string;
  target: string;
  kind: TopoEdgeKind;
}

export interface Topology {
  nodes: TopoNode[];
  libraries: string[];
  events: TopoEvent[];
  edges: TopoEdge[];
  substrate: { name: string; wraps: string[] };
  lint: { orphan_emitted: string[]; unproduced_reacted: string[] };
}

// ─── Traces (View 2) ─────────────────────────────────────────────────────────

export interface TraceRow {
  captured_at: string;
  node: string;
  node_version: string;
  venture_id: string;
  correlation_id: string;
  trigger_event_id: string;
  trigger_type: string;
  emitted_types: string[];
  emitted_event_ids: string[];
  latency_ms: number;
  cost_usd: number;
  error: string | null;
  // Added by the API's chain builder:
  seq: number;
  parent_step: number | null;
  is_start: boolean;
  is_end: boolean;
}

export interface TraceChain {
  correlation_id: string;
  steps: TraceRow[];
}

export interface TracesResponse {
  count: number;
  traces: TraceRow[];
  chains: TraceChain[];
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`${path} failed: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`${path} failed: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

export interface PublishResponse {
  correlation_id: string;
  published: { type: string; venture_id: string };
  chain: TraceChain;
}

export const fetchTopology = () => getJSON<Topology>("/api/topology");
export const fetchTraces = () => getJSON<TracesResponse>("/api/traces");

export const publishEvent = (body: {
  type: string;
  venture_id?: string;
  payload?: Record<string, unknown>;
}) => postJSON<PublishResponse>("/api/publish", body);

export const resetTraces = () => postJSON<{ status: string }>("/api/reset", {});
