"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function CostsPage() {
  const [ventures, setVentures] = useState<any[]>([]);
  const [selectedVenture, setSelectedVenture] = useState("");
  const [report, setReport] = useState<any>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.ventures.list().then(setVentures).catch(() => {});
  }, []);

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
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Costs</h1>

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
        <p className="text-gray-500">Select a venture to view cost report.</p>
      ) : loading ? (
        <p className="text-gray-500">Loading cost data...</p>
      ) : report ? (
        <div className="space-y-6">
          {/* Total Spend */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-2">Total Spend</h3>
            <p className="text-3xl font-bold text-gray-900">
              ${typeof report.total_spend === "number" ? report.total_spend.toFixed(2) : report.total_spend || "0.00"}
            </p>
          </div>

          {/* By Module Breakdown */}
          {report.by_module && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">By Module</h3>
              <div className="space-y-2">
                {Object.entries(report.by_module as Record<string, number>).map(([module, cost]) => (
                  <div key={module} className="flex items-center justify-between py-2 border-b border-gray-100">
                    <span className="text-sm font-medium text-gray-700 capitalize">{module}</span>
                    <span className="text-sm text-gray-900">
                      ${typeof cost === "number" ? cost.toFixed(2) : String(cost)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* By Provider Breakdown */}
          {report.by_provider && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">By Provider</h3>
              <div className="space-y-2">
                {Object.entries(report.by_provider as Record<string, number>).map(([provider, cost]) => (
                  <div key={provider} className="flex items-center justify-between py-2 border-b border-gray-100">
                    <span className="text-sm font-medium text-gray-700">{provider}</span>
                    <span className="text-sm text-gray-900">
                      ${typeof cost === "number" ? cost.toFixed(2) : String(cost)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Raw report fallback */}
          {!report.by_module && !report.by_provider && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Report Details</h3>
              <pre className="text-sm text-gray-600 whitespace-pre-wrap bg-gray-50 p-4 rounded-md">
                {JSON.stringify(report, null, 2)}
              </pre>
            </div>
          )}
        </div>
      ) : (
        <p className="text-gray-500">No cost data available.</p>
      )}

      {/* Alerts Section */}
      {alerts.length > 0 && (
        <div className="mt-6 bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Alerts</h3>
          <div className="space-y-3">
            {alerts.map((alert, i) => (
              <div
                key={i}
                className={`p-3 rounded-md text-sm ${
                  alert.severity === "critical"
                    ? "bg-red-50 text-red-800 border border-red-200"
                    : alert.severity === "warning"
                    ? "bg-yellow-50 text-yellow-800 border border-yellow-200"
                    : "bg-blue-50 text-blue-800 border border-blue-200"
                }`}
              >
                <p className="font-medium">{alert.title || alert.message || "Alert"}</p>
                {alert.description && <p className="mt-1">{alert.description}</p>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
