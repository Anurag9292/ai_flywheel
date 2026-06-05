"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function AgentsPage() {
  const [ventures, setVentures] = useState<any[]>([]);
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

  const [createForm, setCreateForm] = useState({
    name: "",
    description: "",
    agent_type: "research",
    model: "gpt-4",
    system_prompt: "",
  });

  useEffect(() => {
    api.ventures.list().then(setVentures).catch(() => {});
  }, []);

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

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Agents</h1>
        {selectedVenture && (
          <button
            onClick={() => setShowCreateForm(!showCreateForm)}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium"
          >
            {showCreateForm ? "Cancel" : "Create Agent"}
          </button>
        )}
      </div>

      {/* Venture Selector */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-1">Select Venture</label>
        <select
          value={selectedVenture}
          onChange={(e) => setSelectedVenture(e.target.value)}
          className="w-full max-w-xs px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">-- Select a venture --</option>
          {ventures.map((v) => (
            <option key={v.id} value={v.id}>{v.name}</option>
          ))}
        </select>
      </div>

      {/* Create Agent Form */}
      {showCreateForm && (
        <form onSubmit={handleCreate} className="bg-white rounded-lg shadow p-6 mb-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Create New Agent</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
              <input
                type="text"
                value={createForm.name}
                onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <input
                type="text"
                value={createForm.description}
                onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Agent Type</label>
              <select
                value={createForm.agent_type}
                onChange={(e) => setCreateForm({ ...createForm, agent_type: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="research">Research</option>
                <option value="analysis">Analysis</option>
                <option value="synthesis">Synthesis</option>
                <option value="execution">Execution</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Model</label>
              <select
                value={createForm.model}
                onChange={(e) => setCreateForm({ ...createForm, model: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="gpt-4">GPT-4</option>
                <option value="gpt-4-turbo">GPT-4 Turbo</option>
                <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                <option value="claude-3-opus">Claude 3 Opus</option>
                <option value="claude-3-sonnet">Claude 3 Sonnet</option>
              </select>
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">System Prompt</label>
              <textarea
                value={createForm.system_prompt}
                onChange={(e) => setCreateForm({ ...createForm, system_prompt: e.target.value })}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="mt-4 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 text-sm font-medium disabled:opacity-50"
          >
            {submitting ? "Creating..." : "Create Agent"}
          </button>
        </form>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md mb-4 text-sm">
          {error}
        </div>
      )}

      {!selectedVenture ? (
        <p className="text-gray-500">Select a venture to view agents.</p>
      ) : loading ? (
        <p className="text-gray-500">Loading agents...</p>
      ) : agents.length === 0 ? (
        <p className="text-gray-500">No agents found for this venture.</p>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Model</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {agents.map((agent) => (
                <tr key={agent.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{agent.name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{agent.agent_type || agent.type}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{agent.model}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                      {agent.status || "ready"}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <button
                      onClick={() => {
                        setExecuteAgentId(agent.id);
                        setShowExecuteModal(true);
                        setExecuteResult(null);
                        setTaskInput("");
                      }}
                      className="px-3 py-1 bg-purple-600 text-white rounded text-xs hover:bg-purple-700"
                    >
                      Execute
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Execute Modal */}
      {showExecuteModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Execute Agent</h3>
            <form onSubmit={handleExecute}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">Task</label>
                <textarea
                  value={taskInput}
                  onChange={(e) => setTaskInput(e.target.value)}
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Describe the task for the agent..."
                  required
                />
              </div>
              <div className="mb-4 flex items-center gap-2">
                <input
                  type="checkbox"
                  id="require-approval"
                  checked={requireApproval}
                  onChange={(e) => setRequireApproval(e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="require-approval" className="text-sm text-gray-700">
                  Require human approval before returning result
                </label>
              </div>
              {executeResult && (
                <div className="mb-4 p-3 bg-gray-50 rounded-md text-sm">
                  <p className="font-medium text-gray-700 mb-1">Result:</p>
                  <pre className="text-xs text-gray-600 whitespace-pre-wrap">{JSON.stringify(executeResult, null, 2)}</pre>
                </div>
              )}
              <div className="flex gap-2 justify-end">
                <button
                  type="button"
                  onClick={() => setShowExecuteModal(false)}
                  className="px-4 py-2 text-gray-700 border border-gray-300 rounded-md text-sm hover:bg-gray-50"
                >
                  Close
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-purple-600 text-white rounded-md text-sm hover:bg-purple-700 disabled:opacity-50"
                >
                  {submitting ? "Running..." : "Run"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
