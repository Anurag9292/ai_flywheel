"use client";

import { useCallback, useState, useMemo, useEffect } from "react";
import {
  ReactFlow,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  BackgroundVariant,
  type Connection,
  type Edge,
  type Node,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import AgentNode from "@/components/workflow/agent-node";
import { NodePalette } from "@/components/workflow/node-palette";
import { PageHeader, Button, Card, Modal, Input, Select, Badge } from "@/components/ui";
import { api } from "@/lib/api";

const initialNodes: Node[] = [
  { id: "start", type: "agentNode", position: { x: 300, y: 50 }, data: { label: "Start", type: "start" } },
  { id: "researcher", type: "agentNode", position: { x: 300, y: 180 }, data: { label: "Research Agent", type: "agent", model: "gpt-4o-mini", description: "Gathers market data" } },
  { id: "analyzer", type: "agentNode", position: { x: 300, y: 330 }, data: { label: "Analysis Agent", type: "agent", model: "gpt-4o-mini", description: "Processes findings" } },
  { id: "review", type: "agentNode", position: { x: 300, y: 480 }, data: { label: "Founder Review", type: "human_review", description: "Approve or reject" } },
  { id: "end", type: "agentNode", position: { x: 300, y: 620 }, data: { label: "End", type: "end" } },
];

const initialEdges: Edge[] = [
  { id: "e-start-researcher", source: "start", target: "researcher", animated: true, style: { stroke: "rgba(139, 92, 246, 0.5)" }, markerEnd: { type: MarkerType.ArrowClosed, color: "rgba(139, 92, 246, 0.7)" } },
  { id: "e-researcher-analyzer", source: "researcher", target: "analyzer", animated: true, style: { stroke: "rgba(139, 92, 246, 0.5)" }, markerEnd: { type: MarkerType.ArrowClosed, color: "rgba(139, 92, 246, 0.7)" } },
  { id: "e-analyzer-review", source: "analyzer", target: "review", animated: true, style: { stroke: "rgba(139, 92, 246, 0.5)" }, markerEnd: { type: MarkerType.ArrowClosed, color: "rgba(139, 92, 246, 0.7)" } },
  { id: "e-review-end", source: "review", target: "end", animated: true, style: { stroke: "rgba(139, 92, 246, 0.5)" }, markerEnd: { type: MarkerType.ArrowClosed, color: "rgba(139, 92, 246, 0.7)" } },
];

export default function WorkflowsPage() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [showCompile, setShowCompile] = useState(false);
  const [compiled, setCompiled] = useState<any>(null);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [ventures, setVentures] = useState<any[]>([]);
  const [selectedVenture, setSelectedVenture] = useState<string>("");
  const [deploying, setDeploying] = useState(false);
  const [deployResult, setDeployResult] = useState<string | null>(null);

  useEffect(() => {
    api.ventures.list().then(setVentures).catch(() => {});
  }, []);

  const nodeTypes = useMemo(() => ({ agentNode: AgentNode }), []);

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) =>
        addEdge(
          {
            ...connection,
            animated: true,
            style: { stroke: "rgba(139, 92, 246, 0.5)" },
            markerEnd: { type: MarkerType.ArrowClosed, color: "rgba(139, 92, 246, 0.7)" },
          },
          eds
        )
      );
    },
    [setEdges]
  );

  function handleAddNode(type: string, label: string) {
    const id = `node-${Date.now()}`;
    const newNode: Node = {
      id,
      type: "agentNode",
      position: { x: 200 + Math.random() * 200, y: 200 + Math.random() * 200 },
      data: { label, type, model: type === "agent" ? "gpt-4o-mini" : undefined },
    };
    setNodes((nds) => [...nds, newNode]);
  }

  function handleCompile() {
    // Convert graph to Temporal workflow config
    const config = {
      name: "compiled-workflow",
      steps: nodes
        .filter((n) => (n.data as any).type !== "start" && (n.data as any).type !== "end")
        .map((n) => ({
          id: n.id,
          type: (n.data as any).type,
          label: (n.data as any).label,
          model: (n.data as any).model || null,
          connections: edges
            .filter((e) => e.source === n.id)
            .map((e) => e.target),
        })),
      edges: edges.map((e) => ({ from: e.source, to: e.target })),
      execution_order: topologicalSort(nodes, edges),
    };
    setCompiled(config);
    setShowCompile(true);
  }

  async function handleDeployAndRun() {
    if (!selectedVenture) {
      setDeployResult("Please select a venture first.");
      return;
    }
    setDeploying(true);
    setDeployResult(null);

    // Compile the graph
    const config = {
      venture_id: selectedVenture,
      name: "compiled-workflow",
      steps: nodes
        .filter((n) => (n.data as any).type !== "start" && (n.data as any).type !== "end")
        .map((n) => ({
          id: n.id,
          type: (n.data as any).type,
          label: (n.data as any).label,
          model: (n.data as any).model || null,
          connections: edges
            .filter((e) => e.source === n.id)
            .map((e) => e.target),
        })),
      edges: edges.map((e) => ({ from: e.source, to: e.target })),
      execution_order: topologicalSort(nodes, edges),
    };

    try {
      const result = await api.workflows.deployGraph(config);
      setDeployResult(`Deployed! Job ID: ${result.job_id} — Status: ${result.status}`);
    } catch (err: any) {
      setDeployResult(`Deploy failed: ${err.message || "Unknown error"}`);
    } finally {
      setDeploying(false);
    }
  }

  function topologicalSort(nodes: Node[], edges: Edge[]): string[] {
    const adj: Record<string, string[]> = {};
    const inDegree: Record<string, number> = {};
    nodes.forEach((n) => { adj[n.id] = []; inDegree[n.id] = 0; });
    edges.forEach((e) => { adj[e.source]?.push(e.target); inDegree[e.target] = (inDegree[e.target] || 0) + 1; });

    const queue = Object.keys(inDegree).filter((k) => inDegree[k] === 0);
    const result: string[] = [];
    while (queue.length) {
      const node = queue.shift()!;
      result.push(node);
      for (const neighbor of adj[node] || []) {
        inDegree[neighbor]--;
        if (inDegree[neighbor] === 0) queue.push(neighbor);
      }
    }
    return result;
  }

  function handleDeleteNode() {
    if (!selectedNode) return;
    setNodes((nds) => nds.filter((n) => n.id !== selectedNode.id));
    setEdges((eds) => eds.filter((e) => e.source !== selectedNode.id && e.target !== selectedNode.id));
    setSelectedNode(null);
  }

  return (
    <div className="space-y-6 h-[calc(100vh-80px)]">
      <PageHeader
        title="Workflow Builder"
        subtitle="Design multi-agent systems visually. Connect nodes to define execution flow."
        actions={
          <div className="flex items-center gap-3">
            <select
              value={selectedVenture}
              onChange={(e) => setSelectedVenture(e.target.value)}
              className="px-3 py-1.5 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-subtle)] text-sm text-[var(--text-primary)]"
            >
              <option value="">Select Venture...</option>
              {ventures.map((v) => (
                <option key={v.id} value={v.id}>{v.name}</option>
              ))}
            </select>
            <Button variant="ghost" onClick={() => { setNodes(initialNodes); setEdges(initialEdges); }}>Reset</Button>
            <Button onClick={handleCompile}>Compile to Temporal</Button>
            <Button onClick={handleDeployAndRun} disabled={deploying || !selectedVenture}>
              {deploying ? "Deploying..." : "Deploy & Run"}
            </Button>
          </div>
        }
      />

      {deployResult && (
        <Card padding="sm" className="!p-3">
          <p className="text-sm text-[var(--text-secondary)]">{deployResult}</p>
        </Card>
      )}

      <div className="grid grid-cols-[220px_1fr] gap-4 h-[calc(100%-80px)]">
        {/* Sidebar palette */}
        <div className="space-y-4">
          <Card padding="sm" className="!p-4">
            <NodePalette onAddNode={handleAddNode} />
          </Card>

          {selectedNode && (
            <Card padding="sm" className="!p-4 space-y-3">
              <p className="text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider">Selected Node</p>
              <p className="text-sm text-[var(--text-primary)] font-medium">{(selectedNode.data as any).label}</p>
              <Badge variant="purple">{(selectedNode.data as any).type}</Badge>
              <Button variant="danger" size="sm" onClick={handleDeleteNode} className="w-full !mt-3">Delete Node</Button>
            </Card>
          )}

          <Card padding="sm" className="!p-4">
            <p className="text-xs text-[var(--text-muted)]">
              <strong className="text-[var(--text-secondary)]">Nodes:</strong> {nodes.length} &nbsp;|&nbsp;
              <strong className="text-[var(--text-secondary)]">Edges:</strong> {edges.length}
            </p>
          </Card>
        </div>

        {/* Canvas */}
        <div className="rounded-xl border border-[var(--border-subtle)] overflow-hidden bg-[rgba(5,5,12,0.8)]">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={(_, node) => setSelectedNode(node)}
            onPaneClick={() => setSelectedNode(null)}
            nodeTypes={nodeTypes}
            fitView
            proOptions={{ hideAttribution: true }}
          >
            <Controls className="!bg-[var(--bg-secondary)] !border-[var(--border-subtle)] !rounded-lg [&>button]:!bg-[var(--bg-secondary)] [&>button]:!border-[var(--border-subtle)] [&>button]:!text-[var(--text-secondary)] [&>button:hover]:!bg-[rgba(139,92,246,0.1)]" />
            <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="rgba(139, 92, 246, 0.15)" />
          </ReactFlow>
        </div>
      </div>

      {/* Compile Modal */}
      <Modal open={showCompile} onClose={() => setShowCompile(false)} title="Compiled Workflow Config" wide>
        <div className="space-y-4">
          <p className="text-sm text-[var(--text-secondary)]">
            This configuration can be deployed as a Temporal workflow. Each step executes in topological order.
          </p>
          <div className="code-block max-h-[400px] overflow-y-auto">
            <pre>{JSON.stringify(compiled, null, 2)}</pre>
          </div>
          <div className="flex justify-end gap-3">
            <Button variant="ghost" onClick={() => setShowCompile(false)}>Close</Button>
            <Button onClick={() => { navigator.clipboard.writeText(JSON.stringify(compiled, null, 2)); }}>Copy Config</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
