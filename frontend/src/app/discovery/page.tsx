"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function DiscoveryPage() {
  const [ventures, setVentures] = useState<any[]>([]);
  const [selectedVenture, setSelectedVenture] = useState("");
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [guide, setGuide] = useState<any>(null);
  const [generatingGuide, setGeneratingGuide] = useState(false);

  const [formData, setFormData] = useState({
    name: "",
    domain: "",
    hypothesis: "",
    assumptions: "",
  });

  useEffect(() => {
    api.ventures.list().then(setVentures).catch(() => {});
  }, []);

  useEffect(() => {
    if (selectedVenture) {
      loadProjects();
    }
  }, [selectedVenture]);

  async function loadProjects() {
    setLoading(true);
    try {
      const data = await api.discovery.listProjects(selectedVenture);
      setProjects(data);
      setError("");
    } catch (e: any) {
      setError(e.message || "Failed to load projects");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.discovery.createProject(selectedVenture, {
        ...formData,
        assumptions: formData.assumptions.split(",").map((s) => s.trim()).filter(Boolean),
      });
      setFormData({ name: "", domain: "", hypothesis: "", assumptions: "" });
      setShowForm(false);
      await loadProjects();
    } catch (e: any) {
      setError(e.message || "Failed to create project");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleGenerateGuide(projectId: string) {
    setGeneratingGuide(true);
    setGuide(null);
    try {
      const result = await api.discovery.generateGuide(selectedVenture, { project_id: projectId });
      setGuide(result);
    } catch (e: any) {
      setError(e.message || "Failed to generate guide");
    } finally {
      setGeneratingGuide(false);
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Discovery</h1>
        {selectedVenture && (
          <button
            onClick={() => setShowForm(!showForm)}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium"
          >
            {showForm ? "Cancel" : "New Project"}
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

      {/* Create Project Form */}
      {showForm && (
        <form onSubmit={handleCreate} className="bg-white rounded-lg shadow p-6 mb-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">New Discovery Project</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Domain</label>
              <input
                type="text"
                value={formData.domain}
                onChange={(e) => setFormData({ ...formData, domain: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Hypothesis</label>
              <textarea
                value={formData.hypothesis}
                onChange={(e) => setFormData({ ...formData, hypothesis: e.target.value })}
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Assumptions (comma-separated)</label>
              <input
                type="text"
                value={formData.assumptions}
                onChange={(e) => setFormData({ ...formData, assumptions: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="assumption 1, assumption 2, assumption 3"
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="mt-4 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 text-sm font-medium disabled:opacity-50"
          >
            {submitting ? "Creating..." : "Create Project"}
          </button>
        </form>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md mb-4 text-sm">
          {error}
        </div>
      )}

      {!selectedVenture ? (
        <p className="text-gray-500">Select a venture to view discovery projects.</p>
      ) : loading ? (
        <p className="text-gray-500">Loading projects...</p>
      ) : projects.length === 0 ? (
        <p className="text-gray-500">No discovery projects found.</p>
      ) : (
        <div className="space-y-4">
          {projects.map((project) => (
            <div key={project.id} className="bg-white rounded-lg shadow p-6">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-lg font-medium text-gray-900">{project.name}</h3>
                  <p className="text-sm text-gray-500 mt-1">Domain: {project.domain}</p>
                  {project.hypothesis && (
                    <p className="text-sm text-gray-600 mt-2">Hypothesis: {project.hypothesis}</p>
                  )}
                  {project.assumptions && project.assumptions.length > 0 && (
                    <div className="mt-2">
                      <p className="text-sm font-medium text-gray-700">Assumptions:</p>
                      <ul className="list-disc list-inside text-sm text-gray-600">
                        {project.assumptions.map((a: string, i: number) => (
                          <li key={i}>{a}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
                <button
                  onClick={() => handleGenerateGuide(project.id)}
                  disabled={generatingGuide}
                  className="px-3 py-1 bg-indigo-600 text-white rounded text-xs hover:bg-indigo-700 disabled:opacity-50"
                >
                  {generatingGuide ? "Generating..." : "Generate Interview Guide"}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Interview Guide Display */}
      {guide && (
        <div className="mt-6 bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Interview Guide</h3>
          {guide.questions ? (
            <ol className="list-decimal list-inside space-y-2">
              {guide.questions.map((q: string, i: number) => (
                <li key={i} className="text-sm text-gray-700">{q}</li>
              ))}
            </ol>
          ) : (
            <pre className="text-sm text-gray-600 whitespace-pre-wrap">{JSON.stringify(guide, null, 2)}</pre>
          )}
        </div>
      )}
    </div>
  );
}
