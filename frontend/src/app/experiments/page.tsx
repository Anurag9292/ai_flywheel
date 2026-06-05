"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function ExperimentsPage() {
  const [ventures, setVentures] = useState<any[]>([]);
  const [selectedVenture, setSelectedVenture] = useState("");
  const [experiments, setExperiments] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedExperiment, setSelectedExperiment] = useState<any>(null);
  const [results, setResults] = useState<any>(null);
  const [loadingResults, setLoadingResults] = useState(false);

  useEffect(() => {
    api.ventures.list().then(setVentures).catch(() => {});
  }, []);

  useEffect(() => {
    if (selectedVenture) {
      loadExperiments();
    }
  }, [selectedVenture]);

  async function loadExperiments() {
    setLoading(true);
    try {
      const data = await api.experiments.list(selectedVenture);
      setExperiments(data);
      setError("");
    } catch (e: any) {
      setError(e.message || "Failed to load experiments");
    } finally {
      setLoading(false);
    }
  }

  async function viewResults(experiment: any) {
    setSelectedExperiment(experiment);
    setLoadingResults(true);
    try {
      const data = await api.experiments.getResults(selectedVenture, experiment.id);
      setResults(data);
    } catch (e: any) {
      setError(e.message || "Failed to load results");
    } finally {
      setLoadingResults(false);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Experiments</h1>

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

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md mb-4 text-sm">
          {error}
        </div>
      )}

      {!selectedVenture ? (
        <p className="text-gray-500">Select a venture to view experiments.</p>
      ) : loading ? (
        <p className="text-gray-500">Loading experiments...</p>
      ) : experiments.length === 0 ? (
        <p className="text-gray-500">No experiments found for this venture.</p>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sample Size</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Winner</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {experiments.map((exp) => (
                <tr key={exp.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{exp.name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{exp.type || exp.experiment_type}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      exp.status === "completed" ? "bg-green-100 text-green-800" :
                      exp.status === "running" ? "bg-blue-100 text-blue-800" :
                      "bg-yellow-100 text-yellow-800"
                    }`}>
                      {exp.status || "pending"}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{exp.sample_size || "—"}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{exp.winner || "—"}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <button
                      onClick={() => viewResults(exp)}
                      className="px-3 py-1 bg-indigo-600 text-white rounded text-xs hover:bg-indigo-700"
                    >
                      View Results
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Results Panel */}
      {selectedExperiment && (
        <div className="mt-6 bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900">
              Results: {selectedExperiment.name}
            </h3>
            <button
              onClick={() => { setSelectedExperiment(null); setResults(null); }}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Close
            </button>
          </div>
          {loadingResults ? (
            <p className="text-gray-500">Loading results...</p>
          ) : results ? (
            <pre className="text-sm text-gray-600 whitespace-pre-wrap bg-gray-50 p-4 rounded-md">
              {JSON.stringify(results, null, 2)}
            </pre>
          ) : (
            <p className="text-gray-500">No results available.</p>
          )}
        </div>
      )}
    </div>
  );
}
