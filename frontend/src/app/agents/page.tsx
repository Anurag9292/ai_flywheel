"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PageHeader, Card, Button, Modal, VentureSelector, Spinner, EmptyState, Badge, Input, Textarea, Select } from "@/components/ui";
import { statusVariant } from "@/components/ui/badge";

function RatingSection({ ventureId, agentId, executionId }: { ventureId: string; agentId: string; executionId: string }) {
  const [rating, setRating] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  async function handleRate(value: number) {
    setSubmitting(true);
    try {
      await api.agents.submitFeedback({
        venture_id: ventureId,
        execution_id: executionId,
        agent_id: agentId,
        rating: value,
      });
      setRating(value);
      setSubmitted(true);
    } catch {
      // Silently handle errors
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex items-center gap-2 mt-3 pt-3 border-t border-[var(--border-subtle)]">
      <span className="text-xs text-[var(--text-muted)]">Rate this output:</span>
      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            onClick={() => handleRate(star)}
            disabled={submitting || submitted}
            className={`text-sm transition-colors ${
              rating && star <= rating
                ? "text-amber-400"
                : "text-[var(--text-muted)] hover:text-amber-400"
            } disabled:cursor-not-allowed`}
            title={`Rate ${star}/5`}
          >
            {rating && star <= rating ? "★" : "☆"}
          </button>
        ))}
      </div>
      {submitted && (
        <span className="text-[10px] text-green-400 ml-2">Feedback saved</span>
      )}
      {submitting && (
        <span className="text-[10px] text-[var(--text-muted)] ml-2">Saving...</span>
      )}
    </div>
  );
}

