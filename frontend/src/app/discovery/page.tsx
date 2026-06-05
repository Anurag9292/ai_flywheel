"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function DiscoveryPage() {
  const [ventures, setVentures] = useState<any[]>([]);
  const [selectedVenture, setSelectedVenture] = useState("");
  const [projects, setProjects] = useState<any[]>([]);
  const [selectedProject, setSelectedProject] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Create form
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ name: "", domain: "", hypothesis: "", assumptions: "" });

  // Guide & transcript
  const [guide, setGuide] = useState<any>(null);
  const [generatingGuide, setGeneratingGuide] = useState(false);
  const [showTranscript, setShowTranscript] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<any>(null);

  // Synthesis
  const [synthesizing, setSynthesizing] = useState(false);
  const [synthesis, setSynthesis] = useState<any>(null);

  useEffect(() => {
    api.ventures.list().then(setVentures).catch(() => {});
  }, []);

  useEffect(() => {
    if (selectedVenture) loadProjects();
  }, [selectedVenture]);

  async function loadProjects() {
    setLoading(true);
    try {
      const data = await api.discovery.listProjects(selectedVenture);
      setProjects(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api.discovery.createProject(selectedVenture, {
        ...formData,
        assumptions: formData.assumptions.split("\n").map((s) => s.trim()).filter(Boolean),
      });
      setFormData({ name: "", domain: "", hypothesis: "", assumptions: "" });
      setShowForm(false);
      await loadProjects();
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function handleGenerateGuide(projectId: string) {
    setGeneratingGuide(true);
    setGuide(null);
    try {
      const result = await api.discovery.generateGuide(selectedVenture, { project_id: projectId });
      setGuide(result);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setGeneratingGuide(false);
    }
  }

  async function handleAnalyzeTranscript() {
    if (!selectedProject || !transcript.trim()) return;
    setAnalyzing(true);
    setAnalysisResult(null);
    try {
      const result = await api.discovery.analyzeTranscript(selectedVenture, {
        project_id: selectedProject.id,
        transcript: transcript,
      });
      setAnalysisResult(result);
      await loadProjects();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleSynthesize(projectId: string) {
    setSynthesizing(true);
    setSynthesis(null);
    try {
      const result = await api.discovery.synthesize(selectedVenture, { project_id: projectId });
      setSynthesis(result);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSynthesizing(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Customer Discovery</h1>
          <p className="text-sm text-gray-500 mt-1">
            Interview guides, transcript analysis, pain extraction. Evidence-based customer understanding.
          </p>
        </div>
        <div className="flex gap-3">
          <select
            value={selectedVenture}
            onChange={(e) => { setSelectedVenture(e.target.value); setSelectedProject(null); }}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="">Select venture...</option>
            {ventures.map((v) => (
              <option key={v.id} value={v.id}>{v.name}</option>
            ))}
          </select>
          {selectedVenture && (
            <button onClick={() => setShowForm(true)} className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700">
              + New Project
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm">
          {error}
          <button onClick={() => setError("")} className="ml-2 text-red-500 underline text-xs">dismiss</button>
        </div>
      )}

      <div className="grid grid-cols-3 gap-6">
        {/* Project List */}
        <div className="col-span-1 space-y-3">
          {loading ? (
            <p className="text-sm text-gray-500">Loading...</p>
          ) : projects.length === 0 && selectedVenture ? (
            <div className="bg-white rounded-lg border border-dashed border-gray-300 p-6 text-center">
              <p className="text-gray-500 text-sm">No discovery projects yet.</p>
              <p className="text-gray-400 text-xs mt-1">Create one to start interviewing.</p>
            </div>
          ) : (
            projects.map((p) => (
              <div
                key={p.id}
                onClick={() => setSelectedProject(p)}
                className={`bg-white rounded-lg border p-4 cursor-pointer transition-all ${
                  selectedProject?.id === p.id ? "border-indigo-500 ring-2 ring-indigo-200" : "border-gray-200 hover:border-gray-300"
                }`}
              >
                <h3 className="font-medium text-gray-900 text-sm">{p.name}</h3>
                <p className="text-xs text-gray-500 mt-1">{p.domain}</p>
                {p.confidence !== undefined && (
                  <div className="mt-2">
                    <div className="flex justify-between text-xs text-gray-500 mb-1">
                      <span>Confidence</span>
                      <span>{(p.confidence * 100).toFixed(0)}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-1.5">
                      <div className="h-1.5 rounded-full bg-indigo-500" style={{ width: `${p.confidence * 100}%` }} />
                    </div>
                  </div>
                )}
                {p.interviews_count !== undefined && (
                  <p className="text-xs text-gray-400 mt-2">{p.interviews_count} interviews</p>
                )}
              </div>
            ))
          )}
        </div>

        {/* Project Detail */}
        <div className="col-span-2 space-y-4">
          {selectedProject ? (
            <>
              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <h2 className="text-xl font-bold text-gray-900">{selectedProject.name}</h2>
                <p className="text-sm text-gray-500 mt-1">Domain: {selectedProject.domain}</p>
                {selectedProject.hypothesis && (
                  <p className="text-sm text-gray-600 mt-2 italic">&ldquo;{selectedProject.hypothesis}&rdquo;</p>
                )}

                {/* Assumptions */}
                {selectedProject.assumptions?.length > 0 && (
                  <div className="mt-4">
                    <h3 className="text-sm font-semibold text-gray-700 mb-2">Assumptions</h3>
                    <div className="space-y-2">
                      {selectedProject.assumptions.map((a: any, i: number) => (
                        <div key={i} className="flex items-center gap-3 text-sm">
                          <span className={`w-2 h-2 rounded-full ${
                            a.status === "validated" ? "bg-green-500" :
                            a.status === "invalidated" ? "bg-red-500" : "bg-gray-400"
                          }`} />
                          <span className="text-gray-700">{typeof a === "string" ? a : a.statement || a}</span>
                          {a.confidence !== undefined && (
                            <span className="text-xs text-gray-400">({(a.confidence * 100).toFixed(0)}%)</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-3 mt-4 pt-4 border-t border-gray-200">
                  <button
                    onClick={() => handleGenerateGuide(selectedProject.id)}
                    disabled={generatingGuide}
                    className="bg-indigo-600 text-white px-3 py-1.5 rounded text-sm hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {generatingGuide ? "Generating..." : "Generate Interview Guide"}
                  </button>
                  <button
                    onClick={() => setShowTranscript(true)}
                    className="bg-green-600 text-white px-3 py-1.5 rounded text-sm hover:bg-green-700"
                  >
                    Analyze Transcript
                  </button>
                  <button
                    onClick={() => handleSynthesize(selectedProject.id)}
                    disabled={synthesizing}
                    className="bg-purple-600 text-white px-3 py-1.5 rounded text-sm hover:bg-purple-700 disabled:opacity-50"
                  >
                    {synthesizing ? "Synthesizing..." : "Synthesize Insights"}
                  </button>
                </div>
              </div>

              {/* Interview Guide */}
              {guide && (
                <div className="bg-white rounded-lg border border-indigo-200 p-6">
                  <h3 className="text-sm font-semibold text-indigo-800 mb-3">Interview Guide (Mom Test)</h3>
                  {guide.questions ? (
                    <ol className="list-decimal list-inside space-y-2">
                      {guide.questions.map((q: string, i: number) => (
                        <li key={i} className="text-sm text-gray-700">{q}</li>
                      ))}
                    </ol>
                  ) : (
                    <pre className="text-xs text-gray-600 whitespace-pre-wrap">{JSON.stringify(guide, null, 2)}</pre>
                  )}
                </div>
              )}

              {/* Analysis Result */}
              {analysisResult && (
                <div className="bg-white rounded-lg border border-green-200 p-6">
                  <h3 className="text-sm font-semibold text-green-800 mb-3">Transcript Analysis</h3>
                  <pre className="text-xs text-gray-600 whitespace-pre-wrap bg-gray-50 p-3 rounded">
                    {JSON.stringify(analysisResult, null, 2)}
                  </pre>
                </div>
              )}

              {/* Synthesis */}
              {synthesis && (
                <div className="bg-white rounded-lg border border-purple-200 p-6">
                  <h3 className="text-sm font-semibold text-purple-800 mb-3">Cross-Interview Synthesis</h3>
                  <pre className="text-xs text-gray-600 whitespace-pre-wrap bg-gray-50 p-3 rounded">
                    {JSON.stringify(synthesis, null, 2)}
                  </pre>
                </div>
              )}
            </>
          ) : (
            <div className="bg-white rounded-lg border border-dashed border-gray-300 p-12 text-center">
              <p className="text-gray-500">Select a project to view details</p>
            </div>
          )}
        </div>
      </div>

      {/* Create Project Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg shadow-xl">
            <h2 className="text-lg font-bold text-gray-900 mb-4">New Discovery Project</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="text-sm font-medium text-gray-700">Name</label>
                <input value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" required />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">Domain</label>
                <input value={formData.domain} onChange={(e) => setFormData({ ...formData, domain: e.target.value })} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" required />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">Hypothesis</label>
                <textarea value={formData.hypothesis} onChange={(e) => setFormData({ ...formData, hypothesis: e.target.value })} rows={2} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" required placeholder="We believe X will pay for Y because Z" />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">Assumptions (one per line)</label>
                <textarea value={formData.assumptions} onChange={(e) => setFormData({ ...formData, assumptions: e.target.value })} rows={3} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" placeholder="One assumption per line" />
              </div>
              <div className="flex justify-end gap-3">
                <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 text-sm text-gray-700">Cancel</button>
                <button type="submit" className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700">Create</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Analyze Transcript Modal */}
      {showTranscript && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-2xl shadow-xl space-y-4">
            <h2 className="text-lg font-bold text-gray-900">Analyze Interview Transcript</h2>
            <p className="text-sm text-gray-500">Paste a customer interview transcript. The AI will extract pain points, buying signals, and validate assumptions.</p>
            <textarea
              value={transcript}
              onChange={(e) => setTranscript(e.target.value)}
              rows={12}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono"
              placeholder="Paste interview transcript here...&#10;&#10;Interviewer: Tell me about your biggest challenge with...&#10;Customer: Well, the main thing is..."
            />
            <div className="flex justify-end gap-3">
              <button onClick={() => setShowTranscript(false)} className="px-4 py-2 text-sm text-gray-700">Cancel</button>
              <button onClick={handleAnalyzeTranscript} disabled={analyzing} className="bg-green-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-green-700 disabled:opacity-50">
                {analyzing ? "Analyzing..." : "Analyze Transcript"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
