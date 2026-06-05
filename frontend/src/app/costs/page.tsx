"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PageHeader, Card, VentureSelector, Spinner, EmptyState, StatCard, Badge } from "@/components/ui";
import { statusVariant } from "@/components/ui/badge";

export default function CostsPage() {
  const [selectedVenture, setSelectedVenture] = useState("");
  const [report, setReport] = useState<any>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (selectedVenture) {
      loadCostData();
    }
  }, [selectedVenture]);

  async function loadCostData() {
    setLoading(true);
    try {
      const [reportData, alertsData] = await Promise.all([
        api.costs.report(selectedVenture),
        api.costs.alerts(selectedVenture).catch(() => []),
      ]);
      setReport(reportData);
      setAlerts(alertsData);
      setError("");
    } catch (e: any) {
      setError(e.message || "Failed to load cost data");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Costs"
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
        <EmptyState message="Select a venture to view cost report." />
      ) : loading ? (
        <Spinner text="Loading cost data..." />
      ) : report ? (
        <div className="space-y-6">
          {/* Total Spend */}
          <StatCard
            label="Total Spend"
            value={`$${typeof report.total_spend === "number" ? report.total_spend.toFixed(2) : report.total_spend || "0.00"}`}
            icon="M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            color="from-green-500 to-emerald-600"
          />

          {/* By Module Breakdown */}
          {report.by_module && (
            <Card padding="lg">
              <h3 className="text-lg font-medium text-[var(--text-primary)] mb-4">By Module</h3>
              <div className="space-y-2">
                {Object.entries(report.by_module as Record<string, number>).map(([module, cost]) => (
                  <div key={module} className="flex items-center justify-between py-2 border-b border-[var(--border-subtle)] last:border-0">
                    <span className="text-sm font-medium text-[var(--text-secondary)] capitalize">{module}</span>
                    <span className="text-sm text-[var(--text-primary)]">
                      ${typeof cost === "number" ? cost.toFixed(2) : String(cost)}
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* By Provider Breakdown */}
          {report.by_provider && (
            <Card padding="lg">
              <h3 className="text-lg font-medium text-[var(--text-primary)] mb-4">By Provider</h3>
              <div className="space-y-2">
                {Object.entries(report.by_provider as Record<string, number>).map(([provider, cost]) => (
                  <div key={provider} className="flex items-center justify-between py-2 border-b border-[var(--border-subtle)] last:border-0">
                    <span className="text-sm font-medium text-[var(--text-secondary)]">{provider}</span>
                    <span className="text-sm text-[var(--text-primary)]">
                      ${typeof cost === "number" ? cost.toFixed(2) : String(cost)}
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Raw report fallback */}
          {!report.by_module && !report.by_provider && (
            <Card padding="lg">
              <h3 className="text-lg font-medium text-[var(--text-primary)] mb-4">Report Details</h3>
              <pre className="text-sm text-[var(--text-muted)] whitespace-pre-wrap code-block p-4 rounded-md">
                {JSON.stringify(report, null, 2)}
              </pre>
            </Card>
          )}
        </div>
      ) : (
        <EmptyState message="No cost data available." />
      )}

      {/* Alerts Section */}
      {alerts.length > 0 && (
        <Card padding="lg">
          <h3 className="text-lg font-medium text-[var(--text-primary)] mb-4">Alerts</h3>
          <div className="space-y-3">
            {alerts.map((alert, i) => (
              <div
                key={i}
                className={`p-3 rounded-md text-sm border ${
                  alert.severity === "critical"
                    ? "border-red-500/30 text-red-400 bg-red-500/5"
                    : alert.severity === "warning"
                    ? "border-yellow-500/30 text-yellow-400 bg-yellow-500/5"
                    : "border-blue-500/30 text-blue-400 bg-blue-500/5"
                }`}
              >
                <p className="font-medium">{alert.title || alert.message || "Alert"}</p>
                {alert.description && <p className="mt-1 opacity-80">{alert.description}</p>}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
