"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PageHeader, Card, Button, VentureSelector, Spinner, EmptyState, Badge } from "@/components/ui";
import { statusVariant } from "@/components/ui/badge";

export default function ExperimentsPage() {
  const [selectedVenture, setSelectedVenture] = useState("");
  const [experiments, setExperiments] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedExperiment, setSelectedExperiment] = useState<any>(null);
  const [results, setResults] = useState<any>(null);
  const [loadingResults, setLoadingResults] = useState(false);

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
    <div className="space-y-6">
      <PageHeader
        title="Experiments"
        actions={
          <VentureSelector value={selectedVenture} onChange={setSelectedVenture} />
        }
      />

      {error && (
        <div className="glass-card border-red-500/30 p-4 text-sm text-red-400">
          {error}
        </div>
      )}

      {!selectedVenture ? (
        <EmptyState message="Select a venture to view experiments." />
      ) : loading ? (
        <Spinner text="Loading experiments..." />
      ) : experiments.length === 0 ? (
        <EmptyState message="No experiments found for this venture." />
      ) : (
        <Card padding="sm" className="overflow-hidden">
          <table className="min-w-full">
            <thead>
              <tr className="border-b border-[var(--border-subtle)]">
                <th className="px-6 py-3 text-left text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider">Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider">Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider">Sample Size</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider">Winner</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody>
              {experiments.map((exp) => (
                <tr key={exp.id} className="border-b border-[var(--border-subtle)] last:border-0">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-[var(--text-primary)]">{exp.name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-[var(--text-secondary)]">{exp.type || exp.experiment_type}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <Badge variant={statusVariant(exp.status || "pending")}>
                      {exp.status || "pending"}
                    </Badge>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-[var(--text-secondary)]">{exp.sample_size || "\u2014"}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-[var(--text-secondary)]">{exp.winner || "\u2014"}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <Button size="sm" onClick={() => viewResults(exp)}>
                      View Results
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {/* Results Panel */}
      {selectedExperiment && (
        <Card padding="lg">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-[var(--text-primary)]">
              Results: {selectedExperiment.name}
            </h3>
            <Button variant="ghost" size="sm" onClick={() => { setSelectedExperiment(null); setResults(null); }}>
              Close
            </Button>
          </div>
          {loadingResults ? (
            <Spinner text="Loading results..." />
          ) : results ? (
            <pre className="text-sm text-[var(--text-muted)] whitespace-pre-wrap code-block p-4 rounded-md">
              {JSON.stringify(results, null, 2)}
            </pre>
          ) : (
            <p className="text-[var(--text-muted)]">No results available.</p>
          )}
        </Card>
      )}
    </div>
  );
}
