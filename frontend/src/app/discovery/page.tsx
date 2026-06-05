"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PageHeader, Card, Button, Modal, VentureSelector, Spinner, EmptyState, Input, Textarea, ConfidenceBar } from "@/components/ui";

export default function DiscoveryPage() {
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
      <PageHeader
        title="Customer Discovery"
        subtitle="Interview guides, transcript analysis, pain extraction. Evidence-based customer understanding."
        actions={
          <div className="flex gap-3 items-center">
            <VentureSelector value={selectedVenture} onChange={(id) => { setSelectedVenture(id); setSelectedProject(null); }} />
            {selectedVenture && (
              <Button onClick={() => setShowForm(true)}>+ New Project</Button>
            )}
          </div>
        }
      />

      {error && (
        <div className="glass-card border-red-500/30 p-4 text-sm text-red-400">
          {error}
          <button onClick={() => setError("")} className="ml-2 text-red-300 underline text-xs">dismiss</button>
        </div>
      )}

      <div className="grid grid-cols-3 gap-6">
        {/* Project List */}
        <div className="col-span-1 space-y-3">
          {loading ? (
            <Spinner text="Loading..." />
          ) : projects.length === 0 && selectedVenture ? (
            <EmptyState message="No discovery projects yet." hint="Create one to start interviewing." />
          ) : (
            projects.map((p) => (
              <Card
                key={p.id}
                active={selectedProject?.id === p.id}
                onClick={() => setSelectedProject(p)}
                padding="sm"
              >
                <h3 className="font-medium text-[var(--text-primary)] text-sm">{p.name}</h3>
                <p className="text-xs text-[var(--text-muted)] mt-1">{p.domain}</p>
                {p.confidence !== undefined && (
                  <div className="mt-2">
                    <ConfidenceBar value={p.confidence} height="sm" showLabel />
                  </div>
                )}
                {p.interviews_count !== undefined && (
                  <p className="text-xs text-[var(--text-muted)] mt-2">{p.interviews_count} interviews</p>
                )}
              </Card>
            ))
          )}
        </div>

        {/* Project Detail */}
        <div className="col-span-2 space-y-4">
          {selectedProject ? (
            <>
              <Card padding="lg">
                <h2 className="text-xl font-bold text-[var(--text-primary)]">{selectedProject.name}</h2>
                <p className="text-sm text-[var(--text-muted)] mt-1">Domain: {selectedProject.domain}</p>
                {selectedProject.hypothesis && (
                  <p className="text-sm text-[var(--text-secondary)] mt-2 italic">&ldquo;{selectedProject.hypothesis}&rdquo;</p>
                )}

                {/* Assumptions */}
                {selectedProject.assumptions?.length > 0 && (
                  <div className="mt-4">
                    <h3 className="text-sm font-semibold text-[var(--text-secondary)] mb-2">Assumptions</h3>
                    <div className="space-y-2">
                      {selectedProject.assumptions.map((a: any, i: number) => (
                        <div key={i} className="flex items-center gap-3 text-sm">
                          <span className={`w-2 h-2 rounded-full ${
                            a.status === "validated" ? "bg-green-500" :
                            a.status === "invalidated" ? "bg-red-500" : "bg-[var(--text-muted)]"
                          }`} />
                          <span className="text-[var(--text-secondary)]">{typeof a === "string" ? a : a.statement || a}</span>
                          {a.confidence !== undefined && (
                            <span className="text-xs text-[var(--text-muted)]">({(a.confidence * 100).toFixed(0)}%)</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-3 mt-4 pt-4 border-t border-[var(--border-subtle)]">
                  <Button size="sm" onClick={() => handleGenerateGuide(selectedProject.id)} disabled={generatingGuide}>
                    {generatingGuide ? "Generating..." : "Generate Interview Guide"}
                  </Button>
                  <Button size="sm" onClick={() => setShowTranscript(true)} className="!from-green-600 !to-emerald-700">
                    Analyze Transcript
                  </Button>
                  <Button size="sm" onClick={() => handleSynthesize(selectedProject.id)} disabled={synthesizing} className="!from-purple-600 !to-violet-700">
                    {synthesizing ? "Synthesizing..." : "Synthesize Insights"}
                  </Button>
                </div>
              </Card>

              {/* Interview Guide */}
              {guide && (
                <Card className="border-[var(--accent-purple)]/30">
                  <h3 className="text-sm font-semibold text-[var(--accent-purple)] mb-3">Interview Guide (Mom Test)</h3>
                  {guide.questions ? (
                    <ol className="list-decimal list-inside space-y-2">
                      {guide.questions.map((q: string, i: number) => (
                        <li key={i} className="text-sm text-[var(--text-secondary)]">{q}</li>
                      ))}
                    </ol>
                  ) : (
                    <pre className="text-xs text-[var(--text-muted)] whitespace-pre-wrap code-block p-3 rounded">{JSON.stringify(guide, null, 2)}</pre>
                  )}
                </Card>
              )}

              {/* Analysis Result */}
              {analysisResult && (
                <Card className="border-green-500/30">
                  <h3 className="text-sm font-semibold text-green-400 mb-3">Transcript Analysis</h3>
                  <pre className="text-xs text-[var(--text-muted)] whitespace-pre-wrap code-block p-3 rounded">
                    {JSON.stringify(analysisResult, null, 2)}
                  </pre>
                </Card>
              )}

              {/* Synthesis */}
              {synthesis && (
                <Card className="border-[var(--accent-purple)]/30">
                  <h3 className="text-sm font-semibold text-[var(--accent-purple)] mb-3">Cross-Interview Synthesis</h3>
                  <pre className="text-xs text-[var(--text-muted)] whitespace-pre-wrap code-block p-3 rounded">
                    {JSON.stringify(synthesis, null, 2)}
                  </pre>
                </Card>
              )}
            </>
          ) : (
            <EmptyState message="Select a project to view details" />
          )}
        </div>
      </div>

      {/* Create Project Modal */}
      <Modal open={showForm} onClose={() => setShowForm(false)} title="New Discovery Project">
        <form onSubmit={handleCreate} className="space-y-4">
          <Input label="Name" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} required />
          <Input label="Domain" value={formData.domain} onChange={(e) => setFormData({ ...formData, domain: e.target.value })} required />
          <Textarea label="Hypothesis" value={formData.hypothesis} onChange={(e) => setFormData({ ...formData, hypothesis: e.target.value })} rows={2} required placeholder="We believe X will pay for Y because Z" />
          <Textarea label="Assumptions (one per line)" value={formData.assumptions} onChange={(e) => setFormData({ ...formData, assumptions: e.target.value })} rows={3} placeholder="One assumption per line" />
          <div className="flex justify-end gap-3">
            <Button variant="ghost" type="button" onClick={() => setShowForm(false)}>Cancel</Button>
            <Button type="submit">Create</Button>
          </div>
        </form>
      </Modal>

      {/* Analyze Transcript Modal */}
      <Modal open={showTranscript} onClose={() => setShowTranscript(false)} title="Analyze Interview Transcript" wide>
        <div className="space-y-4">
          <p className="text-sm text-[var(--text-muted)]">Paste a customer interview transcript. The AI will extract pain points, buying signals, and validate assumptions.</p>
          <Textarea
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            rows={12}
            placeholder={"Paste interview transcript here...\n\nInterviewer: Tell me about your biggest challenge with...\nCustomer: Well, the main thing is..."}
          />
          <div className="flex justify-end gap-3">
            <Button variant="ghost" onClick={() => setShowTranscript(false)}>Cancel</Button>
            <Button onClick={handleAnalyzeTranscript} disabled={analyzing}>
              {analyzing ? "Analyzing..." : "Analyze Transcript"}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
