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

export interface EmittedEvent {
  type: string;
  event_id: string;
  payload: Record<string, unknown>;
}

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
  // Full payloads (what the node received + produced). Optional so an older
  // backend without them still renders.
  trigger_payload?: Record<string, unknown>;
  emitted?: EmittedEvent[];
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

// How long to wait before assuming the backend isn't going to answer. The dev
// runtime is sub-millisecond, so a multi-second wait almost always means the
// backend is paused (e.g. stopped at a breakpoint in the debugger) or down.
const REQUEST_TIMEOUT_MS = 6000;

/** Thrown when a request times out or the backend is unreachable/unresponsive.
 *  Distinguished so the UI can show a friendly "paused/slow — retry" message
 *  rather than a raw HTTP error. */
export class BackendUnavailableError extends Error {
  constructor(public readonly path: string) {
    super(
      `The dev API didn't respond (${path}). It may be paused at a breakpoint ` +
        `in the debugger, slow, or not running. Resume/restart it, then retry.`,
    );
    this.name = "BackendUnavailableError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      cache: "no-store",
      signal: controller.signal,
      ...init,
    });
  } catch (e) {
    // AbortError (timeout) or a network/connection failure — treat as the
    // backend being unavailable (commonly: paused at a breakpoint).
    if (e instanceof DOMException && e.name === "AbortError") {
      throw new BackendUnavailableError(path);
    }
    throw new BackendUnavailableError(path);
  } finally {
    clearTimeout(timer);
  }
  // 500/502/503/504 from the Next dev proxy mean the upstream (our FastAPI dev
  // server) didn't answer — almost always a paused (breakpoint) or stopped
  // backend. Surface the friendly, actionable error rather than a raw 500.
  if (
    res.status === 500 ||
    res.status === 502 ||
    res.status === 503 ||
    res.status === 504
  ) {
    throw new BackendUnavailableError(path);
  }
  if (!res.ok) {
    throw new Error(`${path} failed: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

async function getJSON<T>(path: string): Promise<T> {
  return request<T>(path);
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export interface PublishResponse {
  correlation_id: string;
  published: { type: string; venture_id: string };
  chain: TraceChain;
}

// ─── Human review queue (Step 5 — Wizard-of-Oz) ──────────────────────────────

export interface ReviewItem {
  event_id: string;
  type: string;
  venture_id: string;
  correlation_id: string;
  payload: Record<string, unknown>;
}

export interface ReviewResponse {
  count: number;
  pending: ReviewItem[];
}

export interface ApproveResponse {
  correlation_id: string;
  approved: string;
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

export const fetchReview = () => getJSON<ReviewResponse>("/api/review");

// ─── Venture composition (Layer 2 — functions) ───────────────────────────────

export interface VentureFunction {
  name: string;
  description: string;
  nodes: string[];
  events_in: string[];
  events_out: string[];
}

export interface VentureLint {
  unknown_nodes: string[];
  inactive_nodes: string[];
  config_conflicts: string[];
  orphan_emitted: string[];
  unproduced_reacted: string[];
}

export interface VentureResponse {
  name: string;
  description: string;
  domain: Record<string, unknown>;
  // "live" = lead-gen discovery hits real public ATS APIs; "fake" = canned.
  // Optional so an older backend without the field renders as fake.
  mode?: "live" | "fake";
  functions: VentureFunction[];
  lint: VentureLint;
}

export const fetchVenture = () => getJSON<VentureResponse>("/api/venture");

export const approveReview = (body: {
  event_id: string;
  venture_id?: string;
  draft?: string;
}) => postJSON<ApproveResponse>("/api/review/approve", body);