export default function AgentsPage() {
  const [selectedVenture, setSelectedVenture] = useState("");
  const [agents, setAgents] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showExecuteModal, setShowExecuteModal] = useState(false);
  const [executeAgentId, setExecuteAgentId] = useState("");
  const [taskInput, setTaskInput] = useState("");
  const [requireApproval, setRequireApproval] = useState(false);
  const [executeResult, setExecuteResult] = useState<any>(null);
  const [submitting, setSubmitting] = useState(false);
  const [suggesting, setSuggesting] = useState(false);
  const [networkRunning, setNetworkRunning] = useState(false);
  const [networkResults, setNetworkResults] = useState<any>(null);

  const [createForm, setCreateForm] = useState({
    name: "",
    description: "",
    agent_type: "research",
    model: "gpt-4",
    system_prompt: "",
  });

  useEffect(() => {
    if (selectedVenture) {
      loadAgents();
    }
  }, [selectedVenture]);

  async function loadAgents() {
    setLoading(true);
    try {
      const data = await api.agents.list(selectedVenture);
      setAgents(data);
      setError("");
    } catch (e: any) {
      setError(e.message || "Failed to load agents");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.agents.create(selectedVenture, createForm);
      setCreateForm({ name: "", description: "", agent_type: "research", model: "gpt-4", system_prompt: "" });
      setShowCreateForm(false);
      await loadAgents();
    } catch (e: any) {
      setError(e.message || "Failed to create agent");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleExecute(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const result = await api.agents.execute(selectedVenture, {
        agent_id: executeAgentId,
        task: taskInput,
        require_approval: requireApproval,
      });
      setExecuteResult(result);
    } catch (e: any) {
      setError(e.message || "Failed to execute agent");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSuggestTask() {
    setSuggesting(true);
    try {
      const result = await api.agents.suggestTask(selectedVenture, executeAgentId);
      setTaskInput(result.suggested_task);
    } catch (e: any) {
      setError(e.message || "Failed to suggest task");
    } finally {
      setSuggesting(false);
    }
  }

  async function handleRunNetwork() {
    setNetworkRunning(true);
    setNetworkResults(null);
    try {
      const result = await api.agents.runNetwork(selectedVenture);
      setNetworkResults(result);
    } catch (e: any) {
      setError(e.message || "Failed to run agent network");
    } finally {
      setNetworkRunning(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Agents"
        actions={
          <div className="flex gap-3 items-center">
            <VentureSelector value={selectedVenture} onChange={setSelectedVenture} />
            {selectedVenture && (
              <>
                <Button onClick={handleRunNetwork} disabled={networkRunning} variant="ghost">
                  {networkRunning ? "Running Network..." : "Run Network"}
                </Button>
                <Button onClick={() => setShowCreateForm(!showCreateForm)}>
                  {showCreateForm ? "Cancel" : "Create Agent"}
                </Button>
              </>
            )}
          </div>
        }
      />

      {error && (
        <div className="glass-card border-red-500/30 p-4 text-sm text-red-400">
          {error}
        </div>
      )}

      {!selectedVenture ? (
        <EmptyState message="Select a venture to view agents." />
      ) : loading ? (
        <Spinner text="Loading agents..." />
      ) : agents.length === 0 ? (
        <EmptyState message="No agents found for this venture." />
      ) : (
        <Card padding="sm" className="overflow-hidden">
          <table className="min-w-full">
            <thead>
              <tr className="border-b border-[var(--border-subtle)]">
                <th className="px-6 py-3 text-left text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider">Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider">Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider">Model</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody>
              {agents.map((agent) => (
                <tr key={agent.id} className="border-b border-[var(--border-subtle)] last:border-0">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-[var(--text-primary)]">{agent.name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-[var(--text-secondary)]">{agent.agent_type || agent.type}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-[var(--text-secondary)]">{agent.model}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <Badge variant={statusVariant(agent.status || "ready")}>
                      {agent.status || "ready"}
                    </Badge>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <Button
                      size="sm"
                      onClick={() => {
                        setExecuteAgentId(agent.id);
                        setShowExecuteModal(true);
                        setExecuteResult(null);
                        setTaskInput("");
                      }}
                    >
                      Execute
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {/* Network Results Section */}
      {networkResults && (
        <Card padding="md">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-[var(--text-primary)]">Network Execution Results</h3>
              <div className="flex gap-4 text-sm text-[var(--text-muted)]">
                <span>Total Cost: ${networkResults.total_cost_usd?.toFixed(4)}</span>
                <span>Duration: {(networkResults.total_duration_ms / 1000).toFixed(1)}s</span>
              </div>
            </div>
            <div className="space-y-3">
              {networkResults.steps?.map((step: any, i: number) => (
                <div key={i} className="glass-card p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-[var(--accent-purple)]">Step {i + 1}</span>
                      <span className="text-sm font-medium text-[var(--text-primary)]">{step.agent_name}</span>
                      <Badge variant={statusVariant(step.status)}>
                        {step.status}
                      </Badge>
                    </div>
                    <div className="flex gap-3 text-xs text-[var(--text-muted)]">
                      <span>${step.cost_usd?.toFixed(4)}</span>
                      <span>{(step.duration_ms / 1000).toFixed(1)}s</span>
                    </div>
                  </div>
                  {step.output && (
                    <div className="code-block p-3 rounded-md text-xs text-[var(--text-secondary)] whitespace-pre-wrap max-h-40 overflow-y-auto">
                      {step.output}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </Card>
      )}

      {/* Create Agent Modal */}
      <Modal open={showCreateForm} onClose={() => setShowCreateForm(false)} title="Create New Agent" wide>
        <form onSubmit={handleCreate} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Name"
              type="text"
              value={createForm.name}
              onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
              required
            />
            <Input
              label="Description"
              type="text"
              value={createForm.description}
              onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
            />
            <Select
              label="Agent Type"
              value={createForm.agent_type}
              onChange={(e) => setCreateForm({ ...createForm, agent_type: e.target.value })}
            >
              <option value="research">Research</option>
              <option value="analysis">Analysis</option>
              <option value="synthesis">Synthesis</option>
              <option value="execution">Execution</option>
            </Select>
            <Select
              label="Model"
              value={createForm.model}
              onChange={(e) => setCreateForm({ ...createForm, model: e.target.value })}
            >
              <option value="gpt-4">GPT-4</option>
              <option value="gpt-4-turbo">GPT-4 Turbo</option>
              <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
              <option value="claude-3-opus">Claude 3 Opus</option>
              <option value="claude-3-sonnet">Claude 3 Sonnet</option>
            </Select>
          </div>
          <Textarea
            label="System Prompt"
            value={createForm.system_prompt}
            onChange={(e) => setCreateForm({ ...createForm, system_prompt: e.target.value })}
            rows={3}
          />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="ghost" type="button" onClick={() => setShowCreateForm(false)}>Cancel</Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Creating..." : "Create Agent"}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Execute Modal */}
      <Modal open={showExecuteModal} onClose={() => setShowExecuteModal(false)} title="Execute Agent">
        <form onSubmit={handleExecute} className="space-y-4">
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-sm font-medium text-[var(--text-secondary)]">Task</label>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={handleSuggestTask}
                disabled={suggesting}
              >
                {suggesting ? "Suggesting..." : "Suggest Task"}
              </Button>
            </div>
            <Textarea
              value={taskInput}
              onChange={(e) => setTaskInput(e.target.value)}
              rows={4}
              placeholder="Describe the task for the agent..."
              required
            />
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="require-approval"
              checked={requireApproval}
              onChange={(e) => setRequireApproval(e.target.checked)}
              className="h-4 w-4 rounded border-[var(--border-subtle)] bg-[var(--bg-secondary)] text-[var(--accent-purple)] focus:ring-[var(--accent-purple)]"
            />
            <label htmlFor="require-approval" className="text-sm text-[var(--text-secondary)]">
              Require human approval before returning result
            </label>
          </div>
          {executeResult && (
            <div className="glass-card p-4 space-y-3">
              <div className="flex items-center justify-between">
                <p className="font-medium text-[var(--text-primary)]">Execution Result</p>
                <Badge variant={statusVariant(executeResult.status)}>
                  {executeResult.status}
                </Badge>
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs text-[var(--text-muted)]">
                <div>
                  <span className="block text-[var(--text-secondary)]">Cost</span>
                  ${executeResult.cost_usd?.toFixed(4)}
                </div>
                <div>
                  <span className="block text-[var(--text-secondary)]">Tokens</span>
                  {executeResult.tokens_input} in / {executeResult.tokens_output} out
                </div>
                <div>
                  <span className="block text-[var(--text-secondary)]">Duration</span>
                  {(executeResult.duration_ms / 1000).toFixed(1)}s
                </div>
              </div>
              {executeResult.output && (
                <div className="code-block p-3 rounded-md text-sm text-[var(--text-secondary)] whitespace-pre-wrap max-h-60 overflow-y-auto">
                  {executeResult.output}
                </div>
              )}
              {executeResult.execution_id && (
                <RatingSection
                  ventureId={selectedVenture}
                  agentId={executeAgentId}
                  executionId={executeResult.execution_id}
                />
              )}
            </div>
          )}
          <div className="flex gap-2 justify-end">
            <Button variant="ghost" type="button" onClick={() => setShowExecuteModal(false)}>Close</Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Running..." : "Run"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
