/**
 * Turns a code-derived Topology (from /api/topology) into React Flow nodes and
 * edges, laid out in horizontal bands:
 *
 *   Band 0 (top):    Events (the bus)
 *   Band 1 (middle): Nodes  (dumb / agentic)
 *   Band 2 (bottom): Library tools  +  the trace-recorder substrate
 *
 * Edges:
 *   reacts  event -> node   (dashed, fuchsia)
 *   emits   node  -> event  (solid, fuchsia)
 *   calls   node  -> library (dashed, slate)
 */

import { MarkerType, type Edge, type Node } from "@xyflow/react";
import type { Topology } from "./topology-api";

export type FlowKind =
  | "event"
  | "node_dumb"
  | "node_agentic"
  | "library"
  | "substrate";

/** A node's function membership + the color of its primary function. A node may
 *  belong to several functions (e.g. signal-analyzer). */
export interface FunctionTag {
  name: string;
  color: string;
}

export interface FlowNodeData {
  label: string;
  kind: FlowKind;
  detail?: Record<string, unknown>;
  functions?: FunctionTag[];
  [key: string]: unknown;
}

/** Map of node name -> its function tags (name + color). Built on the page from
 *  /api/venture and a color palette. */
export type NodeFunctionMap = Record<string, FunctionTag[]>;

const COL = 260;
const ROW_EVENTS = 40;
const ROW_NODES = 260;
const ROW_LIBS = 500;

function spread(count: number, i: number): number {
  // Center each band horizontally around x=0.
  const total = (count - 1) * COL;
  return i * COL - total / 2;
}

export function buildFlow(
  topo: Topology,
  nodeFunctions: NodeFunctionMap = {},
): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = [];

  topo.events.forEach((e, i) => {
    nodes.push({
      id: `event:${e.type}`,
      position: { x: spread(topo.events.length, i), y: ROW_EVENTS },
      data: {
        label: e.type,
        kind: "event",
        detail: { emitted_by: e.emitted_by, reacted_by: e.reacted_by },
      } satisfies FlowNodeData,
      type: "flow",
    });
  });

  topo.nodes.forEach((n, i) => {
    nodes.push({
      id: `node:${n.name}`,
      position: { x: spread(topo.nodes.length, i), y: ROW_NODES },
      data: {
        label: n.name,
        kind: n.kind === "agentic" ? "node_agentic" : "node_dumb",
        functions: nodeFunctions[n.name] ?? [],
        detail: {
          version: n.version,
          kind: n.kind,
          reacts_to: n.reacts_to,
          emits: n.emits,
          calls: n.calls,
        },
      } satisfies FlowNodeData,
      type: "flow",
    });
  });

  const libCount = topo.libraries.length + 1; // + substrate
  topo.libraries.forEach((lib, i) => {
    nodes.push({
      id: `lib:${lib}`,
      position: { x: spread(libCount, i), y: ROW_LIBS },
      data: { label: lib, kind: "library" } satisfies FlowNodeData,
      type: "flow",
    });
  });

  nodes.push({
    id: `substrate:${topo.substrate.name}`,
    position: { x: spread(libCount, libCount - 1), y: ROW_LIBS },
    data: {
      label: topo.substrate.name,
      kind: "substrate",
      detail: { wraps: topo.substrate.wraps },
    } satisfies FlowNodeData,
    type: "flow",
  });

  const edges: Edge[] = topo.edges.map((e, i) => {
    const src =
      e.kind === "reacts" ? `event:${e.source}` : `node:${e.source}`;
    const tgt =
      e.kind === "emits"
        ? `event:${e.target}`
        : e.kind === "calls"
          ? `lib:${e.target}`
          : `node:${e.target}`;
    const color =
      e.kind === "calls" ? "rgba(148,163,184,0.7)" : "rgba(217,70,239,0.8)";
    return {
      id: `edge:${e.kind}:${e.source}->${e.target}:${i}`,
      source: src,
      target: tgt,
      label: e.kind,
      animated: e.kind !== "calls",
      style: {
        stroke: color,
        strokeWidth: 1.6,
        strokeDasharray: e.kind === "emits" ? undefined : "5 4",
      },
      labelStyle: { fill: "#cbd5e1", fontSize: 10 },
      labelBgStyle: { fill: "rgba(15,23,42,0.85)" },
      markerEnd: { type: MarkerType.ArrowClosed, color },
    } satisfies Edge;
  });

  return { nodes, edges };
}
