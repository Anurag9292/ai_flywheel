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

  const [newTitle, setNewTitle] = useState("");
  const [newHypothesis, setNewHypothesis] = useState("");
  const [newAssumptions, setNewAssumptions] = useState("");
  const [newKillSignals, setNewKillSignals] = useState("");

  const [evidenceContent, setEvidenceContent] = useState("");
  const [evidenceDirection, setEvidenceDirection] = useState<"supports" | "contradicts" | "neutral">("supports");
  const [evidenceStrength, setEvidenceStrength] = useState(0.5);
  const [evidenceAssumption, setEvidenceAssumption] = useState("");
  const [evidenceSourceType, setEvidenceSourceType] = useState("observation");

  useEffect(() => { api.ventures.list().then(setVentures).catch(() => {}); }, []);
  useEffect(() => {
    if (selectedVenture) {
      setLoading(true);
      api.thesis.list(selectedVenture).then(setTheses).catch(() => setTheses([])).finally(() => setLoading(false));
    }
  }, [selectedVenture]);

  async function handleCreate() {
    if (!selectedVenture || !newTitle || !newHypothesis) return;
    const assumptions = newAssumptions.split("\n").filter(Boolean).map((s) => ({ statement: s.trim(), risk_level: "medium" as const }));
    const kill_signals = newKillSignals.split("\n").filter(Boolean).map((s) => s.trim());
    const thesis = await api.thesis.create(selectedVenture, { title: newTitle, hypothesis: newHypothesis, assumptions, kill_signals });
    setTheses([...theses, thesis]);
    setShowCreate(false);
    setNewTitle(""); setNewHypothesis(""); setNewAssumptions(""); setNewKillSignals("");
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
    const updated = await api.thesis.list(selectedVenture);
    setTheses(updated);
    const refreshed = updated.find((t: Thesis) => t.id === selectedThesis.id);
    if (refreshed) setSelectedThesis(refreshed);
    setShowEvidence(false);
    setEvidenceContent("");
  }

  function getConfClass(c: number) {
    if (c >= 0.7) return "confidence-high";
    if (c >= 0.4) return "confidence-mid";
    return "confidence-low";
  }

  function getStatusBadge(status: string) {
    switch (status) {
      case "validated": return "badge-green";
      case "invalidated": case "killed": return "badge-red";
      case "active": return "badge-purple";
      default: return "badge-blue";
    }
  }

  function getRiskBadge(risk: string) {
    switch (risk) {
      case "critical": return "badge-red";
      case "high": return "badge-yellow";
      case "medium": return "badge-blue";
      case "low": return "badge-green";
      default: return "badge-blue";
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold gradient-text">Venture Thesis Engine</h1>
          <p className="text-[var(--text-secondary)] mt-1">
            Formulate hypotheses, track evidence, detect kill signals. Kill early, kill cheap.
          </p>
        </div>
        <div className="flex gap-3">
          <select value={selectedVenture} onChange={(e) => { setSelectedVenture(e.target.value); setSelectedThesis(null); }} className="input-dark w-48">
            <option value="">Select venture...</option>
            {ventures.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
          </select>
          {selectedVenture && (
            <button onClick={() => setShowCreate(true)} className="btn-glow">+ New Thesis</button>
          )}
        </div>
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-3 gap-6">
        {/* Thesis list */}
        <div className="col-span-1 space-y-3">
          {loading ? (
            <div className="flex items-center gap-2 text-[var(--text-muted)]">
              <div className="w-3 h-3 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin" />
              Loading...
            </div>
          ) : theses.length === 0 && selectedVenture ? (
            <div className="glass-card p-6 text-center">
              <p className="text-[var(--text-muted)]">No theses yet.</p>
              <p className="text-xs text-[var(--text-muted)] mt-1">Create one to start validating.</p>
            </div>
          ) : (
            theses.map((thesis) => (
              <div
                key={thesis.id}
                onClick={() => setSelectedThesis(thesis)}
                className={`glass-card p-4 cursor-pointer ${selectedThesis?.id === thesis.id ? "glass-card-active" : ""}`}
              >
                <div className="flex items-start justify-between">
                  <h3 className="font-medium text-[var(--text-primary)] text-sm">{thesis.title}</h3>
                  <span className={`badge ${getStatusBadge(thesis.status)}`}>{thesis.status}</span>
                </div>
                <div className="mt-3">
                  <div className="flex justify-between text-xs text-[var(--text-muted)] mb-1.5">
                    <span>Confidence</span>
                    <span>{(thesis.confidence * 100).toFixed(0)}%</span>
                  </div>
                  <div className="confidence-bar">
                    <div className={`confidence-bar-fill ${getConfClass(thesis.confidence)}`} style={{ width: `${thesis.confidence * 100}%` }} />
                  </div>
                </div>
                <div className="mt-2 flex gap-3 text-xs text-[var(--text-muted)]">
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
            <div className="glass-card p-6 space-y-6">
              {/* Header */}
              <div>
                <div className="flex items-start justify-between">
                  <h2 className="text-xl font-bold text-[var(--text-primary)]">{selectedThesis.title}</h2>
                  <span className={`badge ${getStatusBadge(selectedThesis.status)}`}>{selectedThesis.status}</span>
                </div>
                <p className="mt-2 text-[var(--text-secondary)] text-sm italic">&ldquo;{selectedThesis.hypothesis}&rdquo;</p>
              </div>

              {/* Confidence */}
              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium text-[var(--text-secondary)]">Overall Confidence</span>
                  <span className="text-2xl font-bold text-[var(--text-primary)]">{(selectedThesis.confidence * 100).toFixed(0)}%</span>
                </div>
                <div className="confidence-bar" style={{ height: "8px" }}>
                  <div className={`confidence-bar-fill ${getConfClass(selectedThesis.confidence)}`} style={{ width: `${selectedThesis.confidence * 100}%` }} />
                </div>
              </div>

              {/* Kill Signals */}
              {selectedThesis.kill_signals.length > 0 && (
                <div className="kill-alert">
                  <h3 className="text-sm font-semibold text-red-300 mb-2 flex items-center gap-2">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                    </svg>
                    Kill Signals
                  </h3>
                  <ul className="space-y-1">
                    {selectedThesis.kill_signals.map((signal, i) => (
                      <li key={i} className="text-sm text-red-200/80 flex items-center gap-2">
                        <span className="w-1.5 h-1.5 bg-red-400 rounded-full shadow-[0_0_4px_rgba(248,113,113,0.6)]" />
                        {signal}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Assumptions */}
              <div>
                <h3 className="text-sm font-semibold text-[var(--text-secondary)] mb-3">Assumptions ({selectedThesis.assumptions.length})</h3>
                <div className="space-y-3">
                  {selectedThesis.assumptions.map((a) => (
                    <div key={a.id} className="p-3 rounded-lg border border-[var(--border-subtle)] bg-[rgba(0,0,0,0.2)]">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm text-[var(--text-primary)]">{a.statement}</p>
                        <span className={`badge ${getRiskBadge(a.risk_level)}`}>{a.risk_level}</span>
                      </div>
                      <div className="mt-2 flex items-center gap-4">
                        <div className="flex-1">
                          <div className="confidence-bar" style={{ height: "4px" }}>
                            <div className={`confidence-bar-fill ${getConfClass(a.confidence)}`} style={{ width: `${a.confidence * 100}%` }} />
                          </div>
                        </div>
                        <span className="text-xs text-[var(--text-muted)]">{(a.confidence * 100).toFixed(0)}% | {a.evidence_count} ev</span>
                        <span className={`badge ${getStatusBadge(a.status)}`}>{a.status}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-3 pt-4 border-t border-[var(--border-subtle)]">
                <button onClick={() => setShowEvidence(true)} className="btn-glow">+ Add Evidence</button>
                <button onClick={() => api.thesis.generateValidationPlan(selectedVenture, { thesis_id: selectedThesis.id })} className="btn-ghost">Generate Plan</button>
                <button onClick={() => api.thesis.generateMemo(selectedVenture, { thesis_id: selectedThesis.id })} className="btn-ghost">Generate Memo</button>
              </div>
            </div>
          ) : (
            <div className="glass-card p-12 text-center">
              <p className="text-[var(--text-muted)]">Select a thesis to view details</p>
              <p className="text-xs text-[var(--text-muted)] mt-1">Or create a new one to start validating your venture idea</p>
            </div>
          )}
        </div>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="modal-overlay">
          <div className="modal-content space-y-4">
            <h2 className="text-lg font-bold text-[var(--text-primary)]">New Venture Thesis</h2>
            <div>
              <label className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">Title</label>
              <input value={newTitle} onChange={(e) => setNewTitle(e.target.value)} className="input-dark mt-1" placeholder="e.g., AI Sales Coach for B2B SDRs" />
            </div>
            <div>
              <label className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">Hypothesis</label>
              <textarea value={newHypothesis} onChange={(e) => setNewHypothesis(e.target.value)} rows={3} className="input-dark mt-1" placeholder="We believe [ICP] will pay [price] for [solution] because [pain]..." />
            </div>
            <div>
              <label className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">Assumptions (one per line)</label>
              <textarea value={newAssumptions} onChange={(e) => setNewAssumptions(e.target.value)} rows={3} className="input-dark mt-1" placeholder="SDRs spend 2+ hours daily on research&#10;Managers lack visibility into prep quality" />
            </div>
            <div>
              <label className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">Kill Signals (one per line)</label>
              <textarea value={newKillSignals} onChange={(e) => setNewKillSignals(e.target.value)} rows={2} className="input-dark mt-1" placeholder="Less than 3/10 interviews confirm pain&#10;Landing page converts below 2%" />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button onClick={() => setShowCreate(false)} className="btn-ghost">Cancel</button>
              <button onClick={handleCreate} className="btn-glow">Create Thesis</button>
            </div>
          </div>
        </div>
      )}

      {/* Evidence Modal */}
      {showEvidence && selectedThesis && (
        <div className="modal-overlay">
          <div className="modal-content space-y-4">
            <h2 className="text-lg font-bold text-[var(--text-primary)]">Add Evidence</h2>
            <div>
              <label className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">Assumption</label>
              <select value={evidenceAssumption} onChange={(e) => setEvidenceAssumption(e.target.value)} className="input-dark mt-1">
                <option value="">General (thesis overall)</option>
                {selectedThesis.assumptions.map((a) => <option key={a.id} value={a.id}>{a.statement}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">Evidence</label>
              <textarea value={evidenceContent} onChange={(e) => setEvidenceContent(e.target.value)} rows={3} className="input-dark mt-1" placeholder="Describe the evidence..." />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">Direction</label>
                <select value={evidenceDirection} onChange={(e) => setEvidenceDirection(e.target.value as any)} className="input-dark mt-1">
                  <option value="supports">Supports</option>
                  <option value="contradicts">Contradicts</option>
                  <option value="neutral">Neutral</option>
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">Source</label>
                <select value={evidenceSourceType} onChange={(e) => setEvidenceSourceType(e.target.value)} className="input-dark mt-1">
                  <option value="interview">Interview</option>
                  <option value="experiment">Experiment</option>
                  <option value="market_signal">Market</option>
                  <option value="metric">Metric</option>
                  <option value="observation">Observation</option>
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">Strength ({evidenceStrength.toFixed(1)})</label>
                <input type="range" min="0" max="1" step="0.1" value={evidenceStrength} onChange={(e) => setEvidenceStrength(parseFloat(e.target.value))} className="mt-3 w-full accent-violet-500" />
              </div>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button onClick={() => setShowEvidence(false)} className="btn-ghost">Cancel</button>
              <button onClick={handleAddEvidence} className="btn-glow">Add Evidence</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
