"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";

interface Assumption {
  id: string;
  statement: string;
  risk_level: string;
  status: string;
  confidence: number;
  evidence_count: number;
  validation_method: string | null;
}

interface Thesis {
  id: string;
  venture_id: string;
  title: string;
  hypothesis: string;
  status: string;
  confidence: number;
  evidence_count: number;
  assumptions: Assumption[];
  kill_signals: string[];
  validation_plan: any | null;
  created_at: string;
}

export default function ThesisPage() {
  const [ventures, setVentures] = useState<any[]>([]);
  const [selectedVenture, setSelectedVenture] = useState("");
  const [theses, setTheses] = useState<Thesis[]>([]);
  const [selectedThesis, setSelectedThesis] = useState<Thesis | null>(null);
  const [loading, setLoading] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [showEvidence, setShowEvidence] = useState(false);

  // Create form
  const [newTitle, setNewTitle] = useState("");
  const [newHypothesis, setNewHypothesis] = useState("");
  const [newAssumptions, setNewAssumptions] = useState("");
  const [newKillSignals, setNewKillSignals] = useState("");

  // Evidence form
  const [evidenceContent, setEvidenceContent] = useState("");
  const [evidenceDirection, setEvidenceDirection] = useState<"supports" | "contradicts" | "neutral">("supports");
  const [evidenceStrength, setEvidenceStrength] = useState(0.5);
  const [evidenceAssumption, setEvidenceAssumption] = useState("");
  const [evidenceSourceType, setEvidenceSourceType] = useState<string>("observation");

  useEffect(() => {
    api.ventures.list().then(setVentures).catch(() => {});
  }, []);

  useEffect(() => {
    if (selectedVenture) {
      setLoading(true);
      api.thesis.list(selectedVenture).then(setTheses).catch(() => setTheses([])).finally(() => setLoading(false));
    }
  }, [selectedVenture]);

  async function handleCreate() {
    if (!selectedVenture || !newTitle || !newHypothesis) return;
    const assumptions = newAssumptions
      .split("\n")
      .filter(Boolean)
      .map((s) => ({ statement: s.trim(), risk_level: "medium" as const }));
    const kill_signals = newKillSignals.split("\n").filter(Boolean).map((s) => s.trim());

    const thesis = await api.thesis.create(selectedVenture, {
      title: newTitle,
      hypothesis: newHypothesis,
      assumptions,
      kill_signals,
    });
    setTheses([...theses, thesis]);
    setShowCreate(false);
    setNewTitle("");
    setNewHypothesis("");
    setNewAssumptions("");
    setNewKillSignals("");
  }

  async function handleAddEvidence() {
    if (!selectedThesis || !evidenceContent) return;
    await api.thesis.addEvidence(selectedVenture, {
      thesis_id: selectedThesis.id,
      assumption_id: evidenceAssumption || null,
      source_type: evidenceSourceType,
      content: evidenceContent,
      direction: evidenceDirection,
      strength: evidenceStrength,
    });
    // Refresh thesis data
    const updated = await api.thesis.list(selectedVenture);
    setTheses(updated);
    const refreshed = updated.find((t: Thesis) => t.id === selectedThesis.id);
    if (refreshed) setSelectedThesis(refreshed);
    setShowEvidence(false);
    setEvidenceContent("");
  }

  async function handleGenerateValidationPlan() {
    if (!selectedThesis) return;
    const plan = await api.thesis.generateValidationPlan(selectedVenture, {
      thesis_id: selectedThesis.id,
    });
    // Refresh
    const updated = await api.thesis.list(selectedVenture);
    setTheses(updated);
    const refreshed = updated.find((t: Thesis) => t.id === selectedThesis.id);
    if (refreshed) setSelectedThesis(refreshed);
  }

  function getStatusColor(status: string) {
    switch (status) {
      case "validated": return "bg-green-100 text-green-800";
      case "invalidated": return "bg-red-100 text-red-800";
      case "active": return "bg-blue-100 text-blue-800";
      case "killed": return "bg-red-200 text-red-900";
      default: return "bg-gray-100 text-gray-800";
    }
  }

  function getConfidenceColor(confidence: number) {
    if (confidence >= 0.7) return "bg-green-500";
    if (confidence >= 0.4) return "bg-yellow-500";
    return "bg-red-500";
  }

  function getRiskBadge(risk: string) {
    switch (risk) {
      case "critical": return "bg-red-100 text-red-700 border-red-200";
      case "high": return "bg-orange-100 text-orange-700 border-orange-200";
      case "medium": return "bg-yellow-100 text-yellow-700 border-yellow-200";
      case "low": return "bg-green-100 text-green-700 border-green-200";
      default: return "bg-gray-100 text-gray-700 border-gray-200";
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Venture Thesis Engine</h1>
          <p className="text-sm text-gray-500 mt-1">
            Formulate hypotheses, track evidence, detect kill signals. Kill early, kill cheap.
          </p>
        </div>
        <div className="flex gap-3">
          <select
            value={selectedVenture}
            onChange={(e) => { setSelectedVenture(e.target.value); setSelectedThesis(null); }}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="">Select venture...</option>
            {ventures.map((v) => (
              <option key={v.id} value={v.id}>{v.name}</option>
            ))}
          </select>
          {selectedVenture && (
            <button
              onClick={() => setShowCreate(true)}
              className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700"
            >
              + New Thesis
            </button>
          )}
        </div>
      </div>

      {/* Main content area */}
      <div className="grid grid-cols-3 gap-6">
        {/* Thesis list */}
        <div className="col-span-1 space-y-3">
          {loading ? (
            <p className="text-gray-500 text-sm">Loading theses...</p>
          ) : theses.length === 0 && selectedVenture ? (
            <div className="bg-white rounded-lg border border-dashed border-gray-300 p-6 text-center">
              <p className="text-gray-500 text-sm">No theses yet.</p>
              <p className="text-gray-400 text-xs mt-1">Create one to start validating.</p>
            </div>
          ) : (
            theses.map((thesis) => (
              <div
                key={thesis.id}
                onClick={() => setSelectedThesis(thesis)}
                className={`bg-white rounded-lg border p-4 cursor-pointer transition-all ${
                  selectedThesis?.id === thesis.id
                    ? "border-indigo-500 ring-2 ring-indigo-200"
                    : "border-gray-200 hover:border-gray-300"
                }`}
              >
                <div className="flex items-start justify-between">
                  <h3 className="font-medium text-gray-900 text-sm">{thesis.title}</h3>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${getStatusColor(thesis.status)}`}>
                    {thesis.status}
                  </span>
                </div>
                {/* Confidence bar */}
                <div className="mt-3">
                  <div className="flex justify-between text-xs text-gray-500 mb-1">
                    <span>Confidence</span>
                    <span>{(thesis.confidence * 100).toFixed(0)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full transition-all ${getConfidenceColor(thesis.confidence)}`}
                      style={{ width: `${thesis.confidence * 100}%` }}
                    />
                  </div>
                </div>
                <div className="mt-2 flex gap-3 text-xs text-gray-500">
                  <span>{thesis.assumptions.length} assumptions</span>
                  <span>{thesis.evidence_count} evidence</span>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Thesis detail */}
        <div className="col-span-2">
          {selectedThesis ? (
            <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-6">
              {/* Header */}
              <div>
                <div className="flex items-start justify-between">
                  <h2 className="text-xl font-bold text-gray-900">{selectedThesis.title}</h2>
                  <span className={`text-sm px-3 py-1 rounded-full ${getStatusColor(selectedThesis.status)}`}>
                    {selectedThesis.status}
                  </span>
                </div>
                <p className="mt-2 text-gray-600 text-sm italic">&ldquo;{selectedThesis.hypothesis}&rdquo;</p>
              </div>

              {/* Confidence */}
              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium text-gray-700">Overall Confidence</span>
                  <span className="text-2xl font-bold text-gray-900">
                    {(selectedThesis.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div
                    className={`h-3 rounded-full transition-all ${getConfidenceColor(selectedThesis.confidence)}`}
                    style={{ width: `${selectedThesis.confidence * 100}%` }}
                  />
                </div>
              </div>

              {/* Kill Signals */}
              {selectedThesis.kill_signals.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <h3 className="text-sm font-semibold text-red-800 mb-2">Kill Signals</h3>
                  <ul className="space-y-1">
                    {selectedThesis.kill_signals.map((signal, i) => (
                      <li key={i} className="text-sm text-red-700 flex items-center gap-2">
                        <span className="w-1.5 h-1.5 bg-red-500 rounded-full" />
                        {signal}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Assumptions */}
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-3">
                  Assumptions ({selectedThesis.assumptions.length})
                </h3>
                <div className="space-y-3">
                  {selectedThesis.assumptions.map((assumption) => (
                    <div
                      key={assumption.id}
                      className="border border-gray-200 rounded-lg p-3"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm text-gray-800">{assumption.statement}</p>
                        <span className={`text-xs px-2 py-0.5 rounded border whitespace-nowrap ${getRiskBadge(assumption.risk_level)}`}>
                          {assumption.risk_level}
                        </span>
                      </div>
                      <div className="mt-2 flex items-center gap-4">
                        <div className="flex-1">
                          <div className="w-full bg-gray-200 rounded-full h-1.5">
                            <div
                              className={`h-1.5 rounded-full ${getConfidenceColor(assumption.confidence)}`}
                              style={{ width: `${assumption.confidence * 100}%` }}
                            />
                          </div>
                        </div>
                        <span className="text-xs text-gray-500">
                          {(assumption.confidence * 100).toFixed(0)}% | {assumption.evidence_count} evidence
                        </span>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${getStatusColor(assumption.status)}`}>
                          {assumption.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-3 pt-4 border-t border-gray-200">
                <button
                  onClick={() => setShowEvidence(true)}
                  className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700"
                >
                  + Add Evidence
                </button>
                <button
                  onClick={handleGenerateValidationPlan}
                  className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-md text-sm font-medium hover:bg-gray-50"
                >
                  Generate Validation Plan
                </button>
                <button
                  onClick={() => api.thesis.generateMemo(selectedVenture, { thesis_id: selectedThesis.id })}
                  className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-md text-sm font-medium hover:bg-gray-50"
                >
                  Generate Memo
                </button>
              </div>

              {/* Validation Plan */}
              {selectedThesis.validation_plan && (
                <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
                  <h3 className="text-sm font-semibold text-indigo-800 mb-2">Validation Plan</h3>
                  <pre className="text-xs text-indigo-700 whitespace-pre-wrap">
                    {JSON.stringify(selectedThesis.validation_plan, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-dashed border-gray-300 p-12 text-center">
              <p className="text-gray-500">Select a thesis to view details</p>
              <p className="text-gray-400 text-sm mt-1">Or create a new one to start validating your venture idea</p>
            </div>
          )}
        </div>
      </div>

      {/* Create Thesis Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg shadow-xl space-y-4">
            <h2 className="text-lg font-bold text-gray-900">New Venture Thesis</h2>
            <div>
              <label className="text-sm font-medium text-gray-700">Title</label>
              <input
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                placeholder="e.g., AI Sales Coach for B2B SDRs"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">Hypothesis</label>
              <textarea
                value={newHypothesis}
                onChange={(e) => setNewHypothesis(e.target.value)}
                rows={3}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                placeholder="We believe [ICP] will pay [price] for [solution] because [pain]. Disproven if [condition]."
              />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">Assumptions (one per line)</label>
              <textarea
                value={newAssumptions}
                onChange={(e) => setNewAssumptions(e.target.value)}
                rows={4}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                placeholder="SDRs spend 2+ hours daily on research&#10;Managers can't see rep preparation quality&#10;Existing tools don't personalize by industry"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">Kill Signals (one per line)</label>
              <textarea
                value={newKillSignals}
                onChange={(e) => setNewKillSignals(e.target.value)}
                rows={2}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                placeholder="Less than 3/10 interviews confirm pain&#10;Landing page converts below 2%"
              />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm text-gray-700 hover:text-gray-900">
                Cancel
              </button>
              <button onClick={handleCreate} className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700">
                Create Thesis
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Evidence Modal */}
      {showEvidence && selectedThesis && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg shadow-xl space-y-4">
            <h2 className="text-lg font-bold text-gray-900">Add Evidence</h2>
            <div>
              <label className="text-sm font-medium text-gray-700">Related Assumption</label>
              <select
                value={evidenceAssumption}
                onChange={(e) => setEvidenceAssumption(e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              >
                <option value="">General (applies to thesis overall)</option>
                {selectedThesis.assumptions.map((a) => (
                  <option key={a.id} value={a.id}>{a.statement}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">Evidence</label>
              <textarea
                value={evidenceContent}
                onChange={(e) => setEvidenceContent(e.target.value)}
                rows={3}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                placeholder="Describe the evidence..."
              />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="text-sm font-medium text-gray-700">Direction</label>
                <select
                  value={evidenceDirection}
                  onChange={(e) => setEvidenceDirection(e.target.value as any)}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                >
                  <option value="supports">Supports</option>
                  <option value="contradicts">Contradicts</option>
                  <option value="neutral">Neutral</option>
                </select>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">Source Type</label>
                <select
                  value={evidenceSourceType}
                  onChange={(e) => setEvidenceSourceType(e.target.value)}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                >
                  <option value="interview">Interview</option>
                  <option value="experiment">Experiment</option>
                  <option value="market_signal">Market Signal</option>
                  <option value="metric">Metric</option>
                  <option value="observation">Observation</option>
                </select>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">Strength ({evidenceStrength.toFixed(1)})</label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={evidenceStrength}
                  onChange={(e) => setEvidenceStrength(parseFloat(e.target.value))}
                  className="mt-2 w-full"
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button onClick={() => setShowEvidence(false)} className="px-4 py-2 text-sm text-gray-700">Cancel</button>
              <button onClick={handleAddEvidence} className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700">
                Add Evidence
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
