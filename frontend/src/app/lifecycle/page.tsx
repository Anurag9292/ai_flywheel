"use client";

import { useState, useEffect, useRef } from "react";
import { PageHeader, Card, Button, VentureSelector, Badge, Spinner, Modal, Input, Textarea } from "@/components/ui";
import { statusVariant } from "@/components/ui/badge";
import { apiFetch } from "@/lib/api";

interface StageInfo {
  name: string;
  label: string;
  description: string;
  icon: string;
}

const STAGES: StageInfo[] = [
  { name: "thesis", label: "Thesis", description: "Formulate hypothesis & assumptions", icon: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" },
  { name: "discovery", label: "Discovery", description: "Customer interviews & pain extraction", icon: "M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" },
  { name: "market", label: "Market", description: "Signal analysis & opportunity scoring", icon: "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" },
  { name: "offer", label: "Offer", description: "ICP, positioning, pricing design", icon: "M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7" },
];

export default function LifecyclePage() {
  const [ventureId, setVentureId] = useState("");
  const [ventures, setVentures] = useState<any[]>([]);
  const [workflowStatus, setWorkflowStatus] = useState<any>(null);
  const [polling, setPolling] = useState(false);
  const [showLaunch, setShowLaunch] = useState(false);
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  // Launch form
  const [hypothesis, setHypothesis] = useState("");
  const [assumptions, setAssumptions] = useState("");
  const [killSignals, setKillSignals] = useState("");
  const [launching, setLaunching] = useState(false);

  useEffect(() => {
    apiFetch<any[]>("/api/ventures/").then(setVentures).catch(() => {});
  }, []);

  useEffect(() => {
    if (ventureId) {
      fetchStatus();
      startPolling();
    }
    return () => stopPolling();
  }, [ventureId]);

  function startPolling() {
    stopPolling();
    setPolling(true);
    pollRef.current = setInterval(fetchStatus, 3000);
  }

  function stopPolling() {
    if (pollRef.current) clearInterval(pollRef.current);
    setPolling(false);
  }

  async function fetchStatus() {
    if (!ventureId) return;
    try {
      const status = await apiFetch<any>(`/api/workflows/venture/${ventureId}/active`);
      setWorkflowStatus(status);
      if (status.stage === "completed" || status.status === "none" || status.killed) {
        stopPolling();
      }
    } catch {
      setWorkflowStatus(null);
    }
  }

  async function handleLaunch() {
    if (!ventureId || !hypothesis) return;
    setLaunching(true);
    const venture = ventures.find((v) => v.id === ventureId);
    try {
      await apiFetch("/api/workflows/lifecycle", {
        method: "POST",
        body: JSON.stringify({
          venture_id: ventureId,
          venture_name: venture?.name || "Venture",
          domain: venture?.domain || "general",
          initial_hypothesis: hypothesis,
          assumptions: assumptions.split("\n").filter(Boolean),
          kill_signals: killSignals.split("\n").filter(Boolean),
        }),
      });
      setShowLaunch(false);
      startPolling();
      setTimeout(fetchStatus, 1000);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setLaunching(false);
    }
  }

  async function handleApprove() {
    if (!workflowStatus?.workflow_id) return;
    await apiFetch(`/api/workflows/${workflowStatus.workflow_id}/approve`, { method: "POST" });
    setTimeout(fetchStatus, 1000);
  }

  async function handleKill() {
    if (!workflowStatus?.workflow_id) return;
    await apiFetch(`/api/workflows/${workflowStatus.workflow_id}/kill?reason=Manual kill from UI`, { method: "POST" });
    setTimeout(fetchStatus, 1000);
  }

  function getStageStatus(stageName: string): "completed" | "active" | "pending" | "killed" {
    if (!workflowStatus || workflowStatus.status === "none") return "pending";
    if (workflowStatus.killed && workflowStatus.stage === stageName) return "killed";
    const completed = workflowStatus.completed_stages || [];
    if (completed.includes(stageName)) return "completed";
    if (workflowStatus.stage === stageName) return "active";
    if (workflowStatus.stage?.startsWith("awaiting") && workflowStatus.stage.includes(stageName)) return "active";
    return "pending";
  }

  function getStageResult(stageName: string): any {
    return workflowStatus?.stage_results?.[stageName] || null;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Venture Lifecycle"
        subtitle="Orchestrate the full validation pipeline. Thesis → Discovery → Market → Offer."
        actions={
          <div className="flex gap-3 items-center">
            <select
              value={ventureId}
              onChange={(e) => setVentureId(e.target.value)}
              className="input-dark w-48"
            >
              <option value="">Select venture...</option>
              {ventures.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
            </select>
            {ventureId && (
              <Button onClick={() => setShowLaunch(true)}>Launch Lifecycle</Button>
            )}
          </div>
        }
      />

      {/* Pipeline Visualization */}
      {ventureId && (
        <div className="space-y-6">
          {/* Stage Pipeline */}
          <Card padding="lg">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-sm font-semibold text-[var(--text-primary)]">Pipeline Status</h2>
              {polling && (
                <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
                  <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                  Live
                </div>
              )}
              {workflowStatus?.killed && <Badge variant="red">KILLED</Badge>}
              {workflowStatus?.stage === "completed" && <Badge variant="green">VALIDATED</Badge>}
            </div>

            {/* Stage Steps */}
            <div className="relative">
              {/* Connection line */}
              <div className="absolute top-8 left-8 right-8 h-0.5 bg-[var(--border-subtle)]" />

              <div className="relative grid grid-cols-4 gap-4">
                {STAGES.map((stage, i) => {
                  const status = getStageStatus(stage.name);
                  const result = getStageResult(stage.name);

                  return (
                    <div key={stage.name} className="flex flex-col items-center text-center">
                      {/* Circle indicator */}
                      <div className={`relative z-10 w-16 h-16 rounded-full flex items-center justify-center border-2 transition-all ${
                        status === "completed"
                          ? "bg-green-500/20 border-green-500 shadow-[0_0_12px_rgba(34,197,94,0.3)]"
                          : status === "active"
                          ? "bg-violet-500/20 border-violet-500 shadow-[0_0_12px_rgba(139,92,246,0.4)] animate-pulse"
                          : status === "killed"
                          ? "bg-red-500/20 border-red-500 shadow-[0_0_12px_rgba(239,68,68,0.3)]"
                          : "bg-[var(--bg-card)] border-[var(--border-subtle)]"
                      }`}>
                        {status === "completed" ? (
                          <svg className="w-6 h-6 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                          </svg>
                        ) : status === "active" ? (
                          <div className="w-4 h-4 border-2 border-violet-400 border-t-transparent rounded-full animate-spin" />
                        ) : status === "killed" ? (
                          <svg className="w-6 h-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        ) : (
                          <svg className="w-5 h-5 text-[var(--text-muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d={stage.icon} />
                          </svg>
                        )}
                      </div>

                      {/* Label */}
                      <p className={`mt-3 text-sm font-medium ${
                        status === "active" ? "text-violet-300" :
                        status === "completed" ? "text-green-300" :
                        status === "killed" ? "text-red-300" :
                        "text-[var(--text-muted)]"
                      }`}>
                        {stage.label}
                      </p>
                      <p className="text-[10px] text-[var(--text-muted)] mt-0.5">{stage.description}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          </Card>

          {/* Stage Results */}
          {workflowStatus?.stage_results && Object.keys(workflowStatus.stage_results).length > 0 && (
            <div className="grid grid-cols-2 gap-4">
              {STAGES.map((stage) => {
                const result = getStageResult(stage.name);
                if (!result) return null;

                return (
                  <Card key={stage.name} padding="md">
                    <div className="flex items-center gap-2 mb-3">
                      <svg className="w-4 h-4 text-[var(--text-secondary)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d={stage.icon} />
                      </svg>
                      <h3 className="text-sm font-semibold text-[var(--text-primary)]">{stage.label} Result</h3>
                      <Badge variant={result.status === "passed" ? "green" : "yellow"}>{result.status}</Badge>
                    </div>
                    <div className="code-block text-[11px] max-h-40 overflow-y-auto">
                      <pre>{JSON.stringify(result, null, 2)}</pre>
                    </div>
                  </Card>
                );
              })}
            </div>
          )}

          {/* Action Buttons */}
          {workflowStatus?.stage?.startsWith("awaiting") && (
            <Card padding="md" className="!border-amber-500/30">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-amber-300">Awaiting Approval</p>
                  <p className="text-xs text-[var(--text-muted)] mt-1">
                    The workflow is paused. Review the results and decide to proceed or kill.
                  </p>
                </div>
                <div className="flex gap-3">
                  <Button onClick={handleApprove}>Approve & Proceed</Button>
                  <Button variant="danger" onClick={handleKill}>Kill Venture</Button>
                </div>
              </div>
            </Card>
          )}

          {/* No active workflow */}
          {(!workflowStatus || workflowStatus.status === "none") && (
            <Card padding="lg" className="text-center">
              <p className="text-[var(--text-muted)]">No active lifecycle workflow for this venture.</p>
              <p className="text-xs text-[var(--text-muted)] mt-1">Click "Launch Lifecycle" to start the validation pipeline.</p>
            </Card>
          )}
        </div>
      )}

      {/* Launch Modal */}
      <Modal open={showLaunch} onClose={() => setShowLaunch(false)} title="Launch Venture Lifecycle">
        <div className="space-y-4">
          <p className="text-sm text-[var(--text-secondary)]">
            This will run the full validation pipeline: Thesis → Discovery → Market → Offer.
            Each stage has kill gates that will terminate if signals are detected.
          </p>
          <Textarea
            label="Hypothesis"
            value={hypothesis}
            onChange={(e) => setHypothesis(e.target.value)}
            rows={2}
            placeholder="We believe [ICP] will pay [price] for [solution] because [pain]..."
          />
          <Textarea
            label="Assumptions (one per line)"
            value={assumptions}
            onChange={(e) => setAssumptions(e.target.value)}
            rows={3}
            placeholder="Target users have this pain&#10;They currently solve it with manual work&#10;They would pay $X/mo for automation"
          />
          <Textarea
            label="Kill Signals (one per line)"
            value={killSignals}
            onChange={(e) => setKillSignals(e.target.value)}
            rows={2}
            placeholder="Less than 3/10 interviews confirm pain&#10;Market size < $10M"
          />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="ghost" onClick={() => setShowLaunch(false)}>Cancel</Button>
            <Button onClick={handleLaunch} disabled={launching || !hypothesis}>
              {launching ? "Launching..." : "Launch Pipeline"}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
